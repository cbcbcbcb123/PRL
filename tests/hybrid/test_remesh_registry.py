from __future__ import annotations

import numpy as np
import pytest

from hybrid.remesh_registry import (
    SurfaceMaterialRegistry,
    material_point_positions,
    rebind_registry,
    resultant_and_moment,
    scatter_material_forces,
)


VERTICES = np.array(
    [
        [0.0, 0.0, 0.0],
        [1.0, 0.0, 0.0],
        [1.0, 1.0, 0.0],
        [0.0, 1.0, 0.0],
    ],
    dtype=np.float64,
)
OLD_FACES = np.array([[0, 1, 2], [0, 2, 3]], dtype=np.int64)
SWAPPED_FACES = np.array([[0, 1, 3], [1, 2, 3]], dtype=np.int64)


def registry() -> SurfaceMaterialRegistry:
    return SurfaceMaterialRegistry(
        point_ids=np.array([101, 205, 999], dtype=np.int64),
        face_ids=np.array([0, 1, 1], dtype=np.int64),
        barycentric=np.array(
            [[0.2, 0.3, 0.5], [0.4, 0.25, 0.35], [0.7, 0.2, 0.1]],
            dtype=np.float64,
        ),
        reference_weights=np.array([0.17, 0.23, 0.11], dtype=np.float64),
        labels=("apical", "basal", "basal"),
        state=np.array(
            [[1.0, 0.0, 0.2], [0.0, 1.0, 0.4], [0.6, 0.8, 0.9]],
            dtype=np.float64,
        ),
    )


def assert_exact_state_retention(original, rebound, report) -> None:
    np.testing.assert_array_equal(rebound.point_ids, original.point_ids)
    np.testing.assert_array_equal(rebound.reference_weights, original.reference_weights)
    np.testing.assert_array_equal(rebound.state, original.state)
    assert rebound.labels == original.labels
    assert report.id_retention_fraction == 1.0
    assert report.state_retention_residual == 0.0
    assert report.weight_retention_residual == 0.0
    assert report.maximum_position_error <= 1e-12


def test_material_state_survives_edge_swap() -> None:
    original = registry()
    rebound, report = rebind_registry(
        original,
        VERTICES,
        OLD_FACES,
        VERTICES,
        SWAPPED_FACES,
    )
    assert_exact_state_retention(original, rebound, report)
    np.testing.assert_allclose(
        material_point_positions(original, VERTICES, OLD_FACES),
        material_point_positions(rebound, VERTICES, SWAPPED_FACES),
        atol=1e-12,
        rtol=0.0,
    )


def test_material_state_survives_edge_split() -> None:
    split_vertices = np.vstack((VERTICES, np.array([[0.5, 0.5, 0.0]])))
    split_faces = np.array(
        [[0, 1, 4], [1, 2, 4], [0, 4, 3], [4, 2, 3]],
        dtype=np.int64,
    )
    original = registry()
    rebound, report = rebind_registry(
        original,
        VERTICES,
        OLD_FACES,
        split_vertices,
        split_faces,
    )
    assert_exact_state_retention(original, rebound, report)


def test_force_scatter_preserves_resultant_and_moment_after_swap() -> None:
    original = registry()
    rebound, _ = rebind_registry(
        original,
        VERTICES,
        OLD_FACES,
        VERTICES,
        SWAPPED_FACES,
    )
    material_forces = np.array(
        [[0.7, -0.2, 0.5], [-0.1, 0.4, 0.3], [0.2, 0.1, -0.6]],
        dtype=np.float64,
    )
    point_positions = material_point_positions(original, VERTICES, OLD_FACES)
    expected_force, expected_moment = resultant_and_moment(
        point_positions,
        material_forces,
    )

    old_nodal = scatter_material_forces(original, VERTICES, OLD_FACES, material_forces)
    new_nodal = scatter_material_forces(rebound, VERTICES, SWAPPED_FACES, material_forces)
    old_force, old_moment = resultant_and_moment(VERTICES, old_nodal)
    new_force, new_moment = resultant_and_moment(VERTICES, new_nodal)

    np.testing.assert_allclose(old_force, expected_force, atol=1e-12, rtol=0.0)
    np.testing.assert_allclose(new_force, expected_force, atol=1e-12, rtol=0.0)
    np.testing.assert_allclose(old_moment, expected_moment, atol=1e-12, rtol=0.0)
    np.testing.assert_allclose(new_moment, expected_moment, atol=1e-12, rtol=0.0)


def test_rebind_fails_if_geometry_moves_outside_frozen_distance() -> None:
    shifted = VERTICES.copy()
    shifted[:, 2] = 1e-4
    with pytest.raises(ValueError, match="cannot be rebound"):
        rebind_registry(
            registry(),
            VERTICES,
            OLD_FACES,
            shifted,
            SWAPPED_FACES,
            maximum_distance=1e-8,
        )
