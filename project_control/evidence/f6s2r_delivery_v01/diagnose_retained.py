"""Read saved pressure state only; no solver, remesh, material change or retry."""
import json
from pathlib import Path
import numpy as np
from prl.verification.ventricle_3d import load_arrays,fields,kinematics,extra_points,state_audit
from prl.runs.fenicsx_ring import digest
from prl.runs.fenicsx_runtime import save_json

root=Path('E:/Temp-Projects/PRL-results/ventricle_fem/f6s2r_idealized_3d_resume_v01_20260918')
target=root/'offline_diagnosis.json'
if target.exists():
    raise FileExistsError('Diagnosis is create-only')
mesh=load_arrays(root/'raw/M0_mesh.npz'); state=load_arrays(root/'raw/M0_state_pressure_1.npz')
cfg=json.loads((root/'configuration.json').read_text()); meta=json.loads((root/'raw/M0_state_pressure_1.json').read_text())
audit=state_audit(mesh,state,meta,cfg); result=fields(mesh,state,cfg)
_,sample,_,_,bary,vertices=kinematics(mesh,state['u'],extra_points())
positions=np.einsum('qa,cai->cqi',bary,vertices)
pm=np.einsum('qa,ca->cq',bary,state['pressure'].ravel()[mesh['pressure_cells']])
weights=result['weights']; cell_volume=weights.sum(axis=1)
local_max=np.maximum(np.max(np.abs(result['J']-1),axis=1),np.max(np.abs(sample-1),axis=1))
cell_mean=np.sum(weights*(result['J']-1),axis=1)/cell_volume
pointwise=sample-1-pm/cfg['kappa']
clamp_adjacent=np.any(np.abs(vertices[:,:,2])<1e-12,axis=1)
worst=np.unravel_index(np.argmax(np.abs(sample-1)),sample.shape)
def region(indices):
    return {'cells':int(indices.sum()),'above_one_percent_cells':int(np.sum(local_max[indices]>.01)),
            'sample_max_abs_J_minus_one':float(local_max[indices].max()),
            'cell_mean_max_abs_J_minus_one':float(np.abs(cell_mean[indices]).max())}
report={'status':'passed','scientific_status':'failed',
    'replayed_failed_checks':audit['failed_checks'],'state_sha256':digest(root/'raw/M0_state_pressure_1.npz'),
    'solver_iterations':meta['iterations'],'solver_free_residual':meta['free_residual_norm'],
    'weak_pressure_norm':audit['weak_pressure_norm'],'volume_change':audit['volume_change'],
    'max_displacement_over_L':audit['max_displacement'],'quadrature_max_abs_J_minus_one':audit['quadrature_max_abs_J_minus_one'],
    'all_sample_max_abs_J_minus_one':audit['max_abs_J_minus_one'],
    'reference_volume_weighted_mean_J_minus_one':float(np.sum(weights*(result['J']-1))/weights.sum()),
    'pointwise_constraint_error_max':float(np.max(np.abs(pointwise))),
    'maximum_abs_material_pressure_over_kappa_at_extra_points':float(np.max(np.abs(pm/cfg['kappa']))),
    'worst_extra_point':{'cell':int(worst[0]),'point_index':int(worst[1]),'layer':int(mesh['layers'][worst[0]]),
        'reference_xyz':positions[worst].tolist(),'J':float(sample[worst]),'material_pressure':float(pm[worst]),
        'clamp_adjacent':bool(clamp_adjacent[worst[0]])},
    'regions':{'clamp_adjacent':region(clamp_adjacent),'away_from_clamp':region(~clamp_adjacent),
        **{'layer_'+str(i):region(mesh['layers']==i) for i in [1,2,3]}},
    'excluded_causes':{'nonconverged_SNES':meta['snes_reason']>0 and meta['free_residual_norm']<1e-9,
        'native_independent_field_disagreement':max(audit['field_errors'].values())<1e-10,
        'MUMPS_failure':meta['linear_solver']['status']=='passed','negative_J':audit['J_min']>0},
    'interpretation':'Confirmed: solved weak equations and matching independently reconstructed fields do not meet the frozen pointwise volume gate. P1 pressure weak moments are tiny while pointwise J-1-p/kappa is not. Mesh/basal-clamp/local-pressure-space contributions remain unseparated.',
    'proposed_falsifiable_next':'Same physics and p=0.01 on the existing M1 geometry, zero then first pressure only; if distortion decreases substantially, spatial discretization contributes. No new solve is authorized by this diagnosis.',
    'new_FEM_solves':0,'threshold_changes':0}
assert report['replayed_failed_checks']==['local_volume']
save_json(target,report)
print(json.dumps(report,indent=2))
