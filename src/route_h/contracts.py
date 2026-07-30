"""Frozen-input checks and execution guards for Route H."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


STAGE0_CONTRACT_ID = "CONTRACT-PRL-ROUTE-H-STAGE0-V05"
STAGE1_BUNDLE_ID = "REFERENCE-BUNDLE-PRL-ROUTE-H-STAGE1-V01"

_FROZEN_SHA256 = {
    "data/route_h/route_h_reference_geometry_spec_v05.json":
        "45A1BE59D412B0816A4AB0BF15F4D6C37CF93F58D13CF584A22824CB032C9CFA",
    "src/route_h/route_h_contract_v05.json":
        "7CE576EF1ABB321256A8AC7736934BDE7901DA553251386E56A2F0E64AFE0B06",
    "src/route_h/route_h_model_specialization_v05.json":
        "290B31015913E2A9EBE1B577CF488925EBCD715B15A79B196ABE8782ED154F16",
    "data/route_h/route_h_cases_v05.json":
        "F0523D9BA882EA10BF1D9B80607FE1AF064E8810198E01882AA180F3C6150B65",
    "docs/route_h/route_h_coordinate_and_sign_convention_v05.md":
        "55AB293795DFE5DB89524B364034C06DD1B7A65C999A04E7D0EED5BF953855C0",
    "docs/route_h/route_h_port_and_power_ledger_v05.csv":
        "7A6CA70C084013F949BB761EC741FA11EC0884859FCF09CF71CFBBACC38C4189",
    "tests/route_h/route_h_verification_registry_v05.csv":
        "6A0C2279F249B2F0604086AB80AAB09137D04F42FEC66BDECB5A5F6C5F4A1DDA",
    "project_control/route_h_stage0_v05_revision_execution_log.md":
        "AD4932F3E2A59DF3B9141AE65CDE905A4D5F5B808C0A6ED7835DB0C627CFC54D",
}


def repository_root() -> Path:
    return Path(__file__).resolve().parents[2]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def assert_stage0_inputs(root: Path | None = None) -> dict[str, str]:
    """Stop before computation if any frozen Stage 0 v04 input changed."""
    base = repository_root() if root is None else Path(root)
    observed: dict[str, str] = {}
    mismatches: list[str] = []
    for relative, expected in _FROZEN_SHA256.items():
        path = base / relative
        actual = sha256_file(path) if path.is_file() else "MISSING"
        observed[relative] = actual
        if actual != expected:
            mismatches.append(f"{relative}: expected {expected}, observed {actual}")
    if mismatches:
        raise RuntimeError("Frozen Stage 0 input mismatch:\n" + "\n".join(mismatches))
    return observed


def load_json(relative_path: str, root: Path | None = None) -> dict[str, Any]:
    base = repository_root() if root is None else Path(root)
    with (base / relative_path).open("r", encoding="utf-8") as stream:
        return json.load(stream)


def load_stage0(root: Path | None = None) -> tuple[dict[str, Any], ...]:
    assert_stage0_inputs(root)
    return (
        load_json("src/route_h/route_h_contract_v05.json", root),
        load_json("src/route_h/route_h_model_specialization_v05.json", root),
        load_json("data/route_h/route_h_reference_geometry_spec_v05.json", root),
        load_json("data/route_h/route_h_cases_v05.json", root),
    )


def require_passive_stage1(*, active: bool = False, full_patch_trajectory: bool = False) -> None:
    """Enforce the authorization boundary at every public solver entry."""
    if active:
        raise PermissionError("Active contraction is Stage 2 and is not authorized.")
    if full_patch_trajectory:
        raise PermissionError("Full-patch trajectories are not authorized in Stage 1.")
