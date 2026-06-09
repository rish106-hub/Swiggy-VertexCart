from __future__ import annotations

"""
POST /api/v1/session/{session_id}/confirm — place one vertical's order.
PRD ref: Section 8.3 (FastAPI Endpoints), Section 7.1 (Pre-order Confirmation)

One call per vertical. Never batch. Non-idempotent placement goes through
order_orchestrator ONLY — never called directly here.

Frontend calls this once per vertical, sequentially:
  POST /confirm  {vertical: "instamart"}  → im order placed
  POST /confirm  {vertical: "food"}       → food order placed
  POST /confirm  {vertical: "dineout"}    → reservation confirmed
"""

import uuid
import logging

from fastapi import APIRouter, HTTPException

from app.core import order_orchestrator
from app.core.session_manager import get_session
from app.models.intent import Vertical
from app.models.order import ConfirmRequest, ConfirmResponse, OrderPlacementError

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/session/{session_id}/confirm", response_model=ConfirmResponse)
async def confirm_order(session_id: uuid.UUID, body: ConfirmRequest) -> ConfirmResponse:
    """
    Place one vertical's order. Caller must confirm each vertical separately.

    Routing:
      food      → order_orchestrator.place_food_order()
      instamart → order_orchestrator.checkout_instamart()
      dineout   → order_orchestrator.book_table_dineout()

    All three are NON-IDEMPOTENT — this route NEVER calls mcp_client directly.
    PRD ref: Section 7.1 (sequential per-vertical confirmation)
    """
    try:
        session = await get_session(session_id)
    except ValueError:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")

    token = session.swiggy_access_token or ""

    try:
        if body.vertical == Vertical.FOOD:
            return await order_orchestrator.place_food_order(session_id, token=token)

        if body.vertical == Vertical.INSTAMART:
            return await order_orchestrator.checkout_instamart(session_id, token=token)

        if body.vertical == Vertical.DINEOUT:
            # Dineout booking requires slot details from session context.
            # In the full flow these come from a prior dineout discovery turn.
            # For now surface a clear error — full slot binding wired in Sprint 6+ refinement.
            raise HTTPException(
                status_code=400,
                detail=(
                    "Dineout confirmation requires slot selection first. "
                    "Complete a Dineout discovery turn before confirming."
                ),
            )

        raise HTTPException(status_code=400, detail=f"Unknown vertical: {body.vertical}")

    except OrderPlacementError as exc:
        logger.error(
            "Order placement failed: session=%s vertical=%s error=%s",
            session_id, body.vertical, exc,
        )
        raise HTTPException(status_code=502, detail=str(exc))
