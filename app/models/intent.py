from __future__ import annotations
"""
Intent classification models.
PRD ref: Section 8.3 (Module 1 — Intent Parser), Section 7.5 (Intent Classification Matrix)
"""

from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field


class EntityType(str, Enum):
    INGREDIENT = "ingredient"       # Instamart: raw items for cooking
    READY_TO_EAT = "ready_to_eat"   # Food: restaurant-delivered dishes
    RESERVATION = "reservation"     # Dineout: table booking


class Vertical(str, Enum):
    INSTAMART = "instamart"
    FOOD = "food"
    DINEOUT = "dineout"


class IntentEntity(BaseModel):
    """A single extracted entity from user text, mapped to a Swiggy vertical."""

    text: str = Field(description="Original phrase from user input")
    type: EntityType
    vertical: Vertical
    confidence: float = Field(ge=0.0, le=1.0)


class Occasion(str, Enum):
    WEEKNIGHT_DINNER = "weeknight_dinner"
    WEEKEND_OUTING = "weekend_outing"
    QUICK_SNACK = "quick_snack"
    UNKNOWN = "unknown"


class Urgency(str, Enum):
    IMMEDIATE = "immediate"
    SCHEDULED = "scheduled"   # Not supported in v1 — agent must inform user
    UNKNOWN = "unknown"


class IntentResult(BaseModel):
    """
    Structured output from the intent parser.
    Drives which MCP tool paths the session manager activates.
    PRD ref: Section 8.3 (Module 1 output schema)
    """

    entities: list[IntentEntity] = Field(default_factory=list)
    occasion: Occasion = Occasion.UNKNOWN
    urgency: Urgency = Urgency.UNKNOWN
    dineout_signal: bool = False
    requires_clarification: bool = False
    raw_input: str = ""

    @property
    def active_verticals(self) -> list[Vertical]:
        """Deduplicated list of verticals this intent touches."""
        return list({e.vertical for e in self.entities})

    @property
    def is_multi_vertical(self) -> bool:
        return len(self.active_verticals) > 1
