from __future__ import annotations

"""
Unit tests for error classifier.
PRD ref: Section 8.3 (Module 6 — Error Classifier, bucket table)

Covers all 11 buckets defined in the PRD plus edge cases.
"""

import pytest

from app.core.error_classifier import classify, ErrorClassification


# ── Helpers ───────────────────────────────────────────────────────────────────

def assert_bucket(
    http_status: int,
    message: str,
    expected_bucket: str,
    expected_retryable: bool,
    expected_action: str,
    tool_name: str = "test_tool",
) -> ErrorClassification:
    result = classify(http_status, message, tool_name)
    assert result.bucket == expected_bucket, (
        f"Expected bucket '{expected_bucket}', got '{result.bucket}' "
        f"for status={http_status} msg='{message}'"
    )
    assert result.is_retryable == expected_retryable, (
        f"Expected is_retryable={expected_retryable} for bucket '{expected_bucket}'"
    )
    assert result.action == expected_action, (
        f"Expected action '{expected_action}', got '{result.action}'"
    )
    return result


# ── Bucket 1: auth_failure ────────────────────────────────────────────────────

class TestAuthFailure:
    def test_http_401(self):
        assert_bucket(401, "", "auth_failure", False, "re_auth")

    def test_http_401_with_message(self):
        assert_bucket(401, "Token expired", "auth_failure", False, "re_auth")

    def test_is_not_retryable(self):
        result = classify(401, "unauthorized")
        assert result.is_retryable is False


# ── Bucket 2: bad_input ───────────────────────────────────────────────────────

class TestBadInput:
    def test_http_400(self):
        assert_bucket(400, "Invalid request", "bad_input", False, "fix_args")

    def test_http_400_missing_field(self):
        assert_bucket(400, "Missing required field addressId", "bad_input", False, "fix_args")

    def test_http_200_invalid_message(self):
        assert_bucket(200, "Invalid addressId format", "bad_input", False, "fix_args")

    def test_http_200_missing_message(self):
        assert_bucket(200, "Missing restaurantId", "bad_input", False, "fix_args")

    def test_is_not_retryable(self):
        result = classify(400, "bad param")
        assert result.is_retryable is False


# ── Bucket 3: upstream_timeout ────────────────────────────────────────────────

class TestUpstreamTimeout:
    def test_http_504(self):
        assert_bucket(504, "", "upstream_timeout", True, "backoff_retry")

    def test_message_contains_timeout(self):
        assert_bucket(200, "upstream timeout reached", "upstream_timeout", True, "backoff_retry")

    def test_message_timeout_case_insensitive(self):
        assert_bucket(200, "TIMEOUT after 30s", "upstream_timeout", True, "backoff_retry")

    def test_is_retryable(self):
        result = classify(504, "")
        assert result.is_retryable is True


# ── Bucket 4: upstream_error ──────────────────────────────────────────────────

class TestUpstreamError:
    def test_http_502(self):
        assert_bucket(502, "", "upstream_error", True, "backoff_retry")

    def test_http_503(self):
        assert_bucket(503, "", "upstream_error", True, "backoff_retry")

    def test_is_retryable(self):
        result = classify(502, "bad gateway")
        assert result.is_retryable is True


# ── Bucket 5: internal_error ──────────────────────────────────────────────────

class TestInternalError:
    def test_http_500(self):
        assert_bucket(500, "", "internal_error", True, "backoff_once_then_report")

    def test_is_retryable_once(self):
        result = classify(500, "internal server error")
        assert result.is_retryable is True
        assert result.action == "backoff_once_then_report"


# ── Bucket 6: food_cart_cap ───────────────────────────────────────────────────

class TestFoodCartCap:
    def test_message_contains_1000(self):
        result = assert_bucket(
            200, "cart exceeds ₹1000 limit", "food_cart_cap", False, "reduce_items"
        )
        assert "₹1000" in result.user_message

    def test_message_cart_cap(self):
        assert_bucket(200, "cart cap reached", "food_cart_cap", False, "reduce_items")

    def test_message_cart_limit(self):
        assert_bucket(200, "cart limit exceeded", "food_cart_cap", False, "reduce_items")

    def test_user_message_is_set(self):
        result = classify(200, "₹1000 cart limit")
        assert result.user_message != ""

    def test_is_not_retryable(self):
        result = classify(200, "1000 limit")
        assert result.is_retryable is False


# ── Bucket 7: instamart_minimum ───────────────────────────────────────────────

class TestInstamartMinimum:
    def test_message_minimum(self):
        result = assert_bucket(
            200, "cart below minimum order value", "instamart_minimum", False, "add_items"
        )
        assert "₹99" in result.user_message

    def test_message_min_order(self):
        assert_bucket(200, "min order not met", "instamart_minimum", False, "add_items")

    def test_user_message_is_set(self):
        result = classify(200, "minimum order requirement not met")
        assert result.user_message != ""

    def test_is_not_retryable(self):
        result = classify(200, "minimum not met")
        assert result.is_retryable is False


# ── Bucket 8: item_unavailable ────────────────────────────────────────────────

class TestItemUnavailable:
    def test_out_of_stock(self):
        assert_bucket(200, "item is out of stock", "item_unavailable", False, "suggest_alternatives")

    def test_unavailable(self):
        assert_bucket(200, "product unavailable at this location", "item_unavailable", False, "suggest_alternatives")

    def test_is_not_retryable(self):
        result = classify(200, "out of stock")
        assert result.is_retryable is False


# ── Bucket 9: address_not_serviceable ────────────────────────────────────────

class TestAddressNotServiceable:
    def test_not_serviceable(self):
        assert_bucket(
            200, "address not serviceable", "address_not_serviceable", False, "ask_alternative_address"
        )

    def test_unserviceable(self):
        assert_bucket(
            200, "location is unserviceable", "address_not_serviceable", False, "ask_alternative_address"
        )

    def test_is_not_retryable(self):
        result = classify(200, "not serviceable")
        assert result.is_retryable is False


# ── Bucket 10: restaurant_closed ─────────────────────────────────────────────

class TestRestaurantClosed:
    def test_restaurant_closed(self):
        assert_bucket(200, "restaurant closed", "restaurant_closed", False, "re_search")

    def test_closed_keyword(self):
        assert_bucket(200, "this restaurant is currently closed", "restaurant_closed", False, "re_search")

    def test_is_not_retryable(self):
        result = classify(200, "restaurant closed")
        assert result.is_retryable is False


# ── Bucket 11: domain_failure (catch-all) ────────────────────────────────────

class TestDomainFailure:
    def test_http_200_unknown_message(self):
        assert_bucket(200, "something went wrong", "domain_failure", False, "surface_to_user")

    def test_empty_message(self):
        assert_bucket(200, "", "domain_failure", False, "surface_to_user")

    def test_is_not_retryable(self):
        result = classify(200, "unrecognised error condition")
        assert result.is_retryable is False


# ── Priority ordering — more specific buckets win ────────────────────────────

class TestBucketPriority:
    def test_401_beats_message_content(self):
        """HTTP 401 must always be auth_failure regardless of message."""
        result = classify(401, "minimum order not met")
        assert result.bucket == "auth_failure"

    def test_cart_cap_beats_domain_failure(self):
        result = classify(200, "order exceeds ₹1000 cap")
        assert result.bucket == "food_cart_cap"

    def test_timeout_message_on_200_beats_domain_failure(self):
        result = classify(200, "gateway timeout occurred")
        assert result.bucket == "upstream_timeout"

    def test_504_beats_domain_failure(self):
        result = classify(504, "something went wrong")
        assert result.bucket == "upstream_timeout"


# ── Return type integrity ─────────────────────────────────────────────────────

class TestReturnType:
    def test_always_returns_error_classification(self):
        for status in (200, 400, 401, 500, 502, 503, 504):
            result = classify(status, "some message")
            assert isinstance(result, ErrorClassification)

    def test_bucket_is_always_string(self):
        result = classify(200, "")
        assert isinstance(result.bucket, str)
        assert len(result.bucket) > 0

    def test_action_is_always_string(self):
        result = classify(200, "")
        assert isinstance(result.action, str)
        assert len(result.action) > 0
