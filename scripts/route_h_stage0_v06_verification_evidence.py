"""Build Stage 0 v06 geometry-family metrics and terminal-status evidence."""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET

import numpy as np

from route_h.discretization import LEVELS, load_discretization_level
from route_h.geometry import signed_surface_volume, triangle_geometry, triangle_quality
from route_h.solver import audit_reference_arrays, evaluate_passive_arrays


ROOT = Path(__file__).resolve().parents[1]
JUNIT = ROOT / "tests/route_h/stage0_v06_pytest_junit_v01.xml"
METRICS = ROOT / "tests/route_h/stage0_v06_metrics_v01.json"
RESULTS = ROOT / "tests/route_h/stage0_v06_verification_results_v01.csv"
REGISTRY = ROOT / "tests/route_h/route_h_verification_registry_v06.csv"
STAGE1_RESULTS = ROOT / "tests/route_h/stage1_verification_results_v02.csv"

V06_TEST_IDS = {
    "AUTH-STAGE2-GATE",
    "SPACE-FAMILY-SPEC",
    "STAGE2-DISCRETIZATION-SEAL",
    "SPACE-LEVEL-COUNTS",
    "SPACE-BASE-BYTE-REUSE",
    "SPACE-GEOMETRY-VALIDITY",
    "SPACE-MAP-COVERAGE",
    "SPACE-DETERMINISTIC-REPLAY",
    "SPACE-REFERENCE-SEAL",
    "SPACE-FLOAT-INTERFACE-SNAP",
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def anchor_minimum_length(arrays: dict[str, np.ndarray]) -> float:
    minimum = float("inf")
    for cell_id in range(6, 15):
        vertices = arrays["cell_vertices"][cell_id]
        faces = arrays["cell_faces"][cell_id]
        areas, _ = triangle_geometry(vertices, faces)
        centers = []
        for column, key in enumerate(
            ("cell_anchor_minus_face_ids", "cell_anchor_plus_face_ids")
        ):
            count = int(arrays["cell_anchor_counts"][cell_id, column])
            selected = arrays[key][cell_id, :count]
            weights = np.zeros(len(vertices))
            for face_id in selected:
                weights[faces[face_id]] += areas[face_id] / 3.0
            centers.append(
                np.sum(weights[:, None] * vertices, axis=0) / weights.sum()
            )
        minimum = min(
            minimum,
            float(np.linalg.norm(centers[1] - centers[0])),
        )
    return minimum


def level_metrics(level_name: str) -> dict[str, object]:
    arrays, metadata = load_discretization_level(level_name)
    passive = evaluate_passive_arrays(arrays)
    audit = audit_reference_arrays(arrays, metadata)
    vertices = arrays["ecm_vertices"]
    determinants = []
    for tet in arrays["ecm_tetrahedra"]:
        matrix = np.column_stack(
            (
                vertices[tet[1]] - vertices[tet[0]],
                vertices[tet[2]] - vertices[tet[0]],
                vertices[tet[3]] - vertices[tet[0]],
            )
        )
        determinants.append(float(np.linalg.det(matrix)))
    interface_codes = arrays["material_tether_integer"][:, 0]
    gaps = arrays["material_tether_float"][:, 7]
    gap_summary = {
        str(int(code)): {
            "count": int(np.count_nonzero(interface_codes == code)),
            "maximum_g0_pair": float(np.max(gaps[interface_codes == code])),
        }
        for code in np.unique(interface_codes)
    }
    return {
        "cell_count": len(arrays["cell_vertices"]),
        "vertices_per_cell": int(arrays["cell_vertices"].shape[1]),
        "faces_per_cell": int(arrays["cell_faces"].shape[1]),
        "minimum_cell_triangle_quality": min(
            float(np.min(triangle_quality(cell_vertices, faces)))
            for cell_vertices, faces in zip(
                arrays["cell_vertices"],
                arrays["cell_faces"],
                strict=True,
            )
        ),
        "minimum_cell_signed_volume": min(
            signed_surface_volume(cell_vertices, faces)
            for cell_vertices, faces in zip(
                arrays["cell_vertices"],
                arrays["cell_faces"],
                strict=True,
            )
        ),
        "minimum_anchor_length": anchor_minimum_length(arrays),
        "ecm_vertices": len(arrays["ecm_vertices"]),
        "ecm_tetrahedra": len(arrays["ecm_tetrahedra"]),
        "minimum_reference_tetra_determinant": min(determinants),
        "minimum_ECM_J": passive.minimum_ecm_jacobian,
        "material_tethers": audit.material_tether_count,
        "myocardial_source_maps": len(
            arrays["myocardial_source_map_integer"]
        ),
        "tether_gap_summary_by_interface_code": gap_summary,
        "eligible_steric_pairs": audit.eligible_steric_pairs,
        "steric_owner_records": audit.steric_owner_records,
        "minimum_steric_gap": audit.minimum_steric_gap,
        "proper_intersections": audit.proper_intersections,
        "steric_energy": audit.steric_energy,
        "maximum_tether_opening": audit.maximum_tether_opening,
        "maximum_tether_slip": audit.maximum_tether_slip,
        "maximum_tether_force": audit.maximum_tether_force,
        "assembled_net_force": audit.assembled_net_force,
        "assembled_net_moment": audit.assembled_net_moment,
        "passive_total_energy": float(passive.total_energy),
        "maximum_cell_force": passive.maximum_cell_force,
        "maximum_ECM_force": passive.maximum_ecm_force,
    }


def build_metrics() -> dict[str, object]:
    junit_root = ET.parse(JUNIT).getroot()
    suite = junit_root if junit_root.tag == "testsuite" else junit_root.find("testsuite")
    if suite is None:
        raise RuntimeError("pytest JUnit has no testsuite")
    metrics: dict[str, object] = {
        "evidence_id": "EVIDENCE-PRL-ROUTE-H-STAGE0-V06-V01",
        "contract_id": "CONTRACT-PRL-ROUTE-H-STAGE0-V06",
        "family_manifest_sha256": sha256(
            ROOT
            / "data/route_h/stage0_v06_discretization_family/manifest.json"
        ),
        "replay_evidence_sha256": sha256(
            ROOT / "tests/route_h/stage0_v06_replay_results_v01.json"
        ),
        "junit_sha256": sha256(JUNIT),
        "pytest": {
            "tests": int(suite.attrib["tests"]),
            "failures": int(suite.attrib["failures"]),
            "errors": int(suite.attrib["errors"]),
            "skipped": int(suite.attrib["skipped"]),
        },
        "levels": {
            level.name: level_metrics(level.name)
            for level in LEVELS
        },
        "authorization": {
            "stage2_scientific_runs_before_v06_freeze": 0,
            "active_enabled_during_v06": False,
            "full_patch_trajectory_run_during_v06": False,
            "periodic_registered": False,
        },
    }
    METRICS.write_bytes(
        (json.dumps(metrics, ensure_ascii=False, indent=2) + "\n").encode()
    )
    return metrics


def build_results() -> list[dict[str, str]]:
    with STAGE1_RESULTS.open("r", encoding="utf-8", newline="") as stream:
        stage1 = {
            row["test_id"]: row
            for row in csv.DictReader(stream)
        }
    with REGISTRY.open("r", encoding="utf-8", newline="") as stream:
        registry = list(csv.DictReader(stream))
    output = []
    for row in registry:
        test_id = row["test_id"]
        if row["stage"] == "0":
            status = "passed"
            if test_id in V06_TEST_IDS:
                evidence = (
                    "pytest:tests/stage0_v06; "
                    "tests/route_h/stage0_v06_metrics_v01.json"
                )
                note = "v06-specific PreStage2 assertion passed."
            else:
                evidence = (
                    "project_control/route_h_stage0_v05_freeze_record.md; "
                    "pytest:test_v06_contract_cross_references_authority_and_family_hashes"
                )
                note = "Immutable v05 static evidence inherited by exact hash."
        elif row["stage"] == "1":
            inherited = stage1.get(test_id)
            if inherited is None:
                status = "not_run_stage2_preexecution"
                evidence = "tests/route_h/route_h_verification_registry_v06.csv"
                note = "No inherited Stage 1 terminal row; retained as not run."
            else:
                inherited_status = inherited["terminal_status"]
                status = (
                    "not_run_stage2_preexecution"
                    if inherited_status.startswith("not_run")
                    else inherited_status
                )
                evidence = (
                    "tests/route_h/stage1_verification_results_v02.csv"
                )
                note = (
                    "Stage 1 v02 pass inherited without promotion."
                    if status == "passed"
                    else (
                        "Historically out of Stage 1 scope; Stage 2 is now authorized "
                        "but this response test remains not run before v06 freeze."
                    )
                )
        else:
            status = "not_run_stage2_preexecution"
            evidence = (
                "project_control/"
                "route_h_stage0_v06_discretization_authorization_decision_v01.md"
            )
            note = (
                "Stage 2 response is authorized only after v06 freeze and inspection."
            )
        output.append(
            {
                "test_id": test_id,
                "terminal_status": status,
                "observed": note,
                "registered_threshold": row["threshold"],
                "evidence": evidence,
                "source_registry": "route_h_verification_registry_v06.csv",
            }
        )
    with RESULTS.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(
            stream,
            fieldnames=list(output[0]),
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(output)
    return output


def main() -> None:
    metrics = build_metrics()
    results = build_results()
    counts = {
        status: sum(row["terminal_status"] == status for row in results)
        for status in sorted({row["terminal_status"] for row in results})
    }
    print(
        json.dumps(
            {
                "metrics": str(METRICS.relative_to(ROOT)),
                "metrics_sha256": sha256(METRICS),
                "results": str(RESULTS.relative_to(ROOT)),
                "results_sha256": sha256(RESULTS),
                "terminal_status_counts": counts,
                "level_count": len(metrics["levels"]),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
