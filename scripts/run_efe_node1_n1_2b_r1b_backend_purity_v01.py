from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIRECTORY = str(ROOT / "src")
if SOURCE_DIRECTORY not in sys.path:
    sys.path.insert(0, SOURCE_DIRECTORY)

from hybrid.efe_fast_trilayer import build_fast_trilayer_model  # noqa: E402
from hybrid.efe_fast_trilayer_solver import (  # noqa: E402
    build_exact_volume_coordinates,
    unpack_exact_volume_variables,
)
from hybrid.efe_path_sensitivity import (  # noqa: E402
    array_difference_metrics,
    sparse_difference_metrics,
    summarize_array_replicates,
    summarize_scalar_replicates,
)
from run_efe_node1_n1_2_periodic_case_v01 import (  # noqa: E402
    load_checkpoint,
)
from run_efe_node1_n1_2b_r1a_fixed_point_pilot_v01 import (  # noqa: E402
    checkpoint_array_digest,
    replay_accepted_state_history,
)


DEFAULT_BASELINE_CASE = (
    ROOT
    / "results/hybrid/efe_node1_n1_2b_cycle_stability_v01_20260820"
    / "N1_2B_D0_E0_F150_T016"
)
DEFAULT_INPUT = DEFAULT_BASELINE_CASE / "cycle_03/accepted_step_003.npz"
DEFAULT_TARGET = (
    ROOT
    / "results/hybrid/efe_node1_n1_2b_r1a_picard_control_v01_20260820"
    / "final_candidate_checkpoint.npz"
)
DEFAULT_OUTPUT = (
    ROOT
    / "results/hybrid/efe_node1_n1_2b_r1b_backend_purity_v01_20260820"
)
REPLICATE_COUNT = 3
TARGET_REPEATS_PER_BACKEND = 3
PURITY_TOLERANCE = 1.0e-12


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--target", type=Path, default=DEFAULT_TARGET)
    parser.add_argument(
        "--baseline-case-directory", type=Path, default=DEFAULT_BASELINE_CASE
    )
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    arguments = parser.parse_args()

    output_path = arguments.output.resolve()
    output_path.mkdir(parents=True, exist_ok=True)
    baseline_case = arguments.baseline_case_directory.resolve()
    model = build_fast_trilayer_model(
        dcm_level="D0", ecm_level="E0", ecm_footprint_scale=1.5
    )
    coordinates = build_exact_volume_coordinates(model)
    contact_count = len(model.myocyte_interface.tethers) + len(
        model.endocardial_interface.tethers
    )
    initial_arrays = load_checkpoint(
        arguments.input.resolve(),
        model,
        len(coordinates.free_indices),
        contact_count,
    )
    target_variables, target_internal_z, _ = load_checkpoint(
        arguments.target.resolve(),
        model,
        len(coordinates.free_indices),
        contact_count,
    )
    target_ecm_vertices = unpack_exact_volume_variables(
        model, coordinates, target_variables
    )[1]
    initial_digest = checkpoint_array_digest(*initial_arrays)

    from hybrid.fenicsx_ecm_backend import FenicsxECMBackend

    group_arrays: dict[str, dict[str, list[object]]] = {}
    group_records: dict[str, list[dict[str, object]]] = {}
    for mode in ("cold", "accepted_states"):
        group_arrays[mode] = {
            "forces": [],
            "jacobians": [],
            "hessians": [],
            "energies": [],
        }
        group_records[mode] = []
        for replicate in range(1, REPLICATE_COUNT + 1):
            backend = FenicsxECMBackend(model.ecm_reference)
            history_report: dict[str, object] = {
                "mode": "cold",
                "recoverable_state_count": 0,
            }
            if mode == "accepted_states":
                history_report = replay_accepted_state_history(
                    model,
                    coordinates,
                    baseline_case,
                    backend.energy_force,
                    variable_count=len(coordinates.free_indices),
                    contact_count=contact_count,
                )
            repeat_energies: list[float] = []
            repeat_forces: list[np.ndarray] = []
            repeat_jacobians: list[np.ndarray] = []
            repeat_hessians = []
            for _ in range(TARGET_REPEATS_PER_BACKEND):
                energy, force, jacobians = backend.energy_force(
                    target_ecm_vertices,
                    model.ecm_reference,
                    target_internal_z,
                )
                hessian = backend.energy_hessian(
                    target_ecm_vertices,
                    model.ecm_reference,
                    target_internal_z,
                )
                repeat_energies.append(float(energy["ecm_total"]))
                repeat_forces.append(force)
                repeat_jacobians.append(jacobians)
                repeat_hessians.append(hessian)
            within_force = summarize_array_replicates(repeat_forces)
            within_jacobian = summarize_array_replicates(repeat_jacobians)
            within_energy = summarize_scalar_replicates(repeat_energies)
            within_hessian = [
                sparse_difference_metrics(repeat_hessians[0], candidate)
                for candidate in repeat_hessians[1:]
            ]
            replicate_path = output_path / f"{mode}_replicate_{replicate:02d}.npz"
            np.savez_compressed(
                replicate_path,
                energy=np.asarray(repeat_energies, dtype=np.float64),
                force=np.stack(repeat_forces),
                jacobians=np.stack(repeat_jacobians),
                hessian_indptr=repeat_hessians[0].indptr,
                hessian_indices=repeat_hessians[0].indices,
                hessian_data=repeat_hessians[0].data,
                hessian_shape=np.asarray(repeat_hessians[0].shape),
            )
            record = {
                "replicate": replicate,
                "history": history_report,
                "initial_checkpoint_array_digest": initial_digest,
                "energy_total": repeat_energies[0],
                "force_norm": float(np.linalg.norm(repeat_forces[0])),
                "jacobian_minimum": float(np.min(repeat_jacobians[0])),
                "hessian_norm": float(repeat_hessians[0].power(2).sum() ** 0.5),
                "within_backend_energy": within_energy,
                "within_backend_force": within_force,
                "within_backend_jacobians": within_jacobian,
                "within_backend_hessian_maximum_symmetric_relative": max(
                    metric["symmetric_relative"] for metric in within_hessian
                ),
                "artifact": str(replicate_path),
                "backend_diagnostics": backend.diagnostics(),
            }
            group_records[mode].append(record)
            group_arrays[mode]["forces"].append(repeat_forces[0])
            group_arrays[mode]["jacobians"].append(repeat_jacobians[0])
            group_arrays[mode]["hessians"].append(repeat_hessians[0])
            group_arrays[mode]["energies"].append(repeat_energies[0])

    group_summary: dict[str, object] = {}
    for mode in ("cold", "accepted_states"):
        hessians = group_arrays[mode]["hessians"]
        group_summary[mode] = {
            "energy": summarize_scalar_replicates(
                group_arrays[mode]["energies"]
            ),
            "force": summarize_array_replicates(
                group_arrays[mode]["forces"]
            ),
            "jacobians": summarize_array_replicates(
                group_arrays[mode]["jacobians"]
            ),
            "hessian_maximum_symmetric_relative": max(
                sparse_difference_metrics(hessians[0], candidate)[
                    "symmetric_relative"
                ]
                for candidate in hessians[1:]
            ),
        }

    cross_energy = max(
        abs(float(cold) - float(warm))
        for cold in group_arrays["cold"]["energies"]
        for warm in group_arrays["accepted_states"]["energies"]
    )
    cross_force = max(
        array_difference_metrics(cold, warm)["symmetric_relative"]
        for cold in group_arrays["cold"]["forces"]
        for warm in group_arrays["accepted_states"]["forces"]
    )
    cross_jacobian = max(
        array_difference_metrics(cold, warm)["symmetric_relative"]
        for cold in group_arrays["cold"]["jacobians"]
        for warm in group_arrays["accepted_states"]["jacobians"]
    )
    cross_hessian = max(
        sparse_difference_metrics(cold, warm)["symmetric_relative"]
        for cold in group_arrays["cold"]["hessians"]
        for warm in group_arrays["accepted_states"]["hessians"]
    )
    passed = bool(
        cross_energy <= PURITY_TOLERANCE
        and cross_force <= PURITY_TOLERANCE
        and cross_jacobian <= PURITY_TOLERANCE
        and cross_hessian <= PURITY_TOLERANCE
    )
    report = {
        "schema_version": "efe_node1_n1_2b_r1b_backend_purity_v01",
        "status": (
            "passed_backend_history_purity_audit"
            if passed
            else "failed_backend_history_purity_audit"
        ),
        "input_checkpoint": str(arguments.input.resolve()),
        "target_checkpoint": str(arguments.target.resolve()),
        "baseline_case_directory": str(baseline_case),
        "replicates_per_group": REPLICATE_COUNT,
        "target_repeats_per_backend": TARGET_REPEATS_PER_BACKEND,
        "tolerance": PURITY_TOLERANCE,
        "group_records": group_records,
        "group_summary": group_summary,
        "cold_vs_history_warmed": {
            "energy_maximum_absolute": cross_energy,
            "force_maximum_symmetric_relative": cross_force,
            "jacobian_maximum_symmetric_relative": cross_jacobian,
            "hessian_maximum_symmetric_relative": cross_hessian,
        },
        "passed": passed,
        "evidence_boundary": (
            "All recoverable accepted states were replayed in order. The "
            "original optimizer-internal evaluation sequence was not archived."
        ),
    }
    (output_path / "summary.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8"
    )
    print(json.dumps({"status": report["status"], "passed": passed}, indent=2))
    if not passed:
        raise RuntimeError(str(report["status"]))


if __name__ == "__main__":
    main()
