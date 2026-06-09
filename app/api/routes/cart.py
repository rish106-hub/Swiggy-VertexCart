"""GET /api/v1/session/{session_id}/cart — read live cart state from Swiggy servers."""

import uuid

from fastapi import APIRouter

router = APIRouter()


@router.get("/session/{session_id}/cart")
async def get_cart(session_id: uuid.UUID) -> dict:
    """
    Returns live cart state by calling get_food_cart + get_cart (Instamart)
    and get_booking_status if Dineout is active.

    IMPORTANT: result is NEVER cached. Every call reads from Swiggy servers.
    PRD ref: Section 8.3 (FastAPI Endpoints), Section 7.4 (cart state authority)

    Stub: wired in Sprint 8.
    """
    raise NotImplementedError("Cart route wired in Sprint 8")
