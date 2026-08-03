from __future__ import annotations

import json
from pathlib import Path

from hybrid.r1_midpoint_packaging_repair_v10r2 import export_v10r2_package


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = (
    ROOT / "results/hybrid/x1_k_r1_midpoint_collapse_diagnosis_v10r2"
)
REPORT_PATH = (
    ROOT
    / "project_control/"
    "hybrid_x1_k_r1_midpoint_collapse_locator_count_fork_evidence_repair_"
    "report_v10r2.md"
)


def main() -> int:
    summary = export_v10r2_package(ROOT, OUTPUT_DIR, REPORT_PATH)
    print(json.dumps(summary, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
