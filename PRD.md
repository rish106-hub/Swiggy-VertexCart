# VertexCart — Product Requirements Document
**Version:** 2.0 (Restructured per Swiggy MCP Builders Club documentation)
**Author:** Rishav
**Status:** Active
**Last Updated:** June 2026
**Based on:** https://mcp.swiggy.com/builders/ (v1.0 — April 2026 launch)

---

## IMPORTANT: What Changed in v2.0

The original PRD made several technically incorrect assumptions about the Swiggy MCP platform. This version corrects all of them based on actual Swiggy Builders Club documentation. The product concept is the same. The architecture is not.

**What was wrong:**
- "One unified checkout" — does not exist. Each vertical has its own checkout call.
- "Local basket builder maintaining cart state" — wrong. All cart state lives server-side.
- "Swiggy One Eligibility Engine" — no such tool exists in the 35-tool catalog.
- ₹1000 food cart cap was not acknowledged.
- COD-only constraint was not acknowledged.
- Dineout-only-free-reservations was not acknowledged.
- OAuth 2.1 PKCE was not properly scoped as an engineering requirement.

---

## 1. What We're Building

VertexCart is a conversational commerce agent built on top of Swiggy's 35-tool MCP stack (Food, Instamart, Dineout). The user describes what they want in natural language. VertexCart figures out which verticals to engage, orchestrates the right tool calls across Swiggy's three MCP servers, and guides the user through a single conversational session that ends in real orders — across multiple Swiggy verticals, in sequence, without switching tabs.

The user says one thing. VertexCart calls the right tools. Orders happen.

**What VertexCart is not:** A unified checkout button. A local basket system. A Swiggy clone. It is an agent layer on top of Swiggy's existing MCP infrastructure that makes cross-vertical ordering feel like one conversation.

---

## 2. Platform Overview (Actual, Not Assumed)

### 2.1 MCP Servers Available

| Server | Endpoint | Tools | v1 Status |
|---|---|---|---|
| Food | `mcp.swiggy.com/food` | 14 tools | Live |
| Instamart | `mcp.swiggy.com/im` | 13 tools | Live |
| Dineout | `mcp.swiggy.com/dineout` | 8 tools | Live |

One OAuth token works across all three servers.  
Carts are per-server — Food cart and Instamart cart are independent.  
Orders are per-server — `get_food_orders` won't show Instamart orders.

### 2.2 Complete Tool Catalog

**Food (14 tools)**

| Tool | Stage | Mutating? |
|---|---|---|
| `get_addresses` | Setup | No |
| `search_restaurants` | Discover | No |
| `get_restaurant_menu` | Discover | No |
| `search_menu` | Discover | No |
| `update_food_cart` | Cart | Yes |
| `get_food_cart` | Cart | No |
| `flush_food_cart` | Cart | Yes |
| `fetch_food_coupons` | Cart | No |
| `apply_food_coupon` | Cart | Yes |
| `place_food_order` | Order | Yes (non-idempotent) |
| `get_food_orders` | Manage | No |
| `track_food_order` | Manage | No |
| `search_menu` | Discover | No |
| `report_error` | Support | Yes |

**Instamart (13 tools)**

| Tool | Stage | Mutating? |
|---|---|---|
| `get_addresses` | Setup | No |
| `search_products` | Discover | No |
| `your_go_to_items` | Discover | No |
| `update_cart` | Cart | Yes |
| `get_cart` | Cart | No |
| `clear_cart` | Cart | Yes |
| `create_address` | Setup | Yes |
| `checkout` | Order | Yes (non-idempotent) |
| `get_orders` | Manage | No |
| `track_order` | Manage | No |
| `report_error` | Support | Yes |

**Dineout (8 tools)**

| Tool | Stage | Mutating? |
|---|---|---|
| `get_saved_locations` | Find | No |
| `search_restaurants_dineout` | Find | No |
| `get_restaurant_details` | Find | No |
| `get_available_slots` | Reserve | No |
| `create_cart` | Reserve | Yes |
| `book_table` | Reserve | Yes (non-idempotent) |
| `get_booking_status` | Manage | No |
| `report_error` | Support | Yes |

### 2.3 Hard Constraints (v1 — Non-Negotiable)

These are platform-level constraints. VertexCart must design around them, not work against them.

| Constraint | Detail |
|---|---|
| Payment method | COD only. No online/card payments in v1. |
| Food cart cap | ₹1000 max per order for Builders Club origin orders. |
| Instamart minimum | ₹99 minimum cart value. |
| Food cart binding | One restaurant per cart. Switching restaurant flushes the cart. |
| Instamart cart binding | One delivery address per cart. Address change requires `clear_cart` first. |
| Dineout reservations | Free reservations only (`isFree=true`, `bookingPrice=0`). Paid deals are rejected. |
| Scheduled delivery | Not supported. `place_food_order` is immediate delivery only. |
| Cart state | Server-side only. No local cart caching. Always `get_*_cart` before mutating. |
| Checkout | Per-server. No single unified checkout. Three separate order placement calls. |
| Authentication | OAuth 2.1 with PKCE (S256). JWT access tokens, 5-day lifetime. No refresh tokens in v1. |
| Widgets | Designed but NOT live in v1. iframe layer shipping in v1.1. Frontend must build its own UI. |
| Error codes | Symbolic `error.code` not emitted in v1. Classify by `error.message` text + HTTP status. |
| Data residency | India only (AWS Mumbai primary, AWS Singapore failover). |

### 2.4 Address Scope Difference (Important)

Food and Dineout use different address systems:

- **Food**: Uses `addressId` from `get_addresses` tool
- **Dineout**: Uses lat/lng from `get_saved_locations` tool

These are not interchangeable. Never pass a Food `addressId` to a Dineout search. The agent must handle this context switch.

---

## 3. North Star

**"One intent. Multiple verticals. One session."**

**North Star Metric:** Cross-vertical sessions completed per active user per month (CVS/user/month)

This captures the behavioral change needed — users actually completing orders across 2+ verticals in one conversation. GOV and One upgrades follow when this metric moves.

**Leading Indicator:** Intent-to-multi-vertical-order completion rate (user states intent → agent successfully places orders across 2+ servers in one session)

**Lagging Indicator:** Cross-vertical GOV per session (monetization signal once behavior is established)

---

## 4. Problem Statement

Swiggy has three live MCP servers. Users use one. The product experience does not make cross-vertical ordering feel natural.

The gap is not the API — the API exists and works. The gap is the UX layer: nobody has built a conversational agent that takes "I'm making pasta tonight and want to order dessert" and converts it into simultaneous Instamart + Food tool calls that result in two real orders in one session.

Swiggy's own "Plan my evening" recipe (in their official combined recipe docs) does exactly this — but as a reference pattern, not a shipped product. VertexCart ships it as a product.

**What Zomato does:** Passive cross-promotion banners. No agent. No unified session. No combined cart flow.

---

## 5. Ideal Customer Profile

**Primary ICP — The Convenience-First Urban Professional**

- Age: 24–34
- City: Tier 1 (Mumbai, Bengaluru, Delhi NCR, Hyderabad, Pune)
- Income: ₹8–30L per annum
- Living situation: 1–2 person urban household
- Swiggy behavior: 3+ food orders/week. Uses Instamart for top-ups. Uses Dineout 2–3x/month.
- Has Swiggy One or is close to getting it
- Pain: switching between app sections for a single evening plan feels like unnecessary work
- Will pay for convenience, not for complexity

**Secondary ICP — The Weekend Social Planner**

- Plans meals or outings for groups of 2–4
- Uses Instamart for cooking ingredients on weekends
- Uses Dineout for dinner reservations
- Occasion-driven: weekends, dates, small gatherings
- VertexCart adds value by building a "full evening plan" from one prompt

**Non-ICP (excluded):**
- Bulk grocery shoppers (Instamart is a top-up layer for VertexCart, not a weekly store)
- Users with fewer than 3 Swiggy orders per month
- Users outside Tier 1 (Instamart + Dineout coverage is thin)
- Users who primarily pay online (COD-only is a v1 constraint that may friction them)

---

## 6. Objectives and Key Results

**OKR 1 — Cross-Vertical Behavior**
- KR1: 25% cross-vertical session rate within 90 days (baseline ~8%)
- KR2: 40% of users who complete one cross-vertical session repeat within 14 days
- KR3: Intent-to-multi-server-order completion rate >55% in first 30 days

**OKR 2 — GOV Lift (Within Platform Constraints)**
- KR1: Average cross-vertical session GOV >₹550 (vs ₹280 food-only baseline) — note: Food capped at ₹1000 per order in v1, so combined sessions of ₹300 food + ₹400 Instamart are realistic targets
- KR2: Instamart attach rate on food-intent sessions >30%
- KR3: Dineout reservation attach rate on weekend evening sessions >20%

**OKR 3 — Product Experience**
- KR1: User completes intent-to-first-order in <5 conversational turns
- KR2: Agent response latency <2.5s per turn (tool calls + LLM inference)
- KR3: Cart abandonment rate <30% after basket confirmation screen

**OKR 4 — Platform Compliance**
- KR1: Zero order placements without user confirmation step
- KR2: Zero instances of cart state mismatch between agent display and Swiggy server
- KR3: `report_error` called on 100% of tool failures that reach the user

---

## 7. Product Flow (Corrected for Actual API Behavior)

### 7.1 Core User Journey

The key change from v1.0 PRD: there is no "unified checkout." There are sequential order placements per vertical, each requiring user confirmation before the mutating call.

```
User inputs intent
("I'm making pasta tonight and want to order tiramisu for dessert")
        |
        v
Intent Parser (Claude / LLM)
 - Extracts entities: pasta ingredients → Instamart, tiramisu → Food
 - Classifies occasion: weeknight dinner
 - Identifies dineout signal: none
 - Returns structured intent with vertical assignments
        |
        v
Address Resolution (parallel read calls — safe to run together)
 - get_addresses (Food) → home addressId
 - get_saved_locations (Dineout) → lat/lng (only if dineout signal detected)
        |
        v
Product Discovery (sequential, per vertical)
 - Instamart: search_products for each ingredient entity
   → Results include spinId (variant-level ID, required for cart)
 - Food: search_restaurants for tiramisu near addressId
   → Results include restaurantId, availabilityStatus
        |
        v
Agent presents results to user
"Found pasta ingredients on Instamart (₹380, ~12 min).
 Tiramisu available from Smoke House Deli on Food (₹320, ~35 min).
 Want me to add both?"
        |
        v
User confirms
        |
        v
Cart Building (sequential, server-side)
 - Instamart: update_cart with spinIds and quantities
   → Server creates/updates Instamart cart
 - Food: update_food_cart with itemId and restaurantId
   → Server creates/updates Food cart
   → Note: Food cart now bound to Smoke House Deli
 - Verify carts: get_cart (Instamart) + get_food_cart (Food)
        |
        v
Coupon Check (optional)
 - Food: fetch_food_coupons → filter to COD-compatible only
 - If applicable: apply_food_coupon
        |
        v
Pre-order Confirmation Screen
 Agent shows:
  INSTAMART: [items] — ₹380 total — ~12 min
  SWIGGY FOOD: [tiramisu] — ₹320 total — ~35 min (COD)
  COMBINED: ₹700
 "Confirm Instamart order?" → User: Yes
 "Confirm Food order?" → User: Yes
        |
        v
Order Placement (sequential, non-idempotent — must confirm before each)
 - checkout (Instamart) → instamart_order_id
   → On 5xx: call get_orders before retrying
 - place_food_order (Food, COD) → food_order_id
   → On 5xx: call get_food_orders before retrying
        |
        v
Confirmation + Tracking
 - Agent shows both order IDs and ETAs
 - track_order (Instamart) + track_food_order (Food) — poll max every 10s
```

### 7.2 Dineout Flow (Weekend Variant)

Triggered when intent contains dineout signal ("book a table," "dinner out," "restaurant for Friday").

Constraint: Only free reservations supported. Agent must filter to `isFree=true` deals.

```
get_saved_locations → lat/lng
        |
        v
search_restaurants_dineout (query, lat/lng, entityType if applicable)
        |
        v
get_restaurant_details (for top 2 results)
        |
        v
get_available_slots (date, guestCount, lat/lng)
 → Returns 7-day forward availability in breakfast/lunch/dinner bands
 → Filter: show only isFree=true slots
        |
        v
Agent presents free slot options to user
        |
        v
User selects slot
        |
        v
book_table (restaurantId, slotId, itemId, reservationTime, guestCount, lat, lng)
 → Non-idempotent: if 5xx, call get_booking_status before retrying
        |
        v
get_booking_status → confirmation number + restaurant address
```

### 7.3 Combined Flow (Dineout + Food in One Session)

Based on Swiggy's own "Plan my evening" reference recipe. Confirmed pattern for the platform.

The agent handles Food and Dineout flows sequentially: reservation first (user needs to see slot options early), Food delivery second. Same OAuth session covers both servers.

Key gotcha from docs: `place_food_order` is immediate delivery only. If user wants "dessert at 10pm after dinner out," the agent cannot schedule this in v1. Agent must prompt the user at the right time to place the order, or clearly communicate this limitation upfront.

### 7.4 Multi-Turn Cart State Management

This is a critical agent behavior requirement from Swiggy's documentation.

**Rules:**
1. Never cache cart state between turns. Always call `get_*_cart` at the start of any turn that might touch the cart.
2. Detect restaurant switch early — warn user before `update_food_cart` flushes their Food cart.
3. Detect address switch early for Instamart — run `clear_cart` before changing address, not after.
4. Call `get_food_cart` immediately before `place_food_order`. User may have edited in the Swiggy app between agent turns.

```
Turn 1: User: "Add chicken biryani"
Agent: [update_food_cart(add biryani)] → "Added chicken biryani (₹349). Anything else?"

Turn 2: User: "Make it 2"
Agent: [get_food_cart → sees 1 biryani]
       [update_food_cart(set quantity 2)] → "2 biryanis (₹698). Anything else?"

Turn 3: User: "Also order pasta from Punjab Grill"
Agent: [get_food_cart → sees Biryani House cart]
       "That will clear your Biryani House cart (2 biryanis, ₹698). Continue?" ← MUST surface this
```

### 7.5 Intent Classification Matrix

| User Says | Classified As | Vertical | Tool Path |
|---|---|---|---|
| "pasta ingredients" | Ingredient | Instamart | search_products → update_cart |
| "order tiramisu" | Ready-to-eat | Food | search_restaurants → update_food_cart |
| "book a table for Friday" | Reservation | Dineout | get_saved_locations → search_restaurants_dineout → get_available_slots → book_table |
| "coffee and croissant at home" | Ready-to-eat | Food | search_restaurants → update_food_cart |
| "reorder my usual groceries" | Reorder | Instamart | your_go_to_items → update_cart (1 call instead of search) |
| "dinner tonight, fancy" | Ambiguous | Ask | Agent asks: cook / order in / go out? |
| "something sweet" | Ambiguous | Ask | Agent asks: delivered (Food) or from Instamart? |

### 7.6 Edge Cases

1. **Restaurant switch during Food flow** — Agent warns before flushing cart. Shows what will be lost.
2. **Instamart item out of stock** — Flag item as unavailable. Continue with rest of order. Do not drop silently.
3. **Dineout slot unavailable** — Refetch `get_available_slots`, offer alternatives.
4. **Food cart hits ₹1000 cap** — Agent surfaces this before the user picks the 8th item. "Cart limit reached (₹1000 for this session). Want to remove something?"
5. **Instamart under ₹99** — Prompt user to add items to meet minimum.
6. **5xx on order placement** — Check-then-retry pattern (not blind retry). Call `get_*_orders` to verify before retrying.
7. **OAuth expiry mid-session** — Re-run OAuth flow once. Update bearer for all three servers. Retry.
8. **Stale cart on return** — If cart returns `CART_EXPIRED`, re-fetch, rebuild, confirm with user before re-adding items.
9. **User wants scheduled delivery** — Not supported in v1. Agent informs user clearly. Does not attempt to schedule.

---

## 8. Technical Architecture (Corrected)

### 8.1 What VertexCart Actually Builds

VertexCart is NOT a layer that rebuilds Swiggy's commerce infrastructure. It is an agent that orchestrates Swiggy's existing 35 tools through the MCP protocol. The architecture reflects this.

```
Frontend (React/Next.js + Framer Motion)
    |
    v
VertexCart Backend (FastAPI — Python)
    |
    ├── Intent Parser (Claude via Anthropic API)
    ├── OAuth 2.1 PKCE Handler (Swiggy auth flow)
    ├── Multi-Turn Session Manager (conversation history + turn logic)
    ├── MCP Client (calls Swiggy's 35 tools via streamable HTTP)
    │       ├── mcp.swiggy.com/food
    │       ├── mcp.swiggy.com/im
    │       └── mcp.swiggy.com/dineout
    ├── Cart State Reader (get_*_cart calls — server is authoritative)
    ├── Order Placement Orchestrator (with non-idempotency guards)
    └── Error Classifier (message-based in v1, no symbolic codes yet)
    |
    v
PostgreSQL (sessions, conversation history, order references)
```

### 8.2 Actual Technical Stack

| Layer | Technology | Reason |
|---|---|---|
| Backend | FastAPI (Python 3.11+) | Async, fast, aligns with MCP's streamable HTTP model |
| MCP Client | httpx AsyncClient | Direct streamable HTTP calls to Swiggy endpoints |
| LLM (Intent) | Claude claude-haiku-4-5 via Anthropic API | Low latency for turn-by-turn intent parsing |
| Auth | OAuth 2.1 PKCE (S256) | Required by Swiggy platform |
| DB | PostgreSQL via asyncpg | Session storage, conversation logs, order references |
| Frontend | Next.js 14 + Tailwind + Framer Motion | App Router, dark UI, animation |
| Colors | Swiggy orange `#FF5200` | Required by Swiggy co-branding guidelines |

### 8.3 Core Backend Modules

**Module 1: Intent Parser**

Input: Raw user text  
Output: Structured intent JSON with entity classifications and vertical assignments  
Model: `claude-haiku-4-5-20251001` for speed  

```json
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
```

**Module 2: OAuth 2.1 PKCE Handler**

Manages Swiggy OAuth flow:
- Generates code_verifier + code_challenge (S256)
- Handles authorization code exchange
- Stores JWT access tokens (5-day lifetime)
- Detects expiry: re-initiates OAuth flow on 401 / JSON-RPC -32001
- No refresh token in v1 — full re-auth required on expiry

Single token covers all three MCP servers.

**Module 3: Multi-Turn Session Manager**

- Stores conversation history per session (user turns + agent responses)
- Tracks which verticals have been engaged in the current session
- Tracks current cart state references per vertical (read from server, not stored locally)
- Handles correction turns: re-parses user correction, identifies affected vertical, calls only relevant tools
- Manages the "turn boundary" pattern: `get_*_cart` at start of any cart-touching turn

**Module 4: MCP Client**

Direct streamable HTTP calls to Swiggy endpoints. No custom orchestration framework needed — the MCP spec is the interface.

Per-call behavior:
- Auth: Bearer token in header
- Request: JSON-RPC 2.0 `tools/call` method
- Response: parse `success` boolean first, then `data` or `error.message`
- Error classification (v1): HTTP status + `error.message` text (no `error.code` in v1)

Tool call retry policy:
- Read tools: always safe to retry with backoff
- Cart mutations (`update_*_cart`, `clear_cart`): safe to retry (server is idempotent on session)
- Order placement (`place_food_order`, `checkout`, `book_table`): check-then-retry, never blind retry
- Backoff: 500ms → 1s → 2s → 4s, max 5 retries, cap 30s total wall-clock time

**Module 5: Order Placement Orchestrator**

Handles non-idempotent order calls with the check-then-retry pattern:

```
On place_food_order 5xx:
  1. Wait 2-5 seconds
  2. Call get_food_orders
  3. If order found → treat as success, return order details
  4. If not found → retry place_food_order
  5. After 3 retries with no confirmation → surface error to user, call report_error
```

Same pattern for `checkout` (Instamart) and `book_table` (Dineout).

**Module 6: Error Classifier (v1)**

Since symbolic `error.code` is not emitted in v1, classify by HTTP status + message text:

| Bucket | Detection | Action |
|---|---|---|
| Auth failure | HTTP 401 or JSON-RPC -32001 | Re-run OAuth flow |
| Bad input | HTTP 400 + message "Invalid..." / "Missing..." | Fix args, do not retry |
| Upstream timeout | HTTP 504 or message contains "timeout" | Exponential backoff, max 5 retries |
| Upstream error | HTTP 502/503 | Exponential backoff, max 5 retries |
| Domain failure | HTTP 200 + success:false | Surface to user, do not retry. Call report_error if user wants to report. |
| Food: restaurant closed | success:false, message "restaurant closed" | Re-run search_restaurants |
| Food: cart cap exceeded | success:false, message "₹1000" | Prompt user to reduce items |
| Instamart: out of stock | success:false | Suggest alternatives via search_products |
| Instamart: address not serviceable | success:false | Offer alternative address or pivot to Food |
| Instamart: minimum not met | success:false | Prompt user to add items |
| Dineout: slot unavailable | success:false | Refetch get_available_slots |

**Module 7: FastAPI Endpoints**

```
POST /api/v1/intent                    → Parse user text, return intent classification
POST /api/v1/session                   → Create new session, return session_id
POST /api/v1/session/{id}/turn         → Process a conversation turn (core orchestration loop)
GET  /api/v1/session/{id}/cart         → Read current cart state from Swiggy servers (live read)
POST /api/v1/session/{id}/confirm      → User confirms order — trigger order placement sequence
GET  /api/v1/session/{id}/orders       → Return placed order references for tracking
GET  /health                           → Health check
POST /api/v1/auth/callback             → OAuth 2.1 PKCE callback handler
```

Note: No `/basket/build` endpoint. No local basket object. Cart state is always read from Swiggy servers.

**Module 8: Database Schema**

```sql
-- Sessions
CREATE TABLE sessions (
  id UUID PRIMARY KEY,
  user_id VARCHAR NOT NULL,
  swiggy_access_token TEXT,
  token_expires_at TIMESTAMP,
  created_at TIMESTAMP DEFAULT now(),
  last_active_at TIMESTAMP
);

-- Conversation turns
CREATE TABLE conversation_turns (
  id UUID PRIMARY KEY,
  session_id UUID REFERENCES sessions(id),
  turn_number INTEGER,
  role VARCHAR CHECK (role IN ('user', 'agent')),
  content TEXT,
  intent JSONB,
  tools_called JSONB,
  created_at TIMESTAMP DEFAULT now()
);

-- Order references (not order data — Swiggy owns the order)
CREATE TABLE order_references (
  id UUID PRIMARY KEY,
  session_id UUID REFERENCES sessions(id),
  vertical VARCHAR CHECK (vertical IN ('food', 'instamart', 'dineout')),
  swiggy_order_id VARCHAR,
  placed_at TIMESTAMP DEFAULT now(),
  status VARCHAR DEFAULT 'placed'
);

-- No "baskets" table — cart state lives on Swiggy's servers, not ours
```

### 8.4 What VertexCart Does NOT Build

- Local cart storage (server-side on Swiggy)
- Payment processing (COD handled by Swiggy)
- Order fulfillment logic (Swiggy's responsibility)
- Swiggy One integration (no API tool available in v1)
- Scheduled delivery (not supported in v1)
- Widget rendering (Swiggy widgets not live in v1 — build custom UI from tool response data)

---

## 9. Frontend Requirements

This is the tool UI — the surface users interact with. NOT a landing page.

### 9.1 Tech Stack

Next.js 14 (App Router), TypeScript, Tailwind CSS, Framer Motion. No component libraries.

### 9.2 Color System (Per Swiggy Co-branding Guidelines)

- Swiggy Orange: `#FF5200` (use only with "Powered by Swiggy" attribution)
- Background: `#0D0D0D` (dark mode only in v1)
- Surface: `#1A1A1A`
- Surface elevated: `#242424`
- Text primary: `#FFFFFF`
- Text secondary: `#A0A0A0`
- Instamart accent: `#00B383` (green)
- Dineout accent: `#8B5CF6` (purple)

Must display "Powered by Swiggy" per co-branding requirements.

### 9.3 Screens

**Screen 1: Intent Input**
- Full-screen, dark background
- Wide pill-shaped input bar
- Placeholder: "Tell me what you're planning tonight..."
- 3 example intent chips below input
- Animations: headline fade-in, input slide-up on load, chip hover scale

**Screen 2: Parsing / Tool Call State**
- Animated lanes showing which verticals are being queried
- Instamart (green), Food (orange), Dineout (purple)
- Items animate into their respective lanes as tool responses arrive
- Skeleton loader if backend takes >1.5s

**Screen 3: Agent Response + Cart Preview**
- Split vertical columns (only render columns with items)
- Per column: vertical name, items, prices, ETA badge
- Important: this shows what's been QUEUED, not what's been ordered (cart is server-side)
- Agent reasoning panel: collapsible sidebar showing intent classifications
- User can correct agent here ("actually get pasta from Food too")

**Screen 4: Confirmation Screen**
- Two separate confirmation prompts, presented sequentially (one per vertical)
- Platform constraint: cannot confirm all in one button — each order placement is a separate non-idempotent call requiring explicit user intent
- Shows cart from Swiggy server (live `get_*_cart` call) before each confirm
- "Powered by Swiggy" badge

**Screen 5: Order Status**
- Both order IDs displayed
- ETAs from tracking calls
- Poll tracking every 10s (platform guidance)

### 9.4 Swiggy Widgets Note

Swiggy's native widget system (restaurant cards, menu items, cart widgets via iframe) is not live in v1.0. It ships in v1.1. Build custom UI components from raw tool response data. Wire the iframe integration when v1.1 ships — the postMessage contract is documented and stable.

---

## 10. Access Requirements and Application

VertexCart applies under the Developer track at mcp.swiggy.com/builders/access.

**What the application needs:**
1. Who we are: individual developer project / student hackathon
2. What we're building: cross-vertical conversational commerce agent on Food + Instamart + Dineout MCPs
3. Integration architecture: FastAPI backend → Swiggy MCP tools via OAuth 2.1 PKCE → Next.js frontend
4. Redirect URIs: HTTPS for production, `http://localhost` for local dev
5. Static IPs or gateway IPs: backend hosting provider's egress IPs
6. Security contact
7. Data handling declaration: no PII storage beyond session duration, no analytics use of Swiggy data
8. Acknowledgement of MCP terms

**What we must NOT do per ground rules:**
- Resell or share MCP access
- Build aggregation layers that hide Swiggy brand
- Misrepresent prices, availability, or delivery times
- Use for competitive intelligence
- Scrape beyond API scope
- Dark patterns or deceptive UX
- Build fake traffic

**Build locally first.** Per Swiggy's docs: no credentials needed until production. Build against `localhost` mock, record a video of a working flow, include in application. This is the fastest path to production credentials.

---

## 11. Compliance and Data Handling

Per Swiggy MCP documentation:

- Swiggy is the Data Fiduciary under DPDP 2023. VertexCart acts as a Data Processor within Swiggy's permitted scope.
- Swiggy-originated data (addresses, orders, restaurant data) may ONLY be used to serve the user's immediate task.
- Cannot use Swiggy data for analytics, advertising, or model training without separate explicit user consent.
- Must hash user IDs at rest (not plaintext) unless specific lawful basis exists.
- Log session IDs for debugging, not full request/response bodies.
- If a user requests data deletion: direct to Swiggy app for Swiggy-originated data.
- If VertexCart's inference runs outside India: requires signed Data Processing Agreement with Swiggy before production.

---

## 12. Competitive Positioning

| Capability | VertexCart | Zomato/Blinkit |
|---|---|---|
| Conversational intent parsing | Yes | No |
| Cross-vertical session in one conversation | Yes | No |
| Multi-server tool orchestration | Yes | No |
| Agent-driven order flow | Yes | No |
| Dineout + Food in one session | Yes | No |
| Swiggy MCP native | Yes | N/A |

---

## 13. Swiggy One (Deferred to v2)

Swiggy One membership benefits are NOT available as an API tool in v1. There is no `get_swiggy_one_status` or savings calculation tool in the 35-tool catalog.

v2 plan: If Swiggy exposes Swiggy One status as part of enterprise/partner API access, add:
- Membership status check before order confirmation
- Savings calculation display
- Upgrade CTA if savings exceed threshold

For v1: Remove all Swiggy One references from the product UI. Do not promise savings that cannot be verified via API.

---

## 14. Success Definition at 90 Days

VertexCart is successful if:
1. CVS/user/month reaches 2+ for engaged users (baseline: 0)
2. Average cross-vertical session GOV exceeds ₹500 (acknowledging ₹1000 Food cap constraint)
3. Intent-to-multi-order completion rate >50%
4. Agent response latency consistently <2.5s
5. Zero order placement errors due to cart state mismatch
6. Application accepted by Swiggy Builders Club

---

## 15. v1 Known Limitations (Honest)

| Limitation | Impact | Resolution |
|---|---|---|
| COD only | Segments out users who prefer online payment | Resolved in Swiggy v2 (online payment roadmap) |
| ₹1000 Food cap | Caps upsell potential on Food vertical | Builders Club constraint — negotiate higher cap at enterprise tier |
| No scheduled delivery | "Dessert at 10pm" flow not possible | Agent must prompt user at the right time, cannot automate |
| No unified checkout | Two confirmation taps (one per vertical) instead of one | Unavoidable in v1 — reframe as "each order confirmed separately for safety" |
| Free Dineout only | Premium restaurant reservations not bookable | Paid reservations in Swiggy roadmap |
| No Swiggy One API | Can't show membership savings | v2 feature, needs partner-level API access |
| No refresh tokens | OAuth re-auth on token expiry | Swiggy v1.1 roadmap adds refresh tokens |
| No widget iframes | Must build custom restaurant/product cards | Swiggy v1.1 ships hosted widget layer |