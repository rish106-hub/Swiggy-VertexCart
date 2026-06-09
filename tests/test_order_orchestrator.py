from __future__ import annotations

"""
Unit tests for order placement orchestrator.
PRD ref: Section 8.3 (Module 5 — Order Placement Orchestrator)
cli.md Prompt 1.7: 7 required test cases + additional coverage.

Uses call-count tracking and controlled side-effects to verify
check-then-retry behavior without live Swiggy credentials.
"""

import uuid
from unittest.mock import AsyncMock, patch

import pytest

from app.core.mcp_client import MCPToolError, mcp_client
from app.core.error_classifier import ErrorClassification
from app.core import order_orchestrator
from app.core.order_orchestrator import (
    _order_placed_recently,
    place_food_order,
    checkout_instamart,
    book_table_dineout,
)
from app.models.order import OrderPlacementError


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def mock_mode(monkeypatch):
    monkeypatch.setattr("app.core.order_orchestrator.settings.mock_mode", True)
    monkeypatch.setattr("app.core.mcp_client.settings.mock_mode", True)


@pytest.fixture(autouse=True)
def no_sleep(monkeypatch):
    """Disable backoff sleeps so tests run instantly."""
    monkeypatch.setattr("app.core.order_orchestrator.asyncio.sleep", AsyncMock())


def _retryable_error() -> MCPToolError:
    return MCPToolError(
        ErrorClassification(bucket="upstream_error", is_retryable=True, action="backoff_retry")
    )


def _domain_error(bucket: str = "domain_failure") -> MCPToolError:
    return MCPToolError(
        ErrorClassification(bucket=bucket, is_retryable=False, action="surface_to_user"),
        raw_message="domain failure",
    )


MOCK_FOOD_CART = {
    "restaurantId": "rest_001",
    "items": [{"itemId": "item_001", "quantity": 1}],
    "subtotal": 320,
    "status": "ACTIVE",
}

MOCK_IM_CART = {
    "items": [{"spinId": "spin_001", "quantity": 2}],
    "subtotal": 178,
    "status": "ACTIVE",
}

FOOD_ORDER = {"orderId": "food_ord_001", "status": "PLACED", "eta": "30 min", "paymentMethod": "COD"}
IM_ORDER = {"orderId": "im_ord_001", "status": "PLACED", "eta": "12 min", "paymentMethod": "COD"}
DINEOUT_BOOKING = {
    "bookingId": "dout_bk_001",
    "status": "CONFIRMED",
    "reservationTime": "2026-06-13T19:30:00",
}

SESSION_ID = uuid.uuid4()


# ── _order_placed_recently helper ─────────────────────────────────────────────

class TestOrderPlacedRecently:
    def test_returns_order_when_no_timestamp(self):
        orders = [{"orderId": "x"}]
        assert _order_placed_recently(orders) is not None

    def test_returns_none_for_empty_list(self):
        assert _order_placed_recently([]) is None

    def test_returns_order_for_recent_timestamp(self):
        from datetime import datetime, timezone
        orders = [{"orderId": "x", "placedAt": datetime.now(tz=timezone.utc).isoformat()}]
        assert _order_placed_recently(orders) is not None

    def test_returns_none_for_old_order(self):
        orders = [{"orderId": "x", "placedAt": "2020-01-01T00:00:00+00:00"}]
        assert _order_placed_recently(orders, within_seconds=60) is None


# ── Test Case 1: Happy path — food order placed successfully ──────────────────

@pytest.mark.asyncio
async def test_food_order_happy_path(monkeypatch):
    monkeypatch.setattr(mcp_client, "get_food_cart", AsyncMock(return_value=MOCK_FOOD_CART))
    monkeypatch.setattr(mcp_client, "place_food_order", AsyncMock(return_value=FOOD_ORDER))

    result = await place_food_order(SESSION_ID, token="tok")

    assert result.order_id == "food_ord_001"
    assert result.vertical.value == "food"
    assert result.status == "PLACED"


# ── Test Case 2: 5xx → order found in get_food_orders → treated as success ───

@pytest.mark.asyncio
async def test_food_order_5xx_then_found_in_get_orders(monkeypatch):
    """
    place_food_order raises 5xx. get_food_orders returns a recent order.
    Orchestrator must treat it as success without retrying placement.
    PRD ref: Section 8.3 (Module 5 — check-then-retry step c)
    """
    place_calls = 0

    async def failing_place(**kwargs):
        nonlocal place_calls
        place_calls += 1
        raise _retryable_error()

    monkeypatch.setattr(mcp_client, "get_food_cart", AsyncMock(return_value=MOCK_FOOD_CART))
    monkeypatch.setattr(mcp_client, "place_food_order", failing_place)
    monkeypatch.setattr(
        mcp_client, "get_food_orders",
        AsyncMock(return_value=[FOOD_ORDER])  # Order found!
    )

    result = await place_food_order(SESSION_ID, token="tok")

    assert result.order_id == "food_ord_001"
    assert place_calls == 1   # Did NOT retry placement after finding the order


# ── Test Case 3: 5xx → order not found → retry succeeds on 2nd attempt ───────

@pytest.mark.asyncio
async def test_food_order_5xx_retry_succeeds_second_attempt(monkeypatch):
    """
    First placement attempt raises 5xx, get_food_orders empty, second attempt succeeds.
    PRD ref: Section 8.3 (Module 5 — check-then-retry step d)
    """
    attempt_num = 0

    async def flaky_place(**kwargs):
        nonlocal attempt_num
        attempt_num += 1
        if attempt_num == 1:
            raise _retryable_error()
        return FOOD_ORDER

    monkeypatch.setattr(mcp_client, "get_food_cart", AsyncMock(return_value=MOCK_FOOD_CART))
    monkeypatch.setattr(mcp_client, "place_food_order", flaky_place)
    monkeypatch.setattr(mcp_client, "get_food_orders", AsyncMock(return_value=[]))  # Empty

    result = await place_food_order(SESSION_ID, token="tok")

    assert result.order_id == "food_ord_001"
    assert attempt_num == 2


# ── Test Case 4: All retries fail → OrderPlacementError raised ────────────────

@pytest.mark.asyncio
async def test_food_order_all_retries_exhausted(monkeypatch):
    """
    All MAX_RETRIES attempts fail. OrderPlacementError must be raised.
    report_error must be called once.
    PRD ref: Section 8.3 (Module 5 — after 3 retries)
    """
    monkeypatch.setattr(mcp_client, "get_food_cart", AsyncMock(return_value=MOCK_FOOD_CART))
    monkeypatch.setattr(mcp_client, "place_food_order", AsyncMock(side_effect=_retryable_error()))
    monkeypatch.setattr(mcp_client, "get_food_orders", AsyncMock(return_value=[]))

    report_calls = 0
    async def mock_report_error(**kwargs):
        nonlocal report_calls
        report_calls += 1
        return {"reported": True}

    monkeypatch.setattr(mcp_client, "report_error", mock_report_error)

    with pytest.raises(OrderPlacementError) as exc_info:
        await place_food_order(SESSION_ID, token="tok")

    assert "food" in exc_info.value.vertical
    assert report_calls == 1


# ── Test Case 5: ₹1000 cap exceeded → rejected before placement ───────────────

@pytest.mark.asyncio
async def test_food_order_rejected_when_cart_exceeds_cap(monkeypatch):
    """
    Cart total > ₹1000. OrderPlacementError raised BEFORE calling place_food_order.
    PRD ref: Section 2.3 (Food cart cap), Section 7.6 (Edge Case 4)
    """
    over_cap_cart = {**MOCK_FOOD_CART, "subtotal": 1050}
    monkeypatch.setattr(mcp_client, "get_food_cart", AsyncMock(return_value=over_cap_cart))
    place_mock = AsyncMock()
    monkeypatch.setattr(mcp_client, "place_food_order", place_mock)

    with pytest.raises(OrderPlacementError) as exc_info:
        await place_food_order(SESSION_ID, token="tok")

    assert "₹1000" in str(exc_info.value)
    place_mock.assert_not_called()   # placement must NOT be attempted


# ── Test Case 6: Instamart minimum not met → rejected before checkout ─────────

@pytest.mark.asyncio
async def test_instamart_order_rejected_below_minimum(monkeypatch):
    """
    Cart total < ₹99. OrderPlacementError raised BEFORE calling checkout.
    PRD ref: Section 2.3 (Instamart minimum), Section 7.6 (Edge Case 5)
    """
    under_min_cart = {**MOCK_IM_CART, "subtotal": 50}
    monkeypatch.setattr(mcp_client, "get_cart", AsyncMock(return_value=under_min_cart))
    checkout_mock = AsyncMock()
    monkeypatch.setattr(mcp_client, "checkout", checkout_mock)

    with pytest.raises(OrderPlacementError) as exc_info:
        await checkout_instamart(SESSION_ID, token="tok")

    assert "₹99" in str(exc_info.value)
    checkout_mock.assert_not_called()


# ── Test Case 7: Dineout paid slot → rejected before book_table ───────────────

@pytest.mark.asyncio
async def test_dineout_paid_slot_rejected(monkeypatch):
    """
    slot_is_free=False or bookingPrice > 0. Rejected BEFORE calling book_table.
    PRD ref: Section 2.3 (Dineout — free reservations only), Section 7.6 (Edge Case — paid slot)
    """
    book_mock = AsyncMock()
    monkeypatch.setattr(mcp_client, "book_table", book_mock)

    with pytest.raises(OrderPlacementError) as exc_info:
        await book_table_dineout(
            SESSION_ID,
            restaurant_id="drest_001",
            slot_id="slot_paid",
            item_id="item_001",
            reservation_time="2026-06-13T20:30:00",
            guest_count=2,
            latitude=12.97,
            longitude=77.59,
            slot_is_free=False,
            booking_price=500,
            token="tok",
        )

    assert "free" in str(exc_info.value).lower() or "paid" in str(exc_info.value).lower()
    book_mock.assert_not_called()


# ── Additional: Dineout happy path ────────────────────────────────────────────

@pytest.mark.asyncio
async def test_dineout_booking_happy_path(monkeypatch):
    monkeypatch.setattr(mcp_client, "book_table", AsyncMock(return_value=DINEOUT_BOOKING))

    result = await book_table_dineout(
        SESSION_ID,
        restaurant_id="drest_001",
        slot_id="slot_001",
        item_id="item_001",
        reservation_time="2026-06-13T19:30:00",
        guest_count=2,
        latitude=12.97,
        longitude=77.59,
        slot_is_free=True,
        booking_price=0,
        token="tok",
    )

    assert result.order_id == "dout_bk_001"
    assert result.vertical.value == "dineout"


# ── Additional: Instamart happy path ─────────────────────────────────────────

@pytest.mark.asyncio
async def test_instamart_checkout_happy_path(monkeypatch):
    monkeypatch.setattr(mcp_client, "get_cart", AsyncMock(return_value=MOCK_IM_CART))
    monkeypatch.setattr(mcp_client, "checkout", AsyncMock(return_value=IM_ORDER))

    result = await checkout_instamart(SESSION_ID, token="tok")

    assert result.order_id == "im_ord_001"
    assert result.vertical.value == "instamart"


# ── Additional: domain failure not retried ────────────────────────────────────

@pytest.mark.asyncio
async def test_food_order_domain_failure_not_retried(monkeypatch):
    """
    Domain failure (success=false) must raise immediately — no retries.
    PRD ref: Section 8.3 (Module 5 — on domain failure: surface, no retry)
    """
    call_count = 0

    async def domain_failing_place(**kwargs):
        nonlocal call_count
        call_count += 1
        raise _domain_error("restaurant_closed")

    monkeypatch.setattr(mcp_client, "get_food_cart", AsyncMock(return_value=MOCK_FOOD_CART))
    monkeypatch.setattr(mcp_client, "place_food_order", domain_failing_place)

    with pytest.raises(OrderPlacementError):
        await place_food_order(SESSION_ID, token="tok")

    assert call_count == 1   # Called once, not retried


# ── Additional: empty cart blocked ───────────────────────────────────────────

@pytest.mark.asyncio
async def test_food_order_empty_cart_rejected(monkeypatch):
    empty_cart = {**MOCK_FOOD_CART, "items": [], "subtotal": 0}
    monkeypatch.setattr(mcp_client, "get_food_cart", AsyncMock(return_value=empty_cart))
    place_mock = AsyncMock()
    monkeypatch.setattr(mcp_client, "place_food_order", place_mock)

    with pytest.raises(OrderPlacementError, match="empty"):
        await place_food_order(SESSION_ID, token="tok")

    place_mock.assert_not_called()


# ── Additional: Instamart 5xx → found in get_orders → success ────────────────

@pytest.mark.asyncio
async def test_instamart_5xx_then_found_in_get_orders(monkeypatch):
    async def failing_checkout(**kwargs):
        raise _retryable_error()

    monkeypatch.setattr(mcp_client, "get_cart", AsyncMock(return_value=MOCK_IM_CART))
    monkeypatch.setattr(mcp_client, "checkout", failing_checkout)
    monkeypatch.setattr(mcp_client, "get_orders", AsyncMock(return_value=[IM_ORDER]))

    result = await checkout_instamart(SESSION_ID, token="tok")
    assert result.order_id == "im_ord_001"
