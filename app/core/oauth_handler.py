from __future__ import annotations
"""
OAuth 2.1 PKCE handler for Swiggy MCP authentication.
PRD ref: Section 8.3 (Module 2 — OAuth 2.1 PKCE Handler), Section 2.3 (Hard Constraints)

One token covers all three MCP servers (food, instamart, dineout).
No refresh tokens in v1 — re-auth required on expiry.

Stub: filled in Sprint 3.
"""

import uuid


class OAuthExpiredError(Exception):
    """Raised when the Swiggy access token is expired or invalid."""
    pass


async def build_authorization_url(session_id: uuid.UUID) -> tuple[str, str]:
    """
    Generate PKCE code_verifier + authorization URL.
    Returns (authorization_url, code_verifier) — caller must persist verifier in session.
    """
    raise NotImplementedError("OAuth handler implemented in Sprint 3")


async def exchange_code_for_token(
    session_id: uuid.UUID,
    code: str,
    code_verifier: str,
) -> str:
    """
    Exchange authorization code for JWT access token.
    Stores token + expiry in sessions table.
    Returns the access token.
    """
    raise NotImplementedError("OAuth handler implemented in Sprint 3")


def validate_token(token: str | None, expires_at) -> None:
    """Raise OAuthExpiredError if token is missing or past its expiry."""
    raise NotImplementedError("OAuth handler implemented in Sprint 3")
