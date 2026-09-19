"""Replay the actual failed P3 native export; no Docker or FEM solve."""
from pathlib import Path
import hashlib
import json

import numpy as np
import pytest

from prl.fem.nodal_export import canonical_nodal_cells
from prl.verification.mixed_cube_space import kinematics, mapping_checks
from prl.verification.mixed_cube import assembled, error_metrics, exact_fields


FIXTURE = Path(__file__).parent / 'fixtures' / 'p3_native_orientation_v01.npz'


def native_fixture():
    provenance = json.loads(FIXTURE.with_suffix('.json').read_text(encoding='utf-8'))
    assert hashlib.sha256(FIXTURE.read_bytes()).hexdigest() == provenance['sha256']
    with np.load(FIXTURE, allow_pickle=False) as saved:
        return dict(saved)


def test_actual_failure_is_retained_and_export_reordering_is_bijective():
    data = native_fixture()
    original = {key: value.copy() for key, value in data.items()}
    assert not mapping_checks(data)['u_degree_nodes']
    cells, slots = canonical_nodal_cells(data['coordinates'], data['cells'], data['u_reference_nodes'])
    assert np.count_nonzero(np.any(slots != np.arange(20), axis=1)) == 22
    np.testing.assert_array_equal(np.sort(cells, axis=1), np.sort(data['cells'], axis=1))
    np.testing.assert_array_equal(cells[:, :4], data['cells'][:, :4])
    for key, value in original.items():
        np.testing.assert_array_equal(data[key], value)
    data['cells'] = cells
    data['native_cells'] = original['cells']
    data['u_canonical_to_native_slots'] = slots
    assert all(mapping_checks(data).values())
    second, identity = canonical_nodal_cells(data['coordinates'], cells, data['u_reference_nodes'])
    np.testing.assert_array_equal(second, cells)
    np.testing.assert_array_equal(identity, np.tile(np.arange(20), (len(cells), 1)))
    pcells, pslots = canonical_nodal_cells(data['pressure_coordinates'], data['pressure_cells'],
                                         data['p_reference_nodes'])
    np.testing.assert_array_equal(pcells, data['pressure_cells'])
    np.testing.assert_array_equal(pslots, np.tile(np.arange(10), (len(pcells), 1)))
    data['u_canonical_to_native_slots'] = np.tile(np.arange(20), (len(cells), 1))
    assert not mapping_checks(data)['u_export_permutation']


def test_real_oriented_mesh_recovers_cubic_field_gradient_and_equilibrium():
    data = native_fixture()
    case = {'kind': 'cubic_volume', 'kappa': 1000.}
    state = {'u': exact_fields(data['coordinates'], case['kind'], case['kappa'])['u'],
             'pressure': exact_fields(data['pressure_coordinates'], case['kind'], case['kappa'])['pressure']}
    old, _ = error_metrics(data, state, case)
    assert old['relative_u_H1'] > .01
    data['cells'], _ = canonical_nodal_cells(data['coordinates'], data['cells'], data['u_reference_nodes'])
    metrics, _ = error_metrics(data, state, case)
    assert metrics['relative_u_H1'] < 1e-11
    assert metrics['max_abs_J_error'] < 1e-12
    fields = assembled(data, state, case)
    assert np.linalg.norm(fields['force'][~data['fixed']]) < 1e-10
    assert np.linalg.norm(fields['weak']) < 1e-12
    # A general cubic cross term detects more than the x-only patch can detect.
    xyz = data['coordinates']; u = np.zeros_like(xyz)
    u[:, 1] = xyz[:, 0] * xyz[:, 1] * xyz[:, 2]
    points = data['qpoints']
    F, _, _, _, bary, vertices = kinematics(data, u, points)
    physical = np.einsum('qa,cai->cqi', bary, vertices)
    gradient = np.stack((physical[..., 1]*physical[..., 2],
                         physical[..., 0]*physical[..., 2],
                         physical[..., 0]*physical[..., 1]), axis=-1)
    np.testing.assert_allclose(F[:, :, 1] - np.array([0., 1., 0.]), gradient, atol=5e-13, rtol=0)


@pytest.mark.parametrize('corruption', ['duplicate', 'displaced', 'nonfinite', 'wrong_vertex', 'degenerate'])
def test_malformed_native_export_fails_closed(corruption):
    data = native_fixture(); coords = data['coordinates']; cells = data['cells']; nodes = data['u_reference_nodes']
    if corruption == 'duplicate':
        cells[0, 5] = cells[0, 4]
    elif corruption == 'displaced':
        coords[cells[0, 4], 0] += .001
    elif corruption == 'nonfinite':
        coords[0, 0] = np.nan
    elif corruption == 'wrong_vertex':
        nodes[[0, 1]] = nodes[[1, 0]]
    else:
        cells[0, 3] = cells[0, 2]
    with pytest.raises(ValueError):
        canonical_nodal_cells(coords, cells, nodes)
