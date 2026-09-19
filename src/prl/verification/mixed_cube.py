"""Independent NumPy verification of cube MMS; no production-form imports."""
from collections import defaultdict
import math
import numpy as np
from .ventricle_3d import EDGES, tetra_shape, triangle_shape, kinematics, extra_points, mapping_checks


def quadrature(dimension, order=6):
    """Gauss-Duffy rule; order 6 integrates every tetra polynomial of total degree 8."""
    nodes, weights = np.polynomial.legendre.leggauss(order)
    nodes, weights = (nodes+1)/2, weights/2
    if dimension == 3:
        points = [[a,(1-a)*b,(1-a)*(1-b)*c] for a in nodes for b in nodes for c in nodes]
        mass = [weights[i]*weights[j]*weights[k]*(1-a)**2*(1-b)
                for i,a in enumerate(nodes) for j,b in enumerate(nodes) for k,c in enumerate(nodes)]
    elif dimension == 2:
        points = [[a,(1-a)*b] for a in nodes for b in nodes]
        mass = [weights[i]*weights[j]*(1-a) for i,a in enumerate(nodes) for j,b in enumerate(nodes)]
    else:
        raise ValueError('Only triangle/tetrahedron rules supported')
    return np.asarray(points), np.asarray(mass)


def exact_kinematics(points, kind):
    points = np.asarray(points)
    shape = points.shape[:-1]
    displacement = np.zeros_like(points)
    gradient = np.zeros(shape+(3,3))
    hessian = np.zeros(shape+(3,3,3))
    if kind == 'affine':
        gradient[...] = np.diag([.001,-.0004,-.0003])
        displacement = points*np.array([.001,-.0004,-.0003])
    elif kind == 'shear':
        gradient[...,0,1] = .1
        displacement[...,0] = .1*points[...,1]
    elif kind == 'quadratic_volume':
        displacement[...,0] = .002*points[...,0]**2
        gradient[...,0,0] = .004*points[...,0]
        hessian[...,0,0,0] = .004
    elif kind == 'isochoric_mms':
        sine,cosine=np.sin(np.pi*points),np.cos(np.pi*points)
        value=.002*sine[...,1]*sine[...,2]
        displacement[...,0]=value
        gradient[...,0,1]=.002*np.pi*cosine[...,1]*sine[...,2]
        gradient[...,0,2]=.002*np.pi*sine[...,1]*cosine[...,2]
        hessian[...,0,1,1]=hessian[...,0,2,2]=-np.pi**2*value
        hessian[...,0,1,2]=hessian[...,0,2,1]=.002*np.pi**2*cosine[...,1]*cosine[...,2]
    elif kind == 'mms':
        sine, cosine = np.sin(np.pi*points), np.cos(np.pi*points)
        value = .002*np.prod(sine, axis=-1)
        displacement[...,0] = value
        for j in range(3):
            others = [axis for axis in range(3) if axis != j]
            gradient[...,0,j] = .002*np.pi*cosine[...,j]*np.prod(sine[...,others],axis=-1)
            for k in range(3):
                if j == k:
                    hessian[...,0,j,k] = -np.pi**2*value
                else:
                    remaining = 3-j-k
                    hessian[...,0,j,k] = .002*np.pi**2*cosine[...,j]*cosine[...,k]*sine[...,remaining]
    else:
        raise ValueError('Unknown manufactured field')
    return displacement, gradient, hessian


def piola(F, pressure, mu=1.):
    J = np.linalg.det(F)
    if not np.isfinite(J).all() or np.min(J) <= 0:
        raise ValueError('Nonpositive/nonfinite valid-state J')
    inverse_t = np.linalg.inv(F).swapaxes(-1,-2)
    invariant = np.sum(F*F,axis=(-1,-2))
    P = mu*J[...,None,None]**(-2/3)*(F-invariant[...,None,None]/3*inverse_t)
    return P+pressure[...,None,None]*J[...,None,None]*inverse_t


def exact_fields(points, kind, kappa, mu=1.):
    u, grad, hessian = exact_kinematics(points,kind)
    F = np.eye(3)+grad; J = np.linalg.det(F); pressure = kappa*(J-1)
    inverse_t = np.linalg.inv(F).swapaxes(-1,-2)
    invariant = np.sum(F*F,axis=(-1,-2)); factor = J**(-2/3)
    base = F-invariant[...,None,None]/3*inverse_t
    body = np.zeros_like(points)
    for axis in range(3):
        derivative = hessian[...,axis]
        dJ = J*np.sum(inverse_t*derivative,axis=(-1,-2))
        dI = 2*np.sum(F*derivative,axis=(-1,-2))
        dG = -inverse_t @ derivative.swapaxes(-1,-2) @ inverse_t
        derivative_P = mu*((-2/3*factor*dJ/J)[...,None,None]*base
            +factor[...,None,None]*(derivative-dI[...,None,None]/3*inverse_t-invariant[...,None,None]/3*dG))
        derivative_P += ((kappa*J+pressure)*dJ)[...,None,None]*inverse_t+(pressure*J)[...,None,None]*dG
        body -= derivative_P[..., :, axis]
    return {'u':u,'grad':grad,'F':F,'J':J,'pressure':pressure,'P':piola(F,pressure,mu),'body':body}


def boundary_data(coordinates, cells):
    """Independent boundary extraction from tetra incidence; tags 1..6 are x0,x1,y0,y1,z0,z1."""
    incidence = defaultdict(list)
    for cell_id, cell in enumerate(cells):
        for opposite in range(4):
            face = tuple(sorted(int(cell[i]) for i in range(4) if i != opposite))
            incidence[face].append(cell_id)
    lookup = {tuple(np.round(point,13)):i for i,point in enumerate(coordinates)}
    faces, tags, owners = [], [], []
    for face, owner in sorted(incidence.items()):
        if len(owner) == 2:
            continue
        if len(owner) != 1:
            raise ValueError('Nonmanifold tetra mesh')
        vertex = coordinates[list(face)]
        identifiers = [2*axis+side+1 for axis in range(3) for side in [0,1]
                       if np.all(np.abs(vertex[:,axis]-side)<1e-12)]
        if len(identifiers) != 1:
            raise ValueError('Boundary not on a unit-cube face')
        mids = [lookup[tuple(np.round((vertex[i]+vertex[j])/2,13))] for i,j in [(1,2),(0,2),(0,1)]]
        faces.append(list(face)+mids); tags.append(identifiers[0]); owners.append(owner[0])
    return {'boundary_faces':np.asarray(faces,dtype=np.int64), 'boundary_tags':np.asarray(tags),
            'boundary_owners':np.asarray(owners)}


def surface_load(data, case, points=None, weights=None):
    points = data['facet_qpoints'] if points is None else points
    weights = data['facet_qweights'] if weights is None else weights
    basis,_ = triangle_shape(points)
    vertices = data['coordinates'][data['boundary_faces'][:,:3]]
    bary = np.column_stack((1-points.sum(axis=1),points))
    xyz = np.einsum('qa,fai->fqi',bary,vertices)
    measure = np.linalg.norm(np.cross(vertices[:,1]-vertices[:,0],vertices[:,2]-vertices[:,0]),axis=-1)
    tags = data['boundary_tags']; normals = np.zeros((len(tags),3))
    normals[np.arange(len(tags)),(tags-1)//2] = np.where(tags%2==1,-1.,1.)
    exact = exact_fields(xyz,case['kind'],case['kappa'])
    traction = np.einsum('fqij,fj->fqi',exact['P'],normals)
    mass = measure[:,None]*weights
    nodal = np.zeros_like(data['coordinates'])
    local = np.einsum('qa,fqi,fq->fai',basis,traction,mass)
    free = tags != 1
    np.add.at(nodal,data['boundary_faces'][free].ravel(),local[free].reshape(-1,3))
    totals = [np.sum(traction[tags==tag]*mass[tags==tag,:,None],axis=(0,1)) for tag in range(1,7)]
    return nodal,np.asarray(totals),xyz,normals,mass


def assembled(data,state,case):
    F,J,gradients,detmap,bary,vertices = kinematics(data,state['u'],data['qpoints'])
    basis = tetra_shape(data['qpoints'])[0]; mass = detmap[:,None]*data['qweights']
    xyz = np.einsum('qa,cai->cqi',bary,vertices)
    pressure = np.einsum('qa,ca->cq',bary,state['pressure'][data['pressure_cells']])
    P = piola(F,pressure)
    exact = exact_fields(xyz,case['kind'],case['kappa'])
    nodal = np.einsum('cqij,cqaj,cq->cai',P,gradients,mass)
    nodal -= np.einsum('qa,cqi,cq->cai',basis,exact['body'],mass)
    force = np.zeros_like(state['u']); np.add.at(force,data['cells'].ravel(),nodal.reshape(-1,3))
    traction,totals,_,_,_ = surface_load(data,case)
    force -= traction
    weak = np.zeros_like(state['pressure'])
    np.add.at(weak,data['pressure_cells'].ravel(),np.einsum('qa,cq,cq->ca',bary,J-1-pressure/case['kappa'],mass).ravel())
    body_nodal = np.zeros_like(state['u'])
    np.add.at(body_nodal,data['cells'].ravel(),np.einsum('qa,cqi,cq->cai',basis,exact['body'],mass).reshape(-1,3))
    return {'force':force,'weak':weak,'F':F,'J':J,'P':P,'body':exact['body'],
            'external':body_nodal+traction,'face_exact':totals}


def numerical_face_forces(data,state,case):
    points,weights=quadrature(2)
    _,_,xyz,normals,mass = surface_load(data,case,points,weights)
    owners=data['boundary_owners']; cells=data['cells'][owners]
    vertices=data['coordinates'][cells[:,:4]]
    mapping=np.stack([vertices[:,i]-vertices[:,0] for i in [1,2,3]],axis=-1)
    inverse=np.linalg.inv(mapping)
    reference=np.einsum('fij,fqj->fqi',inverse,xyz-vertices[:,None,0])
    _,derivative,bary=tetra_shape(reference.reshape(-1,3))
    derivative=derivative.reshape(len(cells),-1,10,3); bary=bary.reshape(len(cells),-1,4)
    gradients=np.einsum('fqai,fij->fqaj',derivative,inverse)
    F=np.eye(3)+np.einsum('fai,fqaj->fqij',state['u'][cells],gradients)
    pressure=np.einsum('fqa,fa->fq',bary,state['pressure'][data['pressure_cells'][owners]])
    traction=np.einsum('fqij,fj->fqi',piola(F,pressure),normals)
    return np.array([np.sum(traction[data['boundary_tags']==tag]*mass[data['boundary_tags']==tag,:,None],axis=(0,1))
                     for tag in range(1,7)])


def error_metrics(data,state,case):
    points, weights = quadrature(3)
    basis,_,bary = tetra_shape(points)
    sums = {key:0. for key in ['u','u_ref','grad','grad_ref','p','p_ref','J','r','volume']}
    cell_jmax=[]; cell_rms=[]; maximum=0.; min_J=float('inf'); rmax=0.; gmax=0.
    for first in range(0,len(data['cells']),128):
        local = {**data,'cells':data['cells'][first:first+128],
                 'pressure_cells':data['pressure_cells'][first:first+128]}
        F,J,_,detmap,_,vertices = kinematics(local,state['u'],points)
        xyz = np.einsum('qa,cai->cqi',bary,vertices); mass = detmap[:,None]*weights
        reference = exact_fields(xyz,case['kind'],case['kappa'])
        u = np.einsum('qa,cai->cqi',basis,state['u'][local['cells']])
        pressure = np.einsum('qa,ca->cq',bary,state['pressure'][local['pressure_cells']])
        terms = {'u':np.sum((u-reference['u'])**2,axis=-1),'u_ref':np.sum(reference['u']**2,axis=-1),
            'grad':np.sum((F-reference['F'])**2,axis=(-1,-2)),
            'grad_ref':np.sum(reference['grad']**2,axis=(-1,-2)),
            'p':(pressure-reference['pressure'])**2,'p_ref':reference['pressure']**2,
            'J':(J-reference['J'])**2,'r':(J-1-pressure/case['kappa'])**2,'volume':np.ones_like(J)}
        for key, values in terms.items():
            sums[key] += float(np.sum(mass*values))
        _,extra_J,_,_,extra_bary,_ = kinematics(local,state['u'],extra_points())
        extra_xyz = np.einsum('qa,cai->cqi',extra_bary,vertices)
        extra_true = exact_fields(extra_xyz,case['kind'],case['kappa'])['J']
        extra_pressure=np.einsum('qa,ca->cq',extra_bary,state['pressure'][local['pressure_cells']])
        rmax=max(rmax,float(np.sqrt(terms['r']).max()),float(np.max(np.abs(extra_J-1-extra_pressure/case['kappa']))))
        gmax=max(gmax,float(np.max(np.abs(J-1))),float(np.max(np.abs(extra_J-1))))
        local_max = np.maximum(np.max(np.abs(J-reference['J']),axis=1),np.max(np.abs(extra_J-extra_true),axis=1))
        cell_jmax.extend(local_max); cell_rms.extend(np.sqrt(np.sum(mass*terms['r'],axis=1)/mass.sum(axis=1)))
        maximum=max(maximum,float(local_max.max())); min_J=min(min_J,float(J.min()),float(extra_J.min()))
    if not np.isfinite(min_J) or min_J<=0:
        raise ValueError('Nonpositive/nonfinite independently sampled J')
    result={'relative_u_L2':math.sqrt(sums['u']/sums['u_ref']),
        'relative_u_H1':math.sqrt(sums['grad']/sums['grad_ref']),
        'scaled_pressure_L2':math.sqrt(sums['p'])/max(1.,math.sqrt(sums['p_ref'])),
        'relative_pressure_L2':math.sqrt(sums['p']/sums['p_ref']) if sums['p_ref']>1e-28 else None,
        'J_error_RMS':math.sqrt(sums['J']/sums['volume']),'max_abs_J_error':maximum,
        'projection_defect_RMS':math.sqrt(sums['r']/sums['volume']), 'max_abs_projection_defect':rmax,
        'max_abs_J_minus_one':gmax,'minimum_sampled_J':min_J,
        'reference_volume':sums['volume'],'evaluation_points_per_cell':len(points)}
    return result,{'cell_max_abs_J_error':np.asarray(cell_jmax),'cell_projection_RMS':np.asarray(cell_rms)}


def audit(data,state,metadata,case,config):
    values=assembled(data,state,case)
    metrics,arrays=error_metrics(data,state,case)
    fixed=data['fixed'].astype(bool); reaction=np.where(fixed,values['force'],0.)
    position=data['coordinates']+state['u']
    balance=values['external']+reaction
    prescribed=exact_kinematics(data['coordinates'],case['kind'])[0]
    agreement=max(float(np.max(np.abs(values[key]-state[target]))) for key,target in
        [('force','force_residual'),('weak','weak_residual'),('P','P'),('body','body')])
    kinematics_error=max(float(np.max(np.abs(values[key]-state[key]))) for key in ['F','J'])
    checks={**mapping_checks(data),
        'mixed_map':bool(np.array_equal(state['u'].ravel(),state['mixed_state'][data['mixed_u_map']])
            and np.array_equal(state['pressure'],state['mixed_state'][data['mixed_p_map']])),
        'assembly_and_load_agreement':agreement<=2e-7,'kinematics_agreement':kinematics_error<=1e-10,
        'fixed_value':float(np.max(np.abs((state['u']-prescribed)[fixed])))<=1e-12,
        'snes':metadata['snes_reason']>0 and metadata['iterations']<=30,
        'solver_free_residual':metadata['free_residual_norm']<=1e-9,
        'independent_free_force':float(np.linalg.norm(values['force'][~fixed]))<=2e-6,
        'weak_pressure':float(np.linalg.norm(values['weak']))<=1e-8,
        'force_balance':float(np.linalg.norm(balance.sum(axis=0)))<=2e-6,
        'moment_balance':float(np.linalg.norm(np.cross(position,balance).sum(axis=0)))<=2e-6,
        'positive_J':metrics['minimum_sampled_J']>0,
        'linear_solver':metadata['linear_solver']['status']=='passed',
        'initial_zero':bool(np.all(state['initial_mixed']==0))}
    # Integrate actual (possibly nonconstant) numerical Piola on every patch face.
    face_errors=[]
    if case['kind'] not in {'mms','isochoric_mms'}:
        computed=numerical_face_forces(data,state,case)
        face_errors=np.linalg.norm(computed-values['face_exact'],axis=1).tolist()
        reaction_error=float(np.linalg.norm(reaction.sum(axis=0)-values['face_exact'][0]))
        metrics['face_force_scaled_error']=max(max(face_errors),reaction_error) # force scale mu L^2 = 1
        checks.update({key:metrics[key]<=limit for key,limit in config['patch_gates'].items()})
    hard_keys=['p2_order','p1_order','volume_weights','surface_weights','mixed_map',
               'assembly_and_load_agreement','kinematics_agreement','fixed_value','positive_J','initial_zero']
    hard=[key for key in hard_keys if not checks[key]]
    return {'status':'passed' if all(checks.values()) else 'failed','checks':checks,
        'failed_checks':[key for key,value in checks.items() if not value],'hard_failures':hard,
        'metrics':metrics,'force_agreement':agreement,'kinematics_error':kinematics_error,
        'reaction':reaction.sum(axis=0).tolist(),'exact_face_forces':values['face_exact'].tolist(),
        'patch_face_force_errors':face_errors,'force_balance':float(np.linalg.norm(balance.sum(axis=0))),
        'moment_balance':float(np.linalg.norm(np.cross(position,balance).sum(axis=0))),
        'pressure_weak_norm':float(np.linalg.norm(values['weak']))},arrays


def verify(root):
    """Read-only reconstruction of persisted states, iterates, and batch qualification."""
    import json
    from pathlib import Path
    from .ventricle_3d import load_arrays
    root=Path(root); config=json.loads((root/'configuration.json').read_text())
    summary=json.loads((root/'summary.json').read_text())
    reports={}; checks={}; maximum_metric_delta=0.
    for case in config['cases']:
        name=case['name']; state_path=root/'raw'/f'{name}_state.npz'
        if not state_path.exists():
            continue
        data=load_arrays(root/'raw'/f'{name}_mesh.npz'); state=load_arrays(state_path)
        meta=json.loads(state_path.with_suffix('.json').read_text())
        report,arrays=audit(data,state,meta,case,config); reports[name]=report
        saved=json.loads((root/'raw'/f'{name}_audit.json').read_text())
        checks[name+'_verdict']=report['status']==saved['status'] and report['checks']==saved['checks']
        for key,value in report['metrics'].items():
            if value is not None:
                maximum_metric_delta=max(maximum_metric_delta,abs(value-saved['metrics'][key]))
        derived=load_arrays(root/'raw'/f'{name}_derived.npz')
        checks[name+'_arrays']=all(np.allclose(value,derived[key],rtol=1e-10,atol=1e-12) for key,value in arrays.items())
        paths=sorted((root/'iterates'/name).glob('iterate_*.npz'))
        checks[name+'_iterate_count']=len(paths)==meta['iterations']+1
        checks[name+'_initial']=bool(np.all(load_arrays(root/'iterates'/name/'initial.npz')['mixed_state']==0))
        checks[name+'_final_iterate']=bool(paths and np.allclose(load_arrays(paths[-1])['mixed_state'],state['mixed_state'],rtol=0,atol=1e-12))
        for path in paths:
            iterate=load_arrays(path)
            _,J,_,_,_,_=kinematics(data,iterate['u'],extra_points())
            checks[name+'_'+path.stem]=bool(np.isfinite(J).all() and np.min(J)>0
                and np.array_equal(iterate['u'].ravel(),iterate['mixed_state'][data['mixed_u_map']])
                and np.array_equal(iterate['pressure'],iterate['mixed_state'][data['mixed_p_map']]))
    outcome=convergence(reports,config)
    checks['metrics_readback']=maximum_metric_delta<=1e-10
    checks['convergence_verdict']=outcome['status']==summary['convergence']['status']
    checks['no_unregistered_cases']=set(reports).issubset({case['name'] for case in config['cases']})
    checks['invocation_limit']=summary['attempted_solves']<=config['maximum_equilibrium_solves'] and summary['automatic_retries']==0
    return {'status':('not_run' if not reports else 'passed') if all(checks.values()) else 'failed','checks':checks,
        'qualification':outcome['status'],'cases':reports,'convergence':outcome,
        'evaluated_states':len(reports),'maximum_metric_delta':maximum_metric_delta,
        'scope':'readback integrity, not a replacement for scientific qualification'}


def convergence(cases,config):
    if config['schema']=='prl.mixed_cube_controls.v1':
        return control_convergence(cases,config)
    groups={}
    for kappa in [100,1000]:
        names=[f'mms_k{kappa}_n{n}' for n in [2,4,8]]
        present=[name for name in names if name in cases]
        if not present:
            groups[str(kappa)]={'status':'not_run','reason':'no evaluated MMS states'}
            continue
        if len(present)!=len(names):
            groups[str(kappa)]={'status':'blocked','reason':'incomplete MMS grid sequence'}
            continue
        if any(cases[name]['status']!='passed' for name in names):
            groups[str(kappa)]={'status':'failed','reason':'incomplete or nonqualified solver states'}
            continue
        metrics=[cases[name]['metrics'] for name in names]
        checks={}; orders={}
        for label,key in [('u_L2','relative_u_L2'),('u_H1','relative_u_H1'),('pressure_L2','relative_pressure_L2')]:
            errors=[item[key] for item in metrics]
            orders[label]=[math.log(errors[i]/errors[i+1],2) for i in range(2)]
            checks[label+'_decreases']=all(errors[i+1]<errors[i] for i in range(2))
            checks[label+'_order']=orders[label][-1]>=config['mms_gates']['EOC_'+label]
            checks[label+'_fine']=errors[-1]<=config['mms_gates']['fine_relative_'+label]
        checks['fine_J_error']=metrics[-1]['J_error_RMS']<=config['mms_gates']['fine_J_error_RMS']
        groups[str(kappa)]={'status':'passed' if all(checks.values()) else 'failed','checks':checks,'EOC':orders}
    statuses={group['status'] for group in groups.values()}
    status=('passed' if statuses=={'passed'} else 'not_run' if statuses=={'not_run'}
            else 'failed' if 'failed' in statuses else 'blocked')
    return {'status':status,'groups':groups,
        'does_not_qualify_original_ventricle':True,'inf_sup_or_locking_proof':False}


def control_convergence(cases,config):
    """Evaluate only the approved, defined control gates; zero-p relative error is unknown."""
    patch=cases.get('patch_quadratic_volume')
    patch_status=patch['status'] if patch else 'not_run'
    names=[f'isochoric_k1000_n{n}' for n in [2,4,8]]
    present=[name for name in names if name in cases]
    checks={}; orders={}
    if not present:
        shear_status='not_run'
    elif len(present)!=3:
        shear_status='blocked'
    elif any(cases[name]['status']!='passed' for name in names):
        shear_status='failed'
    else:
        metrics=[cases[name]['metrics'] for name in names]
        for label,key in [('u_L2','relative_u_L2'),('u_H1','relative_u_H1')]:
            errors=[item[key] for item in metrics]
            finite=all(math.isfinite(value) and value>0 for value in errors)
            orders[label]=[math.log(errors[i]/errors[i+1],2) for i in range(2)] if finite else [None,None]
            checks[label+'_decreases']=finite and all(errors[i+1]<errors[i] for i in range(2))
            checks[label+'_order']=finite and orders[label][-1]>=config['mms_gates']['EOC_'+label]
            checks[label+'_fine']=finite and errors[-1]<=config['mms_gates']['fine_relative_'+label]
        checks['fine_J_error']=metrics[-1]['J_error_RMS']<=config['mms_gates']['fine_J_error_RMS']
        checks['zero_pressure_relative_undefined']=all(item['relative_pressure_L2'] is None for item in metrics)
        shear_status='passed' if all(checks.values()) else 'failed'
    statuses={patch_status,shear_status}
    status=('passed' if statuses=={'passed'} else 'failed' if 'failed' in statuses
            else 'not_run' if statuses=={'not_run'} else 'blocked')
    return {'status':status,'groups':{'quadratic_volume':{'status':patch_status},
        'isochoric':{'status':shear_status,'checks':checks,'EOC':orders,
            'relative_pressure_qualification':'unknown','relative_pressure_error':None,
            'reason':'Exact p*=0; relative pressure norm and convergence order undefined'}},
        'scope':'only the defined four-control gates; no original benchmark qualification',
        'original_eight_case_qualification':'failed_unchanged',
        'does_not_qualify_original_ventricle':True,'inf_sup_or_locking_proof':False}
