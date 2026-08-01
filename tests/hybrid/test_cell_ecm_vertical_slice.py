from __future__ import annotations

import numpy as np
import pytest

from hybrid.cell_ecm_coupling import CellECMVerticalSlice, build_cell_ecm_tether
from hybrid.remesh_registry import SurfaceMaterialRegistry, rebind_registry
from route_h.ecm_finite_strain import build_ecm_reference


CELL_VERTICES = np.array(
    [
        [0.0, 0.0, 0.0],
        [1.0, 0.0, 0.0],
        [1.0, 1.0, 0.0],
        [0.0, 1.0, 0.0],
        [0.0, 0.0, 1.0],
        [1.0, 0.0, 1.0],
        [1.0, 1.0, 1.0],
        [0.0, 1.0, 1.0],
    ],
    dtype=np.float64,
)
CELL_FACES = np.array(
    [
        [0, 2, 1], [0, 3, 2],
        [4, 5, 6], [4, 6, 7],
        [0, 1, 5], [0, 5, 4],
        [1, 2, 6], [1, 6, 5],
        [2, 3, 7], [2, 7, 6],
        [3, 0, 4], [3, 4, 7],
    ],
    dtype=np.int64,
)
REMESHED_CELL_FACES = CELL_FACES.copy()
REMESHED_CELL_FACES[:2] = np.array([[0, 3, 1], [1, 3, 2]], dtype=np.int64)

ECM_VERTICES = np.array(
    [
        [0.0, 0.0, -0.1],
        [1.0, 0.0, -0.1],
        [0.0, 1.0, -0.1],
        [0.0, 0.0, -1.0],
    ],
    dtype=np.float64,
)
ECM_TETRAHEDRA = np.array([[0, 2, 1, 3]], dtype=np.int64)
ECM_BOUNDARY_FACES = np.array([[0, 1, 2]], dtype=np.int64)


def registry() -> SurfaceMaterialRegistry:
    return SurfaceMaterialRegistry(
        point_ids=np.array([701], dtype=np.int64),
        face_ids=np.array([0], dtype=np.int64),
        barycentric=np.array([[0.2, 0.2, 0.6]], dtype=np.float64),
        reference_weights=np.array([0.25], dtype=np.float64),
        labels=("basal",),
        state=np.zeros((1, 0), dtype=np.float64),
    )


def model(*, remeshed: bool = False) -> CellECMVerticalSlice:
    original_registry = registry()
    tether = build_cell_ecm_tether(
        material_point_id=701,
        ecm_face_id=0,
        ecm_barycentric=np.array([0.0, 0.8, 0.2]),
        cell_reference_vertices=CELL_VERTICES,
        cell_faces=CELL_FACES,
        registry=original_registry,
        ecm_reference_vertices=ECM_VERTICES,
        ecm_boundary_faces=ECM_BOUNDARY_FACES,
        adhesion_work=0.02,
        tangential_stiffness=0.5,
    )
    faces = CELL_FACES
    active_registry = original_registry
    if remeshed:
        active_registry, _ = rebind_registry(
            original_registry,
            CELL_VERTICES,
            CELL_FACES,
            CELL_VERTICES,
            REMESHED_CELL_FACES,
        )
        faces = REMESHED_CELL_FACES
    return CellECMVerticalSlice(
        cell_reference_vertices=CELL_VERTICES,
        cell_faces=faces,
        cell_registry=active_registry,
        ecm_reference=build_ecm_reference(ECM_VERTICES, ECM_TETRAHEDRA),
        ecm_boundary_faces=ECM_BOUNDARY_FACES,
        tethers=(tether,),
    )


def test_remeshing_preserves_cell_ecm_tether_response() -> None:
    displaced_ecm = ECM_VERTICES + np.array([0.0, 0.0, -0.02])
    before = model().evaluate(CELL_VERTICES, displaced_ecm)
    after = model(remeshed=True).evaluate(CELL_VERTICES, displaced_ecm)
    assert abs(before.energies["total"] - after.energies["total"]) <= 1e-12
    np.testing.assert_allclose(
        before.cell_forces.sum(axis=0),
        after.cell_forces.sum(axis=0),
        atol=1e-12,
        rtol=0.0,
    )
    np.testing.assert_allclose(
        before.ecm_forces.sum(axis=0),
        after.ecm_forces.sum(axis=0),
        atol=1e-12,
        rtol=0.0,
    )


def test_vertical_slice_pair_force_and_moment_are_balanced() -> None:
    displaced_ecm = ECM_VERTICES + np.array([0.004, -0.003, -0.02])
    evaluation = model(remeshed=True).evaluate(CELL_VERTICES, displaced_ecm)
    assert evaluation.pair_force_residual <= 1e-10
    assert evaluation.pair_moment_residual <= 1e-10
    assert evaluation.minimum_gap > 0.0
    assert np.min(evaluation.ecm_jacobians) > 0.0


def test_vertical_slice_force_matches_total_energy_directional_derivative() -> None:
    vertical_slice = model(remeshed=True)
    cell = CELL_VERTICES.copy()
    ecm = ECM_VERTICES.copy()
    ecm[1] += np.array([0.01, -0.004, -0.015])
    rng = np.random.default_rng(20260801)
    cell_direction = rng.standard_normal(cell.shape)
    ecm_direction = rng.standard_normal(ecm.shape)
    scale = np.sqrt(
        np.sum(cell_direction * cell_direction)
        + np.sum(ecm_direction * ecm_direction)
    )
    cell_direction /= scale
    ecm_direction /= scale
    step = 1e-7
    plus = vertical_slice.evaluate(
        cell + step * cell_direction,
        ecm + step * ecm_direction,
    ).energies["total"]
    minus = vertical_slice.evaluate(
        cell - step * cell_direction,
        ecm - step * ecm_direction,
    ).energies["total"]
    finite = (plus - minus) / (2.0 * step)
    evaluation = vertical_slice.evaluate(cell, ecm)
    analytic = -float(
        np.sum(evaluation.cell_forces * cell_direction)
        + np.sum(evaluation.ecm_forces * ecm_direction)
    )
    residual = abs(finite - analytic) / max(1.0, abs(finite), abs(analytic))
    assert residual <= 1e-6


def test_vertical_slice_prescribed_motion_closes_power_ledger() -> None:
    vertical_slice = model(remeshed=True)
    cell_velocity = np.zeros_like(CELL_VERTICES)
    cell_velocity[:, 0] = 0.002
    ecm_velocity = np.zeros_like(ECM_VERTICES)
    ecm_velocity[:, 2] = -0.01
    audit = vertical_slice.audit_prescribed_motion(
        CELL_VERTICES,
        ECM_VERTICES,
        cell_velocity,
        ecm_velocity,
        duration=0.02,
        step_count=200,
    )
    assert audit.normalized_residual <= 5e-3


def test_vertical_slice_rejects_an_open_cell_surface() -> None:
    valid = model()
    with pytest.raises(ValueError, match="closed two-manifold"):
        CellECMVerticalSlice(
            cell_reference_vertices=valid.cell_reference_vertices,
            cell_faces=valid.cell_faces[:-1],
            cell_registry=valid.cell_registry,
            ecm_reference=valid.ecm_reference,
            ecm_boundary_faces=valid.ecm_boundary_faces,
            tethers=valid.tethers,
        )


def test_vertical_slice_fails_fast_on_cell_ecm_penetration() -> None:
    penetrated_ecm = ECM_VERTICES + np.array([0.0, 0.0, 0.2])
    with pytest.raises(ValueError, match="penetration"):
        model().evaluate(CELL_VERTICES, penetrated_ecm)
