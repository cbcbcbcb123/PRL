"""Independent checks for the retained terminal-residual diagnosis."""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image

from ..workspace import find_workspace


RESULT_RELATIVE = Path(
    "results/ventricle_z1/z1_myo_terminal_residual_diagnosis_v01_20260915"
)
CASES = ("END_DT0.02", "END_DT0.01", "SIDE_DT0.02", "SIDE_DT0.01")
MODELS = (
    "single_exponential_zero",
    "exponential_floor",
    "double_exponential_zero",
    "shifted_power_zero",
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _bounded_result(workspace: Path, value: Path | str | None) -> Path:
    candidate = workspace / RESULT_RELATIVE if value is None else Path(value)
    if not candidate.is_absolute():
        candidate = workspace / candidate
    resolved = candidate.resolve(strict=True)
    try:
        resolved.relative_to(workspace.resolve(strict=True))
    except ValueError as error:
        raise ValueError("diagnosis result must stay inside the workspace") from error
    return resolved


def _csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream))


def _listed_hashes_match(root: Path, records: list[dict[str, Any]]) -> bool:
    for record in records:
        path = root / record["path"]
        if (
            not path.is_file()
            or path.stat().st_size != record["bytes"]
            or _sha256(path) != record["sha256"]
        ):
            return False
    return True


def verify_terminal_residual_diagnosis(
    workspace: Path | str | None = None,
    result: Path | str | None = None,
) -> dict[str, Any]:
    """Recompute frozen table decisions without importing the diagnostic module."""
    root = find_workspace(workspace)
    target = _bounded_result(root, result)
    diagnosis = json.loads((target / "diagnosis.json").read_text(encoding="utf-8"))
    manifest = json.loads((target / "manifest.json").read_text(encoding="utf-8"))

    source_hashes_match = _listed_hashes_match(root, diagnosis.get("provenance", []))
    manifest_hashes_match = _listed_hashes_match(target, manifest.get("files", []))

    tail = _csv(target / "tail_models.csv")
    indexed = {
        (row["case"], float(row["train_end"]), row["model"]): row for row in tail
    }
    expected = {
        (case, end, model)
        for case in CASES
        for end in (15.0, 17.0)
        for model in MODELS
    }
    tail_complete = set(indexed) == expected
    single_scale_inadequate = tail_complete and all(
        float(indexed[(case, end, "exponential_floor")]["test_rmse"])
        <= 0.25 * float(indexed[(case, end, "single_exponential_zero")]["test_rmse"])
        for case in CASES
        for end in (15.0, 17.0)
    )
    slow_zero_competitive = tail_complete and all(
        float(indexed[(case, end, "double_exponential_zero")]["test_rmse"])
        <= 1.25 * float(indexed[(case, end, "exponential_floor")]["test_rmse"])
        and json.loads(indexed[(case, end, "double_exponential_zero")]["parameters"])[
            "slow_rate"
        ]
        <= 1.0e-4
        for case in CASES
        for end in (15.0, 17.0)
    )
    tail_classification = (
        "unresolved_positive_floor_vs_slow_zero_mode"
        if single_scale_inadequate and slow_zero_competitive
        else "not_resolved_by_frozen_rules"
    )

    components = _csv(target / "component_snapshots.csv")
    terminal = [row for row in components if abs(float(row["coordinate"]) - 20.0) <= 1.0e-8]
    terminal_cases = {row["case"] for row in terminal}
    reconstruction_passed = len(components) == 20 and all(
        float(row["reconstruction_maximum_absolute_error"]) <= 1.0e-12
        and float(row["reconstruction_relative_l2_error"]) <= 1.0e-12
        for row in components
    )
    power_closure = len(components) == 20 and all(
        abs(
            sum(
                float(row[f"{component}_power_fraction"])
                for component in ("skeleton", "surface", "pressure", "contact")
            )
            - 1.0
        )
        <= 1.0e-10
        for row in components
    )
    contact_not_limiting = terminal_cases == set(CASES) and all(
        float(row["maximum_node_contact_force"]) <= 1.0e-12
        and abs(float(row["contact_power_fraction"])) <= 0.02
        for row in terminal
    )
    skeleton_dominant = terminal_cases == set(CASES) and all(
        float(row["skeleton_power_fraction"]) > 0.50 for row in terminal
    )
    endpoint_force_match = terminal_cases == set(CASES)
    source = root / diagnosis["source_result"] / "E"
    for row in terminal:
        states = np.atleast_1d(
            np.genfromtxt(source / row["case"] / "states.csv", delimiter=",", names=True)
        )
        endpoint_force_match = endpoint_force_match and abs(
            float(states["max_free_force"][-1]) - float(row["maximum_total_force"])
        ) <= 1.0e-12

    dimensions: dict[str, list[int]] = {}
    figures_readable = True
    for name in (
        "tail_model_holdout.png",
        "force_component_power.png",
        "terminal_residual_localization.png",
    ):
        try:
            with Image.open(target / "figures" / name) as image:
                image.verify()
            with Image.open(target / "figures" / name) as image:
                dimensions[name] = [image.width, image.height]
                figures_readable = figures_readable and image.width >= 1000 and image.height >= 500
        except (OSError, SyntaxError):
            figures_readable = False

    findings = diagnosis.get("findings", {})
    findings_match = (
        findings.get("single_scale_zero_asymptote_inadequate") is single_scale_inadequate
        and findings.get("slow_zero_mode_competitive_with_positive_floor") is slow_zero_competitive
        and findings.get("tail_classification") == tail_classification
        and findings.get("contact_is_terminal_rate_limiting") is (not contact_not_limiting)
        and findings.get("terminal_power_driver")
        == ("persistent_cytoskeleton_dominant" if skeleton_dominant else "not_resolved")
    )
    checks = {
        "diagnosis_schema": diagnosis.get("schema_version") == "prl.terminal_residual_diagnosis.v1",
        "process_passed_but_science_blocked": diagnosis.get("status") == "passed"
        and diagnosis.get("scientific_status") == "blocked",
        "zero_solver_calls_and_no_gpu": diagnosis.get("solver_calls") == 0
        and diagnosis.get("gpu") is False,
        "source_hashes_match": source_hashes_match,
        "manifest_hashes_match": manifest_hashes_match,
        "tail_table_complete": tail_complete,
        "passive_reconstruction_within_tolerance": reconstruction_passed,
        "component_power_closure": power_closure,
        "terminal_force_matches_source": endpoint_force_match,
        "finding_values_match": findings_match,
        "figures_readable": figures_readable,
        "output_within_16_mib": sum(
            path.stat().st_size for path in target.rglob("*") if path.is_file()
        )
        <= 16 * 1024**2,
    }
    report = {
        "schema_version": "prl.terminal_residual_diagnosis.verification.v1",
        "status": "passed" if all(checks.values()) else "failed",
        "checks": checks,
        "recomputed_findings": {
            "single_scale_zero_asymptote_inadequate": single_scale_inadequate,
            "slow_zero_mode_competitive_with_positive_floor": slow_zero_competitive,
            "tail_classification": tail_classification,
            "contact_is_terminal_rate_limiting": not contact_not_limiting,
            "terminal_power_driver": "persistent_cytoskeleton_dominant"
            if skeleton_dominant
            else "not_resolved",
        },
        "figure_dimensions": dimensions,
        "scope": "independent consistency verification; no solver or scientific re-adjudication",
    }
    verification_path = target / "verification.json"
    if verification_path.exists():
        raise ValueError(f"create-only verification exists: {verification_path}")
    verification_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return report

