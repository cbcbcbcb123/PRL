"""Small array counterexamples, not new scientific equilibria or native solves."""
import numpy as np
import pytest

from prl.verification.representation_guard_diagnosis import (
    endpoint_scan, path_probe, registered_failure, sampled_failure)


def test_registered_budget_can_reject_every_endpoint_despite_smaller_safe_step():
    base = np.eye(3)[None, None]
    direction = np.zeros_like(base)
    direction[..., 0, 0] = -1.5 * 2.**20
    rows = endpoint_scan(base, direction)
    assert len(rows) == 21
    assert all(row['minimum_J'] < 0 for row in rows)
    assert rows[-1]['minimum_J'] == pytest.approx(-.5)
    assert path_probe(base, direction, 20)['minimum_path_J'] == pytest.approx(-.5)
    assert path_probe(base, direction, 21)['minimum_path_J'] == pytest.approx(.25)


def test_positive_endpoints_do_not_certify_a_path_with_interior_inversion():
    base = np.eye(3)[None, None]
    direction = np.diag([-3., -1.5, 0.])[None, None]
    assert endpoint_scan(base, direction, max_halvings=0)[0]['minimum_J'] > 0
    assert path_probe(base, direction, 0)['minimum_path_J'] < 0


def test_nonfinite_or_nonadmissible_base_is_rejected():
    base = np.eye(3)[None, None]
    bad = base.copy()
    bad[..., 0, 0] = np.nan
    with pytest.raises(ValueError, match='finite sampled'):
        endpoint_scan(base, bad)
    bad[..., 0, 0] = -1.
    with pytest.raises(ValueError, match='current state'):
        endpoint_scan(bad, np.zeros_like(base))


@pytest.mark.parametrize('n,sequence', [(4, 28), (8, 15)])
def test_failure_selection_uses_registered_case_and_recorded_sequence(n, sequence):
    from prl.fem.mixed_cube_representation_spec import configuration
    name = f'mms_p3p1_n{n}'
    assert registered_failure(configuration(), {'case': name}, {'sequence': sequence}) == (name, sequence)


@pytest.mark.parametrize('corruption', ['case', 'sequence', 'halvings', 'floor', 'space'])
def test_unregistered_failure_or_relaxed_gate_is_rejected(corruption):
    from prl.fem.mixed_cube_representation_spec import configuration
    cfg = configuration()
    failure = {'case': 'mms_p3p1_n4'}
    guard = {'sequence': 28}
    if corruption == 'case':
        failure['case'] = 'mms_p3p2_n4'
    elif corruption == 'sequence':
        guard['sequence'] = -1
    elif corruption == 'space':
        next(case for case in cfg['cases'] if case['name'] == failure['case'])['p_degree'] = 2
    else:
        cfg['trial_guard']['max_halvings' if corruption == 'halvings' else 'floor'] = 21
    with pytest.raises(ValueError):
        registered_failure(cfg, failure, guard)


def test_cell_chunking_preserves_direct_endpoint_and_path_diagnosis():
    from pathlib import Path
    from prl.fem.nodal_export import canonical_nodal_cells
    fixture = Path(__file__).parent / 'fixtures' / 'p3_native_orientation_v01.npz'
    with np.load(fixture, allow_pickle=False) as saved:
        data = dict(saved)
    data['cells'], _ = canonical_nodal_cells(data['coordinates'], data['cells'], data['u_reference_nodes'])
    u = data['coordinates'] * .001
    step = np.zeros_like(u)
    step[:, 0] = 1.5 * 2.**20 * data['coordinates'][:, 0]
    whole = sampled_failure(data, u, step, chunk_size=64)
    split = sampled_failure(data, u, step, chunk_size=7)
    assert whole['registered_endpoint_scan'] == split['registered_endpoint_scan']
    assert whole['minimum_registered_step_path'] == split['minimum_registered_step_path']
    assert whole['out_of_budget_readonly_probe'] == split['out_of_budget_readonly_probe']
    assert whole['worst_minimum_step_sample'] == split['worst_minimum_step_sample']
