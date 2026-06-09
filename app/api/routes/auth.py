from __future__ import annotations

"""POST /api/v1/auth/callback — OAuth 2.1 PKCE callback from Swiggy."""

import uuid
import logging

from fastapi import APIRouter, Query, HTTPException
from pydantic import BaseModel

from app.core.oauth_handler import (
    exchange_code_for_token,
    token_expiry_from_now,
    OAuthExchangeError,
    OAuthExpiredError,
)

router = APIRouter()
logger = logging.getLogger(__name__)


class AuthCallbackResponse(BaseModel):
    success: bool
    session_id: str | None = None
    error: str | None = None


@router.get("/auth/callback", response_model=AuthCallbackResponse)
async def oauth_callback(
    code: str = Query(..., description="Authorization code from Swiggy"),
    state: str = Query(..., description="session_id passed as OAuth state parameter"),
) -> AuthCallbackResponse:
    """
    Receives the authorization code after user approves Swiggy OAuth consent.
    Exchanges code for JWT access token and stores in DB session row.

    The `state` parameter carries the session_id (set during build_authorization_url).
    PRD ref: Section 8.3 (Module 2 — OAuth 2.1 PKCE Handler, step 2)
    """
    try:
        session_id = uuid.UUID(state)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid state parameter — not a UUID")

    # Code verifier was persisted when auth URL was built; pass it from in-memory store.
    # In Sprint 6, session_manager will also persist it to DB for resilience across restarts.
    from app.core.oauth_handler import _pending_verifiers
    verifier = _pending_verifiers.get(str(session_id))
    if not verifier:
        raise HTTPException(
            status_code=400,
            detail="No pending OAuth flow for this session — verifier not found",
        )

    try:
        token = await exchange_code_for_token(session_id, code, verifier)
    except (OAuthExpiredError, OAuthExchangeError) as exc:
        logger.error("OAuth callback failed for session %s: %s", session_id, exc)
        return AuthCallbackResponse(success=False, error=str(exc))

    # Token storage to DB wired in Sprint 6 (session_manager.store_token).
    # For now, log success — mock mode returns fake token.
    expiry = token_expiry_from_now()
    logger.info(
        "OAuth: token stored for session %s, expires %s", session_id, expiry.isoformat()
    )

    return AuthCallbackResponse(success=True, session_id=str(session_id))
