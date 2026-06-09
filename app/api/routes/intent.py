"""POST /api/v1/intent — parse user text into structured intent."""

from fastapi import APIRouter
from pydantic import BaseModel

from app.core import intent_parser
from app.models.intent import IntentResult

router = APIRouter()


class IntentRequest(BaseModel):
    text: str
    user_id: str


@router.post("/intent", response_model=IntentResult)
async def classify_intent(body: IntentRequest) -> IntentResult:
    """
    Stateless intent classification. Does NOT create a session.
    Use for preview/instant feedback before a session is started.
    PRD ref: Section 8.3 (Module 1), Section 7.5 (Intent Classification Matrix)
    """
    return await intent_parser.parse(body.text)
