"""Freeze the verified Stage 0 v06 spatial-discretization family."""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
FROZEN_AT = "2026-07-31T10:15:00+08:00"
MANIFEST_PATH = (
    ROOT / "project_control/route_h_stage0_v06_freeze_manifest_v01.json"
)
RECORD_PATH = ROOT / "project_control/route_h_stage0_v06_freeze_record_v01.md"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def relative(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def required_paths() -> list[Path]:
    paths = [
        ROOT / "pyproject.toml",
        ROOT
        / "project_control/route_h_stage2_preflight_discretization_block_v01.md",
        ROOT
        / "project_control/"
        "route_h_stage0_v06_discretization_authorization_decision_v01.md",
        ROOT
        / "project_control/route_h_stage0_v06_revision_execution_log_v01.md",
        ROOT
        / "data/route_h/route_h_spatial_discretization_family_v06.json",
        ROOT / "data/route_h/route_h_cases_v06.json",
        ROOT
        / "docs/route_h/route_h_spatial_discretization_protocol_v06.md",
        ROOT / "src/route_h/geometry.py",
        ROOT / "src/route_h/discretization.py",
        ROOT / "src/route_h/solver.py",
        ROOT / "src/route_h/route_h_contract_v06.json",
        ROOT / "src/route_h/route_h_model_specialization_v06.json",
        ROOT / "scripts/route_h_stage0_v06_artifacts.py",
        ROOT / "scripts/route_h_stage0_v06_materialize.py",
        ROOT / "scripts/route_h_stage0_v06_verification_evidence.py",
        ROOT / "scripts/route_h_stage0_v06_freeze.py",
        ROOT / "tests/route_h/route_h_verification_registry_v06.csv",
        ROOT / "tests/route_h/stage0_v06_pytest_junit_v01.xml",
        ROOT / "tests/route_h/stage0_v06_replay_results_v01.json",
        ROOT / "tests/route_h/stage0_v06_metrics_v01.json",
        ROOT / "tests/route_h/stage0_v06_verification_results_v01.csv",
        ROOT / "tests/stage0_v06/conftest.py",
        ROOT / "tests/stage0_v06/test_discretization_family.py",
    ]
    family_root = ROOT / "data/route_h/stage0_v06_discretization_family"
    paths.extend(
        path
        for path in sorted(family_root.rglob("*"))
        if path.is_file()
    )
    return sorted(set(paths), key=relative)


def validate_evidence() -> tuple[dict[str, Any], list[dict[str, str]]]:
    metrics = json.loads(
        (
            ROOT / "tests/route_h/stage0_v06_metrics_v01.json"
        ).read_text(encoding="utf-8")
    )
    if metrics["pytest"] != {
        "tests": 11,
        "failures": 0,
        "errors": 0,
        "skipped": 0,
    }:
        raise RuntimeError(f"unexpected v06 pytest status: {metrics['pytest']}")
    authorization = metrics["authorization"]
    if authorization["stage2_scientific_runs_before_v06_freeze"] != 0:
        raise RuntimeError("Stage 2 scientific execution occurred before v06 freeze")
    if (
        authorization["active_enabled_during_v06"]
        or authorization["full_patch_trajectory_run_during_v06"]
        or authorization["periodic_registered"]
    ):
        raise RuntimeError("v06 authorization boundary was violated")
    for level_name, level in metrics["levels"].items():
        checks = {
            "triangle quality": level["minimum_cell_triangle_quality"] >= 0.30,
            "cell volume": level["minimum_cell_signed_volume"] > 0.0,
            "anchor length": level["minimum_anchor_length"] >= 0.80,
            "tet determinant": level["minimum_reference_tetra_determinant"] > 0.0,
            "ECM J": level["minimum_ECM_J"] > 0.0,
            "steric energy": level["steric_energy"] == 0.0,
            "proper intersections": level["proper_intersections"] == 0,
            "tether opening": level["maximum_tether_opening"] < 1e-12,
            "tether slip": level["maximum_tether_slip"] < 1e-12,
            "tether force": level["maximum_tether_force"] < 1e-10,
            "net force": level["assembled_net_force"] < 1e-10,
            "net moment": level["assembled_net_moment"] < 1e-10,
            "cell force": level["maximum_cell_force"] < 1e-12,
            "ECM force": level["maximum_ECM_force"] < 1e-12,
        }
        failed = [name for name, passed in checks.items() if not passed]
        if failed:
            raise RuntimeError(
                f"v06 {level_name} reference seal failed: {', '.join(failed)}"
            )
    family = json.loads(
        (
            ROOT / "data/route_h/stage0_v06_discretization_family/manifest.json"
        ).read_text(encoding="utf-8")
    )
    if not family["base_reuse"]["all_22_arrays_byte_exact"]:
        raise RuntimeError("v06 base reuse is not byte exact")
    replay = json.loads(
        (
            ROOT / "tests/route_h/stage0_v06_replay_results_v01.json"
        ).read_text(encoding="utf-8")
    )
    if not replay["passed"]:
        raise RuntimeError("v06 deterministic replay did not pass")
    with (
        ROOT / "tests/route_h/stage0_v06_verification_results_v01.csv"
    ).open("r", encoding="utf-8", newline="") as stream:
        results = list(csv.DictReader(stream))
    required_pass = {
        "AUTH-STAGE2-GATE",
        "SPACE-FAMILY-SPEC",
        "STAGE2-DISCRETIZATION-SEAL",
        "SPACE-LEVEL-COUNTS",
        "SPACE-BASE-BYTE-REUSE",
        "SPACE-GEOMETRY-VALIDITY",
        "SPACE-MAP-COVERAGE",
        "SPACE-DETERMINISTIC-REPLAY",
        "SPACE-REFERENCE-SEAL",
        "SPACE-FLOAT-INTERFACE-SNAP",
    }
    observed_pass = {
        row["test_id"]
        for row in results
        if row["terminal_status"] == "passed"
    }
    if not required_pass <= observed_pass:
        raise RuntimeError(
            "v06 required registry rows did not pass: "
            + ", ".join(sorted(required_pass - observed_pass))
        )
    spatial = next(row for row in results if row["test_id"] == "SPACE-REFINEMENT")
    if spatial["terminal_status"] != "not_run_stage2_preexecution":
        raise RuntimeError("Stage 2 spatial response was incorrectly promoted")
    return metrics, results


def main() -> None:
    metrics, results = validate_evidence()
    paths = required_paths()
    missing = [relative(path) for path in paths if not path.is_file()]
    if missing:
        raise RuntimeError("missing v06 freeze inputs: " + ", ".join(missing))
    files = [
        {
            "path": relative(path),
            "bytes": path.stat().st_size,
            "sha256": sha256(path),
        }
        for path in paths
    ]
    seal_payload = b"".join(
        f"{record['path']}\0{record['sha256']}\n".encode()
        for record in files
    )
    direct_inputs = [
        "src/route_h/route_h_contract_v05.json",
        "data/route_h/route_h_reference_geometry_spec_v05.json",
        "project_control/route_h_stage1_freeze_record_v02.md",
        "project_control/route_h_stage1_readonly_scientific_code_review_v02.md",
        "project_control/route_h_stage1_acceptance_decision_v01.md",
        "project_control/route_h_stage2_authorization_decision_v01.md",
    ]
    family = json.loads(
        (
            ROOT / "data/route_h/stage0_v06_discretization_family/manifest.json"
        ).read_text(encoding="utf-8")
    )
    status_counts = {
        status: sum(row["terminal_status"] == status for row in results)
        for status in sorted({row["terminal_status"] for row in results})
    }
    manifest: dict[str, Any] = {
        "freeze_id": "FREEZE-PRL-ROUTE-H-STAGE0-V06",
        "frozen_at": FROZEN_AT,
        "status": "frozen_pending_readonly_inspection",
        "contract_id": "CONTRACT-PRL-ROUTE-H-STAGE0-V06",
        "geometry_family_id": (
            "DISCRETIZATION-FAMILY-PRL-ROUTE-H-STAGE0-V06"
        ),
        "supersedes_for_future_work": "FREEZE-PRL-ROUTE-H-STAGE0-V05",
        "files": files,
        "file_count": len(files),
        "package_sha256": hashlib.sha256(seal_payload).hexdigest().upper(),
        "family_sha256": family["family_sha256"],
        "base_array_reuse": family["base_reuse"],
        "pytest": metrics["pytest"],
        "registry_terminal_status_counts": status_counts,
        "stage2_scientific_runs_before_freeze": 0,
        "direct_inputs": [
            {
                "path": path,
                "sha256": sha256(ROOT / path),
            }
            for path in direct_inputs
        ],
        "authorization_boundary": {
            "v06_spatial_family_materialized": True,
            "Stage2_response_run": False,
            "active_enabled": False,
            "periodic_registered": False,
            "parameter_sweep_run": False,
        },
    }
    MANIFEST_PATH.write_bytes(
        (json.dumps(manifest, ensure_ascii=False, indent=2) + "\n").encode()
    )
    manifest_sha = sha256(MANIFEST_PATH)
    level_rows = "\n".join(
        (
            f"| {name} | {level['vertices_per_cell']} / "
            f"{level['faces_per_cell']} | {level['ecm_vertices']} / "
            f"{level['ecm_tetrahedra']} | "
            f"{level['minimum_cell_triangle_quality']:.12g} | "
            f"{level['minimum_reference_tetra_determinant']:.12g} | "
            f"{level['assembled_net_force']:.3e} | "
            f"{level['assembled_net_moment']:.3e} |"
        )
        for name, level in metrics["levels"].items()
    )
    record = f"""# Route H Stage 0 v06 空间离散族冻结记录

## 冻结结论

- freeze ID：`{manifest['freeze_id']}`
- frozen at：`{FROZEN_AT}`
- status：`frozen_pending_readonly_inspection`
- contract：`{manifest['contract_id']}`
- frozen files：{manifest['file_count']}
- package SHA-256：`{manifest['package_sha256']}`
- manifest SHA-256：`{manifest_sha}`
- family SHA-256：`{manifest['family_sha256']}`
- v05 base 22 arrays byte exact：`true`
- Stage 2 scientific runs before freeze：`0`

## 三层 reference seal

| level | cell V/F | ECM V/T | min cell quality | min det(Dm) | net force | net moment |
|---|---:|---:|---:|---:|---:|---:|
{level_rows}

三层均满足：cell watertight/orientation/positive volume、ECM positive tetra、
material/source/owner/gauge coverage、passive reference force、material pair force/moment、
zero steric energy、零 proper intersection 和 deterministic replay。

## coarse geometry admission

v06 冻结 `0.075` 作为 cell–ECM reference tether 的 geometry-only materialization
ceiling；coarse 实测最大 `g0_pair=0.06348416662201481`。该 ceiling 不进入任何
energy、force、power 或 solver；每对 tether 仍使用自身封存的 `g0_pair`。

## 注册状态

`STAGE2-DISCRETIZATION-SEAL` 已通过，原 PreStage2 阻断可以在只读检查接受后关闭。
`SPACE-REFINEMENT` 仍为 `not_run_stage2_preexecution`：v06 只封存 family 和阈值，
没有提前运行 E0/E4 响应。

## 不变性

任一 manifest 内文件变化都会使本冻结失效。v01–v05、Stage 1 v02、力学方程、
无量纲参数、接触/黏附势、载荷、功率账本、periodic 排除和 Gate A–E 顺序均未改变。
本记录不宣告 Stage 2 任一 gate 通过，也不形成生理或论文结论。
"""
    RECORD_PATH.write_bytes(record.encode())
    print(
        json.dumps(
            {
                "freeze_manifest": relative(MANIFEST_PATH),
                "manifest_sha256": manifest_sha,
                "freeze_record": relative(RECORD_PATH),
                "freeze_record_sha256": sha256(RECORD_PATH),
                "package_sha256": manifest["package_sha256"],
                "file_count": manifest["file_count"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
