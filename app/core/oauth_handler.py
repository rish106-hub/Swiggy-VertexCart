from __future__ import annotations

"""
OAuth 2.1 PKCE handler for Swiggy MCP authentication.
PRD ref: Section 8.3 (Module 2), Section 2.3 (Hard Constraints — authentication)

Flow:
  1. build_authorization_url()  → redirect user to Swiggy consent page
  2. exchange_code_for_token()  → swap authorization code for JWT
  3. validate_token()           → check expiry before every MCP call

One JWT covers all three servers: food, instamart, dineout.
No refresh tokens in v1 — full re-auth on expiry (OAuthExpiredError).

In MOCK_MODE: token exchange returns a hardcoded fake JWT, no network calls.
"""

import base64
import hashlib
import logging
import os
import uuid
from datetime import datetime, timedelta, timezone

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

# JWT lifetime per Swiggy v1 spec (PRD Section 2.3)
_TOKEN_LIFETIME_DAYS = 5

# In-memory store for code_verifiers keyed by session_id (cleared after exchange)
# Production: move to Redis or DB if horizontal scaling is needed
_pending_verifiers: dict[str, str] = {}

_MOCK_TOKEN = "mock.jwt.token.vertexcart"


# ── Exceptions ────────────────────────────────────────────────────────────────

class OAuthExpiredError(Exception):
    """
    Raised when the Swiggy access token is expired or invalid (HTTP 401 / JSON-RPC -32001).
    Caller must re-initiate the OAuth flow once, then retry.
    PRD ref: Section 7.6 (Edge Case 7 — OAuth expiry mid-session)
    """
    pass


class OAuthExchangeError(Exception):
    """Raised when the authorization code exchange fails (non-401 error)."""
    pass


# ── PKCE helpers ──────────────────────────────────────────────────────────────

def _generate_code_verifier() -> str:
    """
    Generate a cryptographically random PKCE code_verifier.
    RFC 7636: 43–128 URL-safe Base64 characters, no padding.
    """
    raw = os.urandom(64)
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _derive_code_challenge(verifier: str) -> str:
    """
    Derive PKCE code_challenge from verifier using S256 method.
    challenge = BASE64URL(SHA256(ASCII(verifier)))
    """
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")


# ── Public API ────────────────────────────────────────────────────────────────

async def build_authorization_url(session_id: uuid.UUID) -> tuple[str, str]:
    """
    Generate PKCE verifier/challenge and build the Swiggy authorization URL.

    Returns:
        (authorization_url, code_verifier)
        Caller must persist code_verifier in the session row — needed for token exchange.

    PRD ref: Section 8.3 (Module 2 — step 1)
    """
    verifier = _generate_code_verifier()
    challenge = _derive_code_challenge(verifier)

    # Persist verifier in memory until exchange completes
    _pending_verifiers[str(session_id)] = verifier

    params = {
        "client_id": settings.swiggy_client_id,
        "redirect_uri": settings.swiggy_redirect_uri,
        "response_type": "code",
        "code_challenge": challenge,
        "code_challenge_method": "S256",
        "scope": "mcp:tools",
        "state": str(session_id),  # Round-trip session_id for callback binding
    }
    query_string = "&".join(f"{k}={v}" for k, v in params.items())
    authorization_url = f"{settings.swiggy_auth_url}?{query_string}"

    logger.info("OAuth: authorization URL built for session %s", session_id)
    return authorization_url, verifier


async def exchange_code_for_token(
    session_id: uuid.UUID,
    code: str,
    code_verifier: str,
) -> str:
    """
    Exchange an authorization code for a Swiggy JWT access token.

    Stores token + expiry in the sessions table (via caller — returns token string).
    Clears the in-memory verifier after successful exchange.

    In MOCK_MODE: returns a hardcoded fake token without network calls.

    PRD ref: Section 8.3 (Module 2 — step 2)
    """
    if settings.mock_mode:
        logger.warning("[MOCK] OAuth token exchange — returning fake JWT for session %s", session_id)
        _pending_verifiers.pop(str(session_id), None)
        return _MOCK_TOKEN

    payload = {
        "grant_type": "authorization_code",
        "code": code,
        "code_verifier": code_verifier,
        "client_id": settings.swiggy_client_id,
        "redirect_uri": settings.swiggy_redirect_uri,
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(settings.swiggy_token_url, data=payload)
    except httpx.RequestError as exc:
        raise OAuthExchangeError(f"Token endpoint unreachable: {exc}") from exc

    if response.status_code == 401:
        raise OAuthExpiredError("Token exchange rejected with 401 — invalid code or verifier")

    if not response.is_success:
        raise OAuthExchangeError(
            f"Token exchange failed: HTTP {response.status_code} — {response.text[:200]}"
        )

    data = response.json()
    token = data.get("access_token")
    if not token:
        raise OAuthExchangeError("Token endpoint returned no access_token field")

    _pending_verifiers.pop(str(session_id), None)
    logger.info("OAuth: token exchanged successfully for session %s", session_id)
    return token


def token_expiry_from_now() -> datetime:
    """Return the expiry timestamp for a freshly issued Swiggy JWT."""
    return datetime.now(tz=timezone.utc) + timedelta(days=_TOKEN_LIFETIME_DAYS)


def validate_token(token: str | None, expires_at: datetime | None) -> None:
    """
    Raise OAuthExpiredError if the token is missing or past its expiry.
    Called before every MCP tool invocation.

    PRD ref: Section 8.3 (Module 2 — step 3), Section 7.6 (Edge Case 7)
    """
    if not token:
        raise OAuthExpiredError("No access token present in session")

    if expires_at is None:
        raise OAuthExpiredError("Token expiry not recorded — treat as expired")

    # Normalise to UTC-aware for comparison
    now = datetime.now(tz=timezone.utc)
    expiry = expires_at if expires_at.tzinfo else expires_at.replace(tzinfo=timezone.utc)

    if now >= expiry:
        raise OAuthExpiredError(
            f"Token expired at {expiry.isoformat()} (now {now.isoformat()})"
        )


def is_mcp_auth_error(http_status: int, json_rpc_code: int | None = None) -> bool:
    """
    Detect auth failures from Swiggy MCP responses.
    Covers HTTP 401 and JSON-RPC error code -32001.
    PRD ref: Section 8.3 (Module 6 — Error Classifier, auth_failure bucket)
    """
    return http_status == 401 or json_rpc_code == -32001
