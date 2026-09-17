"""Scope and retained-geometry checks only; no container or equilibrium."""
from pathlib import Path
import numpy as np
import pytest
from prl.fem.fenicsx_contour import execution_meshes,refine
from prl.runs.fenicsx_contour import configuration,PASSIVE_RESULT,RETAINED_MESH


def test_fine_scope_is_two_uncomputed_states_with_unchanged_physics():
    cfg=configuration(fine=True); parent=configuration(retained=True)
    assert execution_meshes(cfg)==['M1'] and cfg['passive_loads']==[0.,.02]
    for key in ['mu','kappa','solver','radii','quadrature_degree','active_peak','retained_mesh']:
        assert cfg[key]==parent[key]
    assert execution_meshes(parent)==['M0','M1']


@pytest.mark.parametrize('change',[{'execution_meshes':['M0','M1']},{'passive_loads':[0.,.02,.04]},
                                 {'active_peak':.1},{'diagnostic':'unknown'}])
def test_scope_expansion_refused(change):
    cfg=configuration(fine=True); cfg.update(change)
    with pytest.raises(ValueError): execution_meshes(cfg)


def test_fine_cli_mode_is_exclusive():
    from prl.cli import _parser
    for command in ['run','verify','render']:
        assert _parser().parse_args([command,'fem-fenicsx-contour','--fine-diagnostic']).fine_diagnostic
    with pytest.raises(SystemExit):
        _parser().parse_args(['run','fem-fenicsx-contour','--fine-diagnostic','--retained-passive'])


def test_refinement_matches_previously_retained_uncomputed_fine_mesh():
    from prl.verification.fenicsx_ring import load_arrays
    root=Path(__file__).parents[2]
    if not (root/RETAINED_MESH).exists(): pytest.skip('Local input evidence outside Git')
    fine=refine(load_arrays(root/RETAINED_MESH))
    previous=load_arrays(root/PASSIVE_RESULT/'raw/M1_input_mesh.npz')
    assert set(fine)==set(previous)
    assert all(np.array_equal(fine[k],previous[k]) for k in fine)
    assert len(fine['triangles'])==14164


def test_audit_tolerance_never_changes_scientific_gate():
    from prl.verification.fenicsx_fine import same_audit
    assert same_audit({'status':'failed','residual':1e-14},{'status':'failed','residual':1.01e-14})
    assert not same_audit({'status':'passed','J':.1115},{'status':'failed','J':.1115})
    assert not same_audit({'J':.01},{'J':.1115})


def test_retained_fine_failure_not_hidden_by_close_global_response():
    from prl.result_store import result_path
    from prl.runs.fenicsx_contour import FINE_RESULT
    from prl.verification.fenicsx_fine import verify_fine
    try:
        root=result_path(Path(__file__).parents[2],FINE_RESULT)
    except FileNotFoundError:
        pytest.skip('External scientific evidence is intentionally outside Git')
    report=verify_fine(root)
    assert report['status']=='failed' and report['failed_checks']==['state_1']
    assert report['new_saved_states']==2 and report['checks']['no_coarse_solve']
    assert report['checks']['mesh_response']
    assert report['volume']['M1']['max_abs_J_minus_one']>report['volume']['M0']['max_abs_J_minus_one']>.01
    assert report['volume']['M1']['reference_volume_fraction_above_one_percent']<report['volume']['M0']['reference_volume_fraction_above_one_percent']
