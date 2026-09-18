"""Independent NumPy P2/P1 ring audit. No production UFL or FEM imports."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from scipy.optimize import brentq


def load_arrays(path):
    with np.load(path,allow_pickle=False) as data:
        return {k:data[k] for k in data.files}


def shape(points):
    bary=np.column_stack((1-points.sum(axis=1),points))
    gradients=np.array([[-1.,-1.],[1.,0.],[0.,1.]])
    values=[bary[:,i]*(2*bary[:,i]-1) for i in range(3)]
    deriv=[(4*bary[:,i]-1)[:,None]*gradients[i] for i in range(3)]
    for i,j in [(1,2),(0,2),(0,1)]:
        values.append(4*bary[:,i]*bary[:,j])
        deriv.append(4*(bary[:,i,None]*gradients[j]+bary[:,j,None]*gradients[i]))
    return np.stack(values,axis=1),np.stack(deriv,axis=1),bary


def pressure_basis(mesh):
    """Independent scalar basis; old archives unambiguously default to CG1."""
    kind=str(np.asarray(mesh.get('pressure_space','CG1')).item())
    n,_,bary=shape(mesh['qpoints'])
    basis={'CG1':bary,'DG2':n}.get(kind)
    if basis is None or mesh['pressure_cells'].shape[1]!=basis.shape[1]:
        raise ValueError('Unrecognized pressure basis or cell map')
    if kind=='DG2':
        local=mesh['pressure_cells'].ravel()
        if len(np.unique(local))!=len(local):
            raise ValueError('DG2 pressure degrees of freedom must be cell-local')
        if 'pressure_coordinates' not in mesh or not np.allclose(
                mesh['pressure_coordinates'][mesh['pressure_cells']],mesh['coordinates'][mesh['cells']],rtol=0,atol=1e-12):
            raise ValueError('DG2 pressure coordinate ordering differs from independent quadratic basis')
    return basis


def fields(mesh,state,mu=1.,kappa=1000.):
    nodes,cells=mesh['coordinates'],mesh['cells']
    v=nodes[cells[:,:3]]
    mapping=np.stack((v[:,1]-v[:,0],v[:,2]-v[:,0]),axis=-1)
    n,dn,bary=shape(mesh['qpoints'])
    gradients=np.einsum('qai,cij->cqaj',dn,np.linalg.inv(mapping))
    weights=np.abs(np.linalg.det(mapping))[:,None]*mesh['qweights'][None,:]
    position=np.einsum('qa,cai->cqi',bary,v)
    deformation=np.broadcast_to(np.eye(3),(len(cells),len(n),3,3)).copy()
    deformation[:,:,:2,:2]+=np.einsum('cai,cqaj->cqij',state['u'][cells],gradients)
    determinant=np.linalg.det(deformation)
    if not np.all(np.isfinite(determinant)) or np.min(determinant)<=0:
        raise ValueError('invalid saved deformation determinant')
    pressure_values=np.asarray(state['pressure'])
    expected=len(mesh['pressure_coordinates']) if 'pressure_coordinates' in mesh else int(mesh['pressure_cells'].max()+1)
    if pressure_values.shape not in ((expected,),(1,expected)):
        raise ValueError('saved pressure has an unrecognized shape')
    pressure_values=pressure_values.reshape(expected)
    pressure_shape=pressure_basis(mesh)
    pressure=np.einsum('qa,ca->cq',pressure_shape,pressure_values[mesh['pressure_cells']])
    inverse_t=np.linalg.inv(deformation).swapaxes(-1,-2)
    invariant=np.sum(deformation*deformation,axis=(-1,-2))
    passive=mu*determinant[:,:,None,None]**(-2/3)*(deformation-invariant[:,:,None,None]/3*inverse_t)
    passive+=pressure[:,:,None,None]*determinant[:,:,None,None]*inverse_t
    fiber=np.zeros(position.shape[:-1]+(3,))
    radius=np.linalg.norm(position,axis=-1)
    fiber[:,:,0]=-position[:,:,1]/radius
    fiber[:,:,1]=position[:,:,0]/radius
    stretched=np.einsum('cqij,cqj->cqi',deformation,fiber)
    active=(mesh['layers']==3)[:,None,None,None]*float(state['activation'])*np.einsum('cqi,cqj->cqij',stretched,fiber)
    piola=passive+active
    stress=np.einsum('cqik,cqjk->cqij',piola,deformation)/determinant[:,:,None,None]
    stress_active=np.einsum('cqik,cqjk->cqij',active,deformation)/determinant[:,:,None,None]
    force=np.zeros_like(nodes)
    local=np.einsum('cqij,cqaj,cq->cai',piola[:,:,:2,:2],gradients,weights)
    np.add.at(force,cells.ravel(),local.reshape(-1,2))
    pressure_residual=np.zeros_like(pressure_values)
    local_pressure=np.einsum('qa,cq,cq->ca',pressure_shape,determinant-1-pressure/kappa,weights)
    np.add.at(pressure_residual,mesh['pressure_cells'].ravel(),local_pressure.ravel())
    active_energy=.5*float(state['activation'])*np.sum(weights*(mesh['layers']==3)[:,None]*(np.sum(stretched**2,axis=-1)-1))
    active_local=np.einsum('cqij,cqaj,cq->cai',active[:,:,:2,:2],gradients,weights)
    active_force=np.zeros_like(nodes)
    np.add.at(active_force,cells.ravel(),active_local.reshape(-1,2))
    return {'F':deformation,'J':determinant,'stress':stress,'active_stress':stress_active,
            'force':force,'pressure_residual':pressure_residual,'weights':weights,
            'active_energy':active_energy,'active_force':active_force}


def cavity(mesh,u,pressure):
    points=mesh['coordinates']+u
    parameter,weight=np.polynomial.legendre.leggauss(4)
    s=(parameter+1)/2
    weight=weight/2
    n=np.stack((2*s*s-3*s+1,4*s-4*s*s,2*s*s-s),axis=1)
    dn=np.stack((4*s-3,4-8*s,4*s-1),axis=1)
    curves=points[mesh['inner_edges']]
    q=np.einsum('qa,eai->eqi',n,curves)
    tangent=np.einsum('qa,eai->eqi',dn,curves)
    normal_line=np.stack((tangent[:,:,1],-tangent[:,:,0]),axis=-1)
    traction=pressure*normal_line
    force=np.zeros_like(points)
    local=np.einsum('qa,eqi,q->eai',n,traction,weight)
    np.add.at(force,mesh['inner_edges'].ravel(),local.reshape(-1,2))
    area=.5*np.einsum('eq,q->',q[:,:,0]*tangent[:,:,1]-q[:,:,1]*tangent[:,:,0],weight)
    moment=np.einsum('eq,q->',q[:,:,0]*traction[:,:,1]-q[:,:,1]*traction[:,:,0],weight)
    return float(area),force,float(moment)


def analytic_c(pressure,inner=20/27,outer=1.):
    if pressure==0:
        return 0.
    def residual(c):
        a2,b2=inner*inner+c,outer*outer+c
        return np.log(outer*np.sqrt(a2)/(inner*np.sqrt(b2)))+.5*c*(1/a2-1/b2)-pressure
    return float(brentq(residual,0.,20.,xtol=1e-14))


def state_audit(mesh,state,metadata,config):
    f=fields(mesh,state,config['mu'],config['kappa'])
    p=float(state['load'])
    area,external,moment=cavity(mesh,state['u'],p)
    reference,_,_=cavity(mesh,np.zeros_like(state['u']),0.)
    residual=f['force']-external
    fixed=mesh['fixed'].astype(bool)
    scale=max(1.,np.linalg.norm(external))
    free=float(np.linalg.norm(residual[~fixed])/scale)
    reaction=float(np.linalg.norm(residual[fixed])/scale)
    weak=float(np.linalg.norm(f['pressure_residual']))
    max_j=float(np.max(np.abs(f['J']-1)))
    f_error=float(np.max(np.abs(f['F']-state['F'])))
    j_error=float(np.max(np.abs(f['J']-state['J'])))
    s_error=float(np.max(np.abs(f['stress']-state['stress'])))
    a_error=float(np.max(np.abs(f['active_stress']-state['active_stress'])))
    delta=np.column_stack((np.sin(mesh['coordinates'][:,0]+.2*mesh['coordinates'][:,1]),
                           np.cos(.4*mesh['coordinates'][:,0]-mesh['coordinates'][:,1])))*.01
    h=1e-5
    plus,_,_=cavity(mesh,state['u']+h*delta,p)
    minus,_,_=cavity(mesh,state['u']-h*delta,p)
    work=float(np.sum(external*delta))
    pressure_work_error=abs(work-p*(plus-minus)/(2*h))/max(1.,abs(work))
    active_work=float(np.sum(f['active_force']*delta))
    if float(state['activation'])!=0.:
        plus_active=fields(mesh,{**state,'u':state['u']+h*delta},config['mu'],config['kappa'])['active_energy']
        minus_active=fields(mesh,{**state,'u':state['u']-h*delta},config['mu'],config['kappa'])['active_energy']
        active_difference=float((plus_active-minus_active)/(2*h))
    else:
        active_difference=0.
    active_work_error=abs(active_work-active_difference)/max(1.,abs(active_work))
    active_energy_error=float(abs(f['active_energy']-metadata['active_energy']))
    force_compare=float(np.max(np.abs(residual-state['force_residual'])))
    active_zero=float(np.max(np.abs(state['active_stress'][mesh['layers']!=3])))
    checks={
        'snes_convergence':metadata['snes_reason']>0 and metadata['iterations']<=30,
        'solver_free_residual':metadata['free_residual_norm']<=1e-9,
        'independent_free_force':free<=2e-6,
        'independent_weak_pressure':weak<=1e-8,
        'positive_J':bool(np.min(f['J'])>0),
        'local_volume':max_j<=.01,
        'kinematics_reconstruction':max(f_error,j_error)<=1e-10,
        'stress_reconstruction':max(s_error,a_error)<=2e-7,
        'force_assembly_agreement':force_compare<=2e-7,
        'closed_pressure':max(float(np.linalg.norm(external.sum(axis=0))),abs(moment))/scale<=2e-6,
        'gauge_reactions':reaction<=2e-6,
        'pressure_virtual_work':pressure_work_error<=2e-6,
        'active_localization':active_zero==0.,
        'active_energy_reconstruction':active_energy_error<=2e-7,
        'active_virtual_work':active_work_error<=2e-6,
        'gauge_displacement':float(np.max(np.abs(state['u'][fixed])))<=1e-12,
    }
    result={'status':'passed' if all(checks.values()) else 'failed','checks':checks,
            'pressure':p,'activation':float(state['activation']),'cavity_area':area,
            'cavity_area_change':area/reference-1,
            'max_abs_J_minus_one':max_j,'J_min':float(f['J'].min()),'J_max':float(f['J'].max()),
            'weighted_mean_J':float(np.sum(f['J']*f['weights'])/f['weights'].sum()),
            'independent_free_force':free,'pressure_weak_residual':weak,'gauge_reactions':reaction,
            'F_error':f_error,'J_error':j_error,'stress_error':s_error,'force_assembly_error':force_compare,
            'pressure_virtual_work_error':pressure_work_error,
            'pressure_virtual_work':work,'pressure_area_difference_work':float(p*(plus-minus)/(2*h)),
            'active_virtual_work':active_work,'active_energy_difference_work':active_difference,
            'active_virtual_work_error':active_work_error,'active_energy_error':active_energy_error}
    if float(state['activation'])==0. and p>0 and config.get('geometry_kind','ring')=='ring':
        c=analytic_c(p)
        expected=c/config['radii'][0]**2
        result['analytic_area_change']=expected
        result['analytic_relative_error']=abs(result['cavity_area_change']-expected)/expected
        xy=mesh['coordinates']
        r=np.linalg.norm(xy,axis=-1)
        # Exactly the contract's point gauge: translate to leave outer (B,0) fixed.
        exact=(np.sqrt(r*r+c)/r-1)[:,None]*xy
        exact[:,0]-=np.sqrt(config['radii'][-1]**2+c)-config['radii'][-1]
        result['radial_displacement_l2_error']=float(np.linalg.norm(state['u']-exact)/np.linalg.norm(exact))
    return result


def verify_fenicsx_ring(root,stage='all',save=False,parent_root=None):
    root=Path(root)
    config=json.loads((root/'configuration.json').read_text(encoding='utf-8'))
    if config.get('parent_result') and parent_root is None:
        workspace=next(p for p in root.resolve().parents if (p/'AGENTS.md').is_file())
        parent_root=workspace/config['parent_result']
    parent_root=Path(parent_root) if parent_root is not None else root
    g0=json.loads((parent_root/'g0_runtime.json').read_text(encoding='utf-8'))
    cases={}
    geometry={}
    checks={'g0_runtime':g0['status']=='passed'}
    for case in config['meshes']:
        name=case['name']
        mesh_path=root/'raw'/f'{name}_mesh.npz'
        if not mesh_path.exists():
            checks[name+'_geometry']=False
            continue
        mesh=load_arrays(mesh_path)
        geom=json.loads((root/'raw'/f'{name}_geometry.json').read_text())
        geometry[name]=geom
        local=mesh['coordinates'][mesh['cells']]
        expected_midpoints=np.stack(((local[:,1]+local[:,2])/2,(local[:,0]+local[:,2])/2,(local[:,0]+local[:,1])/2),axis=1)
        checks[name+'_basis_mapping']=bool(np.max(np.abs(local[:,3:]-expected_midpoints))<1e-12 and
            np.max(np.abs(mesh['pressure_coordinates'][mesh['pressure_cells']]-local[:,:3]))<1e-12 and
            abs(mesh['qweights'].sum()-.5)<1e-13)
        checks[name+'_geometry']=geom['minimum_signed_area']>0 and geom['minimum_angle_degrees']>=20 and geom['edge_manifold'] and geom['boundary_count_correct'] and geom['circle_area_relative_error']<=(.002 if name=='M0' else .0005)
        tangent_path=root/'raw'/f'{name}_tangent.json'
        if tangent_path.exists():
            tangent=json.loads(tangent_path.read_text())
            checks[name+'_tangent']=all(tangent[k]<=v for k,v in [('pressure',2e-6),('active',2e-6),('total',2e-5)])
        else:
            checks[name+'_tangent']=False
        records={}
        paths=list((root/'raw').glob(f'{name}_state_*.npz'))
        if parent_root!=root:
            paths+=list((parent_root/'raw').glob(f'{name}_state_passive_*.npz'))
            original_mesh=load_arrays(parent_root/'raw'/f'{name}_mesh.npz')
            checks[name+'_parent_mesh_identity']=all(np.array_equal(mesh[k],original_mesh[k]) for k in
                ['coordinates','cells','pressure_coordinates','pressure_cells','layers','qpoints','qweights','fixed','inner_edges'])
        for path in sorted(paths):
            label=path.stem.split('_state_',1)[1]
            metadata=json.loads(path.with_suffix('.json').read_text())
            record=state_audit(mesh,load_arrays(path),metadata,config)
            records[label]=record
            checks[name+'_'+label]=record['status']=='passed'
        cases[name]=records
        checks[name+'_G1_complete']=all(f'passive_{i}' in records for i in range(5))
        previous=None
        for i in range(5):
            path=parent_root/'raw'/f'{name}_state_passive_{i}.npz'
            if not path.exists():
                break
            retained=load_arrays(path)
            expected=np.zeros_like(retained['mixed_state']) if previous is None else previous
            checks[f'{name}_initial_chain_{i}']=bool(np.array_equal(retained['initial_mixed'],expected))
            previous=retained['mixed_state']
        for i in range(1,5):
            record=records.get(f'passive_{i}',{})
            checks[f'{name}_analytic_{i}']=record.get('analytic_relative_error',float('inf'))<=(.02 if name=='M0' else .01)
            if name=='M1':
                checks[f'{name}_radial_{i}']=record.get('radial_displacement_l2_error',float('inf'))<=.01
        if stage=='all':
            checks[name+'_G2_complete']=all(f'{case_name}_{i}' in records for case_name in ['active','combined'] for i in range(1,5))
            for case_name in ['active','combined']:
                previous=load_arrays(parent_root/'raw'/f'{name}_state_passive_0.npz')['mixed_state']
                for i in range(1,5):
                    path=root/'raw'/f'{name}_state_{case_name}_{i}.npz'
                    if not path.exists():
                        break
                    retained=load_arrays(path)
                    checks[f'{name}_{case_name}_initial_chain_{i}']=bool(np.array_equal(retained['initial_mixed'],previous))
                    previous=retained['mixed_state']
            if checks[name+'_G2_complete'] and 'passive_2' in records:
                a=records['active_4']['cavity_area_change']
                b=records['combined_4']['cavity_area_change']
                p=records['passive_2']['cavity_area_change']
                checks[name+'_four_conditions']=p>=.01 and a<=-.005 and b-a>=.005 and p-b>=.005
    comparisons={}
    labels=['passive_4']+(['active_4','combined_4'] if stage=='all' else [])
    for label in labels:
        if all(label in cases.get(name,{}) for name in ['M0','M1']):
            first,second=[cases[n][label]['cavity_area_change'] for n in ['M0','M1']]
            absolute=abs(first-second)
            relative=absolute/max(abs(first),abs(second),1e-15)
            comparisons[label]={'absolute':absolute,'relative':relative}
            checks[label+'_mesh_response']=absolute<=.002 and relative<=.05
        else:
            checks[label+'_mesh_response']=False
    result={'status':'passed' if all(checks.values()) else 'failed','stage':stage,
            'checks':checks,'failed_checks':[k for k,v in checks.items() if not v],
            'geometry':geometry,'cases':cases,'mesh_comparisons':comparisons,
            'biology':'not_run','independence':'NumPy P2/P1 differentiation and force assembly; no production UFL import'}
    if save:
        (root/('g1_verification.json' if stage=='passive' else 'verification.json')).write_text(json.dumps(result,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    return result
