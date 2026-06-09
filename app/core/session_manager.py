from __future__ import annotations

"""
Multi-turn session manager.
PRD ref: Section 8.3 (Module 3), Section 7.4 (Multi-Turn Cart State Management)

Responsibilities:
  1. Create and retrieve sessions (DB-backed, in-memory fallback in MOCK_MODE)
  2. Persist conversation turns (user + agent) with intent + tool call metadata
  3. Enforce turn boundary pattern — get_*_cart BEFORE any cart-touching turn
  4. Detect and surface restaurant-switch warnings (Food cart flush risk)
  5. Detect and surface address-switch warnings (Instamart clear_cart required)
  6. Handle CART_EXPIRED — rebuild from history, confirm with user before re-adding
  7. Track which verticals are active in each session

In MOCK_MODE: DB calls are skipped; an in-memory store is used instead.
This lets the full conversation loop work end-to-end without a live PostgreSQL instance.
"""

import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from app.config import settings
from app.core.mcp_client import mcp_client
from app.models.intent import IntentResult, Vertical
from app.models.session import ConversationTurn, Session

logger = logging.getLogger(__name__)

# ── In-memory store (MOCK_MODE + tests) ──────────────────────────────────────
# Keyed by session UUID string. Replaced by DB reads/writes in production.

_mock_sessions: dict[str, Session] = {}
_mock_turns: dict[str, list[ConversationTurn]] = {}  # session_id → turns list


# ── Session lifecycle ─────────────────────────────────────────────────────────

async def create_session(user_id: str) -> uuid.UUID:
    """
    Create a new session and persist it.

    In MOCK_MODE: stored in _mock_sessions.
    In production: inserts into sessions table.

    PRD ref: Section 8.3 (sessions table), FastAPI POST /api/v1/session
    """
    session = Session(user_id=user_id)

    if settings.mock_mode:
        _mock_sessions[str(session.id)] = session
        _mock_turns[str(session.id)] = []
        logger.warning("[MOCK] Session created in memory: %s", session.id)
        return session.id

    from app.db.connection import get_connection
    async with get_connection() as conn:
        await conn.execute(
            """
            INSERT INTO sessions (id, user_id, created_at, last_active_at)
            VALUES ($1, $2, $3, $4)
            """,
            session.id,
            session.user_id,
            session.created_at,
            session.last_active_at,
        )

    logger.info("Session created: %s for user %s", session.id, user_id)
    return session.id


async def get_session(session_id: uuid.UUID) -> Session:
    """
    Retrieve a session by ID. Raises ValueError if not found.
    PRD ref: Section 8.3 (sessions table)
    """
    if settings.mock_mode:
        session = _mock_sessions.get(str(session_id))
        if not session:
            raise ValueError(f"Session not found: {session_id}")
        return session

    from app.db.connection import get_connection
    async with get_connection() as conn:
        row = await conn.fetchrow(
            "SELECT * FROM sessions WHERE id = $1", session_id
        )

    if not row:
        raise ValueError(f"Session not found: {session_id}")

    return Session(
        id=row["id"],
        user_id=row["user_id"],
        swiggy_access_token=row["swiggy_access_token"],
        token_expires_at=row["token_expires_at"],
        created_at=row["created_at"],
        last_active_at=row["last_active_at"],
    )


async def store_token(
    session_id: uuid.UUID,
    token: str,
    expires_at: datetime,
) -> None:
    """
    Persist OAuth token + expiry into the sessions row.
    Called from auth callback after successful token exchange.
    PRD ref: Section 8.3 (Module 2 — token storage)
    """
    if settings.mock_mode:
        session = _mock_sessions.get(str(session_id))
        if session:
            session.swiggy_access_token = token
            session.token_expires_at = expires_at
        return

    from app.db.connection import get_connection
    async with get_connection() as conn:
        await conn.execute(
            """
            UPDATE sessions
            SET swiggy_access_token = $1, token_expires_at = $2
            WHERE id = $3
            """,
            token,
            expires_at,
            session_id,
        )


async def touch_session(session_id: uuid.UUID) -> None:
    """Update last_active_at. Called on every turn."""
    now = datetime.now(tz=timezone.utc)

    if settings.mock_mode:
        session = _mock_sessions.get(str(session_id))
        if session:
            session.last_active_at = now
        return

    from app.db.connection import get_connection
    async with get_connection() as conn:
        await conn.execute(
            "UPDATE sessions SET last_active_at = $1 WHERE id = $2",
            now,
            session_id,
        )


# ── Conversation turns ────────────────────────────────────────────────────────

async def add_turn(
    session_id: uuid.UUID,
    role: str,
    content: str,
    intent: IntentResult | None = None,
    tools_called: list[dict] | None = None,
) -> uuid.UUID:
    """
    Persist one conversation turn (user or agent).

    intent and tools_called stored as JSONB in production.
    PRD ref: Section 8.3 (conversation_turns table)
    """
    existing = await get_conversation_history(session_id, limit=1)
    turn_number = (existing[0].turn_number + 1) if existing else 1

    turn = ConversationTurn(
        session_id=session_id,
        turn_number=turn_number,
        role=role,
        content=content,
        intent=intent,
        tools_called=tools_called,
    )

    if settings.mock_mode:
        key = str(session_id)
        if key not in _mock_turns:
            _mock_turns[key] = []
        _mock_turns[key].append(turn)
        await touch_session(session_id)
        return turn.id

    from app.db.connection import get_connection
    intent_json = intent.model_dump() if intent else None
    async with get_connection() as conn:
        await conn.execute(
            """
            INSERT INTO conversation_turns
              (id, session_id, turn_number, role, content, intent, tools_called, created_at)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            """,
            turn.id,
            session_id,
            turn_number,
            role,
            content,
            intent_json,
            tools_called,
            turn.created_at,
        )

    await touch_session(session_id)
    return turn.id


async def get_conversation_history(
    session_id: uuid.UUID,
    limit: int = 10,
) -> list[ConversationTurn]:
    """
    Return the last `limit` turns ordered oldest-first (for LLM context window).
    PRD ref: Section 8.3 (session_manager — get_conversation_history)
    """
    if settings.mock_mode:
        turns = _mock_turns.get(str(session_id), [])
        return turns[-limit:]

    from app.db.connection import get_connection
    async with get_connection() as conn:
        rows = await conn.fetch(
            """
            SELECT * FROM conversation_turns
            WHERE session_id = $1
            ORDER BY created_at DESC
            LIMIT $2
            """,
            session_id,
            limit,
        )

    # Reverse so oldest turn is first (chronological order for LLM)
    return [
        ConversationTurn(
            id=r["id"],
            session_id=r["session_id"],
            turn_number=r["turn_number"],
            role=r["role"],
            content=r["content"],
            intent=r["intent"],
            tools_called=r["tools_called"],
            created_at=r["created_at"],
        )
        for r in reversed(rows)
    ]


# ── Vertical tracking ─────────────────────────────────────────────────────────

async def get_active_verticals(session_id: uuid.UUID) -> list[Vertical]:
    """
    Derive active verticals from conversation history (intent fields on user turns).
    PRD ref: Section 8.3 (session_manager — vertical tracking)
    """
    turns = await get_conversation_history(session_id, limit=50)
    verticals: set[Vertical] = set()

    for turn in turns:
        if turn.role == "user" and turn.intent:
            for entity in turn.intent.entities:
                verticals.add(entity.vertical)

    return list(verticals)


# ── Cart state helpers (turn boundary pattern) ────────────────────────────────

async def get_live_cart_state(
    session_id: uuid.UUID,
    token: str,
) -> dict[str, Any]:
    """
    Read live cart state from Swiggy servers for all active verticals.

    NEVER returns cached data — always calls get_*_cart tools.
    Called at the start of any turn that might touch a cart.
    PRD ref: Section 7.4 (turn boundary pattern — rule 1)
    """
    active = await get_active_verticals(session_id)
    state: dict[str, Any] = {}

    if Vertical.FOOD in active:
        try:
            state["food"] = await mcp_client.get_food_cart(token=token)
        except Exception as exc:
            logger.warning("get_food_cart failed for session %s: %s", session_id, exc)
            state["food"] = {"error": str(exc)}

    if Vertical.INSTAMART in active:
        try:
            state["instamart"] = await mcp_client.get_cart(token=token)
        except Exception as exc:
            logger.warning("get_cart (IM) failed for session %s: %s", session_id, exc)
            state["instamart"] = {"error": str(exc)}

    return state


async def should_warn_restaurant_switch(
    session_id: uuid.UUID,
    new_restaurant_id: str,
    token: str,
) -> tuple[bool, dict]:
    """
    Check if switching to new_restaurant_id would flush the current Food cart.

    Returns (should_warn, current_cart_snapshot).
    should_warn=True means agent must surface warning before calling update_food_cart.

    PRD ref: Section 7.4 (Turn 3 example), Section 7.6 (Edge Case 1)
    """
    try:
        cart = await mcp_client.get_food_cart(token=token)
    except Exception:
        # No cart or error reading — no risk of flush
        return False, {}

    current_restaurant = cart.get("restaurantId", "")
    cart_has_items = bool(cart.get("items"))

    if cart_has_items and current_restaurant and current_restaurant != new_restaurant_id:
        return True, cart

    return False, cart


async def should_warn_address_switch(
    session_id: uuid.UUID,
    new_address_id: str,
    token: str,
) -> tuple[bool, dict]:
    """
    Check if changing Instamart delivery address would require a cart clear.

    Returns (should_warn, current_cart_snapshot).
    PRD ref: Section 2.3 (Instamart cart binding), Section 7.4 (address switch)
    """
    try:
        cart = await mcp_client.get_cart(token=token)
    except Exception:
        return False, {}

    current_address = cart.get("deliveryAddress", {}).get("id", "")
    cart_has_items = bool(cart.get("items"))

    if cart_has_items and current_address and current_address != new_address_id:
        return True, cart

    return False, cart


async def is_cart_expired(cart_state: dict) -> bool:
    """
    Detect CART_EXPIRED state from a get_*_cart response.
    PRD ref: Section 7.6 (Edge Case 8 — cart expired)
    """
    status = cart_state.get("status", "").upper()
    return status == "CART_EXPIRED"


async def rebuild_cart_from_history(session_id: uuid.UUID) -> dict[str, list[dict]]:
    """
    Reconstruct cart contents from conversation history when Swiggy returns CART_EXPIRED.

    Returns {vertical: [items]} — caller must confirm with user before re-adding.
    PRD ref: Section 7.6 (Edge Case 8)
    """
    turns = await get_conversation_history(session_id, limit=50)
    items_by_vertical: dict[str, list[dict]] = {
        "food": [],
        "instamart": [],
    }

    for turn in turns:
        if turn.role != "agent" or not turn.tools_called:
            continue
        for tool_call in turn.tools_called:
            tool_name = tool_call.get("tool", "")
            args = tool_call.get("arguments", {})

            if tool_name == "update_food_cart":
                items_by_vertical["food"] = args.get("items", [])
            elif tool_name == "update_cart":
                # Merge items — later calls override earlier for same spinId
                existing = {i["spinId"]: i for i in items_by_vertical["instamart"]}
                for item in args.get("items", []):
                    existing[item["spinId"]] = item
                items_by_vertical["instamart"] = list(existing.values())

    return items_by_vertical


# ── Context window builder ────────────────────────────────────────────────────

def build_llm_context(turns: list[ConversationTurn]) -> list[dict[str, str]]:
    """
    Convert conversation turns into the message format expected by Gemini.
    Maps role "agent" → "model" (Gemini's expected role name).
    PRD ref: Section 8.3 (Module 3 — get_conversation_history for LLM context)
    """
    return [
        {
            "role": "user" if t.role == "user" else "model",
            "parts": [{"text": t.content}],
        }
        for t in turns
    ]
