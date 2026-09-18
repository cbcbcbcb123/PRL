"""Permutation-invariant tetrahedron shape measures, separate from mechanics."""
from itertools import combinations
import numpy as np
from scipy.stats import rankdata


def tetra_quality(vertices):
    """Reference vertices (cell, 4, 3); orientation is not shape quality.

    q_radius = 3 r_in / R_circum, q_mean = 12 (3V)^(2/3) / sum(edge^2).
    Both equal one for an equilateral tetrahedron. Dihedrals are internal.
    condition_regular measures the affine map FROM an equilateral tetrahedron;
    it is not the condition number of the assembled mixed FEM matrix.
    """
    vertices = np.asarray(vertices, dtype=float)
    if vertices.ndim != 3 or vertices.shape[1:] != (4, 3) or not np.isfinite(vertices).all():
        raise ValueError('Finite (cell,4,3) vertices required')
    edge_vectors = np.stack([vertices[:, j]-vertices[:, i] for i, j in combinations(range(4), 2)], axis=1)
    edges = np.linalg.norm(edge_vectors, axis=-1)
    mapping = (vertices[:, 1:]-vertices[:, :1]).swapaxes(-1, -2)
    volume = np.abs(np.linalg.det(mapping))/6
    if np.any(volume <= 0) or np.any(edges <= 0):
        raise ValueError('Degenerate tetrahedron')
    normals = []
    areas = []
    for opposite in range(4):
        face = vertices[:, [i for i in range(4) if i != opposite]]
        normal = np.cross(face[:, 1]-face[:, 0], face[:, 2]-face[:, 0])
        length = np.linalg.norm(normal, axis=-1)
        outward = np.einsum('ci,ci->c', normal, vertices[:, opposite]-face[:, 0]) < 0
        normals.append(normal / length[:, None] * np.where(outward, 1., -1.)[:, None])
        areas.append(length/2)
    normals = np.stack(normals, axis=1)
    areas = np.stack(areas, axis=1)
    cosines = np.stack([-np.sum(normals[:, i]*normals[:, j], axis=-1)
                        for i, j in combinations(range(4), 2)], axis=1)
    angles = np.rad2deg(np.arccos(np.clip(cosines, -1, 1)))
    relative = vertices[:, 1:]-vertices[:, :1]
    circumcenter = np.linalg.solve(relative, (.5*np.sum(relative**2, axis=-1))[..., None])[..., 0]
    circumradius = np.linalg.norm(circumcenter, axis=-1)
    inradius = 3*volume/areas.sum(axis=1)
    regular = np.array([[1., .5, .5], [0., np.sqrt(3)/2, np.sqrt(3)/6], [0., 0., np.sqrt(2/3)]])
    normalized = mapping @ np.linalg.inv(regular)
    return {'volume': volume, 'q_radius': 3*inradius/circumradius,
            'q_mean': 12*np.power(3*volume, 2/3)/np.sum(edges**2, axis=1),
            'min_dihedral_deg': angles.min(axis=1), 'max_dihedral_deg': angles.max(axis=1),
            'edge_ratio': edges.max(axis=1)/edges.min(axis=1),
            'max_edge_over_min_height': edges.max(axis=1)*areas.max(axis=1)/(3*volume),
            'condition_regular': np.linalg.cond(normalized), 'centroid': vertices.mean(axis=1)}


def distribution(values):
    values = np.asarray(values)
    if not len(values):
        return None
    return dict(zip(['min', 'p05', 'median', 'p95', 'max'], map(float, np.quantile(values, [0, .05, .5, .95, 1]))))


def descriptive_spearman(x, y):
    """No p value: FE cells are spatially dependent, not biological replicates."""
    if len(x) < 3:
        return None
    # Treat numerical roundoff of symmetry-equivalent cells as ties.
    a, b = [rankdata(np.round(values, 12)) for values in [x, y]]
    if np.ptp(a) == 0 or np.ptp(b) == 0:
        return None
    return float(np.corrcoef(a, b)[0, 1])


def regional_summary(data):
    count = len(data['q_radius'])
    bad = data['max_abs_J_minus_one'] > .01
    flagged = (data['q_radius'] < .2) | (data['min_dihedral_deg'] < 10.)
    selectors = {'all': np.ones(count, dtype=bool), 'clamp_adjacent': data['clamp_adjacent'],
                 'away_from_clamp': ~data['clamp_adjacent']}
    for layer in [1, 2, 3]:
        selectors['layer_'+str(layer)] = data['layers'] == layer
        for near, mask in [('clamp', data['clamp_adjacent']), ('away', ~data['clamp_adjacent'])]:
            selectors[f'layer_{layer}_{near}'] = (data['layers'] == layer) & mask
    result = {}
    metrics = ['q_radius', 'q_mean', 'min_dihedral_deg', 'max_dihedral_deg', 'edge_ratio',
               'max_edge_over_min_height', 'condition_regular', 'max_abs_J_minus_one']
    for name, mask in selectors.items():
        result[name] = {'cells': int(mask.sum()), 'volume_gate_failed_cells': int(np.sum(bad & mask)),
            'shape_screen_flagged_cells': int(np.sum(flagged & mask)),
            'shape_flagged_and_volume_failed': int(np.sum(flagged & bad & mask)),
            'reference_volume_fraction': float(data['volume'][mask].sum()/data['volume'].sum()),
            'distributions': {key: distribution(data[key][mask]) for key in metrics},
            'q_radius_vs_J_spearman_descriptive': descriptive_spearman(data['q_radius'][mask], data['max_abs_J_minus_one'][mask]),
            'volume_failed_q_radius': distribution(data['q_radius'][mask & bad]),
            'volume_passed_q_radius': distribution(data['q_radius'][mask & ~bad])}
    return result


def analyze(mesh, state, config, mechanics=None, probe=None):
    if mechanics is None:
        from prl.verification import ventricle_3d as mechanics
    if probe is None:
        from prl.verification import ventricle_mesh_probe as probe
    vertices = mesh['coordinates'][mesh['cells'][:, :4]]
    quality = tetra_quality(vertices)
    mechanical = probe.cell_measures(mesh, state, config, mechanics)
    if not np.allclose(quality['volume'], mechanical['cell_volume'], rtol=1e-12, atol=1e-15):
        raise ValueError('Geometry/mechanics cell indexing or volume mismatch')
    data = {**quality, **mechanical, 'layers': mesh['layers']}
    top = np.argsort(data['max_abs_J_minus_one'])[-12:][::-1]
    return data, {'cells': len(vertices), 'regions': regional_summary(data),
        'worst_volume_cells': [{'cell': int(i), 'layer': int(data['layers'][i]),
            'centroid': data['centroid'][i].tolist(), 'q_radius': float(data['q_radius'][i]),
            'min_dihedral_deg': float(data['min_dihedral_deg'][i]),
            'clamp_adjacent': bool(data['clamp_adjacent'][i]),
            'max_abs_J_minus_one': float(data['max_abs_J_minus_one'][i])} for i in top]}
