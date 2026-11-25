import axios from 'axios';

// An empty value means same-origin requests (relative URLs), used when the
// frontend proxies /api to the backend (see setupProxy.js).
const apiBaseUrl = (process.env.REACT_APP_API_BASE_URL ?? 'http://localhost:5000').replace(
  /\/+$/,
  ''
);
const MESH_API_BASE_URL = `${apiBaseUrl}/api/v1/meshes`;

// Extracts a readable message from the API's standardized error envelope.
const extractErrorMessage = (error, fallbackMessage) => {
  const apiError = error?.response?.data?.error;
  if (apiError) {
    const details =
      apiError.details && apiError.details.length > 0
        ? ` (${apiError.details.join('; ')})`
        : '';
    return `${apiError.message}${details}`;
  }
  return fallbackMessage;
};

// Builds the request body shared by every mesh endpoint, omitting optional
// fields that were not provided so the API applies its own defaults.
const buildRequestBody = (
  boundaryPoints,
  { maxEdgeLength, partitionCount, sensorRangeMeters } = {}
) => {
  const body = { boundaryPoints };
  if (maxEdgeLength != null) {
    body.maxEdgeLength = maxEdgeLength;
  }
  if (partitionCount != null) {
    body.partitionCount = partitionCount;
  }
  if (sensorRangeMeters != null) {
    body.sensorRangeMeters = sensorRangeMeters;
  }
  return body;
};

// Generates the mesh (Constrained Delaunay + Voronoi + sensor candidates) for
// the provided points. Returns { success, data } on success or { success, error }.
export const generateMesh = async (boundaryPoints, options = {}) => {
  try {
    const response = await axios.post(
      MESH_API_BASE_URL,
      buildRequestBody(boundaryPoints, options)
    );
    return { success: true, data: response.data.data };
  } catch (error) {
    return {
      success: false,
      error: extractErrorMessage(
        error,
        'Não foi possível gerar a malha. Verifique se a API está em execução.'
      ),
    };
  }
};

// Requests the mesh as GeoJSON and triggers the file download in the browser.
export const exportMeshAsGeoJson = async (boundaryPoints, options = {}) => {
  try {
    const response = await axios.post(
      `${MESH_API_BASE_URL}/geojson`,
      buildRequestBody(boundaryPoints, options),
      { responseType: 'blob' }
    );
    triggerFileDownload(response.data, 'mesh.geojson', 'application/geo+json');
    return { success: true };
  } catch (error) {
    return { success: false, error: await extractErrorMessageFromBlob(error) };
  }
};

const triggerFileDownload = (content, fileName, mimeType) => {
  const url = window.URL.createObjectURL(new Blob([content], { type: mimeType }));
  const link = document.createElement('a');
  link.href = url;
  link.download = fileName;
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.URL.revokeObjectURL(url);
};

// When a download fails the error response arrives as a Blob (responseType:
// 'blob'), so it must be read as text to recover the JSON error envelope.
const extractErrorMessageFromBlob = async (error) => {
  const fallbackMessage = 'Não foi possível exportar o GeoJSON.';
  const errorData = error?.response?.data;
  if (errorData instanceof Blob) {
    try {
      const text = await errorData.text();
      const body = JSON.parse(text);
      return body?.error
        ? extractErrorMessage({ response: { data: body } }, fallbackMessage)
        : fallbackMessage;
    } catch (_readError) {
      return fallbackMessage;
    }
  }
  return extractErrorMessage(error, fallbackMessage);
};
