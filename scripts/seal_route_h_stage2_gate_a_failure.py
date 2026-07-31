"""Create the deterministic failed Gate A evidence manifest."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_PATH = (
    REPOSITORY_ROOT
    / "project_control/route_h_stage2_gate_a_failure_manifest_v01.json"
)
EVIDENCE_PATHS = (
    ".gitattributes",
    "project_control/route_h_stage2_numerical_method_decision_v01.md",
    "project_control/route_h_stage2_numerical_method_decision_v02.md",
    "project_control/route_h_stage2_gate_a_execution_log_v01.md",
    "project_control/route_h_stage2_gate_a_readonly_scientific_code_review_v01.md",
    "src/route_h/dcm_cell.py",
    "src/route_h/activation.py",
    "src/route_h/stage2_gate_a.py",
    "src/route_h/solver.py",
    "scripts/run_route_h_stage2_gate_a.py",
    "scripts/verify_route_h_stage2_gate_a.py",
    "scripts/seal_route_h_stage2_gate_a_failure.py",
    "tests/stage1/test_dcm_vectorized_equivalence.py",
    "tests/stage2/test_gate_a_activation.py",
    "tests/route_h/stage2_gate_a_manufactured_metrics_v01.json",
    "tests/route_h/stage2_gate_a_pytest_junit_v01.xml",
    "tests/route_h/stage2_gate_a_verification_results_v01.csv",
    "tests/route_h/route_h_verification_registry_v07.csv",
    "results/route_h/stage2_gate_a_v01/formal_run_stdout.log",
    "results/route_h/stage2_gate_a_v01/formal_run_stderr.log",
    "results/route_h/stage2_gate_a_v01/gate_a_acceptance.json",
    "results/route_h/stage2_gate_a_v01/A0_ZERO_dt0.01/manifest.json",
    "results/route_h/stage2_gate_a_v01/A0_ZERO_dt0.01/summary.json",
    "results/route_h/stage2_gate_a_v01/A0_ZERO_dt0.01/time_series.csv",
    "results/route_h/stage2_gate_a_v01/A0_ZERO_dt0.01/vertices.bin",
    "src/route_h/route_h_contract_v06.json",
    "src/route_h/route_h_model_specialization_v06.json",
    "data/route_h/stage0_v06_discretization_family/manifest.json",
    "project_control/route_h_stage0_v06_freeze_manifest_v02.json",
)


def _canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def main() -> int:
    records = []
    for relative in EVIDENCE_PATHS:
        payload = (REPOSITORY_ROOT / relative).read_bytes()
        records.append(
            {
                "path": relative,
                "bytes": len(payload),
                "sha256": hashlib.sha256(payload).hexdigest().upper(),
            }
        )
    seal_payload = b"".join(
        f"{record['path']}\0{record['sha256']}\n".encode("utf-8")
        for record in records
    )
    manifest = {
        "manifest_id": "MANIFEST-PRL-ROUTE-H-STAGE2-GATE-A-FAILURE-V01",
        "status": "frozen_failed_gate",
        "gate_id": "A",
        "gate_status": "failed_invalid_numerics",
        "downstream_status": "Gate B-E blocked",
        "effective_contract": "CONTRACT-PRL-ROUTE-H-STAGE0-V06",
        "effective_freeze": "FREEZE-PRL-ROUTE-H-STAGE0-V06-V02",
        "effective_numerical_method": (
            "DEC-PRL-ROUTE-H-STAGE2-NUMERICAL-METHOD-V02"
        ),
        "formal_response_rerun": False,
        "files": records,
        "package_sha256": hashlib.sha256(seal_payload).hexdigest().upper(),
    }
    payload = _canonical_json_bytes(manifest)
    OUTPUT_PATH.write_bytes(payload)
    print(
        json.dumps(
            {
                "manifest": str(OUTPUT_PATH.relative_to(REPOSITORY_ROOT)),
                "manifest_sha256": hashlib.sha256(payload).hexdigest().upper(),
                "package_sha256": manifest["package_sha256"],
                "file_count": len(records),
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
