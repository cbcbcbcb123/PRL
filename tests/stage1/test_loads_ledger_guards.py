from __future__ import annotations

import numpy as np
import pytest

from route_h.contracts import require_passive_stage1
from route_h.coupling import zero_myocardial_source_assembly
from route_h.gauge import gauge_rate_and_power, project_zero_gauge_rate
from route_h.ledger import MechanicalLedger, integrated_power_residual
from route_h.loads import (
    blood_nodal_force,
    flow_sensor_rate,
    force_power,
    kelvin_voigt_support,
    support_weights,
)
from route_h.solver import evaluate_passive_reference


def test_pressure_normal_wss_tangential_and_force_power_identity(bundle):
    arrays, _ = bundle
    cell_id = 0
    vertices = arrays["cell_vertices"][cell_id]
    faces = arrays["cell_faces"][cell_id]
    apical = np.flatnonzero(arrays["cell_primary_identity"][cell_id] == 1)
    pressure, wss = blood_nodal_force(
        vertices, faces, apical,
        pressure=0.05, wss_command=np.array([0.02, 0.0, 0.0]),
    )
    pressure_resultant = pressure.sum(axis=0)
    wss_resultant = wss.sum(axis=0)
    assert np.linalg.norm(pressure_resultant[:2]) / np.linalg.norm(pressure_resultant) < 1e-10
    assert abs(wss_resultant[2]) / np.linalg.norm(wss_resultant) < 1e-10
    velocity = np.random.default_rng(5).standard_normal(vertices.shape)
    assert force_power(pressure, velocity) == pytest.approx(float(np.sum(pressure * velocity)))
    assert force_power(wss, velocity) == pytest.approx(float(np.sum(wss * velocity)))


def test_fixed_support_energy_force_derivative_and_dissipation(bundle):
    arrays, _ = bundle
    cell_id = 6
    reference = arrays["cell_vertices"][cell_id]
    faces = arrays["cell_faces"][cell_id]
    opposite = np.flatnonzero(arrays["cell_primary_identity"][cell_id] == 3)
    weights = support_weights(reference, faces, opposite)
    state = reference + np.array([0.01, -0.02, 0.03])
    velocity = np.random.default_rng(2).standard_normal(state.shape) * 0.01
    stiffness = np.diag([0.25, 0.25, 1.0])
    damping = stiffness.copy()
    energy, force, dissipation = kelvin_voigt_support(
        state, velocity, reference, weights, stiffness, damping
    )
    elastic_force = kelvin_voigt_support(
        state, np.zeros_like(velocity), reference, weights, stiffness, damping
    )[1]
    direction = np.random.default_rng(3).standard_normal(state.shape)
    step = 1e-7
    plus = kelvin_voigt_support(
        state + step * direction, np.zeros_like(velocity), reference,
        weights, stiffness, damping,
    )[0]
    minus = kelvin_voigt_support(
        state - step * direction, np.zeros_like(velocity), reference,
        weights, stiffness, damping,
    )[0]
    assert abs((plus - minus) / (2 * step) + np.sum(elastic_force * direction)) < 1e-7
    assert energy > 0.0
    assert dissipation >= 0.0
    assert np.isfinite(force).all()


def test_zero_source_mapping_is_exact_and_nonzero_is_forbidden(bundle):
    arrays, _ = bundle
    source, power = zero_myocardial_source_assembly(
        arrays["myocardial_source_map_integer"],
        arrays["myocardial_source_map_float"],
        len(arrays["ecm_tetrahedra"]),
    )
    assert np.count_nonzero(source) == 0
    assert power == 0.0
    with pytest.raises(PermissionError, match="Nonzero j_myo"):
        zero_myocardial_source_assembly(
            arrays["myocardial_source_map_integer"],
            arrays["myocardial_source_map_float"],
            len(arrays["ecm_tetrahedra"]),
            j_myo=1e-3,
        )


def test_global_gauge_has_zero_rate_and_power(bundle):
    arrays, _ = bundle
    reference = arrays["cell_vertices"][6]
    weights = arrays["cell_gauge_dual_area_weights"][6]
    velocity = np.random.default_rng(7).standard_normal(reference.shape)
    projected = project_zero_gauge_rate(velocity, reference, weights)
    rate, power = gauge_rate_and_power(
        projected, reference, weights, np.arange(1.0, 7.0)
    )
    assert np.linalg.norm(rate) < 1e-12
    assert abs(power) < 1e-12


def test_ledger_nonnegative_dissipation_and_integrated_closure():
    ledger = MechanicalLedger()
    ledger.add_stored("support", 0.5)
    ledger.add_dissipation("support", 0.2)
    ledger.add_external_power("pressure", 0.7)
    assert ledger.total_stored == 0.5
    assert ledger.total_dissipation == 0.2
    assert ledger.total_external_power == 0.7
    with pytest.raises(ValueError, match="negative dissipation"):
        ledger.add_dissipation("bad", -1e-4)
    time = np.array([0.0, 0.5, 1.0])
    energy = np.array([0.0, 0.25, 0.5])
    dissipation = np.array([0.2, 0.2, 0.2])
    power = np.array([0.7, 0.7, 0.7])
    assert integrated_power_residual(time, energy, dissipation, power) < 1e-15


def test_flow_sensor_has_no_mechanical_output():
    rate = flow_sensor_rate(0.1, np.array([0.02, 0.0, 0.0]))
    assert isinstance(rate, float)
    assert rate != 0.0


def test_active_full_patch_and_stage2_paths_are_blocked():
    require_passive_stage1()
    with pytest.raises(PermissionError, match="Active contraction"):
        require_passive_stage1(active=True)
    with pytest.raises(PermissionError, match="Full-patch"):
        require_passive_stage1(full_patch_trajectory=True)
    with pytest.raises(PermissionError):
        evaluate_passive_reference(active=True)
    with pytest.raises(PermissionError):
        evaluate_passive_reference(full_patch_trajectory=True)
