"""Materialize numerical manufactured metrics for the failed Gate A package."""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
import sys
from typing import Any

import numpy as np


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = REPOSITORY_ROOT / "src"
if str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT))

from route_h.activation import (  # noqa: E402
    active_energy_force,
    active_input_power,
    activation_protocol,
    build_active_reference,
    transverse_scale_changes,
)
from route_h.dcm_cell import (  # noqa: E402
    _hinge_angle_gradient,
    _hinge_angle_gradients_bulk,
    build_cell_reference,
)
from route_h.discretization import load_discretization_level  # noqa: E402


OUTPUT_PATH = (
    REPOSITORY_ROOT
    / "tests/route_h/stage2_gate_a_manufactured_metrics_v01.json"
)


def _canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def main() -> int:
    arrays, _ = load_discretization_level("base")
    cell_id = 6
    vertices = arrays["cell_vertices"][cell_id]
    faces = arrays["cell_faces"][cell_id]
    counts = arrays["cell_anchor_counts"][cell_id]
    minus = arrays["cell_anchor_minus_face_ids"][
        cell_id, : int(counts[0])
    ]
    plus = arrays["cell_anchor_plus_face_ids"][
        cell_id, : int(counts[1])
    ]
    active_reference = build_active_reference(
        vertices,
        faces,
        minus,
        plus,
    )
    cell_reference = build_cell_reference(
        vertices,
        faces,
        arrays["cell_primary_identity"][cell_id],
        arrays["cell_directional_identity"][cell_id],
    )

    rng = np.random.default_rng(20260731)
    current = vertices + 2.0e-3 * rng.standard_normal(vertices.shape)
    direction = rng.standard_normal(vertices.shape)
    direction /= np.linalg.norm(direction)
    alpha = 0.07
    _, force, state = active_energy_force(
        current,
        active_reference,
        alpha=alpha,
        alpha_rate=0.03,
    )
    finite_difference_step = 1.0e-7
    plus_energy = active_energy_force(
        current + finite_difference_step * direction,
        active_reference,
        alpha=alpha,
    )[0]
    minus_energy = active_energy_force(
        current - finite_difference_step * direction,
        active_reference,
        alpha=alpha,
    )[0]
    finite_difference = (
        plus_energy - minus_energy
    ) / (2.0 * finite_difference_step)
    analytic = -float(np.sum(force * direction))
    derivative_relative_error = abs(finite_difference - analytic) / max(
        1.0,
        abs(finite_difference),
        abs(analytic),
    )
    centroid = np.mean(current, axis=0)
    net_force = float(np.linalg.norm(force.sum(axis=0)))
    net_moment = float(
        np.linalg.norm(np.cross(current - centroid, force).sum(axis=0))
    )

    angle = 0.37
    rotation = np.asarray(
        [
            [math.cos(angle), -math.sin(angle), 0.0],
            [math.sin(angle), math.cos(angle), 0.0],
            [0.0, 0.0, 1.0],
        ]
    )
    translation = np.asarray([0.7, -0.4, 0.2])
    transformed_reference = build_active_reference(
        vertices @ rotation.T + translation,
        faces,
        minus,
        plus,
    )
    transformed_current = current @ rotation.T + translation
    energy, force, _ = active_energy_force(
        current,
        active_reference,
        alpha=alpha,
    )
    transformed_energy, transformed_force, _ = active_energy_force(
        transformed_current,
        transformed_reference,
        alpha=alpha,
    )
    dual_weights = arrays["cell_gauge_dual_area_weights"][cell_id]
    transverse = transverse_scale_changes(
        current,
        active_reference,
        dual_weights,
    )
    transformed_transverse = transverse_scale_changes(
        transformed_current,
        transformed_reference,
        dual_weights,
    )

    perturbed = vertices + 1.0e-4 * rng.standard_normal(vertices.shape)
    local = perturbed[cell_reference.hinges.vertices]
    vector_angles, vector_gradients = _hinge_angle_gradients_bulk(local)
    scalar = [_hinge_angle_gradient(item) for item in local]
    scalar_angles = np.asarray([item[0] for item in scalar])
    scalar_gradients = np.asarray([item[1] for item in scalar])

    loading_alpha, loading_alpha_rate = activation_protocol(
        1.5,
        alpha_peak=0.1,
    )
    _, _, loading_state = active_energy_force(
        vertices,
        active_reference,
        alpha=loading_alpha,
        alpha_rate=loading_alpha_rate,
    )
    metrics = {
        "metrics_id": "PRL-ROUTE-H-STAGE2-GATE-A-MANUFACTURED-V01",
        "formal_response_rerun": False,
        "active_directional_derivative_relative_error": (
            derivative_relative_error
        ),
        "active_net_force": net_force,
        "active_net_moment": net_moment,
        "active_rigid_energy_absolute_error": abs(
            transformed_energy - energy
        ),
        "active_rigid_force_max_absolute_error": float(
            np.max(np.abs(transformed_force - force @ rotation.T))
        ),
        "transverse_rigid_metric_max_absolute_error": float(
            np.max(np.abs(transformed_transverse - transverse))
        ),
        "active_loading_input_power": active_input_power(loading_state),
        "active_loading_input_power_positive": (
            active_input_power(loading_state) > 0.0
        ),
        "vectorized_hinge_angle_max_absolute_error": float(
            np.max(np.abs(vector_angles - scalar_angles))
        ),
        "vectorized_hinge_gradient_max_absolute_error": float(
            np.max(np.abs(vector_gradients - scalar_gradients))
        ),
        "active_state_power_sample": active_input_power(state),
    }
    payload = _canonical_json_bytes(metrics)
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_bytes(payload)
    print(
        json.dumps(
            {
                "output": str(OUTPUT_PATH.relative_to(REPOSITORY_ROOT)),
                "sha256": hashlib.sha256(payload).hexdigest().upper(),
                "metrics": metrics,
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
