from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np

from hybrid.efe_fast_trilayer import build_fast_trilayer_model
from hybrid.fenicsx_ecm_spike import (
    ECMSpikeCase,
    build_affine_case,
    build_m0_case,
    evaluate_reference_case,
)


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PEAK_STATE = (
    ROOT
    / "results/hybrid/efe_node1_n1_1a_sparse_footprint_v03_20260818"
    / "F150/solver_step_07/activation_020_state.npz"
)
DEFAULT_OUTPUT = (
    ROOT / "results/hybrid/efe_node1_fenicsx_spike_v01_20260819"
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def peak_case(model, peak_state_path: Path) -> ECMSpikeCase:
    arrays = np.load(peak_state_path)
    current = np.asarray(arrays["ecm_vertices"], dtype=np.float64)
    expected_shape = model.ecm_reference.vertices.shape
    if current.shape != expected_shape:
        raise ValueError(
            f"peak ECM shape {current.shape} does not match F150 {expected_shape}"
        )
    if "ecm_internal_z" in arrays.files:
        internal_z = np.asarray(arrays["ecm_internal_z"], dtype=np.float64)
    else:
        internal_z = np.zeros(
            (len(model.ecm_reference.tetrahedra), 3, 3), dtype=np.float64
        )
    return ECMSpikeCase(
        name="f150_d0_e0_activation_020_peak",
        reference_vertices=model.ecm_reference.vertices.copy(),
        current_vertices=current.copy(),
        tetrahedra=model.ecm_reference.tetrahedra.copy(),
        internal_z=internal_z.copy(),
    )


def write_case(
    case: ECMSpikeCase,
    model,
    case_path: Path,
    warm_repeats: int,
) -> dict[str, object]:
    energies, force, jacobians, benchmark = evaluate_reference_case(
        case,
        model.ecm_reference,
        mu_eq=model.mu_eq,
        kappa_eq=model.kappa_eq,
        mu_ve=model.mu_ve,
        warm_repeats=warm_repeats,
    )
    displacement = case.current_vertices - case.reference_vertices
    np.savez_compressed(
        case_path,
        schema_version=np.asarray("efe_node1_fenicsx_ecm_exchange_v01"),
        case_name=np.asarray(case.name),
        reference_vertices=case.reference_vertices,
        current_vertices=case.current_vertices,
        tetrahedra=case.tetrahedra,
        internal_z=case.internal_z,
        mu_eq=np.asarray(model.mu_eq),
        kappa_eq=np.asarray(model.kappa_eq),
        mu_ve=np.asarray(model.mu_ve),
        expected_equilibrium_energy=np.asarray(energies["ecm_equilibrium"]),
        expected_viscoelastic_energy=np.asarray(energies["ecm_viscoelastic"]),
        expected_total_energy=np.asarray(energies["ecm_total"]),
        expected_force=force,
        expected_jacobians=jacobians,
    )
    resultant = force.sum(axis=0)
    centre = case.reference_vertices.mean(axis=0)
    moment = np.cross(case.current_vertices - centre, force).sum(axis=0)
    return {
        "name": case.name,
        "path": str(case_path.relative_to(ROOT)).replace("\\", "/"),
        "sha256": sha256(case_path),
        "vertex_count": int(len(case.reference_vertices)),
        "tetrahedron_count": int(len(case.tetrahedra)),
        "maximum_displacement": float(np.linalg.norm(displacement, axis=1).max()),
        "equilibrium_energy": float(energies["ecm_equilibrium"]),
        "viscoelastic_energy": float(energies["ecm_viscoelastic"]),
        "total_energy": float(energies["ecm_total"]),
        "force_l2": float(np.linalg.norm(force)),
        "resultant_force_l2": float(np.linalg.norm(resultant)),
        "resultant_moment_l2": float(np.linalg.norm(moment)),
        "minimum_j": float(jacobians.min()),
        "maximum_j": float(jacobians.max()),
        "reference_backend_timing": benchmark,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--peak-state", type=Path, default=DEFAULT_PEAK_STATE)
    parser.add_argument("--warm-repeats", type=int, default=7)
    arguments = parser.parse_args()

    output_path = arguments.output.resolve()
    inputs_path = output_path / "inputs"
    inputs_path.mkdir(parents=True, exist_ok=True)
    peak_state_path = arguments.peak_state.resolve()
    if not peak_state_path.is_file():
        raise FileNotFoundError(peak_state_path)

    model = build_fast_trilayer_model(
        dcm_level="D0", ecm_level="E0", ecm_footprint_scale=1.5
    )
    cases = (
        build_m0_case(model.ecm_reference),
        build_affine_case(model.ecm_reference),
        peak_case(model, peak_state_path),
    )
    records = []
    for case in cases:
        case_path = inputs_path / f"{case.name}.npz"
        records.append(
            write_case(case, model, case_path, arguments.warm_repeats)
        )

    manifest = {
        "schema_version": "efe_node1_fenicsx_spike_input_manifest_v01",
        "status": "reference_inputs_exported",
        "evidence_class": "backend_spike_not_formal_n1_2_evidence",
        "model": {
            "dcm_level": model.dcm_level,
            "ecm_level": model.ecm_level,
            "ecm_footprint_scale": model.ecm_footprint_scale,
            "ecm_divisions": list(model.ecm_divisions),
            "mu_eq": model.mu_eq,
            "kappa_eq": model.kappa_eq,
            "mu_ve": model.mu_ve,
            "eta_ve": model.eta_ve,
        },
        "peak_source": {
            "path": str(peak_state_path.relative_to(ROOT)).replace("\\", "/"),
            "sha256": sha256(peak_state_path),
        },
        "cases": records,
    }
    manifest_path = output_path / "input_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
