from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from .geographic_point import GeographicPoint


@dataclass(frozen=True)
class MeshGenerationRequest:
    """Already-validated parameters for a computational mesh generation.

    This object represents the client's intent *after* input validation,
    isolating the service layer from HTTP transport details (the raw JSON body).

    Attributes:
        boundary_points: Ordered points that delimit the area of interest.
        max_edge_length: Optional refinement target (in meters). When provided,
            it is converted (via the polygon's latitude) into degrees and then
            into a maximum triangle area, so the constrained triangulation
            refines the interior. ``None`` means "no refinement".
        partition_count: Number of balanced partitions requested for the mesh
            (``1`` means "do not partition").
            sensor_range_meters: Optional radius, in meters, used to display the
                influence area around each suggested sensor.
    """

    boundary_points: list[GeographicPoint]
    max_edge_length: Optional[float]
    partition_count: int = 1
    sensor_range_meters: Optional[float] = None
