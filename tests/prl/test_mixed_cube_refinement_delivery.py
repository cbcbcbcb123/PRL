"""Metadata and failure-semantics fixtures, never scientific solver validation."""
import copy
from pathlib import Path

import numpy as np
import pytest

from prl.fem.mixed_cube_refinement_spec import configuration
from prl.fem.mixed_cube_representation_spec import configuration as parent_configuration
from prl.runs import mixed_cube_refinement_delivery as delivery


def fake_audit(n):
    return {'status':'passed','checks':{'positive_J':True},'metrics':{
        'relative_u_L2':2/n**4,'relative_u_H1':3/n**3,'relative_pressure_L2':1/n**3,
        'J_error_RMS':.01/n**2}}


def fixture_environment(monkeypatch, *, terminal=True):
    """An in-memory report filesystem; no output files or temporary directories."""
    root,parent=Path('new_attempt'),Path('reference_attempt')
    name='mms_p3p2_n12'; folder=root/'iterates'/name
    config=configuration()
    config['reference_source_root']=str(parent)
    config['reference_reports']={f'mms_p3p2_n{n}':fake_audit(n) for n in (4,8)}
    metadata={'mixed_dofs':16,'tetrahedra':1,'elapsed_seconds':1.,'iterations':0,'process_peak_rss_bytes':1024}
    data={'coordinates':np.zeros((4,3)), 'cells':np.array([[0,1,2,3]]),
          'boundary_faces':np.array([[0,1,2]]), 'boundary_tags':np.array([1]),
          'fixed':np.ones((4,3),dtype=bool),'mixed_u_map':np.arange(12),'mixed_p_map':np.arange(12,16)}
    state={'u':np.zeros((4,3)),'pressure':np.zeros(4),'mixed_state':np.zeros(16)}
    documents={root/'summary.json':{'attempted_solves':1 if terminal else 0,
        'container_invocations':1,'automatic_retries':0},
        parent/'configuration.json':parent_configuration(),parent/'delivery_analysis.json':{'cases':[
            {'name':f'mms_p3p2_n{n}','independent_comparison_eligible':True,'case_path_status':'passed',
             'error_integration':{'status':'passed','order8_J_safety':{'status':'passed'}}} for n in (4,8)]}}
    arrays={root/'raw'/f'{name}_mesh.npz':data}
    for n in (4,8):
        label=f'mms_p3p2_n{n}'
        documents[parent/'raw'/f'{label}_state.json']=metadata.copy()
        documents[parent/'raw'/f'{label}_audit.json']=fake_audit(n)
        arrays[parent/'raw'/f'{label}_mesh.npz']=data
        arrays[parent/'raw'/f'{label}_state.npz']=state
    if terminal:
        documents[folder/'history.json']=[{'iteration':0,'minimum_sampled_J':1.,'residual':0.}]
        documents[root/'raw'/f'{name}_state.json']=metadata.copy()
        arrays[root/'raw'/f'{name}_state.npz']=state
        arrays[folder/'iterate_000.npz']=state
    prefix=name+'_0_'
    paths={'status':'passed' if terminal else 'not_run','accepted_steps_checked':1 if terminal else 0,
        'candidates':[{'case':name,'sequence':0,'accepted_scale':1.}] if terminal else [],
        'checks':{prefix+key:True for key in ('path','native_kinematics','scale','base_is_accepted','accepted_in_segment')}
                 if terminal else {}}
    monkeypatch.setattr(delivery,'_read',lambda path:copy.deepcopy(documents[Path(path)]))
    monkeypatch.setattr(delivery,'load_arrays',lambda path:arrays[Path(path)])
    monkeypatch.setattr(Path,'exists',lambda path:path in documents or path in arrays)
    monkeypatch.setattr(Path,'glob',lambda path,pattern:iter(
        [key for key in arrays if key.parent==path and key.name.startswith('iterate_')]))
    monkeypatch.setattr(delivery,'audit',lambda data,state,meta,case,config:(fake_audit(case['n']),{}))
    monkeypatch.setattr(delivery,'verify',lambda root:{'status':'passed' if terminal else 'not_run',
        'cases':{name:fake_audit(12)} if terminal else {}})
    monkeypatch.setattr(delivery,'audit_paths',lambda root:paths)
    monkeypatch.setattr(delivery,'resolve_roundtrip',lambda root,original:{'status':original['status'],'certificates':{}})
    monkeypatch.setattr(delivery,'describe_iterate',lambda data,state:{'status':'passed',
        'production':{'minimum_J':1.},'extra':{'minimum_J':1.}})
    monkeypatch.setattr(delivery,'integration_diagnostics',lambda data,state,case:{'status':'passed'})
    return root,config,documents,arrays,paths


def test_complete_report_cannot_pass_until_local_path_and_high_order_checks_pass(monkeypatch):
    root,config,documents,arrays,paths=fixture_environment(monkeypatch)
    result,_,_=delivery.analyze(root,config)
    assert result['status']=='passed'
    assert result['completed_terminal_states']==1
    paths['checks']['mms_p3p2_n12_0_native_kinematics']=False
    result,_,_=delivery.analyze(root,config)
    assert result['status']=='failed'
    assert result['convergence']['registered_gate_status']=='passed'
    assert 'mms_p3p2_n12_paths' in result['convergence']['independent_failures']
    paths['checks']['mms_p3p2_n12_0_native_kinematics']=True
    monkeypatch.setattr(delivery,'integration_diagnostics',lambda *args:{'status':'failed'})
    assert delivery.analyze(root,config)[0]['status']=='failed'


def test_empty_new_attempt_remains_blocked_without_fake_terminal_or_metrics(monkeypatch):
    root,config,_,_,_=fixture_environment(monkeypatch,terminal=False)
    result,arrays,_=delivery.analyze(root,config)
    assert result['status']=='blocked'
    assert result['new_terminal_readback']=='not_run'
    assert result['accepted_states_checked']==result['completed_terminal_states']==0
    assert result['cases'][-1]['equilibrium']=='not_run'
    assert result['cases'][-1]['metrics'] is None
    assert not any('_u_' in key for key in arrays)


@pytest.mark.parametrize('defect',['missing','duplicate','wrong_index'])
def test_missing_or_invalid_history_retains_states_and_fails_delivery(monkeypatch,defect):
    root,config,documents,_,_=fixture_environment(monkeypatch)
    path=root/'iterates'/'mms_p3p2_n12'/'history.json'
    if defect=='missing':
        documents.pop(path)
    elif defect=='duplicate':
        documents[path] *= 2
    else:
        documents[path][0]['iteration']=1
    result,arrays,_=delivery.analyze(root,config)
    assert result['status']=='failed'
    assert not result['checks']['mms_p3p2_n12_history_inventory']
    assert result['accepted_states_checked']==1
    assert 'mms_p3p2_n12_u_0' in arrays


def test_bad_mixed_state_diagnostic_is_recorded_as_failed_not_an_exception(monkeypatch):
    root,config,_,_,_=fixture_environment(monkeypatch)
    def invalid(*args):
        raise ValueError('Saved mixed-map drift')
    monkeypatch.setattr(delivery,'describe_iterate',invalid)
    result,_,_=delivery.analyze(root,config)
    assert result['status']=='failed'
    assert 'mixed-map drift' in result['iterate_diagnostics']['mms_p3p2_n12'][0]['reason']


@pytest.mark.parametrize('defect',['embedded_audit','retained_path','retained_q8'])
def test_reference_reports_must_match_frozen_source_and_qualification(monkeypatch,defect):
    root,config,documents,_,_=fixture_environment(monkeypatch)
    parent=Path(config['reference_source_root'])
    if defect=='embedded_audit':
        config['reference_reports']['mms_p3p2_n8']['status']='failed'
    elif defect=='retained_path':
        documents[parent/'delivery_analysis.json']['cases'][1]['case_path_status']='failed'
    else:
        documents[parent/'delivery_analysis.json']['cases'][1]['error_integration']['order8_J_safety']['status']='failed'
    result,_,_=delivery.analyze(root,config)
    assert result['status']=='failed'
    assert result['delivery_integrity']=='failed'


def test_observed_snapshot_cannot_override_execution_source_expected_hash(monkeypatch):
    path=Path('attempt/sources_at_execution/source.py')
    monkeypatch.setattr(delivery,'_digest',lambda path:'tampered')
    with pytest.raises(ValueError,match='Protected file drift'):
        delivery.assert_preserved({path:'tampered'},{path:'frozen'})


def test_reference_source_hashes_must_be_explicitly_in_protection_contract(monkeypatch):
    parent=Path('reference').resolve()
    config={'reference_source_root':str(parent)}
    protected={parent/name:'hash' for name in ('configuration.json','delivery_analysis.json','source_hashes.json')}
    for n in (4,8):
        for suffix in ('_mesh.npz','_state.npz','_state.json','_audit.json'):
            protected[parent/'raw'/f'mms_p3p2_n{n}{suffix}']='hash'
    monkeypatch.setattr(delivery,'_read',lambda path:{'source.py':'original-source-hash'})
    with pytest.raises(ValueError,match='source hash contract mismatch'):
        delivery.require_reference_protection(config,protected)
    protected[parent/'sources_at_execution/source.py']='original-source-hash'
    delivery.require_reference_protection(config,protected)
    protected.pop(parent/'raw/mms_p3p2_n8_state.npz')
    with pytest.raises(ValueError,match='missing frozen hash protection'):
        delivery.require_reference_protection(config,protected)


def test_create_only_refuses_frozen_root_before_reading_or_writing(monkeypatch):
    root=Path('root')
    monkeypatch.setattr(Path,'resolve',lambda path,**kwargs:path)
    monkeypatch.setattr(Path,'exists',lambda path:path.name=='manifest.json')
    monkeypatch.setattr(delivery,'_read',lambda path:pytest.fail('No analysis permitted'))
    with pytest.raises(FileExistsError,match='Create-only'):
        delivery.deliver(root)
