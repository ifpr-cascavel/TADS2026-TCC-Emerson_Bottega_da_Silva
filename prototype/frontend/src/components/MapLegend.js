import React from 'react';
import { MAP_VISUALS } from '../config/mapVisuals';
import InfoTooltip from './InfoTooltip';

// Discreet legend describing every element rendered on the map. Entries are
// derived from the shared MAP_VISUALS tokens, so the legend always matches what
// is actually drawn. Line-based elements (edges) use a bar marker; point-based
// elements use a dot marker.
const LEGEND_ENTRIES = [
  { visual: MAP_VISUALS.boundaryPoint, shape: 'dot' },
  { visual: MAP_VISUALS.sensorCandidate, shape: 'dot-ring' },
  { visual: MAP_VISUALS.sensorInfluence, shape: 'sensor-influence' },
  { visual: MAP_VISUALS.triangleEdge, shape: 'line' },
  { visual: MAP_VISUALS.voronoiEdge, shape: 'line-dashed' },
  { visual: MAP_VISUALS.boundaryArea, shape: 'area' },
];

const MapLegend = ({ isPartitioned, visibleVisuals, onVisibilityChange }) => (
  <div className="legend" aria-label="Legenda do mapa">
    <span className="legend-title">Legenda</span>
    <ul className="legend-list">
      {LEGEND_ENTRIES.map(({ visual, shape }) => (
        <li key={visual.id} className="legend-item">
          <input
            type="checkbox"
            className="legend-checkbox"
            checked={visibleVisuals[visual.id]}
            onChange={() => onVisibilityChange(visual.id)}
            aria-label={`Exibir ${visual.label}`}
          />
          <LegendMarker shape={shape} visual={visual} />
          <span className="legend-label">{visual.label}</span>
          {visual.tooltip && (
            <InfoTooltip text={visual.tooltip} label={`Sobre: ${visual.label}`} />
          )}
        </li>
      ))}
      {isPartitioned && (
        <li className="legend-item">
          <input
            type="checkbox"
            className="legend-checkbox"
            checked={visibleVisuals.triangleEdge}
            onChange={() => onVisibilityChange('triangleEdge')}
            aria-label="Exibir triângulos coloridos por partição"
          />
          <span className="legend-marker legend-marker--partitions" />
          <span className="legend-label">Triângulos coloridos por partição</span>
        </li>
      )}
    </ul>
  </div>
);

const LegendMarker = ({ shape, visual }) => {
  const color = visual.color;
  switch (shape) {
    case 'line':
      return <span className="legend-marker legend-marker--line" style={{ backgroundColor: color }} />;
    case 'line-dashed':
      return (
        <span
          className="legend-marker legend-marker--line-dashed"
          style={{ backgroundImage: `linear-gradient(90deg, ${color} 60%, transparent 40%)` }}
        />
      );
    case 'sensor-influence':
      return (
        <svg
          className="legend-marker legend-marker--sensor-influence"
          viewBox="0 0 16 16"
          width="16"
          height="16"
          aria-hidden="true"
        >
          <circle
            cx="8"
            cy="8"
            r="6.5"
            fill={visual.fillColor || '#f59e0b'}
            fillOpacity="0.25"
            stroke="#ffffff"
            strokeWidth="1.5"
            strokeDasharray="3 2"
            style={{ filter: 'drop-shadow(0 0 0.8px rgba(15, 23, 42, 0.45))' }}
          />
        </svg>
      );
    case 'area':
      return (
        <span
          className="legend-marker legend-marker--area"
          style={{ borderColor: color, backgroundColor: visual.fillColor }}
        />
      );
    case 'dot-ring':
      return (
        <span
          className="legend-marker legend-marker--dot-ring"
          style={{ backgroundColor: color }}
        />
      );
    case 'dot':
    default:
      return <span className="legend-marker legend-marker--dot" style={{ backgroundColor: color }} />;
  }
};

export default MapLegend;
