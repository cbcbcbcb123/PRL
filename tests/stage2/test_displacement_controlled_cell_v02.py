"""Verification for global-area, quality-regularized displacement loading."""

from __future__ import annotations

import numpy as np
import pytest

from route_h.displacement_controlled_cell_v02 import (
    _triangle_angles_and_gradients,
    global_area_energy_gradient,
    mesh_quality_energy_gradient,
    run_displacement_equilibrium_v02,
)
from route_h.geometry import triangle_geometry
from route_h.stage2_gate_a import _build_reference


def _directional_derivative_check(
    energy_function,
    vertices: np.ndarray,
    gradient: np.ndarray,
) -> None:
    rng = np.random.default_rng(4107)
    direction = rng.normal(size=vertices.shape)
    direction /= np.linalg.norm(direction)
    epsilon = 1.0e-7
    plus = energy_function(vertices + epsilon * direction)
    minus = energy_function(vertices - epsilon * direction)
    finite_difference = (plus - minus) / (2.0 * epsilon)
    analytic = float(np.sum(gradient * direction))
    assert finite_difference == pytest.approx(
        analytic,
        rel=2.0e-6,
        abs=2.0e-8,
    )


def test_global_area_energy_gradient_matches_finite_difference() -> None:
    reference = _build_reference()
    vertices = reference.vertices.copy()
    vertices[:, 0] *= 0.97
    energy, gradient, _ = global_area_energy_gradient(
        vertices,
        reference.faces,
        float(reference.cell.area0.sum()),
        0.2,
    )
    assert energy > 0.0
    _directional_derivative_check(
        lambda current: global_area_energy_gradient(
            current,
            reference.faces,
            float(reference.cell.area0.sum()),
            0.2,
        )[0],
        vertices,
        gradient,
    )


def test_mesh_quality_energy_is_scale_invariant_and_has_valid_gradient() -> None:
    reference = _build_reference()
    reference_areas, _ = triangle_geometry(
        reference.vertices,
        reference.faces,
    )
    reference_angles, _ = _triangle_angles_and_gradients(
        reference.vertices[reference.faces]
    )
    uniform = 1.3 * reference.vertices
    energy, gradient = mesh_quality_energy_gradient(
        uniform,
        reference.faces,
        reference_angles,
        reference_areas,
        0.05,
    )
    assert energy == pytest.approx(0.0, abs=1.0e-26)
    assert np.linalg.norm(gradient) < 1.0e-13

    vertices = uniform.copy()
    vertices[7] += np.array([0.01, -0.006, 0.004])
    energy, gradient = mesh_quality_energy_gradient(
        vertices,
        reference.faces,
        reference_angles,
        reference_areas,
        0.05,
    )
    assert energy > 0.0
    _directional_derivative_check(
        lambda current: mesh_quality_energy_gradient(
            current,
            reference.faces,
            reference_angles,
            reference_areas,
            0.05,
        )[0],
        vertices,
        gradient,
    )


def test_small_displacement_equilibrium_preserves_volume_and_mesh() -> None:
    run = run_displacement_equilibrium_v02(
        target_shortening=0.02,
        step_count=1,
        global_area_stiffness=0.1,
        mesh_quality_stiffness=0.05,
    )
    final = run.samples[-1]
    assert run.status == "completed"
    assert final.measured_anchor_shortening == pytest.approx(
        0.02,
        abs=1.0e-12,
    )
    assert final.volume_ratio == pytest.approx(1.0, abs=1.0e-8)
    assert final.geometry.minimum_face_area_ratio >= 0.05
    assert final.geometry.flipped_face_count == 0
    assert final.kkt_residual <= 1.0e-5
