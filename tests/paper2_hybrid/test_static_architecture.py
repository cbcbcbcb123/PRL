from __future__ import annotations

import ast
import inspect
from pathlib import Path

import pytest

from paper2_hybrid import (
    ACTIVE_CONFIG,
    ACTIVE_PROTOCOL,
    ACTIVE_TISSUE_ROLES,
    TissueRoles,
    endpoint_key,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]
ACTIVE_SOURCE = PROJECT_ROOT / "src" / "paper2_hybrid"


def _source_files() -> list[Path]:
    return sorted(ACTIVE_SOURCE.glob("*.py"))


def test_fixed_tissue_roles_and_cases() -> None:
    assert ACTIVE_TISSUE_ROLES.manifest() == {
        "endocardium": "discrete_cell_chain",
        "myocardium": "active_plane_strain_fem",
        "ecm": "viscoelastic_plane_strain_fem",
        "fluid": "absent_in_v08",
    }
    assert ACTIVE_CONFIG.cases == (
        "P0",
        "P1",
        "A1",
        "A2",
        "LN",
        "LS",
        "C0",
        "CQ",
        "S1",
    )
    assert ACTIVE_PROTOCOL.parity_cases == ("A2", "LN", "LS", "C0", "CQ", "S1")


def test_endpoint_key_has_no_model_axis() -> None:
    assert endpoint_key("A2") == "A2__S4__T64__D0"
    assert tuple(inspect.signature(endpoint_key).parameters) == (
        "case_id",
        "spatial_level",
        "time_level",
        "tolerance_level",
    )
    with pytest.raises(TypeError):
        endpoint_key("A2", representation="DCM")  # type: ignore[call-arg]


def test_invalid_tissue_role_is_rejected() -> None:
    with pytest.raises(ValueError, match="fixed"):
        TissueRoles(myocardium="discrete_network").checked()


def test_active_source_has_no_retired_runtime_symbols_or_imports() -> None:
    forbidden_tokens = (
        "representation",
        "_dcm_network_full",
        "passive_dcm_scale",
        "active_dcm_scale",
        "calibration",
        "go-id",
        "maybe-id",
        "no-go-id",
        "paper2_m2",
    )
    for path in _source_files():
        source = path.read_text(encoding="utf-8")
        lowered = source.lower()
        for token in forbidden_tokens:
            assert token not in lowered, f"{token!r} remains in {path}"
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                assert not (node.module or "").startswith("paper2_m2")
            elif isinstance(node, ast.Import):
                assert all(not name.name.startswith("paper2_m2") for name in node.names)


def test_model_builder_signature_is_fixed_by_static_ast() -> None:
    tree = ast.parse((ACTIVE_SOURCE / "model.py").read_text(encoding="utf-8"))
    function = next(
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name == "build_system"
    )
    keyword_names = tuple(argument.arg for argument in function.args.kwonlyargs)
    assert keyword_names == ("spatial_label", "active_profile", "config")


def test_one_time_runner_does_not_import_retired_python_package() -> None:
    runner = PROJECT_ROOT / "scripts" / "run_paper2_v08_fem_only_parity_v01.py"
    tree = ast.parse(runner.read_text(encoding="utf-8"))
    imports = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            imports.append(node.module or "")
        elif isinstance(node, ast.Import):
            imports.extend(name.name for name in node.names)
    assert all(not name.startswith("paper2_m2") for name in imports)


def test_mainline_v03_retires_old_route_and_has_fem_family_figure4() -> None:
    plan = (
        PROJECT_ROOT / "project_control" / "prl_independent_theory_mainline_plan_v03.md"
    ).read_text(encoding="utf-8")
    assert "retired_historical_evidence" in plan
    figure4 = plan.split("### Figure 4", 1)[1].split("### Figure 5", 1)[0]
    assert "cell/meso-resolved active FEM" in figure4
    assert "homogenized active FEM" in figure4
    assert "心肌 DCM" not in figure4
