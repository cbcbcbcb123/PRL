from __future__ import annotations

from io import BytesIO

import numpy as np
import pytest

from hybrid.efe_step_transaction import (
    CycleStepConsistencyMetrics,
    PeriodicWarmStartMetrics,
    StepOracleMetrics,
    audit_cycle_step_consistency,
    audit_periodic_warm_start,
    audit_transaction_candidate,
    checkpoint_array_digest,
    cycle_phase_spec,
    serialize_checkpoint,
    validation_cycle_indices,
)


def passing_metrics() -> StepOracleMetrics:
    return StepOracleMetrics(
        normalized_kkt_residual=1.0e-7,
        raw_coupling_residual=2.0e-5,
        volume_constraint_residual=0.0,
        minimum_ecm_jacobian=0.99,
        minimum_gap=0.01,
        minimum_myocyte_face_area_ratio=0.9,
        minimum_endocardial_face_area_ratio=0.9,
        internal_symmetry_residual=0.0,
        internal_trace_residual=0.0,
    )


def test_checkpoint_digest_is_stable_and_content_sensitive() -> None:
    variables = np.asarray([1.0, 2.0])
    internal_z = np.zeros((1, 3, 3))
    contact = np.asarray([0.0])
    first = checkpoint_array_digest(variables, internal_z, contact)
    assert first == checkpoint_array_digest(
        variables.copy(), internal_z.copy(), contact.copy()
    )
    changed = variables.copy()
    changed[0] += 1.0e-12
    assert first != checkpoint_array_digest(changed, internal_z, contact)


def test_checkpoint_digest_rejects_nonfinite_values() -> None:
    with pytest.raises(ValueError, match="finite"):
        checkpoint_array_digest(np.asarray([np.nan]))


def test_checkpoint_serialization_round_trip_preserves_digest() -> None:
    variables = np.asarray([1.0, -2.0])
    internal_z = np.zeros((2, 3, 3))
    contact = np.asarray([0.5, 0.0])
    payload = serialize_checkpoint(
        variables=variables,
        internal_z=internal_z,
        contact_multipliers=contact,
    )
    with np.load(BytesIO(payload)) as arrays:
        observed = checkpoint_array_digest(
            arrays["variables"],
            arrays["ecm_internal_z"],
            arrays["contact_multipliers"],
        )
    assert observed == checkpoint_array_digest(variables, internal_z, contact)


def test_candidate_audit_passes_only_when_all_parent_gates_pass() -> None:
    digest = "same"
    audit = audit_transaction_candidate(
        worker_passed=True,
        expected_input_digest=digest,
        worker_input_digest=digest,
        post_worker_input_digest=digest,
        metrics=passing_metrics(),
    )
    assert audit["passed"] is True
    assert all(audit["checks"].values())


@pytest.mark.parametrize(
    ("worker_passed", "worker_digest", "post_digest", "metrics_field"),
    (
        (False, "same", "same", None),
        (True, "wrong", "same", None),
        (True, "same", "wrong", None),
        (True, "same", "same", "normalized_kkt_residual"),
        (True, "same", "same", "raw_coupling_residual"),
        (True, "same", "same", "minimum_ecm_jacobian"),
        (True, "same", "same", "minimum_gap"),
    ),
)
def test_candidate_audit_rejects_any_failed_gate(
    worker_passed: bool,
    worker_digest: str,
    post_digest: str,
    metrics_field: str | None,
) -> None:
    values = passing_metrics().__dict__.copy()
    failing_values = {
        "normalized_kkt_residual": 2.0e-5,
        "raw_coupling_residual": 2.0e-4,
        "minimum_ecm_jacobian": 0.4,
        "minimum_gap": -1.0e-5,
    }
    if metrics_field is not None:
        values[metrics_field] = failing_values[metrics_field]
    audit = audit_transaction_candidate(
        worker_passed=worker_passed,
        expected_input_digest="same",
        worker_input_digest=worker_digest,
        post_worker_input_digest=post_digest,
        metrics=StepOracleMetrics(**values),
    )
    assert audit["passed"] is False


def test_cycle_phase_default_reproduces_archived_failed_step() -> None:
    phase = cycle_phase_spec(
        cycle_index=3,
        step_index=4,
        steps_per_cycle=16,
        period=1.0,
        peak_activation=0.2,
    )
    assert phase.time_step == pytest.approx(1.0 / 16.0)
    assert phase.phase_time == pytest.approx(0.25)
    assert phase.time_value == pytest.approx(2.25)
    assert phase.activation == pytest.approx(0.1)
    assert phase.activation_rate == pytest.approx(0.2 * np.pi)


@pytest.mark.parametrize(
    ("cycle_index", "step_index", "steps_per_cycle", "period"),
    (
        (0, 1, 16, 1.0),
        (1, 0, 16, 1.0),
        (1, 17, 16, 1.0),
        (1, 1, 0, 1.0),
        (1, 1, 16, 0.0),
    ),
)
def test_cycle_phase_rejects_invalid_coordinates(
    cycle_index: int,
    step_index: int,
    steps_per_cycle: int,
    period: float,
) -> None:
    with pytest.raises(ValueError):
        cycle_phase_spec(
            cycle_index=cycle_index,
            step_index=step_index,
            steps_per_cycle=steps_per_cycle,
            period=period,
            peak_activation=0.2,
        )


def test_cycle_step_consistency_requires_sls_match_and_dissipation() -> None:
    passing = audit_cycle_step_consistency(
        CycleStepConsistencyMetrics(
            internal_update_symmetric_relative=0.0,
            dissipation_step=1.0e-8,
        )
    )
    assert passing["passed"] is True
    mismatched = audit_cycle_step_consistency(
        CycleStepConsistencyMetrics(
            internal_update_symmetric_relative=2.0e-12,
            dissipation_step=1.0e-8,
        )
    )
    assert mismatched["passed"] is False
    negative = audit_cycle_step_consistency(
        CycleStepConsistencyMetrics(
            internal_update_symmetric_relative=0.0,
            dissipation_step=-1.0e-10,
        )
    )
    assert negative["passed"] is False


def passing_periodic_warm_start_metrics() -> PeriodicWarmStartMetrics:
    return PeriodicWarmStartMetrics(
        frozen_periodicity_residual=1.0e-15,
        candidate_internal_relative_difference=0.0,
        normalized_kkt_residual=1.0e-7,
        volume_constraint_residual=0.0,
        minimum_ecm_jacobian=0.99,
        minimum_gap=0.01,
        minimum_myocyte_face_area_ratio=0.9,
        minimum_endocardial_face_area_ratio=0.9,
        internal_symmetry_residual=0.0,
        internal_trace_residual=0.0,
    )


def test_periodic_warm_start_requires_periodic_candidate_and_state_gates() -> None:
    passing = audit_periodic_warm_start(
        passing_periodic_warm_start_metrics()
    )
    assert passing["passed"] is True
    for field, failing_value in (
        ("frozen_periodicity_residual", 2.0e-12),
        ("candidate_internal_relative_difference", 2.0e-12),
        ("normalized_kkt_residual", 2.0e-5),
        ("volume_constraint_residual", 2.0e-8),
        ("minimum_ecm_jacobian", 0.4),
        ("minimum_gap", -1.0e-5),
        ("minimum_myocyte_face_area_ratio", 0.04),
        ("minimum_endocardial_face_area_ratio", 0.04),
        ("internal_symmetry_residual", 2.0e-12),
        ("internal_trace_residual", 2.0e-12),
    ):
        values = passing_periodic_warm_start_metrics().__dict__.copy()
        values[field] = failing_value
        rejected = audit_periodic_warm_start(
            PeriodicWarmStartMetrics(**values)
        )
        assert rejected["passed"] is False, field


def test_validation_cycle_indices_preserve_r3_default_and_r4_window() -> None:
    assert validation_cycle_indices(3) == (3, 4)
    assert validation_cycle_indices(5) == (5, 6)
    assert validation_cycle_indices(7) == (7, 8)
    with pytest.raises(ValueError):
        validation_cycle_indices(0)
    with pytest.raises(ValueError):
        validation_cycle_indices(1, 0)
