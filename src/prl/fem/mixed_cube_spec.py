"""User-approved eight-case matrix; no imports from its independent verifier."""
from itertools import permutations
import numpy as np
from prl.fem.ventricle_geometry import configuration as ventricular_configuration


def configuration():
    cases = [{'name': 'patch_affine', 'kind': 'affine', 'n': 2, 'kappa': 1000.},
             {'name': 'patch_shear', 'kind': 'shear', 'n': 2, 'kappa': 1000.}]
    cases += [{'name': f'mms_k{int(kappa)}_n{n}', 'kind': 'mms', 'n': n, 'kappa': kappa}
              for kappa in [100., 1000.] for n in [2, 4, 8]]
    return {'schema': 'prl.mixed_cube_benchmark.v1', 'mu': 1., 'cases': cases,
        'solver': ventricular_configuration()['solver'], 'quadrature_degree': 6,
        'independent_quadrature': 'six-point-per-axis Gauss-Duffy; total polynomial degree >= 8',
        'maximum_equilibrium_solves': 8, 'diagnostic_trace': True,
        'resources': {'seconds': 1800, 'stop_reserve_seconds': 120, 'threads': 1, 'gpu': 0, 'automatic_retries': 0},
        'patch_gates': {'relative_u_L2': 1e-8, 'relative_u_H1': 1e-8,
            'scaled_pressure_L2': 1e-7, 'max_abs_J_error': 1e-9, 'face_force_scaled_error': 1e-7},
        'mms_gates': {'EOC_u_L2': 2.5, 'EOC_u_H1': 1.5, 'EOC_pressure_L2': 1.5,
            'fine_relative_u_L2': .02, 'fine_relative_u_H1': .15, 'fine_relative_pressure_L2': .15,
            'fine_J_error_RMS': .001},
        'scope': 'verification cube, not ventricular load, inf-sup proof, biology, growth or FSI'}


def guarded_configuration():
    result=configuration()
    result['trial_guard']={'method':'sampled_path_bernstein_cubic','floor':1e-12,'max_halvings':20,
        'sampling':'original production quadrature plus original 56 extra points',
        'scope':'trial admission only; accepted-state safety and accuracy gates unchanged'}
    return result


def control_configuration():
    """Four separately authorized controls; never replaces the original MMS gates."""
    result=guarded_configuration()
    result.update(schema='prl.mixed_cube_controls.v1',maximum_equilibrium_solves=4,
        cases=[{'name':'patch_quadratic_volume','kind':'quadratic_volume','n':2,'kappa':1000.}]
            +[{'name':f'isochoric_k1000_n{n}','kind':'isochoric_mms','n':n,'kappa':1000.} for n in [2,4,8]],
        pressure_relative_gate='unknown: exact pressure is zero in isochoric controls',
        scope='four diagnostic controls only; original eight-case and ventricular failures unchanged')
    return result


def cube(n):
    """Six Freudenthal tetrahedra per voxel, identical unit-cube boundary for all n."""
    if n not in [2, 4, 8, 12]:
        raise ValueError('Only registered mesh levels are implemented; runtime authority is separate')
    xyz = np.array([[i,j,k] for i in range(n+1) for j in range(n+1) for k in range(n+1)], float)/n
    def node(index):
        i,j,k = index
        return i*(n+1)**2+j*(n+1)+k
    cells = []
    for i in range(n):
        for j in range(n):
            for k in range(n):
                for order in permutations(range(3)):
                    point = np.array([i,j,k]); ids = [node(point)]
                    for axis in order:
                        point = point.copy(); point[axis] += 1; ids.append(node(point))
                    cells.append(ids)
    cells = np.asarray(cells, np.int64)
    vertices = xyz[cells]
    sign = np.linalg.det(np.stack([vertices[:,i]-vertices[:,0] for i in [1,2,3]], axis=-1))
    reverse = sign < 0
    cells[reverse,1], cells[reverse,2] = cells[reverse,2].copy(), cells[reverse,1].copy()
    return {'xyz': xyz, 'tetrahedra': cells}


def disposition(kind, audit):
    """Precision/nonconvergence failures may continue only in the independent MMS set."""
    if audit['hard_failures']:
        return 'stop_batch'
    if kind not in {'mms','isochoric_mms'} and audit['status'] != 'passed':
        return 'stop_batch'
    return 'continue_registered_cases'
