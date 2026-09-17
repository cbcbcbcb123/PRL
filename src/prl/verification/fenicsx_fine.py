"""Independent saved M1 two-state audit and retained M0 comparison; no UFL."""
import hashlib
import json
from pathlib import Path
import numpy as np
from .fenicsx_contour import geometry_audit,SOURCE_SHA
from .fenicsx_ring import load_arrays,state_audit,fields


def same_audit(actual,expected):
    """Platform rounding tolerance only; categorical/scientific gates exact."""
    if isinstance(expected,dict):
        return set(actual)==set(expected) and all(same_audit(actual[k],v) for k,v in expected.items())
    if isinstance(expected,list):
        return len(actual)==len(expected) and all(same_audit(a,b) for a,b in zip(actual,expected))
    if isinstance(expected,float):
        return bool(np.isclose(actual,expected,rtol=1e-10,atol=1e-12))
    return actual==expected


def volume_metrics(mesh,state):
    values=fields(mesh,state)
    deviation=np.abs(values['J']-1)
    worst=np.unravel_index(np.argmax(deviation),deviation.shape)
    bary=np.column_stack((1-mesh['qpoints'].sum(axis=1),mesh['qpoints']))
    position=np.einsum('qa,cai->cqi',bary,mesh['coordinates'][mesh['cells'][:,:3]])
    pressure=np.einsum('qa,ca->cq',bary,state['pressure'][mesh['pressure_cells']])
    return {'max_abs_J_minus_one':float(deviation.max()),
            'weighted_mean_J':float(np.sum(values['weights']*values['J'])/values['weights'].sum()),
            'reference_volume_fraction_above_one_percent':float(np.sum(values['weights']*(deviation>.01))/values['weights'].sum()),
            'pointwise_mixed_constraint_max':float(np.max(np.abs(values['J']-1-pressure/1000))),
            'max_abs_pressure_over_kappa':float(np.max(np.abs(pressure/1000))),
            'worst_cell':int(worst[0]),'worst_quadrature_point':int(worst[1]),
            'worst_reference_xy':position[worst].tolist(),'worst_layer':int(mesh['layers'][worst[0]]),
            'max_displacement_over_L':float(np.linalg.norm(state['u'],axis=1).max()),
            'layers':{str(i):{'cells':int(np.sum(mesh['layers']==i)),
                             'failed_cells':int(np.sum(np.max(deviation[mesh['layers']==i],axis=1)>.01)),
                             'max_abs_J_minus_one':float(deviation[mesh['layers']==i].max())} for i in [1,2,3]}}


def verify_fine(root,save=False):
    root=Path(root); comparison=root/'comparison'
    cfg=json.loads((root/'configuration.json').read_text())
    parent_cfg=json.loads((comparison/'configuration.json').read_text())
    source=load_arrays(root/'geometry_source.npz')
    identities=json.loads((comparison/'source_identity.json').read_text())
    frozen=['mu','kappa','radii','solver','active_peak','quadrature_degree','geometry_kind']
    checks={'frozen_physics':all(cfg[k]==parent_cfg[k] for k in frozen),
            'two_state_scope':cfg['passive_loads']==[0.,.02] and cfg['execution_meshes']==['M1'],
            'source_identity':hashlib.sha256((root/'geometry_source.npz').read_bytes()).hexdigest()==SOURCE_SHA,
            'comparison_identity':all(hashlib.sha256((comparison/p).read_bytes()).hexdigest()==v['sha256'] for p,v in identities.items()),
            'no_coarse_solve':not any((root/'raw').glob('M0_state*')),
            'no_extra_states':set(p.name for p in (root/'raw').glob('*_state_*.npz'))<=
                {'M1_state_passive_0.npz','M1_state_passive_1.npz'}}
    geometries={}
    for name in ['M0','M1']:
        geom=load_arrays(root/'raw'/f'{name}_input_mesh.npz')
        geometries[name]=geometry_audit(geom,source)
        checks[name+'_geometry']=geometries[name]['status']=='passed'
        if name=='M1':
            prior=load_arrays(comparison/'M1_input_mesh.npz')
            checks['retained_fine_identity']=set(prior)==set(geom) and all(np.array_equal(prior[k],geom[k]) for k in prior)
    coarse_mesh=load_arrays(comparison/'M0_mesh.npz')
    original=json.loads((comparison/'verification.json').read_text())['cases']['M0']
    coarse={f'passive_{i}':state_audit(coarse_mesh,load_arrays(comparison/f'M0_state_passive_{i}.npz'),
            json.loads((comparison/f'M0_state_passive_{i}.json').read_text()),parent_cfg) for i in range(2)}
    checks['coarse_audit_reproduced']=same_audit(coarse,original)
    records={}; volumes={}
    volumes['M0']=volume_metrics(coarse_mesh,load_arrays(comparison/'M0_state_passive_1.npz'))
    mesh_path=root/'raw/M1_mesh.npz'
    if mesh_path.exists():
        mesh=load_arrays(mesh_path)
        positions=mesh['coordinates'][mesh['cells']]
        mids=np.stack(((positions[:,1]+positions[:,2])/2,(positions[:,0]+positions[:,2])/2,(positions[:,0]+positions[:,1])/2),axis=1)
        checks['P2P1_mapping']=bool(np.max(np.abs(positions[:,3:]-mids))<1e-12 and
              np.max(np.abs(mesh['pressure_coordinates'][mesh['pressure_cells']]-positions[:,:3]))<1e-12)
        tangent_path=root/'raw/M1_tangent.json'
        tangent=json.loads(tangent_path.read_text()) if tangent_path.exists() else {}
        checks['tangent']=all(tangent.get(k,float('inf'))<=v for k,v in [('pressure',2e-6),('active',2e-6),('total',2e-5)])
        previous=None
        for i,p in enumerate([0.,.02]):
            path=root/'raw'/f'M1_state_passive_{i}.npz'
            if not path.exists():
                break
            state=load_arrays(path)
            metadata=json.loads(path.with_suffix('.json').read_text())
            records[f'passive_{i}']=state_audit(mesh,state,metadata,cfg)
            checks[f'state_{i}']=records[f'passive_{i}']['status']=='passed'
            checks[f'load_{i}']=float(state['load'])==p and float(state['activation'])==0.
            expected=np.zeros_like(state['mixed_state']) if previous is None else previous
            checks[f'chain_{i}']=bool(np.array_equal(state['initial_mixed'],expected))
            previous=state['mixed_state']
            if i==0:
                checks['zero_stress']=bool(np.max(np.abs(state['stress']))<=2e-7)
            else:
                volumes['M1']=volume_metrics(mesh,state)
    checks['two_states_saved']=len(records)==2
    comparison_result={}
    if 'passive_1' in records:
        a,b=[c['passive_1']['cavity_area_change'] for c in [coarse,records]]
        comparison_result={'cavity_change_M0':a,'cavity_change_M1':b,'absolute':abs(a-b),
                           'relative':abs(a-b)/max(abs(a),abs(b),1e-15),
                           'peak_J_fine_over_coarse':volumes['M1']['max_abs_J_minus_one']/volumes['M0']['max_abs_J_minus_one']}
        checks['mesh_response']=comparison_result['absolute']<=.002 and comparison_result['relative']<=.05
    else:
        checks['mesh_response']=False
    report={'status':'passed' if all(checks.values()) else 'failed','scope':'two-state fine-grid diagnostic only',
            'checks':checks,'failed_checks':[k for k,v in checks.items() if not v],
            'geometry':geometries,'cases':{'M0_retained':coarse,'M1':records},'volume':volumes,
            'comparison':comparison_result,'new_saved_states':len(records),
            'active_contraction':'not_run','full_passive_qualification':'not_run','biological_validation':'not_run'}
    if save:
        (root/'verification.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    return report
