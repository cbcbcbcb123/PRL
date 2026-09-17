"""Bounded 5x5 quasistatic doubled-target growth qualification."""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

from ..storage import MIB, evaluate_storage, scan_workspace
from .myocardial_crowded_box import (
    BUILD,
    CONTACT_HEADER,
    CONTACT_SOURCE,
    EXECUTABLE,
    REQUESTED_STEP,
    REQUESTED_STEPS,
    SHRINK_STEPS,
    SOURCE,
    generate_heterogeneity,
    prepare_geometry,
    write_box,
    write_heterogeneity,
    write_mesh,
)
from .myocardial_crowded_target_pair import (
    INITIAL_GAP,
    INITIAL_WALL_MARGIN,
    _call,
    _write_json,
)
from .myocardial_crowded_volume_x2 import (
    AREA_SCALE,
    MAXIMUM_INITIAL_VOLUME_RELATIVE_CHANGE,
    VOLUME_SCALE,
    generate_doubled_reference_targets,
    write_doubled_reference_targets,
)


RESULT = Path(
    "results/ventricle_z1/z1_myo_crowded_quasistatic_growth_v01_20260916"
)
PARENT_RESULT = Path(
    "results/ventricle_z1/z1_myo_crowded_target_pair_v01_20260916"
)
CONTRACT = Path(
    "project_control/ventricle_myocardial_crowded_quasistatic_growth_contract_v01.md"
)
STAGE = "Z1-MYO-CROWD-QUASISTATIC-GROWTH-B"
CONDITIONS = ("QS_COARSE_K30", "QS_REFINED_K30", "QS_REFINED_K15")
CONTROL_COLUMNS = (
    "stage_name",
    "target_start_fraction",
    "target_ramp_steps",
    "contact_maximum_edge",
    "motion_fraction",
    "bulk_modulus_scale",
    "maximum_backtracks",
    "minimum_trial_gap",
    "output_budget_bytes",
)
CONTROL = {
    "QS_COARSE_K30": {
        "contact_maximum_edge": 0.40,
        "motion_fraction": 0.05,
        "bulk_modulus_scale": 1.0,
    },
    "QS_REFINED_K30": {
        "contact_maximum_edge": 0.20,
        "motion_fraction": 0.01,
        "bulk_modulus_scale": 1.0,
    },
    "QS_REFINED_K15": {
        "contact_maximum_edge": 0.20,
        "motion_fraction": 0.01,
        "bulk_modulus_scale": 0.5,
    },
}
TARGET_START_FRACTION = 0.5
TARGET_RAMP_STEPS = 120
MAXIMUM_BACKTRACKS = 12
MINIMUM_TRIAL_GAP = 1.0e-8
PER_CONDITION_OUTPUT_BUDGET = 64 * MIB


def control_record(condition: str) -> dict[str, object]:
    """Return one preregistered runtime-control row."""

    values = CONTROL[condition]
    return {
        "stage_name": STAGE,
        "target_start_fraction": TARGET_START_FRACTION,
        "target_ramp_steps": TARGET_RAMP_STEPS,
        "contact_maximum_edge": values["contact_maximum_edge"],
        "motion_fraction": values["motion_fraction"],
        "bulk_modulus_scale": values["bulk_modulus_scale"],
        "maximum_backtracks": MAXIMUM_BACKTRACKS,
        "minimum_trial_gap": MINIMUM_TRIAL_GAP,
        "output_budget_bytes": PER_CONDITION_OUTPUT_BUDGET,
    }


def write_control(path: Path, condition: str) -> None:
    with path.open("x", newline="", encoding="ascii") as stream:
        writer = csv.DictWriter(stream, fieldnames=CONTROL_COLUMNS)
        writer.writeheader()
        record = control_record(condition)
        writer.writerow(
            {
                key: f"{value:.17g}" if isinstance(value, float) else value
                for key, value in record.items()
            }
        )


def _condition_targets(
    cells: list[object], faces: object, condition: str
) -> list[dict[str, float | int | str]]:
    records = generate_doubled_reference_targets(cells, faces)  # type: ignore[arg-type]
    return [{**record, "condition": condition} for record in records]


def _source_files(root: Path, parent: Path) -> list[Path]:
    return [
        root / CONTRACT,
        root / SOURCE,
        root / CONTACT_SOURCE,
        root / CONTACT_HEADER,
        Path(__file__).resolve(),
        root / "src/prl/verification/myocardial_crowded_quasistatic_growth.py",
        root / "src/prl/rendering/myocardial_crowded_quasistatic_growth.py",
        root / "src/prl/rendering/cb_plot_unified_style.py",
        parent / "initial_cells.mesh",
        parent / "heterogeneity.csv",
        parent / "targets/HETEROGENEOUS_TARGETS.csv",
        parent / "verification.json",
    ]


def _write_source_hashes(root: Path, output: Path, parent: Path) -> None:
    hashes = {
        path.resolve(strict=True).relative_to(root).as_posix(): hashlib.sha256(
            path.resolve(strict=True).read_bytes()
        ).hexdigest()
        for path in _source_files(root, parent)
    }
    _write_json(output / "source_hashes.json", hashes)


def _execute_condition(
    root: Path, output: Path, condition: str
) -> dict[str, object]:
    raw = output / "raw"
    raw.mkdir(exist_ok=True)
    execution = _call(
        root,
        [
            root / EXECUTABLE,
            output / "initial_cells.mesh",
            output / "heterogeneity.csv",
            output / "box_schedule.csv",
            raw / condition,
            REQUESTED_STEP,
            REQUESTED_STEPS,
            SHRINK_STEPS,
            780,
            output / "targets" / f"{condition}.csv",
            output / "controls" / f"{condition}.csv",
        ],
        800,
    )
    _write_json(output / f"execution_{condition}.json", execution)
    return execution


def _stage_bytes(path: Path) -> int:
    return sum(item.stat().st_size for item in path.rglob("*") if item.is_file())


def run_myocardial_crowded_quasistatic_growth(root: Path) -> dict[str, object]:
    """Build once and execute the frozen conditional three-run matrix."""

    root = root.resolve(strict=True)
    output = root / RESULT
    parent = root / PARENT_RESULT
    if output.exists():
        raise FileExistsError(f"create-only result already exists: {output}")
    if not (parent / "verification.json").is_file():
        return {
            "status": "blocked",
            "reason": "retained heterogeneous parent evidence is missing",
            "parent": str(parent),
        }
    admission = evaluate_storage(
        scan_workspace(root), planned_new_bytes=256 * MIB, stop_reserve_bytes=64 * MIB
    )
    if not admission["can_start"]:
        return {"status": "blocked", "reason": "storage admission", "storage": admission}

    output.mkdir(parents=True)
    _write_json(output / "storage_preflight.json", admission)
    _write_json(
        output / "ownership.json",
        {
            "owner": "Codex",
            "purpose": "5x5 quasistatic doubled-target contact qualification",
            "gpu": False,
            "threads": 1,
            "planned_solver_invocations": 3,
            "automatic_retries": 0,
            "maximum_new_bytes": 256 * MIB,
            "stop_reserve_bytes": 64 * MIB,
        },
    )

    heterogeneity = generate_heterogeneity()
    cells, faces, box = prepare_geometry(
        root,
        heterogeneity,
        initial_gap=INITIAL_GAP,
        initial_wall_margin=INITIAL_WALL_MARGIN,
        target_planar_scale=1.0,
    )
    write_heterogeneity(output / "heterogeneity.csv", heterogeneity)
    write_mesh(output / "initial_cells.mesh", cells, faces)
    write_box(output / "box_schedule.csv", box)
    if (output / "initial_cells.mesh").read_bytes() != (
        parent / "initial_cells.mesh"
    ).read_bytes():
        raise RuntimeError("quasistatic-growth initial mesh differs from retained parent")
    if (output / "heterogeneity.csv").read_bytes() != (
        parent / "heterogeneity.csv"
    ).read_bytes():
        raise RuntimeError("quasistatic-growth heterogeneity differs from retained parent")

    targets_directory = output / "targets"
    controls_directory = output / "controls"
    targets_directory.mkdir()
    controls_directory.mkdir()
    for condition in CONDITIONS:
        write_doubled_reference_targets(
            targets_directory / f"{condition}.csv",
            _condition_targets(cells, faces, condition),
        )
        write_control(controls_directory / f"{condition}.csv", condition)

    _write_json(
        output / "configuration.json",
        {
            "schema_version": 1,
            "stage": STAGE,
            "contract": CONTRACT.as_posix(),
            "parent_result": PARENT_RESULT.as_posix(),
            "conditions": list(CONDITIONS),
            "cell_grid": [5, 5],
            "cell_count": 25,
            "requested_step": REQUESTED_STEP,
            "requested_steps": REQUESTED_STEPS,
            "target_ramp_steps": TARGET_RAMP_STEPS,
            "snapshot_interval_steps": 30,
            "target_start_fraction_of_final": TARGET_START_FRACTION,
            "box_policy": "fixed_at_parent_initial_bounds",
            "global_volume_scale_from_parent": VOLUME_SCALE,
            "global_area_scale_from_parent": AREA_SCALE,
            "shape_index_policy": "cellwise_target_isoperimetric_ratio_preserved",
            "maximum_initial_volume_relative_change": (
                MAXIMUM_INITIAL_VOLUME_RELATIVE_CHANGE
            ),
            "contact_controls": CONTROL,
            "maximum_backtracks": MAXIMUM_BACKTRACKS,
            "minimum_trial_gap": MINIMUM_TRIAL_GAP,
            "contraction_enabled": False,
            "coordinate_semantics": (
                "algorithmic_loading_and_relaxation_not_physiological_time"
            ),
        },
    )
    _write_json(
        output / "target_summary.json",
        {
            "final_volume_scale_from_parent": VOLUME_SCALE,
            "final_area_scale_from_parent": AREA_SCALE,
            "start_volume_scale_from_parent": 1.0,
            "saved_target_fraction_sequence": [
                0.5,
                0.625,
                0.75,
                0.875,
                1.0,
                1.0,
                1.0,
                1.0,
                1.0,
            ],
        },
    )
    _write_source_hashes(root, output, parent)

    build = _call(
        root,
        [
            "cmake",
            "--build",
            root / BUILD,
            "--config",
            "Release",
            "--target",
            "prl_myo_crowded_box_relaxation_v01",
            "--parallel",
            "1",
        ],
        600,
    )
    _write_json(output / "build.json", build)
    if build["return_code"] != 0:
        return finalize_myocardial_crowded_quasistatic_growth(root)
    _write_json(
        output / "binary.json",
        {
            "path": EXECUTABLE.as_posix(),
            "sha256": hashlib.sha256((root / EXECUTABLE).read_bytes()).hexdigest(),
        },
    )

    executions: dict[str, dict[str, object]] = {}
    for condition in CONDITIONS[:2]:
        executions[condition] = _execute_condition(root, output, condition)
        if _stage_bytes(output) > 192 * MIB:
            _write_json(
                output / "numerical_convergence_gate.json",
                {
                    "status": "failed",
                    "reason": "stage output exceeded 192 MiB before stop reserve",
                },
            )
            break

    from ..verification.myocardial_crowded_quasistatic_growth import (
        evaluate_numerical_convergence,
    )

    convergence = evaluate_numerical_convergence(output)
    _write_json(output / "numerical_convergence_gate.json", convergence)
    if convergence.get("status") == "passed" and all(
        executions.get(condition, {}).get("return_code") == 0
        for condition in CONDITIONS[:2]
    ):
        executions[CONDITIONS[2]] = _execute_condition(root, output, CONDITIONS[2])
    else:
        _write_json(
            output / f"execution_{CONDITIONS[2]}.json",
            {
                "status": "not_run",
                "reason": "K15 is conditional on completed and converged K30 controls",
                "automatic_retry": False,
            },
        )
    return finalize_myocardial_crowded_quasistatic_growth(root)


def finalize_myocardial_crowded_quasistatic_growth(root: Path) -> dict[str, object]:
    """Verify and render retained evidence without invoking the solver."""

    root = root.resolve(strict=True)
    output = (root / RESULT).resolve(strict=True)
    from ..rendering.myocardial_crowded_quasistatic_growth import (
        render_myocardial_crowded_quasistatic_growth,
    )
    from ..verification.myocardial_crowded_quasistatic_growth import (
        verify_myocardial_crowded_quasistatic_growth,
    )

    verification = verify_myocardial_crowded_quasistatic_growth(output)
    _write_json(output / "verification.json", verification)
    try:
        rendering = render_myocardial_crowded_quasistatic_growth(output)
    except Exception as error:  # retained data remain authoritative
        rendering = {
            "status": "failed",
            "error_type": type(error).__name__,
            "error": str(error),
        }
    _write_json(output / "rendering.json", rendering)
    postprocess_sources = [
        root / "src/prl/verification/myocardial_crowded_quasistatic_growth.py",
        root / "src/prl/rendering/myocardial_crowded_quasistatic_growth.py",
        root / "src/prl/runs/myocardial_crowded_quasistatic_growth.py",
    ]
    _write_json(
        output / "postprocess_source_hashes.json",
        {
            path.relative_to(root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in postprocess_sources
        },
    )
    postflight = evaluate_storage(
        scan_workspace(root), planned_new_bytes=0, stop_reserve_bytes=64 * MIB
    )
    _write_json(output / "storage_postflight.json", postflight)
    status = verification.get("status", "failed")
    if rendering.get("status") != "passed" or not postflight["can_start"]:
        status = "failed"
    summary = {
        "schema_version": 1,
        "stage": STAGE,
        "status": status,
        "numerical_qualification": verification.get(
            "numerical_qualification", "unknown"
        ),
        "conditions": verification.get("conditions", {}),
        "numerical_convergence": verification.get("numerical_convergence", {}),
        "material_sensitivity": verification.get("material_sensitivity", {}),
        "biological_validation": "not_run",
        "contraction": "not_run",
        "rendering": rendering,
        "storage": postflight,
    }
    _write_json(output / "summary.json", summary)
    return summary
