from __future__ import annotations

from typing import Optional

from flask import Response, jsonify


class StandardizedApiResponse:
    """Builds HTTP responses with a standardized, consistent envelope.

    Success: ``{"success": true,  "data": <content>, "error": null}``
    Error:   ``{"success": false, "data": null, "error": {code, message, details}}``

    Standardizing the envelope makes consumption easier for external clients and
    for the prototype, which can always inspect the ``success`` flag before
    handling the data or the error.
    """

    @staticmethod
    def success(data, http_status: int = 200) -> Response:
        response = jsonify({"success": True, "data": data, "error": None})
        response.status_code = http_status
        return response

    @staticmethod
    def error(
        message: str,
        error_code: str,
        http_status: int,
        details: Optional[list[str]] = None,
    ) -> Response:
        body = {
            "success": False,
            "data": None,
            "error": {
                "code": error_code,
                "message": message,
                "details": details or [],
            },
        }
        response = jsonify(body)
        response.status_code = http_status
        return response
