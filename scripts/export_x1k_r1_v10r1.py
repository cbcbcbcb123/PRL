from __future__ import annotations

import argparse
import json
from pathlib import Path

from hybrid.r1_midpoint_packaging_repair import export_v10r1_package


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Export the append-only X1-K v10r1 packaging repair"
    )
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    summary = export_v10r1_package(
        args.repo_root.resolve(),
        args.output_dir.resolve(),
    )
    print(json.dumps(summary, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
