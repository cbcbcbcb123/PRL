"""Independent mesh reconstruction and static gradient adjudication for sheet pairs."""
from __future__ import annotations

from collections import Counter
import hashlib
import json
from pathlib import Path

import numpy as np

from .contact_performance_equilibrium import _mesh_metrics, _crossing_count, _contained_witnesses
from .passive_mechanics import _geometry, reference_energy


def read_csv(path: Path) -> np.ndarray:
    return np.atleast_1d(np.genfromtxt(path, delimiter=",", names=True))


def field(rows: np.ndarray, names) -> np.ndarray:
    return np.column_stack([rows[name] for name in names])


def topology_closed(faces: np.ndarray, vertex_count: int) -> bool:
    edges = Counter((int(face[i]), int(face[(i+1) % 3])) for face in faces for i in range(3))
    return (all(count == 1 and edges[(b, a)] == 1 for (a, b), count in edges.items())
            and vertex_count-len(edges)//2+len(faces) == 2)


def gradient_error(difference: float, expected: float) -> float:
    return float(abs(difference-expected)/max(1.0, abs(difference), abs(expected)))


def verify_sheet(output: Path) -> dict:
    root = output.parents[2]
    configuration = json.loads((output/"configuration.json").read_text())
    hashes = json.loads((output/"source_hashes.json").read_text())
    binary = json.loads((output/"binary.json").read_text())
    checks = {"sources_unchanged": all((root/path).is_file() and hashlib.sha256((root/path).read_bytes()).hexdigest() == sha
                                      for path, sha in hashes.items()),
              "binary_unchanged": hashlib.sha256((root/binary["path"]).read_bytes()).hexdigest() == binary["sha256"]}
    ledger = json.loads((output/"static_execution.json").read_text())
    checks["eighteen_static_calls"] = len(ledger) == 18 and all(row["return_code"] == 0 for row in ledger)
    details, groups = {}, []
    for case in ("regular", "irregular"):
        stored = np.load(output/"inputs"/f"{case}.npz")
        points, faces = stored["points"], stored["faces"]
        base = output/"static"/case
        nodes = read_csv(base/"nodes.csv"); states = read_csv(base/"states.csv"); separation = read_csv(base/"separation.csv")
        positions = field(nodes, ("x", "y", "z"))
        force = field(nodes, ("fx", "fy", "fz")); contact = field(nodes, ("cfx", "cfy", "cfz"))
        reaction = field(nodes, ("rfx", "rfy", "rfz"))
        passive = force-reaction-contact
        areas, volumes, quality, crossings, containment = [], [], [], 0, 0
        for cell in range(16):
            area, volume = _geometry(points[cell], faces); areas.append(area); volumes.append(volume)
            quality.append(_mesh_metrics(points[cell], faces)["min_angle"])
            crossings += _crossing_count(points[cell][faces], points[cell][faces], faces, faces)
            for other in range(cell):
                if np.all(points[cell].min(axis=0) <= points[other].max(axis=0)) and np.all(points[other].min(axis=0) <= points[cell].max(axis=0)):
                    crossings += _crossing_count(points[cell][faces], points[other][faces])
                    containment += _contained_witnesses(points[cell], points[other][faces])+_contained_witnesses(points[other], points[cell][faces])
        pressure_energy = sum(reference_energy(a, v, gamma=.160, ka=.050, bulk=30, v0=v, cap=100, q0=configuration["q0"])
                              for a, v in zip(areas, volumes))
        contact_scale = max(float(np.linalg.norm(contact, axis=1).sum()), 1e-12)
        force_balance = float(np.linalg.norm(contact.sum(axis=0))/contact_scale)
        arms = positions-positions.mean(axis=0)
        torque = np.cross(arms, contact)
        torque_balance = float(np.linalg.norm(torque.sum(axis=0))/max(float(np.linalg.norm(torque, axis=1).sum()), 1e-12))
        # Geometric potential adjacency, not an invented pair-resolved contact-force ledger.
        adjacent_distances = []
        for cell in range(16):
            for other in (cell+1 if cell % 4 < 3 else -1, cell+4 if cell < 12 else -1):
                if other >= 0:
                    distance = np.linalg.norm(points[cell, :, None, :]-points[other, None, :, :], axis=2).min()
                    adjacent_distances.append(float(distance))
        detail = dict(volumes=volumes, areas=areas, minimum_angle=min(quality), crossings=crossings, containment=containment,
                      intercell_distance=float(separation["intercell_distance"][0]),
                      nonincident_distance=float(separation["nonincident_distance"][0]),
                      geometry_adjacent_distances=adjacent_distances, contact_support=float(states["contact_support_area"][0]),
                      contact_energy=float(states["contact_energy"][0]), passive_energy=float(states["passive_energy"][0]),
                      independent_passive_energy=pressure_energy, contact_force_balance=force_balance, contact_torque_balance=torque_balance,
                      fixed_nodes=int(nodes["fixed"].sum()), maximum_contact_traction=float((np.linalg.norm(contact, axis=1)/nodes["area"]).max()))
        checks[f"{case}_geometry"] = bool(topology_closed(faces, points.shape[1]) and min(volumes)>0 and min(quality)>=15
                            and crossings == containment == 0 and detail["intercell_distance"]>1e-8 and detail["nonincident_distance"]>1e-8
                            and np.allclose(positions, points.reshape(-1, 3), rtol=0, atol=1e-12))
        checks[f"{case}_finite"] = all(np.isfinite(nodes[key]).all() for key in nodes.dtype.names)
        checks[f"{case}_contact_balance"] = force_balance<=1e-10 and torque_balance<=1e-10
        checks[f"{case}_contact_support"] = len(adjacent_distances)==24 and max(adjacent_distances)<.35 and detail["contact_support"]>0
        checks[f"{case}_passive_energy"] = gradient_error(detail["passive_energy"], pressure_energy)<=1e-10
        checks[f"{case}_clamps"] = detail["fixed_nodes"] == 8*9*5 and np.max(np.linalg.norm(force[nodes["fixed"] == 1], axis=1)) == 0
        details[case] = detail
        for direction_name in ("translation", "shape"):
            direction = stored[direction_name].reshape(-1, 3)
            projected = {"total": -float((force*direction).sum()), "contact": -float((contact*direction).sum()),
                         "passive": -float((passive*direction).sum())}
            samples = []
            for exponent in (4, 5):
                perturbed = [read_csv(output/"static"/f"{case}_{direction_name}_e{exponent}_{sign}"/"states.csv")
                             for sign in ("plus", "minus")]
                gradients = {name: float((perturbed[0][f"{name}_energy"][0]-perturbed[1][f"{name}_energy"][0])/(2*10**(-exponent)))
                             for name in ("passive", "contact")}
                gradients["total"] = gradients["passive"]+gradients["contact"]
                samples.append(dict(epsilon=10**(-exponent), finite_difference=gradients, minus_force_dot_direction=projected,
                                    error={name: gradient_error(gradients[name], projected[name]) for name in projected}))
            best = {name: min(sample["error"][name] for sample in samples) for name in projected}
            groups.append(dict(case=case, direction=direction_name, best_error=best, samples=samples))
            checks[f"{case}_{direction_name}_gradient"] = best["total"]<=1e-6
    checks["matched_volumes"] = bool(np.max(np.abs(np.array(details["regular"]["volumes"])/np.array(details["irregular"]["volumes"])-1))<=1e-12)
    return dict(status="passed" if all(checks.values()) else "failed", checks={k: bool(v) for k,v in checks.items()}, cases=details,
                gradients=groups, pilot_status="not_run", equilibrium_status="not_run", biological_validation="not_run",
                adjacency_scope="24 expected geometric neighbors within cutoff, nonzero global contact support; not pair-resolved transmitted force",
                gradient_normalization="abs(FD+F.d)/max(1,abs(FD),abs(F.d)); conservative terms only")
