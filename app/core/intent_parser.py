from __future__ import annotations

"""
Intent parser — classifies raw user text into a structured IntentResult.
Model: Gemini 2.5 Flash (google-generativeai SDK).
PRD ref: Section 8.3 (Module 1 — Intent Parser), Section 7.5 (Intent Classification Matrix)

In MOCK_MODE, returns a realistic hardcoded result without calling the API.
On LLM parse failure, returns a safe fallback IntentResult with unknown fields.
"""

import json
import logging
from typing import Any

import google.generativeai as genai

from app.config import settings
from app.models.intent import (
    EntityType,
    IntentEntity,
    IntentResult,
    Occasion,
    Urgency,
    Vertical,
)

logger = logging.getLogger(__name__)

# ── Prompt ────────────────────────────────────────────────────────────────────

_SYSTEM_PROMPT = """You are an intent classification engine for a conversational commerce app built on Swiggy.

Swiggy has three verticals:
- food: restaurant-delivered ready-to-eat dishes (biryani, pizza, tiramisu, coffee, etc.)
- instamart: grocery/ingredient delivery (pasta, tomatoes, milk, eggs, wine, etc.)
- dineout: table reservations at restaurants ("book a table", "dinner out", "Friday night reservation")

Your job: extract entities from user text and classify each entity.

Entity types:
- ingredient: raw items for cooking → vertical: instamart
- ready_to_eat: restaurant-delivered food → vertical: food
- reservation: table booking intent → vertical: dineout

Occasions: weeknight_dinner, weekend_outing, quick_snack, unknown
Urgency: immediate, scheduled, unknown

Return ONLY valid JSON matching this exact schema — no markdown, no explanation:

{
  "entities": [
    {
      "text": "<phrase from user input>",
      "type": "ingredient" | "ready_to_eat" | "reservation",
      "vertical": "instamart" | "food" | "dineout",
      "confidence": <float 0.0-1.0>
    }
  ],
  "occasion": "weeknight_dinner" | "weekend_outing" | "quick_snack" | "unknown",
  "urgency": "immediate" | "scheduled" | "unknown",
  "dineout_signal": <true | false>,
  "requires_clarification": <true | false>
}

Rules:
- requires_clarification=true when intent is genuinely ambiguous (e.g. "something nice tonight" could be food delivery OR going out)
- dineout_signal=true whenever any entity maps to dineout
- "reorder my usual groceries" → instamart, ingredient, requires_clarification=false
- "the usual" without context → requires_clarification=true
- scheduled delivery phrases ("at 10pm", "for tomorrow") → urgency=scheduled
- confidence reflects how certain you are about the vertical assignment
"""

# ── Mock data ─────────────────────────────────────────────────────────────────

_MOCK_RESULT = IntentResult(
    entities=[
        IntentEntity(
            text="pasta ingredients",
            type=EntityType.INGREDIENT,
            vertical=Vertical.INSTAMART,
            confidence=0.93,
        ),
        IntentEntity(
            text="tiramisu",
            type=EntityType.READY_TO_EAT,
            vertical=Vertical.FOOD,
            confidence=0.91,
        ),
    ],
    occasion=Occasion.WEEKNIGHT_DINNER,
    urgency=Urgency.IMMEDIATE,
    dineout_signal=False,
    requires_clarification=False,
    raw_input="pasta ingredients tonight and order tiramisu for dessert",
)

# ── Parser ────────────────────────────────────────────────────────────────────

def _build_fallback(raw_input: str) -> IntentResult:
    """Return a safe unknown-intent result. Used when LLM output cannot be parsed."""
    return IntentResult(
        entities=[],
        occasion=Occasion.UNKNOWN,
        urgency=Urgency.UNKNOWN,
        dineout_signal=False,
        requires_clarification=True,
        raw_input=raw_input,
    )


def _parse_llm_json(raw_output: str, user_text: str) -> IntentResult:
    """
    Parse Gemini JSON output into IntentResult.
    Strips markdown fences if present. Falls back to unknown result on any parse error.
    """
    # Strip ```json ... ``` fences if the model disobeys the prompt
    cleaned = raw_output.strip()
    if cleaned.startswith("```"):
        lines = cleaned.splitlines()
        cleaned = "\n".join(lines[1:-1]) if len(lines) > 2 else cleaned

    try:
        data: dict[str, Any] = json.loads(cleaned)
    except json.JSONDecodeError:
        logger.warning("Intent parser: JSON decode failed. raw=%s", raw_output[:200])
        return _build_fallback(user_text)

    try:
        entities = [
            IntentEntity(
                text=e["text"],
                type=EntityType(e["type"]),
                vertical=Vertical(e["vertical"]),
                confidence=float(e.get("confidence", 0.5)),
            )
            for e in data.get("entities", [])
        ]
        return IntentResult(
            entities=entities,
            occasion=Occasion(data.get("occasion", "unknown")),
            urgency=Urgency(data.get("urgency", "unknown")),
            dineout_signal=bool(data.get("dineout_signal", False)),
            requires_clarification=bool(data.get("requires_clarification", False)),
            raw_input=user_text,
        )
    except (KeyError, ValueError) as exc:
        logger.warning("Intent parser: model validation failed. error=%s", exc)
        return _build_fallback(user_text)


async def parse(text: str) -> IntentResult:
    """
    Parse raw user text into a structured IntentResult.

    In MOCK_MODE: returns hardcoded result without calling Gemini.
    With API key: calls Gemini 2.5 Flash with structured JSON prompt.
    On any failure: returns safe fallback (requires_clarification=True).

    PRD ref: Section 8.3 (Module 1), Section 7.5 (Intent Classification Matrix)
    """
    if settings.mock_mode:
        logger.warning("[MOCK] intent_parser.parse called — returning mock IntentResult")
        mock = _MOCK_RESULT.model_copy()
        mock.raw_input = text
        return mock

    if not settings.gemini_api_key:
        logger.error("GEMINI_API_KEY not set and MOCK_MODE=false — returning fallback")
        return _build_fallback(text)

    try:
        genai.configure(api_key=settings.gemini_api_key)
        model = genai.GenerativeModel(
            model_name="gemini-2.5-flash",
            system_instruction=_SYSTEM_PROMPT,
        )
        response = model.generate_content(
            text,
            generation_config=genai.types.GenerationConfig(
                temperature=0.1,      # Low temperature for deterministic classification
                max_output_tokens=512,
            ),
        )
        raw_output = response.text
        return _parse_llm_json(raw_output, text)

    except Exception as exc:
        logger.error("Intent parser: Gemini call failed. error=%s", exc)
        return _build_fallback(text)
