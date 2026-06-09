# VertexCart — CLI to CLI Task List (v2.0)
**Restructured per Swiggy MCP Builders Club actual documentation**
**Build Sequence:** Sequential only

---

## What Changed from v1.0

The original CLI task list had you building a custom basket builder and cart state manager. That was wrong. Swiggy maintains cart state server-side. You do not build a basket object — you read it from Swiggy with `get_*_cart` calls.

The corrected task list reflects:
- OAuth 2.1 PKCE flow as a required Phase 1 module
- Multi-turn session management (not a basket builder)
- Check-then-retry pattern for non-idempotent order tools
- Error classification by `error.message` text (no symbolic codes in v1)
- Frontend pulls data from live Swiggy tool responses, not a local basket object
- Actual tool names from the 35-tool catalog

---

## Phase Overview

```
Phase 1 → Claude Code      Intent parser, OAuth, session manager, MCP client, order orchestrator, FastAPI routes, DB schema
Phase 2 → Gemini CLI       Next.js frontend — conversational UI, cart preview, confirmation screens, animations
Phase 3 → Claude Code      API wiring, contract alignment, CORS, end-to-end smoke test
Phase 4 → Copilot CLI      Debugging, integration tests, edge case coverage, non-idempotency guard tests
Phase 5 → Devin CLI        Alembic migrations, connection pooling, session persistence, query optimization
Phase 6 → Kiro CLI         Multi-turn orchestration refinement, retry loop tuning, error recovery flows
```

---

## PHASE 1 — Claude Code: Backend

### What Claude Code Builds

- Project scaffolding (FastAPI, folder structure, .env)
- Intent Parser (Claude haiku via Anthropic API)
- OAuth 2.1 PKCE Handler (Swiggy auth flow)
- MCP Client (direct streamable HTTP calls to Swiggy's 35 tools)
- Multi-Turn Session Manager (conversation history + turn boundary patterns)
- Cart State Reader (always reads from Swiggy servers, never local)
- Order Placement Orchestrator (non-idempotency guards)
- Error Classifier (message-based, v1 pattern)
- FastAPI routes (7 endpoints)
- PostgreSQL schema (3 tables — no baskets table)

### Prerequisites

- Copy `VertexCart_PRD.md` into project root — Claude Code must read this before writing anything
- Have `ANTHROPIC_API_KEY` in `.env`
- Swiggy credentials will come after application is accepted — use MOCK MODE until then

---

### Prompt 1.1 — Project Setup

```
Read VertexCart_PRD.md in this directory before writing any code.

Set up a FastAPI project with this exact folder structure:

vertexcart/
├── app/
│   ├── main.py
│   ├── api/
│   │   └── routes/
│   │       ├── intent.py
│   │       ├── session.py
│   │       ├── turn.py
│   │       ├── cart.py
│   │       ├── confirm.py
│   │       ├── orders.py
│   │       └── auth.py
│   ├── core/
│   │   ├── intent_parser.py
│   │   ├── oauth_handler.py
│   │   ├── session_manager.py
│   │   ├── mcp_client.py
│   │   ├── order_orchestrator.py
│   │   └── error_classifier.py
│   ├── models/
│   │   ├── intent.py
│   │   ├── session.py
│   │   └── order.py
│   ├── db/
│   │   ├── connection.py
│   │   └── schema.sql
│   └── config.py
├── tests/
├── .env.example
├── requirements.txt
└── README.md

Python 3.11+. Pydantic v2. asyncpg for PostgreSQL. httpx for HTTP calls. No SQLAlchemy.

Create all files with correct imports but leave core logic as stubs (pass with docstrings).
Document which PRD section each module corresponds to.
```

---

### Prompt 1.2 — Intent Parser

```
Build the intent parser in app/core/intent_parser.py.

This module takes raw user text and returns a structured IntentResult.

Use Claude (claude-haiku-4-5-20251001) via Anthropic API.

System prompt the LLM to:
- Extract entities from user text
- Classify each entity as: ingredient, ready_to_eat, reservation
- Assign each to a vertical: instamart / food / dineout
- Return a confidence score (0.0-1.0) per entity
- Detect occasion: weeknight_dinner / weekend_outing / quick_snack / unknown
- Detect urgency: immediate / scheduled / unknown
- Detect dineout signal: boolean
- Flag if clarification is needed: boolean (true when intent is ambiguous)

Output Pydantic model (app/models/intent.py):
{
  "entities": [
    {
      "text": str,
      "type": "ingredient" | "ready_to_eat" | "reservation",
      "vertical": "instamart" | "food" | "dineout",
      "confidence": float
    }
  ],
  "occasion": str,
  "urgency": str,
  "dineout_signal": bool,
  "requires_clarification": bool,
  "raw_input": str
}

LLM must return valid JSON only. Strip markdown fences before parsing.
On parse failure: return fallback IntentResult with all fields "unknown" and log the raw output.

Write unit tests (tests/test_intent_parser.py) with 6 test cases:
1. Multi-vertical: pasta ingredients + dessert order
2. Single food intent
3. Single instamart intent
4. Dineout intent ("book a table for Friday dinner")
5. Ambiguous intent ("something nice tonight") — should have requires_clarification=true
6. Reorder intent ("the usual groceries") — should classify as instamart with requires_clarification=false
```

---

### Prompt 1.3 — OAuth 2.1 PKCE Handler

```
Build the OAuth handler in app/core/oauth_handler.py.

Swiggy uses OAuth 2.1 with PKCE (S256). One token covers all three MCP servers.

This module must:

1. Generate authorization URL:
   - Create code_verifier (random 43-128 char string, URL-safe Base64)
   - Derive code_challenge via SHA-256 hash of verifier, then URL-safe Base64 encode
   - Build authorization URL with: client_id, redirect_uri, code_challenge, code_challenge_method=S256, scope=mcp:tools
   - Store code_verifier in session (needed for token exchange)

2. Exchange authorization code for token:
   - POST to Swiggy token endpoint with: code, code_verifier, client_id, redirect_uri, grant_type=authorization_code
   - Parse JWT access token from response
   - Store token + expiry (5-day lifetime) in session record in DB

3. Token validation:
   - Check token expiry before each MCP call
   - If expired: raise OAuthExpiredError — caller must re-initiate auth flow
   - Do not attempt to refresh (no refresh tokens in v1)

4. Handle auth failures from MCP calls:
   - HTTP 401 or JSON-RPC -32001 from any Swiggy endpoint → raise OAuthExpiredError
   - Caller initiates re-auth once, retries, then fails with user-visible error if still failing

Read SWIGGY_CLIENT_ID, SWIGGY_AUTH_URL, SWIGGY_TOKEN_URL, SWIGGY_REDIRECT_URI from env.

In MOCK MODE (env var MOCK_MODE=true): return a hardcoded fake token, skip actual OAuth flow.
```

---

### Prompt 1.4 — MCP Client

```
Build the MCP client in app/core/mcp_client.py.

This is the core layer that calls Swiggy's 35 tools over streamable HTTP (JSON-RPC 2.0).

Architecture:
- One httpx AsyncClient with connection pooling
- Three base URLs: mcp.swiggy.com/food, mcp.swiggy.com/im, mcp.swiggy.com/dineout
- All calls use POST with JSON-RPC 2.0 format
- Bearer token in Authorization header

JSON-RPC call format:
{
  "jsonrpc": "2.0",
  "method": "tools/call",
  "params": {
    "name": "<tool_name>",
    "arguments": { ... }
  },
  "id": 1
}

Response parsing:
1. Check HTTP status first
2. Parse JSON
3. Check "success" boolean in response body
4. If success=true: return data field
5. If success=false: pass to error classifier

Implement these tool wrappers (each as an async method):

Food tools:
- get_addresses() → list of {id, label, displayText}
- search_restaurants(addressId, query) → list of restaurants
- get_restaurant_menu(restaurantId) → menu with categories, items, variants
- search_menu(query, restaurantId=None) → menu items matching query
- update_food_cart(restaurantId, items: list[{itemId, quantity}]) → cart state
- get_food_cart() → current Food cart from server (NEVER cache this)
- flush_food_cart() → clear Food cart
- fetch_food_coupons() → list of coupons (filter to COD-compatible only)
- apply_food_coupon(couponCode, addressId) → updated cart
- place_food_order(paymentMethod="COD") → orderId (NON-IDEMPOTENT — see orchestrator)
- get_food_orders() → recent orders (used for idempotency check)
- track_food_order(orderId) → delivery status + ETA

Instamart tools:
- im_get_addresses() → same as Food get_addresses but on /im server
- search_products(addressId, query) → list of products with variants and spinIds
- your_go_to_items(addressId) → frequently ordered SKUs (use for reorder intents)
- update_cart(items: list[{spinId, quantity}]) → cart state (uses spinId, NOT productId)
- get_cart() → current Instamart cart (NEVER cache this)
- clear_cart() → clear Instamart cart (call before address switch)
- checkout(paymentMethod="COD") → orderId (NON-IDEMPOTENT)
- get_orders() → recent Instamart orders (idempotency check)
- track_order(orderId) → delivery status + ETA

Dineout tools:
- get_saved_locations() → list of {id, addressLine, lat, lng} (NOT addressId — uses lat/lng)
- search_restaurants_dineout(query, lat, lng, entityType=None, addressId=None)
- get_restaurant_details(restaurantId, latitude, longitude)
- get_available_slots(restaurantId, date, latitude, longitude) → filter: show only isFree=true slots
- book_table(restaurantId, slotId, itemId, reservationTime, guestCount, latitude, longitude) → bookingId (NON-IDEMPOTENT)
- get_booking_status(orderId) → booking confirmation
- report_error(tool, errorMessage, domain=None, flowDescription=None, toolContext=None) → diagnostic link

In MOCK MODE: every tool returns realistic hardcoded responses. Log a warning on every call.

Critical notes in docstrings for each non-idempotent tool:
  "NON-IDEMPOTENT: Do not call directly. Use order_orchestrator.place_* which implements check-then-retry."
```

---

### Prompt 1.5 — Error Classifier

```
Build the error classifier in app/core/error_classifier.py.

Swiggy MCP v1 does not emit symbolic error.code values. Classification uses HTTP status + error.message text.

The classifier takes: http_status (int), error_message (str), tool_name (str)
Returns: ErrorClassification object with fields: bucket (str), is_retryable (bool), user_message (str), action (str)

Implement this classification table:

HTTP 401 or JSON-RPC -32001 → bucket="auth_failure", is_retryable=False, action="re_auth"
HTTP 400 + message starts "Invalid" or "Missing" → bucket="bad_input", is_retryable=False, action="fix_args"
HTTP 504 or message contains "timeout" → bucket="upstream_timeout", is_retryable=True, action="backoff_retry"
HTTP 502 or HTTP 503 → bucket="upstream_error", is_retryable=True, action="backoff_retry"
HTTP 500 or JSON-RPC -32603 → bucket="internal_error", is_retryable=True (once), action="backoff_once_then_report"
HTTP 200 + success=false + message contains "₹1000" → bucket="food_cart_cap", is_retryable=False, user_message="Food orders are capped at ₹1000 in this session.", action="reduce_items"
HTTP 200 + success=false + message contains "minimum" → bucket="instamart_minimum", is_retryable=False, user_message="Add items to meet the ₹99 minimum.", action="add_items"
HTTP 200 + success=false + message contains "out of stock" → bucket="item_unavailable", is_retryable=False, action="suggest_alternatives"
HTTP 200 + success=false + message contains "not serviceable" → bucket="address_not_serviceable", is_retryable=False, action="ask_alternative_address"
HTTP 200 + success=false + message contains "restaurant closed" → bucket="restaurant_closed", is_retryable=False, action="re_search"
HTTP 200 + success=false (any other) → bucket="domain_failure", is_retryable=False, action="surface_to_user"

Write unit tests (tests/test_error_classifier.py) for each bucket.
```

---

### Prompt 1.6 — Multi-Turn Session Manager

```
Build the session manager in app/core/session_manager.py.

This manages the state of a multi-turn conversation with the user. It does NOT store cart state — that lives on Swiggy's servers. It stores conversation context and orchestrates which tools to call each turn.

Core responsibilities:

1. Conversation history: store each turn (role: user/agent, content, tools_called, intent) in DB
2. Turn boundary pattern: at the start of ANY turn that might touch a cart, call get_*_cart first
   - This is a hard requirement from Swiggy's multi-turn documentation
   - The agent's mental model of the cart may be stale — always read server state

3. Vertical tracking: which verticals have been engaged in current session
   - First turn: detect from intent classification
   - Subsequent turns: detect corrections or additions

4. Correction handling: if user sends a correction turn:
   - Re-parse the correction with intent parser
   - Identify which vertical is affected
   - Call ONLY the affected vertical's tools (don't rebuild entire session)
   - Do not flush unaffected carts

5. Restaurant switch warning (Food):
   - Before any update_food_cart call, call get_food_cart
   - If cart exists and new restaurant != current cart restaurant: surface warning
   - "This will clear your [existing restaurant] cart ([items, total]). Continue?"
   - Wait for user confirmation before proceeding

6. Address switch warning (Instamart):
   - If delivery address changes mid-session: call clear_cart before switching
   - Never silently switch address mid-cart

7. Cart expired handling:
   - If get_*_cart returns CART_EXPIRED: rebuild cart from session history
   - Confirm with user before re-adding items ("Your cart expired. Shall I rebuild it?")

Methods:
- create_session(user_id) → session_id
- get_session(session_id) → Session object
- add_turn(session_id, role, content, intent=None, tools_called=None) → turn_id
- get_conversation_history(session_id) → list of turns (last N turns for LLM context)
- get_active_verticals(session_id) → list of vertical names
- should_warn_restaurant_switch(session_id, new_restaurant_id) → bool (reads live cart)
- rebuild_cart_from_history(session_id) → dict of items per vertical
```

---

### Prompt 1.7 — Order Placement Orchestrator

```
Build the order orchestrator in app/core/order_orchestrator.py.

place_food_order, checkout (Instamart), and book_table (Dineout) are NON-IDEMPOTENT.
Do not call these directly from routes. All order placement goes through this module.

Implement check-then-retry pattern for each:

place_food_order():
  1. Verify cart via get_food_cart — confirm items + total match what user confirmed
  2. Verify cart total <= ₹1000 — surface error if cap exceeded
  3. Call mcp_client.place_food_order(paymentMethod="COD")
  4. On success: return order details, store order_reference in DB
  5. On 5xx or network error:
     a. Wait 2 seconds
     b. Call get_food_orders, check for order placed in last 60 seconds
     c. If found: treat as success, return that order
     d. If not found: retry place_food_order (max 3 retries)
     e. After 3 retries: raise OrderPlacementError with message and call report_error
  6. On any domain failure (success=false): classify error, surface to user, do NOT retry

checkout_instamart():
  Same pattern. Use get_orders instead of get_food_orders for verification.
  Also verify: cart >= ₹99 minimum before attempting.

book_table_dineout(restaurantId, slotId, itemId, reservationTime, guestCount, lat, lng):
  Same pattern. Use get_booking_status for verification on failure.
  Additional: only proceed if slot's isFree=true — reject paid slots before calling.

Each method must:
- Log the tool call with session_id for debugging
- Store order_reference in DB on success
- Call report_error on persistent failure (not user-visible, but server-side logging)

Write tests (tests/test_order_orchestrator.py):
1. Happy path: order placed successfully
2. 5xx → order found in get_*_orders → treated as success
3. 5xx → order not found → retry succeeds on second attempt
4. 3 retries all fail → OrderPlacementError raised
5. ₹1000 cap exceeded → rejected before placement call
6. Instamart minimum not met → rejected before placement call
7. Dineout paid slot → rejected before book_table call
```

---

### Prompt 1.8 — FastAPI Routes and Main

```
Wire all modules into FastAPI routes and main.py.

Routes (see PRD Section 8.3 for full spec):

POST /api/v1/intent
  Body: {text: str, user_id: str}
  → intent_parser.parse(text)
  → Returns: IntentResult

POST /api/v1/session
  Body: {user_id: str}
  → session_manager.create_session(user_id)
  → Returns: {session_id: str}

POST /api/v1/session/{id}/turn
  Body: {text: str}
  → This is the core conversation loop:
     1. intent_parser.parse(text)
     2. If requires_clarification: return clarifying question to user
     3. session_manager.add_turn(session_id, "user", text, intent)
     4. If Food vertical: get_food_cart (turn boundary pattern)
     5. If Instamart vertical: get_cart (turn boundary pattern)
     6. If restaurant switch detected: return warning, wait for confirmation
     7. Call relevant discovery/cart tools based on intent
     8. session_manager.add_turn(session_id, "agent", response, tools_called=...)
  → Returns: {agent_response: str, verticals_active: list, cart_summary: dict, requires_confirmation: bool}

GET /api/v1/session/{id}/cart
  → Calls get_food_cart + get_cart (and get_booking_status if Dineout active) in sequence
  → Returns live cart state from Swiggy servers (never cached)

POST /api/v1/session/{id}/confirm
  Body: {vertical: str}  (one at a time — "food" | "instamart" | "dineout")
  → Calls order_orchestrator.place_* for the specified vertical
  → Returns: {order_id: str, eta: str, status: str}

GET /api/v1/session/{id}/orders
  → Returns all order_references for session from DB
  → For each: call track_* for live ETA (poll-friendly endpoint, caller polls every 10s)

GET /health
  → Returns {status: "ok", mock_mode: bool}

POST /api/v1/auth/callback
  → Handles OAuth 2.1 PKCE callback
  → Exchanges code for token, stores in session
  → Returns {success: bool}

In main.py:
- CORS middleware (allow localhost:3000 in dev, env-configured in prod)
- Request logging middleware (log session_id on every request)
- Mount all routers under /api/v1
- Startup event: verify DB connection

Write schema.sql at app/db/schema.sql with the three tables from PRD Section 8.3:
  sessions, conversation_turns, order_references
  Note: NO baskets table. Cart state lives on Swiggy's servers.
```

---

### Phase 1 Completion Checklist

- [ ] `uvicorn app.main:app --reload` runs without errors
- [ ] `/health` returns 200 with `mock_mode: true`
- [ ] `/api/v1/intent` returns valid IntentResult for test input
- [ ] `/api/v1/session` creates a session and returns session_id
- [ ] `/api/v1/session/{id}/turn` processes a turn and returns agent response
- [ ] `/api/v1/session/{id}/cart` calls `get_food_cart` + `get_cart` (mock responses)
- [ ] `/api/v1/session/{id}/confirm` triggers order orchestrator (mock mode)
- [ ] All unit tests pass (intent parser, error classifier, order orchestrator)
- [ ] `schema.sql` is complete and has no `baskets` table
- [ ] Restaurant switch warning triggers correctly in session manager
- [ ] Non-idempotent tools are NOT called directly in any route — all go through orchestrator

---

## PHASE 2 — Gemini CLI: Frontend

### What Gemini CLI Builds

Next.js 14 frontend. 5 screens. Framer Motion animations. Data pulled from live Swiggy tool responses (no local basket object).

### Prerequisites

- Phase 1 backend running on localhost:8000
- API contract from Phase 1 finalized — no backend changes during Phase 2
- Note: Frontend shows cart data from `GET /api/v1/session/{id}/cart` which reads live from Swiggy

---

### Prompt 2.1 — Project Setup

```
Build the frontend for VertexCart — a conversational commerce agent for Swiggy.

This is the tool interface, NOT a landing page.

Tech: Next.js 14 (App Router), TypeScript, Tailwind CSS, Framer Motion. No component libraries.

Folder structure:
vertexcart-frontend/
├── app/
│   ├── layout.tsx
│   ├── page.tsx
│   └── globals.css
├── components/
│   ├── IntentInput.tsx
│   ├── ParsingState.tsx
│   ├── CartPreview.tsx
│   ├── AgentPanel.tsx
│   ├── ConfirmOrder.tsx
│   ├── OrderStatus.tsx
│   └── PoweredBySwiggy.tsx  ← required by co-branding
├── lib/
│   ├── api.ts         (all fetch calls to FastAPI)
│   └── types.ts       (TypeScript interfaces matching backend Pydantic models)
└── public/

Color palette (exact values — these match Swiggy co-branding requirements):
- Swiggy Orange: #FF5200 (use only with "Powered by Swiggy" attribution)
- Background: #0D0D0D
- Surface: #1A1A1A
- Surface elevated: #242424
- Text primary: #FFFFFF
- Text secondary: #A0A0A0
- Instamart accent: #00B383
- Food accent: #FF5200
- Dineout accent: #8B5CF6

Font: Inter (Google Fonts). No component libraries.

Important: The frontend displays cart data by calling GET /api/v1/session/{id}/cart which reads live from Swiggy servers. There is no local cart state in the frontend.
```

---

### Prompt 2.2 — Intent Input Screen

```
Build IntentInput component.

Full-screen, dark background (#0D0D0D). Centered content.

Elements:
1. VertexCart wordmark — top left, small, white
2. PoweredBySwiggy component — bottom right, small (required)
3. Headline: "What are you planning tonight?" — 32px, white, semi-bold, centered
4. Subline: "I'll handle food, groceries, and reservations." — 16px, #A0A0A0
5. Input bar: 80% viewport width, pill shape, #242424, white text, orange (#FF5200) focus ring
   Placeholder: "Tell me what you need..."
   Send button: #FF5200 circle, right side, arrow icon
6. Three example chips:
   "Pasta tonight + dessert delivery"
   "Friday dinner out + wine at home"
   "Reorder my usual groceries + pizza"
   Clicking chips fills the input.

Animations (Framer Motion):
- Headline fades in 0.4s on load
- Subline fades in with 0.2s delay
- Input slides up 0.3s delay
- Chip hover: scale 1.03

On submit:
- Call POST /api/v1/session to create session, store session_id
- Call POST /api/v1/intent with the text for immediate classification preview
- Then call POST /api/v1/session/{id}/turn with the text
- While waiting: transition to ParsingState component
```

---

### Prompt 2.3 — Parsing State + Cart Preview

```
Build ParsingState and CartPreview components.

ParsingState (shows during backend processing):
- Full screen, dark background
- Input text animates to top of screen (0.3s)
- Three vertical lanes appear: Instamart (green #00B383 border), Food (orange #FF5200 border), Dineout (purple #8B5CF6 border)
- "Reading your intent..." text with animated dots pulses center
- As backend responds, items animate into lanes with stagger (0.1s between items)
- If no response in 1.5s: skeleton loader in each lane
- Transition to CartPreview when /session/{id}/cart returns data

CartPreview (shows after parsing):
- Multi-column grid, one column per active vertical
- Column header: vertical name + icon + ETA badge
- Items: dark surface cards with name, price, quantity
- Important note in code: "This data comes from GET /session/{id}/cart which reads live Swiggy server state"
- Column subtotal at bottom
- Agent reasoning panel: collapsible sidebar
  Shows turn-by-turn intent classification: "pasta → Instamart | tiramisu → Food"
  User can type corrections here → calls POST /session/{id}/turn with correction text
- Combined total at bottom of screen
- Two CTAs, one per vertical (e.g., "Confirm Instamart Order" and "Confirm Food Order")
  Rationale: two separate order placements required per Swiggy platform constraints
  Add small tooltip: "Each order is confirmed separately for safety"
```

---

### Prompt 2.4 — Confirmation and Order Status

```
Build ConfirmOrder and OrderStatus components.

ConfirmOrder:
- Shows per-vertical, triggered sequentially (Instamart first, then Food, then Dineout)
- Shows live cart data (fetched from GET /session/{id}/cart just before render)
- Items list, subtotal, payment method (COD)
- Food: shows ₹1000 cap remaining ("₹680 used of ₹1000 limit")
- Instamart: shows "₹99 minimum" status
- CTA: "Place [Vertical] Order — ₹[total]"
  On click: POST /session/{id}/confirm with {vertical: "instamart"} (or "food", "dineout")
  On loading: spinner, "Placing order..."
  On success: animate out, show success tick, move to next vertical
  On error: show error message from backend + "Contact Swiggy support" link

"Powered by Swiggy" badge visible on this screen — required for co-branding.

OrderStatus:
- Shows after all verticals confirmed
- List of orders with: vertical icon, order ID, ETA, status
- Poll GET /session/{id}/orders every 10 seconds (match Swiggy's delivery-partner ETA cadence)
- Progress indicator per order
- "Groceries in ~12 min | Dessert in ~35 min" style summary
```

---

### Prompt 2.5 — PoweredBySwiggy Component + lib files

```
Build PoweredBySwiggy.tsx:
- Small badge, bottom-right of screen
- Text: "Powered by Swiggy"
- Use #FF5200 for Swiggy wordmark portion only (per brand guidelines)
- Not clickable, not intrusive

Build lib/api.ts with all fetch calls to FastAPI backend:
- createSession(userId: string)
- parseIntent(text: string, userId: string)
- sendTurn(sessionId: string, text: string)
- getCart(sessionId: string)  ← always fetches live from backend, never cached
- confirmOrder(sessionId: string, vertical: string)
- getOrders(sessionId: string)

All functions: use try/catch, handle 4xx/5xx with typed errors, never return undefined silently.
Read backend URL from NEXT_PUBLIC_API_URL env var.

Build lib/types.ts with TypeScript interfaces matching every FastAPI Pydantic model.
Include a comment above each interface: "Matches backend model: <module path>"
```

---

### Phase 2 Completion Checklist

- [ ] `npm run dev` runs without errors
- [ ] All 5 screens render at localhost:3000
- [ ] No hardcoded localhost URLs — all from NEXT_PUBLIC_API_URL
- [ ] Cart data is fetched from backend API, never stored locally in component state
- [ ] "Powered by Swiggy" visible on CartPreview and ConfirmOrder screens
- [ ] Two separate confirm CTAs (one per vertical) — not a single "place all orders" button
- [ ] Framer Motion animations working on all screens
- [ ] Mobile responsive at 390px
- [ ] No console errors

---

## PHASE 3 — Claude Code: API Wiring

### Prompt 3.1 — Contract Alignment

```
Review the FastAPI backend (app/api/routes/, app/models/) and Next.js frontend (lib/api.ts, lib/types.ts).

Do the following in order:

1. Build a contract diff table:
   | Endpoint | Backend input shape | Frontend call shape | Match? |
   | Endpoint | Backend response shape | Frontend TypeScript interface | Match? |
   Fix all mismatches — prefer updating frontend types to match backend.

2. Add CORS in app/main.py:
   - Allow http://localhost:3000 in development
   - Read ALLOWED_ORIGINS from env for production

3. Add NEXT_PUBLIC_API_URL=http://localhost:8000 to frontend .env.local

4. Run end-to-end smoke test in MOCK_MODE:
   - From frontend: submit test intent ("pasta tonight + tiramisu dessert")
   - Verify: session created → turn processed → cart preview renders → mock orders placed
   - Report what worked and what didn't

5. Fix anything broken. Do not redesign — only fix integration issues.
```

---

### Phase 3 Completion Checklist

- [ ] Full flow works end-to-end in mock mode
- [ ] CORS configured
- [ ] No TypeScript errors
- [ ] API contract diff table shows all matches

---

## PHASE 4 — Copilot CLI: Debugging + Tests

### Prompt 4.1 — Backend Bug Review

```
Review the complete backend codebase in app/.

Find and fix:
1. Any route that calls place_food_order, checkout, or book_table DIRECTLY (must go through orchestrator)
2. Any turn that reads cart data from local state instead of calling get_*_cart (turn boundary violation)
3. Missing try/catch on httpx calls (every MCP tool call must be in try/except)
4. Auth failures (401) that are not routed to re-auth flow
5. Any function that returns None where a Pydantic model is expected
6. Missing check for success:false in MCP tool responses
7. Missing ₹1000 cap check before place_food_order
8. Missing ₹99 minimum check before Instamart checkout
9. Missing isFree check before book_table call
10. Any hardcoded MCP URLs that should be env vars

Write integration tests (tests/test_integration.py):
1. Happy path: food + instamart in one session, both orders placed
2. Restaurant switch warning triggers correctly
3. 5xx on place_food_order → check_then_retry → success on second attempt
4. 5xx on place_food_order → order found in get_food_orders → treated as success
5. ₹1000 cap exceeded → order rejected before placement
6. Instamart minimum not met → rejected
7. Dineout paid slot → rejected before book_table
8. Cart expired → rebuild flow triggered
9. OAuth 401 → re-auth triggered
10. Multi-turn correction → only affected vertical's tools called (not full rebuild)
```

---

### Prompt 4.2 — Frontend Bug Review

```
Review the frontend codebase in components/ and lib/.

Check:
1. Any component that stores cart data in local state instead of fetching from API
2. Any confirmation button that fires for multiple verticals simultaneously (should be sequential)
3. Any fetch call without error handling
4. Any hardcoded URL not using NEXT_PUBLIC_API_URL
5. Loading states that don't reset on error
6. Animations that get stuck on API failure
7. The 10-second poll on OrderStatus — confirm it doesn't poll faster than this

Fix all issues. Document each fix.
```

---

### Phase 4 Completion Checklist

- [ ] All integration tests pass in mock mode
- [ ] No direct place_food_order/checkout/book_table calls outside orchestrator
- [ ] No local cart state in frontend components
- [ ] CHANGELOG.md updated with all fixes

---

## PHASE 5 — Devin CLI: Database and Persistence

### Prompt 5.1 — Migrations and Persistence

```
Work on the VertexCart backend. Schema is at app/db/schema.sql.

Tasks in sequence:

1. Add Alembic to project (requirements.txt + alembic.ini)
2. Convert schema.sql into Alembic migration scripts — one migration per table:
   - 001_create_sessions.py
   - 002_create_conversation_turns.py
   - 003_create_order_references.py

3. Configure asyncpg connection pool in app/db/connection.py:
   - Min size: 2, Max size: 10
   - Read from DATABASE_URL env var
   - Expose get_connection() context manager

4. Wire DB writes to routes:
   - POST /session → insert sessions row
   - POST /session/{id}/turn → insert conversation_turns row
   - POST /session/{id}/confirm → insert order_references row on success

5. Add index on conversation_turns: (session_id, created_at DESC) — supports history lookup
6. Add index on order_references: (session_id) — supports order list lookup

7. Add GET /api/v1/session/{id}/history endpoint:
   Returns last 10 conversation turns for a session

Do not change business logic. Only add persistence layer on top of existing routes.

Test: run `alembic upgrade head` against local PostgreSQL, confirm all three tables created.
```

---

### Phase 5 Completion Checklist

- [ ] `alembic upgrade head` completes without errors
- [ ] All three tables created in local PostgreSQL
- [ ] Session, turns, and order references persist after full flow
- [ ] /session/{id}/history endpoint returns correct data

---

## PHASE 6 — Kiro CLI: Orchestration Refinement

### Prompt 6.1 — Retry Logic and Multi-Turn Refinement

```
Refine the orchestration layer using Kiro.

1. Enhance retry logic in order_orchestrator.py:
   - Implement full exponential backoff: 500ms, 1000ms, 2000ms, 4000ms with ±30% jitter
   - Cap: 5 retries max, 30s total wall-clock time for user-facing flows
   - Separate retry budgets for read tools vs write tools vs order placement

2. Refine the multi-turn correction loop in session_manager.py:
   - When user sends correction mid-session, the agent should:
     a. Identify the affected vertical from the correction's intent
     b. Call get_*_cart for that vertical (turn boundary)
     c. If correction is additive (more items): update_cart / update_food_cart
     d. If correction is a removal: flush or update quantity to 0
     e. If correction changes the restaurant (Food): surface warning BEFORE flushing
     f. Return updated cart state in agent response

3. Add degradation handling:
   - If one vertical's tools fail but others succeed: continue with working verticals
   - Example: Instamart times out → continue with Food order → surface Instamart failure to user clearly
   - Agent: "I couldn't reach Instamart right now. Your food order is ready to confirm. Want to try groceries again?"

4. Add report_error calls on persistent failures:
   - When order orchestrator exhausts retries: call report_error with toolContext
   - Include: tool name, error message, flow description, all relevant IDs

5. Document the orchestration flow as a diagram comment at the top of turn.py.
```

---

### Phase 6 Completion Checklist

- [ ] Retry with jitter working on simulated MCP timeout
- [ ] Multi-turn correction updates only the affected vertical
- [ ] Restaurant switch warning fires correctly during correction flow
- [ ] Degradation: one vertical failing does not block the other
- [ ] report_error called on persistent failures
- [ ] Full end-to-end test: intent → correction → confirm each vertical → orders tracked

---

## Build Sequence Summary

```
Phase 1 → Claude Code (backend, auth, MCP client, session manager, order orchestrator, DB schema)
  Verify: backend runs, all endpoints respond, non-idempotency guards in place

Phase 2 → Gemini CLI (frontend, 5 screens, animations, live cart reads)
  Verify: all screens render, cart data from API (not local state), two confirm CTAs

Phase 3 → Claude Code (API wiring, contract alignment, CORS, smoke test)
  Verify: full flow works end-to-end in mock mode

Phase 4 → Copilot CLI (bug fixes, integration tests)
  Verify: all tests pass, no direct order calls outside orchestrator

Phase 5 → Devin CLI (Alembic migrations, connection pooling, persistence)
  Verify: data persists, migrations clean

Phase 6 → Kiro CLI (retry logic, multi-turn refinement, degradation handling)
  Verify: resilient flows, partial failure handled gracefully
```

---

## Environment Variables Reference

```env
# Anthropic
ANTHROPIC_API_KEY=

# Swiggy MCP (blank until application accepted — use MOCK_MODE=true until then)
SWIGGY_CLIENT_ID=
SWIGGY_AUTH_URL=https://accounts.swiggy.com/oauth/authorize
SWIGGY_TOKEN_URL=https://accounts.swiggy.com/oauth/token
SWIGGY_REDIRECT_URI=http://localhost:8000/api/v1/auth/callback

# Swiggy MCP Endpoints
SWIGGY_FOOD_MCP_URL=https://mcp.swiggy.com/food
SWIGGY_INSTAMART_MCP_URL=https://mcp.swiggy.com/im
SWIGGY_DINEOUT_MCP_URL=https://mcp.swiggy.com/dineout

# Database
DATABASE_URL=postgresql://user:password@localhost:5432/vertexcart

# App Config
MOCK_MODE=true          # Set false when real Swiggy credentials available
LOG_SESSION_IDS=true    # Required for Swiggy support correlation

# CORS
ALLOWED_ORIGINS=http://localhost:3000

# Frontend
NEXT_PUBLIC_API_URL=http://localhost:8000
```

---

## Before Applying to Swiggy Builders Club

Per the access guidelines at mcp.swiggy.com/builders/access:

**Build locally first.** No credentials needed until production.  
Build the mock-mode version end-to-end, then record a screen capture of a working flow.  
Include the video link in your application — it's the fastest path to approval.

**Application checklist:**
- [ ] Working demo video recorded (Loom or YouTube unlisted)
- [ ] Integration architecture described (FastAPI → Swiggy MCP tools → Next.js)
- [ ] Redirect URIs listed (localhost for dev, HTTPS for production)
- [ ] Data handling declaration written (no Swiggy PII beyond session, no analytics use)
- [ ] Servers requested: food, instamart, dineout
- [ ] Acknowledged terms
- [ ] Apply via Developer track: https://forms.gle/4vkeKyqm15Qb6fnJA

---

## Common Failure Points by Phase

**Phase 1:** The biggest trap is building a local cart state manager. If Claude Code creates any data structure that "stores what's in the cart" rather than reading it from `get_*_cart` — reject it and push back explicitly. The PRD Section 8.4 is clear: carts live on Swiggy's servers.

**Phase 2:** Gemini may create a "confirm all" button instead of per-vertical confirm buttons. Reject this. The platform requires separate `place_food_order` and `checkout` calls — combining them into one UI action creates incorrect user expectations about what's atomic.

**Phase 3:** Most contract mismatches will be cart-related. The backend returns live Swiggy data (nested JSON from tool responses); the frontend TypeScript types may not match the nested structure. Fix the TypeScript types, not the backend.

**Phase 4:** Copilot's most important test to write is the non-idempotency guard test. If it doesn't write this, add it manually: "Assert that calling POST /session/{id}/confirm twice rapidly does NOT result in two Instamart orders."

**Phase 5:** Devin may try to cache cart data in the DB. Explicitly tell it: "Do NOT create a cart or basket table. The only order-related table is order_references which stores orderId after placement — not cart contents."

**Phase 6:** The degradation case (one vertical failing, others proceeding) is the hardest Kiro prompt to get right. Run this scenario specifically: simulate Instamart MCP timeout while Food MCP works. Confirm the session manager returns a useful agent response that surfaces the Instamart failure clearly while proceeding with Food.