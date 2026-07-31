"""Freeze Stage 0 v06 v02 with checkout-stable LF/binary attributes."""

from __future__ import annotations

import csv
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
from typing import Any
import xml.etree.ElementTree as ET


ROOT = Path(__file__).resolve().parents[1]
FROZEN_AT = "2026-07-31T10:26:00+08:00"
MANIFEST_PATH = (
    ROOT / "project_control/route_h_stage0_v06_freeze_manifest_v02.json"
)
RECORD_PATH = ROOT / "project_control/route_h_stage0_v06_freeze_record_v02.md"


def load_v01_module():
    path = ROOT / "scripts/route_h_stage0_v06_freeze.py"
    specification = importlib.util.spec_from_file_location("v06_freeze_v01", path)
    if specification is None or specification.loader is None:
        raise RuntimeError("cannot load v06 v01 freeze module")
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    return module


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def relative(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def validate_v02_junit() -> dict[str, int]:
    path = ROOT / "tests/route_h/stage0_v06_pytest_junit_v02.xml"
    root = ET.parse(path).getroot()
    suite = root if root.tag == "testsuite" else root.find("testsuite")
    if suite is None:
        raise RuntimeError("v02 JUnit has no testsuite")
    observed = {
        "tests": int(suite.attrib["tests"]),
        "failures": int(suite.attrib["failures"]),
        "errors": int(suite.attrib["errors"]),
        "skipped": int(suite.attrib["skipped"]),
    }
    expected = {"tests": 11, "failures": 0, "errors": 0, "skipped": 0}
    if observed != expected:
        raise RuntimeError(f"unexpected v02 JUnit status: {observed}")
    return observed


def validate_line_endings_and_attributes(paths: list[Path]) -> dict[str, int]:
    text_suffixes = {".json", ".md", ".csv", ".txt", ".py", ".toml", ".xml"}
    text_paths = [
        path
        for path in paths
        if path.name == ".gitattributes" or path.suffix.lower() in text_suffixes
    ]
    carriage_returns = [
        relative(path)
        for path in text_paths
        if b"\r" in path.read_bytes()
    ]
    if carriage_returns:
        raise RuntimeError(
            "non-LF frozen text files: " + ", ".join(carriage_returns)
        )
    command = [
        "git",
        "check-attr",
        "text",
        "eol",
        "--",
        *[relative(path) for path in paths],
    ]
    result = subprocess.run(
        command,
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    attributes: dict[str, dict[str, str]] = {}
    for line in result.stdout.splitlines():
        path, attribute, value = line.rsplit(": ", 2)
        attributes.setdefault(path, {})[attribute] = value
    bad_text = [
        relative(path)
        for path in text_paths
        if attributes.get(relative(path), {}).get("text") != "set"
        or attributes.get(relative(path), {}).get("eol") != "lf"
    ]
    if bad_text:
        raise RuntimeError(
            "frozen text missing text/eol=lf attributes: " + ", ".join(bad_text)
        )
    binary_paths = [path for path in paths if path.suffix.lower() == ".bin"]
    bad_binary = [
        relative(path)
        for path in binary_paths
        if attributes.get(relative(path), {}).get("text") != "unset"
    ]
    if bad_binary:
        raise RuntimeError(
            "frozen binary missing -text attribute: " + ", ".join(bad_binary)
        )
    return {
        "LF_text_files": len(text_paths),
        "binary_minus_text_files": len(binary_paths),
        "carriage_return_violations": 0,
        "attribute_violations": 0,
    }


def main() -> None:
    v01 = load_v01_module()
    metrics, results = v01.validate_evidence()
    junit = validate_v02_junit()
    paths = list(v01.required_paths())
    paths.extend(
        [
            ROOT / ".gitattributes",
            ROOT
            / "project_control/route_h_stage0_v06_freeze_manifest_v01.json",
            ROOT / "project_control/route_h_stage0_v06_freeze_record_v01.md",
            ROOT
            / "project_control/"
            "route_h_stage0_v06_readonly_scientific_code_review_v01.md",
            ROOT
            / "project_control/route_h_stage0_v06_v02_revision_execution_log.md",
            ROOT / "scripts/route_h_stage0_v06_freeze_v02.py",
            ROOT / "tests/route_h/stage0_v06_pytest_junit_v02.xml",
        ]
    )
    paths = sorted(set(paths), key=relative)
    missing = [relative(path) for path in paths if not path.is_file()]
    if missing:
        raise RuntimeError("missing v02 freeze inputs: " + ", ".join(missing))
    eol_audit = validate_line_endings_and_attributes(paths)
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
    family = json.loads(
        (
            ROOT / "data/route_h/stage0_v06_discretization_family/manifest.json"
        ).read_text(encoding="utf-8")
    )
    with (
        ROOT / "tests/route_h/stage0_v06_verification_results_v01.csv"
    ).open("r", encoding="utf-8", newline="") as stream:
        result_rows = list(csv.DictReader(stream))
    status_counts = {
        status: sum(row["terminal_status"] == status for row in result_rows)
        for status in sorted({row["terminal_status"] for row in result_rows})
    }
    direct_inputs = [
        ".gitattributes",
        "project_control/route_h_stage0_v06_freeze_manifest_v01.json",
        "project_control/route_h_stage0_v06_freeze_record_v01.md",
        "project_control/route_h_stage0_v06_readonly_scientific_code_review_v01.md",
        "project_control/route_h_stage0_v06_v02_revision_execution_log.md",
    ]
    manifest: dict[str, Any] = {
        "freeze_id": "FREEZE-PRL-ROUTE-H-STAGE0-V06-V02",
        "frozen_at": FROZEN_AT,
        "status": "frozen_pending_readonly_inspection",
        "contract_id": "CONTRACT-PRL-ROUTE-H-STAGE0-V06",
        "geometry_family_id": (
            "DISCRETIZATION-FAMILY-PRL-ROUTE-H-STAGE0-V06"
        ),
        "supersedes": "FREEZE-PRL-ROUTE-H-STAGE0-V06",
        "resolved_finding": "V06-EOL-SEAL-001",
        "files": files,
        "file_count": len(files),
        "package_sha256": hashlib.sha256(seal_payload).hexdigest().upper(),
        "family_sha256": family["family_sha256"],
        "base_array_reuse": family["base_reuse"],
        "scientific_metrics_source": {
            "path": "tests/route_h/stage0_v06_metrics_v01.json",
            "sha256": sha256(
                ROOT / "tests/route_h/stage0_v06_metrics_v01.json"
            ),
            "unchanged_from_v01_scientific_freeze": True,
        },
        "v02_pytest": junit,
        "v02_junit_sha256": sha256(
            ROOT / "tests/route_h/stage0_v06_pytest_junit_v02.xml"
        ),
        "deterministic_replay_sha256": sha256(
            ROOT / "tests/route_h/stage0_v06_replay_results_v01.json"
        ),
        "line_ending_audit": eol_audit,
        "registry_terminal_status_counts": status_counts,
        "stage2_scientific_runs_before_freeze": 0,
        "direct_inputs": [
            {"path": path, "sha256": sha256(ROOT / path)}
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
    record = f"""# Route H Stage 0 v06 v02 冻结记录

## 冻结结论

- freeze ID：`{manifest['freeze_id']}`
- frozen at：`{FROZEN_AT}`
- status：`frozen_pending_readonly_inspection`
- supersedes：`FREEZE-PRL-ROUTE-H-STAGE0-V06`
- resolved：`V06-EOL-SEAL-001`
- frozen files：{manifest['file_count']}
- package SHA-256：`{manifest['package_sha256']}`
- manifest SHA-256：`{manifest_sha}`
- family SHA-256：`{manifest['family_sha256']}`
- v05 base 22 arrays byte exact：`true`
- Stage 2 scientific runs before freeze：`0`

## v02 修订

Python、TOML、XML 与 `.gitattributes` 现全部由 Git attribute 固定为 LF；
binary `.bin` 全部固定为 `-text`。v02 freeze 的全部文本文件 carriage-return
违规数为 0，attribute 违规数为 0。

## 证据

- v02 pytest：{junit['tests']}/{junit['tests']} passed；
- Stage 1 regression：32/32 passed；
- deterministic replay：66/66 arrays byte exact；
- v01 scientific metrics：hash 不变并由 v02 重新封存；
- coarse/base/fine proper intersections：0 / 0 / 0；
- coarse/base/fine steric energy：0 / 0 / 0；
- registry：86 passed，4 `not_run_stage2_preexecution`。

## 不变性

v02 只修复跨-checkout byte stability；v06 v01 scientific geometry、binary arrays、
contract、parameters、reference metrics 和 Stage 2 authorization boundary 均未改变。
本记录不宣告 Stage 2 任一 gate 通过。
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
                "line_ending_audit": eol_audit,
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
