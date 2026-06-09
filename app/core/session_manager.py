from __future__ import annotations
"""
Multi-turn session manager.
PRD ref: Section 8.3 (Module 3), Section 7.4 (Multi-Turn Cart State Management)

Responsibilities:
- Persist conversation history to DB
- Enforce turn boundary pattern (get_*_cart before cart-touching turns)
- Warn on restaurant/address switches before flushing carts
- Handle cart expiry with user-confirmed rebuild

Stub: filled in Sprint 6.
"""

import uuid

from app.models.intent import IntentResult, Vertical
from app.models.session import Session, ConversationTurn


async def create_session(user_id: str) -> uuid.UUID:
    """Create a new session row in DB and return its UUID."""
    raise NotImplementedError("Session manager implemented in Sprint 6")


async def get_session(session_id: uuid.UUID) -> Session:
    raise NotImplementedError


async def add_turn(
    session_id: uuid.UUID,
    role: str,
    content: str,
    intent: IntentResult | None = None,
    tools_called: list[dict] | None = None,
) -> uuid.UUID:
    """Persist one conversation turn and return its UUID."""
    raise NotImplementedError


async def get_conversation_history(
    session_id: uuid.UUID, limit: int = 10
) -> list[ConversationTurn]:
    """Return last `limit` turns ordered by recency, for LLM context window."""
    raise NotImplementedError


async def get_active_verticals(session_id: uuid.UUID) -> list[Vertical]:
    raise NotImplementedError


async def should_warn_restaurant_switch(
    session_id: uuid.UUID, new_restaurant_id: str
) -> bool:
    """
    Read live Food cart from Swiggy. Return True if cart exists with a different restaurant.
    PRD ref: Section 7.4 (Turn 3 example — restaurant switch warning)
    """
    raise NotImplementedError


async def rebuild_cart_from_history(session_id: uuid.UUID) -> dict:
    """
    Reconstruct what was in the cart from conversation history.
    Used when Swiggy returns CART_EXPIRED.
    Caller must confirm with user before re-adding items.
    """
    raise NotImplementedError
