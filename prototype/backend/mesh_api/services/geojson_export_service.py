from __future__ import annotations

from ..models.geographic_point import GeographicPoint
from ..models.mesh_generation_result import MeshGenerationResult


class GeoJsonExportService:
    """Converts a mesh generation result into a GeoJSON FeatureCollection.

    GeoJSON is a standardized, interoperable format, so the generated mesh can be
    opened in geoprocessing tools (e.g. QGIS) without any further conversion.
    Coordinates follow the ``[longitude, latitude]`` order required by the spec.
    Each triangle feature also carries its ``partition`` id (when the mesh was
    partitioned), enabling styling by partition in external tools.
    """

    def convert_to_feature_collection(self, result: MeshGenerationResult) -> dict:
        features: list[dict] = []
        features.extend(self._build_point_features(result.original_points, "original_point"))
        features.extend(self._build_point_features(result.mesh_points, "mesh_point"))
        features.extend(
            self._build_point_features(result.sensor_candidates, "sensor_candidate")
        )
        features.extend(self._build_triangle_features(result))
        features.extend(self._build_voronoi_edge_features(result))

        return {"type": "FeatureCollection", "features": features}

    def _build_point_features(
        self, points: list[GeographicPoint], feature_type: str
    ) -> list[dict]:
        return [
            {
                "type": "Feature",
                "properties": {"type": feature_type},
                "geometry": {
                    "type": "Point",
                    "coordinates": point.to_longitude_latitude_pair(),
                },
            }
            for point in points
        ]

    def _build_triangle_features(self, result: MeshGenerationResult) -> list[dict]:
        features: list[dict] = []
        for triangle_index, triangle in enumerate(result.triangles):
            polygon_ring = [
                result.mesh_points[point_index].to_longitude_latitude_pair()
                for point_index in triangle
            ]
            # GeoJSON requires the polygon ring to be closed (first point repeated).
            polygon_ring.append(polygon_ring[0])

            properties: dict = {"type": "triangle"}
            if result.triangle_partitions:
                properties["partition"] = result.triangle_partitions[triangle_index]

            features.append(
                {
                    "type": "Feature",
                    "properties": properties,
                    "geometry": {"type": "Polygon", "coordinates": [polygon_ring]},
                }
            )
        return features

    def _build_voronoi_edge_features(self, result: MeshGenerationResult) -> list[dict]:
        return [
            {
                "type": "Feature",
                "properties": {"type": "voronoi_edge"},
                "geometry": {
                    "type": "LineString",
                    "coordinates": [
                        edge.start_point.to_longitude_latitude_pair(),
                        edge.end_point.to_longitude_latitude_pair(),
                    ],
                },
            }
            for edge in result.voronoi_edges
        ]
