from __future__ import annotations
"""
Order placement orchestrator.
PRD ref: Section 8.3 (Module 5 — Order Placement Orchestrator)

All three order placement tools are NON-IDEMPOTENT.
This module is the ONLY entry point for placing orders.
Routes must NEVER call mcp_client.place_food_order / checkout / book_table directly.

Implements check-then-retry pattern:
  1. Attempt placement
  2. On 5xx: wait, call get_*_orders to check if order already exists
  3. If found → treat as success
  4. If not found → retry (max 3 attempts)
  5. If exhausted → raise OrderPlacementError, call report_error

Stub: filled in Sprint 7.
"""

import uuid

from app.models.order import ConfirmResponse, OrderPlacementError  # noqa: F401


async def place_food_order(session_id: uuid.UUID) -> ConfirmResponse:
    """
    Place a Food order via check-then-retry.

    Pre-conditions checked before placement:
    - Cart total <= ₹1000 (PRD Section 2.3 — Food cart cap)
    - Cart matches what user confirmed (live get_food_cart call)
    - Payment method: COD only (v1 constraint)
    """
    raise NotImplementedError("Order orchestrator implemented in Sprint 7")


async def checkout_instamart(session_id: uuid.UUID) -> ConfirmResponse:
    """
    Place an Instamart order via check-then-retry.

    Pre-conditions:
    - Cart total >= ₹99 minimum (PRD Section 2.3)
    - Payment method: COD only
    """
    raise NotImplementedError


async def book_table_dineout(
    session_id: uuid.UUID,
    restaurant_id: str,
    slot_id: str,
    item_id: str,
    reservation_time: str,
    guest_count: int,
    latitude: float,
    longitude: float,
) -> ConfirmResponse:
    """
    Book a Dineout table via check-then-retry.

    Pre-conditions:
    - Slot must be isFree=true, bookingPrice=0 (paid deals rejected — v1 constraint)
    """
    raise NotImplementedError
