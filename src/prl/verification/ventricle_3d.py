"""Independent 3D NumPy reconstruction. No production geometry/UFL/FEM imports."""
import json
from pathlib import Path
import numpy as np

EDGES=[(2,3),(1,3),(1,2),(0,3),(0,2),(0,1)]


def is_retained(config,name,label):
    return bool(config.get('reuse_m0_zero',False) and name=='M0' and label=='zero')


def state_path(root,config,name,label):
    # Path bookkeeping is local so a frozen verifier remains independently portable.
    folder='retained' if is_retained(config,name,label) else 'raw'
    return Path(root)/folder/f'{name}_state_{label}.npz'


def load_arrays(path):
    with np.load(path,allow_pickle=False) as saved:
        return {k:saved[k] for k in saved.files}


def tetra_shape(points):
    bary=np.column_stack((1-points.sum(axis=1),points))
    gradients=np.vstack((-np.ones(3),np.eye(3)))
    values=[bary[:,i]*(2*bary[:,i]-1) for i in range(4)]
    deriv=[(4*bary[:,i]-1)[:,None]*gradients[i] for i in range(4)]
    for i,j in EDGES:
        values.append(4*bary[:,i]*bary[:,j])
        deriv.append(4*(bary[:,i,None]*gradients[j]+bary[:,j,None]*gradients[i]))
    return np.stack(values,axis=1),np.stack(deriv,axis=1),bary


def triangle_shape(points):
    bary=np.column_stack((1-points.sum(axis=1),points))
    gradients=np.array([[-1.,-1.],[1.,0.],[0.,1.]])
    values=[bary[:,i]*(2*bary[:,i]-1) for i in range(3)]
    deriv=[(4*bary[:,i]-1)[:,None]*gradients[i] for i in range(3)]
    for i,j in [(1,2),(0,2),(0,1)]:
        values.append(4*bary[:,i]*bary[:,j])
        deriv.append(4*(bary[:,i,None]*gradients[j]+bary[:,j,None]*gradients[i]))
    return np.stack(values,axis=1),np.stack(deriv,axis=1)


def kinematics(data,u,points):
    vertices=data['coordinates'][data['cells'][:,:4]]
    mapping=np.stack([vertices[:,i]-vertices[:,0] for i in [1,2,3]],axis=-1)
    shape,derivative,bary=tetra_shape(points)
    gradients=np.einsum('qai,cij->cqaj',derivative,np.linalg.inv(mapping))
    F=np.eye(3)+np.einsum('cai,cqaj->cqij',u[data['cells']],gradients)
    return F,np.linalg.det(F),gradients,np.abs(np.linalg.det(mapping)),bary,vertices


def extra_points():
    return np.array([[i,j,k] for i in range(6) for j in range(6-i) for k in range(6-i-j)],dtype=float)/5


def fields(data,state,config):
    F,J,gradients,detmap,bary,vertices=kinematics(data,state['u'],data['qpoints'])
    if not np.isfinite(J).all() or np.min(J)<=0:
        raise ValueError('Nonpositive/nonfinite reconstructed J')
    weights=detmap[:,None]*data['qweights']
    position=np.einsum('qa,cai->cqi',bary,vertices)
    normal=position/np.square(config['axes'])
    normal/=np.linalg.norm(normal,axis=-1)[...,None]
    tensor=(np.eye(3)-np.einsum('cqi,cqj->cqij',normal,normal))/2
    pressure_values=np.asarray(state['pressure'])
    expected=len(data['pressure_coordinates'])
    if pressure_values.shape not in ((expected,),(1,expected)):
        raise ValueError('Unrecognized scalar pressure layout')
    pressure_values=pressure_values.reshape(expected)
    pressure=np.einsum('qa,ca->cq',bary,pressure_values[data['pressure_cells']])
    inverse_t=np.linalg.inv(F).swapaxes(-1,-2)
    invariant=np.sum(F*F,axis=(-1,-2))
    passive=config['mu']*J[...,None,None]**(-2/3)*(F-invariant[...,None,None]/3*inverse_t)
    passive+=pressure[...,None,None]*J[...,None,None]*inverse_t
    factor=(data['layers']==3)[:,None,None,None]*float(state['activation'])
    active=factor*np.einsum('cqik,cqkj->cqij',F,tensor)
    P=passive+active
    stress=np.einsum('cqik,cqjk->cqij',P,F)/J[...,None,None]
    active_stress=np.einsum('cqik,cqjk->cqij',active,F)/J[...,None,None]
    force=np.zeros_like(data['coordinates']); active_force=np.zeros_like(force)
    for target,piola in [(force,P),(active_force,active)]:
        local=np.einsum('cqij,cqaj,cq->cai',piola,gradients,weights)
        np.add.at(target,data['cells'].ravel(),local.reshape(-1,3))
    weak=np.zeros(len(data['pressure_coordinates']))
    local=np.einsum('qa,cq,cq->ca',bary,J-1-pressure/config['kappa'],weights)
    np.add.at(weak,data['pressure_cells'].ravel(),local.ravel())
    FA=np.einsum('cqik,cqkj->cqij',F,tensor)
    energy=float(.5*float(state['activation'])*np.sum(weights*(data['layers']==3)[:,None]*(np.sum(FA*F,axis=(-1,-2))-1)))
    return {'F':F,'J':J,'stress':stress,'active_stress':active_stress,'force':force,
            'active_force':active_force,'active_energy':energy,'weak':weak,'weights':weights}


def cavity(data,u,pressure):
    # Inner triangles are oriented away from the lumen. The fixed z=0 cap has zero volume term.
    n,dn=triangle_shape(data['facet_qpoints'])
    nodes=(data['coordinates']+u)[data['inner_faces']]
    position=np.einsum('qa,fai->fqi',n,nodes)
    tangents=np.einsum('qar,fai->fqir',dn,nodes)
    area_vector=np.cross(tangents[:,:,:,0],tangents[:,:,:,1])
    weights=data['facet_qweights']
    volume=float(np.einsum('fqi,fqi,q->',position,area_vector,weights)/3)
    force=np.zeros_like(u)
    local=pressure*np.einsum('qa,fqi,q->fai',n,area_vector,weights)
    np.add.at(force,data['inner_faces'].ravel(),local.reshape(-1,3))
    return volume,force


def mapping_checks(data):
    local=data['coordinates'][data['cells']]
    midpoints=np.stack([(local[:,i]+local[:,j])/2 for i,j in EDGES],axis=1)
    return {'p2_order':bool(np.max(np.abs(local[:,4:]-midpoints))<1e-12),
            'p1_order':bool(np.max(np.abs(data['pressure_coordinates'][data['pressure_cells']]-local[:,:4]))<1e-12),
            'volume_weights':abs(float(data['qweights'].sum())-1/6)<1e-13,
            'surface_weights':abs(float(data['facet_qweights'].sum())-.5)<1e-13}


def state_audit(data,state,metadata,config):
    result=fields(data,state,config)
    volume,external=cavity(data,state['u'],float(state['load']))
    reference,_=cavity(data,np.zeros_like(state['u']),0.)
    fixed=data['fixed'].astype(bool); residual=result['force']-external
    reaction=np.where(fixed,residual,0.)
    position=data['coordinates']+state['u']
    force_balance=float(np.linalg.norm((reaction+external).sum(axis=0)))
    moment_balance=float(np.linalg.norm(np.cross(position,reaction+external).sum(axis=0)))
    errors={k:float(np.max(np.abs(result[k]-state[k]))) for k in ['F','J','stress','active_stress']}
    free=float(np.linalg.norm(residual[~fixed])); weak=float(np.linalg.norm(result['weak']))
    force_error=float(np.max(np.abs((residual-state['force_residual'])[~fixed])))
    weak_error=float(np.max(np.abs(result['weak']-state['weak_residual'])))
    _,sample_j,_,_,_,_=kinematics(data,state['u'],extra_points())
    max_j=max(float(np.max(np.abs(result['J']-1))),float(np.max(np.abs(sample_j-1))))
    min_j=min(float(result['J'].min()),float(sample_j.min()))
    delta=.01*np.sin(data['coordinates']+np.array([.2,.4,.6])); delta[fixed]=0.
    h=1e-5; p=float(state['load'])
    plus,_=cavity(data,state['u']+h*delta,p); minus,_=cavity(data,state['u']-h*delta,p)
    pressure_work=float(np.sum(external*delta)); pressure_difference=p*(plus-minus)/(2*h)
    active_work=float(np.sum(result['active_force']*delta))
    if float(state['activation'])!=0.:
        ep=fields(data,{**state,'u':state['u']+h*delta},config)['active_energy']
        em=fields(data,{**state,'u':state['u']-h*delta},config)['active_energy']
        active_difference=(ep-em)/(2*h)
    else:
        active_difference=0.
    checks={**mapping_checks(data),
        'mixed_map_consistency':bool(np.array_equal(state['u'].ravel(),state['mixed_state'][data['mixed_u_map'].ravel()])
            and np.array_equal(state['pressure'].ravel(),state['mixed_state'][data['mixed_p_map'].ravel()])),
        'snes':metadata['snes_reason']>0 and metadata['iterations']<=30,
        'solver_free_residual':metadata['free_residual_norm']<=1e-9,
        'independent_free_force':free<=2e-6,'weak_pressure':weak<=1e-8,
        'kinematics':max(errors['F'],errors['J'])<=1e-10,
        'stress':max(errors['stress'],errors['active_stress'])<=2e-7,
        'free_force_agreement':force_error<=2e-7,'weak_agreement':weak_error<=2e-7,
        'positive_J':min_j>0,'local_volume':max_j<=.01,
        'cavity_volume_agreement':abs(volume-metadata['cavity_volume'])<=1e-10,
        'fixed_displacement':float(np.max(np.abs(state['u'][fixed])))<=1e-12,
        'force_balance_with_support':force_balance<=2e-6,
        'moment_balance_with_support':moment_balance<=2e-6,
        'pressure_virtual_work':abs(pressure_work-pressure_difference)<=2e-6,
        'active_virtual_work':abs(active_work-active_difference)<=2e-6,
        'active_energy':abs(result['active_energy']-metadata['active_energy'])<=2e-7,
        'active_localization':bool(np.max(np.abs(result['active_stress'][data['layers']!=3]))==0),
        'linear_solver':metadata['linear_solver']['status']==('not_run' if metadata['iterations']==0 else 'passed'),
    }
    if p==0 and float(state['activation'])==0:
        checks['zero_displacement']=float(np.max(np.abs(state['u'])))<=1e-10
    return {'status':'passed' if all(checks.values()) else 'failed','checks':checks,
            'failed_checks':[k for k,v in checks.items() if not v],
            'pressure':p,'activation':float(state['activation']),'cavity_volume':volume,
            'reference_volume':reference,'volume_change':volume/reference-1,
            'max_abs_J_minus_one':max_j,'J_min':min_j,
            'quadrature_max_abs_J_minus_one':float(np.max(np.abs(result['J']-1))),
            'max_displacement':float(np.max(np.linalg.norm(state['u'],axis=1))),
            'independent_free_force':free,'weak_pressure_norm':weak,'force_assembly_error':force_error,
            'field_errors':errors,'force_balance':force_balance,'moment_balance':moment_balance,
            'pressure_virtual_work_error':abs(pressure_work-pressure_difference),
            'active_virtual_work_error':abs(active_work-active_difference),
            'cavity_reconstruction_error':abs(volume-metadata['cavity_volume'])}


def verify(root):
    root=Path(root); config=json.loads((root/'configuration.json').read_text())
    cases={}; checks={}; iterates={}; attempted=0; accepted=0; reused=0
    if config.get('reuse_m0_zero',False):
        interface=root/'restart_interface.json'
        checks['native_restart_interface']=interface.exists() and json.loads(interface.read_text())['status']=='passed'
    for case in config['meshes']:
        name=case['name']; cases[name]={}; iterates[name]={}
        mesh_path=root/'raw'/f'{name}_mesh.npz'
        if not mesh_path.exists():
            checks[name+'_complete']=False
            continue
        data=load_arrays(mesh_path)
        geometry=json.loads((root/'raw'/f'{name}_geometry.json').read_text())
        checks[name+'_geometry']=geometry['status']=='passed'
        tangent_path=root/'raw'/f'{name}_tangent.json'
        checks[name+'_tangent']=False
        if tangent_path.exists():
            tangent=json.loads(tangent_path.read_text())
            checks[name+'_tangent']=all(tangent[k]<=v for k,v in [('pressure',2e-6),('active',2e-6),('total',2e-5)])
        for spec in config['states']:
            label=spec['label']; retained=is_retained(config,name,label)
            path=state_path(root,config,name,label)
            if not path.exists():
                continue
            attempted+=int(not retained); reused+=int(retained)
            state=load_arrays(path); metadata=json.loads(path.with_suffix('.json').read_text())
            try:
                audit=state_audit(data,state,metadata,config)
            except Exception as error:
                audit={'status':'failed','reason':repr(error)}
            audit['source']='retained' if retained else 'new'
            cases[name][label]=audit
            checks[name+'_'+label]=audit['status']=='passed'
            accepted+=int(audit['status']=='passed' and not retained)
            initial=np.zeros_like(state['mixed_state']) if spec['initial'] is None else load_arrays(state_path(root,config,name,spec['initial']))['mixed_state']
            checks[name+'_'+label+'_initial']=bool(np.array_equal(initial,state['initial_mixed']))
            checks[name+'_'+label+'_loads']=float(state['load'])==spec['p'] and float(state['activation'])==spec['Ta']
            paths=sorted((root/('retained/iterates' if retained else 'iterates')/f'{name}_{label}').glob('iterate_*.npz'))
            saved=[]
            for entry in paths:
                saved_state=load_arrays(entry)
                _,j,_,_,_,_=kinematics(data,saved_state['u'],data['qpoints'])
                saved.append({'iteration':int(saved_state['iteration']),'minimum_J':float(j.min()),
                              'max_abs_J_minus_one':float(np.max(np.abs(j-1))),'finite':bool(np.isfinite(j).all())})
            iterates[name][label]=saved
            checks[name+'_'+label+'_iterates']=bool(paths and all(s['finite'] and s['minimum_J']>0 for s in saved)
                and len(paths)==metadata['iterations']+1
                and np.allclose(load_arrays(paths[-1])['mixed_state'],state['mixed_state'],rtol=0,atol=1e-12))
        records=cases[name]
        checks[name+'_complete']=len(records)==len(config['states'])
        for label in ['pressure_2','active_2','combined_2']:
            if label not in records or 'volume_change' not in records[label]:
                continue
            change=records[label]['volume_change']
            if label=='pressure_2':
                checks[name+'_pressure_expands']=change>0
            elif label=='active_2':
                checks[name+'_active_contracts']=change<0
            else:
                baseline=records['pressure_2']['cavity_volume']
                records[label]['change_from_pressurized']=records[label]['cavity_volume']/baseline-1
                checks[name+'_combined_contracts_vs_pressure']=records[label]['change_from_pressurized']<0
    comparison={}
    for label in ['pressure_2','active_2','combined_2']:
        if all('volume_change' in cases.get(n,{}).get(label,{}) for n in ['M0','M1']):
            a=cases['M0'][label]['volume_change']; b=cases['M1'][label]['volume_change']
            absolute=abs(a-b); relative=absolute/max(abs(a),abs(b),1e-12)
            comparison[label]={'absolute':absolute,'relative':relative}
            checks[label+'_mesh_response']=absolute<=.002 and relative<=.05
    return {'status':'passed' if all(checks.values()) else 'failed','checks':checks,
            'failed_checks':[k for k,v in checks.items() if not v], 'cases':cases,'iterates':iterates,
            'attempted_states':attempted,'accepted_states':accepted,'reused_states':reused,'comparison':comparison,
            'biological_validation':'not_run','fsi':'not_run','growth':'not_run'}
