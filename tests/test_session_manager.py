from __future__ import annotations

"""
Unit tests for multi-turn session manager.
PRD ref: Section 8.3 (Module 3), Section 7.4 (Multi-Turn Cart State Management)

All tests run in MOCK_MODE — no DB required.
"""

import uuid

import pytest

from app.core import session_manager
from app.core.mcp_client import mcp_client
from app.core.session_manager import (
    build_llm_context,
    create_session,
    add_turn,
    get_conversation_history,
    get_active_verticals,
    should_warn_restaurant_switch,
    should_warn_address_switch,
    is_cart_expired,
    rebuild_cart_from_history,
    _mock_sessions,
    _mock_turns,
)
from app.models.intent import (
    EntityType,
    IntentEntity,
    IntentResult,
    Occasion,
    Urgency,
    Vertical,
)
from app.models.session import ConversationTurn


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def mock_mode(monkeypatch):
    monkeypatch.setattr("app.core.session_manager.settings.mock_mode", True)


@pytest.fixture(autouse=True)
def clean_mock_store():
    """Isolate tests — clear in-memory store before each test."""
    _mock_sessions.clear()
    _mock_turns.clear()
    yield
    _mock_sessions.clear()
    _mock_turns.clear()


def _food_intent(text: str = "order biryani") -> IntentResult:
    return IntentResult(
        entities=[IntentEntity(
            text=text, type=EntityType.READY_TO_EAT,
            vertical=Vertical.FOOD, confidence=0.9,
        )],
        occasion=Occasion.QUICK_SNACK,
        urgency=Urgency.IMMEDIATE,
        raw_input=text,
    )


def _instamart_intent(text: str = "pasta ingredients") -> IntentResult:
    return IntentResult(
        entities=[IntentEntity(
            text=text, type=EntityType.INGREDIENT,
            vertical=Vertical.INSTAMART, confidence=0.92,
        )],
        occasion=Occasion.WEEKNIGHT_DINNER,
        urgency=Urgency.IMMEDIATE,
        raw_input=text,
    )


def _multi_intent() -> IntentResult:
    return IntentResult(
        entities=[
            IntentEntity(text="pasta", type=EntityType.INGREDIENT,
                         vertical=Vertical.INSTAMART, confidence=0.92),
            IntentEntity(text="tiramisu", type=EntityType.READY_TO_EAT,
                         vertical=Vertical.FOOD, confidence=0.88),
        ],
        occasion=Occasion.WEEKNIGHT_DINNER,
        urgency=Urgency.IMMEDIATE,
        raw_input="pasta and tiramisu",
    )


# ── Session creation ──────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_create_session_returns_uuid():
    session_id = await create_session("user_001")
    assert isinstance(session_id, uuid.UUID)


@pytest.mark.asyncio
async def test_create_session_stored_in_mock():
    session_id = await create_session("user_001")
    assert str(session_id) in _mock_sessions
    assert _mock_sessions[str(session_id)].user_id == "user_001"


@pytest.mark.asyncio
async def test_create_session_initialises_empty_turns():
    session_id = await create_session("user_001")
    assert str(session_id) in _mock_turns
    assert _mock_turns[str(session_id)] == []


@pytest.mark.asyncio
async def test_get_session_returns_session():
    session_id = await create_session("user_abc")
    session = await session_manager.get_session(session_id)
    assert session.user_id == "user_abc"
    assert session.id == session_id


@pytest.mark.asyncio
async def test_get_session_raises_for_unknown_id():
    with pytest.raises(ValueError, match="Session not found"):
        await session_manager.get_session(uuid.uuid4())


# ── Turn persistence ──────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_add_user_turn_persists():
    session_id = await create_session("u1")
    turn_id = await add_turn(session_id, "user", "I want biryani")
    assert isinstance(turn_id, uuid.UUID)
    turns = _mock_turns[str(session_id)]
    assert len(turns) == 1
    assert turns[0].content == "I want biryani"
    assert turns[0].role == "user"


@pytest.mark.asyncio
async def test_add_agent_turn_persists():
    session_id = await create_session("u1")
    await add_turn(session_id, "user", "biryani please")
    await add_turn(session_id, "agent", "Found biryani at Biryani House")
    turns = _mock_turns[str(session_id)]
    assert len(turns) == 2
    assert turns[1].role == "agent"


@pytest.mark.asyncio
async def test_turn_numbers_increment():
    session_id = await create_session("u1")
    await add_turn(session_id, "user", "first")
    await add_turn(session_id, "agent", "response")
    await add_turn(session_id, "user", "second")
    turns = _mock_turns[str(session_id)]
    assert turns[0].turn_number == 1
    assert turns[1].turn_number == 2
    assert turns[2].turn_number == 3


@pytest.mark.asyncio
async def test_add_turn_with_intent_stores_intent():
    session_id = await create_session("u1")
    intent = _food_intent()
    await add_turn(session_id, "user", "biryani", intent=intent)
    turns = _mock_turns[str(session_id)]
    assert turns[0].intent is not None
    assert turns[0].intent.entities[0].vertical == Vertical.FOOD


@pytest.mark.asyncio
async def test_add_turn_with_tools_called_stores_tools():
    session_id = await create_session("u1")
    tools = [{"tool": "search_restaurants", "vertical": "food", "success": True}]
    await add_turn(session_id, "agent", "here are restaurants", tools_called=tools)
    turns = _mock_turns[str(session_id)]
    assert turns[0].tools_called[0]["tool"] == "search_restaurants"


# ── get_conversation_history ──────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_history_returns_turns_in_order():
    session_id = await create_session("u1")
    await add_turn(session_id, "user", "turn 1")
    await add_turn(session_id, "agent", "turn 2")
    await add_turn(session_id, "user", "turn 3")
    history = await get_conversation_history(session_id)
    assert [t.content for t in history] == ["turn 1", "turn 2", "turn 3"]


@pytest.mark.asyncio
async def test_get_history_respects_limit():
    session_id = await create_session("u1")
    for i in range(15):
        await add_turn(session_id, "user", f"turn {i}")
    history = await get_conversation_history(session_id, limit=5)
    assert len(history) == 5
    # Should be the last 5
    assert history[-1].content == "turn 14"


@pytest.mark.asyncio
async def test_get_history_empty_for_new_session():
    session_id = await create_session("u1")
    history = await get_conversation_history(session_id)
    assert history == []


# ── Active verticals ──────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_active_verticals_from_food_intent():
    session_id = await create_session("u1")
    await add_turn(session_id, "user", "biryani", intent=_food_intent())
    verticals = await get_active_verticals(session_id)
    assert Vertical.FOOD in verticals


@pytest.mark.asyncio
async def test_active_verticals_multi_vertical():
    session_id = await create_session("u1")
    await add_turn(session_id, "user", "pasta + tiramisu", intent=_multi_intent())
    verticals = await get_active_verticals(session_id)
    assert Vertical.FOOD in verticals
    assert Vertical.INSTAMART in verticals


@pytest.mark.asyncio
async def test_active_verticals_empty_for_new_session():
    session_id = await create_session("u1")
    verticals = await get_active_verticals(session_id)
    assert verticals == []


@pytest.mark.asyncio
async def test_active_verticals_deduplicated():
    """Multiple turns with same vertical should not produce duplicates."""
    session_id = await create_session("u1")
    await add_turn(session_id, "user", "biryani", intent=_food_intent())
    await add_turn(session_id, "user", "pizza too", intent=_food_intent("pizza"))
    verticals = await get_active_verticals(session_id)
    assert verticals.count(Vertical.FOOD) == 1


# ── Restaurant switch warning ─────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_restaurant_switch_warns_when_cart_exists(monkeypatch):
    """
    Cart has items at rest_001. Switching to rest_002 must trigger warning.
    PRD ref: Section 7.4 (Turn 3 — restaurant switch warning)
    """
    monkeypatch.setattr("app.core.session_manager.settings.mock_mode", True)

    async def mock_get_food_cart(token=""):
        return {
            "restaurantId": "rest_001",
            "items": [{"itemId": "item_001", "quantity": 1}],
            "subtotal": 320,
            "status": "ACTIVE",
        }

    monkeypatch.setattr(mcp_client, "get_food_cart", mock_get_food_cart)

    session_id = await create_session("u1")
    should_warn, cart = await should_warn_restaurant_switch(session_id, "rest_002", token="tok")
    assert should_warn is True
    assert cart["restaurantId"] == "rest_001"


@pytest.mark.asyncio
async def test_restaurant_switch_no_warn_same_restaurant(monkeypatch):
    """Same restaurant — no warning needed."""
    async def mock_get_food_cart(token=""):
        return {"restaurantId": "rest_001", "items": [{"itemId": "x"}], "subtotal": 100}

    monkeypatch.setattr(mcp_client, "get_food_cart", mock_get_food_cart)

    session_id = await create_session("u1")
    should_warn, _ = await should_warn_restaurant_switch(session_id, "rest_001", token="tok")
    assert should_warn is False


@pytest.mark.asyncio
async def test_restaurant_switch_no_warn_empty_cart(monkeypatch):
    """Empty cart — no items to lose, no warning needed."""
    async def mock_get_food_cart(token=""):
        return {"restaurantId": "rest_001", "items": [], "subtotal": 0}

    monkeypatch.setattr(mcp_client, "get_food_cart", mock_get_food_cart)

    session_id = await create_session("u1")
    should_warn, _ = await should_warn_restaurant_switch(session_id, "rest_002", token="tok")
    assert should_warn is False


@pytest.mark.asyncio
async def test_restaurant_switch_no_warn_on_cart_error(monkeypatch):
    """If get_food_cart raises (e.g. 5xx), assume no cart — no warning."""
    async def mock_get_food_cart(token=""):
        raise Exception("upstream error")

    monkeypatch.setattr(mcp_client, "get_food_cart", mock_get_food_cart)

    session_id = await create_session("u1")
    should_warn, _ = await should_warn_restaurant_switch(session_id, "rest_002", token="tok")
    assert should_warn is False


# ── Address switch warning (Instamart) ────────────────────────────────────────

@pytest.mark.asyncio
async def test_address_switch_warns_when_cart_exists(monkeypatch):
    """
    Instamart cart has items bound to addr_001. Switching to addr_002 must warn.
    PRD ref: Section 7.4, Section 2.3 (Instamart cart binding)
    """
    async def mock_get_cart(token=""):
        return {
            "items": [{"spinId": "spin_001", "quantity": 2}],
            "subtotal": 178,
            "deliveryAddress": {"id": "addr_001"},
        }

    monkeypatch.setattr(mcp_client, "get_cart", mock_get_cart)

    session_id = await create_session("u1")
    should_warn, _ = await should_warn_address_switch(session_id, "addr_002", token="tok")
    assert should_warn is True


@pytest.mark.asyncio
async def test_address_switch_no_warn_same_address(monkeypatch):
    async def mock_get_cart(token=""):
        return {"items": [{"spinId": "x"}], "deliveryAddress": {"id": "addr_001"}}

    monkeypatch.setattr(mcp_client, "get_cart", mock_get_cart)

    session_id = await create_session("u1")
    should_warn, _ = await should_warn_address_switch(session_id, "addr_001", token="tok")
    assert should_warn is False


# ── Cart expired detection ────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_is_cart_expired_true():
    assert await is_cart_expired({"status": "CART_EXPIRED"}) is True


@pytest.mark.asyncio
async def test_is_cart_expired_false_active():
    assert await is_cart_expired({"status": "ACTIVE"}) is False


@pytest.mark.asyncio
async def test_is_cart_expired_false_empty():
    assert await is_cart_expired({}) is False


@pytest.mark.asyncio
async def test_is_cart_expired_case_insensitive():
    assert await is_cart_expired({"status": "cart_expired"}) is True


# ── Cart rebuild from history ─────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_rebuild_cart_recovers_food_items():
    """
    Agent turn recorded an update_food_cart call.
    Rebuild should recover those items.
    PRD ref: Section 7.6 (Edge Case 8)
    """
    session_id = await create_session("u1")
    tools = [{"tool": "update_food_cart", "arguments": {
        "restaurantId": "rest_001",
        "items": [{"itemId": "item_001", "quantity": 2}],
    }}]
    await add_turn(session_id, "agent", "added tiramisu", tools_called=tools)

    rebuilt = await rebuild_cart_from_history(session_id)
    assert rebuilt["food"] == [{"itemId": "item_001", "quantity": 2}]


@pytest.mark.asyncio
async def test_rebuild_cart_recovers_instamart_items():
    session_id = await create_session("u1")
    tools = [{"tool": "update_cart", "arguments": {
        "items": [
            {"spinId": "spin_001", "quantity": 2},
            {"spinId": "spin_002", "quantity": 1},
        ],
    }}]
    await add_turn(session_id, "agent", "added pasta and tomatoes", tools_called=tools)

    rebuilt = await rebuild_cart_from_history(session_id)
    spin_ids = {i["spinId"] for i in rebuilt["instamart"]}
    assert spin_ids == {"spin_001", "spin_002"}


@pytest.mark.asyncio
async def test_rebuild_cart_latest_call_wins_for_instamart():
    """
    Multiple update_cart calls — later quantity for same spinId wins.
    """
    session_id = await create_session("u1")
    await add_turn(session_id, "agent", "first", tools_called=[{
        "tool": "update_cart",
        "arguments": {"items": [{"spinId": "spin_001", "quantity": 1}]},
    }])
    await add_turn(session_id, "agent", "second", tools_called=[{
        "tool": "update_cart",
        "arguments": {"items": [{"spinId": "spin_001", "quantity": 3}]},
    }])

    rebuilt = await rebuild_cart_from_history(session_id)
    item = next(i for i in rebuilt["instamart"] if i["spinId"] == "spin_001")
    assert item["quantity"] == 3


@pytest.mark.asyncio
async def test_rebuild_cart_empty_for_fresh_session():
    session_id = await create_session("u1")
    rebuilt = await rebuild_cart_from_history(session_id)
    assert rebuilt["food"] == []
    assert rebuilt["instamart"] == []


# ── LLM context builder ───────────────────────────────────────────────────────

def test_build_llm_context_maps_agent_to_model():
    turns = [
        ConversationTurn(session_id=uuid.uuid4(), turn_number=1,
                         role="user", content="hi"),
        ConversationTurn(session_id=uuid.uuid4(), turn_number=2,
                         role="agent", content="hello"),
    ]
    ctx = build_llm_context(turns)
    assert ctx[0]["role"] == "user"
    assert ctx[1]["role"] == "model"


def test_build_llm_context_preserves_content():
    turns = [
        ConversationTurn(session_id=uuid.uuid4(), turn_number=1,
                         role="user", content="order biryani"),
    ]
    ctx = build_llm_context(turns)
    assert ctx[0]["parts"][0]["text"] == "order biryani"


def test_build_llm_context_empty_turns():
    assert build_llm_context([]) == []
