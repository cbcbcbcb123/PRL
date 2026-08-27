"""Commit-after-validation helpers for isolated EFE time-step workers."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
from io import BytesIO
import math
import os
from pathlib import Path

import numpy as np
from numpy.typing import NDArray


FloatArray = NDArray[np.float64]


def file_sha256(path: Path) -> str:
    """Hash one gate-critical source artifact."""
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


@dataclass(frozen=True)
class StepGateContract:
    kkt_tolerance: float = 1.0e-5
    coupling_tolerance: float = 1.0e-4
    volume_tolerance: float = 1.0e-8
    minimum_ecm_jacobian: float = 0.5
    minimum_gap: float = -1.0e-12
    minimum_face_area_ratio: float = 0.05
    internal_symmetry_tolerance: float = 1.0e-12
    internal_trace_tolerance: float = 1.0e-12


@dataclass(frozen=True)
class StepOracleMetrics:
    normalized_kkt_residual: float
    raw_coupling_residual: float
    volume_constraint_residual: float
    minimum_ecm_jacobian: float
    minimum_gap: float
    minimum_myocyte_face_area_ratio: float
    minimum_endocardial_face_area_ratio: float
    internal_symmetry_residual: float
    internal_trace_residual: float


@dataclass(frozen=True)
class CyclePhaseSpec:
    cycle_index: int
    step_index: int
    steps_per_cycle: int
    period: float
    time_step: float
    phase_time: float
    time_value: float
    activation: float
    activation_rate: float


@dataclass(frozen=True)
class CycleStepConsistencyMetrics:
    internal_update_symmetric_relative: float
    dissipation_step: float


@dataclass(frozen=True)
class PeriodicWarmStartMetrics:
    frozen_periodicity_residual: float
    candidate_internal_relative_difference: float
    normalized_kkt_residual: float
    volume_constraint_residual: float
    minimum_ecm_jacobian: float
    minimum_gap: float
    minimum_myocyte_face_area_ratio: float
    minimum_endocardial_face_area_ratio: float
    internal_symmetry_residual: float
    internal_trace_residual: float


def validation_cycle_indices(
    first_cycle_index: int, cycle_count: int = 2
) -> tuple[int, ...]:
    """Return a consecutive, positive validation-cycle window."""
    if first_cycle_index < 1:
        raise ValueError("first cycle index must be positive")
    if cycle_count < 1:
        raise ValueError("cycle count must be positive")
    return tuple(range(first_cycle_index, first_cycle_index + cycle_count))


def cycle_phase_spec(
    *,
    cycle_index: int,
    step_index: int,
    steps_per_cycle: int,
    period: float,
    peak_activation: float,
) -> CyclePhaseSpec:
    """Return the frozen smooth-cycle phase data for one transaction."""
    if cycle_index < 1:
        raise ValueError("cycle index must be positive")
    if steps_per_cycle < 1:
        raise ValueError("steps per cycle must be positive")
    if not 1 <= step_index <= steps_per_cycle:
        raise ValueError("step index must be within the cycle")
    if not math.isfinite(period) or period <= 0.0:
        raise ValueError("period must be finite and positive")
    if not math.isfinite(peak_activation) or peak_activation < 0.0:
        raise ValueError("peak activation must be finite and nonnegative")
    time_step = period / steps_per_cycle
    phase_time = step_index * time_step
    phase_angle = 2.0 * math.pi * phase_time / period
    activation = 0.5 * peak_activation * (1.0 - math.cos(phase_angle))
    activation_rate = (
        peak_activation * math.pi / period * math.sin(phase_angle)
    )
    return CyclePhaseSpec(
        cycle_index=cycle_index,
        step_index=step_index,
        steps_per_cycle=steps_per_cycle,
        period=period,
        time_step=time_step,
        phase_time=phase_time,
        time_value=(cycle_index - 1) * period + phase_time,
        activation=activation,
        activation_rate=activation_rate,
    )


def checkpoint_array_digest(*arrays: FloatArray) -> str:
    """Hash checkpoint arrays independently of their container byte layout."""
    digest = hashlib.sha256()
    for array in arrays:
        contiguous = np.ascontiguousarray(array, dtype=np.float64)
        if not np.all(np.isfinite(contiguous)):
            raise ValueError("checkpoint arrays must be finite")
        digest.update(str(contiguous.shape).encode("ascii"))
        digest.update(contiguous.dtype.str.encode("ascii"))
        digest.update(contiguous.tobytes())
    return digest.hexdigest()


def serialize_checkpoint(
    *,
    variables: FloatArray,
    internal_z: FloatArray,
    contact_multipliers: FloatArray,
) -> bytes:
    """Build a complete compressed checkpoint payload in memory."""
    checkpoint_array_digest(variables, internal_z, contact_multipliers)
    stream = BytesIO()
    np.savez_compressed(
        stream,
        variables=np.asarray(variables, dtype=np.float64),
        ecm_internal_z=np.asarray(internal_z, dtype=np.float64),
        contact_multipliers=np.asarray(
            contact_multipliers, dtype=np.float64
        ),
    )
    return stream.getvalue()


def write_checkpoint_exclusive(
    path: Path,
    *,
    variables: FloatArray,
    internal_z: FloatArray,
    contact_multipliers: FloatArray,
) -> dict[str, object]:
    """Create one accepted checkpoint without permitting replacement."""
    payload = serialize_checkpoint(
        variables=variables,
        internal_z=internal_z,
        contact_multipliers=contact_multipliers,
    )
    expected_digest = checkpoint_array_digest(
        variables, internal_z, contact_multipliers
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as stream:
        stream.write(payload)
        stream.flush()
        os.fsync(stream.fileno())
    with np.load(path) as arrays:
        observed_digest = checkpoint_array_digest(
            np.asarray(arrays["variables"], dtype=np.float64),
            np.asarray(arrays["ecm_internal_z"], dtype=np.float64),
            np.asarray(arrays["contact_multipliers"], dtype=np.float64),
        )
    if observed_digest != expected_digest:
        raise RuntimeError("committed checkpoint digest mismatch")
    return {
        "path": str(path),
        "array_digest": observed_digest,
        "payload_bytes": len(payload),
        "create_only": True,
    }


def audit_transaction_candidate(
    *,
    worker_passed: bool,
    expected_input_digest: str,
    worker_input_digest: str,
    post_worker_input_digest: str,
    metrics: StepOracleMetrics,
    contract: StepGateContract | None = None,
) -> dict[str, object]:
    """Evaluate every parent-side gate before an accepted checkpoint exists."""
    selected_contract = StepGateContract() if contract is None else contract
    values = np.asarray(list(asdict(metrics).values()), dtype=np.float64)
    checks = {
        "worker_reported_pass": bool(worker_passed),
        "worker_loaded_expected_input": (
            worker_input_digest == expected_input_digest
        ),
        "input_preserved_after_worker": (
            post_worker_input_digest == expected_input_digest
        ),
        "oracle_values_finite": bool(np.all(np.isfinite(values))),
        "kkt_gate": (
            metrics.normalized_kkt_residual
            <= selected_contract.kkt_tolerance
        ),
        "raw_coupling_gate": (
            metrics.raw_coupling_residual
            <= selected_contract.coupling_tolerance
        ),
        "volume_gate": (
            metrics.volume_constraint_residual
            <= selected_contract.volume_tolerance
        ),
        "ecm_jacobian_gate": (
            metrics.minimum_ecm_jacobian
            >= selected_contract.minimum_ecm_jacobian
        ),
        "gap_gate": metrics.minimum_gap >= selected_contract.minimum_gap,
        "myocyte_face_gate": (
            metrics.minimum_myocyte_face_area_ratio
            >= selected_contract.minimum_face_area_ratio
        ),
        "endocardial_face_gate": (
            metrics.minimum_endocardial_face_area_ratio
            >= selected_contract.minimum_face_area_ratio
        ),
        "internal_symmetry_gate": (
            metrics.internal_symmetry_residual
            <= selected_contract.internal_symmetry_tolerance
        ),
        "internal_trace_gate": (
            metrics.internal_trace_residual
            <= selected_contract.internal_trace_tolerance
        ),
    }
    return {
        "contract": asdict(selected_contract),
        "oracle_metrics": asdict(metrics),
        "checks": checks,
        "passed": all(checks.values()),
    }


def audit_cycle_step_consistency(
    metrics: CycleStepConsistencyMetrics,
    *,
    internal_update_tolerance: float = 1.0e-12,
    minimum_dissipation: float = -1.0e-14,
) -> dict[str, object]:
    """Check the parent-recomputed SLS update and dissipation contract."""
    values = np.asarray(list(asdict(metrics).values()), dtype=np.float64)
    checks = {
        "consistency_values_finite": bool(np.all(np.isfinite(values))),
        "parent_sls_update_gate": (
            metrics.internal_update_symmetric_relative
            <= internal_update_tolerance
        ),
        "nonnegative_dissipation_gate": (
            metrics.dissipation_step >= minimum_dissipation
        ),
    }
    return {
        "contract": {
            "internal_update_tolerance": internal_update_tolerance,
            "minimum_dissipation": minimum_dissipation,
        },
        "metrics": asdict(metrics),
        "checks": checks,
        "passed": all(checks.values()),
    }


def audit_periodic_warm_start(
    metrics: PeriodicWarmStartMetrics,
    *,
    contract: StepGateContract | None = None,
    periodicity_tolerance: float = 1.0e-12,
    candidate_tolerance: float = 1.0e-12,
) -> dict[str, object]:
    """Apply the registered parent-side gates to a phase-zero warm start."""
    selected_contract = StepGateContract() if contract is None else contract
    values = np.asarray(list(asdict(metrics).values()), dtype=np.float64)
    checks = {
        "values_finite": bool(np.all(np.isfinite(values))),
        "frozen_periodicity_gate": (
            metrics.frozen_periodicity_residual <= periodicity_tolerance
        ),
        "candidate_internal_gate": (
            metrics.candidate_internal_relative_difference
            <= candidate_tolerance
        ),
        "kkt_gate": (
            metrics.normalized_kkt_residual
            <= selected_contract.kkt_tolerance
        ),
        "volume_gate": (
            metrics.volume_constraint_residual
            <= selected_contract.volume_tolerance
        ),
        "ecm_jacobian_gate": (
            metrics.minimum_ecm_jacobian
            >= selected_contract.minimum_ecm_jacobian
        ),
        "gap_gate": metrics.minimum_gap >= selected_contract.minimum_gap,
        "myocyte_face_gate": (
            metrics.minimum_myocyte_face_area_ratio
            >= selected_contract.minimum_face_area_ratio
        ),
        "endocardial_face_gate": (
            metrics.minimum_endocardial_face_area_ratio
            >= selected_contract.minimum_face_area_ratio
        ),
        "internal_symmetry_gate": (
            metrics.internal_symmetry_residual
            <= selected_contract.internal_symmetry_tolerance
        ),
        "internal_trace_gate": (
            metrics.internal_trace_residual
            <= selected_contract.internal_trace_tolerance
        ),
    }
    return {
        "contract": {
            **asdict(selected_contract),
            "periodicity_tolerance": periodicity_tolerance,
            "candidate_tolerance": candidate_tolerance,
        },
        "metrics": asdict(metrics),
        "checks": checks,
        "passed": all(checks.values()),
    }
