from __future__ import annotations

import numpy as np

from ..models.geographic_point import GeographicPoint
from .geometry import is_point_inside_polygon, is_point_on_polygon_boundary


class SensorPlacementService:
    """Suggests candidate sensor locations from an existing triangulation.

    Strategy and rationale
    -----------------------
    Candidate sensors are the internal vertices shared by at least three mesh
    triangles. This places one sensor at each junction of the mesh, avoids
    duplicate coordinates, and leaves boundary vertices out of the suggestions.
    """

    def suggest_candidates(
        self,
        mesh_coordinates: np.ndarray,
        triangles: list[list[int]],
        polygon_coordinates: np.ndarray,
    ) -> list[GeographicPoint]:
        polygon = polygon_coordinates.tolist()
        triangle_incidence = np.zeros(len(mesh_coordinates), dtype=int)
        for triangle in triangles:
            for point_index in set(triangle):
                triangle_incidence[point_index] += 1

        return [
            GeographicPoint.from_longitude_latitude_pair(
                mesh_coordinates[point_index].tolist()
            )
            for point_index, point in enumerate(mesh_coordinates)
            if triangle_incidence[point_index] >= 3
            and is_point_inside_polygon(point, polygon)
            and not is_point_on_polygon_boundary(point, polygon)
        ]
