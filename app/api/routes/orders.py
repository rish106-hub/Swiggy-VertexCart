"""GET /api/v1/session/{session_id}/orders — list placed orders with live ETAs."""

import uuid

from fastapi import APIRouter

router = APIRouter()


@router.get("/session/{session_id}/orders")
async def get_orders(session_id: uuid.UUID) -> list[dict]:
    """
    Return all order_references for the session from DB.
    For each, call the vertical's track_* tool for live ETA.
    Frontend polls this endpoint every 10 seconds.
    PRD ref: Section 8.3 (FastAPI Endpoints), Section 9.3 (Screen 5)

    Stub: wired in Sprint 8.
    """
    raise NotImplementedError("Orders route wired in Sprint 8")
