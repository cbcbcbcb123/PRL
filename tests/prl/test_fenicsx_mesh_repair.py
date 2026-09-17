"""Thin-layer mesh-size regression; no containers or scientific equilibria."""
import numpy as np
from prl.fem.fenicsx_contour import adaptive_boundary_sizes


def test_local_sizes_resolve_adjacent_layer_gap_without_changing_polygon():
    polygon=np.array([[-1.,-1.],[1.,-1.],[1.,1.],[-1.,1.]])
    original=polygon.copy()
    sizes,gaps=adaptive_boundary_sizes(polygon,1.2)
    assert sizes.shape==(4,4)
    assert np.all(sizes<=1.2*gaps+1e-14)
    assert np.all(sizes<=.09) and np.all(sizes>0)
    assert np.allclose(gaps[:2],1/27)
    # From an outer square corner, the nearest inner feature is its corner.
    assert np.allclose(gaps[2],np.sqrt(2)/27)
    assert np.array_equal(original,polygon)


def test_size_control_is_scale_aware_and_bounded():
    polygon=np.array([[-.2,-.2],[.2,-.2],[.2,.2],[-.2,.2]])
    first,gaps=adaptive_boundary_sizes(polygon,.9)
    second,_=adaptive_boundary_sizes(polygon,.7)
    assert np.all(second<first)
    assert np.allclose(first,.9*gaps)


def test_repair_cli_preserves_physics_and_explicit_scope():
    from prl.cli import _parser
    from prl.runs.fenicsx_contour import configuration
    for action in ['run','verify','render']:
        parsed=_parser().parse_args([action,'fem-fenicsx-contour','--repair-thin-mesh'])
        assert parsed.repair_thin_mesh
    original=configuration(); repaired=configuration(repair=True)
    for key in original:
        if key!='mesher':
            assert original[key]==repaired[key]
    assert repaired['mesh_size_candidates']==[1.2,.9,.7]


def test_retained_repair_is_geometry_pass_not_false_mechanics_pass():
    from pathlib import Path
    from prl.verification.fenicsx_contour import verify_mesh_repair
    root=Path(__file__).parents[2]/'results/ventricle_fem/f6s1m_thin_mesh_v01_20260917'
    if not root.exists():
        import pytest
        pytest.skip('Local retained scientific evidence is intentionally outside Git')
    report=verify_mesh_repair(root)
    assert report['status']=='passed' and report['geometry_status']=='passed'
    assert report['storage_admission']=='blocked'
    assert report['passive_mechanics']=='not_run' and report['equilibrium_solves']==0


def test_retained_passive_changes_budget_not_physics():
    from prl.runs.fenicsx_contour import configuration,RETAINED_MESH_SHA
    from prl.cli import _parser
    cfg=configuration(retained=True); old=configuration()
    assert cfg['resources']['stage_bytes']==800*1024**2
    assert cfg['retained_mesh']['sha256']==RETAINED_MESH_SHA
    assert 'mesh_size_candidates' not in cfg
    for key in ['mu','kappa','solver','passive_loads','active_peak','radii']:
        assert cfg[key]==old[key]
    for action in ['run','verify','render']:
        assert _parser().parse_args([action,'fem-fenicsx-contour','--retained-passive']).retained_passive


def test_retained_mesh_identity_mismatch_stops_before_loading(monkeypatch):
    from pathlib import Path
    import pytest
    from prl.fem.fenicsx_contour import retained_geometry
    from prl.runs.fenicsx_contour import configuration
    monkeypatch.setattr(Path,'read_bytes',lambda self:b'changed')
    with pytest.raises(ValueError,match='hash mismatch'):
        retained_geometry(Path.cwd(),configuration(retained=True))


def test_local_volume_failure_not_hidden_by_convergence_or_small_average():
    from pathlib import Path
    import pytest
    from prl.verification.fenicsx_contour import verify_contour,diagnose_local_volume
    root=Path(__file__).parents[2]/'results/ventricle_fem/f6s1p_retained_passive_v01_20260917'
    if not root.exists():
        pytest.skip('Local scientific evidence is intentionally outside Git')
    report=verify_contour(root)
    state=report['cases']['M0']['passive_1']
    assert report['status']=='failed'
    assert state['checks']['snes_convergence'] and state['checks']['independent_free_force']
    assert not state['checks']['local_volume'] and state['max_abs_J_minus_one']>.01
    assert abs(state['weighted_mean_J']-1)<.001
    assert 'M1' not in report['cases']
    diagnosis=diagnose_local_volume(root)
    assert diagnosis['scientific_solves']==0
    assert sum(v['failed_cells'] for v in diagnosis['layers'].values())==69
