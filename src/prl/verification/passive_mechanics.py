"""Independent geometry/energy reconstruction for the real C++ kernel probe."""
from __future__ import annotations

import csv
import hashlib
import json
import math
from pathlib import Path

import numpy as np


def reference_energy(area: float, volume: float, *, gamma: float, ka: float,
                     bulk: float, v0: float, cap: float, q0: float) -> float:
    target_area = (q0*volume*volume)**(1/3)
    elastic = 0.5*ka*(area/target_area-1)**2
    volume_energy = 0.0
    if bulk:
        transition = v0*math.exp(-cap/bulk)
        at = max(volume, transition)
        volume_energy = bulk*(at*math.log(at/v0)-at+v0)
        if volume < transition:
            volume_energy += cap*(transition-volume)
    return gamma*area+elastic+volume_energy


def _geometry(points: np.ndarray, faces: np.ndarray) -> tuple[float, float]:
    a, b, c = (points[faces[:, i]] for i in range(3))
    area = np.linalg.norm(np.cross(b-a, c-a), axis=1).sum()/2
    volume = np.einsum("ij,ij->i", a, np.cross(b, c)).sum()/6
    return float(area), float(volume)


def validate_gradient_matrix(rows: list[dict]) -> None:
    expected = {(shape, term, direction, 10.0**(-power))
                for shape in range(2) for term in range(6) for direction in range(2)
                for power in range(2, 8)}
    keys = [(int(row["shape"]), int(row["term"]), int(row["direction"]), float(row["epsilon"])) for row in rows]
    if len(keys) != len(expected) or set(keys) != expected:
        raise ValueError("incomplete or duplicated gradient matrix")
    if not all(math.isfinite(float(value)) for row in rows for value in row.values()):
        raise ValueError("non-finite gradient matrix")


def verify_passive_mechanics(result: Path, phase: str = "green") -> dict:
    folder = result / phase
    rows = list(csv.DictReader((folder/"gradient.csv").open(encoding="utf-8")))
    validate_gradient_matrix(rows)
    rigid = list(csv.DictReader((folder/"rigid.csv").open(encoding="utf-8")))
    node_rows = list(csv.DictReader((folder/"nodes.csv").open(encoding="utf-8")))
    face_rows = list(csv.DictReader((folder/"faces.csv").open(encoding="utf-8")))
    if not all(math.isfinite(float(value)) for row in rigid+node_rows+face_rows for value in row.values()):
        raise ValueError("non-finite rigid or mesh record")
    meshes = {}
    for shape in ("0", "1"):
        points = np.array([[float(row[k]) for k in ("x", "y", "z")] for row in node_rows if row["shape"] == shape])
        faces = np.array([[int(row[k]) for k in ("a", "b", "c")] for row in face_rows if row["shape"] == shape])
        meshes[shape] = (points, faces)
    geometry_error = energy_error = 0.0
    groups: dict[str, dict] = {}
    for row in rows:
        points, faces = meshes[row["shape"]]
        direction = points.ravel().copy()
        if row["direction"] == "1":
            indices = np.arange(direction.size)
            direction = np.sin(0.73*(indices+1))+0.3*np.cos(0.19*(indices+2))
        direction = (direction/np.linalg.norm(direction)).reshape(points.shape)
        eps = float(row["epsilon"])
        energies = []
        parameters = {key: float(row[key]) for key in ("gamma", "ka", "bulk", "v0", "cap", "q0")}
        for label, sign in (("plus", 1), ("minus", -1)):
            area, volume = _geometry(points+sign*eps*direction, faces)
            geometry_error = max(geometry_error, abs(area-float(row[f"area_{label}"]))/area,
                                 abs(volume-float(row[f"volume_{label}"]))/volume)
            expected = reference_energy(area, volume, **parameters)
            energies.append(expected)
            energy_error = max(energy_error, abs(expected-float(row[f"energy_{label}"]))/max(1.0, abs(expected)))
        analytic = float(row["minus_force_dot_direction"])
        cache_fd = (float(row["energy_plus"])-float(row["energy_minus"]))/2/eps
        residual = abs((energies[0]-energies[1])/2/eps-analytic)/max(1.0, abs(analytic))
        cache_residual = abs(cache_fd-analytic)/max(1.0, abs(analytic))
        key = "/".join(row[field] for field in ("shape", "term", "direction"))
        group = groups.setdefault(key, {"best_reference_error": 1e99, "best_cache_error": 1e99, "samples": 0})
        group["best_reference_error"] = min(group["best_reference_error"], residual)
        group["best_cache_error"] = min(group["best_cache_error"], cache_residual)
        group["samples"] += 1
    rigid_error = max(max(abs(float(row["energy"])-float(row[k]))/float(row["energy_scale"]) for k in ("translated_energy", "rotated_energy")) for row in rigid)
    force_error = max(max(float(row[k])/float(row["force_scale"]) for k in ("net_force", "net_moment", "force_rotation_error")) for row in rigid)
    snapshot_record = json.loads((result/f"{phase}_execution.json").read_text(encoding="utf-8"))
    source_ok = all(hashlib.sha256((result/f"{phase}_source"/item["path"]).read_bytes()).hexdigest() == item["sha256"] for item in snapshot_record["sources"])
    checks = {
        "complete_matrix": len(rows) == 144 and len(groups) == 24 and len(rigid) == 12 and all(group["samples"] == 6 for group in groups.values()),
        "independent_geometry": geometry_error <= 1e-12,
        "energy_values": energy_error <= 1e-10,
        "independent_directional_gradient": all(group["best_reference_error"] <= 1e-6 for group in groups.values()),
        "cached_directional_gradient": all(group["best_cache_error"] <= 1e-6 for group in groups.values()),
        "rigid_energy": rigid_error <= 1e-10,
        "force_moment_covariance": force_error <= 1e-10,
        "explicit_shared_material_q": {float(row["q0"]) for row in rows} == {150.0},
        "source_snapshots": source_ok,
    }
    return {"status": "passed" if all(checks.values()) else "failed", "phase": phase,
            "checks": checks, "groups": groups, "max_geometry_error": geometry_error,
            "max_energy_error": energy_error, "max_rigid_energy_error": rigid_error,
            "max_force_moment_error": force_error, "scope": "static synthetic force-energy qualification; tissue not_run"}


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("result", type=Path)
    parser.add_argument("--phase", choices=("red", "green"), default="green")
    args = parser.parse_args()
    output = args.result/f"{args.phase}_verification.json"
    if output.exists():
        raise ValueError("create-only verification exists")
    report = verify_passive_mechanics(args.result, args.phase)
    output.write_text(json.dumps(report, indent=2)+"\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    raise SystemExit(0 if report["status"] == "passed" else 1)
