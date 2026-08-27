"""Independent small-amplitude benchmarks for EFE Node 1 N1-1."""

from __future__ import annotations

from dataclasses import dataclass
import math

import numpy as np
from numpy.typing import NDArray


ComplexArray = NDArray[np.complex128]
FloatArray = NDArray[np.float64]


@dataclass(frozen=True)
class PeriodicSLSPowerLedger:
    time: FloatArray
    strain: FloatArray
    internal: FloatArray
    stress: FloatArray
    stored_energy: FloatArray
    input_power: FloatArray
    dissipation: FloatArray
    energy_change: float
    integrated_input: float
    integrated_dissipation: float
    normalized_residual: float


def sls_complex_modulus(
    equilibrium_modulus: float,
    viscoelastic_modulus: float,
    relaxation_time: float,
    angular_frequency: float,
) -> complex:
    """Return the standard-linear-solid complex shear modulus."""
    if min(
        equilibrium_modulus,
        viscoelastic_modulus,
        relaxation_time,
        angular_frequency,
    ) < 0.0:
        raise ValueError("SLS parameters must be nonnegative")
    de = angular_frequency * relaxation_time
    return complex(
        equilibrium_modulus
        + viscoelastic_modulus * de * de / (1.0 + de * de),
        viscoelastic_modulus * de / (1.0 + de * de),
    )


def solve_two_boundary_port(
    myocyte_stiffness: complex,
    endocardial_stiffness: complex,
    jelly_stiffness: complex,
    myocyte_input: complex,
    endocardial_force: complex,
) -> ComplexArray:
    """Solve the registered two-boundary transfer matrix."""
    matrix = np.asarray(
        [
            [
                myocyte_stiffness + jelly_stiffness,
                -jelly_stiffness,
            ],
            [
                -jelly_stiffness,
                endocardial_stiffness + jelly_stiffness,
            ],
        ],
        dtype=np.complex128,
    )
    forcing = np.asarray(
        [
            myocyte_stiffness * myocyte_input,
            endocardial_force,
        ],
        dtype=np.complex128,
    )
    return np.linalg.solve(matrix, forcing)


def explicit_normal_port_response(
    myocyte_stiffness: complex,
    endocardial_stiffness: complex,
    jelly_stiffness: complex,
    myocyte_input: complex,
    pressure_force: complex,
) -> ComplexArray:
    """Closed-form response registered in N1-R section 4."""
    determinant = (
        (myocyte_stiffness + jelly_stiffness)
        * (endocardial_stiffness + jelly_stiffness)
        - jelly_stiffness * jelly_stiffness
    )
    myocyte = (
        myocyte_stiffness
        * (endocardial_stiffness + jelly_stiffness)
        * myocyte_input
        + jelly_stiffness * pressure_force
    ) / determinant
    endocardium = (
        myocyte_stiffness * jelly_stiffness * myocyte_input
        + (myocyte_stiffness + jelly_stiffness) * pressure_force
    ) / determinant
    return np.asarray([myocyte, endocardium], dtype=np.complex128)


def explicit_tangential_port_response(
    myocyte_stiffness: complex,
    endocardial_stiffness: complex,
    jelly_stiffness: complex,
    shear_force: complex,
) -> ComplexArray:
    """Closed-form WSS response registered in N1-R section 5."""
    determinant = (
        (myocyte_stiffness + jelly_stiffness)
        * (endocardial_stiffness + jelly_stiffness)
        - jelly_stiffness * jelly_stiffness
    )
    return np.asarray(
        [
            jelly_stiffness * shear_force / determinant,
            (myocyte_stiffness + jelly_stiffness)
            * shear_force
            / determinant,
        ],
        dtype=np.complex128,
    )


def periodic_sls_state(
    time: FloatArray,
    *,
    amplitude: float,
    angular_frequency: float,
    relaxation_time: float,
) -> tuple[FloatArray, FloatArray, FloatArray, FloatArray]:
    """Exact periodic strain/internal-variable state of a scalar SLS branch."""
    phase = angular_frequency * time
    de = angular_frequency * relaxation_time
    denominator = 1.0 + de * de
    strain = amplitude * np.sin(phase)
    strain_rate = amplitude * angular_frequency * np.cos(phase)
    internal = amplitude / denominator * (
        np.sin(phase) - de * np.cos(phase)
    )
    internal_rate = amplitude * angular_frequency / denominator * (
        np.cos(phase) + de * np.sin(phase)
    )
    return strain, internal, strain_rate, internal_rate


def periodic_sls_power_ledger(
    *,
    equilibrium_modulus: float,
    viscoelastic_modulus: float,
    relaxation_time: float,
    amplitude: float,
    angular_frequency: float,
    sample_count: int = 2049,
) -> PeriodicSLSPowerLedger:
    """Evaluate one exact steady SLS cycle with the frozen power convention."""
    if sample_count < 3:
        raise ValueError("periodic ledger needs at least three samples")
    period = 2.0 * math.pi / angular_frequency
    time = np.linspace(0.0, period, sample_count)
    strain, internal, strain_rate, internal_rate = periodic_sls_state(
        time,
        amplitude=amplitude,
        angular_frequency=angular_frequency,
        relaxation_time=relaxation_time,
    )
    branch_strain = strain - internal
    stress = (
        equilibrium_modulus * strain
        + viscoelastic_modulus * branch_strain
    )
    stored_energy = (
        0.5 * equilibrium_modulus * strain * strain
        + 0.5 * viscoelastic_modulus * branch_strain * branch_strain
    )
    input_power = stress * strain_rate
    viscosity = 0.5 * viscoelastic_modulus * relaxation_time
    dissipation = 2.0 * viscosity * internal_rate * internal_rate
    energy_change = float(stored_energy[-1] - stored_energy[0])
    integrated_input = float(np.trapezoid(input_power, time))
    integrated_dissipation = float(np.trapezoid(dissipation, time))
    residual = abs(
        energy_change + integrated_dissipation - integrated_input
    )
    denominator = max(
        1.0e-16,
        abs(energy_change)
        + integrated_dissipation
        + float(np.trapezoid(np.abs(input_power), time)),
    )
    return PeriodicSLSPowerLedger(
        time=time,
        strain=strain,
        internal=internal,
        stress=stress,
        stored_energy=stored_energy,
        input_power=input_power,
        dissipation=dissipation,
        energy_change=energy_change,
        integrated_input=integrated_input,
        integrated_dissipation=integrated_dissipation,
        normalized_residual=residual / denominator,
    )
