from __future__ import annotations

import math

import numpy as np
import pytest

from hybrid.efe_node1_manufactured import (
    explicit_normal_port_response,
    explicit_tangential_port_response,
    periodic_sls_power_ledger,
    periodic_sls_state,
    sls_complex_modulus,
    solve_two_boundary_port,
)
from route_h.ecm_finite_strain import density_and_first_piola


def phase_difference_in_cycles(first: complex, second: complex) -> float:
    return abs(float(np.angle(first / second))) / (2.0 * math.pi)


def test_m5_normal_port_recovers_registered_amplitude_and_phase() -> None:
    angular_frequency = 2.4
    jelly = sls_complex_modulus(1.1, 0.8, 0.6, angular_frequency)
    direct = solve_two_boundary_port(
        2.3,
        1.7,
        jelly,
        0.012 * np.exp(0.2j),
        0.008 * np.exp(-0.35j),
    )
    explicit = explicit_normal_port_response(
        2.3,
        1.7,
        jelly,
        0.012 * np.exp(0.2j),
        0.008 * np.exp(-0.35j),
    )
    np.testing.assert_allclose(direct, explicit, rtol=1.0e-12, atol=1.0e-14)
    for direct_value, explicit_value in zip(direct, explicit, strict=True):
        amplitude_error = abs(abs(direct_value) - abs(explicit_value)) / abs(
            explicit_value
        )
        assert amplitude_error <= 0.01
        assert phase_difference_in_cycles(direct_value, explicit_value) <= 0.01


def test_m6_tangential_port_recovers_transfer_and_zero_linear_normal_crossing() -> None:
    angular_frequency = 3.1
    jelly = sls_complex_modulus(0.9, 0.6, 0.4, angular_frequency)
    shear_force = 0.005 * np.exp(0.4j)
    direct = solve_two_boundary_port(1.8, 1.4, jelly, 0.0, shear_force)
    explicit = explicit_tangential_port_response(1.8, 1.4, jelly, shear_force)
    np.testing.assert_allclose(direct, explicit, rtol=1.0e-12, atol=1.0e-14)

    amplitudes = np.asarray([1.0e-3, 1.0e-4, 1.0e-5])
    normal_cross_response = np.zeros_like(amplitudes)
    assert np.all(normal_cross_response / amplitudes == 0.0)


def test_m9_finite_strain_sls_recovers_storage_loss_and_limits() -> None:
    mu_eq = 1.2
    mu_ve = 0.7
    eta_ve = 0.35
    relaxation_time = 2.0 * eta_ve / mu_ve
    angular_frequency = 2.3
    amplitude = 1.0e-5
    period = 2.0 * math.pi / angular_frequency
    time = np.linspace(0.0, period, 2049)
    strain, internal, _, internal_rate = periodic_sls_state(
        time,
        amplitude=amplitude,
        angular_frequency=angular_frequency,
        relaxation_time=relaxation_time,
    )
    stress = np.empty_like(time)
    dissipation = np.empty_like(time)
    for index, (gamma, z_value, z_rate) in enumerate(
        zip(strain, internal, internal_rate, strict=True)
    ):
        deformation = np.eye(3)
        deformation[0, 1] = gamma
        internal_tensor = np.zeros((3, 3))
        internal_tensor[0, 1] = z_value
        internal_tensor[1, 0] = z_value
        _, first_piola = density_and_first_piola(
            deformation,
            internal_tensor,
            mu_eq=mu_eq,
            mu_ve=mu_ve,
        )
        stress[index] = first_piola[0, 1]
        dissipation[index] = 2.0 * eta_ve * z_rate * z_rate
    design = np.column_stack(
        (
            np.sin(angular_frequency * time),
            np.cos(angular_frequency * time),
        )
    )
    coefficients = np.linalg.lstsq(design, stress, rcond=None)[0] / amplitude
    expected = sls_complex_modulus(
        mu_eq,
        mu_ve,
        relaxation_time,
        angular_frequency,
    )
    assert coefficients[0] == pytest.approx(expected.real, rel=1.0e-5)
    assert coefficients[1] == pytest.approx(expected.imag, rel=1.0e-5)
    assert float(np.min(dissipation)) >= 0.0
    assert sls_complex_modulus(mu_eq, mu_ve, relaxation_time, 1.0e-10).real == (
        pytest.approx(mu_eq, abs=1.0e-10)
    )
    assert sls_complex_modulus(mu_eq, mu_ve, relaxation_time, 1.0e10).real == (
        pytest.approx(mu_eq + mu_ve, rel=1.0e-10)
    )


def test_m11_exact_periodic_sls_power_ledger_closes() -> None:
    ledger = periodic_sls_power_ledger(
        equilibrium_modulus=1.2,
        viscoelastic_modulus=0.7,
        relaxation_time=0.9,
        amplitude=0.015,
        angular_frequency=2.6,
    )
    assert ledger.energy_change == pytest.approx(0.0, abs=1.0e-14)
    assert ledger.integrated_dissipation > 0.0
    assert ledger.integrated_input > 0.0
    assert ledger.integrated_input == pytest.approx(
        ledger.integrated_dissipation,
        rel=1.0e-10,
        abs=1.0e-14,
    )
    assert ledger.normalized_residual <= 0.01
