from __future__ import annotations

from dataclasses import dataclass, field

from .geographic_point import GeographicPoint


@dataclass(frozen=True)
class VoronoiEdge:
    """A line segment connecting two vertices of the Voronoi diagram."""

    start_point: GeographicPoint
    end_point: GeographicPoint

    def to_dict(self) -> dict:
        return {
            "start": self.start_point.to_dict(),
            "end": self.end_point.to_dict(),
        }


@dataclass(frozen=True)
class MeshGenerationResult:
    """Full outcome of the mesh generation and the derived Voronoi diagram.

    Attributes:
        original_points: Points supplied by the user to delimit the area.
        mesh_points: Points actually used in the triangulation (including the
            ones inserted by the refinement step).
        triangles: Each triangle is a list of three indices pointing to
            positions in ``mesh_points``.
        voronoi_vertices: Vertices of the Voronoi diagram.
        voronoi_edges: Finite edges of the Voronoi diagram.
        sensor_candidates: Suggested sensor locations at internal vertices
            shared by at least three mesh triangles.
        triangle_partitions: Partition id assigned to each triangle, aligned by
            index with ``triangles``. Empty when no partitioning was requested.
        partition_count: Number of partitions effectively produced.
            sensor_range_meters: Optional sensor influence radius, in meters.
    """

    original_points: list[GeographicPoint]
    mesh_points: list[GeographicPoint]
    triangles: list[list[int]]
    voronoi_vertices: list[GeographicPoint]
    voronoi_edges: list[VoronoiEdge]
    sensor_candidates: list[GeographicPoint] = field(default_factory=list)
    triangle_partitions: list[int] = field(default_factory=list)
    partition_count: int = 1
    sensor_range_meters: float | None = None

    def to_dict(self) -> dict:
        """Serialize the result to compose the API response body."""
        return {
            "originalPoints": [point.to_dict() for point in self.original_points],
            "meshPoints": [point.to_dict() for point in self.mesh_points],
            "triangles": self.triangles,
            "voronoiVertices": [vertex.to_dict() for vertex in self.voronoi_vertices],
            "voronoiEdges": [edge.to_dict() for edge in self.voronoi_edges],
            "sensorCandidates": [point.to_dict() for point in self.sensor_candidates],
            "trianglePartitions": self.triangle_partitions,
            "partitionCount": self.partition_count,
            "sensorRangeMeters": self.sensor_range_meters,
        }
