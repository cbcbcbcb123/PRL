"""Saved-state pressure-space diagnostics, independent of UFL/DOLFINx."""
import json
from pathlib import Path

import numpy as np
from scipy.sparse import coo_matrix
from scipy.sparse.linalg import spsolve

from .fenicsx_ring import cavity, fields, load_arrays, pressure_basis, shape, state_audit


def same_displacement_mesh(new,old):
    """Mixed-space numbering may change; physical cell maps and gauges must not."""
    for key in ['cells','coordinates','fixed','inner_edges','qpoints','qweights','layers']:
        if new[key].shape!=old[key].shape:
            return False
    if not all(np.array_equal(new[k],old[k]) for k in ['layers','qpoints','qweights']):
        return False
    if not all(np.allclose(new['coordinates'][new[k]],old['coordinates'][old[k]],rtol=0,atol=1e-13)
               for k in ['cells','inner_edges']):
        return False
    for component in [0,1]:
        a=new['coordinates'][new['fixed'][:,component]]
        b=old['coordinates'][old['fixed'][:,component]]
        if a.shape!=b.shape:
            return False
        a=a[np.lexsort(a.T)]; b=b[np.lexsort(b.T)]
        if not np.allclose(a,b,rtol=0,atol=1e-13):
            return False
    return True


def volume_projection(mesh, state, kappa=1000.):
    """L2 decomposition: CG1-visible volume strain versus its orthogonal part.

    This is a postprocessing projection, never a new mechanical equilibrium.
    The squared norm fraction is not a physical volume fraction.
    """
    data=fields(mesh,state,kappa=kappa)
    value=data['J']-1
    basis=pressure_basis(mesh)
    pressure=np.einsum('qa,ca->cq',basis,np.asarray(state['pressure']).reshape(-1)[mesh['pressure_cells']])
    result={'max_abs_J_minus_one':float(np.max(np.abs(value))),
            'pointwise_constraint_max':float(np.max(np.abs(value-pressure/kappa))),
            'max_abs_pressure_over_kappa':float(np.max(np.abs(pressure/kappa)))}
    if str(np.asarray(mesh.get('pressure_space','CG1')).item())!='CG1':
        return result
    _,_,bary=shape(mesh['qpoints'])
    weights=data['weights']; cell_map=mesh['pressure_cells']
    count=int(cell_map.max()+1)
    matrices=np.einsum('qa,qb,cq->cab',bary,bary,weights)
    rows=np.broadcast_to(cell_map[:,:,None],matrices.shape).ravel()
    cols=np.broadcast_to(cell_map[:,None,:],matrices.shape).ravel()
    mass=coo_matrix((matrices.ravel(),(rows,cols)),shape=(count,count)).tocsr()
    rhs=np.zeros(count)
    np.add.at(rhs,cell_map.ravel(),np.einsum('qa,cq,cq->ca',bary,value,weights).ravel())
    projected=spsolve(mass,rhs)
    visible=np.einsum('qa,ca->cq',bary,projected[cell_map])
    unresolved=value-visible
    squared=float(np.sum(weights*value**2))
    unresolved_squared=float(np.sum(weights*unresolved**2))
    result.update(
        cg1_projection_max=float(np.max(np.abs(visible))),
        cg1_projection_pressure_difference=float(np.max(np.abs(visible-pressure/kappa))),
        unresolved_squared_L2_fraction=unresolved_squared/squared if squared>1e-28 else None,
        orthogonality=float(np.sum(weights*visible*unresolved)),
        relative_mass_residual=float(np.linalg.norm(mass@projected-rhs)/max(np.linalg.norm(rhs),1e-30)))
    return result


def diagnostic_state(mesh,state,metadata,config,old=None):
    report=state_audit(mesh,state,metadata,config)
    report['volume']=volume_projection(mesh,state,config['kappa'])
    report['checks']['DG2_pressure_basis']=str(np.asarray(mesh.get('pressure_space','')).item())=='DG2'
    report['checks']['pointwise_pressure_constraint']=report['volume']['pointwise_constraint_max']<=1e-9
    if config['geometry_kind']=='ring' and float(state['load'])>0:
        report['checks']['ring_analytic_response']=report['analytic_relative_error']<=.05
        if old is None:
            raise ValueError('The saved same-mesh CG1 control is required')
        difference=abs(report['cavity_area_change']-old['cavity_area_change'])
        report['relative_response_difference_to_CG1']=difference/max(abs(old['cavity_area_change']),1e-15)
        report['checks']['ring_response_not_locked']=report['relative_response_difference_to_CG1']<=.05
    report['status']='passed' if all(report['checks'].values()) else 'failed'
    return report


def verify_pressure(root):
    root=Path(root)
    config=json.loads((root/'configuration.json').read_text())
    if config.get('resume_first_ring',False):
        return verify_resumed_ring(root)
    checks={}; cases={}; old={}
    for kind in ['ring','contour']:
        cfg={**config,'geometry_kind':'ring' if kind=='ring' else 'image_polygon'}
        source=root/'comparison'/kind
        old_mesh=load_arrays(source/'mesh.npz')
        old_state=load_arrays(source/'state.npz')
        old_config=json.loads((source/'configuration.json').read_text())
        old_record=state_audit(old_mesh,old_state,json.loads((source/'state.json').read_text()),old_config)
        old[kind]={'audit':old_record,'projection':volume_projection(old_mesh,old_state)}
        target=root/kind/'raw'
        cases[kind]={}
        if not (target/'M0_mesh.npz').exists():
            checks[kind+'_completed']=False
            continue
        mesh=load_arrays(target/'M0_mesh.npz')
        checks[kind+'_same_displacement_mesh']=same_displacement_mesh(mesh,old_mesh)
        tangent_path=target/'M0_tangent.json'
        tangent=json.loads(tangent_path.read_text()) if tangent_path.exists() else {}
        checks[kind+'_tangent']=all(tangent.get(k,np.inf)<=v for k,v in [('pressure',2e-6),('active',2e-6),('total',2e-5)])
        previous=None
        for i,load in enumerate([0.,.02]):
            path=target/f'M0_state_passive_{i}.npz'
            if not path.exists():
                continue
            state=load_arrays(path)
            report=diagnostic_state(mesh,state,json.loads(path.with_suffix('.json').read_text()),cfg,old_record)
            expected=np.zeros_like(state['mixed_state']) if previous is None else previous
            checks[f'{kind}_{i}_chain']=np.array_equal(state['initial_mixed'],expected)
            checks[f'{kind}_{i}_load']=float(state['load'])==load and float(state['activation'])==0.
            checks[f'{kind}_{i}_state']=report['status']=='passed'
            cases[kind][str(i)]=report
            previous=state['mixed_state']
        checks[kind+'_completed']=len(cases[kind])==2
        checks[kind+'_no_extra_states']=len(list(target.glob('*_state_*.npz')))==len(cases[kind])
    return {'status':'passed' if all(checks.values()) else 'failed','checks':checks,'cases':cases,
            'retained_CG1':old,'new_saved_states':sum(len(c) for c in cases.values()),
            'scope':'single-grid pressure-space diagnostic, not mesh convergence or 3D/FSI/growth qualification',
            'mesh_convergence':'not_run','active_contraction':'not_run','biological_validation':'not_run'}


def verify_resumed_ring(root):
    """Independent saved-state gate for a single resumed original equilibrium."""
    root=Path(root); cfg=json.loads((root/'configuration.json').read_text())
    cfg={**cfg,'geometry_kind':'ring'}
    retained=root/'retained_zero'; raw=root/'ring/raw'; old=root/'comparison/ring'
    reference=load_arrays(retained/'mesh.npz'); mesh=load_arrays(raw/'M0_mesh.npz')
    zero=load_arrays(retained/'state.npz')
    previous_cfg=json.loads((retained/'configuration.json').read_text())
    zero_report=diagnostic_state(reference,zero,json.loads((retained/'state.json').read_text()),cfg)
    old_mesh=load_arrays(old/'mesh.npz'); old_state=load_arrays(old/'state.npz')
    old_report=state_audit(old_mesh,old_state,json.loads((old/'state.json').read_text()),json.loads((old/'configuration.json').read_text()))
    checks={'retained_zero_accepted':zero_report['status']=='passed' and float(zero['load'])==0. and float(zero['activation'])==0.,
            'exact_DG2_mesh_and_maps':set(mesh)==set(reference) and all(np.array_equal(mesh[k],reference[k]) for k in reference),
            'CG1_same_displacement_mesh':same_displacement_mesh(mesh,old_mesh),
            'only_workspace_solver_change':cfg['solver']=={**previous_cfg['solver'],'mat_mumps_icntl_14':100},
            'same_physics':all(cfg[k]==previous_cfg[k] for k in ['mu','kappa','radii','meshes','quadrature_degree','pressure_space','active_peak']),
            'single_pressure_scope':cfg['objects']==['ring'] and cfg['passive_loads']==[.02] and cfg['maximum_equilibrium_solves']==1,
            'no_new_zero_or_extra_states':all(p.name=='M0_state_passive_1.npz' for p in raw.glob('*_state_*.npz')),
            'no_contour':not (root/'contour').exists()}
    tangent=json.loads((raw/'M0_tangent.json').read_text())
    checks['tangent']=all(tangent.get(k,np.inf)<=v for k,v in [('pressure',2e-6),('active',2e-6),('total',2e-5)])
    state_path=raw/'M0_state_passive_1.npz'; report=None; iterate_metrics=[]
    checks['saved_pressure_state']=state_path.is_file()
    if state_path.exists():
        state=load_arrays(state_path); metadata=json.loads(state_path.with_suffix('.json').read_text())
        checks['exact_initial_chain']=np.array_equal(state['initial_mixed'],zero['mixed_state'])
        checks['original_pressure_only']=float(state['load'])==.02 and float(state['activation'])==0.
        report=diagnostic_state(mesh,state,metadata,cfg,old_report)
        checks['independent_physical_gates']=report['status']=='passed'
        solver=metadata.get('linear_solver',{})
        checks['linear_solver_qualified']=solver.get('ksp_reason',0)>0 and solver.get('pc_failed_reason')==0 and solver.get('mumps_infog_1')==0 and solver.get('mumps_icntl_14')==100
        paths=sorted((root/'ring/iterates/M0_passive_1').glob('iterate_*.npz'))
        history=metadata['history']; previous=None; first=None
        checks['all_accepted_Newton_iterates_retained']=len(paths)==metadata['iterations']+1==len(history)
        for index,path in enumerate(paths):
            item=load_arrays(path); actual=fields(mesh,item,mu=cfg['mu'],kappa=cfg['kappa'])
            force=actual['force']-cavity(mesh,item['u'],float(item['load']))[1]
            values={'iteration':int(item['iteration']),'solver_residual':float(item['residual']),
                    'max_abs_J_minus_one':float(np.max(np.abs(actual['J']-1))),
                    'independent_free_force_norm':float(np.linalg.norm(force[~mesh['fixed']])),
                    'max_displacement':float(np.max(np.linalg.norm(item['u'],axis=1))),
                    'cavity_area':float(cavity(mesh,item['u'],0.)[0])}
            checks[f'iterate_{index}_identity']=int(item['iteration'])==index and index<len(history) and float(item['residual'])==history[index]['residual'] and np.array_equal(item['u'].ravel(),item['mixed_state'][mesh['mixed_u_map']]) and np.array_equal(item['pressure'].ravel(),item['mixed_state'][mesh['mixed_p_map']]) and float(item['load'])==.02 and float(item['activation'])==0.
            iterate_metrics.append(values)
            if first is None:
                first=item['mixed_state']
            previous=item['mixed_state']
        checks['iterate_endpoints_exact']=first is not None and np.array_equal(first,zero['mixed_state']) and np.array_equal(previous,state['mixed_state'])
    failed_initial=None
    if not state_path.exists() and (root/'last_attempt.npz').exists():
        attempt=load_arrays(raw/'M0_attempt.npz'); last=load_arrays(root/'last_attempt.npz')['mixed_state']
        checks['failed_initial_preserved']=np.array_equal(last,attempt['initial']) and np.array_equal(last,zero['mixed_state'])
        item={'u':last[mesh['mixed_u_map']].reshape(-1,2),'pressure':last[mesh['mixed_p_map']],
              'load':float(attempt['load']),'activation':float(attempt['activation'])}
        physical=fields(mesh,item,cfg['mu'],cfg['kappa'])
        external=cavity(mesh,item['u'],float(attempt['load']))[1]
        failed_initial={'independent_free_force_norm':float(np.linalg.norm((physical['force']-external)[~mesh['fixed']])),
                        'max_abs_J_minus_one':float(np.max(np.abs(physical['J']-1))),
                        'interpretation':'Loaded initial guess only; J=1 is not a qualified volume response.'}
    return {'status':'passed' if all(checks.values()) else 'failed','checks':checks,'state':report,
            'retained_zero':zero_report,'retained_CG1':old_report,'iterates':iterate_metrics,
            'nonlinear_equilibrium_attempts':1,'accepted_equilibria':int(report is not None and report['status']=='passed'),
            'zero_load_reruns':0,'automatic_retries':0,'failed_initial':failed_initial,
            'scope':'one coarse ideal annulus passive equilibrium; Newton iteration is not physiological time',
            'mesh_convergence':'not_run','contour':'not_run','active_contraction':'not_run',
            'three_dimensional_model':'not_run','fsi':'not_run','growth':'not_run','biological_validation':'not_run'}
