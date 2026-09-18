"""One Gmsh tetrahedral candidate inside immutable faceted material boundaries."""
from collections import defaultdict
import numpy as np

OPTIONS = {'General.NumThreads': 1, 'General.Terminal': 1, 'General.Verbosity': 4,
    'Mesh.MaxNumThreads1D': 1, 'Mesh.MaxNumThreads2D': 1, 'Mesh.MaxNumThreads3D': 1,
    'Mesh.Algorithm3D': 1, 'Mesh.MeshOnlyEmpty': 1, 'Mesh.ElementOrder': 1,
    'Mesh.MeshSizeMin': .18, 'Mesh.MeshSizeMax': .18, 'Mesh.MeshSizeFromPoints': 0,
    'Mesh.MeshSizeFromCurvature': 0, 'Mesh.MeshSizeExtendFromBoundary': 0,
    'Mesh.Optimize': 0, 'Mesh.OptimizeNetgen': 0, 'Mesh.OptimizeThreshold': .3,
    'Mesh.RandomSeed': 1, 'Mesh.MaxRetries': 0, 'Mesh.Binary': 1}


def boundary_complex(data):
    """Oriented BRep producer; acceptance reconstructs topology independently."""
    records = defaultdict(list); xyz = data['xyz']
    for cell, layer in zip(data['tetrahedra'], data['layers']):
        for order in [[1, 2, 3], [0, 3, 2], [0, 1, 3], [0, 2, 1]]:
            face = tuple(int(cell[k]) for k in order)
            records[tuple(sorted(face))].append((face, int(layer)))
    facets = []; shells = {1: [], 2: [], 3: []}
    for key, owners in sorted(records.items()):
        if len(owners) > 2:
            raise ValueError('Nonmanifold source')
        if len(owners) == 2 and owners[0][1] == owners[1][1]:
            continue
        tag = len(facets)+1
        facets.append(owners[0][0]); shells[owners[0][1]].append(tag)
        if len(owners) == 2:
            shells[owners[1][1]].append(-tag)
    facets = np.asarray(facets, dtype=np.int64)
    return {'facets': facets, 'shells': shells, 'vertices': np.unique(facets)}


def exact_surface_indices(reference_xyz, reference_faces, actual_xyz):
    """Node tags are not identities: match immutable coordinates, never nearest points."""
    positions = {tuple(point): i for i, point in enumerate(actual_xyz)}
    if len(positions) != len(actual_xyz):
        raise ValueError('Duplicate coordinate identity')
    try:
        return np.asarray([[positions[tuple(reference_xyz[v])] for v in face]
                           for face in reference_faces], dtype=np.int64)
    except KeyError as error:
        raise ValueError('A frozen boundary coordinate changed or disappeared') from error


def generate(reference, root, save_json):
    """No retries, new surfaces, snapping, random coordinate edits or installs."""
    import gmsh
    complex_data = boundary_complex(reference)
    gmsh.initialize([], readConfigFiles=False)
    gmsh.logger.start()
    try:
        for key, value in OPTIONS.items():
            gmsh.option.setNumber(key, value)
        save_json(root/'gmsh_environment.json', {'version': gmsh.__version__,
            'explicit_options_readback': {k: gmsh.option.getNumber(k) for k in OPTIONS},
            'optimizer': {'method': '', 'force': False, 'niter': 1}, 'geometry_jitter': False})
        gmsh.write(str(root/'gmsh_options.opt'))
        gmsh.model.add('frozen_M1_three_domains')
        xyz = reference['xyz']; edges = {}
        for vertex in complex_data['vertices']:
            gmsh.model.geo.addPoint(*xyz[vertex], tag=int(vertex)+1)
        for tag, face in enumerate(complex_data['facets'], 1):
            boundary = []
            for first, second in zip(face, np.roll(face, -1)):
                key = tuple(sorted((int(first), int(second))))
                if key not in edges:
                    edges[key] = gmsh.model.geo.addLine(key[0]+1, key[1]+1)
                boundary.append(edges[key]*(1 if first < second else -1))
            loop = gmsh.model.geo.addCurveLoop(boundary)
            gmsh.model.geo.addPlaneSurface([loop], tag=tag)
        for layer, surfaces in complex_data['shells'].items():
            shell = gmsh.model.geo.addSurfaceLoop(surfaces)
            gmsh.model.geo.addVolume([shell], tag=layer)
        gmsh.model.geo.synchronize()
        for vertex in complex_data['vertices']:
            node = int(vertex)+1
            gmsh.model.mesh.addNodes(0, node, [node], xyz[vertex].tolist())
            gmsh.model.mesh.addElementsByType(node, 15, [], [node])
        for endpoints, tag in edges.items():
            gmsh.model.mesh.addElementsByType(tag, 1, [], [v+1 for v in endpoints])
        for tag, face in enumerate(complex_data['facets'], 1):
            gmsh.model.mesh.addElementsByType(tag, 2, [], (face+1).tolist())
        for layer in [1, 2, 3]:
            gmsh.model.addPhysicalGroup(3, [layer], layer)
        gmsh.write(str(root/'fixed_surfaces.msh'))
        save_json(root/'meshing_started.json', {'candidates': 1, 'generate_calls': 1, 'automatic_retries': 0})
        gmsh.model.mesh.generate(3)
        gmsh.write(str(root/'before_optimization.msh'))
        gmsh.model.mesh.optimize('', force=False, niter=1, dimTags=[(3, k) for k in [1, 2, 3]])
        gmsh.write(str(root/'candidate.msh'))
        tags, coords, _ = gmsh.model.mesh.getNodes()
        xyz_new = np.asarray(coords).reshape(-1, 3)
        lookup = {int(tag): i for i, tag in enumerate(tags)}
        cells = []; labels = []
        for layer in [1, 2, 3]:
            types, _, nodes = gmsh.model.mesh.getElements(3, layer)
            if list(types) != [4]:
                raise ValueError('Expected only linear tetrahedra in every volume')
            tetra = np.asarray([[lookup[int(v)] for v in row] for row in np.asarray(nodes[0]).reshape(-1, 4)])
            cells.extend(tetra); labels.extend([layer]*len(tetra))
        cells = np.asarray(cells, dtype=np.int64)
        # Element orientation normalization only; does not move a node.
        sign = np.linalg.det((xyz_new[cells[:, 1:]]-xyz_new[cells[:, :1]]).swapaxes(1, 2))
        flipped = sign < 0
        cells[flipped, 1], cells[flipped, 2] = cells[flipped, 2].copy(), cells[flipped, 1].copy()
        data = {'xyz': xyz_new, 'tetrahedra': cells, 'layers': np.asarray(labels, dtype=np.int32)}
        for name in ['inner_faces', 'outer_faces']:
            data[name] = exact_surface_indices(reference['xyz'], reference[name], xyz_new)
        np.savez_compressed(root/'candidate_geometry.npz', **data)
        return data
    finally:
        save_json(root/'gmsh_log.json', gmsh.logger.get())
        gmsh.logger.stop()
        gmsh.finalize()
