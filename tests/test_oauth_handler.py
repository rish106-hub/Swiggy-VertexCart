from __future__ import annotations

"""
Unit tests for OAuth 2.1 PKCE handler.
PRD ref: Section 8.3 (Module 2 — OAuth 2.1 PKCE Handler)
"""

import uuid
from datetime import datetime, timedelta, timezone

import pytest

from app.core.oauth_handler import (
    OAuthExpiredError,
    _derive_code_challenge,
    _generate_code_verifier,
    _pending_verifiers,
    is_mcp_auth_error,
    token_expiry_from_now,
    validate_token,
    build_authorization_url,
    exchange_code_for_token,
)


# ── PKCE helpers ──────────────────────────────────────────────────────────────

class TestPkceHelpers:
    def test_verifier_length_in_valid_range(self):
        """RFC 7636: verifier must be 43–128 URL-safe Base64 chars."""
        verifier = _generate_code_verifier()
        assert 43 <= len(verifier) <= 128

    def test_verifier_is_url_safe(self):
        """No +, /, or = characters in verifier."""
        verifier = _generate_code_verifier()
        assert "+" not in verifier
        assert "/" not in verifier
        assert "=" not in verifier

    def test_verifier_is_unique_per_call(self):
        v1 = _generate_code_verifier()
        v2 = _generate_code_verifier()
        assert v1 != v2

    def test_challenge_is_deterministic_for_verifier(self):
        verifier = _generate_code_verifier()
        c1 = _derive_code_challenge(verifier)
        c2 = _derive_code_challenge(verifier)
        assert c1 == c2

    def test_challenge_differs_from_verifier(self):
        verifier = _generate_code_verifier()
        challenge = _derive_code_challenge(verifier)
        assert challenge != verifier

    def test_challenge_has_no_padding(self):
        """URL-safe Base64 must have padding stripped."""
        verifier = _generate_code_verifier()
        challenge = _derive_code_challenge(verifier)
        assert "=" not in challenge


# ── validate_token ────────────────────────────────────────────────────────────

class TestValidateToken:
    def test_valid_token_does_not_raise(self):
        future = datetime.now(tz=timezone.utc) + timedelta(days=3)
        validate_token("some.jwt.token", future)  # Should not raise

    def test_missing_token_raises(self):
        future = datetime.now(tz=timezone.utc) + timedelta(days=3)
        with pytest.raises(OAuthExpiredError, match="No access token"):
            validate_token(None, future)

    def test_expired_token_raises(self):
        past = datetime.now(tz=timezone.utc) - timedelta(seconds=1)
        with pytest.raises(OAuthExpiredError, match="expired"):
            validate_token("some.jwt.token", past)

    def test_none_expiry_raises(self):
        with pytest.raises(OAuthExpiredError, match="expiry not recorded"):
            validate_token("some.jwt.token", None)

    def test_naive_datetime_treated_as_utc(self):
        """Timezone-naive expiry should be treated as UTC — not crash."""
        past = datetime.utcnow() - timedelta(seconds=1)
        with pytest.raises(OAuthExpiredError):
            validate_token("token", past)


# ── is_mcp_auth_error ─────────────────────────────────────────────────────────

class TestIsMcpAuthError:
    def test_http_401_is_auth_error(self):
        assert is_mcp_auth_error(401) is True

    def test_jsonrpc_minus_32001_is_auth_error(self):
        assert is_mcp_auth_error(200, json_rpc_code=-32001) is True

    def test_http_200_success_is_not_auth_error(self):
        assert is_mcp_auth_error(200) is False

    def test_http_500_is_not_auth_error(self):
        assert is_mcp_auth_error(500) is False


# ── token_expiry_from_now ─────────────────────────────────────────────────────

def test_token_expiry_is_five_days_from_now():
    before = datetime.now(tz=timezone.utc)
    expiry = token_expiry_from_now()
    after = datetime.now(tz=timezone.utc)
    assert before + timedelta(days=4, hours=23) < expiry < after + timedelta(days=5, seconds=5)


# ── build_authorization_url ───────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_build_authorization_url_contains_required_params(monkeypatch):
    monkeypatch.setattr("app.core.oauth_handler.settings.swiggy_client_id", "test-client")
    monkeypatch.setattr("app.core.oauth_handler.settings.swiggy_auth_url", "https://auth.example.com/oauth")
    monkeypatch.setattr("app.core.oauth_handler.settings.swiggy_redirect_uri", "http://localhost:8000/api/v1/auth/callback")

    session_id = uuid.uuid4()
    url, verifier = await build_authorization_url(session_id)

    assert "code_challenge_method=S256" in url
    assert "response_type=code" in url
    assert "scope=mcp%3Atools" in url or "scope=mcp:tools" in url
    assert str(session_id) in url
    assert len(verifier) >= 43


@pytest.mark.asyncio
async def test_build_authorization_url_stores_verifier(monkeypatch):
    monkeypatch.setattr("app.core.oauth_handler.settings.swiggy_client_id", "test-client")
    monkeypatch.setattr("app.core.oauth_handler.settings.swiggy_auth_url", "https://auth.example.com/oauth")
    monkeypatch.setattr("app.core.oauth_handler.settings.swiggy_redirect_uri", "http://localhost:8000/api/v1/auth/callback")

    session_id = uuid.uuid4()
    _, verifier = await build_authorization_url(session_id)

    assert _pending_verifiers.get(str(session_id)) == verifier


# ── exchange_code_for_token (mock mode) ───────────────────────────────────────

@pytest.mark.asyncio
async def test_exchange_code_mock_mode_returns_fake_token(monkeypatch):
    monkeypatch.setattr("app.core.oauth_handler.settings.mock_mode", True)

    session_id = uuid.uuid4()
    _pending_verifiers[str(session_id)] = "fake-verifier"

    token = await exchange_code_for_token(session_id, "auth-code-123", "fake-verifier")
    assert token == "mock.jwt.token.vertexcart"


@pytest.mark.asyncio
async def test_exchange_code_mock_mode_clears_verifier(monkeypatch):
    monkeypatch.setattr("app.core.oauth_handler.settings.mock_mode", True)

    session_id = uuid.uuid4()
    _pending_verifiers[str(session_id)] = "fake-verifier"

    await exchange_code_for_token(session_id, "code", "fake-verifier")
    assert str(session_id) not in _pending_verifiers
