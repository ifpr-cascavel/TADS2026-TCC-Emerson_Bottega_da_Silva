from __future__ import annotations

from flask import Blueprint

from ..responses.standardized_api_response import StandardizedApiResponse
from ..services.mesh_partitioning_service import MeshPartitioningService

status_controller = Blueprint("status_controller", __name__, url_prefix="/api/v1")

_mesh_partitioning_service = MeshPartitioningService()


@status_controller.route("/status", methods=["GET"])
def check_api_status():
    """Simple availability (health check) endpoint, useful to quickly confirm —
    including via cURL — that the API is up. Also reports whether METIS is
    available in the current environment."""
    return StandardizedApiResponse.success(
        {
            "status": "operational",
            "metisAvailable": _mesh_partitioning_service.is_metis_available(),
        }
    )
