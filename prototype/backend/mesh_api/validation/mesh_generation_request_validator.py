from __future__ import annotations

from typing import Any, Optional

from ..errors.api_exceptions import ValidationException
from ..models.geographic_point import GeographicPoint
from ..models.mesh_generation_request import MeshGenerationRequest

MINIMUM_POINT_COUNT = 3

MINIMUM_LATITUDE = -90.0
MAXIMUM_LATITUDE = 90.0
MINIMUM_LONGITUDE = -180.0
MAXIMUM_LONGITUDE = 180.0

DEFAULT_PARTITION_COUNT = 1
MAXIMUM_PARTITION_COUNT = 32


class MeshGenerationRequestValidator:
    """Validates the raw request body and converts it into a domain object
    (``MeshGenerationRequest``).

    Every inconsistency found is accumulated and reported at once, giving the
    client a complete message about what needs to be fixed instead of failing
    on the first error.
    """

    def validate_and_convert(self, request_body: Any) -> MeshGenerationRequest:
        if not isinstance(request_body, dict):
            raise ValidationException(
                "The request body must be a JSON object.",
                details=["Send a JSON object containing at least the 'boundaryPoints' field."],
            )

        error_details: list[str] = []

        boundary_points = self._validate_boundary_points(
            request_body.get("boundaryPoints"), error_details
        )
        max_edge_length = self._validate_max_edge_length(
            request_body.get("maxEdgeLength"), error_details
        )
        sensor_range_meters = self._validate_sensor_range_meters(
            request_body.get("sensorRangeMeters"), error_details
        )
        partition_count = self._validate_partition_count(
            request_body.get("partitionCount"), len(boundary_points), error_details
        )

        if error_details:
            raise ValidationException(
                "The request could not be processed: it contains invalid data.",
                details=error_details,
            )

        return MeshGenerationRequest(
            boundary_points=boundary_points,
            max_edge_length=max_edge_length,
            partition_count=partition_count,
            sensor_range_meters=sensor_range_meters,
        )

    def _validate_boundary_points(
        self, raw_points: Any, error_details: list[str]
    ) -> list[GeographicPoint]:
        if raw_points is None:
            error_details.append("The 'boundaryPoints' field is required.")
            return []
        if not isinstance(raw_points, list):
            error_details.append("The 'boundaryPoints' field must be a list of objects.")
            return []
        if len(raw_points) < MINIMUM_POINT_COUNT:
            error_details.append(
                f"At least {MINIMUM_POINT_COUNT} points are required to generate the mesh; "
                f"{len(raw_points)} were received."
            )
            return []

        validated_points: list[GeographicPoint] = []
        for index, raw_point in enumerate(raw_points):
            point = self._validate_single_point(index, raw_point, error_details)
            if point is not None:
                validated_points.append(point)
        return validated_points

    def _validate_single_point(
        self, index: int, raw_point: Any, error_details: list[str]
    ) -> Optional[GeographicPoint]:
        if not isinstance(raw_point, dict):
            error_details.append(
                f"The point at position {index} must be an object with 'lat' and 'lng'."
            )
            return None

        latitude = raw_point.get("lat")
        longitude = raw_point.get("lng")

        if not self._is_number(latitude) or not self._is_number(longitude):
            error_details.append(
                f"The point at position {index} must contain numeric 'lat' and 'lng'."
            )
            return None
        if not MINIMUM_LATITUDE <= latitude <= MAXIMUM_LATITUDE:
            error_details.append(
                f"The latitude of the point at position {index} must be between "
                f"{MINIMUM_LATITUDE} and {MAXIMUM_LATITUDE}."
            )
            return None
        if not MINIMUM_LONGITUDE <= longitude <= MAXIMUM_LONGITUDE:
            error_details.append(
                f"The longitude of the point at position {index} must be between "
                f"{MINIMUM_LONGITUDE} and {MAXIMUM_LONGITUDE}."
            )
            return None

        return GeographicPoint(latitude=float(latitude), longitude=float(longitude))

    def _validate_max_edge_length(
        self, value: Any, error_details: list[str]
    ) -> Optional[float]:
        if value is None:
            return None
        if not self._is_number(value) or value <= 0:
            error_details.append(
                "The 'maxEdgeLength' field, when provided, must be a number greater than zero."
            )
            return None
        return float(value)

    def _validate_partition_count(
        self, value: Any, boundary_point_count: int, error_details: list[str]
    ) -> int:
        if value is None:
            return DEFAULT_PARTITION_COUNT
        # Reject booleans and non-integer numbers: the partition count is a
        # strictly positive integer.
        if isinstance(value, bool) or not isinstance(value, int):
            error_details.append("The 'partitionCount' field must be a positive integer.")
            return DEFAULT_PARTITION_COUNT
        if value < 1:
            error_details.append("The 'partitionCount' field must be greater than or equal to 1.")
            return DEFAULT_PARTITION_COUNT
        if value > MAXIMUM_PARTITION_COUNT:
            error_details.append(
                f"The 'partitionCount' field must be at most {MAXIMUM_PARTITION_COUNT}."
            )
            return DEFAULT_PARTITION_COUNT

        # Geometry-based cap (mirrors the frontend). A simple polygon with N
        # boundary points decomposes into N - 2 triangles, and a mesh cannot be
        # split into more parts than it has triangles. This cap is only applied
        # once the boundary itself is valid (>= MINIMUM_POINT_COUNT points);
        # otherwise the boundary error already explains the real problem.
        if boundary_point_count >= MINIMUM_POINT_COUNT:
            geometric_maximum = boundary_point_count - 2
            if value > geometric_maximum:
                error_details.append(
                    f"The 'partitionCount' field must be at most {geometric_maximum} "
                    f"for an area with {boundary_point_count} points: a polygon with "
                    f"N points yields N-2 triangles, and the mesh cannot be split "
                    f"into more parts than it has triangles."
                )
                return DEFAULT_PARTITION_COUNT
        return value

    def _validate_sensor_range_meters(
        self, value: Any, error_details: list[str]
    ) -> Optional[float]:
        if value is None:
            return None
        if not self._is_number(value) or value <= 0:
            error_details.append(
                "The 'sensorRangeMeters' field, when provided, must be a number greater than zero."
            )
            return None
        return float(value)

    @staticmethod
    def _is_number(value: Any) -> bool:
        # Explicitly exclude booleans, which in Python are int instances but do
        # not represent valid coordinates or distances.
        return isinstance(value, (int, float)) and not isinstance(value, bool)
