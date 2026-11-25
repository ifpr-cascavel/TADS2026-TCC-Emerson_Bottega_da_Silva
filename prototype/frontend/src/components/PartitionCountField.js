import React from 'react';
import InfoTooltip from './InfoTooltip';
import {
  MINIMUM_PARTITION_COUNT,
  MAXIMUM_PARTITION_COUNT,
} from '../config/meshParameters';

const PARTITION_TOOLTIP =
  'Divide a malha em regiões menores e equilibradas (usadas para processar ' +
  'partes da área em paralelo). Cada partição recebe uma cor no mapa. ' +
  'O máximo é limitado pela geometria: um polígono de N pontos gera N−2 ' +
  'triângulos, então não é possível criar mais partições do que triângulos. ' +
  'Use 1 para não particionar.';

// Controlled numeric field for the partition count. It keeps the raw text so the
// user can clear/retype freely, but surfaces an inline validation state and only
// reports a valid positive integer to the parent. The upper bound is dynamic:
// it comes from the drawn polygon (see getMaximumPartitionCount).
const PartitionCountField = ({ value, onChange, disabled, maximum = MAXIMUM_PARTITION_COUNT }) => {
  const isValid = isValidPartitionCount(value, maximum);

  const handleChange = (event) => {
    // Accept only digits to prevent invalid characters (e.g. '-', '.', 'e').
    const sanitized = event.target.value.replace(/[^0-9]/g, '');
    onChange(sanitized);
  };

  return (
    <div className="field">
      <label className="field-label" htmlFor="partition-count">
        Número de partições
        <InfoTooltip
          text={PARTITION_TOOLTIP}
          label="O que é o número de partições"
          placement="right"
        />
      </label>
      <input
        id="partition-count"
        className={`field-input${isValid ? '' : ' field-input--invalid'}`}
        type="text"
        inputMode="numeric"
        autoComplete="off"
        value={value}
        onChange={handleChange}
        disabled={disabled}
        aria-invalid={!isValid}
        aria-describedby="partition-count-hint"
      />
      <span
        id="partition-count-hint"
        className={`field-hint${isValid ? '' : ' field-hint--error'}`}
      >
        {isValid
          ? `Inteiro entre ${MINIMUM_PARTITION_COUNT} e ${maximum}. (1 para não particionar)`
          : `Informe um inteiro entre ${MINIMUM_PARTITION_COUNT} e ${maximum}.`}
      </span>
    </div>
  );
};

export const isValidPartitionCount = (rawValue, maximum = MAXIMUM_PARTITION_COUNT) => {
  if (rawValue === '' || rawValue == null) {
    return false;
  }
  const parsed = Number(rawValue);
  return (
    Number.isInteger(parsed) &&
    parsed >= MINIMUM_PARTITION_COUNT &&
    parsed <= maximum
  );
};

export default PartitionCountField;
