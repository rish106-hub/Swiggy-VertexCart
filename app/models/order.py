from __future__ import annotations
"""
Order reference models.
PRD ref: Section 8.3 (order_references table, Module 5 — Order Placement Orchestrator)

Note: We store only Swiggy-issued order IDs, not order contents.
Swiggy is the authoritative source for order data.
"""

import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.models.intent import Vertical


class OrderReference(BaseModel):
    """Lightweight record of a placed order. Contents live on Swiggy's servers."""

    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    session_id: uuid.UUID
    vertical: Vertical
    swiggy_order_id: str
    placed_at: datetime = Field(default_factory=datetime.utcnow)
    status: str = "placed"


class ConfirmRequest(BaseModel):
    """User confirms one vertical's order. One call per vertical — never batch."""

    vertical: Vertical


class ConfirmResponse(BaseModel):
    order_id: str
    vertical: Vertical
    eta: str | None = None
    status: str = "placed"


class OrderPlacementError(Exception):
    """
    Raised when all retries on a non-idempotent order call are exhausted.
    PRD ref: Section 8.3 (Module 5 — check-then-retry pattern)
    """

    def __init__(self, vertical: str, message: str) -> None:
        self.vertical = vertical
        super().__init__(f"[{vertical}] Order placement failed: {message}")
