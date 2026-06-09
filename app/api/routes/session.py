"""POST /api/v1/session — create a new conversation session."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.core import session_manager

router = APIRouter()


class SessionRequest(BaseModel):
    user_id: str


class SessionResponse(BaseModel):
    session_id: str


@router.post("/session", response_model=SessionResponse)
async def create_session(body: SessionRequest) -> SessionResponse:
    """
    Create a new session. Returns session_id used in all subsequent calls.
    PRD ref: Section 8.3 (FastAPI Endpoints)
    """
    session_id = await session_manager.create_session(body.user_id)
    return SessionResponse(session_id=str(session_id))


@router.get("/session/{session_id}/history")
async def get_history(session_id: uuid.UUID, limit: int = 10) -> list[dict]:
    """
    Return last `limit` conversation turns for a session.
    Used by frontend agent reasoning panel and for debugging.
    PRD ref: Section 8.3 (FastAPI Endpoints — Phase 5 addition)
    """
    try:
        await session_manager.get_session(session_id)
    except ValueError:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")

    turns = await session_manager.get_conversation_history(session_id, limit=limit)
    return [
        {
            "turn_number": t.turn_number,
            "role": t.role,
            "content": t.content,
            "created_at": t.created_at.isoformat(),
        }
        for t in turns
    ]
