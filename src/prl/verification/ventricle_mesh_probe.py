"""Independent retained-state mesh diagnostic; no production mechanics or solves."""
import json
from pathlib import Path
import numpy as np


def cell_measures(mesh,state,config,mechanics):
    result=mechanics.fields(mesh,state,config)
    _,sample,_,_,_,vertices=mechanics.kinematics(mesh,state['u'],mechanics.extra_points())
    maximum=np.maximum(np.max(np.abs(result['J']-1),axis=1),np.max(np.abs(sample-1),axis=1))
    sigma=result['stress']; dev=sigma-np.trace(sigma,axis1=-2,axis2=-1)[...,None,None]*np.eye(3)/3
    equivalent=np.sqrt(1.5*np.sum(dev**2,axis=(-1,-2)))
    weights=result['weights']
    return {'max_abs_J_minus_one':maximum,
        'equivalent_stress':np.sum(equivalent*weights,axis=1)/weights.sum(axis=1),
        'clamp_adjacent':np.any(np.abs(vertices[:,:,2])<1e-12,axis=1),
        'cell_volume':weights.sum(axis=1),'cell_mean_J_minus_one':np.sum(weights*(result['J']-1),axis=1)/weights.sum(axis=1)}


def spatial_summary(mesh,state,config,mechanics):
    data=cell_measures(mesh,state,config,mechanics)
    def region(indices):
        values=data['max_abs_J_minus_one'][indices]
        return {'cells':int(indices.sum()),'above_one_percent_cells':int(np.sum(values>.01)),
                'max_abs_J_minus_one':float(values.max()),
                'cell_mean_max_abs_J_minus_one':float(np.max(np.abs(data['cell_mean_J_minus_one'][indices])))}
    return {'tetrahedra':len(mesh['cells']),'displacement_nodes':len(mesh['coordinates']),
        'mixed_dofs':3*len(mesh['coordinates'])+len(mesh['pressure_coordinates']),
        'regions':{'all':region(np.ones(len(mesh['cells']),dtype=bool)),
                   'clamp_adjacent':region(data['clamp_adjacent']),'away_from_clamp':region(~data['clamp_adjacent']),
                   **{'layer_'+str(i):region(mesh['layers']==i) for i in [1,2,3]}},
        'reference_volume_weighted_mean_J_minus_one':float(np.average(data['cell_mean_J_minus_one'],weights=data['cell_volume']))}


def compare_response(coarse,fine):
    difference=abs(coarse['volume_change']-fine['volume_change'])
    relative=difference/max(abs(coarse['volume_change']),abs(fine['volume_change']),1e-12)
    return {'absolute_volume_response_difference':difference,'relative_volume_response_difference':relative,
        'response_reference_gate':difference<=.002 and relative<=.05,
        'local_distortion_ratio_M1_over_M0':fine['max_abs_J_minus_one']/coarse['max_abs_J_minus_one'],
        'pointwise_qualification_both_meshes':coarse['status']=='passed' and fine['status']=='passed',
        'hotspot_or_asymptotic_convergence':'not_run'}


def verify_probe(root):
    from prl.verification import ventricle_3d as mechanics
    root=Path(root); config=json.loads((root/'configuration.json').read_text())
    fine=mechanics.verify(root)
    coarse_mesh=mechanics.load_arrays(root/'retained/M0_mesh.npz')
    coarse_state=mechanics.load_arrays(root/'retained/M0_state_pressure_1.npz')
    coarse_metadata=json.loads((root/'retained/M0_state_pressure_1.json').read_text())
    coarse=mechanics.state_audit(coarse_mesh,coarse_state,coarse_metadata,config)
    checks={'new_mesh_original_gates':fine['status']=='passed',
        'retained_failure_still_local_volume':coarse['failed_checks']==['local_volume'],
        'exact_two_state_scope':len(config['meshes'])==1 and config['meshes'][0]['name']=='M1' and
            config['states']==[{'label':'zero','p':0.,'Ta':0.,'initial':None},
                               {'label':'pressure_1','p':.01,'Ta':0.,'initial':'zero'}] and
            config['maximum_equilibrium_solves']==2 and not config.get('reuse_m0_zero',False)}
    summaries={'M0':spatial_summary(coarse_mesh,coarse_state,config,mechanics)}
    comparison={'status':'not_run'}
    records=fine['cases'].get('M1',{})
    if 'pressure_1' in records and 'volume_change' in records['pressure_1']:
        fine_state=mechanics.load_arrays(root/'raw/M1_state_pressure_1.npz')
        checks['matched_pressure_and_no_active']=float(fine_state['load'])==float(coarse_state['load'])==.01 and float(fine_state['activation'])==float(coarse_state['activation'])==0.
        checks['fine_pressure_expands']=records['pressure_1']['volume_change']>0
        comparison={'status':'passed',**compare_response(coarse,records['pressure_1'])}
        checks['response_reference_gate']=comparison['response_reference_gate']
        summaries['M1']=spatial_summary(mechanics.load_arrays(root/'raw/M1_mesh.npz'),fine_state,config,mechanics)
    else:
        checks['fine_pressure_saved']=False
    return {'status':'passed' if all(checks.values()) else 'failed','checks':checks,
        'failed_checks':[k for k,v in checks.items() if not v], 'new_mesh':fine,'retained_coarse':coarse,
        'spatial':summaries,'comparison':comparison,'complete_3d_loading_qualification':'not_run',
        'active_loading':'not_run','growth':'not_run','fsi':'not_run','biological_validation':'not_run',
        'scope':'M1 zero and first pressure only; M0 failure is not relabeled'}
