"""
PostgreSQL connection pool via asyncpg.
PRD ref: Section 8.3 (Database Schema)

Pool config: min=2, max=10 connections.
Use get_connection() as an async context manager in route handlers.
"""

from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional

import asyncpg

from app.config import settings

_pool: Optional[asyncpg.Pool] = None


async def init_pool() -> None:
    """Create the connection pool. Called once at application startup."""
    global _pool
    _pool = await asyncpg.create_pool(
        dsn=settings.database_url,
        min_size=2,
        max_size=10,
    )


async def close_pool() -> None:
    """Drain and close the pool. Called on application shutdown."""
    global _pool
    if _pool:
        await _pool.close()
        _pool = None


@asynccontextmanager
async def get_connection() -> AsyncGenerator[asyncpg.Connection, None]:
    """Yield a single connection from the pool."""
    if _pool is None:
        raise RuntimeError("Database pool not initialised. Call init_pool() first.")
    async with _pool.acquire() as conn:
        yield conn
