"""Run and persist the X0-B topology-independent material registry probe."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from hybrid.remesh_registry import (
    SurfaceMaterialRegistry,
    material_point_positions,
    rebind_registry,
    resultant_and_moment,
    scatter_material_forces,
)


def main() -> None:
    vertices = np.array(
        [[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [1.0, 1.0, 0.0], [0.0, 1.0, 0.0]],
        dtype=np.float64,
    )
    old_faces = np.array([[0, 1, 2], [0, 2, 3]], dtype=np.int64)
    swapped_faces = np.array([[0, 1, 3], [1, 2, 3]], dtype=np.int64)
    registry = SurfaceMaterialRegistry(
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
    rebound, rebind = rebind_registry(
        registry,
        vertices,
        old_faces,
        vertices,
        swapped_faces,
    )
    point_forces = np.array(
        [[0.7, -0.2, 0.5], [-0.1, 0.4, 0.3], [0.2, 0.1, -0.6]],
        dtype=np.float64,
    )
    point_positions = material_point_positions(registry, vertices, old_faces)
    expected_force, expected_moment = resultant_and_moment(point_positions, point_forces)
    new_nodal = scatter_material_forces(rebound, vertices, swapped_faces, point_forces)
    actual_force, actual_moment = resultant_and_moment(vertices, new_nodal)
    force_residual = float(np.linalg.norm(actual_force - expected_force))
    moment_residual = float(np.linalg.norm(actual_moment - expected_moment))
    accepted = (
        rebind.maximum_position_error <= 1e-12
        and rebind.id_retention_fraction == 1.0
        and rebind.state_retention_residual == 0.0
        and rebind.weight_retention_residual == 0.0
        and force_residual <= 1e-12
        and moment_residual <= 1e-12
    )
    summary = {
        "probe_id": "PRL-HYBRID-X0-B-REMESH-REGISTRY-V01",
        "status": "passed" if accepted else "failed",
        "point_count": rebind.point_count,
        "maximum_position_error": rebind.maximum_position_error,
        "id_retention_fraction": rebind.id_retention_fraction,
        "state_retention_residual": rebind.state_retention_residual,
        "weight_retention_residual": rebind.weight_retention_residual,
        "force_resultant_residual": force_residual,
        "moment_residual": moment_residual,
        "limits": {
            "maximum_position_error": 1e-12,
            "force_resultant_residual": 1e-12,
            "moment_residual": 1e-12,
        },
    }
    output = Path("results/hybrid/x0_probe_v01/summary.json")
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
