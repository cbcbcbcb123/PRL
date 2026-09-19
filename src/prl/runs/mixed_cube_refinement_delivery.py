"""Create-only independent refinement readback; no solver/runtime invocation."""
import json
from pathlib import Path
import time

import numpy as np

from prl.runs.mixed_cube_representation_delivery import (
    _read, _digest, _attempt, describe_iterate, integration_diagnostics, case_path_qualification)
from prl.verification.mixed_cube import audit, verify
from prl.verification.mixed_cube_refinement import convergence
from prl.verification.positive_j import audit_paths
from prl.verification.saved_segment import resolve_roundtrip
from prl.verification.ventricle_3d import load_arrays


def assert_preserved(snapshot, protected):
    """Frozen expected hashes take precedence over newly observed input hashes."""
    for path,value in {**snapshot,**protected}.items():
        if _digest(path)!=value:
            raise ValueError('Protected file drift: '+str(path))


def require_reference_protection(config, protected):
    parent=Path(config['reference_source_root']).resolve()
    hashes={Path(path).resolve():value for path,value in protected.items()}
    required=[parent/'configuration.json',parent/'delivery_analysis.json',parent/'source_hashes.json']
    for n in (4,8):
        required.extend(parent/'raw'/f'mms_p3p2_n{n}{suffix}' for suffix in
                        ('_mesh.npz','_state.npz','_state.json','_audit.json'))
    missing=[str(path) for path in required if path not in hashes]
    if missing:
        raise ValueError('Reference inputs missing frozen hash protection: '+repr(missing))
    sources=_read(parent/'source_hashes.json')
    if not sources:
        raise ValueError('Reference execution source manifest is empty')
    for name,expected in sources.items():
        path=(parent/'sources_at_execution'/name).resolve()
        if hashes.get(path)!=expected:
            raise ValueError('Reference execution source hash contract mismatch: '+str(path))


def analyze(root, config):
    """Read-only analysis, including incomplete or unsafe saved attempts."""
    root=Path(root)
    summary=_read(root/'summary.json')
    readback=_attempt(verify,root); paths=_attempt(audit_paths,root)
    endpoints=(_attempt(resolve_roundtrip,root,paths) if 'candidates' in paths else
               {'status':'failed','reason':'Original path audit could not finish'})
    checks={'new_terminal_readback':readback['status'] in {'passed','not_run'}}
    reports=readback.get('cases',{}); reference_reports={}; rows=[]; arrays={}; histories={}
    failure=_read(root/'failure.json') if (root/'failure.json').exists() else {}
    parent=Path(config['reference_source_root'])
    parent_config=_read(parent/'configuration.json')
    parent_delivery=_read(parent/'delivery_analysis.json')
    for n in (4,8):
        name=f'mms_p3p2_n{n}'
        case=next(item for item in parent_config['cases'] if item['name']==name)
        data=load_arrays(parent/'raw'/f'{name}_mesh.npz')
        state=load_arrays(parent/'raw'/f'{name}_state.npz')
        meta=_read(parent/'raw'/f'{name}_state.json')
        report,_=audit(data,state,meta,case,parent_config)
        prior=config['reference_reports'][name]
        checks[name+'_embedded_reference_matches_file']=prior==_read(parent/'raw'/f'{name}_audit.json')
        checks[name+'_frozen_reference_readback']=(report['status']==prior['status'] and
            report['checks']==prior['checks'] and set(report['metrics'])==set(prior['metrics']) and all(
            value is None and prior['metrics'][key] is None or value is not None and
            prior['metrics'][key] is not None and abs(value-prior['metrics'][key])<=1e-10
            for key,value in report['metrics'].items()))
        original=next(item for item in parent_delivery['cases'] if item['name']==name)
        checks[name+'_retained_path_qualification']=(original.get('independent_comparison_eligible') is True
                                                    and original.get('case_path_status')=='passed')
        checks[name+'_retained_high_order_safety']=(original.get('error_integration',{}).get('status')=='passed'
            and original.get('error_integration',{}).get('order8_J_safety',{}).get('status')=='passed')
        reference_reports[name]=report
        rows.append({**case,'equilibrium':report['status'],'metrics':report['metrics'],
            'DOF':meta['mixed_dofs'],'tetrahedra':meta['tetrahedra'],
            'solver_seconds':meta['elapsed_seconds'],'source_root':str(parent),
            'new_solve':False,'retained_path_status':original['case_path_status']})
    for case in config['cases']:
        name=case['name']; folder=root/'iterates'/name
        report=reports.get(name,{}); mesh_file=root/'raw'/f'{name}_mesh.npz'
        row={**case,'equilibrium':report.get('status','not_run'),'metrics':report.get('metrics'),
             'DOF':None,'tetrahedra':None,'solver_seconds':None,'new_solve':True,'source_root':str(root)}
        if failure.get('case')==name and not report:
            row.update(equilibrium='failed',reason='Interrupted without a qualified terminal state')
        state_file=root/'raw'/f'{name}_state.npz'
        if not mesh_file.exists():
            if state_file.exists() or report:
                checks[name+'_required_mesh']=False
            rows.append(row); continue
        data=load_arrays(mesh_file)
        row.update(DOF=len(data['mixed_u_map'])+len(data['mixed_p_map']),tetrahedra=len(data['cells']))
        for key in ('coordinates','cells','boundary_faces','boundary_tags','fixed'):
            arrays[name+'_'+key]=data[key]
        history=_read(folder/'history.json') if (folder/'history.json').exists() else []
        entries={int(item['iteration']):item for item in history}
        states=sorted(folder.glob('iterate_*.npz')); histories[name]=[]; indices=[]
        checks[name+'_history_inventory']=(len(entries)==len(history) and
            {int(path.stem.split('_')[-1]) for path in states}==set(entries))
        for path in states:
            index=int(path.stem.split('_')[-1]); state=load_arrays(path)
            entry=entries.get(index,{})
            detail=_attempt(describe_iterate,data,state)
            detail['monitor_agreement']=bool(detail['status']=='passed' and 'minimum_sampled_J' in entry and
                abs(min(detail[key]['minimum_J'] for key in ('production','extra'))
                    -entry['minimum_sampled_J'])<=1e-11)
            checks[name+'_'+path.stem]=detail['status']=='passed' and detail['monitor_agreement']
            histories[name].append({**entry,'iteration':index,**detail})
            arrays[f'{name}_u_{index}']=state['u']; arrays[f'{name}_pressure_{index}']=state['pressure']
            indices.append(index)
        arrays[name+'_iterations']=np.asarray(indices,dtype=np.int64)
        path_report=case_path_qualification(name,paths,endpoints)
        row['path_qualification']=path_report
        checks[name+'_paths']=(path_report['status']=='passed' or
                               not states and not state_file.exists() and path_report['status']=='not_run')
        if state_file.exists():
            state=load_arrays(state_file)
            meta=_read(state_file.with_suffix('.json')) if state_file.with_suffix('.json').exists() else {}
            checks[name+'_terminal_metadata']=bool(meta)
            checks[name+'_terminal_readback']=bool(report)
            checks[name+'_accepted_states_exist']=bool(states)
            row.update(solver_seconds=meta.get('elapsed_seconds'),iterations=meta.get('iterations'),
                       process_peak_rss_bytes=meta.get('process_peak_rss_bytes'))
            row['error_integration']=_attempt(integration_diagnostics,data,state,case)
            checks[name+'_integration_and_J']=row['error_integration']['status']=='passed'
        elif report:
            checks[name+'_required_terminal']=False
        rows.append(row)
    outcome=convergence(reports,config,reference_reports)
    registered_status=outcome['status']
    if not all(checks.values()):
        outcome={**outcome,'status':'failed','registered_gate_status':registered_status,
                 'independent_failures':[key for key,value in checks.items() if not value]}
    result={'status':outcome['status'],'convergence':outcome,'cases':rows,'config':config,
        'delivery_integrity':'passed' if all(checks.values()) else 'failed','checks':checks,
        'iterate_diagnostics':histories,'accepted_states_checked':sum(map(len,histories.values())),
        'accepted_paths_checked':paths.get('accepted_steps_checked',0),
        'completed_terminal_states':len(reports),'new_terminal_readback':readback['status'],
        'new_SNES_calls':summary['attempted_solves'],'container_invocations':summary['container_invocations'],
        'automatic_retries':summary['automatic_retries'],'original_ventricular_gate':'failed_unchanged',
        'original_n2_n4_n8_qualification':'failed_unchanged',
        'scope':'same-load kappa100 refinement, not heart/active/growth/FSI qualification'}
    documents={'delivery_analysis.json':result,'delivery_readback.json':readback,'path_readback.json':paths,
        'path_endpoint_certificate.json':endpoints}
    return result,arrays,documents


def deliver(root):
    root=Path(root).resolve(strict=True)
    names=('delivery_analysis.json','delivery_readback.json','path_readback.json',
           'path_endpoint_certificate.json','figure_states.npz','delivery_integrity.json')
    if (root/'manifest.json').exists() or any((root/name).exists() for name in names):
        raise FileExistsError('Create-only refinement delivery, never modify frozen evidence')
    config=_read(root/'configuration.json')
    if config['schema']!='prl.mixed_cube_refinement.v1':
        raise ValueError('Only registered refinement is supported')
    protected={Path(path):value for path,value in _read(root/'protected_inputs.json')['files'].items()}
    snapshot={path:_digest(path) for path in root.rglob('*') if path.is_file()}
    for name,value in _read(root/'source_hashes.json').items():
        protected[root/'sources_at_execution'/name]=value
    assert_preserved(snapshot,protected)
    require_reference_protection(config,protected)
    started=time.monotonic()
    result,arrays,documents=analyze(root,config)
    assert_preserved(snapshot,protected)
    documents['delivery_integrity.json']={
            'status':'passed','scope':'byte preservation only','protected_files':len(protected),
            'original_input_files':len(snapshot),'additional_solves':0,'analysis_seconds':time.monotonic()-started,
            'analyzer_sha256':_digest(Path(__file__))}
    for name,value in documents.items():
        with (root/name).open('x',encoding='utf-8') as stream:
            json.dump(value,stream,indent=2,ensure_ascii=False,allow_nan=False)
    with (root/'figure_states.npz').open('xb') as stream:
        np.savez_compressed(stream,**arrays)
    assert_preserved(snapshot,protected)
    return result


if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser(description=__doc__); parser.add_argument('root',type=Path)
    output=deliver(parser.parse_args().root)
    print(json.dumps({key:output[key] for key in ('status','convergence','delivery_integrity',
        'accepted_states_checked','accepted_paths_checked','new_SNES_calls')},indent=2))
