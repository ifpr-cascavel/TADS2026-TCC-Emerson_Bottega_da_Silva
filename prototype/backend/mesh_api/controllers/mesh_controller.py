from __future__ import annotations

import json

from flask import Blueprint, Response, request

from ..responses.standardized_api_response import StandardizedApiResponse
from ..services.geojson_export_service import GeoJsonExportService
from ..extensions import GENERATION_RATE_LIMIT, limiter
from ..services.mesh_generation_service import MeshGenerationService
from ..validation.mesh_generation_request_validator import (
    MeshGenerationRequestValidator,
)

mesh_controller = Blueprint("mesh_controller", __name__, url_prefix="/api/v1/meshes")

_request_validator = MeshGenerationRequestValidator()
_mesh_generation_service = MeshGenerationService()
_geojson_export_service = GeoJsonExportService()


@mesh_controller.route("", methods=["POST"], strict_slashes=False)
@limiter.limit(GENERATION_RATE_LIMIT)
def generate_mesh():
    """Generate the Constrained Delaunay Triangulation and the Voronoi diagram for
    the provided points, returning the mesh in the standardized API envelope.
    Accepts an optional ``partitionCount`` to also partition the mesh."""
    validated_request = _request_validator.validate_and_convert(request.get_json(silent=True))
    result = _mesh_generation_service.generate(validated_request)
    return StandardizedApiResponse.success(result.to_dict())


@mesh_controller.route("/partitions", methods=["POST"], strict_slashes=False)
@limiter.limit(GENERATION_RATE_LIMIT)
def partition_mesh():
    """Generate the mesh and split it into balanced partitions (dual-graph
    partitioning via METIS). The request body is identical to the generation
    endpoint; ``partitionCount`` defaults to 2 here when omitted, since the
    purpose of this endpoint is explicitly to partition."""
    raw_body = request.get_json(silent=True)
    if isinstance(raw_body, dict) and raw_body.get("partitionCount") is None:
        raw_body = {**raw_body, "partitionCount": 2}

    validated_request = _request_validator.validate_and_convert(raw_body)
    result = _mesh_generation_service.generate(validated_request)
    return StandardizedApiResponse.success(result.to_dict())


@mesh_controller.route("/geojson", methods=["POST"], strict_slashes=False)
@limiter.limit(GENERATION_RATE_LIMIT)
def export_mesh_as_geojson():
    """Generate the mesh and return it as a GeoJSON file for download, in the
    standard format consumed by geoprocessing tools."""
    validated_request = _request_validator.validate_and_convert(request.get_json(silent=True))
    result = _mesh_generation_service.generate(validated_request)
    feature_collection = _geojson_export_service.convert_to_feature_collection(result)

    response_body = json.dumps(feature_collection, ensure_ascii=False)
    response = Response(response_body, mimetype="application/geo+json")
    response.headers["Content-Disposition"] = 'attachment; filename="mesh.geojson"'
    return response
