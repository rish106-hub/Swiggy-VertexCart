from __future__ import annotations

"""
End-to-end smoke tests for all FastAPI routes in MOCK_MODE.
PRD ref: Section 8.3 (Phase 1 Completion Checklist)

Verifies the full mock flow:
  session created → turn processed → cart readable → mock orders placed

Uses FastAPI TestClient (synchronous) via httpx.
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.core.session_manager import _mock_sessions, _mock_turns


# ── Client fixture ────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def client():
    """
    Module-scoped TestClient — shares one app instance across all smoke tests.
    Startup/shutdown events are NOT fired by TestClient by default; use context manager.
    """
    with TestClient(app, raise_server_exceptions=True) as c:
        yield c


@pytest.fixture(autouse=True)
def clean_mock_store():
    _mock_sessions.clear()
    _mock_turns.clear()
    yield
    _mock_sessions.clear()
    _mock_turns.clear()


# ── Health ────────────────────────────────────────────────────────────────────

def test_health_returns_ok(client):
    """Gate 1: server starts and /health returns 200 with mock_mode=true."""
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["mock_mode"] is True


# ── Intent ────────────────────────────────────────────────────────────────────

def test_intent_endpoint_returns_intent_result(client):
    """Gate 2: /intent returns valid IntentResult for test input."""
    resp = client.post("/api/v1/intent", json={
        "text": "pasta tonight and tiramisu dessert",
        "user_id": "smoke_user",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert "entities" in data
    assert "requires_clarification" in data
    assert isinstance(data["entities"], list)


# ── Session ───────────────────────────────────────────────────────────────────

def test_create_session_returns_session_id(client):
    """Gate 3: /session creates session and returns session_id UUID."""
    resp = client.post("/api/v1/session", json={"user_id": "smoke_user"})
    assert resp.status_code == 200
    data = resp.json()
    assert "session_id" in data
    # Must be a valid UUID
    import uuid
    uuid.UUID(data["session_id"])


def test_session_not_found_returns_404(client):
    import uuid
    fake_id = str(uuid.uuid4())
    resp = client.get(f"/api/v1/session/{fake_id}/history")
    assert resp.status_code == 404


# ── Turn ──────────────────────────────────────────────────────────────────────

def test_turn_processes_food_intent(client):
    """Gate 4: turn processes food intent and returns agent response with cart summary."""
    session_resp = client.post("/api/v1/session", json={"user_id": "smoke_u1"})
    session_id = session_resp.json()["session_id"]

    resp = client.post(f"/api/v1/session/{session_id}/turn", json={
        "text": "order tiramisu for dessert"
    })
    assert resp.status_code == 200
    data = resp.json()
    assert "agent_response" in data
    assert isinstance(data["agent_response"], str)
    assert len(data["agent_response"]) > 0
    assert "verticals_active" in data
    assert "cart_summary" in data


def test_turn_processes_instamart_intent(client):
    session_resp = client.post("/api/v1/session", json={"user_id": "smoke_u2"})
    session_id = session_resp.json()["session_id"]

    resp = client.post(f"/api/v1/session/{session_id}/turn", json={
        "text": "pasta ingredients for tonight"
    })
    assert resp.status_code == 200
    data = resp.json()
    assert "agent_response" in data


def test_turn_returns_clarification_for_ambiguous_input(client):
    """Ambiguous intent → requires_clarification=True, no tool calls needed."""
    session_resp = client.post("/api/v1/session", json={"user_id": "smoke_u3"})
    session_id = session_resp.json()["session_id"]

    # Mock mode always returns the same IntentResult — test with clearly ambiguous text
    # The mock IntentResult has requires_clarification=False, so patch it
    import app.core.intent_parser as ip
    from app.models.intent import IntentResult, Occasion, Urgency

    original_parse = ip.parse

    async def ambiguous_parse(text):
        return IntentResult(
            entities=[],
            occasion=Occasion.UNKNOWN,
            urgency=Urgency.UNKNOWN,
            requires_clarification=True,
            raw_input=text,
        )

    ip.parse = ambiguous_parse
    try:
        resp = client.post(f"/api/v1/session/{session_id}/turn", json={
            "text": "something nice tonight"
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["requires_clarification"] is True
    finally:
        ip.parse = original_parse


def test_turn_404_for_unknown_session(client):
    import uuid
    resp = client.post(f"/api/v1/session/{uuid.uuid4()}/turn", json={"text": "hi"})
    assert resp.status_code == 404


# ── Cart ──────────────────────────────────────────────────────────────────────

def test_cart_endpoint_returns_live_state(client):
    """Gate 5: /cart calls get_food_cart + get_cart and returns live data."""
    session_resp = client.post("/api/v1/session", json={"user_id": "smoke_u4"})
    session_id = session_resp.json()["session_id"]

    # Add a food turn so food vertical is active
    client.post(f"/api/v1/session/{session_id}/turn", json={"text": "order biryani"})

    resp = client.get(f"/api/v1/session/{session_id}/cart")
    assert resp.status_code == 200
    data = resp.json()
    # Cart state is a dict — food or instamart keys present when vertical active
    assert isinstance(data, dict)


def test_cart_404_for_unknown_session(client):
    import uuid
    resp = client.get(f"/api/v1/session/{uuid.uuid4()}/cart")
    assert resp.status_code == 404


# ── Confirm ───────────────────────────────────────────────────────────────────

def test_confirm_food_order_in_mock_mode(client):
    """Gate 6: /confirm for food vertical triggers orchestrator, returns order_id."""
    session_resp = client.post("/api/v1/session", json={"user_id": "smoke_u5"})
    session_id = session_resp.json()["session_id"]

    resp = client.post(f"/api/v1/session/{session_id}/confirm", json={
        "vertical": "food"
    })
    assert resp.status_code == 200
    data = resp.json()
    assert "order_id" in data
    assert data["vertical"] == "food"


def test_confirm_instamart_order_in_mock_mode(client):
    session_resp = client.post("/api/v1/session", json={"user_id": "smoke_u6"})
    session_id = session_resp.json()["session_id"]

    resp = client.post(f"/api/v1/session/{session_id}/confirm", json={
        "vertical": "instamart"
    })
    assert resp.status_code == 200
    data = resp.json()
    assert "order_id" in data
    assert data["vertical"] == "instamart"


def test_confirm_404_for_unknown_session(client):
    import uuid
    resp = client.post(f"/api/v1/session/{uuid.uuid4()}/confirm", json={
        "vertical": "food"
    })
    assert resp.status_code == 404


# ── Orders ────────────────────────────────────────────────────────────────────

def test_orders_endpoint_returns_list(client):
    """Gate 7: /orders returns list (empty in mock mode — no DB persistence yet)."""
    session_resp = client.post("/api/v1/session", json={"user_id": "smoke_u7"})
    session_id = session_resp.json()["session_id"]

    resp = client.get(f"/api/v1/session/{session_id}/orders")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


# ── History ───────────────────────────────────────────────────────────────────

def test_history_returns_turns_after_conversation(client):
    session_resp = client.post("/api/v1/session", json={"user_id": "smoke_u8"})
    session_id = session_resp.json()["session_id"]

    client.post(f"/api/v1/session/{session_id}/turn", json={"text": "order biryani"})

    resp = client.get(f"/api/v1/session/{session_id}/history")
    assert resp.status_code == 200
    turns = resp.json()
    assert isinstance(turns, list)
    assert len(turns) >= 1   # At least the user turn
    assert all("role" in t for t in turns)


# ── Full mock flow — intent → turn → cart → confirm ──────────────────────────

def test_full_mock_flow_food_plus_instamart(client):
    """
    Complete flow smoke test:
      create session → send multi-vertical turn → read cart → confirm food → confirm instamart
    PRD ref: Phase 1 Completion Checklist
    """
    # 1. Create session
    session_resp = client.post("/api/v1/session", json={"user_id": "flow_user"})
    assert session_resp.status_code == 200
    session_id = session_resp.json()["session_id"]

    # 2. Send turn
    turn_resp = client.post(f"/api/v1/session/{session_id}/turn", json={
        "text": "pasta tonight and tiramisu dessert"
    })
    assert turn_resp.status_code == 200
    turn_data = turn_resp.json()
    assert len(turn_data["agent_response"]) > 0

    # 3. Read live cart
    cart_resp = client.get(f"/api/v1/session/{session_id}/cart")
    assert cart_resp.status_code == 200

    # 4. Confirm food order
    food_confirm = client.post(f"/api/v1/session/{session_id}/confirm", json={
        "vertical": "food"
    })
    assert food_confirm.status_code == 200
    assert food_confirm.json()["order_id"]

    # 5. Confirm instamart order
    im_confirm = client.post(f"/api/v1/session/{session_id}/confirm", json={
        "vertical": "instamart"
    })
    assert im_confirm.status_code == 200
    assert im_confirm.json()["order_id"]

    # 6. Read orders (empty in mock — no DB)
    orders_resp = client.get(f"/api/v1/session/{session_id}/orders")
    assert orders_resp.status_code == 200
