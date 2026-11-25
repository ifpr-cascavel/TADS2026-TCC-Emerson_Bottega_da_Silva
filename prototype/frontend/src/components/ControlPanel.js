import React from 'react';
import PartitionCountField from './PartitionCountField';
import InfoTooltip from './InfoTooltip';
import { MINIMUM_BOUNDARY_POINTS } from '../config/meshParameters';

const MAX_EDGE_LENGTH_TOOLTIP =
  'Controla o tamanho máximo dos triângulos da malha, em metros. É o ' +
  'comprimento máximo do lado de cada triângulo: valores menores geram ' +
  'triângulos menores e uma malha mais densa (mais detalhe e mais pontos de ' +
  'sensor); valores maiores geram uma malha mais grossa. Deixe em branco para ' +
  'não refinar. A conversão de metros para o mapa é aproximada, calculada pela ' +
  'latitude da área.';

const SENSOR_RANGE_TOOLTIP =
  'Define até que distância, em metros, cada sensor consegue monitorar. ' +
  'A área aparece no mapa como um círculo ao redor de cada ponto sugerido.';

// Side panel that groups every user control: the parameters, the primary/
// secondary actions and the contextual hints. It is purely presentational —
// all state lives in App and is passed down through props.
const ControlPanel = ({
  boundaryPointCount,
  partitionCount,
  onPartitionCountChange,
  isPartitionCountValid,
  maxEdgeLength,
  onMaxEdgeLengthChange,
  isMaxEdgeLengthValid,
  minimumMaxEdgeLength,
  sensorRangeMeters,
  onSensorRangeMetersChange,
  isSensorRangeMetersValid,
  maximumPartitionCount,
  onGenerate,
  onDownloadGeoJson,
  onClear,
  isGenerating,
  hasMesh,
}) => {
  const hasEnoughPoints = boundaryPointCount >= MINIMUM_BOUNDARY_POINTS;
  const canGenerate =
    hasEnoughPoints &&
    isPartitionCountValid &&
    isMaxEdgeLengthValid &&
    isSensorRangeMetersValid &&
    !isGenerating;
  const missingPoints = Math.max(0, MINIMUM_BOUNDARY_POINTS - boundaryPointCount);

  return (
    <section className="control-panel" aria-label="Controles da malha">
      <div className="panel-block">
        <h2 className="panel-heading">Parâmetros</h2>
        <p className="panel-metric">
          <span className="panel-metric-value">{boundaryPointCount}</span>
          <span className="panel-metric-label">
            {boundaryPointCount === 1 ? 'ponto definido' : 'pontos definidos'}
          </span>
        </p>

        <PartitionCountField
          value={partitionCount}
          onChange={onPartitionCountChange}
          disabled={isGenerating}
          maximum={maximumPartitionCount}
        />

        <div className="field">
          <label className="field-label" htmlFor="max-edge-length">
            Refinamento em metros
            <span className="field-optional"> (opcional)</span>
            <InfoTooltip
              text={MAX_EDGE_LENGTH_TOOLTIP}
              label="O que é o comprimento máximo de aresta"
              placement="right"
            />
          </label>
          <input
            id="max-edge-length"
            className={`field-input${isMaxEdgeLengthValid ? '' : ' field-input--invalid'}`}
            type="text"
            inputMode="decimal"
            autoComplete="off"
            placeholder="ex.: 100"
            value={maxEdgeLength}
            onChange={(event) => onMaxEdgeLengthChange(event.target.value)}
            disabled={isGenerating}
            aria-invalid={!isMaxEdgeLengthValid}
            aria-describedby="max-edge-length-hint"
          />
          <span
            id="max-edge-length-hint"
            className={`field-hint${isMaxEdgeLengthValid ? '' : ' field-hint--error'}`}
          >
            {isMaxEdgeLengthValid
              ? 'Em metros. Vazio = sem refinamento. Valores menores = malhas mais densas.'
              : minimumMaxEdgeLength > 0
              ? `Valor muito pequeno para esta área: geraria uma malha densa demais. Use ao menos ${minimumMaxEdgeLength} m (ou deixe em branco).`
              : 'Informe um número maior que zero ou deixe em branco.'}
          </span>
        </div>

        <div className="field">
          <label className="field-label" htmlFor="sensor-range-meters">
            Alcance do sensor em metros (apenas visual)
            <InfoTooltip
              text={SENSOR_RANGE_TOOLTIP}
              label="O que é o alcance do sensor"
            />
          </label>
          <input
            id="sensor-range-meters"
            className={`field-input${isSensorRangeMetersValid ? '' : ' field-input--invalid'}`}
            type="text"
            inputMode="decimal"
            autoComplete="off"
            placeholder="ex.: 500"
            value={sensorRangeMeters}
            onChange={(event) => onSensorRangeMetersChange(event.target.value)}
            disabled={isGenerating}
            aria-invalid={!isSensorRangeMetersValid}
            aria-describedby="sensor-range-meters-hint"
          />
          <span
            id="sensor-range-meters-hint"
            className={`field-hint${isSensorRangeMetersValid ? '' : ' field-hint--error'}`}
          >
            {isSensorRangeMetersValid
              ? 'O círculo de influência será desenhado ao redor de cada sensor sugerido.'
              : 'Informe um número maior que zero ou deixe em branco.'}
          </span>
        </div>
      </div>

      <div className="panel-block panel-actions">
        <button
          type="button"
          className="button button--primary"
          onClick={onGenerate}
          disabled={!canGenerate}
        >
          {isGenerating ? (
            <>
              <span className="spinner" aria-hidden="true" />
              Gerando malha…
            </>
          ) : (
            'Gerar malha'
          )}
        </button>
        <button
          type="button"
          className="button button--ghost"
          onClick={onDownloadGeoJson}
          disabled={!hasMesh || isGenerating}
        >
          Baixar GeoJSON
        </button>
        <button
          type="button"
          className="button button--subtle"
          onClick={onClear}
          disabled={boundaryPointCount === 0 || isGenerating}
        >
          Limpar
        </button>
      </div>

      <p className="panel-hint">
        {hasEnoughPoints
          ? 'Clique em “Gerar malha” para calcular a triangulação, o diagrama de Voronoi e os pontos sugeridos a sensores.'
          : `Clique no mapa para adicionar pontos. Faltam ${missingPoints} para o mínimo de ${MINIMUM_BOUNDARY_POINTS}.`}
      </p>
    </section>
  );
};

export default ControlPanel;
