"""Frozen eight-case specification; runtime authority is checked separately."""
from itertools import combinations

from .mixed_cube_spec import cube, guarded_configuration


def configuration():
    """A new object on each call; neither changes nor authorizes the old batches."""
    result = guarded_configuration()
    cases = [
        dict(name='patch_cubic_volume_p3p2', kind='cubic_volume', n=2,
             kappa=1000., u_degree=3, p_degree=2, role='prerequisite'),
        dict(name='mms_p2p1_q8_n8', kind='mms', n=8,
             kappa=100., u_degree=2, p_degree=1, role='quadrature_control'),
    ]
    for n in (2, 4, 8):
        for pressure_degree in (1, 2):
            cases.append(dict(name=f'mms_p3p{pressure_degree}_n{n}', kind='mms',
                              n=n, kappa=100., u_degree=3, p_degree=pressure_degree,
                              role='displacement_control' if pressure_degree == 1 else 'candidate'))
    result.update(schema='prl.mixed_cube_representation_proposal.v1',
                  authorization='pending_exact_eight_case_confirmation',
                  native_status='not_run', cases=cases, quadrature_degree=8,
                  maximum_equilibrium_solves=8,
                  candidate_orders=dict(u_L2=3.5, u_H1=2.5, pressure_L2=2.5),
                  scope='pending same-load representation comparison; no ventricular qualification')
    result['trial_guard']['sampling'] = (
        'production quadrature plus original 56 extra points plus candidate reference nodes')
    return result


def continuation_configuration():
    """Only the three unattempted cases after v02; no retry of its failed n4."""
    result = configuration()
    matrix = result['cases']
    names = ('mms_p3p2_n4', 'mms_p3p2_n8', 'mms_p3p1_n8')
    result['full_matrix_cases'] = matrix
    result['cases'] = [next(case for case in matrix if case['name'] == name) for name in names]
    result['maximum_equilibrium_solves'] = len(names)
    result['continuation_of'] = 'representation_v02'
    result['scope'] = 'unattempted registered cases only; aggregate qualification requires v02'
    return result


def topology_dof_inventory(n):
    """Count conforming P1/P2/P3 DOFs from actual tetra incidence, not solver output."""
    mesh = cube(n)
    tetrahedra = mesh['tetrahedra']
    edges = {tuple(sorted(int(t[i]) for i in local))
             for t in tetrahedra for local in combinations(range(4), 2)}
    faces = {tuple(sorted(int(t[i]) for i in local))
             for t in tetrahedra for local in combinations(range(4), 3)}
    vertices = len(mesh['xyz'])
    scalar = {1: vertices, 2: vertices + len(edges),
              3: vertices + 2 * len(edges) + len(faces)}
    return dict(n=n, tetrahedra=len(tetrahedra), vertices=vertices,
                edges=len(edges), faces=len(faces), scalar_dofs=scalar,
                mixed_dofs={f'p{u}p{p}': 3 * scalar[u] + scalar[p]
                            for u, p in ((2, 1), (3, 1), (3, 2))})
