"""Independent low-pressure active comparison, using unchanged NumPy mechanics."""
import hashlib
import json
from pathlib import Path

import numpy as np

from .fenicsx_ring import load_arrays, pressure_basis, shape
from .fenicsx_pressure import saved_iterates_audit
from .fenicsx_contour import geometry_audit, SOURCE_SHA
from .fenicsx_contour_pressure import GEOMETRY_HASHES, same_mixed_mesh, contour_state_audit, response_comparison

ACTIVATIONS = [0.,.025,.05,.075,.1]


def active_scope_checks(config, qualified):
    unchanged = [key for key in qualified if key not in
        ['schema_version','maximum_equilibrium_solves','scope','active_peak']]
    return {
        'same_qualified_physics_solver':all(config.get(key)==qualified[key] for key in unchanged),
        'exact_active_ladder':config.get('active_levels')==ACTIVATIONS and config.get('active_peak')==.1
            and config.get('fixed_pressure')==.02 and config.get('maximum_equilibrium_solves')==8,
        'exact_two_contour_meshes':config.get('meshes')==[{'name':'M0'},{'name':'M1'}]
            and config.get('objects')==['contour'] and config.get('pressure_space')=='DG2',
        'single_cpu_zero_gpu_no_retries':config.get('resources')=={'seconds':1200,'threads':1,'gpu':0,'automatic_retries':0},
        'retain_actual_iterates':config.get('retain_solver_iterates') is True,
    }


def fibre_audit(mesh):
    coordinates=np.einsum('qa,cai->cqi',shape(mesh['qpoints'])[0],mesh['coordinates'][mesh['cells']])
    radius=np.linalg.norm(coordinates[mesh['layers']==3],axis=-1)
    minimum=float(radius.min()) if radius.size else 0.
    return {'status':'passed' if minimum>1e-12 and np.isfinite(radius).all() else 'failed',
        'minimum_myocardial_reference_radius_L':minimum,
        'definition':'f0=(-Y,X,0)/sqrt(X^2+Y^2), about origin; assumed, not measured or contour tangent'}


def state_path(root,name,index):
    root=Path(root)
    return root/'retained'/f'{name}_state_passive_1.npz' if index==0 else root/'raw'/f'{name}_state_active_{index}.npz'


def verify_contour_active(root):
    root=Path(root); config=json.loads((root/'configuration.json').read_text())
    qualified=json.loads((root/'prerequisite/configuration.json').read_text())
    parent=json.loads((root/'prerequisite/post_verification.json').read_text())
    checks=active_scope_checks(config,qualified)
    checks['low_pressure_parent_qualified']=parent['status']=='passed' and all(parent['checks'].values())
    checks['source_identity']=hashlib.sha256((root/'geometry_source.npz').read_bytes()).hexdigest()==SOURCE_SHA
    identities=json.loads((root/'input_identities.json').read_text())
    checks['input_copies']=all(hashlib.sha256((root/path).read_bytes()).hexdigest()==item['sha256'] for path,item in identities.items())
    high_pressure=json.loads((root/'prerequisite/high_pressure_failure.json').read_text())
    checks['high_pressure_failure_preserved']=high_pressure['status']=='failed' and high_pressure['label']=='passive_4'
    source=load_arrays(root/'geometry_source.npz'); cases={}; iterates={}; geometry={}; fibres={}; comparisons={}
    for name in ['M0','M1']:
        cases[name],iterates[name]={},{}
        geompath=root/'input'/f'{name}_input_mesh.npz'
        checks[name+'_input_hash']=hashlib.sha256(geompath.read_bytes()).hexdigest()==GEOMETRY_HASHES[name]
        geometry[name]=geometry_audit(load_arrays(geompath),source)
        checks[name+'_geometry']=geometry[name]['status']=='passed'
        retained=load_arrays(root/'retained'/f'{name}_mesh.npz')
        meshpath=root/'raw'/f'{name}_mesh.npz'
        mesh=load_arrays(meshpath) if meshpath.exists() else retained
        pressure_basis(mesh)
        checks[name+'_exact_restart_map']=same_mixed_mesh(mesh,retained)
        fibres[name]=fibre_audit(mesh); checks[name+'_fibre_nonsingular']=fibres[name]['status']=='passed'
        tangentpath=root/('raw' if meshpath.exists() else 'retained')/f'{name}_tangent.json'
        tangent=json.loads(tangentpath.read_text()) if tangentpath.exists() else {}
        checks[name+'_tangent']=all(tangent.get(k,np.inf)<=v for k,v in [('pressure',2e-6),('active',2e-6),('total',2e-5)])
        zero=load_arrays(root/'retained'/f'{name}_state_passive_0.npz')
        zero_meta=json.loads((root/'retained'/f'{name}_state_passive_0.json').read_text())
        checks[name+'_retained_zero']=contour_state_audit(mesh,zero,zero_meta,config)['status']=='passed'
        checks[name+'_zero_load_identity']=float(zero['load'])==0. and float(zero['activation'])==0.
        previous=zero['mixed_state']
        for index,activation in enumerate(ACTIVATIONS):
            label=f'active_{index}'; path=state_path(root,name,index)
            if not path.exists():
                continue
            state=load_arrays(path); meta=json.loads(path.with_suffix('.json').read_text())
            audit=contour_state_audit(mesh,state,meta,config); cases[name][label]=audit
            audit['source']='retained_without_solve' if index==0 else 'new'
            checks[f'{name}_{label}_load']=float(state['load'])==.02 and float(state['activation'])==activation
            checks[f'{name}_{label}_chain']=np.array_equal(state['initial_mixed'],previous)
            checks[f'{name}_{label}_state']=audit['status']=='passed'
            if index:
                iteration=saved_iterates_audit(root/'iterates'/f'{name}_{label}',mesh,state,meta,config,expected_activation=activation)
                iterates[name][label]=iteration
                checks[f'{name}_{label}_iterates']=iteration['status']=='passed'
            baseline=cases[name]['active_0']['cavity_area']
            audit['area_change_from_pressurized_baseline']=audit['cavity_area']/baseline-1.
            previous=state['mixed_state']
        checks[name+'_five_active_levels']=len(cases[name])==5
    for index in range(5):
        label=f'active_{index}'
        if all(label in cases[name] for name in ['M0','M1']):
            comparison=response_comparison(*[cases[name][label]['cavity_area_change'] for name in ['M0','M1']])
            comparison['active_increment_difference']=abs(cases['M0'][label]['area_change_from_pressurized_baseline']-
                cases['M1'][label]['area_change_from_pressurized_baseline'])
            comparisons[label]=comparison; checks[label+'_mesh_response']=comparison['status']=='passed'
    allowed={f'{name}_state_active_{i}.npz' for name in ['M0','M1'] for i in range(1,5)}
    checks['no_extra_or_recomputed_states']={p.name for p in (root/'raw').glob('*_state_*.npz')}<=allowed
    checks['no_ring_or_microprobe']=not any((root/name).exists() for name in ['ring','native_probe','runtime_zero_newton'])
    ledger=root/'continuation_ledger.json'; progress=json.loads(ledger.read_text()) if ledger.exists() else {}
    checks['bounded_attempts']=0<=progress.get('attempted_states',0)<=8
    accepted=sum(record['status']=='passed' for rows in cases.values() for label,record in rows.items() if label!='active_0')
    checks['eight_new_states_accepted']=accepted==8 and progress.get('accepted_states')==8
    checks['all_mesh_responses']=len(comparisons)==5 and all(item['status']=='passed' for item in comparisons.values())
    return {'status':'passed' if all(checks.values()) else 'failed','checks':checks,
        'failed_checks':[key for key,value in checks.items() if not value],'cases':cases,'geometry':geometry,'fibres':fibres,
        'iterates':iterates,'comparison':comparisons,'accepted_new_equilibria':accepted,'reused_equilibria':4,
        'attempted_equilibria':progress.get('attempted_states',0),'controller_accepted_states':progress.get('accepted_states',0),
        'scope':'two-mesh quasi-static assumed-fibre active response at p/mu=0.02; not heartbeat time or hotspot convergence',
        'high_pressure_qualification':'failed','three_dimensional_model':'not_run','fsi':'not_run','growth':'not_run',
        'biological_validation':'not_run'}
