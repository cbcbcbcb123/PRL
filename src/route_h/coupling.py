"""Reference pairing, source ownership, and dynamic contact search helpers."""

from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations

import numpy as np
from numpy.typing import NDArray

from .contact_adhesion import steric_pair_energy_force


FloatArray = NDArray[np.float64]
IntArray = NDArray[np.int64]


@dataclass(frozen=True)
class SurfaceEntity:
    entity_id: str
    vertices: FloatArray
    faces: IntArray
    source_vertex_ids: IntArray
    source_weights: FloatArray


def aabb_distance(vertices_a: FloatArray, vertices_b: FloatArray) -> float:
    minimum_a, maximum_a = vertices_a.min(axis=0), vertices_a.max(axis=0)
    minimum_b, maximum_b = vertices_b.min(axis=0), vertices_b.max(axis=0)
    separation = np.maximum(np.maximum(minimum_a - maximum_b, minimum_b - maximum_a), 0.0)
    return float(np.linalg.norm(separation))


def eligible_entity_pairs(
    entities: list[SurfaceEntity],
    *,
    search_buffer: float = 0.12,
) -> list[tuple[int, int]]:
    return [
        pair for pair in combinations(range(len(entities)), 2)
        if aabb_distance(entities[pair[0]].vertices, entities[pair[1]].vertices) <= search_buffer
    ]


def ordered_steric_pair(
    first: SurfaceEntity,
    second: SurfaceEntity,
    *,
    k_rep: float = 200.0,
) -> tuple[float, FloatArray, FloatArray, int, float]:
    energy_ab, force_a_ab, force_b_ab, records_ab = steric_pair_energy_force(
        first.vertices, first.source_vertex_ids, first.source_weights,
        second.vertices, second.faces, k_rep=k_rep,
    )
    energy_ba, force_b_ba, force_a_ba, records_ba = steric_pair_energy_force(
        second.vertices, second.source_vertex_ids, second.source_weights,
        first.vertices, first.faces, k_rep=k_rep,
    )
    force_a = force_a_ab + force_a_ba
    force_b = force_b_ab + force_b_ba
    minimum_gap = min(
        [record.signed_gap for record in records_ab + records_ba],
        default=float("inf"),
    )
    return (
        energy_ab + energy_ba,
        force_a,
        force_b,
        len(records_ab) + len(records_ba),
        minimum_gap,
    )


def zero_myocardial_source_assembly(
    source_map_integer: IntArray,
    source_map_float: FloatArray,
    tetrahedron_count: int,
    *,
    j_myo: float = 0.0,
) -> tuple[FloatArray, float]:
    if j_myo != 0.0:
        raise PermissionError("Nonzero j_myo is not authorized in Stage 1.")
    if len(source_map_integer) != len(source_map_float):
        raise ValueError("source-map integer/float record count mismatch")
    source = np.zeros(tetrahedron_count, dtype=np.float64)
    power = 0.0
    return source, power


def source_map_coverage(
    source_map_integer: IntArray,
    myocardial_indices: IntArray,
    cell_primary: IntArray,
    basal_code: int,
) -> tuple[int, int]:
    expected = int(np.sum(cell_primary[myocardial_indices] == basal_code))
    keys = {(int(row[1]), int(row[2])) for row in source_map_integer}
    return expected, len(keys)

