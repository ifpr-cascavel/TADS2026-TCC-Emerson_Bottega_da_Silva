from __future__ import annotations

from typing import Optional, Sequence

Coordinate = Sequence[float]


def compute_triangle_centroid(
    vertex_a: Coordinate, vertex_b: Coordinate, vertex_c: Coordinate
) -> Optional[tuple[float, float]]:
    """Return the centroid (barycenter) of a triangle, or ``None`` if it is
    degenerate.

    The centroid is the arithmetic mean of the three vertices. Unlike the
    circumcenter, it is **always located inside** a non-degenerate triangle,
    which makes it a coherent, coverage-oriented sensor position: exactly one
    suggestion per mesh cell, evenly spread across the delimited area.
    """
    ax, ay = vertex_a[0], vertex_a[1]
    bx, by = vertex_b[0], vertex_b[1]
    cx, cy = vertex_c[0], vertex_c[1]

    # A near-zero signed area means the three vertices are collinear, so there is
    # no proper triangle to place a sensor in.
    signed_area_times_two = (bx - ax) * (cy - ay) - (cx - ax) * (by - ay)
    if abs(signed_area_times_two) < 1e-15:
        return None

    return (ax + bx + cx) / 3.0, (ay + by + cy) / 3.0


def compute_polygon_area(polygon: Sequence[Coordinate]) -> float:
    """Return the (absolute) area of ``polygon`` via the shoelace formula.

    ``polygon`` is an ordered ring of ``(x, y)`` vertices; the first vertex does
    not need to be repeated. The area is expressed in the square of the input
    units (here, square degrees), which is enough to reason about relative sizes
    such as how many triangles a refinement target would produce.
    """
    vertex_count = len(polygon)
    if vertex_count < 3:
        return 0.0

    twice_area = 0.0
    for current_index in range(vertex_count):
        current_x, current_y = polygon[current_index][0], polygon[current_index][1]
        next_x, next_y = (
            polygon[(current_index + 1) % vertex_count][0],
            polygon[(current_index + 1) % vertex_count][1],
        )
        twice_area += current_x * next_y - next_x * current_y
    return abs(twice_area) / 2.0


def is_point_inside_polygon(point: Coordinate, polygon: Sequence[Coordinate]) -> bool:
    """Test whether ``point`` lies inside ``polygon`` using the ray-casting
    (even-odd) algorithm.

    ``polygon`` is an ordered sequence of ``(x, y)`` vertices describing a simple
    (possibly non-convex) ring; it does not need to repeat the first vertex.
    """
    x, y = point[0], point[1]
    inside = False
    vertex_count = len(polygon)

    previous_index = vertex_count - 1
    for current_index in range(vertex_count):
        current_x, current_y = polygon[current_index][0], polygon[current_index][1]
        previous_x, previous_y = polygon[previous_index][0], polygon[previous_index][1]

        crosses_ray = (current_y > y) != (previous_y > y)
        if crosses_ray:
            intersection_x = (
                (previous_x - current_x) * (y - current_y) / (previous_y - current_y)
                + current_x
            )
            if x < intersection_x:
                inside = not inside
        previous_index = current_index

    return inside


def is_point_on_polygon_boundary(
    point: Coordinate, polygon: Sequence[Coordinate], tolerance: float = 1e-12
) -> bool:
    """Return whether ``point`` lies on any segment of the polygon boundary."""
    point_x, point_y = point[0], point[1]
    tolerance_squared = tolerance**2

    for index, start in enumerate(polygon):
        end = polygon[(index + 1) % len(polygon)]
        segment_x = end[0] - start[0]
        segment_y = end[1] - start[1]
        segment_length_squared = segment_x**2 + segment_y**2
        if segment_length_squared == 0:
            continue

        projection = (
            (point_x - start[0]) * segment_x + (point_y - start[1]) * segment_y
        ) / segment_length_squared
        projection = max(0.0, min(1.0, projection))
        closest_x = start[0] + projection * segment_x
        closest_y = start[1] + projection * segment_y
        distance_squared = (point_x - closest_x) ** 2 + (point_y - closest_y) ** 2
        if distance_squared <= tolerance_squared:
            return True

    return False


def clip_segment_to_polygon(
    start: Coordinate, end: Coordinate, polygon: Sequence[Coordinate]
) -> list[tuple[tuple[float, float], tuple[float, float]]]:
    """Return the portions of a segment that lie inside a polygon."""
    start_x, start_y = start[0], start[1]
    direction_x, direction_y = end[0] - start_x, end[1] - start_y
    segment_length_squared = direction_x**2 + direction_y**2
    if segment_length_squared == 0:
        return []

    parameters = [0.0, 1.0]
    tolerance = 1e-12

    for index, boundary_start in enumerate(polygon):
        boundary_end = polygon[(index + 1) % len(polygon)]
        boundary_direction_x = boundary_end[0] - boundary_start[0]
        boundary_direction_y = boundary_end[1] - boundary_start[1]
        denominator = (
            direction_x * boundary_direction_y
            - direction_y * boundary_direction_x
        )
        offset_x = boundary_start[0] - start_x
        offset_y = boundary_start[1] - start_y

        if abs(denominator) <= tolerance:
            continue

        segment_parameter = (
            offset_x * boundary_direction_y - offset_y * boundary_direction_x
        ) / denominator
        boundary_parameter = (
            offset_x * direction_y - offset_y * direction_x
        ) / denominator
        if -tolerance <= segment_parameter <= 1.0 + tolerance and (
            -tolerance <= boundary_parameter <= 1.0 + tolerance
        ):
            parameters.append(max(0.0, min(1.0, segment_parameter)))

    parameters = sorted(set(round(parameter, 14) for parameter in parameters))
    portions: list[tuple[tuple[float, float], tuple[float, float]]] = []
    for first_parameter, second_parameter in zip(parameters, parameters[1:]):
        if second_parameter - first_parameter <= tolerance:
            continue
        midpoint_parameter = (first_parameter + second_parameter) / 2.0
        midpoint = (
            start_x + midpoint_parameter * direction_x,
            start_y + midpoint_parameter * direction_y,
        )
        if not is_point_inside_polygon(midpoint, polygon) and not is_point_on_polygon_boundary(
            midpoint, polygon
        ):
            continue

        first_point = (
            start_x + first_parameter * direction_x,
            start_y + first_parameter * direction_y,
        )
        second_point = (
            start_x + second_parameter * direction_x,
            start_y + second_parameter * direction_y,
        )
        portions.append((first_point, second_point))

    return portions


def is_simple_polygon(polygon: Sequence[Coordinate]) -> bool:
    """Return ``True`` when ``polygon`` is a *simple* ring, i.e. none of its
    boundary edges cross each other.

    A self-intersecting boundary (e.g. a "bowtie", where the user's lines fold
    over one another) does not delimit a single well-defined region, so the
    triangulation/partitioning built on top of it would be inconsistent. This
    check rejects those cases before any mesh is generated.

    Edges that merely *share a vertex* (consecutive edges of the ring) are not
    treated as intersections; only proper crossings are.
    """
    vertex_count = len(polygon)
    if vertex_count < 4:
        # Triangles (or fewer points) cannot self-intersect.
        return True

    for i in range(vertex_count):
        first_start = polygon[i]
        first_end = polygon[(i + 1) % vertex_count]
        for j in range(i + 1, vertex_count):
            # Skip edges that are adjacent (they legitimately share a vertex).
            if j == i or (i + 1) % vertex_count == j or (j + 1) % vertex_count == i:
                continue
            second_start = polygon[j]
            second_end = polygon[(j + 1) % vertex_count]
            if _segments_properly_intersect(
                first_start, first_end, second_start, second_end
            ):
                return False
    return True


def _segments_properly_intersect(
    p1: Coordinate, p2: Coordinate, p3: Coordinate, p4: Coordinate
) -> bool:
    """Return ``True`` when segment ``p1-p2`` crosses segment ``p3-p4``.

    Uses the orientation (signed-area) test: the segments cross when each one
    separates the endpoints of the other, i.e. the four orientations alternate
    in sign.
    """
    d1 = _orientation(p3, p4, p1)
    d2 = _orientation(p3, p4, p2)
    d3 = _orientation(p1, p2, p3)
    d4 = _orientation(p1, p2, p4)
    return ((d1 > 0) != (d2 > 0)) and ((d3 > 0) != (d4 > 0))


def _orientation(a: Coordinate, b: Coordinate, c: Coordinate) -> float:
    """Signed area (times two) of triangle ``a-b-c``. Positive/negative tells on
    which side of line ``a-b`` point ``c`` lies; zero means collinear."""
    return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])
