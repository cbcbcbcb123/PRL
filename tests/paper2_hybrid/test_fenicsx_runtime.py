from __future__ import annotations

from paper2_hybrid.model import build_system
from paper2_hybrid.numerics import endpoint_structural_gate, simulate_endpoint
from paper2_hybrid.validation import (
    global_structural_checks,
    interface_action_reaction_manufactured_check,
)


def test_active_architecture_assembly_and_endpoint() -> None:
    system = build_system(spatial_label="S2", active_profile="uniform")
    checks = global_structural_checks(system)
    assert all(record["pass"] for record in checks.values())
    assert interface_action_reaction_manufactured_check()["pass"] is True

    endpoint = simulate_endpoint(system=system, case_id="A2", steps_per_cycle=64)
    structural = endpoint_structural_gate(endpoint.summary)
    assert structural["pass"] is True
    assert endpoint.summary["tissue_roles"] == system.roles.manifest()
    assert "representation" not in endpoint.summary
    assert "passive_dcm_scale" not in endpoint.summary
    assert "active_dcm_scale" not in endpoint.summary
