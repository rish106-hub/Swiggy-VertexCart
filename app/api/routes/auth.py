from __future__ import annotations
"""POST /api/v1/auth/callback — OAuth 2.1 PKCE callback from Swiggy."""

from fastapi import APIRouter, Query
from pydantic import BaseModel

from app.core import oauth_handler

router = APIRouter()


class AuthCallbackResponse(BaseModel):
    success: bool
    session_id: str | None = None
    error: str | None = None


@router.get("/auth/callback", response_model=AuthCallbackResponse)
async def oauth_callback(
    code: str = Query(..., description="Authorization code from Swiggy"),
    state: str = Query(..., description="session_id encoded as state parameter"),
) -> AuthCallbackResponse:
    """
    Receives the authorization code after user approves Swiggy OAuth.
    Exchanges code for JWT access token via PKCE flow.
    Stores token in sessions table.
    PRD ref: Section 8.3 (Module 2 — OAuth 2.1 PKCE Handler)

    Stub: wired in Sprint 3.
    """
    raise NotImplementedError("Auth callback wired in Sprint 3")
