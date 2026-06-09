from __future__ import annotations

"""
Unit tests for SwiggyMCPClient in MOCK_MODE.
PRD ref: Section 8.3 (Module 4 — MCP Client), Section 2.2 (Complete Tool Catalog)

All tests run in mock mode — no live Swiggy credentials needed.
"""

import pytest

from app.core.mcp_client import SwiggyMCPClient, MCPToolError, _parse_response
from app.core.error_classifier import ErrorClassification
from app.core.oauth_handler import OAuthExpiredError


@pytest.fixture
def client(monkeypatch) -> SwiggyMCPClient:
    monkeypatch.setattr("app.core.mcp_client.settings.mock_mode", True)
    return SwiggyMCPClient()


# ── Food tools ────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_addresses_returns_list(client):
    result = await client.get_addresses()
    assert isinstance(result, list)
    assert len(result) > 0
    assert "id" in result[0]
    assert "displayText" in result[0]


@pytest.mark.asyncio
async def test_search_restaurants_returns_open_restaurants(client):
    result = await client.search_restaurants("addr_001", "tiramisu")
    assert all(r["availabilityStatus"] == "OPEN" for r in result)


@pytest.mark.asyncio
async def test_get_restaurant_menu_has_categories(client):
    result = await client.get_restaurant_menu("rest_001")
    assert "categories" in result
    assert len(result["categories"]) > 0


@pytest.mark.asyncio
async def test_search_menu_filters_by_query(client):
    result = await client.search_menu("tiramisu")
    assert any("Tiramisu" in item["name"] for item in result)


@pytest.mark.asyncio
async def test_get_food_cart_has_required_fields(client):
    cart = await client.get_food_cart()
    assert "restaurantId" in cart
    assert "items" in cart
    assert "subtotal" in cart


@pytest.mark.asyncio
async def test_update_food_cart_reflects_items(client):
    items = [{"itemId": "item_001", "quantity": 2}]
    result = await client.update_food_cart("rest_001", items)
    assert result["restaurantId"] == "rest_001"
    assert result["items"] == items


@pytest.mark.asyncio
async def test_flush_food_cart_returns_cleared(client):
    result = await client.flush_food_cart()
    assert result["status"] == "CLEARED"


@pytest.mark.asyncio
async def test_fetch_food_coupons_cod_compatible(client):
    coupons = await client.fetch_food_coupons()
    assert all("COD" in c["paymentMethods"] for c in coupons)


@pytest.mark.asyncio
async def test_place_food_order_returns_order_id(client):
    result = await client.place_food_order()
    assert "orderId" in result
    assert result["paymentMethod"] == "COD"


@pytest.mark.asyncio
async def test_get_food_orders_returns_list(client):
    result = await client.get_food_orders()
    assert isinstance(result, list)


@pytest.mark.asyncio
async def test_track_food_order_has_eta(client):
    result = await client.track_food_order("food_ord_001")
    assert "eta" in result
    assert result["orderId"] == "food_ord_001"


# ── Instamart tools ───────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_search_products_returns_spin_ids(client):
    result = await client.search_products("addr_001", "pasta")
    assert len(result) > 0
    for product in result:
        assert "variants" in product
        assert "spinId" in product["variants"][0]


@pytest.mark.asyncio
async def test_your_go_to_items_returns_products(client):
    result = await client.your_go_to_items("addr_001")
    assert isinstance(result, list)
    assert len(result) > 0


@pytest.mark.asyncio
async def test_get_cart_has_subtotal(client):
    cart = await client.get_cart()
    assert "subtotal" in cart
    assert "items" in cart


@pytest.mark.asyncio
async def test_update_cart_uses_spin_ids(client):
    items = [{"spinId": "spin_001", "quantity": 2}]
    result = await client.update_cart(items)
    assert result["items"] == items


@pytest.mark.asyncio
async def test_clear_cart_returns_cleared(client):
    result = await client.clear_cart()
    assert result["status"] == "CLEARED"


@pytest.mark.asyncio
async def test_checkout_returns_order_id(client):
    result = await client.checkout()
    assert "orderId" in result
    assert result["paymentMethod"] == "COD"


@pytest.mark.asyncio
async def test_get_orders_returns_list(client):
    result = await client.get_orders()
    assert isinstance(result, list)


@pytest.mark.asyncio
async def test_track_order_has_eta(client):
    result = await client.track_order("im_ord_001")
    assert "eta" in result


# ── Dineout tools ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_saved_locations_has_lat_lng(client):
    """Dineout uses lat/lng — not addressId. PRD Section 2.4."""
    result = await client.get_saved_locations()
    assert len(result) > 0
    assert "lat" in result[0]
    assert "lng" in result[0]
    assert "id" not in result[0] or "lat" in result[0]  # lat/lng present


@pytest.mark.asyncio
async def test_get_available_slots_includes_paid_slots_for_filtering(client):
    """
    Raw slots include paid ones (isFree=False).
    Caller must filter — this test confirms raw data is unfiltered.
    PRD ref: Section 7.2 (filter to isFree=true)
    """
    slots = await client.get_available_slots("drest_001", "2026-06-13", 12.97, 77.59)
    all_free = all(s["isFree"] for s in slots)
    has_paid = any(not s["isFree"] for s in slots)
    assert has_paid, "Mock data must include a paid slot to verify caller filtering"


@pytest.mark.asyncio
async def test_book_table_returns_booking_id(client):
    result = await client.book_table(
        restaurant_id="drest_001",
        slot_id="slot_001",
        item_id="item_001",
        reservation_time="2026-06-13T19:30:00",
        guest_count=2,
        latitude=12.9716,
        longitude=77.5946,
    )
    assert "bookingId" in result
    assert "confirmationNumber" in result


@pytest.mark.asyncio
async def test_get_booking_status_returns_booking(client):
    result = await client.get_booking_status("dout_bk_001")
    assert "bookingId" in result


@pytest.mark.asyncio
async def test_report_error_mock_returns_reported(client):
    result = await client.report_error(
        tool="place_food_order",
        error_message="5xx after 3 retries",
        flow_description="food checkout",
    )
    assert result["reported"] is True


# ── _parse_response (unit tests — no HTTP) ────────────────────────────────────

class TestParseResponse:
    def test_success_true_returns_data(self):
        body = {"result": {"success": True, "data": {"orderId": "123"}}}
        result = _parse_response(200, body, "place_food_order")
        assert result == {"orderId": "123"}

    def test_http_401_raises_oauth_expired(self):
        with pytest.raises(OAuthExpiredError):
            _parse_response(401, {}, "get_food_cart")

    def test_jsonrpc_minus_32001_raises_oauth_expired(self):
        body = {"error": {"code": -32001, "message": "auth error"}}
        with pytest.raises(OAuthExpiredError):
            _parse_response(200, body, "get_food_cart")

    def test_http_503_raises_mcp_tool_error(self):
        with pytest.raises(MCPToolError) as exc_info:
            _parse_response(503, {}, "search_restaurants")
        assert exc_info.value.classification.bucket == "upstream_error"

    def test_success_false_domain_failure_raises(self):
        body = {"result": {"success": False, "error": {"message": "restaurant closed"}}}
        with pytest.raises(MCPToolError) as exc_info:
            _parse_response(200, body, "update_food_cart")
        assert exc_info.value.classification.bucket == "restaurant_closed"

    def test_food_cart_cap_message_raises_correct_bucket(self):
        body = {"result": {"success": False, "error": {"message": "cart exceeds ₹1000 limit"}}}
        with pytest.raises(MCPToolError) as exc_info:
            _parse_response(200, body, "update_food_cart")
        assert exc_info.value.classification.bucket == "food_cart_cap"
