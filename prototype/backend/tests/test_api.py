import pytest

from mesh_api import create_application

SQUARE_BOUNDARY = [
    {"lat": -25.430, "lng": -49.270},
    {"lat": -25.430, "lng": -49.260},
    {"lat": -25.440, "lng": -49.260},
    {"lat": -25.440, "lng": -49.270},
]


@pytest.fixture
def client():
    application = create_application()
    application.config.update(TESTING=True, RATELIMIT_ENABLED=False)
    return application.test_client()


def test_status_reports_operational(client):
    response = client.get("/api/v1/status")

    assert response.status_code == 200
    body = response.get_json()
    assert body["success"] is True
    assert body["data"]["status"] == "operational"


def test_generate_mesh_returns_triangles(client):
    response = client.post("/api/v1/meshes", json={"boundaryPoints": SQUARE_BOUNDARY})

    assert response.status_code == 200
    data = response.get_json()["data"]
    assert len(data["triangles"]) > 0
    assert len(data["meshPoints"]) >= len(SQUARE_BOUNDARY)


def test_partition_mesh_defaults_to_two_partitions(client):
    response = client.post(
        "/api/v1/meshes/partitions", json={"boundaryPoints": SQUARE_BOUNDARY}
    )

    assert response.status_code == 200
    assert response.get_json()["data"]["partitionCount"] == 2


def test_geojson_export_returns_feature_collection(client):
    response = client.post(
        "/api/v1/meshes/geojson", json={"boundaryPoints": SQUARE_BOUNDARY}
    )

    assert response.status_code == 200
    assert response.mimetype == "application/geo+json"
    assert response.get_json()["type"] == "FeatureCollection"


def test_rejects_too_few_points(client):
    response = client.post(
        "/api/v1/meshes", json={"boundaryPoints": SQUARE_BOUNDARY[:2]}
    )

    assert response.status_code == 400
    assert response.get_json()["success"] is False


def test_partitioning_guarantees_contiguous_partitions(client):
    y_shaped_boundary = [
        {'lat': -24.960, 'lng': -53.445},
        {'lat': -24.958, 'lng': -53.442},
        {'lat': -24.960, 'lng': -53.440},
        {'lat': -24.965, 'lng': -53.441},
        {'lat': -24.968, 'lng': -53.435},
        {'lat': -24.972, 'lng': -53.436},
        {'lat': -24.969, 'lng': -53.442},
        {'lat': -24.976, 'lng': -53.441},
        {'lat': -24.977, 'lng': -53.443},
        {'lat': -24.975, 'lng': -53.445},
        {'lat': -24.969, 'lng': -53.444},
        {'lat': -24.966, 'lng': -53.450},
        {'lat': -24.964, 'lng': -53.448},
        {'lat': -24.963, 'lng': -53.445},
    ]
    response = client.post(
        '/api/v1/meshes/partitions',
        json={'boundaryPoints': y_shaped_boundary, 'partitionCount': 4},
    )
    assert response.status_code == 200
    data = response.get_json()['data']
    triangles = data['triangles']
    partitions = data['trianglePartitions']

    from mesh_api.services.mesh_partitioning_service import MeshPartitioningService
    adj = MeshPartitioningService._build_dual_graph_adjacency(triangles)

    for p in range(4):
        p_triangles = [i for i, part in enumerate(partitions) if part == p]
        if not p_triangles:
            continue
        p_set = set(p_triangles)
        visited = set()
        queue = [p_triangles[0]]
        visited.add(p_triangles[0])
        while queue:
            curr = queue.pop(0)
            for nbr in adj[curr]:
                if nbr in p_set and nbr not in visited:
                    visited.add(nbr)
                    queue.append(nbr)
        assert len(visited) == len(p_triangles), f'Partition {p} has disconnected islands!'
