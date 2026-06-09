from __future__ import annotations
"""
VertexCart — FastAPI application entry point.
PRD ref: Section 8.1 (Architecture), Section 8.3 (Module 7 — FastAPI Endpoints)

Startup sequence:
  1. Verify PostgreSQL connection
  2. Register all routers under /api/v1
  3. Apply CORS middleware
  4. Apply request logging middleware (logs session_id per Swiggy compliance)
"""

import logging
import time
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.db.connection import close_pool, create_pool
from app.core.mcp_client import mcp_client
from app.api.routes import auth, cart, confirm, intent, orders, session, turn

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown lifecycle."""
    # ── Startup ───────────────────────────────────────────────────────────
    await mcp_client.start()
    logger.info("MCP HTTP clients initialised")

    try:
        await create_pool()
        logger.info("Database pool initialised")
    except Exception as exc:
        logger.error("Database connection failed on startup: %s", exc)
        if not settings.mock_mode:
            raise

    yield

    # ── Shutdown ──────────────────────────────────────────────────────────
    await mcp_client.stop()
    await close_pool()
    logger.info("MCP clients and database pool closed")


app = FastAPI(
    title="VertexCart",
    description="Conversational commerce agent on Swiggy MCP",
    version="1.0.0",
    lifespan=lifespan,
)

# ── Middleware ────────────────────────────────────────────────────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    """
    Log session_id on every request for Swiggy support correlation.
    PRD ref: Section 11 (Compliance — log session IDs for debugging)
    """
    session_id = (
        request.path_params.get("session_id")
        or request.headers.get("X-Session-Id")
        or "no-session"
    )
    request_id = str(uuid.uuid4())[:8]
    start = time.time()

    response = await call_next(request)

    duration_ms = round((time.time() - start) * 1000)
    logger.info(
        "request",
        extra={
            "request_id": request_id,
            "session_id": session_id if settings.log_session_ids else "redacted",
            "method": request.method,
            "path": request.url.path,
            "status": response.status_code,
            "duration_ms": duration_ms,
        },
    )
    return response


# ── Lifecycle ─────────────────────────────────────────────────────────────────

# ── Routes ────────────────────────────────────────────────────────────────────

API_PREFIX = "/api/v1"

app.include_router(intent.router, prefix=API_PREFIX, tags=["intent"])
app.include_router(session.router, prefix=API_PREFIX, tags=["session"])
app.include_router(turn.router, prefix=API_PREFIX, tags=["turn"])
app.include_router(cart.router, prefix=API_PREFIX, tags=["cart"])
app.include_router(confirm.router, prefix=API_PREFIX, tags=["confirm"])
app.include_router(orders.router, prefix=API_PREFIX, tags=["orders"])
app.include_router(auth.router, prefix=API_PREFIX, tags=["auth"])


# ── Health ────────────────────────────────────────────────────────────────────

@app.get("/health", tags=["health"])
async def health_check():
    """
    Liveness probe. Returns mock_mode status so callers know which data is real.
    PRD ref: Section 8.3 (FastAPI Endpoints)
    """
    return {"status": "ok", "mock_mode": settings.mock_mode}
