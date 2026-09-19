"""Conservative sampled positive-J path admission; no constitutive/verifier imports."""
from itertools import combinations
import numpy as np


def determinant_coefficients(base,increment):
    """Power coefficients of det(base + t*increment), by column multilinearity."""
    base=np.asarray(base,dtype=float); increment=np.asarray(increment,dtype=float)
    if base.shape!=increment.shape or base.shape[-2:]!=(3,3):
        raise ValueError('Matching 3x3 deformation gradients required')
    if not np.isfinite(base).all() or not np.isfinite(increment).all():
        raise ValueError('Nonfinite current gradient or trial direction')
    coefficients=np.zeros(base.shape[:-2]+(4,))
    for degree in range(4):
        for columns in combinations(range(3),degree):
            matrix=base.copy()
            matrix[...,list(columns)]=increment[...,list(columns)]
            coefficients[...,degree]+=np.linalg.det(matrix)
    return coefficients


def admissible_scale(base,increment,*,floor=1e-12,max_halvings=20):
    """Certify every t in [0,scale] at each supplied spatial sample.

    Positive Bernstein coefficients suffice, but are not necessary. They do not
    certify unsampled spatial locations or global injectivity of the mesh.
    """
    if not np.isfinite(floor) or floor<0 or max_halvings<0 or int(max_halvings)!=max_halvings:
        raise ValueError('Invalid path-admission settings')
    coefficients=determinant_coefficients(base,increment)
    if not np.isfinite(coefficients).all():
        raise ValueError('Nonfinite determinant polynomial')
    c0,c1,c2,c3=np.moveaxis(coefficients,-1,0)
    if np.min(c0)<=floor:
        raise ValueError('Invalid current sampled deformation; no candidate is admissible')
    trials=[]
    for halvings in range(max_halvings+1):
        scale=2.**(-halvings)
        endpoint=c0+scale*c1+scale**2*c2+scale**3*c3
        bounds=np.stack((c0,c0+scale*c1/3,c0+2*scale*c1/3+scale**2*c2/3,endpoint))
        lower=float(bounds.min())
        trials.append({'scale':scale,'bernstein_lower_bound':lower,'endpoint_minimum_J':float(endpoint.min())})
        if np.isfinite(bounds).all() and lower>floor:
            return {'status':'passed','scale':scale,'halvings':halvings,'floor':floor,
                'current_minimum_J':float(c0.min()),'path_lower_bound':lower,
                'full_step_minimum_J':trials[0]['endpoint_minimum_J'],'trials':trials}
    raise ValueError('No admissible positive-J segment within halving limit')
