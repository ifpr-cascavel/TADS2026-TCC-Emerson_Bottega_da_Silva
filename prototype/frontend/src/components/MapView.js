import React, { useState, useEffect, useRef } from 'react';
import {
  MapContainer,
  TileLayer,
  CircleMarker,
  Polygon,
  Polyline,
  Circle,
  useMap,
  useMapEvents,
} from 'react-leaflet';
import 'leaflet/dist/leaflet.css';
import { MAP_VISUALS, getPartitionColor } from '../config/mapVisuals';

// Initial view centered on Paraná (Cascavel region), matching the agricultural
// context described in the thesis. The user can pan/zoom freely.
const INITIAL_MAP_CENTER = [-24.9578, -53.4595];
const INITIAL_MAP_ZOOM = 7;

const OPENSTREETMAP_TILE_URL = 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png';
const OPENSTREETMAP_ATTRIBUTION =
  '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors';

const toLeafletPosition = (point) => [point.lat, point.lng];

// Visible radius of a boundary point, and the larger (invisible) radius that
// forms the fixed interaction area used to grab and drag the point.
const BOUNDARY_POINT_RADIUS = 6;
const BOUNDARY_POINT_INTERACTION_RADIUS = 14;

// Captures map clicks. The useMapEvents hook can only be used by a component
// rendered inside the MapContainer.
const MAP_LINE_CLICK_TOLERANCE = 12;

const closestPointOnSegment = (point, segmentStart, segmentEnd) => {
  const segmentX = segmentEnd.x - segmentStart.x;
  const segmentY = segmentEnd.y - segmentStart.y;
  const segmentLengthSquared = segmentX ** 2 + segmentY ** 2;

  if (segmentLengthSquared === 0) {
    return { x: segmentStart.x, y: segmentStart.y };
  }

  const projection =
    ((point.x - segmentStart.x) * segmentX + (point.y - segmentStart.y) * segmentY) /
    segmentLengthSquared;
  const clampedProjection = Math.max(0, Math.min(1, projection));
  const closestPoint = {
    x: segmentStart.x + clampedProjection * segmentX,
    y: segmentStart.y + clampedProjection * segmentY,
  };
  return closestPoint;
};

const getClickedBoundarySegment = (map, boundaryPoints, clickPosition) => {
  const clickLayerPoint = map.latLngToLayerPoint([clickPosition.lat, clickPosition.lng]);
  const isInsideExistingPointHandle = boundaryPoints.some((boundaryPoint) => {
    const pointLayerPosition = map.latLngToLayerPoint(toLeafletPosition(boundaryPoint));
    return (
      Math.hypot(
        clickLayerPoint.x - pointLayerPosition.x,
        clickLayerPoint.y - pointLayerPosition.y
      ) <= BOUNDARY_POINT_INTERACTION_RADIUS
    );
  });

  if (isInsideExistingPointHandle) {
    return { blockedByPoint: true };
  }

  if (boundaryPoints.length < 2) {
    return null;
  }

  let closestSegment = null;
  let closestDistance = Infinity;
  let closestLayerPoint = null;

  for (let index = 0; index < boundaryPoints.length; index += 1) {
    const nextIndex = (index + 1) % boundaryPoints.length;
    const start = map.latLngToLayerPoint(toLeafletPosition(boundaryPoints[index]));
    const end = map.latLngToLayerPoint(toLeafletPosition(boundaryPoints[nextIndex]));
    const segmentPoint = closestPointOnSegment(clickLayerPoint, start, end);
    const distance = Math.hypot(
      clickLayerPoint.x - segmentPoint.x,
      clickLayerPoint.y - segmentPoint.y
    );

    if (distance < closestDistance) {
      closestDistance = distance;
      closestSegment = index;
      closestLayerPoint = segmentPoint;
    }
  }

  if (closestDistance > MAP_LINE_CLICK_TOLERANCE) {
    return null;
  }

  const snappedPosition = map.layerPointToLatLng(closestLayerPoint);
  return {
    segmentIndex: closestSegment,
    point: { lat: snappedPosition.lat, lng: snappedPosition.lng },
  };
};

const MapClickHandler = ({ boundaryPoints, onMapClick, suppressNextClickRef }) => {
  const map = useMapEvents({
    click: (event) => {
      // Leaflet can emit a map click immediately after a point drag ends.
      // That click must not be interpreted as a request to add another point.
      if (suppressNextClickRef.current) {
        suppressNextClickRef.current = false;
        return;
      }

      const clickedBoundary = getClickedBoundarySegment(map, boundaryPoints, event.latlng);

      if (clickedBoundary?.blockedByPoint) {
        return;
      }

      onMapClick(
        clickedBoundary?.point ?? { lat: event.latlng.lat, lng: event.latlng.lng },
        clickedBoundary?.segmentIndex ?? null
      );
    },
  });
  return null;
};

const handleBoundaryLayerClick = (map, boundaryPoints, event, onMapClick) => {
  event.originalEvent.stopPropagation();
  const clickedBoundary = getClickedBoundarySegment(map, boundaryPoints, event.latlng);

  if (!clickedBoundary?.blockedByPoint) {
    onMapClick(
      clickedBoundary?.point ?? { lat: event.latlng.lat, lng: event.latlng.lng },
      clickedBoundary?.segmentIndex ?? null
    );
  }
};

const BoundaryOutline = ({ boundaryPoints, onMapClick }) => {
  const map = useMap();
  const positions = boundaryPoints.map(toLeafletPosition);
  const eventHandlers = {
    click: (event) => handleBoundaryLayerClick(map, boundaryPoints, event, onMapClick),
  };

  if (boundaryPoints.length === 2) {
    return (
      <Polyline
        positions={positions}
        pathOptions={{ color: MAP_VISUALS.boundaryArea.color, weight: 2 }}
        eventHandlers={eventHandlers}
      />
    );
  }

  if (boundaryPoints.length > 2) {
    return (
      <Polygon
        positions={positions}
        pathOptions={{
          color: MAP_VISUALS.boundaryArea.color,
          weight: 2,
          fillColor: MAP_VISUALS.boundaryArea.fillColor,
          fillOpacity: 0.15,
        }}
        eventHandlers={eventHandlers}
      />
    );
  }

  return null;
};

// Drives the drag of an existing boundary point. While a point is grabbed it
// follows the cursor (map panning is suspended) and, on release, dragging ends.
// Rendered inside the MapContainer so it can use useMapEvents.
const BoundaryPointDragHandler = ({ isDragging, onDrag, onEndDrag }) => {
  const map = useMap();
  const onDragRef = useRef(onDrag);
  const onEndDragRef = useRef(onEndDrag);

  onDragRef.current = onDrag;
  onEndDragRef.current = onEndDrag;

  // Listen on the document while dragging. Leaflet can stop delivering map
  // mouse events when the pointer moves over another layer or briefly leaves
  // the map, which used to interrupt the drag after a short delay.
  useEffect(() => {
    if (!isDragging) {
      return undefined;
    }

    const handleMouseMove = (event) => {
      const position = map.mouseEventToLatLng(event);
      onDragRef.current({ lat: position.lat, lng: position.lng });
    };

    const handleTouchMove = (event) => {
      if (!event.touches.length) {
        return;
      }
      event.preventDefault();
      const position = map.mouseEventToLatLng(event.touches[0]);
      onDragRef.current({ lat: position.lat, lng: position.lng });
    };

    const handleEndDrag = () => onEndDragRef.current();

    document.addEventListener('mousemove', handleMouseMove);
    document.addEventListener('mouseup', handleEndDrag);
    document.addEventListener('touchmove', handleTouchMove, { passive: false });
    document.addEventListener('touchend', handleEndDrag);

    return () => {
      document.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseup', handleEndDrag);
      document.removeEventListener('touchmove', handleTouchMove);
      document.removeEventListener('touchend', handleEndDrag);
    };
  }, [isDragging, map]);

  // Suspend map panning while a point is being dragged so only the point moves.
  useEffect(() => {
    if (isDragging) {
      map.dragging.disable();
    } else {
      map.dragging.enable();
    }
  }, [isDragging, map]);

  return null;
};

const ZoomControl = () => {
  const map = useMap();

  return (
    <div className="map-zoom-control leaflet-control" aria-label="Controles de zoom">
      <button
        type="button"
        className="map-zoom-button"
        onClick={() => map.zoomIn()}
        aria-label="Aumentar zoom"
      >
        +
      </button>
      <button
        type="button"
        className="map-zoom-button"
        onClick={() => map.zoomOut()}
        aria-label="Diminuir zoom"
      >
        −
      </button>
    </div>
  );
};

const MapView = ({ boundaryPoints, onAddPoint, onMovePoint, mesh, visibleVisuals }) => {
  const trianglePaths = buildTrianglePaths(mesh);
  const isPartitioned = Boolean(mesh?.trianglePartitions?.length);

  // Index of the boundary point currently being dragged (null when none is).
  const [draggingIndex, setDraggingIndex] = useState(null);
  const suppressNextClickRef = useRef(false);

  const startBoundaryPointDrag = (index, event) => {
    event.originalEvent.stopPropagation();
    if (event.type === 'touchstart') {
      event.originalEvent.preventDefault();
    }
    event.target._map.dragging.disable();
    setDraggingIndex(index);
  };

  const boundaryPointEventHandlers = (index) => ({
    mousedown: (event) => startBoundaryPointDrag(index, event),
    touchstart: (event) => startBoundaryPointDrag(index, event),
    click: (event) => event.originalEvent.stopPropagation(),
  });

  return (
    <MapContainer
      center={INITIAL_MAP_CENTER}
      zoom={INITIAL_MAP_ZOOM}
      className="map-canvas"
      zoomControl={false}
      doubleClickZoom={false}
    >
      <TileLayer attribution={OPENSTREETMAP_ATTRIBUTION} url={OPENSTREETMAP_TILE_URL} />

      <ZoomControl />

      <MapClickHandler
        boundaryPoints={boundaryPoints}
        onMapClick={onAddPoint}
        suppressNextClickRef={suppressNextClickRef}
      />

      <BoundaryPointDragHandler
        isDragging={draggingIndex !== null}
        onDrag={(point) => {
          suppressNextClickRef.current = true;
          onMovePoint(draggingIndex, point);
        }}
        onEndDrag={() => setDraggingIndex(null)}
      />

      {/* The open outline is visible while the user is placing its first points. */}
      {/* Delimited area and its click target. Clicking the line snaps the new
          point to it instead of treating the click as a free map point. */}
      {visibleVisuals.boundaryArea && (
        <BoundaryOutline boundaryPoints={boundaryPoints} onMapClick={onAddPoint} />
      )}

      {/* Delaunay triangulation. When partitioned, each triangle is filled with
          its partition color; otherwise only its red outline is drawn.
          Both branches must specify the SAME set of style keys (notably `fill`):
          react-leaflet reuses each layer across re-generations, and Leaflet's
          setStyle only overwrites the keys it receives — so omitting `fill` in
          one branch would leave a previously-applied `fill: false` stuck on,
          making the partition colors disappear on a later regeneration. */}
      {visibleVisuals.triangleEdge && trianglePaths.map(({ path, partition }, index) => (
        <Polygon
          key={`triangle-${index}`}
          positions={path}
          pathOptions={
            isPartitioned
              ? {
                  color: getPartitionColor(partition),
                  weight: 1,
                  opacity: 1,
                  fill: true,
                  fillColor: getPartitionColor(partition),
                  fillOpacity: 0.35,
                }
              : {
                  color: MAP_VISUALS.triangleEdge.color,
                  weight: 1,
                  opacity: 0.7,
                  fill: false,
                  fillColor: MAP_VISUALS.triangleEdge.color,
                  fillOpacity: 0,
                }
          }
        />
      ))}

      {/* Influence areas stay above partition fills so their perimeter remains
          visible, while the transparent fill avoids hiding the mesh colors. */}
      {visibleVisuals.sensorInfluence && mesh?.sensorRangeMeters && mesh.sensorCandidates?.map((point, index) => (
        <Circle
          key={`sensor-influence-${index}`}
          center={toLeafletPosition(point)}
          radius={mesh.sensorRangeMeters}
          pathOptions={{
            color: MAP_VISUALS.sensorInfluence.color || '#ffffff',
            weight: 3,
            opacity: 0.9,
            dashArray: '6 5',
            fillColor: MAP_VISUALS.sensorInfluence.fillColor,
            fillOpacity: 0.08,
          }}
        />
      ))}

      {/* Voronoi diagram edges */}
      {visibleVisuals.voronoiEdge && mesh?.voronoiEdges?.map((edge, index) => (
        <Polyline
          key={`voronoi-edge-${index}`}
          positions={[toLeafletPosition(edge.start), toLeafletPosition(edge.end)]}
          pathOptions={{
            color: MAP_VISUALS.voronoiEdge.color,
            weight: 1.5,
            opacity: 0.85,
            dashArray: '4 4',
          }}
        />
      ))}

      {/* Candidate sensor locations (drawn below boundary handles so an
          overlapping candidate never captures a boundary-point drag). */}
      {visibleVisuals.sensorCandidate && mesh?.sensorCandidates?.map((point, index) => (
        <CircleMarker
          key={`sensor-candidate-${index}`}
          center={toLeafletPosition(point)}
          radius={5}
          pathOptions={{
            color: '#ffffff',
            weight: 1.5,
            fillColor: MAP_VISUALS.sensorCandidate.color,
            fillOpacity: 1,
            interactive: false,
          }}
        />
      ))}

      {/* Boundary points defined by the user. Each visible dot is paired with a
          larger, transparent circle that provides a fixed interaction area:
          pressing it grabs the point so it can be dragged to a new position,
          with its connected lines following in real time. bubblingMouseEvents is
          disabled so grabbing a point does not also register a map click (which
          would add a new point). */}
      {visibleVisuals.boundaryPoint && boundaryPoints.map((point, index) => (
        <React.Fragment key={`boundary-point-${index}`}>
          <CircleMarker
            center={toLeafletPosition(point)}
            radius={BOUNDARY_POINT_RADIUS}
            pathOptions={{
              color: MAP_VISUALS.boundaryPoint.color,
              fillColor: MAP_VISUALS.boundaryPoint.color,
              fillOpacity: 0.9,
              bubblingMouseEvents: false,
              className: 'boundary-point',
            }}
            eventHandlers={boundaryPointEventHandlers(index)}
          />
          <CircleMarker
            center={toLeafletPosition(point)}
            radius={BOUNDARY_POINT_INTERACTION_RADIUS}
            pathOptions={{
              stroke: false,
              fill: true,
              fillColor: MAP_VISUALS.boundaryPoint.color,
              fillOpacity: 0,
              bubblingMouseEvents: false,
              className: 'boundary-point-handle',
            }}
            eventHandlers={boundaryPointEventHandlers(index)}
          />
        </React.Fragment>
      ))}

    </MapContainer>
  );
};

// Maps each triangle (a triple of indices into meshPoints) to a Leaflet path and
// its partition id, guarding against missing mesh data.
const buildTrianglePaths = (mesh) => {
  if (!mesh?.triangles || !mesh?.meshPoints) {
    return [];
  }
  return mesh.triangles.map((triangle, triangleIndex) => ({
    path: triangle.map((pointIndex) => toLeafletPosition(mesh.meshPoints[pointIndex])),
    partition: mesh.trianglePartitions?.[triangleIndex] ?? 0,
  }));
};

export default MapView;
