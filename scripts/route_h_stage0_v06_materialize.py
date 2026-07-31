"""Materialize and deterministically replay the Stage 0 v06 geometry family."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np

from route_h.contracts import repository_root
from route_h.discretization import (
    FAMILY_DIRECTORY,
    LEVELS,
    load_discretization_level,
    materialize_discretization_family,
    regenerate_discretization_level,
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def verify_replay() -> dict[str, object]:
    root = repository_root()
    level_results = []
    for level in LEVELS:
        sealed, _ = load_discretization_level(level.name)
        regenerated, _ = regenerate_discretization_level(level.name)
        unequal = [
            name
            for name in sorted(sealed)
            if not np.array_equal(sealed[name], regenerated[name])
        ]
        level_results.append(
            {
                "level": level.name,
                "array_count": len(sealed),
                "unequal_arrays": unequal,
                "passed": not unequal,
            }
        )
    result: dict[str, object] = {
        "evidence_id": "EVIDENCE-PRL-ROUTE-H-STAGE0-V06-REPLAY-V01",
        "family_manifest": str((FAMILY_DIRECTORY / "manifest.json").as_posix()),
        "family_manifest_sha256": sha256(root / FAMILY_DIRECTORY / "manifest.json"),
        "levels": level_results,
        "passed": all(bool(level["passed"]) for level in level_results),
    }
    evidence_path = root / "tests/route_h/stage0_v06_replay_results_v01.json"
    evidence_path.write_bytes(
        (json.dumps(result, ensure_ascii=False, indent=2) + "\n").encode()
    )
    if not result["passed"]:
        raise RuntimeError("v06 deterministic replay failed")
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--verify-only",
        action="store_true",
        help="Verify the existing family without rematerializing it.",
    )
    arguments = parser.parse_args()
    output: dict[str, object] = {}
    if not arguments.verify_only:
        manifest = materialize_discretization_family()
        output["family_sha256"] = manifest["family_sha256"]
        output["family_levels"] = [record["name"] for record in manifest["levels"]]
    output["replay"] = verify_replay()
    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
