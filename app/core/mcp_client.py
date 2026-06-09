from __future__ import annotations

"""
MCP client — wraps all 35 Swiggy tool calls over streamable HTTP (JSON-RPC 2.0).
PRD ref: Section 8.3 (Module 4 — MCP Client), Section 2.2 (Complete Tool Catalog)

Architecture:
  - One httpx AsyncClient per MCP server (food / instamart / dineout)
  - All calls: POST with JSON-RPC 2.0 envelope, Bearer token in header
  - Response path: HTTP status → parse JSON → check success boolean → data or error

NON-IDEMPOTENT tools (place_food_order, checkout, book_table):
  Do NOT call these methods directly from routes.
  Always go through order_orchestrator.py which implements check-then-retry.

In MOCK_MODE: every method returns realistic hardcoded data and logs a warning.
"""

import logging
import uuid
from typing import Any

import httpx

from app.config import settings
from app.core.error_classifier import classify, ErrorClassification

logger = logging.getLogger(__name__)

_MOCK_TOKEN = "mock.jwt.token.vertexcart"

# ── JSON-RPC builder ──────────────────────────────────────────────────────────

def _build_rpc_payload(tool_name: str, arguments: dict[str, Any]) -> dict:
    return {
        "jsonrpc": "2.0",
        "method": "tools/call",
        "params": {"name": tool_name, "arguments": arguments},
        "id": 1,
    }


# ── Response parser ───────────────────────────────────────────────────────────

class MCPToolError(Exception):
    """Raised when a Swiggy MCP tool returns success=false or an HTTP error."""

    def __init__(self, classification: ErrorClassification, raw_message: str = "") -> None:
        self.classification = classification
        self.raw_message = raw_message
        super().__init__(f"[{classification.bucket}] {classification.user_message or raw_message}")


def _parse_response(
    http_status: int,
    body: dict,
    tool_name: str,
) -> Any:
    """
    Parse a Swiggy JSON-RPC response.
    Raises MCPToolError on any failure path.
    Returns the data payload on success.
    """
    # Auth failures surfaced at HTTP level
    if http_status == 401:
        from app.core.oauth_handler import OAuthExpiredError
        raise OAuthExpiredError("HTTP 401 from Swiggy MCP — token invalid or expired")

    if http_status >= 500:
        classification = classify(http_status, "", tool_name)
        raise MCPToolError(classification)

    # JSON-RPC error block (e.g. -32001 auth error)
    if "error" in body:
        rpc_error = body["error"]
        rpc_code = rpc_error.get("code")
        rpc_message = rpc_error.get("message", "")

        if rpc_code == -32001:
            from app.core.oauth_handler import OAuthExpiredError
            raise OAuthExpiredError(f"JSON-RPC -32001: {rpc_message}")

        classification = classify(http_status, rpc_message, tool_name)
        raise MCPToolError(classification, rpc_message)

    # Domain-level failure (HTTP 200, success=false)
    result = body.get("result", body)
    if not result.get("success", True):
        error_message = result.get("error", {}).get("message", "")
        classification = classify(200, error_message, tool_name)
        raise MCPToolError(classification, error_message)

    return result.get("data", result)


# ── Mock data store ───────────────────────────────────────────────────────────

_MOCK_ADDRESSES = [
    {"id": "addr_001", "label": "Home", "displayText": "12 MG Road, Bengaluru 560001"},
    {"id": "addr_002", "label": "Office", "displayText": "91 Springboard, Koramangala"},
]

_MOCK_RESTAURANTS = [
    {
        "restaurantId": "rest_001",
        "name": "Smoke House Deli",
        "cuisines": ["Continental", "Desserts"],
        "avgDeliveryTime": 35,
        "availabilityStatus": "OPEN",
        "rating": 4.4,
    },
    {
        "restaurantId": "rest_002",
        "name": "Biryani House",
        "cuisines": ["Biryani", "Mughlai"],
        "avgDeliveryTime": 28,
        "availabilityStatus": "OPEN",
        "rating": 4.2,
    },
]

_MOCK_MENU_ITEMS = [
    {"itemId": "item_001", "name": "Tiramisu", "price": 320, "category": "Desserts"},
    {"itemId": "item_002", "name": "Chicken Biryani", "price": 349, "category": "Mains"},
    {"itemId": "item_003", "name": "Margherita Pizza", "price": 299, "category": "Pizza"},
]

_MOCK_FOOD_CART = {
    "restaurantId": "rest_001",
    "restaurantName": "Smoke House Deli",
    "items": [{"itemId": "item_001", "name": "Tiramisu", "price": 320, "quantity": 1}],
    "subtotal": 320,
    "status": "ACTIVE",
}

_MOCK_IM_PRODUCTS = [
    {
        "productId": "prod_001",
        "name": "Pasta (500g)",
        "variants": [{"spinId": "spin_001", "weight": "500g", "price": 89}],
    },
    {
        "productId": "prod_002",
        "name": "Tomatoes (1kg)",
        "variants": [{"spinId": "spin_002", "weight": "1kg", "price": 45}],
    },
    {
        "productId": "prod_003",
        "name": "Olive Oil (500ml)",
        "variants": [{"spinId": "spin_003", "volume": "500ml", "price": 249}],
    },
]

_MOCK_IM_CART = {
    "items": [
        {"spinId": "spin_001", "name": "Pasta (500g)", "price": 89, "quantity": 2},
        {"spinId": "spin_002", "name": "Tomatoes (1kg)", "price": 45, "quantity": 1},
    ],
    "subtotal": 223,
    "status": "ACTIVE",
    "deliveryAddress": _MOCK_ADDRESSES[0],
}

_MOCK_DINEOUT_LOCATIONS = [
    {"id": "loc_001", "addressLine": "12 MG Road, Bengaluru", "lat": 12.9716, "lng": 77.5946},
]

_MOCK_DINEOUT_RESTAURANTS = [
    {
        "restaurantId": "drest_001",
        "name": "The Fatty Bao",
        "cuisine": "Asian",
        "rating": 4.6,
        "priceForTwo": 1800,
    },
    {
        "restaurantId": "drest_002",
        "name": "Toit Brewpub",
        "cuisine": "Continental",
        "rating": 4.5,
        "priceForTwo": 1500,
    },
]

_MOCK_SLOTS = [
    {
        "slotId": "slot_001",
        "date": "2026-06-13",
        "time": "19:30",
        "band": "dinner",
        "isFree": True,
        "bookingPrice": 0,
        "availableSeats": 4,
    },
    {
        "slotId": "slot_002",
        "date": "2026-06-13",
        "time": "20:00",
        "band": "dinner",
        "isFree": True,
        "bookingPrice": 0,
        "availableSeats": 2,
    },
    {
        "slotId": "slot_003",
        "date": "2026-06-14",
        "time": "20:30",
        "band": "dinner",
        "isFree": False,    # Paid slot — agent must filter this out
        "bookingPrice": 500,
        "availableSeats": 6,
    },
]

_MOCK_FOOD_ORDER = {
    "orderId": "food_ord_mock_001",
    "status": "PLACED",
    "eta": "35 min",
    "paymentMethod": "COD",
    "total": 320,
}

_MOCK_IM_ORDER = {
    "orderId": "im_ord_mock_001",
    "status": "PLACED",
    "eta": "12 min",
    "paymentMethod": "COD",
    "total": 223,
}

_MOCK_DINEOUT_BOOKING = {
    "bookingId": "dout_bk_mock_001",
    "status": "CONFIRMED",
    "restaurantName": "The Fatty Bao",
    "reservationTime": "2026-06-13T19:30:00",
    "guestCount": 2,
    "confirmationNumber": "TFB-20260613-001",
    "restaurantAddress": "12 Church Street, Bengaluru",
}


# ── Client ────────────────────────────────────────────────────────────────────

class SwiggyMCPClient:
    """
    Async HTTP client for Swiggy's three MCP servers.
    One instance lives for the application lifetime (singleton in main.py).

    Token is passed per-call (from session) rather than stored on the client,
    so multiple sessions can share one client instance safely.
    """

    def __init__(self) -> None:
        # Separate clients per server to allow independent connection pools
        self._food_client: httpx.AsyncClient | None = None
        self._im_client: httpx.AsyncClient | None = None
        self._dineout_client: httpx.AsyncClient | None = None

    async def start(self) -> None:
        """Initialise HTTP clients. Called at application startup."""
        self._food_client = httpx.AsyncClient(
            base_url=settings.swiggy_food_mcp_url, timeout=15.0
        )
        self._im_client = httpx.AsyncClient(
            base_url=settings.swiggy_instamart_mcp_url, timeout=15.0
        )
        self._dineout_client = httpx.AsyncClient(
            base_url=settings.swiggy_dineout_mcp_url, timeout=15.0
        )

    async def stop(self) -> None:
        """Close HTTP clients. Called at application shutdown."""
        for client in (self._food_client, self._im_client, self._dineout_client):
            if client:
                await client.aclose()

    # ── Internal call helper ──────────────────────────────────────────────

    async def _call(
        self,
        client: httpx.AsyncClient,
        tool_name: str,
        arguments: dict[str, Any],
        token: str,
    ) -> Any:
        """
        Execute one JSON-RPC tool call against a Swiggy MCP server.
        Raises MCPToolError or OAuthExpiredError on any failure.
        """
        payload = _build_rpc_payload(tool_name, arguments)
        headers = {"Authorization": f"Bearer {token}"}

        try:
            response = await client.post("/", json=payload, headers=headers)
        except httpx.RequestError as exc:
            # Network-level failure — classify as upstream error
            classification = classify(503, str(exc), tool_name)
            raise MCPToolError(classification, str(exc)) from exc

        body = response.json()
        return _parse_response(response.status_code, body, tool_name)

    def _mock_warn(self, tool_name: str) -> None:
        logger.warning("[MOCK] MCP tool called: %s — returning mock data", tool_name)

    # ── Food tools ────────────────────────────────────────────────────────

    async def get_addresses(self, token: str = "") -> list[dict]:
        """PRD ref: Section 2.2 (Food — get_addresses)"""
        if settings.mock_mode:
            self._mock_warn("get_addresses")
            return _MOCK_ADDRESSES
        return await self._call(self._food_client, "get_addresses", {}, token)

    async def search_restaurants(
        self, address_id: str, query: str, token: str = ""
    ) -> list[dict]:
        """PRD ref: Section 2.2 (Food — search_restaurants)"""
        if settings.mock_mode:
            self._mock_warn("search_restaurants")
            return [r for r in _MOCK_RESTAURANTS if r["availabilityStatus"] == "OPEN"]
        return await self._call(
            self._food_client,
            "search_restaurants",
            {"addressId": address_id, "query": query},
            token,
        )

    async def get_restaurant_menu(self, restaurant_id: str, token: str = "") -> dict:
        """PRD ref: Section 2.2 (Food — get_restaurant_menu)"""
        if settings.mock_mode:
            self._mock_warn("get_restaurant_menu")
            return {"restaurantId": restaurant_id, "categories": [
                {"name": "Desserts", "items": [_MOCK_MENU_ITEMS[0]]},
                {"name": "Mains", "items": [_MOCK_MENU_ITEMS[1]]},
            ]}
        return await self._call(
            self._food_client, "get_restaurant_menu", {"restaurantId": restaurant_id}, token
        )

    async def search_menu(
        self, query: str, restaurant_id: str | None = None, token: str = ""
    ) -> list[dict]:
        """PRD ref: Section 2.2 (Food — search_menu)"""
        if settings.mock_mode:
            self._mock_warn("search_menu")
            return [i for i in _MOCK_MENU_ITEMS if query.lower() in i["name"].lower()]
        args: dict[str, Any] = {"query": query}
        if restaurant_id:
            args["restaurantId"] = restaurant_id
        return await self._call(self._food_client, "search_menu", args, token)

    async def update_food_cart(
        self, restaurant_id: str, items: list[dict], token: str = ""
    ) -> dict:
        """
        PRD ref: Section 2.2 (Food — update_food_cart)
        Binds cart to restaurant_id. Switching restaurant flushes current cart.
        """
        if settings.mock_mode:
            self._mock_warn("update_food_cart")
            return {**_MOCK_FOOD_CART, "restaurantId": restaurant_id, "items": items}
        return await self._call(
            self._food_client,
            "update_food_cart",
            {"restaurantId": restaurant_id, "items": items},
            token,
        )

    async def get_food_cart(self, token: str = "") -> dict:
        """
        Read current Food cart from Swiggy server.
        NEVER cache this result — always call before any cart-touching turn.
        PRD ref: Section 7.4 (turn boundary pattern), Section 2.2 (Food — get_food_cart)
        """
        if settings.mock_mode:
            self._mock_warn("get_food_cart")
            return _MOCK_FOOD_CART
        return await self._call(self._food_client, "get_food_cart", {}, token)

    async def flush_food_cart(self, token: str = "") -> dict:
        """PRD ref: Section 2.2 (Food — flush_food_cart)"""
        if settings.mock_mode:
            self._mock_warn("flush_food_cart")
            return {"status": "CLEARED"}
        return await self._call(self._food_client, "flush_food_cart", {}, token)

    async def fetch_food_coupons(self, token: str = "") -> list[dict]:
        """
        PRD ref: Section 2.2 (Food — fetch_food_coupons)
        Caller must filter to COD-compatible coupons only before presenting to user.
        """
        if settings.mock_mode:
            self._mock_warn("fetch_food_coupons")
            return [
                {"code": "MOCK50", "discount": 50, "paymentMethods": ["COD"], "minOrder": 200}
            ]
        return await self._call(self._food_client, "fetch_food_coupons", {}, token)

    async def apply_food_coupon(
        self, coupon_code: str, address_id: str, token: str = ""
    ) -> dict:
        """PRD ref: Section 2.2 (Food — apply_food_coupon)"""
        if settings.mock_mode:
            self._mock_warn("apply_food_coupon")
            return {**_MOCK_FOOD_CART, "couponApplied": coupon_code, "discount": 50, "subtotal": 270}
        return await self._call(
            self._food_client,
            "apply_food_coupon",
            {"couponCode": coupon_code, "addressId": address_id},
            token,
        )

    async def place_food_order(self, payment_method: str = "COD", token: str = "") -> dict:
        """
        NON-IDEMPOTENT: Do not call directly from routes or session manager.
        Use order_orchestrator.place_food_order() — implements check-then-retry.
        PRD ref: Section 8.3 (Module 5), Section 7.6 (edge case — 5xx pattern)
        """
        if settings.mock_mode:
            self._mock_warn("place_food_order")
            return _MOCK_FOOD_ORDER
        return await self._call(
            self._food_client,
            "place_food_order",
            {"paymentMethod": payment_method},
            token,
        )

    async def get_food_orders(self, token: str = "") -> list[dict]:
        """Used by order_orchestrator for idempotency check on 5xx."""
        if settings.mock_mode:
            self._mock_warn("get_food_orders")
            return []  # Empty = no recent order found → safe to retry
        return await self._call(self._food_client, "get_food_orders", {}, token)

    async def track_food_order(self, order_id: str, token: str = "") -> dict:
        """PRD ref: Section 7.1 (Confirmation + Tracking — poll max every 10s)"""
        if settings.mock_mode:
            self._mock_warn("track_food_order")
            return {"orderId": order_id, "status": "OUT_FOR_DELIVERY", "eta": "22 min"}
        return await self._call(
            self._food_client, "track_food_order", {"orderId": order_id}, token
        )

    # ── Instamart tools ───────────────────────────────────────────────────

    async def im_get_addresses(self, token: str = "") -> list[dict]:
        """PRD ref: Section 2.2 (Instamart — get_addresses)"""
        if settings.mock_mode:
            self._mock_warn("im_get_addresses")
            return _MOCK_ADDRESSES
        return await self._call(self._im_client, "get_addresses", {}, token)

    async def search_products(
        self, address_id: str, query: str, token: str = ""
    ) -> list[dict]:
        """
        PRD ref: Section 2.2 (Instamart — search_products)
        Response includes spinId (variant-level ID) — required for update_cart.
        """
        if settings.mock_mode:
            self._mock_warn("search_products")
            return [p for p in _MOCK_IM_PRODUCTS if query.lower() in p["name"].lower()]
        return await self._call(
            self._im_client,
            "search_products",
            {"addressId": address_id, "query": query},
            token,
        )

    async def your_go_to_items(self, address_id: str, token: str = "") -> list[dict]:
        """
        PRD ref: Section 2.2 (Instamart — your_go_to_items)
        Used for reorder intents — skips search, returns frequently ordered SKUs directly.
        """
        if settings.mock_mode:
            self._mock_warn("your_go_to_items")
            return _MOCK_IM_PRODUCTS
        return await self._call(
            self._im_client, "your_go_to_items", {"addressId": address_id}, token
        )

    async def update_cart(self, items: list[dict], token: str = "") -> dict:
        """
        PRD ref: Section 2.2 (Instamart — update_cart)
        items: list of {spinId, quantity}. spinId is variant-level — NOT productId.
        """
        if settings.mock_mode:
            self._mock_warn("update_cart")
            return {**_MOCK_IM_CART, "items": items}
        return await self._call(self._im_client, "update_cart", {"items": items}, token)

    async def get_cart(self, token: str = "") -> dict:
        """
        Read current Instamart cart from Swiggy server.
        NEVER cache this result.
        PRD ref: Section 7.4 (turn boundary pattern)
        """
        if settings.mock_mode:
            self._mock_warn("get_cart")
            return _MOCK_IM_CART
        return await self._call(self._im_client, "get_cart", {}, token)

    async def clear_cart(self, token: str = "") -> dict:
        """
        PRD ref: Section 2.3 (Instamart cart binding — clear before address switch)
        Must be called before changing delivery address. Never silently switch.
        """
        if settings.mock_mode:
            self._mock_warn("clear_cart")
            return {"status": "CLEARED"}
        return await self._call(self._im_client, "clear_cart", {}, token)

    async def im_create_address(self, address_data: dict, token: str = "") -> dict:
        """PRD ref: Section 2.2 (Instamart — create_address)"""
        if settings.mock_mode:
            self._mock_warn("im_create_address")
            return {"id": "addr_new_001", **address_data}
        return await self._call(
            self._im_client, "create_address", address_data, token
        )

    async def checkout(self, payment_method: str = "COD", token: str = "") -> dict:
        """
        NON-IDEMPOTENT: Do not call directly.
        Use order_orchestrator.checkout_instamart() — implements check-then-retry.
        Pre-condition: cart total >= ₹99 minimum (PRD Section 2.3).
        """
        if settings.mock_mode:
            self._mock_warn("checkout")
            return _MOCK_IM_ORDER
        return await self._call(
            self._im_client,
            "checkout",
            {"paymentMethod": payment_method},
            token,
        )

    async def get_orders(self, token: str = "") -> list[dict]:
        """Used by order_orchestrator for idempotency check on 5xx."""
        if settings.mock_mode:
            self._mock_warn("get_orders")
            return []
        return await self._call(self._im_client, "get_orders", {}, token)

    async def track_order(self, order_id: str, token: str = "") -> dict:
        """PRD ref: Section 9.3 (Screen 5 — poll every 10s)"""
        if settings.mock_mode:
            self._mock_warn("track_order")
            return {"orderId": order_id, "status": "OUT_FOR_DELIVERY", "eta": "8 min"}
        return await self._call(
            self._im_client, "track_order", {"orderId": order_id}, token
        )

    # ── Dineout tools ─────────────────────────────────────────────────────

    async def get_saved_locations(self, token: str = "") -> list[dict]:
        """
        PRD ref: Section 2.2 (Dineout — get_saved_locations), Section 2.4 (address scope)
        Returns lat/lng — NOT addressId. Never pass Food addressId to Dineout searches.
        """
        if settings.mock_mode:
            self._mock_warn("get_saved_locations")
            return _MOCK_DINEOUT_LOCATIONS
        return await self._call(self._dineout_client, "get_saved_locations", {}, token)

    async def search_restaurants_dineout(
        self,
        query: str,
        lat: float,
        lng: float,
        entity_type: str | None = None,
        token: str = "",
    ) -> list[dict]:
        """PRD ref: Section 2.2 (Dineout — search_restaurants_dineout)"""
        if settings.mock_mode:
            self._mock_warn("search_restaurants_dineout")
            return _MOCK_DINEOUT_RESTAURANTS
        args: dict[str, Any] = {"query": query, "lat": lat, "lng": lng}
        if entity_type:
            args["entityType"] = entity_type
        return await self._call(self._dineout_client, "search_restaurants_dineout", args, token)

    async def get_restaurant_details(
        self, restaurant_id: str, latitude: float, longitude: float, token: str = ""
    ) -> dict:
        """PRD ref: Section 2.2 (Dineout — get_restaurant_details)"""
        if settings.mock_mode:
            self._mock_warn("get_restaurant_details")
            return {
                "restaurantId": restaurant_id,
                "name": "The Fatty Bao",
                "address": "12 Church Street, Bengaluru",
                "cuisines": ["Asian Fusion"],
                "rating": 4.6,
                "latitude": latitude,
                "longitude": longitude,
            }
        return await self._call(
            self._dineout_client,
            "get_restaurant_details",
            {"restaurantId": restaurant_id, "latitude": latitude, "longitude": longitude},
            token,
        )

    async def get_available_slots(
        self,
        restaurant_id: str,
        date: str,
        latitude: float,
        longitude: float,
        token: str = "",
    ) -> list[dict]:
        """
        PRD ref: Section 2.2 (Dineout — get_available_slots), Section 7.2 (Dineout flow)
        Returns all slots. Caller MUST filter to isFree=True before presenting to user.
        Paid slots (isFree=False) are not bookable in v1 (PRD Section 2.3).
        """
        if settings.mock_mode:
            self._mock_warn("get_available_slots")
            return _MOCK_SLOTS
        return await self._call(
            self._dineout_client,
            "get_available_slots",
            {
                "restaurantId": restaurant_id,
                "date": date,
                "latitude": latitude,
                "longitude": longitude,
            },
            token,
        )

    async def book_table(
        self,
        restaurant_id: str,
        slot_id: str,
        item_id: str,
        reservation_time: str,
        guest_count: int,
        latitude: float,
        longitude: float,
        token: str = "",
    ) -> dict:
        """
        NON-IDEMPOTENT: Do not call directly.
        Use order_orchestrator.book_table_dineout() — implements check-then-retry.
        Slot must be isFree=True, bookingPrice=0. Paid slots rejected before this call.
        PRD ref: Section 2.3 (Dineout reservations — free only)
        """
        if settings.mock_mode:
            self._mock_warn("book_table")
            return _MOCK_DINEOUT_BOOKING
        return await self._call(
            self._dineout_client,
            "book_table",
            {
                "restaurantId": restaurant_id,
                "slotId": slot_id,
                "itemId": item_id,
                "reservationTime": reservation_time,
                "guestCount": guest_count,
                "latitude": latitude,
                "longitude": longitude,
            },
            token,
        )

    async def get_booking_status(self, order_id: str, token: str = "") -> dict:
        """Used by order_orchestrator for idempotency check on 5xx."""
        if settings.mock_mode:
            self._mock_warn("get_booking_status")
            return {**_MOCK_DINEOUT_BOOKING, "bookingId": order_id}
        return await self._call(
            self._dineout_client, "get_booking_status", {"orderId": order_id}, token
        )

    # ── Shared ────────────────────────────────────────────────────────────

    async def report_error(
        self,
        tool: str,
        error_message: str,
        domain: str | None = None,
        flow_description: str | None = None,
        tool_context: dict | None = None,
        token: str = "",
    ) -> dict:
        """
        Log diagnostic data with Swiggy for persistent failures.
        Called by order_orchestrator after retry exhaustion.
        PRD ref: Section 6 (OKR 4 — report_error on 100% tool failures reaching user)
        """
        if settings.mock_mode:
            self._mock_warn("report_error")
            logger.error(
                "[MOCK] report_error: tool=%s message=%s flow=%s",
                tool, error_message, flow_description,
            )
            return {"reported": True, "diagnosticLink": "https://mock.swiggy.com/support/mock"}

        # report_error can go to any server — use food as default
        args: dict[str, Any] = {"tool": tool, "errorMessage": error_message}
        if domain:
            args["domain"] = domain
        if flow_description:
            args["flowDescription"] = flow_description
        if tool_context:
            args["toolContext"] = tool_context

        return await self._call(self._food_client, "report_error", args, token)


# Application-level singleton — start()/stop() called in main.py lifecycle
mcp_client = SwiggyMCPClient()
