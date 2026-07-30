from __future__ import annotations

import hashlib
import json
import re

import numpy as np

from route_h.contracts import assert_stage0_inputs
from route_h.dcm_cell import build_cell_reference
from route_h.geometry import (
    DIRECTION_CODES,
    ECM_BOUNDARY_CODES,
    OWNER_CODES,
    PRIMARY_CODES,
    build_cells,
    materialize_reference_bundle,
    signed_surface_volume,
    surface_topology_report,
    triangle_geometry,
    triangle_quality,
)
from route_h.solver import audit_reference_seal


def test_frozen_v05_inputs_and_freeze_record_are_byte_exact():
    observed = assert_stage0_inputs()
    assert len(observed) == 8
    freeze_path = (
        __import__("pathlib").Path(__file__).resolve().parents[2]
        / "project_control/route_h_stage0_v05_freeze_record.md"
    )
    root = freeze_path.parents[1]
    rows = re.findall(
        r"\| \d+ \| `([^`]+)` \| \d+ \| `([0-9A-F]{64})` \|",
        freeze_path.read_text(encoding="utf-8"),
    )
    assert len(rows) == 8
    assert all(
        hashlib.sha256((root / path).read_bytes()).hexdigest().upper() == expected
        for path, expected in rows
    )


def test_reference_bundle_hash_is_deterministic(tmp_path, bundle):
    _, metadata = bundle
    manifest = materialize_reference_bundle(tmp_path)
    canonical = json.loads((tmp_path / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["bundle_sha256"] == canonical["bundle_sha256"]
    assert manifest["bundle_sha256"] == "4A73D370162D8EBFB7B120C42881F7470D68E82D10ABD159CB65C2B73ADECC59"
    assert metadata["contract_id"] == "CONTRACT-PRL-ROUTE-H-STAGE0-V05"


def test_mesh_counts_and_cell_geometry(bundle):
    arrays, _ = bundle
    assert arrays["cell_vertices"].shape == (15, 162, 3)
    assert arrays["cell_faces"].shape == (15, 320, 3)
    assert arrays["ecm_vertices"].shape == (351, 3)
    assert arrays["ecm_tetrahedra"].shape == (1152, 4)
    for vertices, faces in zip(arrays["cell_vertices"], arrays["cell_faces"], strict=True):
        report = surface_topology_report(faces)
        assert report["bad_incidence"] == 0
        assert report["bad_orientation"] == 0
        assert signed_surface_volume(vertices, faces) > 0.0
        assert float(np.min(triangle_quality(vertices, faces))) >= 0.30


def test_face_identity_partition_and_floating_tie_symmetry(bundle):
    arrays, _ = bundle
    primary = arrays["cell_primary_identity"]
    directional = arrays["cell_directional_identity"]
    assert np.all(np.isin(primary, list(PRIMARY_CODES.values())))
    assert np.all((primary == PRIMARY_CODES["lateral"]) == (directional != 0))
    counts = {
        code: int(np.count_nonzero(directional[0] == code))
        for code in DIRECTION_CODES.values() if code
    }
    assert set(counts.values()) == {52}
    cells = build_cells()
    assert all(np.array_equal(cell.directional, directional[index]) for index, cell in enumerate(cells))


def test_myocardial_anchors_are_hashed_nonempty_and_long(bundle):
    arrays, _ = bundle
    for cell_id in range(6, 15):
        vertices = arrays["cell_vertices"][cell_id]
        faces = arrays["cell_faces"][cell_id]
        areas, _ = triangle_geometry(vertices, faces)
        centroids = []
        for column, key in enumerate(("cell_anchor_minus_face_ids", "cell_anchor_plus_face_ids")):
            count = int(arrays["cell_anchor_counts"][cell_id, column])
            ids = arrays[key][cell_id, :count]
            assert count > 0
            weights = np.zeros(len(vertices))
            for face_id in ids:
                weights[faces[face_id]] += areas[face_id] / 3.0
            centroids.append(np.sum(weights[:, None] * vertices, axis=0) / weights.sum())
        assert np.linalg.norm(centroids[1] - centroids[0]) >= 0.80


def test_ecm_orientation_boundary_and_two_thickness_layers(bundle):
    arrays, _ = bundle
    vertices, tets = arrays["ecm_vertices"], arrays["ecm_tetrahedra"]
    determinants = []
    for tet in tets:
        dm = np.column_stack((
            vertices[tet[1]] - vertices[tet[0]],
            vertices[tet[2]] - vertices[tet[0]],
            vertices[tet[3]] - vertices[tet[0]],
        ))
        determinants.append(np.linalg.det(dm))
    assert min(determinants) > 0.0
    assert set(np.unique(vertices[:, 2])) == {0.0, 0.1, 0.2}
    report = surface_topology_report(arrays["ecm_boundary_faces"])
    assert report["bad_incidence"] == 0
    assert report["bad_orientation"] == 0
    assert len(arrays["ecm_boundary_faces"]) == 544
    assert np.all(np.isin(arrays["ecm_boundary_identity"], list(ECM_BOUNDARY_CODES.values())))


def test_tether_coverage_identity_and_reference_natural_state(bundle):
    arrays, _ = bundle
    integers = arrays["material_tether_integer"]
    values = arrays["material_tether_float"]
    assert len(integers) == 1828
    assert np.array_equal(integers[:, 1], np.arange(len(integers)))
    assert len({tuple(row[[0, 2, 3, 4, 5]]) for row in integers}) == len(integers)
    assert np.max(np.abs(values[:, :3] - 1.0 / 3.0)) < 1e-15
    assert np.max(np.abs(values[:, 3:6].sum(axis=1) - 1.0)) < 1e-12
    assert np.min(values[:, 3:6]) >= -1e-12
    assert np.max(values[:, 7]) <= 0.15 + 1e-12
    assert np.min(values[:, 7]) >= -1e-12


def test_source_map_unique_coverage_and_zero_owner_semantics(bundle):
    arrays, _ = bundle
    records = arrays["myocardial_source_map_integer"]
    values = arrays["myocardial_source_map_float"]
    assert len(records) == 504
    assert np.array_equal(records[:, 0], np.arange(504))
    assert len({(int(row[1]), int(row[2])) for row in records}) == 504
    assert np.array_equal(
        records[:, 4], arrays["ecm_boundary_tetra"][records[:, 3]]
    )
    assert np.max(np.abs(values[:, :3] - 1.0 / 3.0)) < 1e-15
    assert np.all(values[:, 6] > 0.0)


def test_boundary_owner_exclusivity_and_gauge_weights(bundle):
    arrays, _ = bundle
    assert np.all(np.isin(arrays["cell_boundary_owner"], list(OWNER_CODES.values())))
    assert np.all(np.isin(arrays["ecm_boundary_owner"], list(OWNER_CODES.values())))
    assert np.all(arrays["cell_gauge_dual_area_weights"] > 0.0)
    assert np.all(arrays["ecm_gauge_lumped_volume_weights"] > 0.0)
    assert np.count_nonzero(arrays["ecm_boundary_owner"] == OWNER_CODES["traction_free"]) > 0


def test_reference_cell_targets_are_exact(bundle):
    arrays, _ = bundle
    reference = build_cell_reference(
        arrays["cell_vertices"][6],
        arrays["cell_faces"][6],
        arrays["cell_primary_identity"][6],
        arrays["cell_directional_identity"][6],
    )
    assert reference.volume0 > 0.0
    assert len(reference.hinges.vertices) == 480
    assert np.all(reference.area0 > 0.0)


def test_full_reference_seal_has_zero_steric_force_moment_and_intersection():
    audit = audit_reference_seal()
    assert audit.eligible_steric_pairs == 46
    assert audit.steric_owner_records == 16584
    assert audit.steric_energy == 0.0
    assert audit.minimum_steric_gap >= 0.0
    assert audit.proper_intersections == 0
    assert audit.material_tether_count == 1828
    assert audit.maximum_tether_opening < 1e-12
    assert audit.maximum_tether_slip < 1e-12
    assert audit.maximum_tether_force < 1e-10
    assert audit.assembled_net_force < 1e-10
    assert audit.assembled_net_moment < 1e-10
