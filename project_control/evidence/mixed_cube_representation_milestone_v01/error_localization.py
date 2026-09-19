"""Read-only localization of retained P3/P2 displacement L2 error.

No production forms, FEM invocation, geometry generation or fitting are used.
The sole optional write is one explicitly selected create-only JSON result.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import sys

import numpy as np

WORKSPACE = Path(__file__).resolve().parents[3]
sys.dont_write_bytecode = True
sys.path.insert(0, str(WORKSPACE / "src"))

from prl.verification.mixed_cube import exact_fields, quadrature
from prl.verification.mixed_cube_space import kinematics, u_shape


# Fixed before inspecting the regional results; not selected from error peaks.
BAND_WIDTH_OVER_L = 0.125
REGIONS = (
    "all", "outer_band", "outer_complement", "dirichlet_band", "dirichlet_complement",
)
ORDER_PER_DUFFY_AXIS = 6
CELL_CHUNK_SIZE = 128
TOTAL_REPRODUCTION_ABSOLUTE_TOLERANCE = 1e-12
REGISTERED_CASES = ((2, 2), (4, 3), (8, 3))
EXACT_REGION_VOLUMES = {
    "all": 1.0,
    "outer_band": 1.0 - (1.0 - 2.0 * BAND_WIDTH_OVER_L) ** 3,
    "outer_complement": (1.0 - 2.0 * BAND_WIDTH_OVER_L) ** 3,
    "dirichlet_band": BAND_WIDTH_OVER_L,
    "dirichlet_complement": 1.0 - BAND_WIDTH_OVER_L,
}


def sha256(path):
    checksum = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            checksum.update(block)
    return checksum.hexdigest()


def analyze(result_base):
    result_base = Path(result_base).resolve()
    input_paths = []
    for divisions, version in REGISTERED_CASES:
        root = result_base / f"mixed_cube_representation_v{version:02d}_20260919"
        name = f"mms_p3p2_n{divisions}"
        input_paths.extend(root / "raw" / f"{name}_{role}.{extension}"
                           for role, extension in (("mesh", "npz"), ("state", "npz"), ("audit", "json")))
    code_paths = [Path(__file__).resolve(), *(
        WORKSPACE / "src/prl/verification" / name for name in
        ("mixed_cube.py", "mixed_cube_space.py", "simplex_lagrange.py", "ventricle_3d.py"))]
    input_hashes = {str(path): sha256(path) for path in input_paths}
    code_hashes = {str(path): sha256(path) for path in code_paths}
    points, weights = quadrature(3, ORDER_PER_DUFFY_AXIS)
    rows = []
    for divisions, version in REGISTERED_CASES:
        root = result_base / f"mixed_cube_representation_v{version:02d}_20260919"
        name = f"mms_p3p2_n{divisions}"
        with np.load(root / "raw" / f"{name}_mesh.npz", allow_pickle=False) as archive:
            data = {key: archive[key] for key in archive.files}
        with np.load(root / "raw" / f"{name}_state.npz", allow_pickle=False) as archive:
            displacement = archive["u"]
        audit = json.loads((root / "raw" / f"{name}_audit.json").read_text(encoding="utf-8"))
        if int(data["u_degree"]) != 3 or int(data["p_degree"]) != 2:
            raise ValueError("Localization is restricted to retained P3/P2 cases")
        basis, _ = u_shape(data, points)
        totals = {region: {"volume": 0.0, "error_squared": 0.0} for region in REGIONS}
        reference_squared = 0.0
        for first in range(0, len(data["cells"]), CELL_CHUNK_SIZE):
            local = dict(data, cells=data["cells"][first:first + CELL_CHUNK_SIZE])
            _, _, _, determinant, barycentric, vertices = kinematics(local, displacement, points)
            coordinates = np.einsum("qa,cai->cqi", barycentric, vertices)
            mass = determinant[:, None] * weights
            exact = exact_fields(coordinates, "mms", 100.0)["u"]
            numerical = np.einsum("qa,cai->cqi", basis, displacement[local["cells"]])
            error_squared = np.sum((numerical - exact) ** 2, axis=-1)
            if not np.isfinite(error_squared).all():
                raise ValueError("Nonfinite reconstructed displacement error")
            reference_squared += float(np.sum(mass * np.sum(exact ** 2, axis=-1)))
            outer = np.min(np.minimum(coordinates, 1.0 - coordinates), axis=-1) < BAND_WIDTH_OVER_L
            dirichlet = coordinates[..., 0] < BAND_WIDTH_OVER_L
            masks = {"all": np.ones_like(outer), "outer_band": outer, "outer_complement": ~outer,
                     "dirichlet_band": dirichlet, "dirichlet_complement": ~dirichlet}
            for region, mask in masks.items():
                totals[region]["volume"] += float(np.sum(mass * mask))
                totals[region]["error_squared"] += float(np.sum(mass * error_squared * mask))
        for region, values in totals.items():
            values.update(
                absolute_L2=math.sqrt(values["error_squared"]),
                volume_fraction=values["volume"] / totals["all"]["volume"],
                error_squared_fraction=values["error_squared"] / totals["all"]["error_squared"],
                exact_region_volume=EXACT_REGION_VOLUMES[region],
                volume_estimate_minus_exact=values["volume"] - EXACT_REGION_VOLUMES[region],
            )
        relative = math.sqrt(totals["all"]["error_squared"] / reference_squared)
        expected = float(audit["metrics"]["relative_u_L2"])
        difference = abs(relative - expected)
        if difference > TOTAL_REPRODUCTION_ABSOLUTE_TOLERANCE:
            raise ValueError(f"Total L2 reproduction failed for {name}: {difference}")
        for band, complement in (("outer_band", "outer_complement"),
                                 ("dirichlet_band", "dirichlet_complement")):
            if abs(totals[band]["error_squared_fraction"] +
                   totals[complement]["error_squared_fraction"] - 1.0) > 1e-12:
                raise ValueError("Regional squared-error contributions fail to partition the total")
        rows.append({"case": name, "n": divisions, "source_root": str(root),
                     "reference_L2": math.sqrt(reference_squared), "relative_u_L2": relative,
                     "retained_relative_u_L2": expected, "absolute_difference": difference,
                     "total_reproduction": "passed", "regions": totals})
    orders = {region: [math.log(rows[index]["regions"][region]["absolute_L2"] /
                               rows[index + 1]["regions"][region]["absolute_L2"], 2)
                       for index in (0, 1)] for region in REGIONS}
    for paths in (input_hashes, code_hashes):
        if any(sha256(path) != expected for path, expected in paths.items()):
            raise ValueError("Input or analysis-code drift during read-only analysis")
    return {
        "schema": "prl.mixed_cube_representation.error_localization.v1",
        "status": "passed",
        "status_scope": "read-only reconstruction, total reproduction and input/code integrity; not scientific qualification",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "method": {
            "case_scope": "Existing P3/P2 original MMS, kappa=100; n2 from v02, n4/n8 from v03",
            "integration": "6-point-per-axis Gauss-Duffy, 216 points per tetrahedron",
            "cell_chunk_size": CELL_CHUNK_SIZE,
            "region_assignment": "Pointwise fixed reference-coordinate mask, not geometrically cut tetrahedra",
            "fixed_band_width_over_L": BAND_WIDTH_OVER_L,
            "outer_band": "min(X,Y,Z,1-X,1-Y,1-Z) < 0.125",
            "dirichlet_band": "X < 0.125",
            "complements": "Logical complements of the respective masks, not complements of their union",
            "absolute_L2": "sqrt(integral_region ||u_h-u_exact||^2 dV); dimensionless unit cube",
            "error_squared_fraction": "regional squared L2 / whole-domain squared L2",
            "orders": "log2(previous absolute L2 / next absolute L2), in order n2->n4 and n4->n8",
            "total_reproduction_absolute_tolerance": TOTAL_REPRODUCTION_ABSOLUTE_TOLERANCE,
        },
        "rows": rows,
        "orders_2to4_4to8": orders,
        "regional_quadrature_limits": {
            "status": "approximate",
            "n2_outer_band_volume_bias": rows[0]["regions"]["outer_band"]["volume_estimate_minus_exact"],
            "n2_outer_band_volume_bias_percentage_points": 100.0 * rows[0]["regions"]["outer_band"]["volume_estimate_minus_exact"],
            "statement": "The fixed-region indicator is discontinuous where it cuts a tetrahedron. "
                         "No cut-cell integration was performed. n2 outer-band volume is underestimated by about "
                         "0.4991 percentage points; exact-looking n4 volume does not certify the regional error integral. "
                         "Regional rates are descriptive localization evidence, not exact regional convergence certificates.",
        },
        "interpretation": {
            "outer_band_dominates_finest_error": False,
            "dirichlet_band_dominates_finest_error": False,
            "evidence": "At n8 the outer band contains 49.0865% of squared error in 57.8125% of volume; "
                        "the Dirichlet band contains 6.4232% of squared error in 12.5% of volume. "
                        "The outer-band complement has the slower final observed rate, 3.2277, and 50.9135% of squared error.",
            "boundary_singularity_proved": False,
            "sole_error_mechanism_identified": False,
            "qualification_thresholds_changed": False,
            "scientific_limit": "These fixed-region diagnostics do not explain the asymptotic regime by themselves "
                                "and cannot turn the original whole-domain L2-order failure into a pass.",
        },
        "integrity": {"status": "passed", "inputs_sha256": input_hashes, "code_sha256": code_hashes,
                      "hashes_verified_unchanged_after_analysis": True},
        "additional_FEM_solves": 0,
        "GPU_workers": 0,
        "source_files_written": 0,
        "result_write_policy": "stdout by default; at most one explicitly requested JSON opened with exclusive creation",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--result-base", type=Path, default=WORKSPACE.parent / "PRL-results/ventricle_fem")
    parser.add_argument("--output", type=Path, help="Optional exact create-only JSON destination; parent must exist")
    arguments = parser.parse_args()
    output = arguments.output.resolve() if arguments.output else None
    if output is not None and (output.exists() or not output.parent.is_dir()):
        raise ValueError("Output must be a new exact path inside an existing directory")
    report = analyze(arguments.result_base)
    rendered = json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
    if output is None:
        print(rendered, end="")
    else:
        with output.open("x", encoding="utf-8", newline="\n") as stream:
            stream.write(rendered)
        print(json.dumps({"status": report["status"], "scope": report["status_scope"],
                          "output": str(output), "output_sha256": sha256(output),
                          "max_total_reproduction_difference": max(row["absolute_difference"] for row in report["rows"]),
                          "additional_FEM_solves": 0}, indent=2))


if __name__ == "__main__":
    main()
