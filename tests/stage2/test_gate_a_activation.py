from __future__ import annotations

import math

import numpy as np
import pytest

from route_h.activation import (
    active_energy_force,
    active_input_power,
    activation_protocol,
    base_envelope,
    build_active_reference,
    transverse_scale_changes,
)
from route_h.discretization import load_discretization_level
from route_h.solver import run_gate_a_trajectory


def _reference_data():
    arrays, _ = load_discretization_level("base")
    cell_id = 6
    counts = arrays["cell_anchor_counts"][cell_id]
    vertices = arrays["cell_vertices"][cell_id]
    faces = arrays["cell_faces"][cell_id]
    reference = build_active_reference(
        vertices,
        faces,
        arrays["cell_anchor_minus_face_ids"][cell_id, : int(counts[0])],
        arrays["cell_anchor_plus_face_ids"][cell_id, : int(counts[1])],
    )
    return arrays, vertices, faces, reference


def test_frozen_activation_envelope_nodes_and_rates():
    expected = {
        0.0: (0.0, 0.0),
        1.0: (0.0, 0.0),
        1.5: (0.5, 0.5 * math.pi),
        2.0: (1.0, 0.0),
        2.5: (1.0, 0.0),
        3.0: (1.0, 0.0),
        3.5: (0.5, -0.5 * math.pi),
        4.0: (0.0, 0.0),
        5.0: (0.0, 0.0),
    }
    for time, target in expected.items():
        assert base_envelope(time) == pytest.approx(target, abs=1.0e-15)
    assert activation_protocol(2.5, alpha_peak=0.1) == pytest.approx(
        (0.1, 0.0)
    )


def test_active_force_matches_directional_derivative_and_internal_balance():
    _, vertices, _, reference = _reference_data()
    rng = np.random.default_rng(20260731)
    current = vertices + 2.0e-3 * rng.standard_normal(vertices.shape)
    direction = rng.standard_normal(vertices.shape)
    direction /= np.linalg.norm(direction)
    alpha = 0.07
    energy, force, _ = active_energy_force(
        current,
        reference,
        alpha=alpha,
    )
    step = 1.0e-7
    plus = active_energy_force(
        current + step * direction,
        reference,
        alpha=alpha,
    )[0]
    minus = active_energy_force(
        current - step * direction,
        reference,
        alpha=alpha,
    )[0]
    finite_difference = (plus - minus) / (2.0 * step)
    analytic = -float(np.sum(force * direction))
    assert energy > 0.0
    assert finite_difference == pytest.approx(
        analytic,
        rel=1.0e-7,
        abs=1.0e-10,
    )
    assert np.linalg.norm(force.sum(axis=0)) < 1.0e-14
    centroid = np.mean(current, axis=0)
    moment = np.cross(current - centroid, force).sum(axis=0)
    assert np.linalg.norm(moment) < 1.0e-14


def test_active_energy_force_and_transverse_metrics_are_rigid_objective():
    arrays, vertices, faces, reference = _reference_data()
    current = vertices.copy()
    current[:, 0] *= 0.97
    angle = 0.37
    rotation = np.asarray(
        [
            [math.cos(angle), -math.sin(angle), 0.0],
            [math.sin(angle), math.cos(angle), 0.0],
            [0.0, 0.0, 1.0],
        ]
    )
    translation = np.asarray([0.7, -0.4, 0.2])
    transformed_reference_vertices = vertices @ rotation.T + translation
    transformed_current = current @ rotation.T + translation
    counts = arrays["cell_anchor_counts"][6]
    transformed_reference = build_active_reference(
        transformed_reference_vertices,
        faces,
        arrays["cell_anchor_minus_face_ids"][6, : int(counts[0])],
        arrays["cell_anchor_plus_face_ids"][6, : int(counts[1])],
    )
    energy, force, _ = active_energy_force(current, reference, alpha=0.08)
    transformed_energy, transformed_force, _ = active_energy_force(
        transformed_current,
        transformed_reference,
        alpha=0.08,
    )
    weights = arrays["cell_gauge_dual_area_weights"][6]
    metric = transverse_scale_changes(current, reference, weights)
    transformed_metric = transverse_scale_changes(
        transformed_current,
        transformed_reference,
        weights,
    )
    assert transformed_energy == pytest.approx(energy, abs=1.0e-14)
    assert np.allclose(
        transformed_force,
        force @ rotation.T,
        rtol=0.0,
        atol=1.0e-14,
    )
    assert np.allclose(transformed_metric, metric, rtol=0.0, atol=1.0e-14)


def test_active_input_power_has_frozen_positive_loading_sign():
    _, vertices, _, reference = _reference_data()
    alpha, alpha_rate = activation_protocol(1.5, alpha_peak=0.1)
    _, _, state = active_energy_force(
        vertices,
        reference,
        alpha=alpha,
        alpha_rate=alpha_rate,
    )
    assert state.preferred_length_rate < 0.0
    assert active_input_power(state) > 0.0


def test_a0_one_step_preserves_reference_exactly():
    trajectory = run_gate_a_trajectory(
        "A0_ZERO",
        dt=0.02,
        duration=0.02,
    )
    assert np.array_equal(trajectory.vertices[0], trajectory.vertices[1])
    assert np.max(np.abs(trajectory.stored_energy)) < 1.0e-30
    assert np.all(trajectory.dissipation == 0.0)
