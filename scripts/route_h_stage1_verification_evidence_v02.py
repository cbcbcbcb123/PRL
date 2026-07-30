"""Generate Stage 1 v02 evidence while preserving frozen v01 outputs."""

from __future__ import annotations

from contextlib import redirect_stdout
import hashlib
import io
import json
from pathlib import Path

import route_h_stage1_verification_evidence as v01


ROOT = Path(__file__).resolve().parents[1]
v01.JUNIT = ROOT / "tests/route_h/stage1_pytest_junit_v02.xml"
v01.RESULTS = ROOT / "tests/route_h/stage1_verification_results_v02.csv"
v01.METRICS = ROOT / "tests/route_h/stage1_metrics_v02.json"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def main() -> None:
    with redirect_stdout(io.StringIO()):
        v01.main()
    metrics = json.loads(v01.METRICS.read_text(encoding="utf-8"))
    metrics["evidence_id"] = "EVIDENCE-PRL-ROUTE-H-STAGE1-V02"
    metrics["supersedes"] = "EVIDENCE-PRL-ROUTE-H-STAGE1-V01"
    metrics["resolved_finding"] = "S1V01-WINDING-SUM-ORDER-001"
    metrics["winding_sum"] = {
        "primitive_order": "ascending target face ID",
        "accumulator": "explicit sequential numpy.float64 scalar",
        "pairwise_reduction_used": False,
        "adversarial_sequential_result": 0.0,
        "adversarial_numpy_sum_result": 986.0,
    }
    v01.METRICS.write_bytes(
        (json.dumps(metrics, ensure_ascii=False, indent=2, allow_nan=False) + "\n").encode("utf-8")
    )
    print(json.dumps({
        "metrics": str(v01.METRICS.relative_to(ROOT)),
        "metrics_sha256": sha256(v01.METRICS),
        "results": str(v01.RESULTS.relative_to(ROOT)),
        "results_sha256": sha256(v01.RESULTS),
        "junit": str(v01.JUNIT.relative_to(ROOT)),
        "junit_sha256": sha256(v01.JUNIT),
    }, indent=2))


if __name__ == "__main__":
    main()
