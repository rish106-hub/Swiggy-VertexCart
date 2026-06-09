"""
Error classifier for Swiggy MCP responses.
PRD ref: Section 8.3 (Module 6 — Error Classifier)

Swiggy MCP v1 does NOT emit symbolic error.code values.
Classification uses HTTP status + error.message text pattern matching.

Stub: filled in Sprint 5.
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
        error_message: error.message string from JSON-RPC response body
        tool_name: name of the tool that failed (for logging context)

    Returns:
        ErrorClassification with bucket, retryability, user-facing message, and action
    """
    raise NotImplementedError("Error classifier implemented in Sprint 5")
