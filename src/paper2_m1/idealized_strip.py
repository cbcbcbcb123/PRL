"""Power-consistent quasi-2D strip for Paper 2 M1.

The model deliberately keeps geometry and constitutive laws small.  A
cell-discrete endocardial chain is coupled to a P1 standard-linear-solid ECM
strip and a P1 active-eigenstrain myocardial strip.  Each node carries a
tangential and a normal displacement, so normal pressure and tangential shear
remain separate mechanical ports.  All parameters are nondimensional in M1.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
import math
from typing import Any

import numpy as np
from numpy.typing import NDArray


FloatArray = NDArray[np.float64]


@dataclass(frozen=True)
class StripConfig:
    node_count: int = 9
    length: float = 1.0
    period: float = 1.0
    cycles: int = 4
    steps_per_cycle: int = 128
    endocardial_connection_stiffness: tuple[float, float] = (0.8, 0.25)
    ecm_equilibrium_modulus: tuple[float, float] = (1.0, 1.2)
    ecm_maxwell_modulus: tuple[float, float] = (0.7, 0.9)
    ecm_relaxation_time: tuple[float, float] = (0.22, 0.30)
    myocardial_modulus: tuple[float, float] = (2.5, 0.8)
    endocardium_ecm_interface_stiffness: tuple[float, float] = (7.0, 8.0)
    ecm_myocardium_interface_stiffness: tuple[float, float] = (8.0, 9.0)
    support_stiffness: tuple[float, float] = (0.45, 0.60)
    endocardial_drag: tuple[float, float] = (0.10, 0.10)
    ecm_drag: tuple[float, float] = (0.05, 0.05)
    myocardial_drag: tuple[float, float] = (0.12, 0.12)

    def checked(self) -> "StripConfig":
        if self.node_count < 3:
            raise ValueError("node_count must be at least three")
        if self.length <= 0.0 or self.period <= 0.0:
            raise ValueError("length and period must be positive")
        if self.cycles < 1 or self.steps_per_cycle < 4:
            raise ValueError("cycles and steps_per_cycle are too small")
        positive_fields = (
            self.endocardial_connection_stiffness,
            self.ecm_equilibrium_modulus,
            self.ecm_maxwell_modulus,
            self.ecm_relaxation_time,
            self.myocardial_modulus,
            self.endocardium_ecm_interface_stiffness,
            self.ecm_myocardium_interface_stiffness,
            self.support_stiffness,
            self.endocardial_drag,
            self.ecm_drag,
            self.myocardial_drag,
        )
        values = np.asarray(positive_fields, dtype=np.float64)
        if values.shape != (11, 2) or not np.all(np.isfinite(values)):
            raise ValueError("all material pairs must be finite two-vectors")
        if np.any(values <= 0.0):
            raise ValueError("all M1 material and drag values must be positive")
        return self


@dataclass(frozen=True)
class DriveProtocol:
    activation_peak: float = 0.0
    pressure_peak: float = 0.0
    shear_amplitude: float = 0.0
    external_tangential_amplitude: float = 0.0
    external_normal_peak: float = 0.0

    def checked(self) -> "DriveProtocol":
        values = np.asarray(
            (
                self.activation_peak,
                self.pressure_peak,
                self.shear_amplitude,
                self.external_tangential_amplitude,
                self.external_normal_peak,
            ),
            dtype=np.float64,
        )
        if not np.all(np.isfinite(values)):
            raise ValueError("drive amplitudes must be finite")
        if self.activation_peak < 0.0 or self.activation_peak >= 1.0:
            raise ValueError("activation_peak must lie in [0,1)")
        if self.pressure_peak < 0.0 or self.external_normal_peak < 0.0:
            raise ValueError("normal pressure peaks must be nonnegative")
        return self


@dataclass(frozen=True)
class StripSystem:
    config: StripConfig
    matrix_a: FloatArray
    matrix_g: FloatArray
    active_vector_h: FloatArray
    active_scalar_c: float
    node_weights: FloatArray
    element_length: float
    endocardium_slice: slice
    ecm_slice: slice
    myocardium_slice: slice
    internal_z_slice: slice

    @property
    def state_size(self) -> int:
        return int(self.matrix_a.shape[0])

    def layer_view(self, state: FloatArray, layer: str) -> FloatArray:
        selected = {
            "endocardium": self.endocardium_slice,
            "ecm": self.ecm_slice,
            "myocardium": self.myocardium_slice,
        }.get(layer)
        if selected is None:
            raise ValueError(f"unknown layer {layer!r}")
        return np.asarray(state[selected], dtype=np.float64).reshape(
            self.config.node_count, 2
        )

    def internal_z_view(self, state: FloatArray) -> FloatArray:
        return np.asarray(state[self.internal_z_slice], dtype=np.float64).reshape(
            self.config.node_count - 1, 2
        )


@dataclass(frozen=True)
class SimulationResult:
    case_name: str
    config: StripConfig
    drive: DriveProtocol
    arrays: dict[str, FloatArray]
    summary: dict[str, Any]


def _pair(value: tuple[float, float]) -> FloatArray:
    return np.asarray(value, dtype=np.float64)


def _node_index(layer_start: int, node: int, component: int) -> int:
    return layer_start + 2 * node + component


def _add_two_node_energy(
    matrix: FloatArray,
    first: int,
    second: int,
    coefficient: float,
) -> None:
    matrix[first, first] += coefficient
    matrix[second, second] += coefficient
    matrix[first, second] -= coefficient
    matrix[second, first] -= coefficient


def assemble_strip_system(config: StripConfig | None = None) -> StripSystem:
    """Assemble the linear-gradient system used by the implicit midpoint step."""
    selected = StripConfig() if config is None else config
    selected = selected.checked()
    node_count = selected.node_count
    element_count = node_count - 1
    element_length = selected.length / element_count
    layer_size = 2 * node_count
    endocardium_start = 0
    ecm_start = layer_size
    myocardium_start = 2 * layer_size
    internal_z_start = 3 * layer_size
    state_size = internal_z_start + 2 * element_count
    endocardium_slice = slice(endocardium_start, ecm_start)
    ecm_slice = slice(ecm_start, myocardium_start)
    myocardium_slice = slice(myocardium_start, internal_z_start)
    internal_z_slice = slice(internal_z_start, state_size)

    node_weights = np.full(node_count, element_length, dtype=np.float64)
    node_weights[[0, -1]] *= 0.5
    matrix_a = np.zeros((state_size, state_size), dtype=np.float64)
    matrix_g = np.zeros((state_size, state_size), dtype=np.float64)
    active_vector_h = np.zeros(state_size, dtype=np.float64)
    active_scalar_c = 0.0

    endocardial_stiffness = _pair(selected.endocardial_connection_stiffness)
    ecm_equilibrium = _pair(selected.ecm_equilibrium_modulus)
    ecm_maxwell = _pair(selected.ecm_maxwell_modulus)
    myocardial_modulus = _pair(selected.myocardial_modulus)

    for element in range(element_count):
        for component in range(2):
            endo_first = _node_index(endocardium_start, element, component)
            endo_second = _node_index(endocardium_start, element + 1, component)
            _add_two_node_energy(
                matrix_a,
                endo_first,
                endo_second,
                endocardial_stiffness[component] / element_length,
            )

            ecm_first = _node_index(ecm_start, element, component)
            ecm_second = _node_index(ecm_start, element + 1, component)
            ecm_coefficient = (
                ecm_equilibrium[component] + ecm_maxwell[component]
            ) / element_length
            _add_two_node_energy(
                matrix_a,
                ecm_first,
                ecm_second,
                ecm_coefficient,
            )
            z_index = internal_z_start + 2 * element + component
            coupling_value = ecm_maxwell[component]
            matrix_a[ecm_first, z_index] += coupling_value
            matrix_a[ecm_second, z_index] -= coupling_value
            matrix_a[z_index, ecm_first] += coupling_value
            matrix_a[z_index, ecm_second] -= coupling_value
            matrix_a[z_index, z_index] += (
                ecm_maxwell[component] * element_length
            )

            myo_first = _node_index(myocardium_start, element, component)
            myo_second = _node_index(myocardium_start, element + 1, component)
            _add_two_node_energy(
                matrix_a,
                myo_first,
                myo_second,
                myocardial_modulus[component] / element_length,
            )
            if component == 0:
                active_vector_h[myo_first] -= myocardial_modulus[0]
                active_vector_h[myo_second] += myocardial_modulus[0]
                active_scalar_c += myocardial_modulus[0] * element_length

    interface_endo_ecm = _pair(
        selected.endocardium_ecm_interface_stiffness
    )
    interface_ecm_myo = _pair(selected.ecm_myocardium_interface_stiffness)
    support_stiffness = _pair(selected.support_stiffness)
    for node, weight in enumerate(node_weights):
        for component in range(2):
            endo_index = _node_index(endocardium_start, node, component)
            ecm_index = _node_index(ecm_start, node, component)
            myo_index = _node_index(myocardium_start, node, component)
            _add_two_node_energy(
                matrix_a,
                endo_index,
                ecm_index,
                interface_endo_ecm[component] * weight,
            )
            _add_two_node_energy(
                matrix_a,
                ecm_index,
                myo_index,
                interface_ecm_myo[component] * weight,
            )
            matrix_a[myo_index, myo_index] += (
                support_stiffness[component] * weight
            )

    layer_drags = (
        _pair(selected.endocardial_drag),
        _pair(selected.ecm_drag),
        _pair(selected.myocardial_drag),
    )
    layer_starts = (endocardium_start, ecm_start, myocardium_start)
    for drag, layer_start in zip(layer_drags, layer_starts, strict=True):
        for node, weight in enumerate(node_weights):
            for component in range(2):
                index = _node_index(layer_start, node, component)
                matrix_g[index, index] = drag[component] * weight

    relaxation_time = _pair(selected.ecm_relaxation_time)
    for element in range(element_count):
        for component in range(2):
            z_index = internal_z_start + 2 * element + component
            matrix_g[z_index, z_index] = (
                ecm_maxwell[component]
                * relaxation_time[component]
                * element_length
            )

    if not np.allclose(matrix_a, matrix_a.T, atol=1.0e-14):
        raise AssertionError("stored-energy matrix is not symmetric")
    if np.min(np.diag(matrix_g)) <= 0.0:
        raise AssertionError("dissipation metric must be positive")
    return StripSystem(
        config=selected,
        matrix_a=matrix_a,
        matrix_g=matrix_g,
        active_vector_h=active_vector_h,
        active_scalar_c=float(active_scalar_c),
        node_weights=node_weights,
        element_length=element_length,
        endocardium_slice=endocardium_slice,
        ecm_slice=ecm_slice,
        myocardium_slice=myocardium_slice,
        internal_z_slice=internal_z_slice,
    )


def _drive_values(
    protocol: DriveProtocol,
    time: float,
    period: float,
) -> dict[str, float]:
    phase = 2.0 * math.pi * time / period
    nonnegative_pulse = 0.5 * (1.0 - math.cos(phase))
    return {
        "activation": protocol.activation_peak * nonnegative_pulse,
        "pressure": protocol.pressure_peak * nonnegative_pulse,
        "shear": protocol.shear_amplitude * math.sin(phase),
        "external_tangential": (
            protocol.external_tangential_amplitude * math.sin(phase)
        ),
        "external_normal": protocol.external_normal_peak * nonnegative_pulse,
    }


def _load_vectors(
    system: StripSystem,
    values: dict[str, float],
) -> tuple[FloatArray, FloatArray]:
    lumen = np.zeros(system.state_size, dtype=np.float64)
    external = np.zeros(system.state_size, dtype=np.float64)
    endocardial = lumen[system.endocardium_slice].reshape(
        system.config.node_count, 2
    )
    myocardial = external[system.myocardium_slice].reshape(
        system.config.node_count, 2
    )
    # n_lum = +e_y and fluid-on-tissue traction is -p*n_lum + tau*e_x.
    endocardial[:, 0] = system.node_weights * values["shear"]
    endocardial[:, 1] = -system.node_weights * values["pressure"]
    myocardial[:, 0] = (
        system.node_weights * values["external_tangential"]
    )
    myocardial[:, 1] = system.node_weights * values["external_normal"]
    return lumen, external


def _energy_components(
    system: StripSystem,
    state: FloatArray,
    activation: float,
) -> dict[str, float]:
    endocardium = system.layer_view(state, "endocardium")
    ecm = system.layer_view(state, "ecm")
    myocardium = system.layer_view(state, "myocardium")
    internal_z = system.internal_z_view(state)
    element_length = system.element_length
    endocardial_strain = np.diff(endocardium, axis=0) / element_length
    ecm_strain = np.diff(ecm, axis=0) / element_length
    myocardial_strain = np.diff(myocardium, axis=0) / element_length
    endocardial_stiffness = _pair(
        system.config.endocardial_connection_stiffness
    )
    ecm_equilibrium = _pair(system.config.ecm_equilibrium_modulus)
    ecm_maxwell = _pair(system.config.ecm_maxwell_modulus)
    myocardial_modulus = _pair(system.config.myocardial_modulus)
    myocardial_mismatch = myocardial_strain.copy()
    myocardial_mismatch[:, 0] += activation
    endo_ecm_difference = endocardium - ecm
    ecm_myo_difference = ecm - myocardium
    return {
        "endocardial_connections": 0.5
        * element_length
        * float(np.sum(endocardial_stiffness * endocardial_strain**2)),
        "ecm_equilibrium": 0.5
        * element_length
        * float(np.sum(ecm_equilibrium * ecm_strain**2)),
        "ecm_viscoelastic": 0.5
        * element_length
        * float(np.sum(ecm_maxwell * (ecm_strain - internal_z) ** 2)),
        "myocardium_active_eigenstrain": 0.5
        * element_length
        * float(np.sum(myocardial_modulus * myocardial_mismatch**2)),
        "interface_endocardium_ecm": 0.5
        * float(
            np.sum(
                system.node_weights[:, None]
                * _pair(system.config.endocardium_ecm_interface_stiffness)
                * endo_ecm_difference**2
            )
        ),
        "interface_ecm_myocardium": 0.5
        * float(
            np.sum(
                system.node_weights[:, None]
                * _pair(system.config.ecm_myocardium_interface_stiffness)
                * ecm_myo_difference**2
            )
        ),
        "external_support": 0.5
        * float(
            np.sum(
                system.node_weights[:, None]
                * _pair(system.config.support_stiffness)
                * myocardium**2
            )
        ),
    }


def _state_observables(
    system: StripSystem,
    state: FloatArray,
) -> dict[str, FloatArray | float]:
    endocardium = system.layer_view(state, "endocardium")
    ecm = system.layer_view(state, "ecm")
    myocardium = system.layer_view(state, "myocardium")
    element_length = system.element_length
    endocardial_connection_force = (
        _pair(system.config.endocardial_connection_stiffness)
        * np.diff(endocardium, axis=0)
        / element_length
    )
    endo_ecm_difference = endocardium - ecm
    ecm_myo_difference = ecm - myocardium
    endo_ecm_stiffness = _pair(
        system.config.endocardium_ecm_interface_stiffness
    )
    ecm_myo_stiffness = _pair(
        system.config.ecm_myocardium_interface_stiffness
    )
    traction_ecm_on_endo = -endo_ecm_stiffness * endo_ecm_difference
    traction_endo_on_ecm = -traction_ecm_on_endo
    traction_myo_on_ecm = -ecm_myo_stiffness * ecm_myo_difference
    traction_ecm_on_myo = -traction_myo_on_ecm
    endocardial_shortening = -float(
        (endocardium[-1, 0] - endocardium[0, 0]) / system.config.length
    )
    ecm_shortening = -float(
        (ecm[-1, 0] - ecm[0, 0]) / system.config.length
    )
    myocardial_shortening = -float(
        (myocardium[-1, 0] - myocardium[0, 0]) / system.config.length
    )
    return {
        "endocardial_connection_force": endocardial_connection_force,
        "traction_ecm_on_endocardium": traction_ecm_on_endo,
        "traction_endocardium_on_ecm": traction_endo_on_ecm,
        "traction_myocardium_on_ecm": traction_myo_on_ecm,
        "traction_ecm_on_myocardium": traction_ecm_on_myo,
        "endocardial_shortening": endocardial_shortening,
        "ecm_shortening": ecm_shortening,
        "myocardial_shortening": myocardial_shortening,
    }


def _dissipation_components(
    system: StripSystem,
    velocity: FloatArray,
) -> dict[str, float]:
    diagonal = np.diag(system.matrix_g)
    endo_power = float(
        np.sum(diagonal[system.endocardium_slice] * velocity[system.endocardium_slice] ** 2)
    )
    ecm_nodal_power = float(
        np.sum(diagonal[system.ecm_slice] * velocity[system.ecm_slice] ** 2)
    )
    z_power = float(
        np.sum(diagonal[system.internal_z_slice] * velocity[system.internal_z_slice] ** 2)
    )
    myo_power = float(
        np.sum(diagonal[system.myocardium_slice] * velocity[system.myocardium_slice] ** 2)
    )
    return {
        "endocardium": endo_power,
        "ecm": ecm_nodal_power + z_power,
        "myocardium": myo_power,
    }


def _harmonic_amplitude_phase(
    time: FloatArray,
    signal: FloatArray,
    period: float,
    steps_per_cycle: int,
) -> dict[str, float]:
    selected_time = np.asarray(time[-(steps_per_cycle + 1) :], dtype=np.float64)
    selected_signal = np.asarray(
        signal[-(steps_per_cycle + 1) :], dtype=np.float64
    )
    omega = 2.0 * math.pi / period
    design = np.column_stack(
        (
            np.ones_like(selected_time),
            np.sin(omega * selected_time),
            np.cos(omega * selected_time),
        )
    )
    coefficients = np.linalg.lstsq(design, selected_signal, rcond=None)[0]
    sine_value = float(coefficients[1])
    cosine_value = float(coefficients[2])
    return {
        "offset": float(coefficients[0]),
        "amplitude": float(math.hypot(sine_value, cosine_value)),
        "phase_rad_relative_to_sine": float(math.atan2(cosine_value, sine_value)),
    }


def _wrapped_phase(value: float) -> float:
    return float((value + math.pi) % (2.0 * math.pi) - math.pi)


def _transfer_metrics(
    system: StripSystem,
    arrays: dict[str, FloatArray],
    drive: DriveProtocol,
) -> dict[str, Any]:
    time = arrays["time"]
    response_signals = {
        "endocardial_shortening": arrays["endocardial_shortening"],
        "ecm_shortening": arrays["ecm_shortening"],
        "myocardial_shortening": arrays["myocardial_shortening"],
        "endocardium_mean_tangential": np.average(
            arrays["endocardium_displacement"][:, :, 0],
            axis=1,
            weights=system.node_weights,
        ),
        "endocardium_mean_normal": np.average(
            arrays["endocardium_displacement"][:, :, 1],
            axis=1,
            weights=system.node_weights,
        ),
        "ecm_mean_tangential": np.average(
            arrays["ecm_displacement"][:, :, 0],
            axis=1,
            weights=system.node_weights,
        ),
        "ecm_mean_normal": np.average(
            arrays["ecm_displacement"][:, :, 1],
            axis=1,
            weights=system.node_weights,
        ),
        "myocardium_mean_tangential": np.average(
            arrays["myocardium_displacement"][:, :, 0],
            axis=1,
            weights=system.node_weights,
        ),
        "myocardium_mean_normal": np.average(
            arrays["myocardium_displacement"][:, :, 1],
            axis=1,
            weights=system.node_weights,
        ),
    }
    drivers = {
        "activation": arrays["activation"],
        "pressure": arrays["pressure"],
        "shear": arrays["shear"],
        "external_tangential": arrays["external_tangential"],
        "external_normal": arrays["external_normal"],
    }
    enabled = {
        "activation": drive.activation_peak != 0.0,
        "pressure": drive.pressure_peak != 0.0,
        "shear": drive.shear_amplitude != 0.0,
        "external_tangential": drive.external_tangential_amplitude != 0.0,
        "external_normal": drive.external_normal_peak != 0.0,
    }
    transfer: dict[str, Any] = {}
    for driver_name, driver_signal in drivers.items():
        if not enabled[driver_name]:
            continue
        driver_harmonic = _harmonic_amplitude_phase(
            time,
            driver_signal,
            system.config.period,
            system.config.steps_per_cycle,
        )
        response_payload: dict[str, Any] = {}
        for response_name, response_signal in response_signals.items():
            response_harmonic = _harmonic_amplitude_phase(
                time,
                response_signal,
                system.config.period,
                system.config.steps_per_cycle,
            )
            input_amplitude = driver_harmonic["amplitude"]
            response_payload[response_name] = {
                **response_harmonic,
                "gain": (
                    response_harmonic["amplitude"] / input_amplitude
                    if input_amplitude > 0.0
                    else float("nan")
                ),
                "phase_lag_rad": _wrapped_phase(
                    response_harmonic["phase_rad_relative_to_sine"]
                    - driver_harmonic["phase_rad_relative_to_sine"]
                ),
            }
        transfer[driver_name] = {
            "input": driver_harmonic,
            "responses": response_payload,
        }
    return transfer


def _json_number(value: np.generic | float | int | bool) -> float | int | bool:
    if isinstance(value, (np.bool_, bool)):
        return bool(value)
    if isinstance(value, (np.integer, int)):
        return int(value)
    return float(value)


def run_case(
    case_name: str,
    *,
    config: StripConfig | None = None,
    drive: DriveProtocol | None = None,
    initial_state: FloatArray | None = None,
) -> SimulationResult:
    """Run one create-new M1 strip case with an implicit midpoint scheme."""
    system = assemble_strip_system(config)
    selected_drive = DriveProtocol() if drive is None else drive
    selected_drive = selected_drive.checked()
    step_count = system.config.cycles * system.config.steps_per_cycle
    time = np.linspace(
        0.0,
        system.config.cycles * system.config.period,
        step_count + 1,
        dtype=np.float64,
    )
    time_step = float(time[1] - time[0])
    state = np.zeros(system.state_size, dtype=np.float64)
    if initial_state is not None:
        candidate = np.asarray(initial_state, dtype=np.float64)
        if candidate.shape != state.shape or not np.all(np.isfinite(candidate)):
            raise ValueError("initial_state has invalid shape or values")
        state[:] = candidate

    states = np.zeros((step_count + 1, system.state_size), dtype=np.float64)
    states[0] = state
    drive_arrays = {
        name: np.zeros(step_count + 1, dtype=np.float64)
        for name in (
            "activation",
            "pressure",
            "shear",
            "external_tangential",
            "external_normal",
        )
    }
    energy_names = tuple(
        _energy_components(system, state, 0.0).keys()
    )
    energy_components = {
        name: np.zeros(step_count + 1, dtype=np.float64)
        for name in energy_names
    }
    stored_energy = np.zeros(step_count + 1, dtype=np.float64)
    displacement_shape = (step_count + 1, system.config.node_count, 2)
    endocardium_displacement = np.zeros(displacement_shape, dtype=np.float64)
    ecm_displacement = np.zeros(displacement_shape, dtype=np.float64)
    myocardium_displacement = np.zeros(displacement_shape, dtype=np.float64)
    internal_z = np.zeros(
        (step_count + 1, system.config.node_count - 1, 2),
        dtype=np.float64,
    )
    connection_force = np.zeros_like(internal_z)
    interface_shape = (step_count + 1, system.config.node_count, 2)
    traction_ecm_on_endo = np.zeros(interface_shape, dtype=np.float64)
    traction_endo_on_ecm = np.zeros(interface_shape, dtype=np.float64)
    traction_myo_on_ecm = np.zeros(interface_shape, dtype=np.float64)
    traction_ecm_on_myo = np.zeros(interface_shape, dtype=np.float64)
    endocardial_shortening = np.zeros(step_count + 1, dtype=np.float64)
    ecm_shortening = np.zeros(step_count + 1, dtype=np.float64)
    myocardial_shortening = np.zeros(step_count + 1, dtype=np.float64)

    step_arrays = {
        name: np.zeros(step_count, dtype=np.float64)
        for name in (
            "delta_stored_energy",
            "dissipation_ecm",
            "dissipation_endocardium",
            "dissipation_myocardium",
            "work_lumen",
            "work_external",
            "work_active",
            "numerical_residual",
            "interface_endocardium_ecm_power_residual",
            "interface_ecm_myocardium_power_residual",
        )
    }

    def capture(sample_index: int, sample_state: FloatArray) -> None:
        values = _drive_values(
            selected_drive, float(time[sample_index]), system.config.period
        )
        for name, value in values.items():
            drive_arrays[name][sample_index] = value
        components = _energy_components(
            system, sample_state, values["activation"]
        )
        for name, value in components.items():
            energy_components[name][sample_index] = value
        stored_energy[sample_index] = float(sum(components.values()))
        endocardium_displacement[sample_index] = system.layer_view(
            sample_state, "endocardium"
        )
        ecm_displacement[sample_index] = system.layer_view(sample_state, "ecm")
        myocardium_displacement[sample_index] = system.layer_view(
            sample_state, "myocardium"
        )
        internal_z[sample_index] = system.internal_z_view(sample_state)
        observables = _state_observables(system, sample_state)
        connection_force[sample_index] = observables[
            "endocardial_connection_force"
        ]
        traction_ecm_on_endo[sample_index] = observables[
            "traction_ecm_on_endocardium"
        ]
        traction_endo_on_ecm[sample_index] = observables[
            "traction_endocardium_on_ecm"
        ]
        traction_myo_on_ecm[sample_index] = observables[
            "traction_myocardium_on_ecm"
        ]
        traction_ecm_on_myo[sample_index] = observables[
            "traction_ecm_on_myocardium"
        ]
        endocardial_shortening[sample_index] = float(
            observables["endocardial_shortening"]
        )
        ecm_shortening[sample_index] = float(observables["ecm_shortening"])
        myocardial_shortening[sample_index] = float(
            observables["myocardial_shortening"]
        )

    capture(0, state)
    left_matrix = system.matrix_g / time_step + 0.5 * system.matrix_a
    right_operator = system.matrix_g / time_step - 0.5 * system.matrix_a
    for step in range(step_count):
        values_start = _drive_values(
            selected_drive, float(time[step]), system.config.period
        )
        values_end = _drive_values(
            selected_drive, float(time[step + 1]), system.config.period
        )
        activation_midpoint = 0.5 * (
            values_start["activation"] + values_end["activation"]
        )
        lumen_start, external_start = _load_vectors(system, values_start)
        lumen_end, external_end = _load_vectors(system, values_end)
        lumen_midpoint = 0.5 * (lumen_start + lumen_end)
        external_midpoint = 0.5 * (external_start + external_end)
        right_hand_side = (
            right_operator @ state
            + lumen_midpoint
            + external_midpoint
            - system.active_vector_h * activation_midpoint
        )
        next_state = np.linalg.solve(left_matrix, right_hand_side)
        increment = next_state - state
        midpoint_state = 0.5 * (next_state + state)
        velocity = increment / time_step
        dissipation_power = _dissipation_components(system, velocity)
        step_arrays["dissipation_endocardium"][step] = (
            time_step * dissipation_power["endocardium"]
        )
        step_arrays["dissipation_ecm"][step] = (
            time_step * dissipation_power["ecm"]
        )
        step_arrays["dissipation_myocardium"][step] = (
            time_step * dissipation_power["myocardium"]
        )
        step_arrays["work_lumen"][step] = float(
            np.dot(lumen_midpoint, increment)
        )
        step_arrays["work_external"][step] = float(
            np.dot(external_midpoint, increment)
        )
        activation_increment = (
            values_end["activation"] - values_start["activation"]
        )
        active_generalized_force = float(
            np.dot(system.active_vector_h, midpoint_state)
            + system.active_scalar_c * activation_midpoint
        )
        step_arrays["work_active"][step] = (
            active_generalized_force * activation_increment
        )

        states[step + 1] = next_state
        capture(step + 1, next_state)
        delta_energy = stored_energy[step + 1] - stored_energy[step]
        step_arrays["delta_stored_energy"][step] = delta_energy
        total_dissipation = (
            step_arrays["dissipation_endocardium"][step]
            + step_arrays["dissipation_ecm"][step]
            + step_arrays["dissipation_myocardium"][step]
        )
        total_input = (
            step_arrays["work_lumen"][step]
            + step_arrays["work_external"][step]
            + step_arrays["work_active"][step]
        )
        step_arrays["numerical_residual"][step] = (
            total_input - delta_energy - total_dissipation
        )

        endo_increment = system.layer_view(increment, "endocardium")
        ecm_increment = system.layer_view(increment, "ecm")
        myo_increment = system.layer_view(increment, "myocardium")
        endo_ecm_traction_midpoint = 0.5 * (
            traction_ecm_on_endo[step] + traction_ecm_on_endo[step + 1]
        )
        myo_ecm_traction_midpoint = 0.5 * (
            traction_myo_on_ecm[step] + traction_myo_on_ecm[step + 1]
        )
        endo_ecm_pair_work = float(
            np.sum(
                system.node_weights[:, None]
                * endo_ecm_traction_midpoint
                * (endo_increment - ecm_increment)
            )
        )
        ecm_myo_pair_work = float(
            np.sum(
                system.node_weights[:, None]
                * myo_ecm_traction_midpoint
                * (ecm_increment - myo_increment)
            )
        )
        step_arrays["interface_endocardium_ecm_power_residual"][step] = (
            endo_ecm_pair_work
            + energy_components["interface_endocardium_ecm"][step + 1]
            - energy_components["interface_endocardium_ecm"][step]
        )
        step_arrays["interface_ecm_myocardium_power_residual"][step] = (
            ecm_myo_pair_work
            + energy_components["interface_ecm_myocardium"][step + 1]
            - energy_components["interface_ecm_myocardium"][step]
        )
        state = next_state

    arrays: dict[str, FloatArray] = {
        "time": time,
        "state": states,
        **drive_arrays,
        "stored_energy": stored_energy,
        **{f"energy_{name}": values for name, values in energy_components.items()},
        "endocardium_displacement": endocardium_displacement,
        "ecm_displacement": ecm_displacement,
        "myocardium_displacement": myocardium_displacement,
        "ecm_internal_z": internal_z,
        "endocardial_connection_force": connection_force,
        "traction_ecm_on_endocardium": traction_ecm_on_endo,
        "traction_endocardium_on_ecm": traction_endo_on_ecm,
        "traction_myocardium_on_ecm": traction_myo_on_ecm,
        "traction_ecm_on_myocardium": traction_ecm_on_myo,
        "endocardial_shortening": endocardial_shortening,
        "ecm_shortening": ecm_shortening,
        "myocardial_shortening": myocardial_shortening,
        **step_arrays,
    }
    arrays.update(
        {
            "stored_energy_rate": step_arrays["delta_stored_energy"]
            / time_step,
            "power_lumen": step_arrays["work_lumen"] / time_step,
            "power_external": step_arrays["work_external"] / time_step,
            "power_active": step_arrays["work_active"] / time_step,
            "dissipation_power_ecm": step_arrays["dissipation_ecm"]
            / time_step,
            "dissipation_power_endocardium": step_arrays[
                "dissipation_endocardium"
            ]
            / time_step,
            "dissipation_power_myocardium": step_arrays[
                "dissipation_myocardium"
            ]
            / time_step,
            "numerical_residual_power": step_arrays["numerical_residual"]
            / time_step,
        }
    )
    action_reaction_error = max(
        float(
            np.max(
                np.abs(traction_ecm_on_endo + traction_endo_on_ecm)
            )
        ),
        float(
            np.max(
                np.abs(traction_myo_on_ecm + traction_ecm_on_myo)
            )
        ),
    )
    all_dissipation = np.concatenate(
        (
            step_arrays["dissipation_ecm"],
            step_arrays["dissipation_endocardium"],
            step_arrays["dissipation_myocardium"],
        )
    )
    cycle_ledgers: list[dict[str, float | int]] = []
    for cycle_index in range(system.config.cycles):
        step_start = cycle_index * system.config.steps_per_cycle
        step_end = (cycle_index + 1) * system.config.steps_per_cycle
        energy_change = float(
            stored_energy[step_end] - stored_energy[step_start]
        )
        dissipation_ecm = float(
            np.sum(step_arrays["dissipation_ecm"][step_start:step_end])
        )
        dissipation_endocardium = float(
            np.sum(
                step_arrays["dissipation_endocardium"][step_start:step_end]
            )
        )
        dissipation_myocardium = float(
            np.sum(
                step_arrays["dissipation_myocardium"][step_start:step_end]
            )
        )
        work_lumen = float(
            np.sum(step_arrays["work_lumen"][step_start:step_end])
        )
        work_external = float(
            np.sum(step_arrays["work_external"][step_start:step_end])
        )
        work_active = float(
            np.sum(step_arrays["work_active"][step_start:step_end])
        )
        residual = float(
            np.sum(step_arrays["numerical_residual"][step_start:step_end])
        )
        cycle_ledgers.append(
            {
                "cycle": cycle_index + 1,
                "delta_stored_energy": energy_change,
                "dissipation_ecm": dissipation_ecm,
                "dissipation_endocardium": dissipation_endocardium,
                "dissipation_myocardium": dissipation_myocardium,
                "work_lumen": work_lumen,
                "work_external": work_external,
                "work_active": work_active,
                "numerical_residual": residual,
            }
        )
    summary: dict[str, Any] = {
        "case_name": case_name,
        "model_identity": "endocardial_DCM__viscoelastic_ECM_FEM__active_myocardial_FEM",
        "dimension_statement": "1D P1 strip with 2D tangential/normal kinematics",
        "units": "nondimensional_M1_verification",
        "node_count": system.config.node_count,
        "steps_per_cycle": system.config.steps_per_cycle,
        "cycles": system.config.cycles,
        "peak_endocardial_shortening": float(
            np.max(endocardial_shortening)
        ),
        "peak_ecm_shortening": float(np.max(ecm_shortening)),
        "peak_myocardial_shortening": float(np.max(myocardial_shortening)),
        "minimum_myocardial_shortening": float(np.min(myocardial_shortening)),
        "maximum_absolute_endocardium_displacement": float(
            np.max(np.abs(endocardium_displacement))
        ),
        "maximum_absolute_ecm_displacement": float(
            np.max(np.abs(ecm_displacement))
        ),
        "maximum_absolute_myocardium_displacement": float(
            np.max(np.abs(myocardium_displacement))
        ),
        "maximum_absolute_ecm_internal_z": float(np.max(np.abs(internal_z))),
        "maximum_absolute_endocardial_connection_force": float(
            np.max(np.abs(connection_force))
        ),
        "maximum_absolute_endocardium_ecm_traction": float(
            np.max(np.abs(traction_ecm_on_endo))
        ),
        "maximum_absolute_ecm_myocardium_traction": float(
            np.max(np.abs(traction_myo_on_ecm))
        ),
        "maximum_action_reaction_error": action_reaction_error,
        "maximum_absolute_step_ledger_residual": float(
            np.max(np.abs(step_arrays["numerical_residual"]))
        ),
        "run_integrated_ledger_residual": float(
            np.sum(step_arrays["numerical_residual"])
        ),
        "maximum_absolute_cycle_integrated_ledger_residual": max(
            abs(float(payload["numerical_residual"]))
            for payload in cycle_ledgers
        ),
        "cycle_ledgers": cycle_ledgers,
        "maximum_absolute_interface_power_residual": max(
            float(
                np.max(
                    np.abs(
                        step_arrays[
                            "interface_endocardium_ecm_power_residual"
                        ]
                    )
                )
            ),
            float(
                np.max(
                    np.abs(
                        step_arrays[
                            "interface_ecm_myocardium_power_residual"
                        ]
                    )
                )
            ),
        ),
        "minimum_step_dissipation": float(np.min(all_dissipation)),
        "integrated_dissipation": {
            "ecm": float(np.sum(step_arrays["dissipation_ecm"])),
            "endocardium": float(
                np.sum(step_arrays["dissipation_endocardium"])
            ),
            "myocardium": float(
                np.sum(step_arrays["dissipation_myocardium"])
            ),
        },
        "integrated_work": {
            "lumen": float(np.sum(step_arrays["work_lumen"])),
            "external": float(np.sum(step_arrays["work_external"])),
            "active": float(np.sum(step_arrays["work_active"])),
        },
        "transfer": _transfer_metrics(system, arrays, selected_drive),
    }
    return SimulationResult(
        case_name=case_name,
        config=system.config,
        drive=selected_drive,
        arrays=arrays,
        summary=summary,
    )


def build_passive_perturbation(
    config: StripConfig | None = None,
    *,
    amplitude: float = 0.01,
) -> FloatArray:
    system = assemble_strip_system(config)
    if not np.isfinite(amplitude) or amplitude <= 0.0:
        raise ValueError("amplitude must be finite and positive")
    state = np.zeros(system.state_size, dtype=np.float64)
    endocardium = state[system.endocardium_slice].reshape(
        system.config.node_count, 2
    )
    coordinates = np.linspace(0.0, 1.0, system.config.node_count)
    endocardium[:, 0] = amplitude * np.sin(math.pi * coordinates)
    endocardium[:, 1] = 0.5 * amplitude * np.sin(2.0 * math.pi * coordinates)
    return state


def _relative_difference(first: float, second: float) -> float:
    return float(abs(first - second) / max(abs(first), abs(second), 1.0e-14))


def run_validation_suite() -> dict[str, Any]:
    """Execute the approved CPU-only M1 validation package."""
    base_config = StripConfig()
    cases = {
        "zero_drive": run_case("zero_drive", config=base_config),
        "active_only": run_case(
            "active_only",
            config=base_config,
            drive=DriveProtocol(activation_peak=0.10),
        ),
        "lumen_normal_only": run_case(
            "lumen_normal_only",
            config=base_config,
            drive=DriveProtocol(pressure_peak=0.045),
        ),
        "lumen_shear_only": run_case(
            "lumen_shear_only",
            config=base_config,
            drive=DriveProtocol(shear_amplitude=0.035),
        ),
        "external_port_only": run_case(
            "external_port_only",
            config=base_config,
            drive=DriveProtocol(
                external_tangential_amplitude=0.02,
                external_normal_peak=0.015,
            ),
        ),
        "passive_relaxation": run_case(
            "passive_relaxation",
            config=base_config,
            initial_state=build_passive_perturbation(base_config),
        ),
    }
    replay = run_case(
        "active_only_replay",
        config=base_config,
        drive=DriveProtocol(activation_peak=0.10),
    )
    deterministic_replay = all(
        np.array_equal(value, replay.arrays[name])
        for name, value in cases["active_only"].arrays.items()
    )

    coarse_time = run_case(
        "active_only_T64",
        config=replace(base_config, steps_per_cycle=64),
        drive=DriveProtocol(activation_peak=0.10),
    )
    fine_mesh = run_case(
        "active_only_N17",
        config=replace(base_config, node_count=17),
        drive=DriveProtocol(activation_peak=0.10),
    )
    base_summary = cases["active_only"].summary
    sensitivity_keys = (
        "peak_myocardial_shortening",
        "maximum_absolute_endocardium_ecm_traction",
        "maximum_absolute_ecm_internal_z",
    )
    time_sensitivity = {
        key: _relative_difference(base_summary[key], coarse_time.summary[key])
        for key in sensitivity_keys
    }
    mesh_sensitivity = {
        key: _relative_difference(base_summary[key], fine_mesh.summary[key])
        for key in sensitivity_keys
    }

    all_summaries = [result.summary for result in cases.values()]
    zero_state_norm = float(
        np.max(np.abs(cases["zero_drive"].arrays["state"]))
    )
    pressure_tangential_leak = float(
        np.max(
            np.abs(
                cases["lumen_normal_only"].arrays[
                    "endocardium_displacement"
                ][:, :, 0]
            )
        )
    )
    shear_normal_leak = float(
        np.max(
            np.abs(
                cases["lumen_shear_only"].arrays[
                    "endocardium_displacement"
                ][:, :, 1]
            )
        )
    )
    passive_energy_drop = float(
        cases["passive_relaxation"].arrays["stored_energy"][0]
        - cases["passive_relaxation"].arrays["stored_energy"][-1]
    )
    gates = {
        "zero_drive_equilibrium": zero_state_norm <= 1.0e-14,
        "active_myocardium_shortens": (
            base_summary["peak_myocardial_shortening"] > 1.0e-5
            and base_summary["integrated_work"]["active"] > 0.0
        ),
        "normal_pressure_is_component_separated": (
            pressure_tangential_leak <= 1.0e-13
            and cases["lumen_normal_only"].summary[
                "maximum_absolute_endocardium_displacement"
            ]
            > 1.0e-6
        ),
        "shear_is_component_separated": (
            shear_normal_leak <= 1.0e-13
            and cases["lumen_shear_only"].summary[
                "maximum_absolute_endocardium_displacement"
            ]
            > 1.0e-6
        ),
        "action_reaction": max(
            summary["maximum_action_reaction_error"]
            for summary in all_summaries
        )
        <= 1.0e-12,
        "power_sign_and_ledger": max(
            summary["maximum_absolute_step_ledger_residual"]
            for summary in all_summaries
        )
        <= 1.0e-11,
        "interface_power": max(
            summary["maximum_absolute_interface_power_residual"]
            for summary in all_summaries
        )
        <= 1.0e-11,
        "passive_limit_and_dissipation": (
            passive_energy_drop > 0.0
            and min(
                summary["minimum_step_dissipation"]
                for summary in all_summaries
            )
            >= -1.0e-14
        ),
        "deterministic_replay": deterministic_replay,
        "time_sensitivity_screen": max(time_sensitivity.values()) < 0.10,
        "mesh_sensitivity_screen": max(mesh_sensitivity.values()) < 0.10,
    }
    return {
        "schema_version": "paper2_m1_idealized_strip_validation_v01",
        "status": (
            "passed_m1_human_gate_candidate"
            if all(gates.values())
            else "failed_m1_hard_gate"
        ),
        "evidence_boundary": (
            "Nondimensional quasi-2D identity/port validation only; the T64/T128 "
            "and N9/N17 comparisons are sensitivity screens, not convergence proof."
        ),
        "gates": {key: bool(value) for key, value in gates.items()},
        "case_summaries": {
            name: result.summary for name, result in cases.items()
        },
        "sensitivity": {
            "time_T64_vs_T128": time_sensitivity,
            "mesh_N9_vs_N17": mesh_sensitivity,
            "claim": "finite_screen_only_not_formal_convergence",
        },
        "deterministic_replay_exact": deterministic_replay,
        "diagnostics": {
            "zero_state_norm": zero_state_norm,
            "pressure_tangential_leak": pressure_tangential_leak,
            "shear_normal_leak": shear_normal_leak,
            "passive_energy_drop": passive_energy_drop,
        },
        "cases": cases,
        "sensitivity_cases": {
            "active_only_T64": coarse_time,
            "active_only_N17": fine_mesh,
        },
    }
