"""Run and persist the frozen X0-C/D interface and coupling probe."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from hybrid.cell_ecm_coupling import CellECMVerticalSlice, build_cell_ecm_tether
from hybrid.remesh_registry import SurfaceMaterialRegistry, rebind_registry
from hybrid.remesh_transfer import (
    MyocardialMaterialField,
    RemeshEvent,
    RemeshOperation,
    SurfaceRegion,
    transfer_myocardial_state,
)
from route_h.ecm_finite_strain import build_ecm_reference


def x0c_probe() -> dict[str, object]:
    vertices = np.array(
        [[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [1.0, 1.0, 0.0], [0.0, 1.0, 0.0]],
        dtype=np.float64,
    )
    faces = np.array([[0, 1, 2], [0, 2, 3]], dtype=np.int64)
    swapped_faces = np.array([[0, 1, 3], [1, 2, 3]], dtype=np.int64)
    split_vertices = np.vstack((vertices, np.array([[0.5, 0.5, 0.0]])))
    split_faces = np.array(
        [[0, 1, 4], [1, 2, 4], [0, 4, 3], [4, 2, 3]],
        dtype=np.int64,
    )
    registry = SurfaceMaterialRegistry(
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
    field = MyocardialMaterialField(
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
    split_registry, _ = rebind_registry(
        registry,
        vertices,
        faces,
        split_vertices,
        split_faces,
    )
    cases = (
        (RemeshOperation.EDGE_SPLIT, registry, vertices, faces, split_vertices, split_faces),
        (RemeshOperation.EDGE_SWAP, registry, vertices, faces, vertices, swapped_faces),
        (RemeshOperation.EDGE_MERGE, split_registry, split_vertices, split_faces, vertices, faces),
    )
    reports: dict[str, dict[str, float | int]] = {}
    for operation, active_registry, old_vertices, old_faces, new_vertices, new_faces in cases:
        _, _, audit = transfer_myocardial_state(
            RemeshEvent(17, operation, 41, 42),
            active_registry,
            field,
            old_vertices,
            old_faces,
            new_vertices,
            new_faces,
        )
        reports[operation.value] = {
            "point_count": audit.point_count,
            "region_retention_fraction": audit.region_retention_fraction,
            "active_state_residual": audit.active_state_residual,
            "maximum_fiber_norm_error": audit.maximum_fiber_norm_error,
            "maximum_fiber_tangency_error": audit.maximum_fiber_tangency_error,
            "minimum_fiber_alignment": audit.minimum_fiber_alignment,
            "maximum_position_error": audit.rebind.maximum_position_error,
        }
    accepted = all(
        report["region_retention_fraction"] == 1.0
        and report["active_state_residual"] == 0.0
        and report["maximum_fiber_norm_error"] <= 1e-12
        and report["maximum_fiber_tangency_error"] <= 1e-12
        and report["minimum_fiber_alignment"] >= 1.0 - 1e-12
        and report["maximum_position_error"] <= 1e-12
        for report in reports.values()
    )
    return {"status": "passed" if accepted else "failed", "operations": reports}


def x0d_model(*, remeshed: bool) -> tuple[CellECMVerticalSlice, np.ndarray, np.ndarray]:
    cell_vertices = np.array(
        [
            [0.0, 0.0, 0.0], [1.0, 0.0, 0.0],
            [1.0, 1.0, 0.0], [0.0, 1.0, 0.0],
            [0.0, 0.0, 1.0], [1.0, 0.0, 1.0],
            [1.0, 1.0, 1.0], [0.0, 1.0, 1.0],
        ],
        dtype=np.float64,
    )
    cell_faces = np.array(
        [
            [0, 2, 1], [0, 3, 2], [4, 5, 6], [4, 6, 7],
            [0, 1, 5], [0, 5, 4], [1, 2, 6], [1, 6, 5],
            [2, 3, 7], [2, 7, 6], [3, 0, 4], [3, 4, 7],
        ],
        dtype=np.int64,
    )
    remeshed_faces = cell_faces.copy()
    remeshed_faces[:2] = np.array([[0, 3, 1], [1, 3, 2]], dtype=np.int64)
    ecm_vertices = np.array(
        [[0.0, 0.0, -0.1], [1.0, 0.0, -0.1], [0.0, 1.0, -0.1], [0.0, 0.0, -1.0]],
        dtype=np.float64,
    )
    ecm_tetrahedra = np.array([[0, 2, 1, 3]], dtype=np.int64)
    ecm_faces = np.array([[0, 1, 2]], dtype=np.int64)
    registry = SurfaceMaterialRegistry(
        point_ids=np.array([701], dtype=np.int64),
        face_ids=np.array([0], dtype=np.int64),
        barycentric=np.array([[0.2, 0.2, 0.6]], dtype=np.float64),
        reference_weights=np.array([0.25], dtype=np.float64),
        labels=("basal",),
        state=np.zeros((1, 0), dtype=np.float64),
    )
    tether = build_cell_ecm_tether(
        material_point_id=701,
        ecm_face_id=0,
        ecm_barycentric=np.array([0.0, 0.8, 0.2]),
        cell_reference_vertices=cell_vertices,
        cell_faces=cell_faces,
        registry=registry,
        ecm_reference_vertices=ecm_vertices,
        ecm_boundary_faces=ecm_faces,
        adhesion_work=0.02,
    )
    active_faces = cell_faces
    if remeshed:
        registry, _ = rebind_registry(
            registry,
            cell_vertices,
            cell_faces,
            cell_vertices,
            remeshed_faces,
        )
        active_faces = remeshed_faces
    model = CellECMVerticalSlice(
        cell_reference_vertices=cell_vertices,
        cell_faces=active_faces,
        cell_registry=registry,
        ecm_reference=build_ecm_reference(ecm_vertices, ecm_tetrahedra),
        ecm_boundary_faces=ecm_faces,
        tethers=(tether,),
    )
    return model, cell_vertices, ecm_vertices


def x0d_probe() -> dict[str, object]:
    original, cell, ecm = x0d_model(remeshed=False)
    remeshed, _, _ = x0d_model(remeshed=True)
    displaced = ecm + np.array([0.004, -0.003, -0.02])
    before = original.evaluate(cell, displaced)
    after = remeshed.evaluate(cell, displaced)
    remesh_energy_residual = abs(before.energies["total"] - after.energies["total"])
    remesh_force_residual = float(
        np.linalg.norm(before.cell_forces.sum(axis=0) - after.cell_forces.sum(axis=0))
    )

    deformed = ecm.copy()
    deformed[1] += np.array([0.01, -0.004, -0.015])
    rng = np.random.default_rng(20260801)
    cell_direction = rng.standard_normal(cell.shape)
    ecm_direction = rng.standard_normal(deformed.shape)
    direction_scale = np.sqrt(
        np.sum(cell_direction * cell_direction) + np.sum(ecm_direction * ecm_direction)
    )
    cell_direction /= direction_scale
    ecm_direction /= direction_scale
    step = 1e-7
    finite = (
        remeshed.evaluate(cell + step * cell_direction, deformed + step * ecm_direction).energies["total"]
        - remeshed.evaluate(cell - step * cell_direction, deformed - step * ecm_direction).energies["total"]
    ) / (2.0 * step)
    evaluation = remeshed.evaluate(cell, deformed)
    analytic = -float(
        np.sum(evaluation.cell_forces * cell_direction)
        + np.sum(evaluation.ecm_forces * ecm_direction)
    )
    derivative_residual = abs(finite - analytic) / max(1.0, abs(finite), abs(analytic))

    cell_velocity = np.zeros_like(cell)
    cell_velocity[:, 0] = 0.002
    ecm_velocity = np.zeros_like(ecm)
    ecm_velocity[:, 2] = -0.01
    power = remeshed.audit_prescribed_motion(
        cell,
        ecm,
        cell_velocity,
        ecm_velocity,
        duration=0.02,
        step_count=200,
    )
    metrics = {
        "remesh_energy_residual": remesh_energy_residual,
        "remesh_resultant_force_residual": remesh_force_residual,
        "pair_force_residual": evaluation.pair_force_residual,
        "pair_moment_residual": evaluation.pair_moment_residual,
        "force_directional_derivative_residual": derivative_residual,
        "normalized_integrated_power_residual": power.normalized_residual,
        "minimum_gap": evaluation.minimum_gap,
        "minimum_ecm_jacobian": float(np.min(evaluation.ecm_jacobians)),
    }
    accepted = (
        remesh_energy_residual <= 1e-12
        and remesh_force_residual <= 1e-12
        and evaluation.pair_force_residual <= 1e-10
        and evaluation.pair_moment_residual <= 1e-10
        and derivative_residual <= 1e-6
        and power.normalized_residual <= 5e-3
        and evaluation.minimum_gap > 0.0
        and np.min(evaluation.ecm_jacobians) > 0.0
    )
    return {"status": "passed" if accepted else "failed", "metrics": metrics}


def main() -> None:
    x0c = x0c_probe()
    x0d = x0d_probe()
    accepted = x0c["status"] == "passed" and x0d["status"] == "passed"
    summary = {
        "probe_id": "PRL-HYBRID-X0-CD-V01",
        "status": "passed" if accepted else "failed",
        "x0_c": x0c,
        "x0_d": x0d,
        "limits": {
            "material_position_error": 1e-12,
            "fiber_norm_error": 1e-12,
            "fiber_tangency_error": 1e-12,
            "pair_force_residual": 1e-10,
            "pair_moment_residual": 1e-10,
            "force_directional_derivative_residual": 1e-6,
            "normalized_integrated_power_residual": 5e-3,
        },
    }
    output = Path("results/hybrid/x0_cd_probe_v01/summary.json")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    if not accepted:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
