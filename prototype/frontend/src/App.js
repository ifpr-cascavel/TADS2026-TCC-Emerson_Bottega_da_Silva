import React, { useState } from 'react';
import MapView from './components/MapView';
import MapLegend from './components/MapLegend';
import ControlPanel from './components/ControlPanel';
import StatusBanner from './components/StatusBanner';
import { isValidPartitionCount } from './components/PartitionCountField';
import { generateMesh, exportMeshAsGeoJson } from './services/meshService';
import {
  DEFAULT_PARTITION_COUNT,
  DEFAULT_SENSOR_RANGE_METERS,
  getMaximumPartitionCount,
  isValidSensorRangeMeters,
} from './config/meshParameters';
import {
  wouldNewPointCrossBoundary,
  wouldMovedPointCrossBoundary,
  getMinimumMaxEdgeLengthMeters,
} from './utils/polygonGeometry';
import { MAP_VISUALS } from './config/mapVisuals';
import './App.css';

const INITIAL_VISIBLE_VISUALS = Object.keys(MAP_VISUALS).reduce(
  (visibility, visualId) => ({ ...visibility, [visualId]: true }),
  {}
);

const App = () => {
  const [boundaryPoints, setBoundaryPoints] = useState([]);
  const [mesh, setMesh] = useState(null);
  const [errorMessage, setErrorMessage] = useState(null);
  const [isGenerating, setIsGenerating] = useState(false);
  const [partitionCountText, setPartitionCountText] = useState(String(DEFAULT_PARTITION_COUNT));
  const [maxEdgeLengthText, setMaxEdgeLengthText] = useState('');
  const [sensorRangeMetersText, setSensorRangeMetersText] = useState(
    String(DEFAULT_SENSOR_RANGE_METERS)
  );
  const [visibleVisuals, setVisibleVisuals] = useState(INITIAL_VISIBLE_VISUALS);

  // The partition ceiling depends on the drawn geometry (a polygon of N points
  // yields N-2 triangles, so it cannot be split into more parts than that).
  const maximumPartitionCount = getMaximumPartitionCount(boundaryPoints.length);
  const isPartitionCountValid = isValidPartitionCount(
    partitionCountText,
    maximumPartitionCount
  );
  // Smallest refinement that stays within the triangle budget for this area; a
  // smaller value would over-refine and stall the request (mirrors the API).
  const minimumMaxEdgeLength = getMinimumMaxEdgeLengthMeters(boundaryPoints);
  const isMaxEdgeLengthValid = isValidMaxEdgeLength(
    maxEdgeLengthText,
    minimumMaxEdgeLength
  );
  const isSensorRangeMetersValid = isValidSensorRangeMeters(sensorRangeMetersText);

  const addBoundaryPoint = (point, segmentIndex = null) => {
    // Prevent drawing a point that would make the outline cross a line already
    // drawn: a self-intersecting boundary does not enclose a single valid area.
    if (wouldNewPointCrossBoundary(boundaryPoints, point, segmentIndex)) {
      setErrorMessage(
        'Esse ponto faria o contorno cruzar uma linha já desenhada. ' +
          'Escolha um ponto que mantenha a área sem sobreposição.'
      );
      return;
    }

    // Any change to the points invalidates the previously generated mesh.
    setBoundaryPoints((current) => {
      if (segmentIndex === null) {
        return [...current, point];
      }
      return [
        ...current.slice(0, segmentIndex + 1),
        point,
        ...current.slice(segmentIndex + 1),
      ];
    });
    setMesh(null);
    setErrorMessage(null);
  };

  // Moves an existing boundary point to a new position while it is dragged. The
  // move is rejected (the point keeps its last valid position) when it would
  // make one of the point's edges cross an existing line — the same simple-
  // polygon rule enforced on creation, so the point cannot be dragged across a
  // line and produce an incoherent mesh.
  const moveBoundaryPoint = (index, point) => {
    setBoundaryPoints((current) => {
      if (wouldMovedPointCrossBoundary(current, index, point)) {
        return current;
      }
      return current.map((existing, i) => (i === index ? point : existing));
    });
    // Any change to the points invalidates the previously generated mesh.
    setMesh(null);
    setErrorMessage(null);
  };

  const clearBoundaryPoints = () => {
    setBoundaryPoints([]);
    setMesh(null);
    setErrorMessage(null);
  };

  const toggleVisual = (visualId) => {
    setVisibleVisuals((current) => ({
      ...current,
      [visualId]: !current[visualId],
    }));
  };

  const buildRequestOptions = () => ({
    partitionCount: Number(partitionCountText),
    maxEdgeLength: maxEdgeLengthText === '' ? null : Number(maxEdgeLengthText),
    sensorRangeMeters:
      sensorRangeMetersText === '' ? null : Number(sensorRangeMetersText),
  });

  const handleGenerateMesh = async () => {
    setErrorMessage(null);
    setIsGenerating(true);
    const result = await generateMesh(boundaryPoints, buildRequestOptions());
    setIsGenerating(false);

    if (result.success) {
      setMesh(result.data);
    } else {
      setMesh(null);
      setErrorMessage(result.error);
    }
  };

  const handleDownloadGeoJson = async () => {
    setErrorMessage(null);
    const result = await exportMeshAsGeoJson(boundaryPoints, buildRequestOptions());
    if (!result.success) {
      setErrorMessage(result.error);
    }
  };

  const isPartitioned = Boolean(mesh?.trianglePartitions?.length);

  return (
    <div className="app">
      <header className="app-header">
        <h1 className="app-title">Planejamento inteligente de sensores</h1>
        <p className="app-subtitle">
          Defina uma área, distribua pontos de monitoramento e encontre os melhores locais para instalar seus sensores
        </p>
      </header>

      <main className="app-main">
        <aside className="app-sidebar">
          <ControlPanel
            boundaryPointCount={boundaryPoints.length}
            partitionCount={partitionCountText}
            onPartitionCountChange={setPartitionCountText}
            isPartitionCountValid={isPartitionCountValid}
            maxEdgeLength={maxEdgeLengthText}
            onMaxEdgeLengthChange={setMaxEdgeLengthText}
            isMaxEdgeLengthValid={isMaxEdgeLengthValid}
            minimumMaxEdgeLength={minimumMaxEdgeLength}
            sensorRangeMeters={sensorRangeMetersText}
            onSensorRangeMetersChange={setSensorRangeMetersText}
            isSensorRangeMetersValid={isSensorRangeMetersValid}
            maximumPartitionCount={maximumPartitionCount}
            onGenerate={handleGenerateMesh}
            onDownloadGeoJson={handleDownloadGeoJson}
            onClear={clearBoundaryPoints}
            isGenerating={isGenerating}
            hasMesh={Boolean(mesh)}
          />
        </aside>

        <div className="map-wrapper">
          <MapView
            boundaryPoints={boundaryPoints}
            onAddPoint={addBoundaryPoint}
            onMovePoint={moveBoundaryPoint}
            mesh={mesh}
            visibleVisuals={visibleVisuals}
          />
          <div className="map-status">
            <StatusBanner variant="error">{errorMessage}</StatusBanner>
            {mesh && !errorMessage && (
              <StatusBanner variant="success">
                {`Malha gerada: ${mesh.triangles.length} triângulos, `}
                {mesh.sensorCandidates.length === 1
                  ? '1 sugestão de sensor'
                  : `${mesh.sensorCandidates.length} sugestões de sensores`}
                {isPartitioned ? `, ${mesh.partitionCount} partições.` : '.'}
              </StatusBanner>
            )}
          </div>
        </div>

        <MapLegend
          isPartitioned={isPartitioned}
          visibleVisuals={visibleVisuals}
          onVisibilityChange={toggleVisual}
        />
      </main>
    </div>
  );
};

// Validates the optional refinement field. Empty means "no refinement". When
// filled, it must be a positive number that is also at least `minimumMeters`
// (the smallest edge length that keeps the mesh within the triangle budget for
// the current area); `minimumMeters` is 0 when there is no polygon yet.
export const isValidMaxEdgeLength = (rawValue, minimumMeters = 0) => {
  if (rawValue === '' || rawValue == null) {
    return true; // Optional field: empty means "no refinement".
  }
  const parsed = Number(rawValue);
  return Number.isFinite(parsed) && parsed > 0 && parsed >= minimumMeters;
};

export default App;
