from __future__ import annotations

"""
Error classifier for Swiggy MCP responses.
PRD ref: Section 8.3 (Module 6 — Error Classifier)

Swiggy MCP v1 does NOT emit symbolic error.code values.
Classification uses HTTP status + error.message text pattern matching.
Full unit tests in tests/test_error_classifier.py (Sprint 5).
"""

from pydantic import BaseModel


class ErrorClassification(BaseModel):
    bucket: str
    is_retryable: bool
    user_message: str = ""
    action: str


def classify(
    http_status: int,
    error_message: str,
    tool_name: str = "",
) -> ErrorClassification:
    """
    Classify a Swiggy MCP error into an actionable bucket.

    Args:
        http_status: HTTP response status code
        error_message: error.message string from JSON-RPC body (or network error string)
        tool_name: tool that failed — used for logging context only

    Returns:
        ErrorClassification with bucket, retryability, user-facing message, action.

    PRD ref: Section 8.3 (Module 6 — error bucket table)
    """
    msg = error_message.lower()

    # ── Auth failures ──────────────────────────────────────────────────────
    if http_status == 401:
        return ErrorClassification(
            bucket="auth_failure",
            is_retryable=False,
            action="re_auth",
        )

    # ── Bad input ──────────────────────────────────────────────────────────
    if http_status == 400 or (
        http_status == 200 and (msg.startswith("invalid") or msg.startswith("missing"))
    ):
        return ErrorClassification(
            bucket="bad_input",
            is_retryable=False,
            action="fix_args",
        )

    # ── Upstream timeout ───────────────────────────────────────────────────
    if http_status == 504 or "timeout" in msg:
        return ErrorClassification(
            bucket="upstream_timeout",
            is_retryable=True,
            action="backoff_retry",
        )

    # ── Upstream errors (gateway) ─────────────────────────────────────────
    if http_status in (502, 503):
        return ErrorClassification(
            bucket="upstream_error",
            is_retryable=True,
            action="backoff_retry",
        )

    # ── Internal server error ─────────────────────────────────────────────
    if http_status == 500:
        return ErrorClassification(
            bucket="internal_error",
            is_retryable=True,
            action="backoff_once_then_report",
        )

    # ── Domain failures (HTTP 200 + success=false) — order matters ────────

    if "1000" in msg or "cart cap" in msg or "cart limit" in msg:
        return ErrorClassification(
            bucket="food_cart_cap",
            is_retryable=False,
            user_message="Food orders are capped at ₹1000 in this session.",
            action="reduce_items",
        )

    if "minimum" in msg or "min order" in msg:
        return ErrorClassification(
            bucket="instamart_minimum",
            is_retryable=False,
            user_message="Add items to meet the ₹99 minimum.",
            action="add_items",
        )

    if "out of stock" in msg or "unavailable" in msg:
        return ErrorClassification(
            bucket="item_unavailable",
            is_retryable=False,
            action="suggest_alternatives",
        )

    if "not serviceable" in msg or "unserviceable" in msg:
        return ErrorClassification(
            bucket="address_not_serviceable",
            is_retryable=False,
            action="ask_alternative_address",
        )

    if "restaurant closed" in msg or "closed" in msg:
        return ErrorClassification(
            bucket="restaurant_closed",
            is_retryable=False,
            action="re_search",
        )

    # ── Catch-all domain failure ───────────────────────────────────────────
    return ErrorClassification(
        bucket="domain_failure",
        is_retryable=False,
        action="surface_to_user",
    )
