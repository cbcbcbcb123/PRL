from __future__ import annotations

import numpy as np

from route_h.distributed_active_cell import (
    build_surface_fiber_reference,
    distributed_fiber_energy_gradient,
    run_distributed_active_cycle,
)
from route_h.stage2_gate_a import _build_reference


def test_distributed_fiber_gradient_matches_centered_difference() -> None:
    reference = _build_reference()
    fibers = build_surface_fiber_reference(
        reference.vertices,
        reference.faces,
    )
    rng = np.random.default_rng(20260810)
    vertices = reference.vertices + 1.0e-3 * rng.normal(
        size=reference.vertices.shape
    )
    direction = rng.normal(size=vertices.shape)
    direction /= np.linalg.norm(direction)
    evaluation = distributed_fiber_energy_gradient(
        vertices,
        fibers,
        activation=0.15,
        stiffness=7.0,
    )
    epsilon = 1.0e-6
    plus = distributed_fiber_energy_gradient(
        vertices + epsilon * direction,
        fibers,
        activation=0.15,
        stiffness=7.0,
    ).energy
    minus = distributed_fiber_energy_gradient(
        vertices - epsilon * direction,
        fibers,
        activation=0.15,
        stiffness=7.0,
    ).energy
    finite_difference = (plus - minus) / (2.0 * epsilon)
    analytic = float(np.sum(evaluation.gradient * direction))
    assert np.isclose(analytic, finite_difference, rtol=2.0e-6, atol=2.0e-8)

    plus_activation = distributed_fiber_energy_gradient(
        vertices,
        fibers,
        activation=0.15 + epsilon,
        stiffness=7.0,
    ).energy
    minus_activation = distributed_fiber_energy_gradient(
        vertices,
        fibers,
        activation=0.15 - epsilon,
        stiffness=7.0,
    ).energy
    activation_difference = (
        plus_activation - minus_activation
    ) / (2.0 * epsilon)
    assert np.isclose(
        evaluation.activation_derivative,
        activation_difference,
        rtol=2.0e-6,
        atol=2.0e-8,
    )


def test_distributed_fiber_is_objective_and_stress_free_at_rest() -> None:
    reference = _build_reference()
    fibers = build_surface_fiber_reference(
        reference.vertices,
        reference.faces,
    )
    rest = distributed_fiber_energy_gradient(
        reference.vertices,
        fibers,
        activation=0.0,
        stiffness=10.0,
    )
    assert rest.energy == 0.0
    assert np.linalg.norm(rest.gradient) == 0.0

    active = distributed_fiber_energy_gradient(
        reference.vertices,
        fibers,
        activation=0.1,
        stiffness=10.0,
    )
    assert np.linalg.norm(active.net_force) < 1.0e-12
    assert np.linalg.norm(active.net_moment) < 1.0e-12
    assert np.min(active.preferred_length_ratios) >= 0.9
    assert np.max(active.preferred_length_ratios) <= 1.0


def test_small_distributed_activation_shortens_cell_at_exact_volume() -> None:
    cycle = run_distributed_active_cycle(
        peak_activation=0.02,
        loading_steps=1,
        unloading_steps=0,
        fiber_stiffness=10.0,
    )
    final = cycle.samples[-1]
    assert cycle.status == "completed"
    assert final.measured_anchor_shortening > 0.0
    assert abs(final.volume_ratio - 1.0) < 1.0e-8
    assert final.kkt_residual < 1.0e-5
    assert final.geometry.flipped_face_count == 0
