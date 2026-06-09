from __future__ import annotations

"""
Unit tests for intent_parser.
All tests run against the mock layer (MOCK_MODE=true) or direct JSON parsing logic.
PRD ref: Section 8.3 (Module 1 — Intent Parser), cli.md Prompt 1.2 test cases
"""

import pytest

from app.models.intent import EntityType, Occasion, Urgency, Vertical


# ── Helpers ───────────────────────────────────────────────────────────────────

def _force_mock_mode(monkeypatch):
    """Ensure tests always run in mock mode — no live Gemini calls."""
    monkeypatch.setattr("app.core.intent_parser.settings.mock_mode", True)


# ── Test: _parse_llm_json (pure function — no I/O) ────────────────────────────

from app.core.intent_parser import _parse_llm_json, _build_fallback


class TestParseLlmJson:
    """Tests for the JSON parsing layer — not the LLM itself."""

    def test_multi_vertical_pasta_and_tiramisu(self):
        """Pasta → Instamart, tiramisu → Food. PRD Section 7.5."""
        raw = """
        {
          "entities": [
            {"text": "pasta ingredients", "type": "ingredient", "vertical": "instamart", "confidence": 0.92},
            {"text": "tiramisu", "type": "ready_to_eat", "vertical": "food", "confidence": 0.88}
          ],
          "occasion": "weeknight_dinner",
          "urgency": "immediate",
          "dineout_signal": false,
          "requires_clarification": false
        }
        """
        result = _parse_llm_json(raw, "pasta tonight and order tiramisu")
        assert len(result.entities) == 2
        assert result.entities[0].vertical == Vertical.INSTAMART
        assert result.entities[1].vertical == Vertical.FOOD
        assert result.is_multi_vertical is True
        assert result.occasion == Occasion.WEEKNIGHT_DINNER
        assert result.requires_clarification is False

    def test_single_food_intent(self):
        """Single food order → Food vertical only."""
        raw = """
        {
          "entities": [
            {"text": "chicken biryani", "type": "ready_to_eat", "vertical": "food", "confidence": 0.95}
          ],
          "occasion": "quick_snack",
          "urgency": "immediate",
          "dineout_signal": false,
          "requires_clarification": false
        }
        """
        result = _parse_llm_json(raw, "order chicken biryani")
        assert len(result.entities) == 1
        assert result.entities[0].vertical == Vertical.FOOD
        assert result.entities[0].type == EntityType.READY_TO_EAT
        assert result.is_multi_vertical is False

    def test_single_instamart_intent(self):
        """Grocery items → Instamart only."""
        raw = """
        {
          "entities": [
            {"text": "tomatoes and onions", "type": "ingredient", "vertical": "instamart", "confidence": 0.97}
          ],
          "occasion": "weeknight_dinner",
          "urgency": "immediate",
          "dineout_signal": false,
          "requires_clarification": false
        }
        """
        result = _parse_llm_json(raw, "get me tomatoes and onions")
        assert result.entities[0].vertical == Vertical.INSTAMART
        assert result.entities[0].type == EntityType.INGREDIENT
        assert result.dineout_signal is False

    def test_dineout_reservation_intent(self):
        """Table booking → Dineout. dineout_signal must be True."""
        raw = """
        {
          "entities": [
            {"text": "book a table for Friday dinner", "type": "reservation", "vertical": "dineout", "confidence": 0.94}
          ],
          "occasion": "weekend_outing",
          "urgency": "scheduled",
          "dineout_signal": true,
          "requires_clarification": false
        }
        """
        result = _parse_llm_json(raw, "book a table for Friday dinner")
        assert result.entities[0].vertical == Vertical.DINEOUT
        assert result.entities[0].type == EntityType.RESERVATION
        assert result.dineout_signal is True
        assert result.urgency == Urgency.SCHEDULED

    def test_ambiguous_intent_requires_clarification(self):
        """Vague intent should flag requires_clarification=True."""
        raw = """
        {
          "entities": [],
          "occasion": "unknown",
          "urgency": "unknown",
          "dineout_signal": false,
          "requires_clarification": true
        }
        """
        result = _parse_llm_json(raw, "something nice tonight")
        assert result.requires_clarification is True
        assert result.occasion == Occasion.UNKNOWN

    def test_reorder_intent_instamart_no_clarification(self):
        """'Reorder usual groceries' → Instamart, no clarification needed."""
        raw = """
        {
          "entities": [
            {"text": "usual groceries", "type": "ingredient", "vertical": "instamart", "confidence": 0.85}
          ],
          "occasion": "unknown",
          "urgency": "immediate",
          "dineout_signal": false,
          "requires_clarification": false
        }
        """
        result = _parse_llm_json(raw, "reorder my usual groceries")
        assert result.entities[0].vertical == Vertical.INSTAMART
        assert result.requires_clarification is False


class TestParseLlmJsonEdgeCases:
    """Resilience tests — bad LLM output should never crash the parser."""

    def test_invalid_json_returns_fallback(self):
        result = _parse_llm_json("not json at all %%%", "some text")
        assert result.requires_clarification is True
        assert result.entities == []

    def test_json_with_markdown_fences_is_stripped(self):
        raw = '```json\n{"entities":[],"occasion":"unknown","urgency":"unknown","dineout_signal":false,"requires_clarification":true}\n```'
        result = _parse_llm_json(raw, "test")
        assert result.requires_clarification is True

    def test_invalid_enum_value_returns_fallback(self):
        raw = '{"entities":[{"text":"pasta","type":"INVALID","vertical":"food","confidence":0.9}],"occasion":"unknown","urgency":"unknown","dineout_signal":false,"requires_clarification":false}'
        result = _parse_llm_json(raw, "pasta")
        # Falls back because EntityType("INVALID") raises ValueError
        assert result.requires_clarification is True


class TestBuildFallback:
    def test_fallback_preserves_raw_input(self):
        result = _build_fallback("some user text")
        assert result.raw_input == "some user text"
        assert result.requires_clarification is True
        assert result.entities == []
        assert result.occasion == Occasion.UNKNOWN


# ── Test: async parse() in mock mode ─────────────────────────────────────────

@pytest.mark.asyncio
async def test_parse_mock_mode_returns_result(monkeypatch):
    """parse() in MOCK_MODE must return a valid IntentResult without calling Gemini."""
    monkeypatch.setattr("app.core.intent_parser.settings.mock_mode", True)

    from app.core.intent_parser import parse
    result = await parse("pasta tonight and tiramisu dessert")

    assert result is not None
    assert len(result.entities) > 0
    assert result.raw_input == "pasta tonight and tiramisu dessert"


@pytest.mark.asyncio
async def test_parse_no_api_key_returns_fallback(monkeypatch):
    """parse() with MOCK_MODE=false and no API key must return fallback, not crash."""
    monkeypatch.setattr("app.core.intent_parser.settings.mock_mode", False)
    monkeypatch.setattr("app.core.intent_parser.settings.gemini_api_key", "")

    from app.core.intent_parser import parse
    result = await parse("order biryani")

    assert result.requires_clarification is True
    assert result.raw_input == "order biryani"
