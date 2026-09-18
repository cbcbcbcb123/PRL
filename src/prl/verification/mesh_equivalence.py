"""Independent volume-mesh identity and pre-FEM shape gates; no mesher imports."""
from collections import defaultdict
from itertools import combinations
import numpy as np
from prl.verification.tetra_quality import tetra_quality, distribution


def topology(data):
    xyz = np.asarray(data['xyz']); cells = np.asarray(data['tetrahedra'])
    layers = np.asarray(data['layers'])
    if (xyz.ndim != 2 or xyz.shape[1] != 3 or cells.ndim != 2 or cells.shape[1] != 4
            or len(layers) != len(cells) or not len(cells) or not np.isfinite(xyz).all()
            or cells.min() < 0 or cells.max() >= len(xyz)):
        raise ValueError('Malformed finite tetrahedral geometry')
    quality = tetra_quality(xyz[cells])
    signed = np.linalg.det((xyz[cells[:, 1:]]-xyz[cells[:, :1]]).swapaxes(1, 2))/6
    faces = defaultdict(list)
    for index, cell in enumerate(cells):
        for opposite in range(4):
            face = tuple(sorted(np.delete(cell, opposite)))
            faces[face].append((index, int(cell[opposite])))
    inner = {tuple(sorted(f)) for f in data['inner_faces']}
    outer = {tuple(sorted(f)) for f in data['outer_faces']}
    surfaces = {}; side_checks = []; adjacency = []
    for face, owners in faces.items():
        points = xyz[list(face)]
        pair = tuple(sorted(int(layers[c]) for c, _ in owners))
        if len(owners) == 2:
            normal = np.cross(points[1]-points[0], points[2]-points[0])
            signs = [float(normal @ (xyz[o]-points[0])) for _, o in owners]
            side_checks.append(signs[0]*signs[1] < 0)
        if len(owners) == 1 or len(set(pair)) > 1:
            key = tuple(sorted(tuple(float(v) for v in p) for p in points))
            surfaces[key] = pair
            adjacency.append(pair)
    exterior = {face for face, owners in faces.items() if len(owners) == 1}
    base = {face for face in exterior if np.all(np.abs(xyz[list(face), 2]) < 1e-12)}
    vectors = xyz[data['inner_faces']]
    cavity = float(np.einsum('fi,fi->', vectors[:, 0], np.cross(vectors[:, 1], vectors[:, 2]))/6)
    edges = {tuple(sorted(e)) for c in cells for e in combinations(c, 2)}
    checks = {
        'positive_volume': bool(np.all(signed > 0)),
        'no_duplicate_cells': len({tuple(sorted(c)) for c in cells}) == len(cells),
        'no_duplicate_coordinates': len({tuple(p) for p in xyz}) == len(xyz),
        'no_unused_vertices': len(np.unique(cells)) == len(xyz),
        'manifold_faces': all(len(v) in [1, 2] for v in faces.values()),
        'opposite_sides_shared_faces': all(side_checks),
        'all_boundary_facets_identified': exterior == inner | outer | base,
        'boundary_labels_disjoint': not (inner & outer or inner & base or outer & base),
        'surface_labels_unique': len(inner) == len(data['inner_faces']) and len(outer) == len(data['outer_faces']),
        'layer_labels': set(layers) == {1, 2, 3},
        'allowed_layer_adjacency': set(adjacency) == {(1,), (3,), (2,), (1, 2), (2, 3)},
        'positive_cavity': cavity > 0,
    }
    near = np.any(np.abs(xyz[cells, 2]) < 1e-12, axis=1)
    masks = {'all': np.ones(len(cells), dtype=bool), 'clamp': near, 'away': ~near,
             'thin_clamp': near & (layers <= 2)}
    for layer in [1, 2, 3]:
        masks['layer_'+str(layer)] = layers == layer
        masks[f'layer_{layer}_clamp'] = (layers == layer) & near
        masks[f'layer_{layer}_away'] = (layers == layer) & ~near
    regions = {name: {'cells': int(mask.sum()),
        **{key: distribution(quality[key][mask]) for key in ['q_radius', 'min_dihedral_deg', 'condition_regular']}}
        for name, mask in masks.items()}
    summary = {'checks': checks, 'vertices': len(xyz), 'tetrahedra': len(cells),
        'edges': len(edges), 'mixed_dofs': 4*len(xyz)+3*len(edges), 'regions': regions,
        'cavity_volume': cavity, 'layer_volumes': {str(k): float(signed[layers == k].sum()) for k in [1, 2, 3]},
        'surface_triangles': len(surfaces)}
    return summary, surfaces, {**quality, 'layers': layers, 'clamp_adjacent': near}


def compare(reference, candidate):
    original, expected, original_arrays = topology(reference)
    actual, obtained, actual_arrays = topology(candidate)
    checks = {'original_topology': all(original['checks'].values()),
              'candidate_topology': all(actual['checks'].values()),
              'identical_surface_coordinates_and_adjacency': expected == obtained,
              'tetrahedra_budget': actual['tetrahedra'] <= 7920,
              'mixed_dof_budget': actual['mixed_dofs'] <= 38238}
    differences = {'cavity': abs(actual['cavity_volume']/original['cavity_volume']-1)}
    for key in ['1', '2', '3']:
        differences['layer_'+key] = abs(actual['layer_volumes'][key]/original['layer_volumes'][key]-1)
    checks['same_volumes'] = all(value <= 1e-10 for value in differences.values())
    before, after = original['regions'], actual['regions']
    checks['global_q05_improves_5percent'] = after['all']['q_radius']['p05'] >= 1.05*before['all']['q_radius']['p05']-1e-12
    for region in ['thin_clamp', 'layer_1_clamp', 'layer_2_clamp']:
        checks[region+'_q05_not_worse'] = (after[region]['cells'] > 0 and
            after[region]['q_radius']['p05'] >= before[region]['q_radius']['p05']-1e-12)
    for region in ['all', 'thin_clamp', 'layer_1_clamp', 'layer_2_clamp']:
        checks[region+'_minimum_dihedral_not_worse'] = (after[region]['cells'] > 0 and
            after[region]['min_dihedral_deg']['min'] >= before[region]['min_dihedral_deg']['min']-1e-12)
    report = {'status': 'passed' if all(checks.values()) else 'failed', 'checks': checks,
              'failed_checks': [k for k, v in checks.items() if not v], 'reference': original,
              'candidate': actual, 'relative_volume_differences': differences,
              'scientific_pressure_gate': 'not_run', 'universal_FEM_quality_claim': False}
    arrays = {prefix+'_'+key: value for prefix, items in [('M1', original_arrays), ('U1', actual_arrays)] for key, value in items.items()}
    return report, arrays
