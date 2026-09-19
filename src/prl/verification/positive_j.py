"""Independent path audit: direct determinants and stationary points, not Bernstein."""
import json
from pathlib import Path
import numpy as np
from .ventricle_3d import extra_points,load_arrays
from .mixed_cube_space import kinematics,sample_points


def path_minimum(base,increment):
    """Minimum over s in [0,1] for each sampled spatial gradient.

    Fit the exact cubic at four s values, then test both endpoints and all real
    interior derivative roots. No imports from production path admission.
    """
    if not np.isfinite(base).all() or not np.isfinite(increment).all():
        raise ValueError('Nonfinite path gradients')
    sample=np.array([0.,1/3,2/3,1.])
    values=np.stack([np.linalg.det(base+s*increment) for s in sample],axis=-1)
    vandermonde=np.vander(sample,4,increasing=True)
    coefficients=np.linalg.solve(vandermonde,values.reshape(-1,4).T).T.reshape(values.shape)
    c0,c1,c2,c3=np.moveaxis(coefficients,-1,0)
    minimum=np.minimum(values[...,0],values[...,-1])
    a=3*c3; b=2*c2; c=c1
    tolerance=64*np.finfo(float).eps*np.maximum(1.,np.max(np.abs(coefficients),axis=-1))
    quadratic=np.abs(a)>tolerance
    linear=(~quadratic)&(np.abs(b)>tolerance)
    discriminant=b*b-4*a*c
    real=quadratic&(discriminant>=0)
    root_term=-.5*(b+np.where(b>=0,1.,-1.)*np.sqrt(np.maximum(discriminant,0)))
    roots=[np.divide(-c,b,out=np.full_like(c,np.nan),where=linear),
        np.divide(root_term,a,out=np.full_like(c,np.nan),where=real),
        np.divide(c,root_term,out=np.full_like(c,np.nan),where=real&(np.abs(root_term)>tolerance))]
    for value in roots:
        inside=np.isfinite(value)&(value>0)&(value<1)
        safe=np.where(inside,value,0.)
        determinant=((c3*safe+c2)*safe+c1)*safe+c0
        minimum=np.minimum(minimum,np.where(inside,determinant,np.inf))
    residual=0.
    for value in [.1,.4,.9]:
        predicted=((c3*value+c2)*value+c1)*value+c0
        residual=max(residual,float(np.max(np.abs(predicted-np.linalg.det(base+value*increment)))))
    if residual>1e-9*max(1.,float(np.max(np.abs(values)))):
        raise ValueError('Independent cubic interpolation mismatch')
    return float(minimum.min()),residual


def audit_paths(root):
    root=Path(root); config=json.loads((root/'configuration.json').read_text())
    rows=[]; checks={}; accepted_checked=0
    for case in config['cases']:
        name=case['name']; folder=root/'iterates'/name
        if not (folder/'guard_history.json').exists():
            continue
        data=load_arrays(root/'raw'/f'{name}_mesh.npz')
        points=np.concatenate((data['qpoints'],sample_points(data)))
        for entry in json.loads((folder/'guard_history.json').read_text()):
            sequence=entry['sequence']; saved=load_arrays(folder/f'candidate_{sequence:03d}.npz')
            current=saved['current_mixed']; direction=saved['direction_mixed']; scale=entry['scale']
            u=current[data['mixed_u_map']].reshape(-1,3)
            step=direction[data['mixed_u_map']].reshape(-1,3)
            base=kinematics(data,u,points)[0]
            increment=kinematics(data,u-step,points)[0]-base
            minimum,fit_error=path_minimum(base,scale*increment)
            actual_current=float(np.linalg.det(base).min())
            actual_full=float(np.linalg.det(base+increment).min())
            prefix=f'{name}_{sequence}'
            checks[prefix+'_path']=minimum>0 and entry['path_lower_bound']<=minimum+1e-10
            checks[prefix+'_native_kinematics']=max(abs(actual_current-entry['current_minimum_J']),abs(actual_full-entry['full_step_minimum_J']))<=1e-9
            checks[prefix+'_scale']=scale==2.**(-entry['halvings']) and 0<=entry['halvings']<=config['trial_guard']['max_halvings']
            old=folder/f'iterate_{entry["newton_iteration"]:03d}.npz'
            checks[prefix+'_base_is_accepted']=old.exists() and np.allclose(load_arrays(old)['mixed_state'],current,rtol=0,atol=1e-11)
            accepted=folder/f'iterate_{entry["newton_iteration"]+1:03d}.npz'
            ratio=None; defect=None
            if accepted.exists():
                change=current-load_arrays(accepted)['mixed_state']
                square=float(direction@direction)
                ratio=float(change@direction/square) if square>0 else 0.
                defect=float(np.linalg.norm(change-ratio*direction)/max(1.,np.linalg.norm(change)))
                checks[prefix+'_accepted_in_segment']=defect<=1e-10 and -1e-12<=ratio<=scale+1e-10
                accepted_checked+=1
            rows.append({'case':name,'sequence':sequence,'newton_iteration':entry['newton_iteration'],
                'scale':scale,'halvings':entry['halvings'],'full_step_minimum_J':actual_full,
                'protected_path_minimum_J':minimum,'polynomial_check_error':fit_error,
                'accepted_scale':ratio,'direction_fit_error':defect})
    return {'status':('passed' if rows else 'not_run') if all(checks.values()) else 'failed',
        'checks':checks,'candidates':rows,'accepted_steps_checked':accepted_checked,
        'scope':'spatially sampled whole-path audit; no global injectivity or field-accuracy claim'}
