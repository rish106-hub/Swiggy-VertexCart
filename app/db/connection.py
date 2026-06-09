from __future__ import annotations

"""
Database connection management using asyncpg.
PRD ref: Section 8.3 (Database Schema), Phase 5 implementation.

Provides a connection pool initialized at app startup and closed at shutdown.
Provides a get_connection() context manager for database operations.
"""

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

import asyncpg

from app.config import settings

logger = logging.getLogger(__name__)

# Global connection pool instance
_pool: asyncpg.Pool | None = None


async def create_pool() -> None:
    """Initialize the asyncpg connection pool."""
    global _pool
    if _pool is not None:
        return

    try:
        _pool = await asyncpg.create_pool(
            dsn=settings.database_url,
            min_size=2,
            max_size=10,
            command_timeout=60,
        )
        logger.info("Database connection pool created.")
    except Exception as exc:
        logger.error("Failed to create database connection pool: %s", exc)
        raise


async def close_pool() -> None:
    """Close the asyncpg connection pool."""
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None
        logger.info("Database connection pool closed.")


@asynccontextmanager
async def get_connection() -> AsyncGenerator[asyncpg.Connection, None]:
    """
    Acquire a connection from the pool.
    Usage:
        async with get_connection() as conn:
            await conn.execute(...)
    """
    if _pool is None:
        raise RuntimeError("Database pool is not initialized. Call create_pool() first.")

    async with _pool.acquire() as connection:
        yield connection
