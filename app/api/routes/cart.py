from __future__ import annotations

"""
GET /api/v1/session/{session_id}/cart — read live cart state from Swiggy servers.
PRD ref: Section 8.3 (FastAPI Endpoints), Section 7.4 (cart state authority)

IMPORTANT: result is NEVER cached. Every call reads fresh from Swiggy.
Frontend calls this before rendering the cart preview and confirmation screens.
"""

import uuid
import logging

from fastapi import APIRouter, HTTPException

from app.core.session_manager import get_live_cart_state, get_session

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/session/{session_id}/cart")
async def get_cart(session_id: uuid.UUID) -> dict:
    """
    Returns live cart state by calling get_food_cart + get_cart (Instamart)
    and get_booking_status if Dineout active.

    Result is NEVER cached — authoritative Swiggy server state.
    PRD ref: Section 8.3, Section 9.3 (Screen 3 — CartPreview reads live)
    """
    try:
        session = await get_session(session_id)
    except ValueError:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")

    token = session.swiggy_access_token or ""
    cart_state = await get_live_cart_state(session_id, token)
    return cart_state
