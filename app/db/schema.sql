-- VertexCart — PostgreSQL schema
-- PRD ref: Section 8.3 (Database Schema)
--
-- Design note: There is NO cart/basket table here.
-- Cart state is server-side on Swiggy. We only store session context,
-- conversation history, and order references (IDs after placement).

CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ── Sessions ──────────────────────────────────────────────────────────────────
-- One row per user conversation session.
-- Holds the OAuth token for Swiggy MCP calls scoped to this session.
CREATE TABLE IF NOT EXISTS sessions (
    id                  UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id             VARCHAR     NOT NULL,
    swiggy_access_token TEXT,                           -- JWT from Swiggy OAuth 2.1 PKCE
    token_expires_at    TIMESTAMP,
    created_at          TIMESTAMP   NOT NULL DEFAULT now(),
    last_active_at      TIMESTAMP   NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON sessions (user_id);
CREATE INDEX IF NOT EXISTS idx_sessions_last_active ON sessions (last_active_at DESC);

-- ── Conversation turns ────────────────────────────────────────────────────────
-- One row per user or agent message within a session.
-- intent and tools_called stored as JSONB for schema flexibility.
CREATE TABLE IF NOT EXISTS conversation_turns (
    id           UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id   UUID        NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    turn_number  INTEGER     NOT NULL,
    role         VARCHAR     NOT NULL CHECK (role IN ('user', 'agent')),
    content      TEXT        NOT NULL,
    intent       JSONB,      -- IntentResult JSON (user turns only)
    tools_called JSONB,      -- list of {tool, vertical, success} (agent turns only)
    created_at   TIMESTAMP   NOT NULL DEFAULT now()
);

-- Supports get_conversation_history(session_id) — last N turns ordered by recency
CREATE INDEX IF NOT EXISTS idx_turns_session_created
    ON conversation_turns (session_id, created_at DESC);

-- ── Order references ──────────────────────────────────────────────────────────
-- Stores Swiggy-issued order IDs after successful placement.
-- We do NOT store order contents — Swiggy owns the order data.
CREATE TABLE IF NOT EXISTS order_references (
    id               UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id       UUID        NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    vertical         VARCHAR     NOT NULL CHECK (vertical IN ('food', 'instamart', 'dineout')),
    swiggy_order_id  VARCHAR     NOT NULL,
    placed_at        TIMESTAMP   NOT NULL DEFAULT now(),
    status           VARCHAR     NOT NULL DEFAULT 'placed'
);

CREATE INDEX IF NOT EXISTS idx_order_refs_session ON order_references (session_id);
