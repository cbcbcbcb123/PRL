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

from hybrid.fenicsx_ecm_backend import FenicsxECMBackend  # noqa: E402
from route_h.ecm_finite_strain import build_ecm_reference  # noqa: E402


DEFAULT_INPUT = (
    ROOT
    / "results/hybrid/efe_node1_fenicsx_spike_v01_20260819/inputs"
)
DEFAULT_OUTPUT = (
    ROOT
    / "results/hybrid/efe_node1_fenicsx_spike_v01_20260819"
    / "fenicsx_p1_jacobian_v01"
)


def relative_error(actual: np.ndarray, expected: np.ndarray) -> float:
    return float(
        np.linalg.norm(actual - expected)
        / max(
            1.0e-14,
            float(np.linalg.norm(actual)),
            float(np.linalg.norm(expected)),
        )
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-directory", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--directions", type=int, default=3)
    parser.add_argument("--step", type=float, default=1.0e-6)
    arguments = parser.parse_args()
    if arguments.directions < 1 or arguments.step <= 0.0:
        raise ValueError("directions and finite-difference step must be positive")

    input_path = arguments.input_directory.resolve()
    output_path = arguments.output.resolve()
    output_path.mkdir(parents=True, exist_ok=True)
    paths = sorted(input_path.glob("*.npz"))
    if not paths:
        raise RuntimeError("no FEniCSx exchange cases found")
    first = np.load(paths[0])
    reference = build_ecm_reference(
        np.asarray(first["reference_vertices"], dtype=np.float64),
        np.asarray(first["tetrahedra"], dtype=np.int64),
    )
    backend = FenicsxECMBackend(reference)
    rng = np.random.default_rng(20260819)
    records = []
    for path in paths:
        arrays = np.load(path)
        current = np.asarray(arrays["current_vertices"], dtype=np.float64)
        internal_z = np.asarray(arrays["internal_z"], dtype=np.float64)
        parameters = {
            "mu_eq": float(arrays["mu_eq"]),
            "kappa_eq": float(arrays["kappa_eq"]),
            "mu_ve": float(arrays["mu_ve"]),
        }
        tangent = backend.energy_hessian(
            current,
            reference,
            internal_z,
            **parameters,
        )
        antisymmetric = tangent - tangent.T
        symmetry_residual = float(
            np.linalg.norm(antisymmetric.data)
            / max(1.0, float(np.linalg.norm(tangent.data)))
        )
        audits = []
        for direction_id in range(arguments.directions):
            direction = rng.normal(size=current.size)
            direction /= np.linalg.norm(direction)
            perturbed_plus = current + arguments.step * direction.reshape(-1, 3)
            perturbed_minus = current - arguments.step * direction.reshape(-1, 3)
            _, plus_force, _ = backend.energy_force(
                perturbed_plus,
                reference,
                internal_z,
                **parameters,
            )
            _, minus_force, _ = backend.energy_force(
                perturbed_minus,
                reference,
                internal_z,
                **parameters,
            )
            finite_difference = (
                -plus_force.reshape(-1) + minus_force.reshape(-1)
            ) / (2.0 * arguments.step)
            ad_product = tangent @ direction
            audits.append(
                {
                    "direction_id": direction_id,
                    "relative_error": relative_error(
                        np.asarray(ad_product), finite_difference
                    ),
                    "cosine": float(
                        np.dot(ad_product, finite_difference)
                        / max(
                            1.0e-14,
                            float(np.linalg.norm(ad_product))
                            * float(np.linalg.norm(finite_difference)),
                        )
                    ),
                }
            )
        translation_residuals = []
        for component in range(3):
            translation = np.zeros_like(current)
            translation[:, component] = 1.0
            vector = translation.reshape(-1)
            translation_residuals.append(
                float(
                    np.linalg.norm(tangent @ vector)
                    / max(
                        1.0,
                        float(np.linalg.norm(tangent.data))
                        * float(np.linalg.norm(vector)),
                    )
                )
            )
        passed = bool(
            symmetry_residual <= 1.0e-10
            and max(audit["relative_error"] for audit in audits) <= 1.0e-5
            and max(translation_residuals) <= 1.0e-10
        )
        records.append(
            {
                "case": str(arrays["case_name"]),
                "tangent_shape": list(tangent.shape),
                "tangent_nonzeros": int(tangent.nnz),
                "symmetry_residual": symmetry_residual,
                "translation_residuals": translation_residuals,
                "directional_audits": audits,
                "passed": passed,
            }
        )

    report = {
        "schema_version": "efe_node1_fenicsx_jacobian_verification_v01",
        "status": "passed" if all(record["passed"] for record in records) else "failed",
        "evidence_class": "backend_productionization_p1_not_formal_n1_2_evidence",
        "finite_difference_step": arguments.step,
        "cases": records,
        "backend_diagnostics": backend.diagnostics(),
        "boundary": (
            "This verifies the ECM stored-energy Hessian only. DCM/interface "
            "Jacobians and formal N1-2 convergence are outside this result."
        ),
    }
    (output_path / "summary.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8"
    )
    print(json.dumps(report, indent=2))
    if report["status"] != "passed":
        raise RuntimeError("FEniCSx ECM Jacobian verification failed")


if __name__ == "__main__":
    main()
