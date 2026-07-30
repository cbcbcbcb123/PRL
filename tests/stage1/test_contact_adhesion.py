from __future__ import annotations

import numpy as np

from route_h.contact_adhesion import (
    _ordered_binary64_sum,
    material_tether_energy_force_with_reference,
    pair_residuals,
    proper_triangle_crossing_ccd,
    signed_surface_distance,
    steric_pair_energy_force,
)


def _cube():
    vertices = np.array([
        [0, 0, 0], [1, 0, 0], [1, 1, 0], [0, 1, 0],
        [0, 0, 1], [1, 0, 1], [1, 1, 1], [0, 1, 1],
    ], dtype=float)
    faces = np.array([
        [0, 2, 1], [0, 3, 2],
        [4, 5, 6], [4, 6, 7],
        [0, 1, 5], [0, 5, 4],
        [1, 2, 6], [1, 6, 5],
        [2, 3, 7], [2, 7, 6],
        [3, 0, 4], [3, 4, 7],
    ], dtype=np.int64)
    return vertices, faces


def _tether_record(bundle, interface_code=3):
    arrays, metadata = bundle
    row = int(np.flatnonzero(
        arrays["material_tether_integer"][:, 0] == interface_code
    )[0])
    integer = arrays["material_tether_integer"][row]
    value = arrays["material_tether_float"][row]
    return arrays, integer, value


def _evaluate_tether(arrays, integer, value, master, slave, reference_master, reference_slave):
    master_id, master_face_id, slave_id, slave_face_id = map(
        int, (integer[2], integer[3], integer[4], integer[5])
    )
    return material_tether_energy_force_with_reference(
        master,
        arrays["cell_faces"][master_id][master_face_id],
        slave,
        arrays["cell_faces"][slave_id][slave_face_id],
        reference_master_vertices=reference_master,
        reference_slave_vertices=reference_slave,
        master_barycentric=value[:3],
        slave_barycentric=value[3:6],
        reference_weight=float(value[6]),
        g0_pair=float(value[7]),
        normal_orientation_sign=float(value[8]),
        reference_t1=value[9:12],
        reference_t2=value[12:15],
        adhesion_work=0.02,
        tangential_stiffness=0.5,
    )


def test_tether_reference_opening_slip_and_force_are_zero(bundle):
    arrays, integer, value = _tether_record(bundle)
    master_id, slave_id = int(integer[2]), int(integer[4])
    master = arrays["cell_vertices"][master_id]
    slave = arrays["cell_vertices"][slave_id]
    energies, master_force, slave_force, state = _evaluate_tether(
        arrays, integer, value, master, slave, master, slave
    )
    assert abs(state["opening"]) < 1e-12
    assert np.linalg.norm(state["slip"]) < 1e-12
    assert np.linalg.norm(master_force) < 1e-12
    assert np.linalg.norm(slave_force) < 1e-12
    assert energies["adhesion_normal"] < 0.0


def test_tether_complete_force_directional_derivative_action_reaction_and_objectivity(bundle):
    arrays, integer, value = _tether_record(bundle)
    master_id, slave_id = int(integer[2]), int(integer[4])
    reference_master = arrays["cell_vertices"][master_id]
    reference_slave = arrays["cell_vertices"][slave_id]
    master = reference_master.copy()
    slave = reference_slave + np.array([0.01, 0.004, -0.003])
    energies, master_force, slave_force, _ = _evaluate_tether(
        arrays, integer, value, master, slave, reference_master, reference_slave
    )
    rng = np.random.default_rng(22)
    direction_master = rng.standard_normal(master.shape)
    direction_slave = rng.standard_normal(slave.shape)
    direction_master /= np.linalg.norm(direction_master)
    direction_slave /= np.linalg.norm(direction_slave)
    step = 1e-7
    plus = _evaluate_tether(
        arrays, integer, value,
        master + step * direction_master, slave + step * direction_slave,
        reference_master, reference_slave,
    )[0]["adhesion_total"]
    minus = _evaluate_tether(
        arrays, integer, value,
        master - step * direction_master, slave - step * direction_slave,
        reference_master, reference_slave,
    )[0]["adhesion_total"]
    finite = (plus - minus) / (2 * step)
    mf = arrays["cell_faces"][master_id][int(integer[3])]
    sf = arrays["cell_faces"][slave_id][int(integer[5])]
    analytic = -float(
        np.sum(master_force * direction_master[mf])
        + np.sum(slave_force * direction_slave[sf])
    )
    assert abs(finite - analytic) / max(1.0, abs(finite), abs(analytic)) < 1e-5
    force_residual, moment_residual = pair_residuals(
        master[mf], master_force, slave[sf], slave_force
    )
    assert force_residual < 1e-10
    assert moment_residual < 1e-10
    assert np.isfinite(energies["adhesion_total"])

    angle = 0.31
    rotation = np.array([
        [np.cos(angle), 0.0, np.sin(angle)],
        [0.0, 1.0, 0.0],
        [-np.sin(angle), 0.0, np.cos(angle)],
    ])
    translation = np.array([0.2, -0.4, 0.6])
    rotated_value = value.copy()
    rotated_value[9:12] = value[9:12] @ rotation.T
    rotated_value[12:15] = value[12:15] @ rotation.T
    rotated = _evaluate_tether(
        arrays, integer, rotated_value,
        master @ rotation.T + translation,
        slave @ rotation.T + translation,
        reference_master @ rotation.T + translation,
        reference_slave @ rotation.T + translation,
    )
    assert abs(rotated[0]["adhesion_total"] - energies["adhesion_total"]) < 1e-12
    assert np.linalg.norm(rotated[1] - master_force @ rotation.T) < 1e-9
    assert np.linalg.norm(rotated[2] - slave_force @ rotation.T) < 1e-9


def test_tension_only_compression_slack_has_no_normal_force(bundle):
    arrays, integer, value = _tether_record(bundle)
    master_id, slave_id = int(integer[2]), int(integer[4])
    reference_master = arrays["cell_vertices"][master_id]
    reference_slave = arrays["cell_vertices"][slave_id]
    normal = value[8] * np.cross(
        reference_master[arrays["cell_faces"][master_id][int(integer[3])][1]]
        - reference_master[arrays["cell_faces"][master_id][int(integer[3])][0]],
        reference_master[arrays["cell_faces"][master_id][int(integer[3])][2]]
        - reference_master[arrays["cell_faces"][master_id][int(integer[3])][0]],
    )
    normal /= np.linalg.norm(normal)
    slave = reference_slave - 0.01 * normal
    _, master_force, slave_force, state = _evaluate_tether(
        arrays, integer, value,
        reference_master, slave, reference_master, reference_slave,
    )
    assert state["opening"] < 0.0
    assert np.linalg.norm(state["slip"]) < 1e-10
    assert np.linalg.norm(master_force) < 1e-9
    assert np.linalg.norm(slave_force) < 1e-9


def test_closed_surface_signed_distance_disjoint_and_inside():
    vertices, faces = _cube()
    outside, state_out, _ = signed_surface_distance(
        np.array([-1.0, 0.5, 0.5]), vertices, faces
    )
    inside, state_in, _ = signed_surface_distance(
        np.array([0.5, 0.5, 0.5]), vertices, faces
    )
    assert state_out == "outside" and abs(outside - 1.0) < 1e-12
    assert state_in == "inside" and abs(inside + 0.5) < 1e-12


def test_winding_accumulator_is_strictly_sequential_binary64():
    adversarial = np.asarray([1e16] + [1.0] * 1000 + [-1e16], dtype=np.float64)
    assert _ordered_binary64_sum(adversarial) == 0.0
    assert float(np.sum(adversarial)) == 986.0


def test_steric_selected_piece_derivative_and_pair_balance():
    target, faces = _cube()
    source = np.array([[0.5, 0.5, 0.45]])
    weights = np.array([0.2])
    energy, source_force, target_force, records = steric_pair_energy_force(
        source, np.array([0]), weights, target, faces
    )
    assert energy > 0.0
    assert records[0].signed_gap < 0.0
    direction_source = np.array([[0.02, -0.01, 0.03]])
    direction_target = np.zeros_like(target)
    step = 1e-7
    plus = steric_pair_energy_force(
        source + step * direction_source, np.array([0]), weights,
        target + step * direction_target, faces,
    )[0]
    minus = steric_pair_energy_force(
        source - step * direction_source, np.array([0]), weights,
        target - step * direction_target, faces,
    )[0]
    finite = (plus - minus) / (2 * step)
    analytic = -float(np.sum(source_force * direction_source) + np.sum(target_force * direction_target))
    assert abs(finite - analytic) < 1e-7
    assert np.linalg.norm(source_force.sum(axis=0) + target_force.sum(axis=0)) < 1e-12
    moment = np.cross(source, source_force).sum(axis=0) + np.cross(target, target_force).sum(axis=0)
    assert np.linalg.norm(moment) < 1e-12


def test_disjoint_steric_energy_force_moment_zero():
    target, faces = _cube()
    source = target + np.array([2.0, 0.0, 0.0])
    energy, source_force, target_force, records = steric_pair_energy_force(
        source, np.arange(8), np.ones(8), target, faces
    )
    assert energy == 0.0
    assert np.count_nonzero(source_force) == 0
    assert np.count_nonzero(target_force) == 0
    assert all(record.signed_gap >= 0.0 for record in records)


def test_ccd_rejects_transverse_crossing_and_allows_endpoint_tangency():
    triangle_a = np.array([[0., 0., 0.], [1., 0., 0.], [0., 1., 0.]])
    start = np.array([[0.2, 0.2, 1.], [0.7, 0.2, 1.], [0.2, 0.7, 1.]])
    crossed = start.copy()
    crossed[:, 2] = -1.0
    tangent = start.copy()
    tangent[:, 2] = 0.0
    assert proper_triangle_crossing_ccd(triangle_a, triangle_a, start, crossed)
    assert not proper_triangle_crossing_ccd(triangle_a, triangle_a, start, tangent)
