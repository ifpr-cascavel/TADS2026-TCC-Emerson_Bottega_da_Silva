import { isValidPartitionCount } from './components/PartitionCountField';
import { isValidSensorRangeMeters } from './config/meshParameters';
import { getPartitionColor, PARTITION_PALETTE } from './config/mapVisuals';
import { wouldNewPointCrossBoundary } from './utils/polygonGeometry';

describe('isValidPartitionCount', () => {
  test('accepts positive integers within range', () => {
    expect(isValidPartitionCount('1')).toBe(true);
    expect(isValidPartitionCount('32')).toBe(true);
  });

  test('rejects empty, zero, out-of-range and non-integer values', () => {
    expect(isValidPartitionCount('')).toBe(false);
    expect(isValidPartitionCount('0')).toBe(false);
    expect(isValidPartitionCount('33')).toBe(false);
    expect(isValidPartitionCount('2.5')).toBe(false);
    expect(isValidPartitionCount('-1')).toBe(false);
  });
});

describe('getPartitionColor', () => {
  test('cycles through the palette', () => {
    expect(getPartitionColor(0)).toBe(PARTITION_PALETTE[0]);
    expect(getPartitionColor(PARTITION_PALETTE.length)).toBe(PARTITION_PALETTE[0]);
  });
});

describe('isValidSensorRangeMeters', () => {
  test('accepts positive values and an empty optional value', () => {
    expect(isValidSensorRangeMeters('500')).toBe(true);
    expect(isValidSensorRangeMeters('')).toBe(true);
  });

  test('rejects zero, negative and non-numeric values', () => {
    expect(isValidSensorRangeMeters('0')).toBe(false);
    expect(isValidSensorRangeMeters('-10')).toBe(false);
    expect(isValidSensorRangeMeters('abc')).toBe(false);
  });
});

describe('wouldNewPointCrossBoundary', () => {
  test('allows a point snapped to an existing edge', () => {
    const boundary = [
      { lat: 0, lng: 0 },
      { lat: 0, lng: 10 },
      { lat: 10, lng: 10 },
      { lat: 10, lng: 0 },
    ];

    expect(
      wouldNewPointCrossBoundary(boundary, { lat: 0, lng: 5 }, 0)
    ).toBe(false);
  });
});
