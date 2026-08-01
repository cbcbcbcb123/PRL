from __future__ import annotations

import numpy as np
import pytest

from hybrid.remesh_registry import SurfaceMaterialRegistry, rebind_registry
from hybrid.remesh_transfer import (
    MyocardialMaterialField,
    RemeshEvent,
    RemeshOperation,
    SurfaceRegion,
    transfer_myocardial_state,
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
SPLIT_VERTICES = np.vstack((VERTICES, np.array([[0.5, 0.5, 0.0]])))
SPLIT_FACES = np.array(
    [[0, 1, 4], [1, 2, 4], [0, 4, 3], [4, 2, 3]],
    dtype=np.int64,
)


def registry() -> SurfaceMaterialRegistry:
    return SurfaceMaterialRegistry(
        point_ids=np.array([101, 205, 999], dtype=np.int64),
        face_ids=np.array([0, 1, 1], dtype=np.int64),
        barycentric=np.array(
            [[0.2, 0.3, 0.5], [0.4, 0.25, 0.35], [0.7, 0.2, 0.1]],
            dtype=np.float64,
        ),
        reference_weights=np.array([0.17, 0.23, 0.11], dtype=np.float64),
        labels=("apical", "basal", "lateral"),
        state=np.zeros((3, 0), dtype=np.float64),
    )


def myocardial_field() -> MyocardialMaterialField:
    return MyocardialMaterialField(
        point_ids=np.array([999, 101, 205], dtype=np.int64),
        regions=(SurfaceRegion.LATERAL, SurfaceRegion.APICAL, SurfaceRegion.BASAL),
        fiber_directions=np.array(
            [[0.6, 0.8, 0.0], [1.0, 0.0, 0.0], [0.0, 1.0, 0.0]],
            dtype=np.float64,
        ),
        active_state=np.array(
            [[0.9, -0.1], [0.2, 0.3], [0.4, 0.7]],
            dtype=np.float64,
        ),
    )


def event(operation: RemeshOperation) -> RemeshEvent:
    return RemeshEvent(
        cell_id=17,
        operation=operation,
        before_revision=41,
        after_revision=42,
    )


def assert_transfer_is_conservative(original, transferred, audit, operation) -> None:
    expected_order = np.array([101, 205, 999], dtype=np.int64)
    np.testing.assert_array_equal(transferred.point_ids, expected_order)
    np.testing.assert_array_equal(
        transferred.active_state,
        original.active_state[[1, 2, 0]],
    )
    assert transferred.regions == (
        SurfaceRegion.APICAL,
        SurfaceRegion.BASAL,
        SurfaceRegion.LATERAL,
    )
    np.testing.assert_allclose(
        transferred.fiber_directions,
        original.fiber_directions[[1, 2, 0]],
        atol=1e-12,
        rtol=0.0,
    )
    assert audit.operation is operation
    assert audit.point_count == 3
    assert audit.region_retention_fraction == 1.0
    assert audit.active_state_residual == 0.0
    assert audit.maximum_fiber_norm_error <= 1e-12
    assert audit.maximum_fiber_tangency_error <= 1e-12
    assert audit.minimum_fiber_alignment >= 1.0 - 1e-12


def test_edge_swap_preserves_myocardial_material_semantics() -> None:
    original = myocardial_field()
    _, transferred, audit = transfer_myocardial_state(
        event(RemeshOperation.EDGE_SWAP),
        registry(),
        original,
        VERTICES,
        OLD_FACES,
        VERTICES,
        SWAPPED_FACES,
    )
    assert_transfer_is_conservative(
        original,
        transferred,
        audit,
        RemeshOperation.EDGE_SWAP,
    )


def test_edge_split_preserves_myocardial_material_semantics() -> None:
    original = myocardial_field()
    _, transferred, audit = transfer_myocardial_state(
        event(RemeshOperation.EDGE_SPLIT),
        registry(),
        original,
        VERTICES,
        OLD_FACES,
        SPLIT_VERTICES,
        SPLIT_FACES,
    )
    assert_transfer_is_conservative(
        original,
        transferred,
        audit,
        RemeshOperation.EDGE_SPLIT,
    )


def test_edge_merge_preserves_myocardial_material_semantics() -> None:
    split_registry, _ = rebind_registry(
        registry(),
        VERTICES,
        OLD_FACES,
        SPLIT_VERTICES,
        SPLIT_FACES,
    )
    original = myocardial_field()
    _, transferred, audit = transfer_myocardial_state(
        event(RemeshOperation.EDGE_MERGE),
        split_registry,
        original,
        SPLIT_VERTICES,
        SPLIT_FACES,
        VERTICES,
        OLD_FACES,
    )
    assert_transfer_is_conservative(
        original,
        transferred,
        audit,
        RemeshOperation.EDGE_MERGE,
    )


def test_remesh_event_rejects_nonmonotone_revision() -> None:
    with pytest.raises(ValueError, match="after_revision"):
        RemeshEvent(
            cell_id=17,
            operation=RemeshOperation.EDGE_SWAP,
            before_revision=4,
            after_revision=4,
        )
