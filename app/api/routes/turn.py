"""POST /api/v1/session/{session_id}/turn — process one conversation turn."""

import uuid

from fastapi import APIRouter

from app.models.session import TurnRequest, TurnResponse

router = APIRouter()


@router.post("/session/{session_id}/turn", response_model=TurnResponse)
async def process_turn(session_id: uuid.UUID, body: TurnRequest) -> TurnResponse:
    """
    Core conversation loop. Steps per turn:
      1. Parse intent from user text
      2. If clarification needed → return clarifying question immediately
      3. Store user turn in conversation history
      4. Apply turn boundary pattern: read live carts for active verticals
      5. Detect restaurant/address switches → return warning if needed
      6. Call discovery + cart tools based on intent
      7. Store agent turn in conversation history
      8. Return agent response with cart summary

    PRD ref: Section 8.3 (Module 3, FastAPI Endpoints), Section 7.4 (Turn boundary pattern)

    Stub: orchestration logic wired in Sprint 8.
    """
    raise NotImplementedError("Turn route wired in Sprint 8")
