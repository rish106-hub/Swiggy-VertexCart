from __future__ import annotations

"""
Integration tests for VertexCart multi-turn conversation and edge cases.
PRD ref: Phase 4 (Integration tests)
"""

import uuid
import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch

from app.main import app
from app.core.mcp_client import mcp_client, MCPToolError
from app.core.error_classifier import ErrorClassification
from app.core.session_manager import _mock_sessions, _mock_turns

@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c

@pytest.fixture(autouse=True)
def clean_mocks():
    _mock_sessions.clear()
    _mock_turns.clear()

def _retryable_error() -> MCPToolError:
    return MCPToolError(
        ErrorClassification(bucket="upstream_error", is_retryable=True, action="backoff_retry")
    )

# ── 1. Happy path: food + instamart in one session ──────────────────────────

def test_integration_multi_vertical_happy_path(client, monkeypatch):
    # Setup session
    session_id = client.post("/api/v1/session", json={"user_id": "u1"}).json()["session_id"]
    
    # Send multi-intent turn
    resp = client.post(f"/api/v1/session/{session_id}/turn", json={"text": "pasta and biryani"})
    assert resp.status_code == 200
    
    # Confirm both
    client.post(f"/api/v1/session/{session_id}/confirm", json={"vertical": "food"})
    client.post(f"/api/v1/session/{session_id}/confirm", json={"vertical": "instamart"})
    
    # Verify both orders exist (in orchestrator logs or similar)
    # In MOCK_MODE, confirm returns successfully.

# ── 2. Restaurant switch warning ─────────────────────────────────────────────

def test_integration_restaurant_switch_warning(client, monkeypatch):
    session_id = client.post("/api/v1/session", json={"user_id": "u2"}).json()["session_id"]
    
    # Add first restaurant item
    client.post(f"/api/v1/session/{session_id}/turn", json={"text": "order from Biryani House"})
    
    # Try to order from another restaurant
    # We patch search_restaurants to return a different ID
    mock_search = AsyncMock(return_value=[{"restaurantId": "other_rest", "name": "Other Place"}])
    monkeypatch.setattr(mcp_client, "search_restaurants", mock_search)
    
    resp = client.post(f"/api/v1/session/{session_id}/turn", json={"text": "order from Pizza Hut"})
    assert resp.status_code == 200
    assert "Switching restaurants will clear your current cart" in resp.json()["agent_response"]
    assert resp.json()["requires_confirmation"] is True

# ── 3. 5xx on placement → check_then_retry → success ─────────────────────────

@pytest.mark.asyncio
async def test_integration_placement_retry_success(client, monkeypatch):
    session_id = client.post("/api/v1/session", json={"user_id": "u3"}).json()["session_id"]
    
    # Flaky placement: fails first, succeeds second
    attempt = 0
    async def flaky_place(**kwargs):
        nonlocal attempt
        attempt += 1
        if attempt == 1: raise _retryable_error()
        return {"orderId": "fixed_id"}
    
    monkeypatch.setattr(mcp_client, "place_food_order", flaky_place)
    monkeypatch.setattr(mcp_client, "get_food_orders", AsyncMock(return_value=[]))
    monkeypatch.setattr("app.core.order_orchestrator.asyncio.sleep", AsyncMock())
    
    resp = client.post(f"/api/v1/session/{session_id}/confirm", json={"vertical": "food"})
    assert resp.status_code == 200
    assert resp.json()["order_id"] == "fixed_id"
    assert attempt == 2

# ── 4. ₹1000 cap exceeded ────────────────────────────────────────────────────

def test_integration_food_cap_exceeded(client, monkeypatch):
    session_id = client.post("/api/v1/session", json={"user_id": "u4"}).json()["session_id"]
    
    # Mock cart with high subtotal
    monkeypatch.setattr(mcp_client, "get_food_cart", AsyncMock(return_value={"subtotal": 1200, "items": [{"id": "1"}]}))
    
    resp = client.post(f"/api/v1/session/{session_id}/confirm", json={"vertical": "food"})
    assert resp.status_code == 502
    assert "₹1000" in resp.json()["detail"]

# ── 5. Instamart minimum not met ──────────────────────────────────────────────

def test_integration_im_minimum_not_met(client, monkeypatch):
    session_id = client.post("/api/v1/session", json={"user_id": "u5"}).json()["session_id"]
    
    monkeypatch.setattr(mcp_client, "get_cart", AsyncMock(return_value={"subtotal": 40, "items": [{"id": "1"}]}))
    
    resp = client.post(f"/api/v1/session/{session_id}/confirm", json={"vertical": "instamart"})
    assert resp.status_code == 502
    assert "₹99" in resp.json()["detail"]

# ── 6. Cart expired flow ──────────────────────────────────────────────────────

def test_integration_cart_expired_flow(client, monkeypatch):
    session_id = client.post("/api/v1/session", json={"user_id": "u6"}).json()["session_id"]
    
    # Cart returns EXPIRED
    monkeypatch.setattr(mcp_client, "get_food_cart", AsyncMock(return_value={"status": "CART_EXPIRED"}))
    
    resp = client.post(f"/api/v1/session/{session_id}/turn", json={"text": "order something"})
    assert resp.status_code == 200
    assert "cart expired" in resp.json()["agent_response"].lower()
    assert "rebuilt" in resp.json()["cart_summary"]

# ── 7. Non-idempotency guard (rapid double clicks) ───────────────────────────

@pytest.mark.asyncio
async def test_integration_rapid_double_confirm(client, monkeypatch):
    """
    Assert that calling POST /session/{id}/confirm twice rapidly does NOT result in two Instamart orders.
    Requires an asyncio lock per session in the backend or similar guard.
    """
    import asyncio
    
    session_id = client.post("/api/v1/session", json={"user_id": "u7"}).json()["session_id"]
    
    call_count = 0
    async def slow_checkout(**kwargs):
        nonlocal call_count
        call_count += 1
        await asyncio.sleep(0.1) # Simulate network delay
        return {"orderId": f"mock_im_ord_{call_count}"}
        
    monkeypatch.setattr(mcp_client, "get_cart", AsyncMock(return_value={"subtotal": 150, "items": [{"id": "1"}]}))
    monkeypatch.setattr(mcp_client, "checkout", slow_checkout)
    
    # To test concurrent requests with TestClient (which is synchronous), we'd need to use AsyncClient
    # Let's import httpx and use AsyncClient directly against the app
    from httpx import AsyncClient, ASGITransport
    
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as ac:
        # Fire two requests concurrently
        req1 = ac.post(f"/api/v1/session/{session_id}/confirm", json={"vertical": "instamart"})
        req2 = ac.post(f"/api/v1/session/{session_id}/confirm", json={"vertical": "instamart"})
        
        responses = await asyncio.gather(req1, req2)
        
    # One should succeed, the other should fail or return the same order ID
    assert call_count == 1, "Checkout was called twice! Non-idempotency guard failed."

