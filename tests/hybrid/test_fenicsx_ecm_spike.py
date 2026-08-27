from __future__ import annotations

import numpy as np
import pytest

from hybrid.efe_fast_trilayer import (
    build_fast_trilayer_model,
    evaluate_fast_trilayer_state,
)
from hybrid.efe_fast_trilayer_solver import solve_fast_trilayer_equilibrium
from hybrid.fenicsx_ecm_spike import (
    affine_deformation,
    build_affine_case,
    build_m0_case,
    evaluate_reference_case,
)
from route_h.ecm_finite_strain import ecm_energy_force


def test_registered_affine_case_is_positive_and_spatially_uniform() -> None:
    model = build_fast_trilayer_model(
        dcm_level="D0", ecm_level="E0", ecm_footprint_scale=1.5
    )
    case = build_affine_case(model.ecm_reference)
    assert np.linalg.det(affine_deformation()) > 0.0
    assert np.allclose(case.internal_z, case.internal_z.transpose(0, 2, 1))
    assert np.allclose(np.trace(case.internal_z, axis1=1, axis2=2), 0.0)

    energies, _, jacobians, _ = evaluate_reference_case(
        case,
        model.ecm_reference,
        mu_eq=model.mu_eq,
        kappa_eq=model.kappa_eq,
        mu_ve=model.mu_ve,
        warm_repeats=2,
    )
    assert energies["ecm_total"] > 0.0
    assert np.allclose(jacobians, np.linalg.det(affine_deformation()), atol=1.0e-12)


def test_m0_case_has_zero_energy_force_and_unit_jacobian() -> None:
    model = build_fast_trilayer_model(
        dcm_level="D0", ecm_level="E0", ecm_footprint_scale=1.5
    )
    case = build_m0_case(model.ecm_reference)
    energies, force, jacobians, benchmark = evaluate_reference_case(
        case,
        model.ecm_reference,
        mu_eq=model.mu_eq,
        kappa_eq=model.kappa_eq,
        mu_ve=model.mu_ve,
        warm_repeats=2,
    )
    assert abs(energies["ecm_total"]) <= 1.0e-14
    assert np.linalg.norm(force) <= 1.0e-13
    assert np.allclose(jacobians, 1.0, atol=1.0e-13)
    assert benchmark["warm_repeats"] == 1


def test_explicit_ecm_backend_seam_matches_default_evaluation() -> None:
    model = build_fast_trilayer_model(
        dcm_level="D0", ecm_level="E0", ecm_footprint_scale=1.0
    )
    call_count = 0

    def recording_backend(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        return ecm_energy_force(*args, **kwargs)

    default = evaluate_fast_trilayer_state(
        model,
        model.myocyte.vertices,
        model.ecm_reference.vertices,
        model.endocardium.vertices,
    )
    explicit = evaluate_fast_trilayer_state(
        model,
        model.myocyte.vertices,
        model.ecm_reference.vertices,
        model.endocardium.vertices,
        ecm_backend=recording_backend,
    )
    assert call_count == 1
    assert explicit.total_stored_energy == pytest.approx(
        default.total_stored_energy, abs=1.0e-14
    )
    assert np.allclose(explicit.ecm_force, default.ecm_force, atol=1.0e-14)
    assert explicit.minimum_ecm_jacobian == pytest.approx(
        default.minimum_ecm_jacobian, abs=1.0e-14
    )


def test_equilibrium_solver_propagates_explicit_ecm_backend() -> None:
    model = build_fast_trilayer_model(
        dcm_level="D0", ecm_level="E0", ecm_footprint_scale=1.0
    )

    class BackendReached(RuntimeError):
        pass

    def stopping_backend(*_args, **_kwargs):
        raise BackendReached

    with pytest.raises(BackendReached):
        solve_fast_trilayer_equilibrium(
            model,
            ecm_backend=stopping_backend,
            maximum_iterations=1,
            maximum_newton_iterations=0,
            maximum_follower_iterations=1,
        )
