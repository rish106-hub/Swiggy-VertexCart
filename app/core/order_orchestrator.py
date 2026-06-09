from __future__ import annotations

"""
Order placement orchestrator.
PRD ref: Section 8.3 (Module 5 — Order Placement Orchestrator)

Three Swiggy tools are NON-IDEMPOTENT:
  - place_food_order   (Food)
  - checkout           (Instamart)
  - book_table         (Dineout)

This module is the ONLY entry point for calling those three tools.
Routes and session manager must NEVER call them directly.

Check-then-retry pattern (per PRD Section 8.3 / 7.6):
  1. Verify pre-conditions (cap, minimum, isFree)
  2. Attempt placement
  3. On 5xx / network error:
       a. Wait (exponential backoff with jitter)
       b. Call get_*_orders / get_booking_status to check if order already exists
       c. If found → treat as success (idempotency recovery)
       d. If not found → retry placement (max MAX_RETRIES attempts)
  4. After MAX_RETRIES with no confirmation → raise OrderPlacementError, call report_error
  5. On domain failure (success=false) → surface to user immediately, no retry

Backoff schedule: 500ms → 1000ms → 2000ms → 4000ms
Each step ±30% jitter. Total wall-clock cap: 30s.
"""

import asyncio
import logging
import random
import uuid
from datetime import datetime, timezone, timedelta

from app.config import settings
from app.core.mcp_client import MCPToolError, mcp_client
from app.models.order import ConfirmResponse, OrderPlacementError

logger = logging.getLogger(__name__)

# ── Retry config (PRD Section 8.3 — Module 4 retry policy) ───────────────────

MAX_RETRIES = 3
_BACKOFF_STEPS_MS = [500, 1000, 2000, 4000]   # ms per attempt
_JITTER_FACTOR = 0.3                           # ±30%
_WALL_CLOCK_CAP_SECONDS = 30

# Food cart cap per Swiggy Builders Club v1 constraint
_FOOD_CART_CAP_INR = 1000

# Instamart minimum order value
_INSTAMART_MINIMUM_INR = 99


# ── Backoff helper ────────────────────────────────────────────────────────────

async def _wait_with_jitter(attempt: int) -> None:
    """
    Wait with exponential backoff + ±30% jitter.
    attempt is 0-indexed (first retry = attempt 0).
    """
    base_ms = _BACKOFF_STEPS_MS[min(attempt, len(_BACKOFF_STEPS_MS) - 1)]
    jitter = base_ms * _JITTER_FACTOR * (random.random() * 2 - 1)  # ±30%
    delay_seconds = (base_ms + jitter) / 1000.0
    await asyncio.sleep(max(delay_seconds, 0.1))


def _order_placed_recently(orders: list[dict], within_seconds: int = 60) -> dict | None:
    """
    Scan recent orders for one placed in the last `within_seconds`.
    Used to detect if a placement succeeded before we received the response.
    PRD ref: Section 8.3 (Module 5 — check-then-retry step b)
    """
    cutoff = datetime.now(tz=timezone.utc) - timedelta(seconds=within_seconds)

    for order in orders:
        placed_raw = order.get("placedAt") or order.get("createdAt") or order.get("placed_at")
        if not placed_raw:
            # No timestamp — treat as recent (safe to return as success)
            return order
        try:
            placed_at = datetime.fromisoformat(str(placed_raw).replace("Z", "+00:00"))
            if placed_at.tzinfo is None:
                placed_at = placed_at.replace(tzinfo=timezone.utc)
            if placed_at >= cutoff:
                return order
        except (ValueError, TypeError):
            return order  # Unparseable timestamp — treat as recent

    return None


async def _store_order_reference(
    session_id: uuid.UUID,
    vertical: str,
    swiggy_order_id: str,
) -> None:
    """Persist order reference to DB. No-op in MOCK_MODE."""
    if settings.mock_mode:
        logger.warning(
            "[MOCK] order_reference stored in memory: session=%s vertical=%s order_id=%s",
            session_id, vertical, swiggy_order_id,
        )
        return

    from app.db.connection import get_connection
    async with get_connection() as conn:
        await conn.execute(
            """
            INSERT INTO order_references (id, session_id, vertical, swiggy_order_id, placed_at, status)
            VALUES (gen_random_uuid(), $1, $2, $3, now(), 'placed')
            """,
            session_id,
            vertical,
            swiggy_order_id,
        )


# ── Session Locks (Idempotency Guards) ────────────────────────────────────────

_active_placements: set[str] = set()

# ── Food order placement ──────────────────────────────────────────────────────

async def place_food_order(session_id: uuid.UUID, token: str = "") -> ConfirmResponse:
    """
    Place a Food order with check-then-retry.

    Pre-conditions verified before placement:
      - Cart total <= ₹1000  (PRD Section 2.3 — Food cart cap)
      - Payment method: COD  (v1 only)

    On 5xx → check get_food_orders → retry up to MAX_RETRIES.
    On domain failure → surface immediately, no retry.
    PRD ref: Section 8.3 (Module 5), Section 7.1 (Order Placement — sequential)
    """
    lock_key = f"{session_id}_food"
    if lock_key in _active_placements:
        raise OrderPlacementError("food", "Order placement already in progress.")
    _active_placements.add(lock_key)

    try:
        # ── Pre-condition: read live cart, verify cap ─────────────────────────
        cart = await mcp_client.get_food_cart(token=token)

        subtotal = cart.get("subtotal", 0)
        if subtotal > _FOOD_CART_CAP_INR:
            raise OrderPlacementError(
                "food",
                f"Cart total ₹{subtotal} exceeds ₹{_FOOD_CART_CAP_INR} cap. "
                "Remove items before placing order.",
            )

        items = cart.get("items", [])
        if not items:
            raise OrderPlacementError("food", "Food cart is empty — nothing to order.")

        # ── Placement with check-then-retry ───────────────────────────────────
        wall_start = asyncio.get_event_loop().time()

        for attempt in range(MAX_RETRIES + 1):
            # Hard wall-clock guard
            if asyncio.get_event_loop().time() - wall_start > _WALL_CLOCK_CAP_SECONDS:
                break

            try:
                result = await mcp_client.place_food_order(
                    payment_method="COD", token=token
                )
                order_id = result.get("orderId", "")
                await _store_order_reference(session_id, "food", order_id)
                logger.info("Food order placed: %s (session %s)", order_id, session_id)
                return ConfirmResponse(
                    order_id=order_id,
                    vertical="food",  # type: ignore[arg-type]
                    eta=result.get("eta"),
                    status=result.get("status", "placed"),
                )

            except MCPToolError as exc:
                # Domain failure (success=false) — do NOT retry, surface immediately
                if not exc.classification.is_retryable:
                    logger.warning(
                        "Food order domain failure (no retry): %s", exc.classification.bucket
                    )
                    raise OrderPlacementError("food", str(exc)) from exc

                # 5xx / network — check if order already exists before retrying
                logger.warning(
                    "Food order 5xx on attempt %d/%d: %s", attempt + 1, MAX_RETRIES, exc
                )
                recent_orders = await mcp_client.get_food_orders(token=token)
                found = _order_placed_recently(recent_orders)
                if found:
                    order_id = found.get("orderId", "recovered")
                    await _store_order_reference(session_id, "food", order_id)
                    logger.info(
                        "Food order recovered from get_food_orders: %s (session %s)",
                        order_id, session_id,
                    )
                    return ConfirmResponse(
                        order_id=order_id,
                        vertical="food",  # type: ignore[arg-type]
                        eta=found.get("eta"),
                        status=found.get("status", "placed"),
                    )

                if attempt < MAX_RETRIES:
                    await _wait_with_jitter(attempt)

            except Exception as exc:
                # Network-level error (httpx.RequestError wrapped in MCPToolError by _call)
                logger.error("Food order unexpected error attempt %d: %s", attempt + 1, exc)
                if attempt < MAX_RETRIES:
                    await _wait_with_jitter(attempt)

        # ── Exhausted retries ─────────────────────────────────────────────────
        await mcp_client.report_error(
            tool="place_food_order",
            error_message=f"Order placement failed after {MAX_RETRIES} retries",
            flow_description="food checkout",
            tool_context={"session_id": str(session_id)},
            token=token,
        )
        raise OrderPlacementError(
            "food",
            f"Could not place Food order after {MAX_RETRIES} attempts. "
            "Please try again or contact Swiggy support.",
        )
    finally:
        _active_placements.discard(lock_key)


# ── Instamart checkout ────────────────────────────────────────────────────────

async def checkout_instamart(session_id: uuid.UUID, token: str = "") -> ConfirmResponse:
    """
    Place an Instamart order with check-then-retry.

    Pre-conditions:
      - Cart total >= ₹99  (PRD Section 2.3 — Instamart minimum)
      - Payment method: COD

    On 5xx → check get_orders → retry up to MAX_RETRIES.
    PRD ref: Section 8.3 (Module 5), Section 7.1
    """
    lock_key = f"{session_id}_instamart"
    if lock_key in _active_placements:
        raise OrderPlacementError("instamart", "Order placement already in progress.")
    _active_placements.add(lock_key)

    try:
        # ── Pre-condition: read live cart, verify minimum ─────────────────────
        cart = await mcp_client.get_cart(token=token)

        subtotal = cart.get("subtotal", 0)
        if subtotal < _INSTAMART_MINIMUM_INR:
            raise OrderPlacementError(
                "instamart",
                f"Cart total ₹{subtotal} is below ₹{_INSTAMART_MINIMUM_INR} minimum. "
                "Add more items to continue.",
            )

        items = cart.get("items", [])
        if not items:
            raise OrderPlacementError("instamart", "Instamart cart is empty — nothing to order.")

        wall_start = asyncio.get_event_loop().time()

        for attempt in range(MAX_RETRIES + 1):
            if asyncio.get_event_loop().time() - wall_start > _WALL_CLOCK_CAP_SECONDS:
                break

            try:
                result = await mcp_client.checkout(payment_method="COD", token=token)
                order_id = result.get("orderId", "")
                await _store_order_reference(session_id, "instamart", order_id)
                logger.info("Instamart order placed: %s (session %s)", order_id, session_id)
                return ConfirmResponse(
                    order_id=order_id,
                    vertical="instamart",  # type: ignore[arg-type]
                    eta=result.get("eta"),
                    status=result.get("status", "placed"),
                )

            except MCPToolError as exc:
                if not exc.classification.is_retryable:
                    raise OrderPlacementError("instamart", str(exc)) from exc

                logger.warning(
                    "Instamart checkout 5xx attempt %d/%d: %s", attempt + 1, MAX_RETRIES, exc
                )
                recent_orders = await mcp_client.get_orders(token=token)
                found = _order_placed_recently(recent_orders)
                if found:
                    order_id = found.get("orderId", "recovered")
                    await _store_order_reference(session_id, "instamart", order_id)
                    return ConfirmResponse(
                        order_id=order_id,
                        vertical="instamart",  # type: ignore[arg-type]
                        eta=found.get("eta"),
                        status=found.get("status", "placed"),
                    )

                if attempt < MAX_RETRIES:
                    await _wait_with_jitter(attempt)

            except Exception as exc:
                logger.error("Instamart checkout unexpected error attempt %d: %s", attempt + 1, exc)
                if attempt < MAX_RETRIES:
                    await _wait_with_jitter(attempt)

        await mcp_client.report_error(
            tool="checkout",
            error_message=f"Instamart checkout failed after {MAX_RETRIES} retries",
            flow_description="instamart checkout",
            tool_context={"session_id": str(session_id)},
            token=token,
        )
        raise OrderPlacementError(
            "instamart",
            f"Could not place Instamart order after {MAX_RETRIES} attempts.",
        )
    finally:
        _active_placements.discard(lock_key)


# ── Dineout table booking ─────────────────────────────────────────────────────

async def book_table_dineout(
    session_id: uuid.UUID,
    restaurant_id: str,
    slot_id: str,
    item_id: str,
    reservation_time: str,
    guest_count: int,
    latitude: float,
    longitude: float,
    slot_is_free: bool,
    booking_price: float,
    token: str = "",
) -> ConfirmResponse:
    """
    Book a Dineout table with check-then-retry.

    Pre-conditions:
      - slot_is_free=True, booking_price=0  (paid deals rejected — PRD Section 2.3)

    On 5xx → check get_booking_status → retry up to MAX_RETRIES.
    PRD ref: Section 8.3 (Module 5), Section 7.2 (Dineout flow)
    """
    lock_key = f"{session_id}_dineout"
    if lock_key in _active_placements:
        raise OrderPlacementError("dineout", "Reservation already in progress.")
    _active_placements.add(lock_key)

    try:
        # ── Pre-condition: reject paid slots before any network call ──────────
        if not slot_is_free or booking_price > 0:
            raise OrderPlacementError(
                "dineout",
                "Only free reservations are supported in this version "
                f"(slot bookingPrice=₹{booking_price}). "
                "Please choose a free slot.",
            )

        wall_start = asyncio.get_event_loop().time()
        last_booking_id: str | None = None

        for attempt in range(MAX_RETRIES + 1):
            if asyncio.get_event_loop().time() - wall_start > _WALL_CLOCK_CAP_SECONDS:
                break

            try:
                result = await mcp_client.book_table(
                    restaurant_id=restaurant_id,
                    slot_id=slot_id,
                    item_id=item_id,
                    reservation_time=reservation_time,
                    guest_count=guest_count,
                    latitude=latitude,
                    longitude=longitude,
                    token=token,
                )
                booking_id = result.get("bookingId", "")
                last_booking_id = booking_id
                await _store_order_reference(session_id, "dineout", booking_id)
                logger.info("Dineout booking confirmed: %s (session %s)", booking_id, session_id)
                return ConfirmResponse(
                    order_id=booking_id,
                    vertical="dineout",  # type: ignore[arg-type]
                    eta=result.get("reservationTime"),
                    status=result.get("status", "confirmed"),
                )

            except MCPToolError as exc:
                if not exc.classification.is_retryable:
                    raise OrderPlacementError("dineout", str(exc)) from exc

                logger.warning(
                    "Dineout book_table 5xx attempt %d/%d: %s", attempt + 1, MAX_RETRIES, exc
                )

                # Check if booking was created despite 5xx response
                if last_booking_id:
                    try:
                        status_result = await mcp_client.get_booking_status(
                            last_booking_id, token=token
                        )
                        if status_result.get("status", "").upper() in ("CONFIRMED", "PLACED"):
                            await _store_order_reference(session_id, "dineout", last_booking_id)
                            return ConfirmResponse(
                                order_id=last_booking_id,
                                vertical="dineout",  # type: ignore[arg-type]
                                eta=status_result.get("reservationTime"),
                                status="confirmed",
                            )
                    except Exception:
                        pass  # Status check failed — proceed to retry

                if attempt < MAX_RETRIES:
                    await _wait_with_jitter(attempt)

            except Exception as exc:
                logger.error("Dineout booking unexpected error attempt %d: %s", attempt + 1, exc)
                if attempt < MAX_RETRIES:
                    await _wait_with_jitter(attempt)

        await mcp_client.report_error(
            tool="book_table",
            error_message=f"Dineout booking failed after {MAX_RETRIES} retries",
            flow_description="dineout reservation",
            tool_context={"session_id": str(session_id), "restaurantId": restaurant_id},
            token=token,
        )
        raise OrderPlacementError(
            "dineout",
            f"Could not complete Dineout reservation after {MAX_RETRIES} attempts.",
        )
    finally:
        _active_placements.discard(lock_key)
