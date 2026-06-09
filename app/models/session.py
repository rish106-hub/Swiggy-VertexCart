from __future__ import annotations
"""
Session and conversation turn models.
PRD ref: Section 8.3 (Module 3 — Multi-Turn Session Manager, Database Schema)
"""

import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.models.intent import IntentResult, Vertical


class ConversationTurn(BaseModel):
    """One message in a session — either from the user or the agent."""

    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    session_id: uuid.UUID
    turn_number: int
    role: str  # "user" | "agent"
    content: str
    intent: IntentResult | None = None
    tools_called: list[dict] | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class Session(BaseModel):
    """
    Runtime session object. Tracks OAuth token and which verticals are active.
    Cart state is NOT stored here — always read from Swiggy servers via get_*_cart.
    PRD ref: Section 8.3 (sessions table)
    """

    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    user_id: str
    swiggy_access_token: str | None = None
    token_expires_at: datetime | None = None
    active_verticals: list[Vertical] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_active_at: datetime = Field(default_factory=datetime.utcnow)


class TurnRequest(BaseModel):
    text: str = Field(min_length=1, max_length=2000)


class TurnResponse(BaseModel):
    """Agent response returned to the frontend after processing one turn."""

    agent_response: str
    verticals_active: list[Vertical]
    cart_summary: dict          # Live data from Swiggy get_*_cart calls
    requires_confirmation: bool = False
    requires_clarification: bool = False
    clarification_prompt: str | None = None
