"""Saved-state volume projection diagnostics; no production forms or solves.

All integrals use reference-volume weights. Fixed physical bands are sampled
by quadrature indicators, not exact cut-cell integrals. Maxima remain sampled.
"""
import numpy as np


def weighted_summary(values, weights, mask=None):
    values = np.asarray(values, dtype=float)
    weights = np.asarray(weights, dtype=float)
    if values.shape != weights.shape or not np.isfinite(values).all():
        raise ValueError('Finite matching values and weights required')
    if not np.isfinite(weights).all() or np.any(weights <= 0):
        raise ValueError('Positive reference-volume weights required')
    if mask is None:
        mask = np.ones(values.shape, dtype=bool)
    mask = np.asarray(mask, dtype=bool)
    if mask.shape != values.shape:
        raise ValueError('Mask shape mismatch')
    if not mask.any():
        return {'samples': 0, 'reference_volume': 0., 'mean': None, 'rms': None, 'max_abs': None}
    selected, mass = values[mask], weights[mask]
    return {'samples': int(mask.sum()), 'reference_volume': float(mass.sum()),
            'mean': float(np.average(selected, weights=mass)),
            'rms': float(np.sqrt(np.average(selected**2, weights=mass))),
            'max_abs': float(np.max(np.abs(selected)))}


def distance_bands(coordinates, edges=(.15, .30, .45)):
    edges = np.asarray(edges, dtype=float)
    coordinates = np.asarray(coordinates)
    if (edges.shape != (3,) or not np.isfinite(edges).all() or edges[0] <= 0
            or not np.all(np.diff(edges) > 0)):
        raise ValueError('Three positive increasing fixed physical edges required')
    if coordinates.shape[-1] != 3 or not np.isfinite(coordinates).all():
        raise ValueError('Finite reference xyz required')
    distance = -coordinates[..., 2]
    if np.min(distance) < -1e-12:
        raise ValueError('This diagnostic is restricted to the retained z<=0 model')
    return np.searchsorted(edges, np.maximum(distance, 0.), side='right')


def analyze(mesh, state, config, mechanics, edges=(.15, .30, .45)):
    """Reuse only the independent kinematics, then calculate new diagnostics."""
    kappa = float(config['kappa'])
    if not np.isfinite(kappa) or kappa <= 0:
        raise ValueError('Finite positive kappa required')
    F, J, _, determinants, bary, vertices = mechanics.kinematics(mesh, state['u'], mesh['qpoints'])
    extra = mechanics.extra_points()
    _, extra_J, _, _, extra_bary, _ = mechanics.kinematics(mesh, state['u'], extra)
    if not np.isfinite(J).all() or not np.isfinite(extra_J).all() or min(J.min(), extra_J.min()) <= 0:
        raise ValueError('Nonpositive or nonfinite saved-state J')
    weights = determinants[:, None] * mesh['qweights']
    coefficients = np.asarray(state['pressure']).reshape(-1)[mesh['pressure_cells']]
    scaled = np.einsum('qa,ca->cq', bary, coefficients) / kappa
    extra_scaled = np.einsum('qa,ca->cq', extra_bary, coefficients) / kappa
    g, extra_g = J - 1, extra_J - 1
    defect, extra_defect = g - scaled, extra_g - extra_scaled
    positions = np.einsum('qa,cai->cqi', bary, vertices)
    extra_positions = np.einsum('qa,cai->cqi', extra_bary, vertices)
    bands = distance_bands(positions, edges)
    extra_bands = distance_bands(extra_positions, edges)
    # Force validation even for an empty region.
    global_defect = weighted_summary(defect, weights)
    all_layers = np.broadcast_to(mesh['layers'][:, None], J.shape)
    extra_layers = np.broadcast_to(mesh['layers'][:, None], extra_J.shape)
    regions = {}
    for layer in [None, 1, 2, 3]:
        tag = 'all' if layer is None else 'layer_' + str(layer)
        layer_mask = np.ones(J.shape, bool) if layer is None else all_layers == layer
        extra_layer = np.ones(extra_J.shape, bool) if layer is None else extra_layers == layer
        region_masks = {'global': (layer_mask, extra_layer),
            'distance_lt_0p30': (layer_mask & (bands < 2), extra_layer & (extra_bands < 2)),
            'distance_ge_0p30': (layer_mask & (bands >= 2), extra_layer & (extra_bands >= 2))}
        region_masks.update({'band_' + str(i): (layer_mask & (bands == i), extra_layer & (extra_bands == i)) for i in range(4)})
        for name, (mask, extra_mask) in region_masks.items():
            item = {'J_minus_one': weighted_summary(g, weights, mask),
                    'p_over_kappa': weighted_summary(scaled, weights, mask),
                    'projection_defect': weighted_summary(defect, weights, mask)}
            for key, qvalues, evalues in [('max_abs_J_minus_one', g, extra_g),
                                          ('max_abs_projection_defect', defect, extra_defect),
                                          ('max_abs_p_over_kappa', scaled, extra_scaled)]:
                samples = np.concatenate([qvalues[mask], evalues[extra_mask]])
                item[key] = float(np.max(np.abs(samples))) if len(samples) else None
            regions[tag + '/' + name] = item
    combined_g = np.concatenate([g, extra_g], axis=1)
    combined_r = np.concatenate([defect, extra_defect], axis=1)
    combined_positions = np.concatenate([positions, extra_positions], axis=1)
    combined_scaled = np.concatenate([scaled, extra_scaled], axis=1)
    cell_peak = np.argmax(np.abs(combined_g), axis=1)
    cell_indices = np.arange(len(vertices))
    maximum = np.max(np.abs(combined_g), axis=1)
    peak_cell = int(np.argmax(maximum))
    peak_point = int(cell_peak[peak_cell])
    mass = weights.sum(axis=1)
    bad = maximum > .01
    pressure_moments = np.zeros(len(mesh['pressure_coordinates']))
    local_moments = np.einsum('qa,cq,cq->ca', bary, defect, weights)
    np.add.at(pressure_moments, mesh['pressure_cells'].ravel(), local_moments.ravel())
    full_energy = float(kappa / 2 * np.sum(weights * g**2))
    projected_energy = float(kappa / 2 * np.sum(weights * scaled**2))
    defect_energy = float(kappa / 2 * np.sum(weights * defect**2))
    cross = float(np.sum(weights * scaled * defect))
    report = {'status': 'passed', 'meaning': 'diagnostic computation only; original scientific failure unchanged',
        'tetrahedra': len(vertices), 'fixed_distance_edges': list(edges),
        'region_volume_method': 'reference quadrature indicator, not exact cut-cell volume',
        'quadrature_points_per_cell': len(bary), 'extra_points_per_cell': len(extra_bary),
        'solid_reference_volume': float(mass.sum()), 'regions': regions,
        'max_abs_J_minus_one': float(maximum.max()),
        'max_abs_p_over_kappa_at_q_and_extra': float(np.max(np.abs(combined_scaled))),
        'rms_projection_defect': global_defect['rms'],
        'max_abs_projection_defect': float(np.max(np.abs(combined_r))),
        'rms_J_minus_one': weighted_summary(g, weights)['rms'],
        'rms_p_over_kappa': weighted_summary(scaled, weights)['rms'],
        'bad_cells': int(bad.sum()), 'fraction_solid_volume_in_bad_cells': float(mass[bad].sum()/mass.sum()),
        'bad_volume_caution': 'whole cells containing an above-1% sample, not exact violating-region volume',
        'pressure_weak_moment_norm': float(np.linalg.norm(pressure_moments)),
        'projection_cross_term': cross, 'pointwise_penalty_energy': full_energy,
        'projected_volumetric_energy': projected_energy, 'projection_defect_penalty': defect_energy,
        'orthogonal_split_error': full_energy-projected_energy-defect_energy,
        'exact_split_identity_error': full_energy-projected_energy-defect_energy-kappa*cross,
        'peak': {'cell': peak_cell, 'layer': int(mesh['layers'][peak_cell]),
            'sample_kind': 'quadrature' if peak_point < len(bary) else 'extra',
            'reference_point': combined_positions[peak_cell, peak_point].tolist(),
            'J_minus_one': float(combined_g[peak_cell, peak_point]),
            'p_over_kappa': float(combined_scaled[peak_cell, peak_point])},
        'scientific_pressure_gate': 'failed' if bad.any() else 'unknown',
        'instability_or_locking_cause': 'unknown', 'new_FEM_solves': 0}
    arrays = {'cell_peak_distance': -combined_positions[cell_indices, cell_peak, 2],
        'cell_max_abs_J_minus_one': maximum, 'cell_max_abs_projection_defect': np.max(np.abs(combined_r), axis=1),
        'cell_rms_projection_defect': np.sqrt(np.sum(weights * defect**2, axis=1)/mass),
        'cell_reference_volume': mass, 'layers': mesh['layers'],
        'coordinates': mesh['coordinates'], 'cells': mesh['cells']}
    return report, arrays
