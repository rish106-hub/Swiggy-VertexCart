"""POST /api/v1/session/{session_id}/confirm — place one vertical's order."""

import uuid

from fastapi import APIRouter

from app.models.order import ConfirmRequest, ConfirmResponse

router = APIRouter()


@router.post("/session/{session_id}/confirm", response_model=ConfirmResponse)
async def confirm_order(session_id: uuid.UUID, body: ConfirmRequest) -> ConfirmResponse:
    """
    Place one vertical's order. Called once per vertical — never batch.

    Routes to order_orchestrator.place_food_order / checkout_instamart / book_table_dineout.
    Non-idempotent calls are NEVER made directly from here — always via orchestrator.

    PRD ref: Section 7.1 (Pre-order Confirmation Screen), Section 8.3 (Module 5)

    Stub: wired in Sprint 8.
    """
    raise NotImplementedError("Confirm route wired in Sprint 8")
