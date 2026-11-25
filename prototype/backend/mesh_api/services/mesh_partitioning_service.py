from __future__ import annotations

from collections import defaultdict

import numpy as np

try:  # METIS is a native library; its Python binding may be unavailable on Windows.
    import pymetis

    _METIS_IS_AVAILABLE = True
except ImportError:  # pragma: no cover - depends on the runtime environment.
    pymetis = None
    _METIS_IS_AVAILABLE = False


class MeshPartitioningService:
    """Splits a triangular mesh into balanced partitions.

    The mesh is modeled as a **dual graph**: each triangle is a node and two
    triangles are connected when they share an edge. Partitioning that graph
    into balanced groups while minimizing the number of cut edges is exactly the
    classic graph-partitioning problem used in parallel/finite-element computing:
    balancing the work per processor and reducing the communication between
    partitions.

    Primary strategy: **METIS** (via ``pymetis``), a multilevel graph
    partitioner that produces high-quality, balanced partitions at low cost.

    Fallback strategy: **Recursive Coordinate Bisection (RCB)**, a pure-NumPy
    geometric method that recursively splits the triangle centroids along their
    axis of largest spread. It requires no native dependency, so the feature
    keeps working on environments where METIS cannot be installed (e.g. Windows
    without a prebuilt wheel).

    Note on parallelism: METIS only *computes* the partitioning; it does not run
    anything in parallel. Distributing each partition across processes/threads is
    a separate responsibility of the application that consumes this result.
    """

    def is_metis_available(self) -> bool:
        return _METIS_IS_AVAILABLE

    def partition(
        self,
        mesh_coordinates: np.ndarray,
        triangles: list[list[int]],
        requested_partition_count: int,
    ) -> tuple[list[int], int, str]:
        """Assign a partition id to each triangle.

        Returns a tuple ``(memberships, effective_partition_count, method)``.
        ``memberships`` is aligned by index with ``triangles``. When no
        partitioning is requested (count <= 1) it returns an empty list.
        """
        triangle_count = len(triangles)
        if requested_partition_count <= 1 or triangle_count <= 1:
            return [], 1, "none"

        # A mesh cannot be split into more parts than it has triangles.
        effective_partition_count = min(requested_partition_count, triangle_count)

        if _METIS_IS_AVAILABLE:
            memberships = self._partition_with_metis(triangles, effective_partition_count)
            method = "metis"
        else:
            memberships = self._partition_with_recursive_coordinate_bisection(
                mesh_coordinates, triangles, effective_partition_count
            )
            method = "recursive-coordinate-bisection"

        memberships = self._enforce_contiguity(
            triangles, memberships, effective_partition_count
        )

        return memberships, effective_partition_count, method

    def _partition_with_metis(
        self, triangles: list[list[int]], partition_count: int
    ) -> list[int]:
        adjacency = self._build_dual_graph_adjacency(triangles)
        _edge_cuts, memberships = pymetis.part_graph(partition_count, adjacency=adjacency)
        return list(memberships)

    @staticmethod
    def _build_dual_graph_adjacency(triangles: list[list[int]]) -> list[list[int]]:
        """Build the triangle adjacency list (dual graph) from shared edges."""
        edge_to_triangles: dict[frozenset[int], list[int]] = defaultdict(list)
        for triangle_index, triangle in enumerate(triangles):
            triangle_edges = (
                frozenset((triangle[0], triangle[1])),
                frozenset((triangle[1], triangle[2])),
                frozenset((triangle[2], triangle[0])),
            )
            for edge in triangle_edges:
                edge_to_triangles[edge].append(triangle_index)

        neighbors: list[set[int]] = [set() for _ in triangles]
        for triangles_sharing_edge in edge_to_triangles.values():
            if len(triangles_sharing_edge) == 2:
                first, second = triangles_sharing_edge
                neighbors[first].add(second)
                neighbors[second].add(first)

        return [sorted(neighbor_set) for neighbor_set in neighbors]

    def _enforce_contiguity(
        self,
        triangles: list[list[int]],
        memberships: list[int],
        partition_count: int,
    ) -> list[int]:
        """Ensure each partition forms a single connected component in the dual graph.

        In non-convex, branching or concave geometries (e.g. Y-shaped lakes or
        curved bodies of water), coordinate-based cuts or unconstrained partitioning
        can leave isolated triangles ('islands') disconnected from their main
        cluster.

        This method detects any disconnected components within each partition and
        reassigns smaller disconnected 'islands' to the neighboring partition with
        which they share the most boundary edges, guaranteeing spatial contiguity.
        """
        if not memberships or partition_count <= 1:
            return memberships

        adjacency = self._build_dual_graph_adjacency(triangles)
        memberships = list(memberships)

        for _ in range(15):
            changed = False
            for p in range(partition_count):
                partition_triangles = [
                    i for i, part in enumerate(memberships) if part == p
                ]
                if len(partition_triangles) <= 1:
                    continue

                p_set = set(partition_triangles)
                visited: set[int] = set()
                components: list[list[int]] = []

                for tri in partition_triangles:
                    if tri in visited:
                        continue
                    comp: list[int] = []
                    queue = [tri]
                    visited.add(tri)
                    while queue:
                        curr = queue.pop(0)
                        comp.append(curr)
                        for nbr in adjacency[curr]:
                            if nbr in p_set and nbr not in visited:
                                visited.add(nbr)
                                queue.append(nbr)
                    components.append(comp)

                if len(components) > 1:
                    components.sort(key=len, reverse=True)
                    for island in components[1:]:
                        island_set = set(island)
                        votes: dict[int, int] = defaultdict(int)
                        for tri in island:
                            for nbr in adjacency[tri]:
                                if nbr not in island_set:
                                    votes[memberships[nbr]] += 1
                        if votes:
                            best_p = max(votes.items(), key=lambda item: item[1])[0]
                            for tri in island:
                                memberships[tri] = best_p
                            changed = True

            if not changed:
                break

        return memberships

    def _partition_with_recursive_coordinate_bisection(
        self,
        mesh_coordinates: np.ndarray,
        triangles: list[list[int]],
        partition_count: int,
    ) -> list[int]:
        centroids = np.array(
            [mesh_coordinates[triangle].mean(axis=0) for triangle in triangles]
        )
        memberships = [0] * len(triangles)
        all_indices = list(range(len(triangles)))
        next_partition_id = self._bisect(centroids, all_indices, partition_count, memberships, 0)
        # ``next_partition_id`` equals the number of partitions actually produced.
        del next_partition_id
        return memberships

    def _bisect(
        self,
        centroids: np.ndarray,
        indices: list[int],
        partition_count: int,
        memberships: list[int],
        first_partition_id: int,
    ) -> int:
        """Recursively split ``indices`` into ``partition_count`` groups, writing
        the assigned ids into ``memberships``. Returns the next free id."""
        if partition_count <= 1 or len(indices) <= 1:
            for index in indices:
                memberships[index] = first_partition_id
            return first_partition_id + 1

        left_count = partition_count // 2
        right_count = partition_count - left_count

        subset = centroids[indices]
        spread = subset.max(axis=0) - subset.min(axis=0)
        split_axis = int(np.argmax(spread))

        ordered = sorted(indices, key=lambda index: centroids[index][split_axis])
        # Split proportionally to the number of partitions each side must hold,
        # keeping the groups balanced in triangle count.
        split_position = round(len(ordered) * left_count / partition_count)
        split_position = max(1, min(split_position, len(ordered) - 1))

        left_indices = ordered[:split_position]
        right_indices = ordered[split_position:]

        next_id = self._bisect(
            centroids, left_indices, left_count, memberships, first_partition_id
        )
        next_id = self._bisect(
            centroids, right_indices, right_count, memberships, next_id
        )
        return next_id
