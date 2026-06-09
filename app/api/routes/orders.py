from __future__ import annotations

"""
GET /api/v1/session/{session_id}/orders — list placed orders with live ETAs.
PRD ref: Section 8.3 (FastAPI Endpoints), Section 9.3 (Screen 5 — Order Status)

Frontend polls this every 10 seconds (Swiggy delivery-partner ETA cadence).
For each order_reference, calls the vertical's track_* tool for live ETA.
"""

import uuid
import logging

from fastapi import APIRouter, HTTPException

from app.core.mcp_client import mcp_client
from app.core.session_manager import get_session
from app.config import settings

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/session/{session_id}/orders")
async def get_orders(session_id: uuid.UUID) -> list[dict]:
    """
    Return all order_references for the session with live tracking data.
    Polls track_food_order / track_order / get_booking_status per reference.
    Frontend polls this endpoint every 10 seconds.
    PRD ref: Section 7.1 (Confirmation + Tracking), Section 9.3 (Screen 5)
    """
    try:
        session = await get_session(session_id)
    except ValueError:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")

    token = session.swiggy_access_token or ""

    # ── Fetch order references from DB ────────────────────────────────────
    order_refs = await _fetch_order_references(session_id)

    if not order_refs:
        return []

    # ── Enrich with live tracking data ────────────────────────────────────
    enriched: list[dict] = []
    for ref in order_refs:
        vertical = ref.get("vertical", "")
        order_id = ref.get("swiggy_order_id", "")
        tracking: dict = {}

        try:
            if vertical == "food":
                tracking = await mcp_client.track_food_order(order_id, token=token)
            elif vertical == "instamart":
                tracking = await mcp_client.track_order(order_id, token=token)
            elif vertical == "dineout":
                tracking = await mcp_client.get_booking_status(order_id, token=token)
        except Exception as exc:
            logger.warning(
                "Tracking failed for %s order %s: %s", vertical, order_id, exc
            )
            tracking = {"status": "unknown", "error": str(exc)}

        enriched.append({
            "order_id": order_id,
            "vertical": vertical,
            "placed_at": ref.get("placed_at"),
            "status": tracking.get("status", ref.get("status", "placed")),
            "eta": tracking.get("eta") or tracking.get("reservationTime"),
            "tracking": tracking,
        })

    return enriched


async def _fetch_order_references(session_id: uuid.UUID) -> list[dict]:
    """
    Fetch order_references rows for this session.
    In MOCK_MODE: returns empty list (orders stored in-memory via orchestrator logs).
    In production: queries order_references table.
    """
    if settings.mock_mode:
        logger.warning("[MOCK] _fetch_order_references — no DB, returning empty list")
        return []

    from app.db.connection import get_connection
    async with get_connection() as conn:
        rows = await conn.fetch(
            """
            SELECT swiggy_order_id, vertical, placed_at, status
            FROM order_references
            WHERE session_id = $1
            ORDER BY placed_at ASC
            """,
            session_id,
        )
    return [dict(r) for r in rows]
