"""
Intent parser — classifies raw user text into a structured IntentResult.
Model: Gemini 2.5 Flash (google-generativeai SDK).
PRD ref: Section 8.3 (Module 1 — Intent Parser)

Stub: filled in Sprint 2.
"""

from app.models.intent import IntentResult


async def parse(text: str) -> IntentResult:
    """
    Parse raw user text into a structured IntentResult.

    Calls Gemini 2.5 Flash with a structured JSON prompt.
    Falls back to a safe unknown-intent result on parse failure.
    """
    raise NotImplementedError("Intent parser implemented in Sprint 2")
