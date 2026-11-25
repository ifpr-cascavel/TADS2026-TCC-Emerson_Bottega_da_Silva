from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class GeographicPoint:
    """A geographic point expressed in decimal degrees (latitude/longitude)."""

    latitude: float
    longitude: float

    def to_longitude_latitude_pair(self) -> list[float]:
        """Return the coordinates as ``[longitude, latitude]``.

        This is the ``(x, y)`` order expected both by the geometry libraries
        (SciPy, Shapely, Triangle) and by the GeoJSON specification, which
        prevents accidental latitude/longitude swaps across the codebase.
        """
        return [self.longitude, self.latitude]

    def to_dict(self) -> dict:
        """Serialize the point in the shape consumed by the web prototype."""
        return {"lat": self.latitude, "lng": self.longitude}

    @staticmethod
    def from_longitude_latitude_pair(pair: list[float]) -> "GeographicPoint":
        """Build a point from a ``[longitude, latitude]`` pair."""
        return GeographicPoint(latitude=float(pair[1]), longitude=float(pair[0]))
