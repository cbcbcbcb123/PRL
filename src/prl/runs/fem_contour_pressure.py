"""Bounded passive finite-deformation pressure test on an image-derived outline."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import platform
import stat
import subprocess
import sys
import time

import numpy as np
import scipy

from prl.runs.fem_active_ellipse import _manifest as _base_manifest, _sha256, _write_json
from prl.runs.fem_finite_strain import scientific_lock
from prl.runs.fem_rotation import mesh_payload, state_payload, package_bytes
from prl.storage import evaluate_storage, scan_workspace


RESULT = Path("results/ventricle_fem/f5_contour_pressure_v01_20260917")
CONTRACT = Path("project_control/ventricle_fem_contour_pressure_contract_v01.md")
SOURCE_RESULT = Path("results/ventricle_fem/f2_measured_contour_v01_20260917")
SOURCE_GEOMETRY = SOURCE_RESULT / "geometry_source.npz"
SOURCE_GEOMETRY_SHA256 = "e2f3ac0f68b523bddcc8e33e8a0ab057cf06116a43120653b90139894d06fa21"
CAP, RESERVE, TIMEOUT = 64 * 1024**2, 64 * 1024**2, 1200
PARENTS = {
    "f2_measured_contour_v01_20260917": (
        "67503c849d363f78e3148c5f44fe66b67d283b92259efc05b07b3571626b1af7", 32),
    "f4_curved_pressure_v01_20260917": (
        "566a3caabfbcc672b5a62c5b4b21c6d25ad25a61bcbad29730195d09575d3d4f", 33),
}


def _manifest(root: Path) -> dict:
    """Build the common inventory while retaining F5-specific provenance."""
    report = _base_manifest(root)
    report["schema_version"] = "prl.fem_contour_pressure_manifest.v1"
    return report


def configuration() -> dict:
    return {
        "schema_version": "prl.fem_contour_pressure_configuration.v1",
        "cases": [
            {"name": "radial_coarse", "radial_intervals": [1, 1, 2]},
            {"name": "radial_fine", "radial_intervals": [2, 2, 4]},
        ],
        "geometry": {
            "source_result": SOURCE_RESULT.as_posix(),
            "source_geometry": SOURCE_GEOMETRY.as_posix(),
            "source_geometry_sha256": SOURCE_GEOMETRY_SHA256,
            "source": "72 hpf Fish 4 maximum-occupied XY slice z=39; not a projection",
            "segments": 36,
            "height": 0.5,
            "radial_boundary_fractions": [20 / 27, 21 / 27, 22 / 27, 1.0],
            "reference_assumption": "static image outline treated as zero-pressure stress-free reference",
            "internal_anatomy": "homothetic cavity and layer interfaces are constructed, not measured",
            "frozen_preflight": {
                "source_mask_iou": 0.9946353311213261,
                "raw_contour_hausdorff_um": 1.2491105980802832,
                "smooth_contour_hausdorff_um": 0.9719503052895044,
                "area_relative_error": 0.00037816659335643266,
                "minimum_orientation_cross": 0.012672907431171892,
            },
        },
        "material": {"model": "neo_hookean", "mu": 1.0},
        "kappa": 1000.0,
        "loads": [0.0, 0.02, 0.04, 0.06, 0.08],
        "solver": {"tolerance": 1e-9, "max_iterations": 30, "max_line_search": 16},
        "constraints": {
            "plane_strain": "all displacement-node uz=0",
            "in_plane_gauge": "outer mid-z anchor A: ux=uy=0; half-circumference B: uy=0; B ux free",
            "traction": "current inner-surface pressure; exterior traction-free; no end-cap pressure",
        },
        "scope": "image-derived outer outline with constructed cavity; passive plane-strain qualification, not a real-heart fit",
        "element": "periodic isoparametric Q2 displacement / continuous Q1 pressure; 3^3 volume and 3^2 surface Gauss",
        "units": "length normalized by 45.10550160766466 um; stress and pressure in uncalibrated mu units; load steps are not physiological time",
        "saved_energy": "internal isochoric material energy density; excludes follower-pressure work",
        "thresholds": {
            "mask_iou_min": 0.98,
            "raw_contour_hausdorff_um_max": 2.0,
            "kinematics_absolute": 1e-10,
            "stress_absolute": 2e-7,
            "free_force_residual": 2e-6,
            "pressure_weak_residual": 1e-8,
            "closed_pressure_resultant_and_moment": 2e-8,
            "gauge_reaction": 2e-6,
            "pressure_virtual_work_relative": 2e-5,
            "same_reference_domain_relative": 1e-12,
            "in_plane_z_variation": 1e-10,
            "midplane_average_area_relative": 1e-10,
            "zero_pressure_stress": 2e-7,
            "maximum_abs_J_minus_one": 0.01,
            "minimum_peak_cavity_area_change": 0.01,
            "radial_mesh_peak_absolute_difference": 0.002,
            "radial_mesh_peak_relative_difference": 0.05,
        },
        "runtime": {
            "python": platform.python_version(), "platform": platform.platform(),
            "numpy": np.__version__, "scipy": scipy.__version__,
        },
        "resources": {
            "threads": 1, "gpu": 0, "dcm": 0, "seconds": TIMEOUT,
            "stage_bytes": CAP, "reserve_bytes": RESERVE, "automatic_retries": 0,
        },
    }


def protected_evidence(workspace: Path) -> dict:
    reports = {}
    for name, (expected_hash, expected_count) in PARENTS.items():
        root = workspace / "results" / "ventricle_fem" / name
        manifest = root / "manifest.json"
        if _sha256(manifest) != expected_hash:
            raise ValueError(f"Protected manifest changed: {name}")
        items = json.loads(manifest.read_text(encoding="utf-8"))["files"]
        if len(items) != expected_count:
            raise ValueError(f"Protected inventory changed: {name}")
        for item in items:
            unresolved = root / item["path"]
            chain = [unresolved, *[p for p in unresolved.parents if p == root or p.is_relative_to(root)]]
            if any(p.is_symlink() or getattr(p.lstat(), "st_file_attributes", 0)
                   & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 1024) for p in chain):
                raise ValueError(f"Protected evidence contains a link: {name}/{item['path']}")
            path = unresolved.resolve()
            if not path.is_relative_to(root.resolve()):
                raise ValueError("Protected path escapes package")
            if path.stat().st_size != item["bytes"] or _sha256(path) != item["sha256"]:
                raise ValueError(f"Protected evidence changed: {name}/{item['path']}")
        reports[name] = {
            "status": "passed", "manifest_sha256": expected_hash,
            "verified_files": len(items),
        }
    if _sha256(workspace / SOURCE_GEOMETRY) != SOURCE_GEOMETRY_SHA256:
        raise ValueError("Frozen F2 geometry source changed")
    return reports


def checkpoint(root: Path, name: str, payload: dict) -> None:
    """Atomically replace an owned checkpoint while budgeting old plus pending bytes."""
    maximum = sum(np.asarray(value).nbytes for value in payload.values()) + 8192 * len(payload)
    if package_bytes(root) + maximum + 65536 > CAP:
        raise RuntimeError("Contour-pressure checkpoint exceeds stage budget")
    destination = root / "raw" / f"{name}.npz"
    pending = destination.with_suffix(".pending.npz")
    np.savez_compressed(pending, **payload)
    os.replace(pending, destination)


def _save_geometry_input(root: Path, arrays: dict[str, np.ndarray]) -> None:
    maximum = sum(value.nbytes for value in arrays.values()) + 8192 * len(arrays)
    if package_bytes(root) + maximum + 65536 > CAP:
        raise RuntimeError("Frozen contour input exceeds stage budget")
    pending = root / "geometry_input.pending.npz"
    np.savez_compressed(pending, **arrays)
    os.replace(pending, root / "geometry_input.npz")


def _raw_mesh_payload(built: dict) -> dict:
    mesh, metadata = built["mesh"], built["metadata"]
    node_shape = np.asarray(metadata["node_shape"], dtype=np.int64)
    inner_mid = np.asarray(metadata["inner_midplane_nodes"], dtype=np.int64)
    outer_mid = np.asarray(metadata["outer_midplane_nodes"], dtype=np.int64)
    anchors = metadata["anchor_node_ids"]
    return {
        **mesh_payload(mesh),
        "fixed_dofs": np.asarray(sorted(built["fixed"]), dtype=np.int64),
        "inner_faces": np.asarray(built["inner_faces"], dtype=np.int64),
        "layer_ids": np.asarray(built["layer_ids"], dtype=np.int64),
        "outer_curve_q2": np.asarray(metadata["outer_curve_nodes"], dtype=float),
        "radial_fractions": np.asarray(metadata["radial_q2_fractions"], dtype=float),
        "pressure_radial_fractions": np.asarray(metadata["radial_q1_fractions"], dtype=float),
        "radial_boundary_fractions": np.asarray(metadata["radial_boundary_fractions"], dtype=float),
        "source_to_solver_rotation": np.asarray(metadata["source_to_solver_rotation"], dtype=float),
        "image_center_um": np.asarray(metadata["center_um"], dtype=float),
        "length_scale_um": np.asarray(metadata["length_scale_um"], dtype=float),
        "height": np.asarray(metadata["height"], dtype=float),
        "node_shape": node_shape,
        "pressure_shape": np.asarray(metadata["pressure_shape"], dtype=np.int64),
        "inner_midplane_nodes": inner_mid,
        "outer_midplane_nodes": outer_mid,
        "anchor_node_ids": np.asarray([anchors["A"], anchors["B"]], dtype=np.int64),
    }


def worker(workspace: Path) -> dict:
    from prl.fem.contour_wall import build_contour_wall
    from prl.fem.follower_pressure import assemble_pressure
    from prl.fem.mixed_hex import solve

    root = workspace / RESULT
    pre = evaluate_storage(scan_workspace(workspace), planned_new_bytes=CAP, stop_reserve_bytes=RESERVE)
    if not pre["can_start"]:
        return {"status": "blocked", "reason": "storage admission", "storage": pre}
    if not (workspace / CONTRACT).is_file():
        raise FileNotFoundError(CONTRACT)
    protected = protected_evidence(workspace)
    with scientific_lock(workspace):
        root.mkdir(parents=True, exist_ok=False)
        (root / "raw").mkdir()
        started = time.perf_counter()
        attempts, completed = 0, 0
        context: dict = {}
        initial = None
        mesh_data: dict = {}
        try:
            config = configuration()
            with np.load(workspace / SOURCE_GEOMETRY, allow_pickle=False) as archive:
                source_arrays = {key: archive[key].copy() for key in archive.files}
            _save_geometry_input(root, source_arrays)
            _write_json(root / "configuration.json", config)
            _write_json(root / "storage_preflight.json", pre)
            _write_json(root / "protected_evidence_preflight.json", protected)

            built_cases = {
                case["name"]: build_contour_wall(
                    source_arrays, case["radial_intervals"],
                    segments=config["geometry"]["segments"], height=config["geometry"]["height"])
                for case in config["cases"]
            }
            _write_json(root / "geometry_adaptation.json", {
                "schema_version": "prl.fem_contour_pressure_geometry.v1",
                "status": "passed",
                "source_geometry_sha256": SOURCE_GEOMETRY_SHA256,
                "frozen_preflight": config["geometry"]["frozen_preflight"],
                "cases": {name: built["metadata"] for name, built in built_cases.items()},
                "interpretation": "image-derived outer Q2 curve; homothetic cavity/layers and stress-free reference are assumptions",
            })
            sources = [CONTRACT, SOURCE_GEOMETRY, SOURCE_RESULT / "geometry.json", *map(Path, [
                "src/prl/fem/contour_wall.py", "src/prl/fem/mixed_hex.py",
                "src/prl/fem/follower_pressure.py", "src/prl/fem/hyperelastic.py",
                "src/prl/runs/fem_contour_pressure.py", "src/prl/runs/fem_rotation.py",
                "src/prl/runs/fem_finite_strain.py", "src/prl/runs/fem_active_ellipse.py",
                "src/prl/verification/fem_contour_pressure.py",
                "src/prl/verification/fem_finite_strain.py",
                "src/prl/verification/fem_curved_pressure.py",
                "src/prl/rendering/fem_contour_pressure.py",
                "src/prl/rendering/fem_measured_contour.py",
                "src/prl/rendering/fem_finite_strain.py",
                "src/prl/rendering/fem_rotation.py",
                "src/prl/rendering/fem_curved_pressure.py",
                "src/prl/rendering/cb_plot_unified_style.py", "src/prl/cli.py", "src/prl/storage.py",
                "src/prl/__main__.py",
            ])]
            _write_json(root / "source_hashes.json", {
                path.as_posix(): _sha256(workspace / path) for path in sources
            })

            for case in config["cases"]:
                name = case["name"]
                built = built_cases[name]
                mesh, fixed, faces = built["mesh"], built["fixed"], built["inner_faces"]
                mesh_data = _raw_mesh_payload(built)
                records, histories = [], []
                initial = np.zeros(3 * len(mesh["nodes"]) + len(mesh["pressure_nodes"]))
                for step, pressure in enumerate(config["loads"]):
                    context = {"case": name, "step": step, "pressure": pressure}
                    if time.perf_counter() - started > TIMEOUT - 90:
                        raise TimeoutError("Contour-pressure compute deadline reached")
                    checkpoint(root, "current_initial", {
                        **mesh_data, "vector": initial, "load": np.asarray(pressure),
                    })
                    _write_json(root / "progress.json", {
                        "status": "unknown", "context": context,
                        "attempts": attempts, "completed_states": completed,
                    })
                    print(f"{name}: pressure {pressure}, state {step + 1}/5", flush=True)
                    attempts += 1
                    solved = solve(
                        mesh, config["material"], config["kappa"],
                        dirichlet=fixed, initial=initial,
                        follower_pressure={"faces": faces, "pressure": pressure},
                        tolerance=config["solver"]["tolerance"],
                        max_iterations=config["solver"]["max_iterations"],
                        max_line_search=config["solver"]["max_line_search"],
                    )
                    force = assemble_pressure(
                        mesh, solved["u"], faces, pressure, with_tangent=False)["force"]
                    records.append({
                        **state_payload(solved, fixed, force),
                        "initial_vectors": initial.copy(),
                    })
                    histories.append(solved["history"])
                    initial = solved["vector"].copy()
                    payload = {
                        key: np.asarray([row[key] for row in records]) for key in records[0]
                    }
                    checkpoint(root, name, {
                        **mesh_data, **payload,
                        "loads": np.asarray(config["loads"][:len(records)]),
                    })
                    _write_json(root / "raw" / f"{name}_newton.json", histories)
                    completed += 1

            _write_json(root / "solver_execution.json", {
                "status": "passed", "new_solves": attempts,
                "completed_states": completed, "scientific_invocations": 1,
                "automatic_retries": 0, "elapsed_seconds": time.perf_counter() - started,
            })
            after = protected_evidence(workspace)
            if after != protected:
                raise ValueError("Protected evidence drifted")
            _write_json(root / "protected_evidence_postflight.json", after)

            from prl.verification.fem_contour_pressure import verify_fem_contour_pressure
            verification = verify_fem_contour_pressure(root, save=True)
            from prl.rendering.fem_contour_pressure import render_fem_contour_pressure
            rendering = render_fem_contour_pressure(root)
            post = evaluate_storage(scan_workspace(workspace), planned_new_bytes=65536,
                                    stop_reserve_bytes=RESERVE)
            _write_json(root / "storage_postflight.json", post)
            if package_bytes(root) + 65536 > CAP:
                raise RuntimeError("Final package lacks control-record headroom")
            report = {
                "status": ("passed" if verification["status"] == "passed"
                           and rendering["status"] == "passed" and post["can_start"] else "failed"),
                "scientific_qualification": verification["status"],
                "rendering": rendering["status"],
                "new_solves": attempts, "completed_states": completed,
                "scientific_invocations": 1, "automatic_retries": 0,
                "threads": 1, "gpu": 0, "dcm": 0,
                "biological_validation": "not_run", "scope": config["scope"],
                "elapsed_seconds": time.perf_counter() - started,
            }
            _write_json(root / "execution.json", report)
            _write_json(root / "progress.json", report)
            _write_json(root / "summary.json", {
                **report,
                "metrics": {
                    "source_geometry": verification.get("source_geometry", {}),
                    "case_geometry": {
                        name: case_report.get("geometry", {})
                        for name, case_report in verification.get("cases", {}).items()
                    },
                    "cases": verification.get("cases", {}),
                    "mesh_comparison": verification.get("mesh_comparison", {}),
                    "gates": verification.get("gates", {}),
                },
                "limitations": [
                    "outer outline only is image-derived; cavity and layer interfaces are constructed",
                    "stress-free reference, pressure, material and plane strain are uncalibrated assumptions",
                    "radial refinement only; local stress and circumferential convergence are not established",
                    "no active contraction, physiological time, free 3-D motion, blood flow, growth or ECM feedback",
                ],
            })
            _write_json(root / "manifest.json", _manifest(root))
            return report
        except Exception as error:
            failure = {
                "status": "failed", "reason": repr(error), "context": context,
                "solve_attempts": attempts, "completed_states": completed,
                "automatic_retries": 0, "elapsed_seconds": time.perf_counter() - started,
            }
            if initial is not None:
                retained = {**mesh_data, "attempted_initial_vector": initial}
                if hasattr(error, "last_state"):
                    retained.update({key: value for key, value in error.last_state.items()
                                     if isinstance(value, np.ndarray)})
                try:
                    checkpoint(root, "failure_state", retained)
                    if hasattr(error, "last_state"):
                        _write_json(root / "last_iteration_history.json",
                                    error.last_state.get("history", []))
                except (OSError, RuntimeError) as retention_error:
                    failure["failure_state_write_error"] = repr(retention_error)
                    failure["retained_evidence"] = "last fully written atomic checkpoints, no deletion/retry"
            _write_json(root / "failure.json", failure)
            _write_json(root / "progress.json", failure)
            _write_json(root / "manifest.json", _manifest(root))
            raise


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", type=Path, default=Path.cwd())
    parser.add_argument("--worker", action="store_true")
    args = parser.parse_args()
    workspace = args.workspace.resolve()
    if args.worker:
        if os.environ.get("PRL_CONTOUR_PRESSURE_CONTROLLER") != "1":
            raise RuntimeError("Use the bounded contour-pressure controller")
        report = worker(workspace)
        print(json.dumps(report, indent=2))
        return 0 if report["status"] == "passed" else 1
    environment = os.environ.copy()
    for name in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
        environment[name] = "1"
    environment.update(
        PYTHONPATH=str(workspace / "src"), PYTHONDONTWRITEBYTECODE="1",
        MPLCONFIGDIR=str(workspace / RESULT / "runtime_cache"),
        PRL_CONTOUR_PRESSURE_CONTROLLER="1",
    )
    try:
        return subprocess.run(
            [sys.executable, "-B", "-X", "utf8", "-m", "prl.runs.fem_contour_pressure",
             "--workspace", str(workspace), "--worker"],
            cwd=workspace, env=environment, timeout=TIMEOUT, check=False,
        ).returncode
    except subprocess.TimeoutExpired:
        if (workspace / RESULT).is_dir():
            failure = {
                "status": "failed", "reason": "1200 second worker cap",
                "automatic_retries": 0,
                "scientific_invocations": 1,
                "retained_evidence": "all files left in place, including any pending write; no deletion or retry",
            }
            _write_json(workspace / RESULT / "timeout.json", failure)
            _write_json(workspace / RESULT / "failure.json", failure)
            _write_json(workspace / RESULT / "progress.json", failure)
            _write_json(workspace / RESULT / "manifest.json", _manifest(workspace / RESULT))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
