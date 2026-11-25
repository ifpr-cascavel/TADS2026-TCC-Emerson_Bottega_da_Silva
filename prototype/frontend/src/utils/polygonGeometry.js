// Geometry helpers used to keep the boundary the user draws valid.
//
// The mesh can only be built on a *simple* polygon (a boundary whose edges do
// not cross each other). This module lets the UI reject, at draw time, a point
// that would make the outline overlap itself — the same rule the backend
// enforces on the closed ring as the authoritative check.

import { MAXIMUM_ESTIMATED_TRIANGLES } from '../config/meshParameters';

const METERS_PER_DEGREE_LATITUDE = 111320;
const MINIMUM_POLYGON_POINTS = 3;

const orientation = (a, b, c) =>
  (b.lng - a.lng) * (c.lat - a.lat) - (b.lat - a.lat) * (c.lng - a.lng);

// True when open segments a-b and c-d properly cross (excluding mere shared
// endpoints, handled by the caller by skipping adjacent segments).
const segmentsProperlyIntersect = (a, b, c, d) => {
  const d1 = orientation(c, d, a);
  const d2 = orientation(c, d, b);
  const d3 = orientation(a, b, c);
  const d4 = orientation(a, b, d);
  return (d1 > 0) !== (d2 > 0) && (d3 > 0) !== (d4 > 0);
};

// Whether adding `candidate` would make the boundary cross a line already drawn.
// The boundary is a *closed* ring (Leaflet and the backend always join the last
// point back to the first), so adding a point introduces two edges that must be
// checked: the freshly drawn one (last existing point -> candidate) and the new
// closing edge (candidate -> first point). Used while drawing to block a point
// that folds the outline over an existing line (the "internal line" case).
// Segments adjacent to a checked edge share a vertex, so they are skipped.
export const wouldNewPointCrossBoundary = (
  boundaryPoints,
  candidate,
  insertionSegmentIndex = null
) => {
  const count = boundaryPoints.length;
  if (count < 2) {
    return false; // Need at least one existing edge to cross.
  }

  // When the user clicks an existing edge, the map snaps the candidate to
  // that edge and inserts it between its two endpoints. The original edge is
  // being split, not replaced by an edge from the last point to the candidate.
  // The append-only checks below would inspect the wrong pair of edges and
  // could report a false self-intersection.
  if (
    insertionSegmentIndex !== null &&
    insertionSegmentIndex >= 0 &&
    insertionSegmentIndex < count
  ) {
    return false;
  }

  const newStart = boundaryPoints[count - 1];
  const newEnd = candidate;
  const firstPoint = boundaryPoints[0];

  // The freshly drawn edge: compare against every existing edge except the one
  // touching newStart (the last existing edge, index count - 2).
  for (let i = 0; i < count - 2; i += 1) {
    const edgeStart = boundaryPoints[i];
    const edgeEnd = boundaryPoints[i + 1];
    if (segmentsProperlyIntersect(newStart, newEnd, edgeStart, edgeEnd)) {
      return true;
    }
  }

  // The closing edge (candidate -> first point). It only exists once the ring
  // has at least three vertices after adding the candidate. It shares the first
  // point with edge 0 and `candidate` with the freshly drawn edge, so both
  // adjacent edges are skipped (loop runs over edges 1 .. count - 2).
  for (let i = 1; i < count - 1; i += 1) {
    const edgeStart = boundaryPoints[i];
    const edgeEnd = boundaryPoints[i + 1];
    if (segmentsProperlyIntersect(newEnd, firstPoint, edgeStart, edgeEnd)) {
      return true;
    }
  }
  return false;
};

// Whether moving the existing boundary point at `movingIndex` to `candidate`
// would make either of its two incident edges cross a non-incident boundary
// edge. This is the drag-time counterpart of wouldNewPointCrossBoundary: it
// enforces the same simple-polygon rule on the *closed* ring while a point is
// dragged, reusing segmentsProperlyIntersect. The two edges incident to the
// moving vertex (the ones being moved) and any edge sharing an endpoint with a
// moved edge are skipped, so neither the moved edges themselves nor their
// neighbours count as a conflict.
export const wouldMovedPointCrossBoundary = (boundaryPoints, movingIndex, candidate) => {
  const count = boundaryPoints.length;
  if (count < 4) {
    return false; // A triangle (or smaller) ring cannot self-intersect.
  }

  const previousIndex = (movingIndex - 1 + count) % count;
  const nextIndex = (movingIndex + 1) % count;

  // The moving vertex's two edges, in their proposed position.
  const movedEdges = [
    [boundaryPoints[previousIndex], candidate],
    [candidate, boundaryPoints[nextIndex]],
  ];

  for (let i = 0; i < count; i += 1) {
    // Skip the two edges incident to the moving vertex: they are being moved,
    // not obstacles. Edge i spans point i -> point i + 1, so the moving vertex's
    // edges are edge `previousIndex` and edge `movingIndex`.
    if (i === movingIndex || i === previousIndex) {
      continue;
    }
    const edgeStart = boundaryPoints[i];
    const edgeEnd = boundaryPoints[(i + 1) % count];
    for (const [movedStart, movedEnd] of movedEdges) {
      // An edge that shares an endpoint with the moved edge meets it at a vertex
      // and is not a real crossing (candidate is a fresh object, so it only
      // matches the moving vertex's own edges, already skipped above).
      if (
        edgeStart === movedStart ||
        edgeStart === movedEnd ||
        edgeEnd === movedStart ||
        edgeEnd === movedEnd
      ) {
        continue;
      }
      if (segmentsProperlyIntersect(movedStart, movedEnd, edgeStart, edgeEnd)) {
        return true;
      }
    }
  }
  return false;
};

// Absolute polygon area (in square degrees) via the shoelace formula, using
// longitude as x and latitude as y.
const polygonAreaInSquareDegrees = (boundaryPoints) => {
  const count = boundaryPoints.length;
  let twiceArea = 0;
  for (let i = 0; i < count; i += 1) {
    const current = boundaryPoints[i];
    const next = boundaryPoints[(i + 1) % count];
    twiceArea += current.lng * next.lat - next.lng * current.lat;
  }
  return Math.abs(twiceArea) / 2;
};

// Average meters per degree at the polygon's mean latitude (see the API's
// _meters_per_degree). Used to convert the degree-based geometry to meters.
const metersPerDegree = (boundaryPoints) => {
  const meanLat =
    boundaryPoints.reduce((sum, p) => sum + p.lat, 0) / boundaryPoints.length;
  const metersPerDegreeLongitude =
    METERS_PER_DEGREE_LATITUDE * Math.cos((meanLat * Math.PI) / 180);
  return (METERS_PER_DEGREE_LATITUDE + metersPerDegreeLongitude) / 2;
};

// Smallest refinement edge length (meters) that keeps the estimated triangle
// count within MAXIMUM_ESTIMATED_TRIANGLES for the drawn area. Mirrors the API's
// budget check so the UI can block an unsafe value before calling it. Returns 0
// when there is no polygon yet (no constraint to apply).
export const getMinimumMaxEdgeLengthMeters = (boundaryPoints) => {
  if (boundaryPoints.length < MINIMUM_POLYGON_POINTS) {
    return 0;
  }
  const area = polygonAreaInSquareDegrees(boundaryPoints);
  const minimumTriangleArea = area / MAXIMUM_ESTIMATED_TRIANGLES;
  const minimumEdgeDegrees = Math.sqrt(minimumTriangleArea / (Math.sqrt(3) / 4));
  return Math.ceil(minimumEdgeDegrees * metersPerDegree(boundaryPoints));
};
