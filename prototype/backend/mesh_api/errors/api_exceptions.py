from __future__ import annotations

from typing import Optional


class ApiException(Exception):
    """Base exception for business errors handled in a standardized way.

    Each subclass defines its HTTP status code and a stable textual error code,
    allowing the global error handler to convert the exception into a
    consistent response without any try/except blocks in the controllers.
    """

    http_status: int = 500
    error_code: str = "INTERNAL_ERROR"

    def __init__(self, message: str, details: Optional[list[str]] = None):
        super().__init__(message)
        self.message = message
        self.details = details or []


class ValidationException(ApiException):
    """Raised for invalid or missing input data (HTTP 400)."""

    http_status = 400
    error_code = "INVALID_INPUT"


class InvalidGeometryException(ApiException):
    """Raised when the points are individually valid but do not form a
    processable geometry (e.g. collinear or coincident points) (HTTP 422)."""

    http_status = 422
    error_code = "INVALID_GEOMETRY"
