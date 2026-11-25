from __future__ import annotations

import math
from typing import Optional

import numpy as np
import triangle as triangle_library
from scipy.spatial import QhullError, Voronoi

from ..errors.api_exceptions import InvalidGeometryException, ValidationException
from ..models.geographic_point import GeographicPoint
from ..models.mesh_generation_request import MeshGenerationRequest
from ..models.mesh_generation_result import MeshGenerationResult, VoronoiEdge
from .geometry import clip_segment_to_polygon, compute_polygon_area, is_simple_polygon
from .mesh_partitioning_service import MeshPartitioningService
from .sensor_placement_service import SensorPlacementService

# Minimum interior angle (degrees) enforced by the quality triangulation. It
# keeps triangles well-shaped (avoids slivers) while staying below the 34° limit
# above which Triangle's convergence is no longer guaranteed.
DEFAULT_MINIMUM_ANGLE_DEGREES = 25.0

# Meters spanned by one degree of latitude. Practically constant over the globe
# (~111.32 km); used to convert the user's edge length (in meters) into the
# degree units the triangulation works in.
METERS_PER_DEGREE_LATITUDE = 111_320.0

# Upper bound on the *estimated* number of triangles a refinement may produce
# (estimate = polygon area / target triangle area). Its purpose is to protect
# both the API (an over-refined mesh can take very long to build/serialize) and
# any client rendering it: an edge length of a couple of meters over an area of
# hundreds of meters would generate tens of thousands of triangles and stall the
# request. The quality step adds ~50-60% Steiner triangles on top of the
# estimate, so the real mesh stays roughly within ~1.6x this value. The limit is
# geometry-relative (derived from the drawn area), not a fixed edge length, so
# it scales correctly for both small and large areas. Tunable if needed.
MAXIMUM_ESTIMATED_TRIANGLES = 3000


class MeshGenerationService:
    """Generates the computational mesh (a Constrained Delaunay Triangulation)
    and the corresponding Voronoi diagram from a set of geographic points.

    Unlike an ordinary Delaunay triangulation, which always fills the *convex
    hull* of the points and therefore leaks triangles outside a non-convex area,
    a Constrained Delaunay Triangulation (CDT) forces the polygon boundary edges
    into the triangulation and discards everything outside them. As a result the
    mesh is produced **exclusively inside** the delimited polygon.
    """

    def __init__(
        self,
        minimum_angle_degrees: float = DEFAULT_MINIMUM_ANGLE_DEGREES,
        sensor_placement_service: Optional[SensorPlacementService] = None,
        mesh_partitioning_service: Optional[MeshPartitioningService] = None,
    ):
        self._minimum_angle_degrees = minimum_angle_degrees
        self._sensor_placement_service = sensor_placement_service or SensorPlacementService()
        self._mesh_partitioning_service = mesh_partitioning_service or MeshPartitioningService()

    def generate(self, request: MeshGenerationRequest) -> MeshGenerationResult:
        polygon_coordinates = np.array(
            [point.to_longitude_latitude_pair() for point in request.boundary_points]
        )

        # Reject self-intersecting boundaries (e.g. lines drawn crossing over one
        # another): they do not delimit a single region, so any mesh built on top
        # of them would be inconsistent.
        if not is_simple_polygon(polygon_coordinates.tolist()):
            raise self._self_intersecting_geometry_error()

        # The user provides the refinement target in meters (intuitive on a map);
        # the triangulation works in degrees, so convert it up front.
        max_edge_length_degrees = self._meters_to_degrees(
            request.max_edge_length, polygon_coordinates
        )

        # Guard against an over-refined mesh that would stall generation/rendering.
        self._ensure_refinement_within_budget(
            max_edge_length_degrees, polygon_coordinates
        )

        triangles, mesh_coordinates = self._build_constrained_triangulation(
            polygon_coordinates, max_edge_length_degrees
        )

        voronoi_vertices, voronoi_edges = self._build_voronoi_diagram(
            mesh_coordinates, polygon_coordinates
        )

        sensor_candidates = self._sensor_placement_service.suggest_candidates(
            mesh_coordinates, triangles, polygon_coordinates
        )

        triangle_partitions, partition_count, _method = self._mesh_partitioning_service.partition(
            mesh_coordinates, triangles, request.partition_count
        )

        return MeshGenerationResult(
            original_points=list(request.boundary_points),
            mesh_points=self._coordinates_to_points(mesh_coordinates),
            triangles=triangles,
            voronoi_vertices=voronoi_vertices,
            voronoi_edges=voronoi_edges,
            sensor_candidates=sensor_candidates,
            triangle_partitions=triangle_partitions,
            partition_count=partition_count,
            sensor_range_meters=request.sensor_range_meters,
        )

    def _build_constrained_triangulation(
        self, polygon_coordinates: np.ndarray, max_edge_length: Optional[float]
    ) -> tuple[list[list[int]], np.ndarray]:
        """Run the Constrained Delaunay Triangulation restricted to the polygon.

        The polygon is described as a Planar Straight Line Graph (PSLG): its
        vertices plus the boundary segments that close the ring. Triangle's
        ``p`` switch honors those segments and removes any triangle outside the
        bounded region, which is what confines the mesh to the delimited area.
        """
        vertex_count = len(polygon_coordinates)
        boundary_segments = np.array(
            [[index, (index + 1) % vertex_count] for index in range(vertex_count)]
        )
        planar_straight_line_graph = {
            "vertices": polygon_coordinates,
            "segments": boundary_segments,
        }

        try:
            triangulation = triangle_library.triangulate(
                planar_straight_line_graph,
                self._build_triangulation_flags(polygon_coordinates, max_edge_length),
            )
        except Exception as error:  # Triangle raises generic errors on bad input.
            raise self._invalid_geometry_error() from error

        if "triangles" not in triangulation or len(triangulation["triangles"]) == 0:
            raise self._invalid_geometry_error()

        return triangulation["triangles"].tolist(), np.asarray(triangulation["vertices"])

    def _build_triangulation_flags(
        self, polygon_coordinates: np.ndarray, max_edge_length: Optional[float]
    ) -> str:
        # 'p': triangulate the polygon defined by the segments (drops the exterior).
        # 'q': quality mesh, enforcing a minimum interior angle (avoids slivers).
        # 'a<area>': cap the triangle area to refine the interior when requested.
        flags = f"pq{self._minimum_angle_degrees:g}"
        if max_edge_length is not None:
            maximum_triangle_area = self._edge_length_to_triangle_area(max_edge_length)
            # Triangle parses the area bound as a fixed-point decimal and silently
            # ignores scientific notation (e.g. "2.7e-05" would disable refinement),
            # so the value is formatted positionally to keep the constraint valid.
            area_flag = np.format_float_positional(maximum_triangle_area, trim="-")
            flags += f"a{area_flag}"
        return flags

    @staticmethod
    def _edge_length_to_triangle_area(max_edge_length: float) -> float:
        """Convert a maximum edge length (in degrees) into the area of an
        equilateral triangle with that side. This lets the user reason in terms
        of edge length while Triangle refines using an area bound."""
        return (math.sqrt(3.0) / 4.0) * (max_edge_length ** 2)

    @classmethod
    def _meters_to_degrees(
        cls, max_edge_length_meters: Optional[float], polygon_coordinates: np.ndarray
    ) -> Optional[float]:
        """Convert a metric edge length into an equivalent length in degrees.

        The triangulation treats coordinates as planar (x = longitude,
        y = latitude, both in degrees), so a metric target must be translated
        into degrees. See ``_meters_per_degree`` for how the scale is obtained.
        """
        if max_edge_length_meters is None:
            return None
        return max_edge_length_meters / cls._meters_per_degree(polygon_coordinates)

    @staticmethod
    def _meters_per_degree(polygon_coordinates: np.ndarray) -> float:
        """Average meters spanned by one degree at the polygon's mean latitude.

        One degree of latitude is ~constant, while one degree of longitude
        shrinks with the cosine of the latitude; we average the two to obtain a
        single, direction-independent scale. This is an approximation, adequate
        for the small areas handled by the prototype (a few km across).
        """
        mean_latitude_degrees = float(np.mean(polygon_coordinates[:, 1]))
        meters_per_degree_longitude = METERS_PER_DEGREE_LATITUDE * math.cos(
            math.radians(mean_latitude_degrees)
        )
        return (METERS_PER_DEGREE_LATITUDE + meters_per_degree_longitude) / 2.0

    def _ensure_refinement_within_budget(
        self,
        max_edge_length_degrees: Optional[float],
        polygon_coordinates: np.ndarray,
    ) -> None:
        """Reject a refinement value so small it would blow the triangle budget.

        The number of triangles is estimated as ``polygon_area / triangle_area``
        (both in square degrees). If that exceeds ``MAXIMUM_ESTIMATED_TRIANGLES``
        the request is refused with the smallest edge length (in meters) that
        stays within budget, so an API consumer gets an actionable message
        instead of a request that never finishes.
        """
        if max_edge_length_degrees is None:
            return

        polygon_area = compute_polygon_area(polygon_coordinates.tolist())
        target_triangle_area = self._edge_length_to_triangle_area(max_edge_length_degrees)
        if target_triangle_area <= 0.0:
            return  # Defensive: the validator already forbids non-positive input.

        estimated_triangles = polygon_area / target_triangle_area
        if estimated_triangles <= MAXIMUM_ESTIMATED_TRIANGLES:
            return

        # Smallest edge length that keeps the estimate within budget, reported in
        # meters and rounded up so the suggested value is guaranteed to pass.
        minimum_triangle_area = polygon_area / MAXIMUM_ESTIMATED_TRIANGLES
        minimum_edge_degrees = math.sqrt(minimum_triangle_area / (math.sqrt(3.0) / 4.0))
        minimum_edge_meters = math.ceil(
            minimum_edge_degrees * self._meters_per_degree(polygon_coordinates)
        )
        raise ValidationException(
            "The refinement value is too small for the delimited area.",
            details=[
                "A maximum edge length that small would generate an excessive "
                "number of triangles and could stall the request. Use a maximum "
                f"edge length of at least {minimum_edge_meters} meters for this "
                "area (larger values produce coarser meshes)."
            ],
        )

    def _build_voronoi_diagram(
        self, mesh_coordinates: np.ndarray, polygon_coordinates: np.ndarray
    ) -> tuple[list[GeographicPoint], list[VoronoiEdge]]:
        """Derive the Voronoi diagram (regions of influence) from the mesh points.

        A Voronoi diagram needs at least a 2D point cloud; when it cannot be
        built (e.g. too few or collinear points) the diagram is simply omitted,
        which never invalidates the triangulation itself.
        """
        if len(mesh_coordinates) < 4:
            return [], []
        try:
            voronoi = Voronoi(mesh_coordinates)
        except QhullError:
            return [], []

        vertices = [
            GeographicPoint.from_longitude_latitude_pair(vertex)
            for vertex in voronoi.vertices.tolist()
        ]
        edges = self._extract_finite_voronoi_edges(voronoi, polygon_coordinates)
        return vertices, edges

    @staticmethod
    def _extract_finite_voronoi_edges(
        voronoi, polygon_coordinates: np.ndarray
    ) -> list[VoronoiEdge]:
        """Return only the finite edges (both endpoints known). Edges extending to
        infinity are omitted because they have no bounded representation on the map.
        Each finite edge is clipped to the user's delimited area."""
        vertices = voronoi.vertices
        edges: list[VoronoiEdge] = []
        for start_index, end_index in voronoi.ridge_vertices:
            if start_index == -1 or end_index == -1:
                continue
            clipped_segments = clip_segment_to_polygon(
                vertices[start_index],
                vertices[end_index],
                polygon_coordinates.tolist(),
            )
            for start_point, end_point in clipped_segments:
                edges.append(
                    VoronoiEdge(
                        start_point=GeographicPoint.from_longitude_latitude_pair(
                            list(start_point)
                        ),
                        end_point=GeographicPoint.from_longitude_latitude_pair(
                            list(end_point)
                        ),
                    )
                )
        return edges

    @staticmethod
    def _coordinates_to_points(coordinates: np.ndarray) -> list[GeographicPoint]:
        return [
            GeographicPoint.from_longitude_latitude_pair(pair)
            for pair in coordinates.tolist()
        ]

    @staticmethod
    def _invalid_geometry_error() -> InvalidGeometryException:
        return InvalidGeometryException(
            "The mesh could not be generated with the provided points.",
            details=[
                "The points may be collinear or coincident. "
                "Provide at least 3 points that form an area."
            ],
        )

    @staticmethod
    def _self_intersecting_geometry_error() -> InvalidGeometryException:
        return InvalidGeometryException(
            "The delimited area is invalid: its boundary intersects itself.",
            details=[
                "The boundary lines cross one another, so they do not enclose a "
                "single area. Reposition the points so the outline does not "
                "overlap itself."
            ],
        )
