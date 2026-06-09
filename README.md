# VertexCart

**Conversational commerce agent for Swiggy — Food, Instamart, and Dineout in one session.**

---

## Table of Contents

1. [Product Overview](#1-product-overview)
2. [Problem Statement](#2-problem-statement)
3. [Who It's For](#3-who-its-for)
4. [What It Solves](#4-what-it-solves)
5. [Core User Experience](#5-core-user-experience)
6. [Product Goals and Metrics](#6-product-goals-and-metrics)
7. [Known Constraints (v1)](#7-known-constraints-v1)
8. [Competitive Position](#8-competitive-position)
9. [Technical Architecture](#9-technical-architecture)
10. [Backend Modules](#10-backend-modules)
11. [API Endpoints](#11-api-endpoints)
12. [Database Schema](#12-database-schema)
13. [Frontend](#13-frontend)
14. [Local Setup](#14-local-setup)
15. [Testing](#15-testing)
16. [Compliance and Data Handling](#16-compliance-and-data-handling)
17. [v1 Limitations and Roadmap](#17-v1-limitations-and-roadmap)

---

## 1. Product Overview

VertexCart is a conversational commerce agent built on Swiggy's MCP (Model Context Protocol) platform. It exposes Swiggy's 35 tools across three verticals — Food, Instamart, and Dineout — through a single natural language interface.

A user describes what they want in plain language. VertexCart figures out which verticals to engage, orchestrates the right tool calls across Swiggy's three MCP servers, and guides the user to real placed orders — across multiple verticals, in one session, without switching screens or apps.

**The user says one thing. VertexCart calls the right tools. Orders happen.**

VertexCart is not a Swiggy clone, a unified checkout button, or a local basket system. It is an orchestration layer on top of Swiggy's existing MCP infrastructure that makes cross-vertical ordering feel like a single conversation.

---

## 2. Problem Statement

Swiggy operates three live MCP servers covering food delivery, grocery/convenience delivery (Instamart), and restaurant reservations (Dineout). These verticals are separate in the app: separate tabs, separate carts, separate checkout flows.

The result: a user planning an evening — cooking pasta, ordering dessert, booking a table for the weekend — has to execute three separate workflows in three separate surfaces. The intent is unified ("I'm planning dinner"), but the execution is fragmented.

The API infrastructure to serve this unified intent already exists. Swiggy's own developer documentation even describes a "Plan my evening" reference pattern using Food + Instamart + Dineout together. Nobody has shipped it as a product.

**VertexCart ships it as a product.**

The gap is not the API. The gap is the UX layer — a conversational agent that takes a natural language intent and converts it into the right sequence of MCP tool calls, handles the multi-turn conversation, manages server-side cart state correctly, and guides the user to confirmed orders across multiple verticals without them having to think about which vertical to use.

Zomato's response to this gap is passive cross-promotion banners. No agent, no unified session, no combined order flow.

---

## 3. Who It's For

### Primary — The Convenience-First Urban Professional

- **Age:** 24–34
- **Location:** Tier 1 cities (Mumbai, Bengaluru, Delhi NCR, Hyderabad, Pune)
- **Income:** ₹8–30L per annum
- **Living situation:** 1–2 person urban household
- **Swiggy behavior:** 3+ food orders per week; uses Instamart for top-ups; uses Dineout 2–3x per month
- **Has or is close to Swiggy One**
- **Core pain:** Switching between app sections to execute a single evening plan feels like unnecessary overhead. They want to tell the app what they want and have it figure out the rest.

### Secondary — The Weekend Social Planner

- Plans meals and outings for groups of 2–4
- Uses Instamart for cooking ingredients on weekends
- Uses Dineout for dinner reservations
- Occasion-driven: weekends, dates, small gatherings
- VertexCart adds value by building a "full evening plan" from one prompt

### Excluded from v1

- Bulk grocery shoppers (Instamart is a convenience top-up layer for VertexCart, not a weekly stock run)
- Users with fewer than 3 Swiggy orders per month
- Users outside Tier 1 (Instamart + Dineout coverage is limited)
- Users who primarily pay online (v1 is COD-only — a platform constraint, not a product choice)

---

## 4. What It Solves

### The Switching Problem

Today, executing a "dinner plan + groceries + restaurant booking" requires navigating three separate sections of the Swiggy app, building three separate carts, and completing three separate checkout flows. There is no surface that treats these as part of a single intent.

### The Intent-to-Action Gap

Users think in terms of what they want ("I'm making pasta tonight"), not in terms of which Swiggy vertical to use and which items to search. The translation from intent to the correct sequence of tool calls requires:

1. Classifying the intent (ingredient vs. ready-to-eat vs. reservation)
2. Assigning it to the right vertical (Instamart vs. Food vs. Dineout)
3. Discovering the right items across different search paradigms
4. Building carts correctly across server-side state
5. Placing orders with proper non-idempotency guards

VertexCart handles all of this. The user only sees the conversation.

### The Cart State Problem

Swiggy's cart state is server-side only. There is no local cart. This means an agent building a multi-vertical order needs to read live cart state before every mutation, detect conflicts (restaurant switches flush the Food cart; address changes require clearing the Instamart cart), and surface these conflicts to the user before they lose items silently.

VertexCart implements this correctly: `get_*_cart` before every cart-touching turn, explicit conflict warnings, and server-authoritative cart reads immediately before order placement.

---

## 5. Core User Experience

### What a session looks like

```
User: "I'm making pasta tonight and want to order tiramisu for dessert"

VertexCart:
  → Classifies: pasta ingredients → Instamart | tiramisu → Food delivery
  → Searches both verticals in parallel
  → "Found pasta ingredients on Instamart (₹380, ~12 min).
     Tiramisu available from Smoke House Deli (₹320, ~35 min).
     Want me to add both?"

User: "Yes"

VertexCart:
  → Adds items to Instamart cart (server-side)
  → Adds tiramisu to Food cart (server-side)
  → Reads back both carts to verify
  → Shows combined summary: ₹700 total across two verticals

  → "Confirm Instamart order (₹380, COD)?" → User: Yes
  → Instamart order placed: #IM-XXXXX
  → "Confirm Food order (₹320, COD)?" → User: Yes
  → Food order placed: #FD-XXXXX

  → Showing ETAs: groceries in 12 min, tiramisu in 35 min.
```

Each order confirmation is separate — this is a platform constraint, not a design choice. Each placement call is non-idempotent and requires explicit user intent before execution.

### What the UI looks like

- Dark-mode interface (`#0D0D0D` background), Swiggy orange (`#FF5200`) accents
- Full-screen intent input with a wide pill input bar
- Animated parsing state showing which verticals are being queried
- Split column cart preview — Food (orange), Instamart (green), Dineout (purple)
- Sequential confirmation prompts per vertical
- Live order tracking with 10-second polling
- "Powered by Swiggy" badge per co-branding requirements

---

## 6. Product Goals and Metrics

### North Star

**Cross-Vertical Sessions per active user per month (CVS/user/month)**

This measures whether users are actually completing orders across 2+ verticals in one conversation — the behavior change VertexCart is trying to drive.

### 90-Day OKRs

**OKR 1 — Cross-Vertical Behavior**
- 25% cross-vertical session rate within 90 days (baseline ~8%)
- 40% of users who complete one cross-vertical session repeat within 14 days
- Intent-to-multi-server-order completion rate >55% in first 30 days

**OKR 2 — GOV Lift**
- Average cross-vertical session GOV >₹550 (vs ₹280 food-only baseline)
- Instamart attach rate on food-intent sessions >30%
- Dineout reservation attach rate on weekend evening sessions >20%

**OKR 3 — Product Experience**
- User completes intent-to-first-order in <5 conversational turns
- Agent response latency <2.5s per turn (tool calls + LLM inference combined)
- Cart abandonment rate <30% after basket confirmation screen

**OKR 4 — Platform Compliance**
- Zero order placements without explicit user confirmation step
- Zero cart state mismatches between agent display and Swiggy server
- `report_error` called on 100% of tool failures that surface to the user

---

## 7. Known Constraints (v1)

These are platform-level constraints from Swiggy's Builders Club v1. VertexCart designs around them.

| Constraint | Detail |
|---|---|
| Payment | COD only. No card/UPI/wallet in v1. |
| Food cart cap | ₹1000 max per order (Builders Club origin). |
| Instamart minimum | ₹99 minimum cart value. |
| Food cart binding | One restaurant per cart. Switching restaurant flushes the cart — VertexCart warns before this happens. |
| Dineout | Free reservations only (`isFree=true`, `bookingPrice=0`). Paid slots are rejected. |
| Scheduled delivery | Not supported. `place_food_order` is immediate only. |
| Cart state | Server-side only. No local caching. `get_*_cart` is authoritative. |
| Checkout | Per-server. No single unified checkout exists. |
| Authentication | OAuth 2.1 with PKCE (S256). 5-day JWT tokens. No refresh tokens in v1. |
| Swiggy One | No API tool available in v1. Membership benefits not surfaced. |
| Widgets | Swiggy's hosted widget layer (restaurant cards, menu items) ships in v1.1. v1 uses custom UI built from raw tool responses. |

---

## 8. Competitive Position

| Capability | VertexCart | Zomato / Blinkit |
|---|---|---|
| Conversational intent parsing | Yes | No |
| Cross-vertical session in one conversation | Yes | No |
| Multi-server tool orchestration | Yes | No |
| Agent-driven order flow | Yes | No |
| Dineout + Food delivery in one session | Yes | No |
| Swiggy MCP native integration | Yes | N/A |

---

## 9. Technical Architecture

### Stack

| Layer | Technology |
|---|---|
| Backend | FastAPI (Python 3.11+), async throughout |
| MCP Client | `httpx` AsyncClient — direct streamable HTTP to Swiggy endpoints |
| LLM (Intent) | Gemini 2.5 Flash via Google Generative AI SDK |
| Authentication | OAuth 2.1 PKCE (S256) — required by Swiggy platform |
| Database | PostgreSQL via `asyncpg` connection pool |
| Migrations | Alembic |
| Frontend | Next.js 14 (App Router), TypeScript, Tailwind CSS, Framer Motion |

### Architecture Diagram

```
Frontend (Next.js 14 + Tailwind + Framer Motion)
    |
    | HTTP (REST)
    v
VertexCart Backend (FastAPI)
    |
    ├── Intent Parser (Gemini 2.5 Flash)
    ├── OAuth 2.1 PKCE Handler
    ├── Multi-Turn Session Manager
    ├── MCP Client ──────────────────────────┐
    │       ├── mcp.swiggy.com/food           │ Swiggy MCP
    │       ├── mcp.swiggy.com/im             │ Servers
    │       └── mcp.swiggy.com/dineout ───────┘
    ├── Order Placement Orchestrator
    └── Error Classifier
    |
    v
PostgreSQL (sessions, conversation turns, order references)
```

### Swiggy MCP Platform

VertexCart connects to three Swiggy MCP servers:

| Server | Endpoint | Tools | Status |
|---|---|---|---|
| Food | `mcp.swiggy.com/food` | 14 tools | Live (v1) |
| Instamart | `mcp.swiggy.com/im` | 13 tools | Live (v1) |
| Dineout | `mcp.swiggy.com/dineout` | 8 tools | Live (v1) |

One OAuth token covers all three servers. Carts and orders are per-server — they are not shared.

---

## 10. Backend Modules

### Intent Parser (`app/core/intent_parser.py`)

Converts raw user text into a structured intent object with entity classifications and vertical assignments.

**Input:** Raw user message  
**Output:** JSON with classified entities, occasion type, urgency, dineout signal, and whether clarification is needed

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

**Intent Classification Rules:**

| User Says | Type | Vertical |
|---|---|---|
| "pasta ingredients", "milk", "vegetables" | Ingredient | Instamart |
| "order biryani", "get tiramisu delivered" | Ready-to-eat | Food |
| "book a table", "dinner out Friday" | Reservation | Dineout |
| "reorder my usual groceries" | Reorder | Instamart (`your_go_to_items`) |
| "dinner tonight, fancy" | Ambiguous | Ask: cook / order in / go out? |

### OAuth Handler (`app/core/oauth_handler.py`)

Manages the full Swiggy OAuth 2.1 PKCE flow:

- Generates `code_verifier` + `code_challenge` (S256 / SHA-256)
- Handles authorization code exchange for JWT access tokens
- Tokens have a 5-day lifetime; no refresh tokens in v1
- Detects expiry via HTTP 401 or JSON-RPC error `-32001`
- On expiry: re-initiates full OAuth flow, updates bearer across all three server clients
- Single token works for all three MCP servers

### Session Manager (`app/core/session_manager.py`)

Manages the full state of a multi-turn conversation:

- Stores conversation history per session (user turns + agent responses)
- Tracks which verticals have been engaged in the current session
- Enforces the **turn boundary pattern**: `get_*_cart` at the start of any turn that touches the cart
- Handles correction turns: re-parses user correction, identifies affected vertical, calls only relevant tools
- Detects restaurant switches before mutation and warns the user
- Detects Instamart address conflicts before `clear_cart` is triggered

**Cart state is never cached locally.** The server is authoritative. Always read before write.

### MCP Client (`app/core/mcp_client.py`)

Direct streamable HTTP client for Swiggy's MCP endpoints. Wraps all 35 tools.

**Protocol:** JSON-RPC 2.0 `tools/call` method over HTTPS  
**Auth:** Bearer token in `Authorization` header  
**Response handling:** Parse `success` boolean first; then `data` or `error.message`

**Retry policy by tool type:**

| Tool Type | Retry Behavior |
|---|---|
| Read tools (`get_*`, `search_*`) | Always safe to retry with backoff |
| Cart mutations (`update_*_cart`, `clear_cart`) | Safe to retry (server-idempotent on session) |
| Order placement (`place_food_order`, `checkout`, `book_table`) | Check-then-retry only — never blind retry |

**Backoff schedule:** 500ms → 1s → 2s → 4s, ±30% jitter per step, 30s wall-clock cap, 5 retries max.

### Order Orchestrator (`app/core/order_orchestrator.py`)

The only module permitted to call non-idempotent order placement tools. Routes and session manager must never call these directly.

**Non-idempotent tools guarded here:**
- `place_food_order` (Food)
- `checkout` (Instamart)
- `book_table` (Dineout)

**Check-then-retry pattern:**

```
On 5xx from order placement:
  1. Wait (exponential backoff with jitter)
  2. Call get_*_orders / get_booking_status
  3. If recent order found → treat as success (idempotency recovery)
  4. If not found → retry placement (max 3 attempts)
  5. After 3 failures → call report_error, surface error to user
```

**Pre-conditions verified before any placement call:**
- Food: cart total ≤ ₹1000, cart non-empty
- Instamart: cart total ≥ ₹99, cart non-empty
- Dineout: `slot_is_free=True`, `booking_price=0`

In-flight placement locks (`_active_placements` set) prevent duplicate concurrent calls for the same session and vertical.

### Error Classifier (`app/core/error_classifier.py`)

Classifies MCP errors into actionable buckets. In v1, Swiggy does not emit symbolic `error.code` fields — classification is by HTTP status + `error.message` text.

| Bucket | Detection | Action |
|---|---|---|
| Auth failure | HTTP 401 or JSON-RPC -32001 | Re-run OAuth flow |
| Bad input | HTTP 400 + "Invalid" / "Missing" | Fix arguments, do not retry |
| Upstream timeout | HTTP 504 or "timeout" in message | Backoff, max 5 retries |
| Upstream error | HTTP 502/503 | Backoff, max 5 retries |
| Domain failure | HTTP 200 + `success: false` | Surface to user immediately, call `report_error` |
| Food: cart cap | `success: false` + "₹1000" | Prompt user to remove items |
| Food: restaurant closed | `success: false` + "restaurant closed" | Re-run `search_restaurants` |
| Instamart: out of stock | `success: false` | Suggest alternatives via `search_products` |
| Instamart: minimum not met | `success: false` | Prompt user to add items |
| Dineout: slot unavailable | `success: false` | Refetch `get_available_slots` |

---

## 11. API Endpoints

All routes prefixed `/api/v1`.

| Method | Path | Description |
|---|---|---|
| `POST` | `/intent` | Parse user text, return intent classification |
| `POST` | `/session` | Create new session, return `session_id` |
| `POST` | `/session/{id}/turn` | Process a conversation turn (core orchestration loop) |
| `GET` | `/session/{id}/cart` | Live read of cart state from Swiggy servers |
| `POST` | `/session/{id}/confirm` | User confirms — trigger order placement sequence |
| `GET` | `/session/{id}/orders` | Return placed order references for tracking |
| `POST` | `/auth/callback` | OAuth 2.1 PKCE callback handler |
| `GET` | `/health` | Liveness check, returns `mock_mode` status |

Cart state is always a live read from Swiggy. There is no `/basket` endpoint — no local basket object exists.

---

## 12. Database Schema

VertexCart stores sessions, conversation history, and order references. It does not store Swiggy's commerce data — that lives on Swiggy's servers.

```sql
-- Active user sessions with OAuth tokens
CREATE TABLE sessions (
  id                UUID PRIMARY KEY,
  user_id           VARCHAR NOT NULL,
  swiggy_access_token TEXT,
  token_expires_at  TIMESTAMP,
  created_at        TIMESTAMP DEFAULT now(),
  last_active_at    TIMESTAMP
);

-- Full conversation history per session
CREATE TABLE conversation_turns (
  id            UUID PRIMARY KEY,
  session_id    UUID REFERENCES sessions(id),
  turn_number   INTEGER,
  role          VARCHAR CHECK (role IN ('user', 'agent')),
  content       TEXT,
  intent        JSONB,
  tools_called  JSONB,
  created_at    TIMESTAMP DEFAULT now()
);

-- References to orders placed on Swiggy (not order data — Swiggy owns that)
CREATE TABLE order_references (
  id               UUID PRIMARY KEY,
  session_id       UUID REFERENCES sessions(id),
  vertical         VARCHAR CHECK (vertical IN ('food', 'instamart', 'dineout')),
  swiggy_order_id  VARCHAR,
  placed_at        TIMESTAMP DEFAULT now(),
  status           VARCHAR DEFAULT 'placed'
);
```

No `baskets` table. Cart state is authoritative on Swiggy's servers and is read live on every turn.

---

## 13. Frontend

**Stack:** Next.js 14 (App Router), TypeScript, Tailwind CSS, Framer Motion. No component libraries.

### Color System (Swiggy co-branding compliant)

| Token | Hex | Usage |
|---|---|---|
| Swiggy Orange | `#FF5200` | Swiggy attribution, Food vertical accent |
| Background | `#0D0D0D` | Page background (dark mode only in v1) |
| Surface | `#1A1A1A` | Cards, panels |
| Surface Elevated | `#242424` | Nested surfaces |
| Text Primary | `#FFFFFF` | Primary content |
| Text Secondary | `#A0A0A0` | Labels, metadata |
| Instamart Green | `#00B383` | Instamart vertical accent |
| Dineout Purple | `#8B5CF6` | Dineout vertical accent |

### Screen Flow

**Screen 1 — Intent Input**
Full-screen input with a wide pill-shaped bar. Placeholder: *"Tell me what you're planning tonight..."*. Example intent chips below (e.g. "Book a table + order dessert"). Fade-in headline, slide-up input animation on load.

**Screen 2 — Parsing State**
Animated lanes per vertical (Food, Instamart, Dineout) showing which tools are being called. Items animate into their vertical lane as responses arrive. Skeleton loader if backend exceeds 1.5s.

**Screen 3 — Cart Preview**
Split column view. One column per engaged vertical. Each column shows: vertical name, items with prices, ETA badge, subtotal. Collapsible sidebar showing agent reasoning and intent classifications. User can correct the agent here ("actually get pasta from Food too").

**Screen 4 — Order Confirmation**
Sequential confirmation prompts — one per vertical. Cannot bundle into one button (platform constraint: each placement call is a separate non-idempotent action). Each prompt shows a live cart read from Swiggy before displaying. "Powered by Swiggy" badge required.

**Screen 5 — Order Status**
Both order IDs displayed. ETAs from tracking calls. Polls tracking every 10 seconds per Swiggy platform guidance.

### Key Components

| Component | File | Purpose |
|---|---|---|
| Intent input | `components/IntentInput.tsx` | Main prompt entry point |
| Parsing state | `components/ParsingState.tsx` | Animated vertical lanes during tool calls |
| Cart preview | `components/CartPreview.tsx` | Multi-column cart summary |
| Cart column | `components/CartColumn.tsx` | Per-vertical item list with ETA |
| Confirm order | `components/ConfirmOrder.tsx` | Sequential per-vertical confirmation |
| Order status | `components/OrderStatus.tsx` | Tracking view post-placement |
| Agent reasoning | `components/AgentReasoning.tsx` | Collapsible intent classification panel |
| Swiggy badge | `components/PoweredBySwiggy.tsx` | Co-branding attribution |

---

## 14. Local Setup

### Prerequisites

- Python 3.11+
- Node.js 18+
- PostgreSQL (or use Docker Compose)
- Swiggy MCP credentials (apply at `mcp.swiggy.com/builders/access`)

### Backend

```bash
# Clone and enter project
cd "Swiggy VertexCart"

# Create virtual environment
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env: set DATABASE_URL, GOOGLE_API_KEY, SWIGGY_CLIENT_ID, SWIGGY_CLIENT_SECRET

# Run database migrations
alembic upgrade head

# Start backend
uvicorn app.main:app --reload --port 8000
```

### Frontend

```bash
cd vertexcart-frontend

# Install dependencies
npm install

# Configure environment
cp .env.local.example .env.local
# Edit .env.local: set NEXT_PUBLIC_API_URL=http://localhost:8000

# Start dev server
npm run dev
```

### Docker (DB only)

```bash
docker-compose up -d
```

### Mock Mode

Set `MOCK_MODE=true` in `.env` to run without live Swiggy credentials. Mock responses are returned for all MCP tool calls. Useful for frontend development and testing without Builders Club access.

---

## 15. Testing

```bash
# Run all tests
pytest

# Run with verbose output
pytest -v

# Run specific test module
pytest tests/test_order_orchestrator.py -v
pytest tests/test_integration.py -v
```

### Test Coverage

| Test File | What It Tests |
|---|---|
| `test_intent_parser.py` | Entity classification, vertical assignment, clarification detection |
| `test_oauth_handler.py` | PKCE flow, token storage, expiry detection, re-auth |
| `test_session_manager.py` | Turn management, cart state reads, conflict detection |
| `test_mcp_client.py` | Tool call formatting, error parsing, retry behavior |
| `test_order_orchestrator.py` | Non-idempotency guards, check-then-retry, pre-condition checks |
| `test_error_classifier.py` | Error bucket classification by HTTP status + message text |
| `test_routes_smoke.py` | Smoke tests for all API routes |
| `test_integration.py` | End-to-end session flows with mock MCP responses |

---

## 16. Compliance and Data Handling

Per Swiggy MCP platform requirements:

- **Data Fiduciary:** Swiggy. VertexCart acts as a Data Processor within Swiggy's permitted scope under DPDP 2023.
- **Data use:** Swiggy-originated data (addresses, orders, restaurant data) may only be used to serve the user's immediate task. Not for analytics, advertising, or model training.
- **Logging:** Session IDs are logged for debugging and Swiggy support correlation. Full request/response bodies are not logged.
- **User IDs:** Hashed at rest. Not stored in plaintext.
- **Data deletion:** User requests for Swiggy-originated data deletion are directed to the Swiggy app. VertexCart deletes its own session records on request.
- **Geography:** India only in v1. AWS Mumbai primary, AWS Singapore failover. Inference outside India requires a signed Data Processing Agreement with Swiggy before production deployment.

---

## 17. v1 Limitations and Roadmap

| Limitation | User Impact | Resolution Path |
|---|---|---|
| COD only | Segments out online-payment-preferred users | Swiggy v2 payment API roadmap |
| ₹1000 Food cart cap | Limits upsell on Food vertical | Enterprise tier negotiation with Swiggy |
| No scheduled delivery | "Dessert at 10pm" flow not automatable | Agent prompts user at right time; scheduling in Swiggy roadmap |
| Two confirmation taps | One per vertical instead of one unified checkout | Platform constraint; reframed as per-order safety confirmation |
| Free Dineout only | Premium restaurant bookings not supported | Paid reservations in Swiggy roadmap |
| No Swiggy One API | Membership savings not surfaced | Partner-level API access (v2) |
| No refresh tokens | Full re-auth on token expiry (every 5 days) | Swiggy v1.1 adds refresh tokens |
| Custom cart UI | Cannot use Swiggy's hosted widget cards | Swiggy v1.1 ships hosted widget layer; iframe integration pre-documented |

### v2 Targets

- Swiggy One membership status + savings display (requires partner API access)
- Online payment methods (Swiggy platform roadmap)
- Scheduled delivery for pre-planned orders
- Native Swiggy widget rendering via iframe layer
- Higher Food cart cap (enterprise tier)
- Refresh token support (Swiggy v1.1)

---

*Built on Swiggy MCP — [mcp.swiggy.com/builders](https://mcp.swiggy.com/builders)*
