from __future__ import annotations

import hashlib
import csv
import json
from pathlib import Path

import numpy as np

from route_h.discretization import (
    CELL_CELL_MATERIALIZATION_GAP_CEILING,
    CELL_ECM_MATERIALIZATION_GAP_CEILING,
    FAMILY_DIRECTORY,
    LEVELS,
)
from route_h.contracts import assert_stage0_inputs
from route_h.geometry import (
    DIRECTION_CODES,
    ECM_BOUNDARY_CODES,
    INTERFACE_CODES,
    OWNER_CODES,
    PRIMARY_CODES,
    load_reference_bundle,
    signed_surface_volume,
    surface_topology_report,
    triangle_geometry,
    triangle_quality,
)


ROOT = Path(__file__).resolve().parents[2]


def test_family_manifest_and_level_hashes_are_complete(v06_levels):
    family_path = ROOT / FAMILY_DIRECTORY / "manifest.json"
    family = json.loads(family_path.read_text(encoding="utf-8"))
    assert family["status"] == "materialized_v06_candidate"
    assert [record["name"] for record in family["levels"]] == [
        "coarse",
        "base",
        "fine",
    ]
    assert family["base_reuse"]["all_22_arrays_byte_exact"] is True
    for record in family["levels"]:
        path = ROOT / FAMILY_DIRECTORY / record["manifest_path"]
        observed = hashlib.sha256(path.read_bytes()).hexdigest().upper()
        assert observed == record["manifest_sha256"]
        assert len(v06_levels[record["name"]][0]) == 22


def test_base_reuses_all_v05_arrays_byte_exact(v06_levels):
    sealed_v05, _ = load_reference_bundle()
    base, _ = v06_levels["base"]
    assert sorted(sealed_v05) == sorted(base)
    assert all(
        np.array_equal(sealed_v05[name], base[name])
        for name in sorted(sealed_v05)
    )


def test_level_counts_watertightness_quality_and_positive_volume(v06_levels):
    for level in LEVELS:
        arrays, _ = v06_levels[level.name]
        assert arrays["cell_vertices"].shape == (
            15,
            level.expected_cell_vertices,
            3,
        )
        assert arrays["cell_faces"].shape == (
            15,
            level.expected_cell_faces,
            3,
        )
        for vertices, faces in zip(
            arrays["cell_vertices"],
            arrays["cell_faces"],
            strict=True,
        ):
            report = surface_topology_report(faces)
            assert report["bad_incidence"] == 0
            assert report["bad_orientation"] == 0
            assert signed_surface_volume(vertices, faces) > 0.0
            assert float(np.min(triangle_quality(vertices, faces))) >= 0.30


def test_ecm_counts_orientation_boundary_and_thickness(v06_levels):
    for level in LEVELS:
        arrays, _ = v06_levels[level.name]
        assert arrays["ecm_vertices"].shape == (level.expected_ecm_vertices, 3)
        assert arrays["ecm_tetrahedra"].shape == (
            level.expected_ecm_tetrahedra,
            4,
        )
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
        assert min(determinants) > 0.0
        assert len(np.unique(vertices[:, 2])) == level.ecm_intervals[2] + 1
        boundary_report = surface_topology_report(arrays["ecm_boundary_faces"])
        assert boundary_report["bad_incidence"] == 0
        assert boundary_report["bad_orientation"] == 0
        assert np.all(
            np.isin(
                arrays["ecm_boundary_identity"],
                list(ECM_BOUNDARY_CODES.values()),
            )
        )


def _expected_tether_masters(arrays):
    expected = {
        INTERFACE_CODES["IF_ENDO_ECM"]: set(),
        INTERFACE_CODES["IF_MYO_ECM"]: set(),
        INTERFACE_CODES["IF_CELL_CELL"]: set(),
    }
    for cell_id in range(15):
        interface = (
            INTERFACE_CODES["IF_ENDO_ECM"]
            if cell_id < 6
            else INTERFACE_CODES["IF_MYO_ECM"]
        )
        basal = np.flatnonzero(
            arrays["cell_primary_identity"][cell_id]
            == PRIMARY_CODES["basal_ecm"]
        )
        expected[interface].update((cell_id, int(face_id)) for face_id in basal)
    for offset, nx, ny in ((0, 3, 2), (6, 3, 3)):
        for grid_j in range(ny):
            for grid_i in range(nx):
                cell_id = offset + grid_j * nx + grid_i
                if grid_i + 1 < nx:
                    face_ids = np.flatnonzero(
                        arrays["cell_directional_identity"][cell_id]
                        == DIRECTION_CODES["lateral_x_plus"]
                    )
                    expected[INTERFACE_CODES["IF_CELL_CELL"]].update(
                        (cell_id, int(face_id)) for face_id in face_ids
                    )
                if grid_j + 1 < ny:
                    face_ids = np.flatnonzero(
                        arrays["cell_directional_identity"][cell_id]
                        == DIRECTION_CODES["lateral_y_plus"]
                    )
                    expected[INTERFACE_CODES["IF_CELL_CELL"]].update(
                        (cell_id, int(face_id)) for face_id in face_ids
                    )
    return expected


def test_tether_coverage_identity_and_geometry_only_ceiling(v06_levels):
    for arrays, metadata in v06_levels.values():
        integers = arrays["material_tether_integer"]
        values = arrays["material_tether_float"]
        assert np.array_equal(integers[:, 1], np.arange(len(integers)))
        assert len(
            {tuple(row[[0, 2, 3, 4, 5]]) for row in integers}
        ) == len(integers)
        expected = _expected_tether_masters(arrays)
        for interface, expected_masters in expected.items():
            selected = integers[:, 0] == interface
            observed = {
                (int(row[2]), int(row[3]))
                for row in integers[selected]
            }
            assert observed == expected_masters
            ceiling = (
                CELL_CELL_MATERIALIZATION_GAP_CEILING
                if interface == INTERFACE_CODES["IF_CELL_CELL"]
                else CELL_ECM_MATERIALIZATION_GAP_CEILING
            )
            assert float(np.max(values[selected, 7])) <= ceiling + 1e-12
        assert float(np.min(values[:, 7])) >= -1e-12
        assert metadata["materialization_gap_ceiling_enters_mechanics"] is False


def test_anchor_source_owner_and_gauge_coverage(v06_levels):
    for arrays, _ in v06_levels.values():
        minimum_anchor_length = float("inf")
        expected_source = set()
        for cell_id in range(6, 15):
            vertices = arrays["cell_vertices"][cell_id]
            faces = arrays["cell_faces"][cell_id]
            areas, _ = triangle_geometry(vertices, faces)
            centers = []
            for column, key in enumerate(
                (
                    "cell_anchor_minus_face_ids",
                    "cell_anchor_plus_face_ids",
                )
            ):
                count = int(arrays["cell_anchor_counts"][cell_id, column])
                assert count > 0
                selected = arrays[key][cell_id, :count]
                weights = np.zeros(len(vertices))
                for face_id in selected:
                    weights[faces[face_id]] += areas[face_id] / 3.0
                centers.append(
                    np.sum(weights[:, None] * vertices, axis=0) / weights.sum()
                )
            minimum_anchor_length = min(
                minimum_anchor_length,
                float(np.linalg.norm(centers[1] - centers[0])),
            )
            basal = np.flatnonzero(
                arrays["cell_primary_identity"][cell_id]
                == PRIMARY_CODES["basal_ecm"]
            )
            expected_source.update((cell_id, int(face_id)) for face_id in basal)
        assert minimum_anchor_length >= 0.80
        source = arrays["myocardial_source_map_integer"]
        assert np.array_equal(source[:, 0], np.arange(len(source)))
        assert {(int(row[1]), int(row[2])) for row in source} == expected_source
        assert np.array_equal(
            source[:, 4],
            arrays["ecm_boundary_tetra"][source[:, 3]],
        )
        assert np.all(
            np.isin(
                arrays["cell_boundary_owner"],
                list(OWNER_CODES.values()),
            )
        )
        assert np.all(
            np.isin(
                arrays["ecm_boundary_owner"],
                list(OWNER_CODES.values()),
            )
        )
        assert np.all(arrays["cell_gauge_dual_area_weights"] > 0.0)
        assert np.all(arrays["ecm_gauge_lumped_volume_weights"] > 0.0)


def test_deterministic_replay_evidence_passes_all_levels():
    evidence = json.loads(
        (
            ROOT / "tests/route_h/stage0_v06_replay_results_v01.json"
        ).read_text(encoding="utf-8")
    )
    assert evidence["passed"] is True
    assert all(record["array_count"] == 22 for record in evidence["levels"])
    assert all(not record["unequal_arrays"] for record in evidence["levels"])


def test_v06_contract_cross_references_authority_and_family_hashes():
    assert len(assert_stage0_inputs()) == 8
    geometry_path = (
        ROOT / "data/route_h/route_h_spatial_discretization_family_v06.json"
    )
    contract_path = ROOT / "src/route_h/route_h_contract_v06.json"
    specialization_path = (
        ROOT / "src/route_h/route_h_model_specialization_v06.json"
    )
    cases_path = ROOT / "data/route_h/route_h_cases_v06.json"
    geometry = json.loads(geometry_path.read_text(encoding="utf-8"))
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    specialization = json.loads(specialization_path.read_text(encoding="utf-8"))
    cases = json.loads(cases_path.read_text(encoding="utf-8"))
    assert contract["contract_id"] == "CONTRACT-PRL-ROUTE-H-STAGE0-V06"
    assert specialization["contract_id"] == contract["contract_id"]
    assert cases["contract_id"] == contract["contract_id"]
    assert geometry["geometry_spec_id"] == specialization["geometry_spec_id"]
    assert geometry["geometry_spec_id"] == cases["geometry_spec_id"]
    for record in contract["direct_inputs"]:
        path = ROOT / record["path"]
        assert hashlib.sha256(path.read_bytes()).hexdigest().upper() == record["sha256"]
    family_record = geometry["family_manifest"]
    family_path = ROOT / family_record["path"]
    assert (
        hashlib.sha256(family_path.read_bytes()).hexdigest().upper()
        == family_record["sha256"]
    )
    assert cases["global_rules"]["stage2_authorized"] is True
    assert cases["global_rules"]["space_refinement_registered"] is True
    assert cases["spatial_refinement_registry"]["relative_difference_max"] == 0.03


def test_v06_preserves_the_v05_mechanical_contract_and_parameters():
    v05 = json.loads(
        (ROOT / "src/route_h/route_h_contract_v05.json").read_text(encoding="utf-8")
    )
    v06 = json.loads(
        (ROOT / "src/route_h/route_h_contract_v06.json").read_text(encoding="utf-8")
    )
    invariant_sections = [
        "scientific_object",
        "nondimensionalization",
        "coordinate_and_load_convention",
        "registered_time_protocols",
        "primary_dynamics",
        "cell_passive_energy",
        "active_preferred_length",
        "contact_and_adhesion",
        "ECM_constitutive_contract",
        "myocardial_source_map",
        "boundary_contract",
        "support_and_power_contract",
        "flow_sensor",
        "power_balance",
        "time_refinement_observables",
    ]
    assert all(v06[key] == v05[key] for key in invariant_sections)
    v05_specialization = json.loads(
        (
            ROOT / "src/route_h/route_h_model_specialization_v05.json"
        ).read_text(encoding="utf-8")
    )
    v06_specialization = json.loads(
        (
            ROOT / "src/route_h/route_h_model_specialization_v06.json"
        ).read_text(encoding="utf-8")
    )
    invariant_specialization_sections = [
        key
        for key in v05_specialization
        if key
        not in {
            "specialization_id",
            "schema_version",
            "created_at",
            "status",
            "contract_id",
            "geometry_spec_id",
            "supersedes",
            "numerical_preregistration",
            "acceptance_thresholds",
            "deferred_before_stage2",
            "stage2_authorized",
        }
    ]
    assert all(
        v06_specialization[key] == v05_specialization[key]
        for key in invariant_specialization_sections
    )


def test_v06_registry_closes_only_the_discretization_preregistration_gap():
    path = ROOT / "tests/route_h/route_h_verification_registry_v06.csv"
    with path.open("r", encoding="utf-8", newline="") as stream:
        rows = list(csv.DictReader(stream))
    test_ids = [row["test_id"] for row in rows]
    assert len(test_ids) == len(set(test_ids))
    assert "STAGE2-DISCRETIZATION-BLOCK" not in test_ids
    assert "SPACE-REFINEMENT-DEFERRED" not in test_ids
    required = {
        "AUTH-STAGE2-GATE",
        "SPACE-FAMILY-SPEC",
        "STAGE2-DISCRETIZATION-SEAL",
        "SPACE-LEVEL-COUNTS",
        "SPACE-BASE-BYTE-REUSE",
        "SPACE-GEOMETRY-VALIDITY",
        "SPACE-MAP-COVERAGE",
        "SPACE-DETERMINISTIC-REPLAY",
        "SPACE-REFERENCE-SEAL",
        "SPACE-REFINEMENT",
    }
    assert required <= set(test_ids)
    spatial = next(row for row in rows if row["test_id"] == "SPACE-REFINEMENT")
    assert spatial["stage"] == "2"
    assert spatial["gate"] == "E"
    assert spatial["threshold"] == "0.03"
    assert spatial["case_ids"] == "E0_ZERO;E4_COMBINED"
