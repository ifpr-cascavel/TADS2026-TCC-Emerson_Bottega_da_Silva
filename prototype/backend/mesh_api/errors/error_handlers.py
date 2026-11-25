from __future__ import annotations

from flask import Flask
from flask_limiter.errors import RateLimitExceeded
from werkzeug.exceptions import HTTPException

from ..responses.standardized_api_response import StandardizedApiResponse
from .api_exceptions import ApiException


def register_error_handlers(application: Flask) -> None:
    """Register the application's global exception handling.

    Concentrating error handling here avoids duplicating try/except blocks in
    the controllers (DRY) and guarantees that any failure is returned to the
    client in the same standardized format.
    """

    @application.errorhandler(ApiException)
    def handle_business_exception(exception: ApiException):
        return StandardizedApiResponse.error(
            message=exception.message,
            error_code=exception.error_code,
            http_status=exception.http_status,
            details=exception.details,
        )

    @application.errorhandler(404)
    def handle_resource_not_found(_exception):
        return StandardizedApiResponse.error(
            message="Resource not found.",
            error_code="RESOURCE_NOT_FOUND",
            http_status=404,
        )

    @application.errorhandler(405)
    def handle_method_not_allowed(_exception):
        return StandardizedApiResponse.error(
            message="HTTP method not allowed for this resource.",
            error_code="METHOD_NOT_ALLOWED",
            http_status=405,
        )

    @application.errorhandler(RateLimitExceeded)
    def handle_rate_limit_exceeded(exception: RateLimitExceeded):
        response = StandardizedApiResponse.error(
            message="Too many mesh generation requests. Please try again later.",
            error_code="RATE_LIMIT_EXCEEDED",
            http_status=429,
        )
        if exception.retry_after:
            response.headers["Retry-After"] = str(exception.retry_after)
        return response

    @application.errorhandler(Exception)
    def handle_unexpected_error(exception: Exception):
        # Preserve the original status of Flask/Werkzeug HTTP exceptions.
        if isinstance(exception, HTTPException):
            return StandardizedApiResponse.error(
                message=exception.description or "Error while processing the request.",
                error_code="HTTP_ERROR",
                http_status=exception.code or 500,
            )
        # Any other unexpected failure is wrapped as an internal error, without
        # leaking implementation details to the client.
        return StandardizedApiResponse.error(
            message="An internal error occurred while processing the request.",
            error_code="INTERNAL_ERROR",
            http_status=500,
        )
