"""Seal the Stage 1 v02 passive kernel after ordered-sum repair."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FROZEN_AT = "2026-07-30T21:06:00+08:00"

FROZEN_PATHS = [
    ".gitignore",
    "README.md",
    "pyproject.toml",
    "data/route_h/route_h_cases_v05.json",
    "data/route_h/route_h_reference_geometry_spec_v05.json",
    "docs/route_h/route_h_coordinate_and_sign_convention_v05.md",
    "docs/route_h/route_h_port_and_power_ledger_v05.csv",
    "project_control/route_h_stage0_v05_freeze_record.md",
    "project_control/route_h_stage0_v05_readonly_scientific_review_v01.md",
    "project_control/route_h_stage0_v05_revision_execution_log.md",
    "project_control/route_h_stage1_authorization_decision_v01.md",
    "project_control/route_h_stage1_execution_log_v01.md",
    "project_control/route_h_stage1_freeze_manifest_v01.json",
    "project_control/route_h_stage1_freeze_record_v01.md",
    "project_control/route_h_stage1_readonly_scientific_code_review_v01.md",
    "project_control/route_h_stage1_scope_disposition_v01.md",
    "project_control/route_h_stage1_v02_revision_execution_log.md",
    "scripts/route_h_stage0_v05_tie_erratum.py",
    "scripts/route_h_stage1_freeze.py",
    "scripts/route_h_stage1_freeze_v02.py",
    "scripts/route_h_stage1_verification_evidence.py",
    "scripts/route_h_stage1_verification_evidence_v02.py",
    "src/route_h/__init__.py",
    "src/route_h/contact_adhesion.py",
    "src/route_h/contracts.py",
    "src/route_h/coupling.py",
    "src/route_h/dcm_cell.py",
    "src/route_h/ecm_finite_strain.py",
    "src/route_h/gauge.py",
    "src/route_h/geometry.py",
    "src/route_h/ledger.py",
    "src/route_h/loads.py",
    "src/route_h/route_h_contract_v05.json",
    "src/route_h/route_h_model_specialization_v05.json",
    "src/route_h/solver.py",
    "tests/route_h/route_h_verification_registry_v05.csv",
    "tests/route_h/stage1_metrics_v02.json",
    "tests/route_h/stage1_pytest_junit_v02.xml",
    "tests/route_h/stage1_verification_results_v02.csv",
    "tests/stage1/conftest.py",
    "tests/stage1/test_contact_adhesion.py",
    "tests/stage1/test_dcm_ecm.py",
    "tests/stage1/test_loads_ledger_guards.py",
    "tests/stage1/test_reference_bundle.py",
]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def main() -> None:
    bundle_dir = ROOT / "data/route_h/stage1_reference_bundle_v01"
    paths = FROZEN_PATHS + [
        str(path.relative_to(ROOT)).replace("\\", "/")
        for path in sorted(bundle_dir.iterdir(), key=lambda item: item.name)
        if path.is_file()
    ]
    if len(paths) != len(set(paths)):
        raise RuntimeError("duplicate path in Stage 1 v02 freeze set")
    missing = [path for path in paths if not (ROOT / path).is_file()]
    if missing:
        raise RuntimeError(f"missing Stage 1 v02 freeze artifact(s): {missing}")
    entries = [
        {
            "path": path,
            "bytes": (ROOT / path).stat().st_size,
            "sha256": sha256(ROOT / path),
        }
        for path in sorted(paths)
    ]
    package_payload = b"".join(
        f"{entry['path']}\0{entry['sha256']}\n".encode("utf-8")
        for entry in entries
    )
    manifest = {
        "freeze_id": "FREEZE-PRL-ROUTE-H-STAGE1-V02",
        "status": "frozen_pending_readonly_inspection",
        "frozen_at": FROZEN_AT,
        "supersedes": "FREEZE-PRL-ROUTE-H-STAGE1-V01",
        "resolved_finding": "S1V01-WINDING-SUM-ORDER-001",
        "contract_id": "CONTRACT-PRL-ROUTE-H-STAGE0-V05",
        "bundle_id": "REFERENCE-BUNDLE-PRL-ROUTE-H-STAGE1-V01",
        "bundle_sha256": "4A73D370162D8EBFB7B120C42881F7470D68E82D10ABD159CB65C2B73ADECC59",
        "hash_algorithm": "SHA-256",
        "file_count": len(entries),
        "files": entries,
        "package_sha256": hashlib.sha256(package_payload).hexdigest().upper(),
        "verification": {
            "pytest_passed": 32,
            "pytest_failed": 0,
            "registry_passed": 37,
            "registry_authorization_correct_not_run": 3,
        },
        "authorization_boundary": {
            "active_enabled": False,
            "full_patch_trajectory_run": False,
            "stage2_authorized": False,
        },
    }
    manifest_path = ROOT / "project_control/route_h_stage1_freeze_manifest_v02.json"
    manifest_path.write_bytes(
        (json.dumps(manifest, ensure_ascii=False, indent=2, allow_nan=False) + "\n").encode("utf-8")
    )
    manifest_hash = sha256(manifest_path)
    record = f"""# Route H Stage 1 v02 冻结记录

## 1. 冻结结论

- freeze ID：`FREEZE-PRL-ROUTE-H-STAGE1-V02`
- frozen at：`{FROZEN_AT}`
- status：`frozen_pending_readonly_inspection`
- supersedes：`FREEZE-PRL-ROUTE-H-STAGE1-V01`
- resolved：`S1V01-WINDING-SUM-ORDER-001`
- contract：`CONTRACT-PRL-ROUTE-H-STAGE0-V05`
- unchanged reference bundle：
  `4A73D370162D8EBFB7B120C42881F7470D68E82D10ABD159CB65C2B73ADECC59`
- frozen files：{len(entries)}
- package SHA-256：`{manifest["package_sha256"]}`
- manifest SHA-256：`{manifest_hash}`

完整逐文件 hash 位于 `project_control/route_h_stage1_freeze_manifest_v02.json`。

## 2. v02 修订

Generalized winding number 的 solid angles 现按 ascending face ID 使用显式
`numpy.float64` scalar accumulator 逐项相加；不使用 pairwise reduction。

对抗回归：

- sequential result：0；
- NumPy pairwise result：986；
- test：passed。

## 3. 冻结状态

- pytest：32/32 passed；
- Ruff：passed；
- Stage 1 registry：37 passed，3 authorization-correct not-run；
- proper intersections：0；
- reference steric energy：0；
- active/full-patch/Stage 2：均未启用或授权。

## 4. 不变性

manifest 中任一文件变化即使本冻结失效。任何 active、trajectory、time/space
refinement、参数、几何、contact/load 或 claim 变化均需新授权/新版本。

下一步只允许新增 v02 冻结后只读 inspection。
"""
    record_path = ROOT / "project_control/route_h_stage1_freeze_record_v02.md"
    record_path.write_bytes(record.encode("utf-8"))
    print(json.dumps({
        "file_count": len(entries),
        "package_sha256": manifest["package_sha256"],
        "manifest_sha256": manifest_hash,
        "freeze_record_sha256": sha256(record_path),
    }, indent=2))


if __name__ == "__main__":
    main()
