"""Run and materialize the frozen Route H Stage 2 Gate A suite."""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path
import sys
from typing import Any

import numpy as np


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = REPOSITORY_ROOT / "src"
if str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT))

from route_h.solver import run_gate_a_trajectory  # noqa: E402
from route_h.stage2_gate_a import (  # noqa: E402
    GateATrajectory,
    evaluate_gate_a_acceptance,
)


OUTPUT_ROOT = REPOSITORY_ROOT / "results/route_h/stage2_gate_a_v01"
RUNS = (
    ("A0_ZERO_dt0.01", "A0_ZERO", 0.01),
    ("A1_ACTIVE_dt0.02", "A1_ACTIVE", 0.02),
    ("A1_ACTIVE_dt0.01", "A1_ACTIVE", 0.01),
    ("A1_ACTIVE_dt0.005", "A1_ACTIVE", 0.005),
)
TIME_SERIES_COLUMNS = (
    "time",
    "alpha",
    "alpha_rate",
    "fiber_length",
    "axial_shortening",
    "transverse_scale_change_1",
    "transverse_scale_change_2",
    "volume_error",
    "centroid_drift",
    "passive_energy",
    "active_energy",
    "stored_energy",
    "dissipation",
    "active_power",
    "active_net_force",
    "active_net_moment",
    "projected_residual",
    "gauge_increment_residual",
    "optimizer_iterations",
    "optimizer_evaluations",
    "optimizer_reported_success",
)


def _canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest().upper()


def _time_series_rows(
    trajectory: GateATrajectory,
) -> list[tuple[float | int, ...]]:
    return [
        (
            trajectory.time[index],
            trajectory.alpha[index],
            trajectory.alpha_rate[index],
            trajectory.fiber_length[index],
            trajectory.axial_shortening[index],
            trajectory.transverse_scale_change[index, 0],
            trajectory.transverse_scale_change[index, 1],
            trajectory.volume_error[index],
            trajectory.centroid_drift[index],
            trajectory.passive_energy[index],
            trajectory.active_energy[index],
            trajectory.stored_energy[index],
            trajectory.dissipation[index],
            trajectory.active_power[index],
            trajectory.active_net_force[index],
            trajectory.active_net_moment[index],
            trajectory.projected_residual[index],
            trajectory.gauge_increment_residual[index],
            trajectory.optimizer_iterations[index],
            trajectory.optimizer_evaluations[index],
            int(trajectory.optimizer_reported_success[index]),
        )
        for index in range(len(trajectory.time))
    ]


def _write_trajectory(
    run_id: str,
    trajectory: GateATrajectory,
) -> dict[str, Any]:
    destination = OUTPUT_ROOT / run_id
    destination.mkdir(parents=True, exist_ok=True)

    time_series_path = destination / "time_series.csv"
    with time_series_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(TIME_SERIES_COLUMNS)
        for row in _time_series_rows(trajectory):
            writer.writerow(
                [
                    (
                        format(float(value), ".17g")
                        if isinstance(value, (float, np.floating))
                        else int(value)
                    )
                    for value in row
                ]
            )

    canonical_vertices = np.asarray(
        trajectory.vertices,
        dtype="<f8",
        order="C",
    )
    vertices_payload = canonical_vertices.tobytes(order="C")
    vertices_path = destination / "vertices.bin"
    vertices_path.write_bytes(vertices_payload)

    summary_path = destination / "summary.json"
    summary_payload = _canonical_json_bytes(trajectory.summary())
    summary_path.write_bytes(summary_payload)

    records = []
    for path, kind, details in (
        (
            time_series_path,
            "utf8_csv",
            {"rows": len(trajectory.time), "columns": list(TIME_SERIES_COLUMNS)},
        ),
        (
            vertices_path,
            "float64_le_c_order",
            {"shape": list(canonical_vertices.shape)},
        ),
        (summary_path, "canonical_json", {}),
    ):
        payload = path.read_bytes()
        records.append(
            {
                "path": path.name,
                "kind": kind,
                "sha256": _sha256(payload),
                **details,
            }
        )
    manifest = {
        "run_id": run_id,
        "case_id": trajectory.case_id,
        "dt": trajectory.dt,
        "duration": float(trajectory.time[-1]),
        "numerical_method": "DEC-PRL-ROUTE-H-STAGE2-NUMERICAL-METHOD-V02",
        "contract": "CONTRACT-PRL-ROUTE-H-STAGE0-V06",
        "freeze": "FREEZE-PRL-ROUTE-H-STAGE0-V06-V02",
        "files": records,
    }
    manifest_payload = _canonical_json_bytes(manifest)
    manifest_path = destination / "manifest.json"
    manifest_path.write_bytes(manifest_payload)
    return {
        "run_id": run_id,
        "manifest_path": str(manifest_path.relative_to(REPOSITORY_ROOT)).replace(
            "\\",
            "/",
        ),
        "manifest_sha256": _sha256(manifest_payload),
    }


def main() -> int:
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    trajectories: dict[str, GateATrajectory] = {}
    run_records: list[dict[str, Any]] = []
    for run_id, case_id, dt in RUNS:
        print(f"START {run_id}", flush=True)
        trajectory = run_gate_a_trajectory(case_id, dt=dt)
        trajectories[run_id] = trajectory
        record = _write_trajectory(run_id, trajectory)
        run_records.append(record)
        print(
            f"COMPLETE {run_id} {json.dumps(trajectory.summary(), sort_keys=True)}",
            flush=True,
        )

    acceptance = evaluate_gate_a_acceptance(trajectories)
    acceptance["run_manifests"] = run_records
    acceptance_path = OUTPUT_ROOT / "gate_a_acceptance.json"
    acceptance_payload = _canonical_json_bytes(acceptance)
    acceptance_path.write_bytes(acceptance_payload)
    suite_manifest = {
        "suite_id": "PRL-ROUTE-H-STAGE2-GATE-A-V01",
        "status": acceptance["status"],
        "acceptance_path": str(
            acceptance_path.relative_to(REPOSITORY_ROOT)
        ).replace("\\", "/"),
        "acceptance_sha256": _sha256(acceptance_payload),
        "run_manifests": run_records,
    }
    suite_manifest_path = OUTPUT_ROOT / "manifest.json"
    suite_manifest_path.write_bytes(_canonical_json_bytes(suite_manifest))
    print(
        f"GATE_A_{acceptance['status'].upper()} "
        f"{suite_manifest_path.relative_to(REPOSITORY_ROOT)}",
        flush=True,
    )
    return 0 if acceptance["status"] == "passed" else 2


if __name__ == "__main__":
    raise SystemExit(main())
