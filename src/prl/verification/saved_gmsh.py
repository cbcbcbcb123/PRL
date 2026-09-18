"""Read an existing MSH with meshio; no mesher, solver or node repair capability."""
from pathlib import Path
import numpy as np


def load_saved(path, reference):
    import meshio
    mesh = meshio.read(Path(path))
    if any(block.type != 'tetra' for block in mesh.cells):
        raise ValueError('Expected volume-only MSH containing linear tetrahedra')
    cells = np.concatenate([block.data for block in mesh.cells]).astype(np.int64)
    layers = np.concatenate(mesh.cell_data['gmsh:physical']).astype(np.int32)
    coordinates = mesh.points
    determinants = np.linalg.det((coordinates[cells[:, 1:]]-coordinates[cells[:, :1]]).swapaxes(1, 2))
    reversed_cells = determinants < 0
    cells[reversed_cells, 1], cells[reversed_cells, 2] = cells[reversed_cells, 2].copy(), cells[reversed_cells, 1].copy()
    # Independent exact mapping: lexicographic coordinate lookup, not Gmsh IDs.
    source = np.asarray(reference['xyz']); records = [tuple(point) for point in coordinates]
    if len(set(records)) != len(records):
        raise ValueError('Duplicate coordinates in exported candidate')
    mapped = {}
    for name in ['inner_faces', 'outer_faces']:
        mapped[name] = np.asarray([[records.index(tuple(source[v])) for v in row]
                                  for row in reference[name]], dtype=np.int64)
    return {'xyz': coordinates, 'tetrahedra': cells, 'layers': layers, **mapped}
