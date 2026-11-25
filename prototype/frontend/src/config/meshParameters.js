// Shared numeric constraints for the mesh parameters. Kept in one place so the
// UI validation and the on-screen hints never disagree with each other. The
// partition bounds mirror the API's own validation (1..32).

export const MINIMUM_BOUNDARY_POINTS = 3;

export const DEFAULT_PARTITION_COUNT = 1;
export const MINIMUM_PARTITION_COUNT = 1;
export const DEFAULT_SENSOR_RANGE_METERS = 50;

export const isValidSensorRangeMeters = (rawValue) => {
  if (rawValue === '' || rawValue == null) {
    return true;
  }
  const parsed = Number(rawValue);
  return Number.isFinite(parsed) && parsed > 0;
};
// Absolute ceiling, mirroring the API. The effective ceiling is usually lower
// and derived from the drawn polygon (see getMaximumPartitionCount).
export const MAXIMUM_PARTITION_COUNT = 32;

// Upper bound on the estimated number of triangles a refinement may produce
// (estimate = polygon area / target triangle area). Mirrors the API constant of
// the same name; keep both in sync. It prevents an over-refined mesh (e.g. a
// 2 m edge over a 400 m area) from generating tens of thousands of triangles and
// stalling the request/rendering.
export const MAXIMUM_ESTIMATED_TRIANGLES = 3000;

// Maximum number of partitions allowed for the polygon the user has drawn.
//
// Criterion (geometry-based): a *simple* polygon with `n` boundary vertices is
// decomposed into exactly `n - 2` triangles, and every triangulation of it has
// at least that many triangles. Since a mesh can never be split into more parts
// than it has triangles, `n - 2` is a safe upper bound that depends only on the
// drawn geometry — it prevents asking for more partitions than the area can
// possibly sustain (e.g. 8 partitions for a 4-point quadrilateral). The result
// is clamped to [1, MAXIMUM_PARTITION_COUNT].
export const getMaximumPartitionCount = (boundaryPointCount) => {
  // Before a valid area exists, keep the field useful instead of showing a
  // misleading upper bound of 1 derived from an incomplete polygon.
  if (boundaryPointCount < MINIMUM_BOUNDARY_POINTS) {
    return MINIMUM_BOUNDARY_POINTS;
  }

  const geometricLimit = boundaryPointCount - 2;
  return Math.max(
    MINIMUM_PARTITION_COUNT,
    Math.min(geometricLimit, MAXIMUM_PARTITION_COUNT)
  );
};
