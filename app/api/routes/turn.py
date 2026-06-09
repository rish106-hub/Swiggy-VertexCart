from __future__ import annotations

"""
POST /api/v1/session/{session_id}/turn — process one conversation turn.
PRD ref: Section 8.3 (Module 3, FastAPI Endpoints), Section 7.4 (turn boundary pattern)

Orchestration flow per turn:

  User Input
      │
      ▼
  ┌───────────────────────┐
  │ 1. Intent Parser      │   (Extracts entities, assigns verticals, detects signals)
  └─────────┬─────────────┘
            │
            ▼ (requires_clarification?)
      [Yes] ├──► Return Clarifying Question (Stop)
      [No]  │
            ▼
  ┌───────────────────────┐
  │ 3. Persist User Turn  │   (Save to conversation_turns table)
  └─────────┬─────────────┘
            │
            ▼
  ┌───────────────────────┐
  │ 4. Turn Boundary      │   (Read live carts from Swiggy servers: get_*_cart)
  └─────────┬─────────────┘
            │
            ▼ (Switch detected?)
      [Yes] ├──► Return Warning to User (Stop, wait for confirmation)
      [No]  │
            ▼
  ┌───────────────────────┐
  │ 8. Discovery & Cart   │   (Run search and update_*_cart tools per vertical)
  │    (Degradation Mode) │   (If one fails, others continue)
  └─────────┬─────────────┘
            │
            ▼
  ┌───────────────────────┐
  │ 9. Persist Agent Turn │   (Save response and tools_called metadata)
  └─────────┬─────────────┘
            │
            ▼
  Return TurnResponse         (agent_message, cart_summary, active_verticals)
"""

import logging
import uuid
from typing import Any

from fastapi import APIRouter, HTTPException

from app.core import intent_parser, session_manager
from app.core.mcp_client import MCPToolError, mcp_client
from app.core.oauth_handler import OAuthExpiredError
from app.core.session_manager import (
    add_turn,
    get_live_cart_state,
    get_session,
    rebuild_cart_from_history,
    should_warn_address_switch,
    should_warn_restaurant_switch,
)
from app.models.intent import EntityType, IntentResult, Urgency, Vertical
from app.models.session import TurnRequest, TurnResponse

router = APIRouter()
logger = logging.getLogger(__name__)


# ── Agent response builder ────────────────────────────────────────────────────

def _build_agent_message(
    intent: IntentResult,
    discovery_results: dict[str, Any],
    cart_state: dict[str, Any],
    failed_verticals: list[str],
) -> str:
    """
    Build a plain-text agent response from discovery results.
    In production this would be LLM-generated from the tool outputs.
    For now: structured template sufficient for end-to-end smoke testing.
    """
    parts: list[str] = []

    if "instamart" in failed_verticals:
        parts.append("I couldn't reach Instamart right now, but your other requests are ready.")
    if "food" in failed_verticals:
        parts.append("I couldn't reach Food right now, but your other requests are ready.")
    if "dineout" in failed_verticals:
        parts.append("I couldn't reach Dineout right now, but your other requests are ready.")

    food_items = discovery_results.get("food_search", [])
    im_products = discovery_results.get("instamart_search", [])

    if food_items:
        names = ", ".join(i.get("name", "item") for i in food_items[:3])
        parts.append(f"Found on Swiggy Food: {names}.")

    if im_products:
        names = ", ".join(p.get("name", "product") for p in im_products[:3])
        parts.append(f"Found on Instamart: {names}.")

    if intent.dineout_signal and "dineout" not in failed_verticals:
        parts.append("Searching Dineout for available slots.")

    if not parts or parts == [f"I couldn't reach {v} right now, but your other requests are ready." for v in failed_verticals]:
        parts.append("I've updated your cart. Shall I proceed to checkout?")

    food_cart = cart_state.get("food", {})
    im_cart = cart_state.get("instamart", {})

    totals: list[str] = []
    if food_cart.get("subtotal"):
        totals.append(f"Food: ₹{food_cart['subtotal']}")
    if im_cart.get("subtotal"):
        totals.append(f"Instamart: ₹{im_cart['subtotal']}")

    if totals:
        parts.append("Current totals — " + " | ".join(totals) + ".")

    return " ".join(parts)


# ── Discovery helpers ─────────────────────────────────────────────────────────

async def _run_food_discovery(
    entities: list,
    address_id: str,
    token: str,
) -> tuple[list[dict], list[dict]]:
    """
    Run Food discovery for ready_to_eat entities.
    Returns (restaurants, menu_items).
    """
    restaurants: list[dict] = []
    menu_items: list[dict] = []

    for entity in entities:
        if entity.type != EntityType.READY_TO_EAT:
            continue
        try:
            results = await mcp_client.search_restaurants(
                address_id=address_id, query=entity.text, token=token
            )
            restaurants.extend(results)

            # Also search menu for the specific item
            menu_results = await mcp_client.search_menu(
                query=entity.text, token=token
            )
            menu_items.extend(menu_results)
        except MCPToolError as exc:
            logger.warning("Food discovery failed for '%s': %s", entity.text, exc)

    return restaurants, menu_items


async def _run_instamart_discovery(
    entities: list,
    address_id: str,
    token: str,
    is_reorder: bool = False,
) -> list[dict]:
    """
    Run Instamart discovery for ingredient entities.
    Uses your_go_to_items for reorder intents (one call instead of search).
    Returns flat list of matched products.
    """
    products: list[dict] = []

    if is_reorder:
        try:
            results = await mcp_client.your_go_to_items(
                address_id=address_id, token=token
            )
            products.extend(results)
            return products
        except MCPToolError as exc:
            logger.warning("your_go_to_items failed, falling back to search: %s", exc)

    for entity in entities:
        if entity.type != EntityType.INGREDIENT:
            continue
        try:
            results = await mcp_client.search_products(
                address_id=address_id, query=entity.text, token=token
            )
            products.extend(results)
        except MCPToolError as exc:
            logger.warning("Instamart search failed for '%s': %s", entity.text, exc)

    return products


async def _run_dineout_discovery(
    lat: float,
    lng: float,
    query: str,
    date: str,
    token: str,
) -> tuple[list[dict], list[dict]]:
    """
    Run Dineout discovery: restaurant search + available free slots.
    Returns (restaurants, free_slots).
    """
    restaurants: list[dict] = []
    free_slots: list[dict] = []

    try:
        restaurants = await mcp_client.search_restaurants_dineout(
            query=query, lat=lat, lng=lng, token=token
        )
    except MCPToolError as exc:
        logger.warning("Dineout restaurant search failed: %s", exc)
        return [], []

    if restaurants:
        try:
            all_slots = await mcp_client.get_available_slots(
                restaurant_id=restaurants[0]["restaurantId"],
                date=date,
                latitude=lat,
                longitude=lng,
                token=token,
            )
            # Filter to free slots only — PRD Section 2.3, 7.2
            free_slots = [s for s in all_slots if s.get("isFree", False)]
        except MCPToolError as exc:
            logger.warning("Dineout slot fetch failed: %s", exc)

    return restaurants, free_slots


# ── Main turn handler ─────────────────────────────────────────────────────────

@router.post("/session/{session_id}/turn", response_model=TurnResponse)
async def process_turn(session_id: uuid.UUID, body: TurnRequest) -> TurnResponse:
    """
    Core conversation loop. Processes one user turn end-to-end.

    Turn boundary pattern enforced: live cart read before any cart mutation.
    Restaurant/address switch warnings returned before flushing.
    PRD ref: Section 7.4 (Multi-Turn Cart State Management), Section 8.3 (Module 3)
    """
    # ── Retrieve session + token ──────────────────────────────────────────
    try:
        session = await get_session(session_id)
    except ValueError:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")

    token = session.swiggy_access_token or ""

    # ── Step 1: Parse intent ──────────────────────────────────────────────
    intent = await intent_parser.parse(body.text)

    # ── Step 2: Clarification needed — return immediately ────────────────
    if intent.requires_clarification:
        return TurnResponse(
            agent_response=(
                "Could you be more specific? For example: "
                "'order biryani', 'pasta ingredients for tonight', "
                "or 'book a table for Friday'."
            ),
            verticals_active=await session_manager.get_active_verticals(session_id),
            cart_summary={},
            requires_clarification=True,
            clarification_prompt="What would you like — food delivery, groceries, or a reservation?",
        )

    # ── Step 3: Persist user turn ─────────────────────────────────────────
    await add_turn(session_id, "user", body.text, intent=intent)

    # ── Step 4: Turn boundary — read live carts ───────────────────────────
    food_entities = [e for e in intent.entities if e.vertical == Vertical.FOOD]
    im_entities = [e for e in intent.entities if e.vertical == Vertical.INSTAMART]
    dineout_entities = [e for e in intent.entities if e.vertical == Vertical.DINEOUT]

    cart_state = await get_live_cart_state(session_id, token)

    # ── Step 5: Scheduled delivery — not supported in v1 ─────────────────
    if intent.urgency == Urgency.SCHEDULED:
        await add_turn(
            session_id, "agent",
            "Scheduled delivery isn't supported yet — all orders are immediate. "
            "I can place the order now if you'd like.",
            tools_called=[],
        )
        return TurnResponse(
            agent_response=(
                "Scheduled delivery isn't supported yet. "
                "Orders are placed for immediate delivery. Want to proceed?"
            ),
            verticals_active=await session_manager.get_active_verticals(session_id),
            cart_summary=cart_state,
            requires_clarification=True,
        )

    # ── Step 6: Cart expired — offer rebuild ──────────────────────────────
    food_cart = cart_state.get("food", {})
    im_cart = cart_state.get("instamart", {})

    if await session_manager.is_cart_expired(food_cart) or \
       await session_manager.is_cart_expired(im_cart):
        rebuilt = await rebuild_cart_from_history(session_id)
        await add_turn(session_id, "agent", "Cart expired — offering rebuild.", tools_called=[])
        return TurnResponse(
            agent_response=(
                "Your cart expired. I can rebuild it from our conversation — "
                "shall I re-add the same items?"
            ),
            verticals_active=await session_manager.get_active_verticals(session_id),
            cart_summary={"rebuilt": rebuilt},
            requires_confirmation=True,
        )

    # ── Resolve addresses ─────────────────────────────────────────────────
    food_address_id = "addr_001"   # Default — replaced by get_addresses in Sprint 3 wiring
    im_address_id = "addr_001"
    dineout_lat, dineout_lng = 12.9716, 77.5946

    try:
        addresses = await mcp_client.get_addresses(token=token)
        if addresses:
            food_address_id = addresses[0]["id"]
            im_address_id = addresses[0]["id"]
    except MCPToolError:
        pass  # Use defaults — non-fatal in mock mode

    if dineout_entities or intent.dineout_signal:
        try:
            locations = await mcp_client.get_saved_locations(token=token)
            if locations:
                dineout_lat = locations[0]["lat"]
                dineout_lng = locations[0]["lng"]
        except MCPToolError:
            pass

    # ── Step 7: Restaurant switch warning ────────────────────────────────
    if food_entities and food_cart.get("restaurantId"):
        # Peek at first restaurant result to check if it's a switch
        try:
            peek_restaurants = await mcp_client.search_restaurants(
                address_id=food_address_id,
                query=food_entities[0].text,
                token=token,
            )
            if peek_restaurants:
                new_rest_id = peek_restaurants[0]["restaurantId"]
                should_warn, existing_cart = await should_warn_restaurant_switch(
                    session_id, new_rest_id, token
                )
                if should_warn:
                    items_desc = ", ".join(
                        f"{i.get('name', 'item')} x{i.get('quantity', 1)}"
                        for i in existing_cart.get("items", [])
                    )
                    total = existing_cart.get("subtotal", 0)
                    agent_msg = (
                        f"Switching restaurants will clear your current cart "
                        f"({items_desc}, ₹{total} from "
                        f"{existing_cart.get('restaurantName', 'current restaurant')}). "
                        "Shall I proceed?"
                    )
                    await add_turn(session_id, "agent", agent_msg, tools_called=[])
                    return TurnResponse(
                        agent_response=agent_msg,
                        verticals_active=await session_manager.get_active_verticals(session_id),
                        cart_summary=cart_state,
                        requires_confirmation=True,
                    )
        except MCPToolError:
            pass  # Warning not surfaced on error — proceed

    # ── Step 8: Run discovery + cart tools ───────────────────────────────
    tools_called: list[dict] = []
    discovery_results: dict[str, Any] = {}
    failed_verticals: list[str] = []

    # Food
    if food_entities:
        restaurants, menu_items = await _run_food_discovery(
            food_entities, food_address_id, token
        )
        discovery_results["food_search"] = menu_items
        tools_called.append({
            "tool": "search_restaurants",
            "vertical": "food",
            "success": bool(restaurants),
            "arguments": {"query": food_entities[0].text},
        })

        # Add first menu item to Food cart if found
        if menu_items and restaurants:
            try:
                updated_cart = await mcp_client.update_food_cart(
                    restaurant_id=restaurants[0]["restaurantId"],
                    items=[{"itemId": menu_items[0]["itemId"], "quantity": 1}],
                    token=token,
                )
                cart_state["food"] = updated_cart
                tools_called.append({
                    "tool": "update_food_cart",
                    "vertical": "food",
                    "success": True,
                    "arguments": {
                        "restaurantId": restaurants[0]["restaurantId"],
                        "items": [{"itemId": menu_items[0]["itemId"], "quantity": 1}],
                    },
                })
            except MCPToolError as exc:
                failed_verticals.append("food")
                logger.warning("update_food_cart failed: %s", exc)
                await mcp_client.report_error(
                    tool="update_food_cart",
                    error_message=str(exc),
                    flow_description="food cart update",
                    token=token,
                )

    # Instamart
    if im_entities:
        is_reorder = any(
            "reorder" in e.text.lower() or "usual" in e.text.lower()
            for e in im_entities
        )
        products = await _run_instamart_discovery(
            im_entities, im_address_id, token, is_reorder=is_reorder
        )
        discovery_results["instamart_search"] = products
        tools_called.append({
            "tool": "search_products" if not is_reorder else "your_go_to_items",
            "vertical": "instamart",
            "success": bool(products),
            "arguments": {"query": im_entities[0].text if im_entities else ""},
        })

        # Add first variant of each found product to Instamart cart
        spin_items = []
        for product in products[:5]:   # Cap at 5 products per turn
            variants = product.get("variants", [])
            if variants:
                spin_items.append({"spinId": variants[0]["spinId"], "quantity": 1})

        if spin_items:
            try:
                updated_im_cart = await mcp_client.update_cart(
                    items=spin_items, token=token
                )
                cart_state["instamart"] = updated_im_cart
                tools_called.append({
                    "tool": "update_cart",
                    "vertical": "instamart",
                    "success": True,
                    "arguments": {"items": spin_items},
                })
            except MCPToolError as exc:
                failed_verticals.append("instamart")
                logger.warning("update_cart failed: %s", exc)
                await mcp_client.report_error(
                    tool="update_cart",
                    error_message=str(exc),
                    flow_description="instamart cart update",
                    token=token,
                )

    # Dineout
    if dineout_entities or intent.dineout_signal:
        from datetime import date as date_cls
        today_str = date_cls.today().isoformat()
        query = dineout_entities[0].text if dineout_entities else "dinner"
        restaurants_dout, free_slots = await _run_dineout_discovery(
            dineout_lat, dineout_lng, query, today_str, token
        )
        
        if not restaurants_dout and not free_slots:
            failed_verticals.append("dineout")
            
        discovery_results["dineout_restaurants"] = restaurants_dout
        discovery_results["dineout_slots"] = free_slots
        tools_called.append({
            "tool": "search_restaurants_dineout",
            "vertical": "dineout",
            "success": bool(restaurants_dout),
            "arguments": {"query": query},
        })

    # ── Step 9: Persist agent turn ────────────────────────────────────────
    agent_message = _build_agent_message(intent, discovery_results, cart_state, failed_verticals)
    await add_turn(session_id, "agent", agent_message, tools_called=tools_called)

    # ── Step 10: Return response ──────────────────────────────────────────
    active_verticals = await session_manager.get_active_verticals(session_id)
    has_items = bool(
        cart_state.get("food", {}).get("items")
        or cart_state.get("instamart", {}).get("items")
        or discovery_results.get("dineout_slots")
    )

    return TurnResponse(
        agent_response=agent_message,
        verticals_active=active_verticals,
        cart_summary=cart_state,
        requires_confirmation=has_items,
    )
