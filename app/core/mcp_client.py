from __future__ import annotations
"""
MCP client — wraps all 35 Swiggy tool calls over streamable HTTP (JSON-RPC 2.0).
PRD ref: Section 8.3 (Module 4 — MCP Client), Section 2.2 (Complete Tool Catalog)

In MOCK_MODE every method returns realistic hardcoded data.
NON-IDEMPOTENT tools (place_food_order, checkout, book_table) must NOT be called
directly from routes — route through order_orchestrator.py.

Stub: filled in Sprint 4.
"""


class SwiggyMCPClient:
    """
    Async HTTP client for Swiggy's three MCP servers.
    Instantiate once and reuse across the application lifetime.
    """

    # ── Food tools ────────────────────────────────────────────────────────

    async def get_addresses(self) -> list[dict]:
        raise NotImplementedError

    async def search_restaurants(self, address_id: str, query: str) -> list[dict]:
        raise NotImplementedError

    async def get_restaurant_menu(self, restaurant_id: str) -> dict:
        raise NotImplementedError

    async def search_menu(self, query: str, restaurant_id: str | None = None) -> list[dict]:
        raise NotImplementedError

    async def update_food_cart(self, restaurant_id: str, items: list[dict]) -> dict:
        raise NotImplementedError

    async def get_food_cart(self) -> dict:
        """
        Read current Food cart from Swiggy server.
        NEVER cache the result — always call before any cart-touching operation.
        PRD ref: Section 7.4 (Multi-Turn Cart State Management)
        """
        raise NotImplementedError

    async def flush_food_cart(self) -> dict:
        raise NotImplementedError

    async def fetch_food_coupons(self) -> list[dict]:
        raise NotImplementedError

    async def apply_food_coupon(self, coupon_code: str, address_id: str) -> dict:
        raise NotImplementedError

    async def place_food_order(self, payment_method: str = "COD") -> dict:
        """
        NON-IDEMPOTENT: Do not call directly.
        Use order_orchestrator.place_food_order() which implements check-then-retry.
        PRD ref: Section 8.3 (Module 5), Section 7.6 (Edge Cases — 5xx pattern)
        """
        raise NotImplementedError

    async def get_food_orders(self) -> list[dict]:
        raise NotImplementedError

    async def track_food_order(self, order_id: str) -> dict:
        raise NotImplementedError

    # ── Instamart tools ───────────────────────────────────────────────────

    async def im_get_addresses(self) -> list[dict]:
        raise NotImplementedError

    async def search_products(self, address_id: str, query: str) -> list[dict]:
        raise NotImplementedError

    async def your_go_to_items(self, address_id: str) -> list[dict]:
        raise NotImplementedError

    async def update_cart(self, items: list[dict]) -> dict:
        """items: list of {spinId, quantity}. spinId is variant-level, not productId."""
        raise NotImplementedError

    async def get_cart(self) -> dict:
        """
        Read current Instamart cart from Swiggy server.
        NEVER cache the result.
        """
        raise NotImplementedError

    async def clear_cart(self) -> dict:
        """Must be called before switching delivery address. PRD ref: Section 2.3."""
        raise NotImplementedError

    async def im_create_address(self, address_data: dict) -> dict:
        raise NotImplementedError

    async def checkout(self, payment_method: str = "COD") -> dict:
        """
        NON-IDEMPOTENT: Do not call directly.
        Use order_orchestrator.checkout_instamart() which implements check-then-retry.
        """
        raise NotImplementedError

    async def get_orders(self) -> list[dict]:
        raise NotImplementedError

    async def track_order(self, order_id: str) -> dict:
        raise NotImplementedError

    # ── Dineout tools ─────────────────────────────────────────────────────

    async def get_saved_locations(self) -> list[dict]:
        """Returns lat/lng locations — NOT addressId. Different system from Food addresses."""
        raise NotImplementedError

    async def search_restaurants_dineout(
        self,
        query: str,
        lat: float,
        lng: float,
        entity_type: str | None = None,
    ) -> list[dict]:
        raise NotImplementedError

    async def get_restaurant_details(
        self, restaurant_id: str, latitude: float, longitude: float
    ) -> dict:
        raise NotImplementedError

    async def get_available_slots(
        self, restaurant_id: str, date: str, latitude: float, longitude: float
    ) -> list[dict]:
        """Returns slots. Caller must filter to isFree=true before presenting to user."""
        raise NotImplementedError

    async def book_table(
        self,
        restaurant_id: str,
        slot_id: str,
        item_id: str,
        reservation_time: str,
        guest_count: int,
        latitude: float,
        longitude: float,
    ) -> dict:
        """
        NON-IDEMPOTENT: Do not call directly.
        Use order_orchestrator.book_table_dineout() which implements check-then-retry.
        Only free slots (isFree=true, bookingPrice=0) are bookable in v1.
        """
        raise NotImplementedError

    async def get_booking_status(self, order_id: str) -> dict:
        raise NotImplementedError

    # ── Shared ────────────────────────────────────────────────────────────

    async def report_error(
        self,
        tool: str,
        error_message: str,
        domain: str | None = None,
        flow_description: str | None = None,
        tool_context: dict | None = None,
    ) -> dict:
        """
        Call on persistent failures to log diagnostics with Swiggy.
        PRD ref: Section 8.3 (Module 6), Section 6 (OKR 4 — report_error on 100% tool failures)
        """
        raise NotImplementedError


# Application-level singleton — initialised in main.py startup
mcp_client = SwiggyMCPClient()
