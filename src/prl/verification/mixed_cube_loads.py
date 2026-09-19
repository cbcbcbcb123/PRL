"""Saved-state load diagnostics, not an equilibrium solver or inf-sup proof."""
import numpy as np
from scipy.sparse import coo_matrix
from scipy.sparse.linalg import spsolve

from .mixed_cube import exact_fields, piola, quadrature, surface_load
from .ventricle_3d import kinematics, tetra_shape


def _scatter_vector(target, cells, local):
    np.add.at(target, cells.ravel(), local.reshape(-1, 3))


def integrate(data, state, case, order=None, *, coupling=False, chunk_size=64):
    """Reconstruct forces in bounded chunks; optional B* uses exact F*, not Fh."""
    if chunk_size < 1:
        raise ValueError('Positive chunk size required')
    points, weights = ((data['qpoints'], data['qweights']) if order is None
                       else quadrature(3, order))
    facet_points, facet_weights = ((data['facet_qpoints'], data['facet_qweights']) if order is None
                                  else quadrature(2, order))
    basis, _, bary = tetra_shape(points)
    vectors = {key: np.zeros_like(state['u']) for key in
               ['internal', 'body', 'exact_iso', 'exact_pressure']}
    weak = np.zeros_like(state['pressure'])
    row_blocks, column_blocks, value_blocks = [], [], []
    minimum_J = float('inf')
    for first in range(0, len(data['cells']), chunk_size):
        cells = data['cells'][first:first + chunk_size]
        pcells = data['pressure_cells'][first:first + chunk_size]
        local_data = {**data, 'cells': cells, 'pressure_cells': pcells}
        F, J, gradients, detmap, _, vertices = kinematics(local_data, state['u'], points)
        minimum_J = min(minimum_J, float(J.min()))
        mass = detmap[:, None] * weights
        xyz = np.einsum('qa,cai->cqi', bary, vertices)
        exact = exact_fields(xyz, case['kind'], case['kappa'])
        pressure = np.einsum('qa,ca->cq', bary, state['pressure'][pcells])
        material = piola(F, pressure)
        cofactor = exact['J'][..., None, None] * np.linalg.inv(exact['F']).swapaxes(-1, -2)
        pressure_P = exact['pressure'][..., None, None] * cofactor
        for key, tensor in [('internal', material), ('exact_iso', exact['P'] - pressure_P),
                            ('exact_pressure', pressure_P)]:
            _scatter_vector(vectors[key], cells,
                            np.einsum('cqij,cqaj,cq->cai', tensor, gradients, mass))
        _scatter_vector(vectors['body'], cells,
                        np.einsum('qa,cqi,cq->cai', basis, exact['body'], mass))
        np.add.at(weak, pcells.ravel(),
                  np.einsum('qa,cq,cq->ca', bary, J - 1 - pressure / case['kappa'], mass).ravel())
        if coupling:
            local_B = np.einsum('qb,cqij,cqaj,cq->cbai', bary, cofactor, gradients, mass)
            columns = 3 * cells[:, :, None] + np.arange(3)
            row_blocks.append(np.broadcast_to(pcells[:, :, None, None], local_B.shape).ravel())
            column_blocks.append(np.broadcast_to(columns[:, None, :, :], local_B.shape).ravel())
            value_blocks.append(local_B.ravel())
    traction, _, _, _, _ = surface_load(data, case, facet_points, facet_weights)
    vectors['external'] = vectors['body'] + traction
    vectors['force'] = vectors['internal'] - vectors['external']
    vectors['weak'] = weak
    vectors['minimum_J'] = minimum_J
    if coupling:
        vectors['B'] = coo_matrix((np.concatenate(value_blocks),
                                  (np.concatenate(row_blocks), np.concatenate(column_blocks))),
                                 shape=(len(state['pressure']), state['u'].size)).tocsr()
    return vectors


def pressure_certificate(matrix, force, fixed):
    """Euclidean nodal-force least squares; no stiffness or mechanical solve."""
    fixed = np.asarray(fixed, dtype=bool).ravel()
    free = ~fixed
    operator = matrix[:, free]
    load = np.asarray(force).ravel()[free]
    gram = (operator @ operator.T).tocsc()
    coefficients = spsolve(gram, operator @ load)
    representable = operator.T @ coefficients
    leakage = load - representable
    load_norm = float(np.linalg.norm(load))
    leakage_norm = float(np.linalg.norm(leakage))
    normal_residual = float(np.linalg.norm(operator @ leakage))
    operator_norm = float(np.linalg.norm(operator.data))
    normal_scaled = normal_residual / max(operator_norm * load_norm, 1e-30)
    work_identity_error = abs(float(load @ leakage) - leakage_norm ** 2)
    if (not np.isfinite(coefficients).all() or normal_scaled > 1e-10
            or work_identity_error > 1e-10 * max(load_norm ** 2, 1e-30)):
        raise ValueError('Pressure projection certificate failed')
    full_leakage = np.zeros_like(fixed, dtype=float)
    full_leakage[free] = leakage
    return {'pressure_force_norm': load_norm, 'unrepresented_force_norm': leakage_norm,
            'unrepresented_fraction': leakage_norm / max(load_norm, 1e-30),
            'normal_equation_scaled_residual': normal_scaled,
            'pressure_virtual_work': float(load @ leakage),
            'work_identity_absolute_error': work_identity_error,
            'scope': 'Euclidean nodal-force projection at exact F*, not equilibrium, L2 pressure projection or inf-sup'}, {
            'least_squares_pressure_coefficients': coefficients,
            'unrepresented_pressure_force': full_leakage.reshape(force.shape)}


def diagnose(data, state, case):
    """Two higher evaluation rules compare the same immutable saved equilibrium."""
    fixed = data['fixed'].astype(bool)
    norm = lambda values: float(np.linalg.norm(values[~fixed]))
    production = integrate(data, state, case)
    high6 = integrate(data, state, case, 6)
    high8 = integrate(data, state, case, 8, coupling=True)
    certificate, arrays = pressure_certificate(high8['B'], high8['exact_pressure'], fixed)
    external_norm = norm(high8['external'])
    exact_force = high8['exact_iso'] + high8['exact_pressure']
    consistency = norm(exact_force - high8['external'])
    source_delta = norm(production['force'] - state['force_residual'])
    if source_delta > 2e-7 or consistency > 1e-8:
        raise ValueError('Saved force agreement or exact virtual-work consistency failed')
    report = {
        'name': case['name'], 'n': case['n'], 'kappa': case['kappa'],
        'tetrahedra': len(data['cells']),
        'production_free_force_norm': norm(production['force']),
        'high6_free_force_norm': norm(high6['force']),
        'high8_free_force_norm': norm(high8['force']),
        'production_load_difference': norm(production['external'] - high8['external']),
        'production_relative_load_difference': norm(production['external'] - high8['external']) / external_norm,
        'high6_high8_load_difference': norm(high6['external'] - high8['external']),
        'high6_high8_internal_difference': norm(high6['internal'] - high8['internal']),
        'production_internal_difference': norm(production['internal'] - high8['internal']),
        'exact_virtual_work_consistency_norm': consistency,
        'saved_force_agreement_norm': source_delta,
        'exact_iso_force_norm': norm(high8['exact_iso']),
        'minimum_evaluation_J': high8['minimum_J'],
        'pressure_certificate': certificate,
        'leakage_to_iso_force_norm_ratio': certificate['unrepresented_force_norm'] / norm(high8['exact_iso']),
        'quadrature_load_to_leakage_ratio': norm(production['external'] - high8['external']) / max(certificate['unrepresented_force_norm'], 1e-30),
        'scope': 'saved-state analysis; no new equilibrium and no changed scientific gates'}
    arrays.update(exact_iso_force=high8['exact_iso'], exact_pressure_force=high8['exact_pressure'],
                  production_load_error=production['external'] - high8['external'])
    return report, arrays
