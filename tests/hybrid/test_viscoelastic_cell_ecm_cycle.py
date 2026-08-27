from __future__ import annotations

import numpy as np
import pytest

from hybrid.fixed_topology_active_cell_ecm import build_fixed_topology_model
from hybrid.viscoelastic_cell_ecm_cycle import update_ecm_internal_state


def test_viscoelastic_model_requires_positive_viscosity() -> None:
    with pytest.raises(ValueError, match="viscosity"):
        build_fixed_topology_model(
            "basal",
            patch_divisions=(1, 1, 1),
            mu_ve=0.5,
            eta_ve=0.0,
        )


def test_ecm_internal_update_preserves_structure_and_dissipates() -> None:
    model = build_fixed_topology_model(
        "basal",
        patch_divisions=(1, 1, 1),
        mu_eq=1.0,
        kappa_eq=20.0,
        mu_ve=0.5,
        eta_ve=0.125,
    )
    reference = model.vertical_slice.ecm_reference
    current = reference.vertices.copy()
    current[model.ecm_free_vertex_ids, 0] += 0.02
    initial = np.zeros((len(reference.tetrahedra), 3, 3), dtype=np.float64)
    updated, dissipation = update_ecm_internal_state(
        model,
        current,
        initial,
        0.1,
    )
    assert np.linalg.norm(updated) > 0.0
    assert np.allclose(updated, np.swapaxes(updated, 1, 2), atol=1.0e-14)
    assert np.max(np.abs(np.trace(updated, axis1=1, axis2=2))) < 1.0e-14
    assert dissipation > 0.0


def test_external_internal_state_changes_ecm_branch_without_mutating_model() -> None:
    model = build_fixed_topology_model(
        "basal",
        patch_divisions=(1, 1, 1),
        mu_ve=0.5,
        eta_ve=0.125,
    )
    cell = model.cell_reference.vertices.copy()
    ecm = model.vertical_slice.ecm_reference.vertices.copy()
    ecm[model.ecm_free_vertex_ids, 0] += 0.01
    zero = np.zeros(
        (len(model.vertical_slice.ecm_reference.tetrahedra), 3, 3),
        dtype=np.float64,
    )
    shifted = zero.copy()
    shifted[:, 0, 0] = 0.01
    shifted[:, 1, 1] = -0.005
    shifted[:, 2, 2] = -0.005
    first = model.vertical_slice.evaluate(
        cell,
        ecm,
        ecm_internal_z=zero,
        reject_penetration=False,
    )
    second = model.vertical_slice.evaluate(
        cell,
        ecm,
        ecm_internal_z=shifted,
        reject_penetration=False,
    )
    assert first.energies["ecm_viscoelastic"] != pytest.approx(
        second.energies["ecm_viscoelastic"],
        abs=1.0e-15,
    )
    assert model.vertical_slice.ecm_internal_z is None
