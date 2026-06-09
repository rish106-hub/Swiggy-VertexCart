"""POST /api/v1/session — create a new conversation session."""

from fastapi import APIRouter
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
