"""Current-area Q2 face pressure and its exact, generally nonsymmetric tangent.

Faces are (element, natural_axis, side), with side -1 or +1.  Positive pressure
acts inward: traction = -pressure * outward_current_unit_normal.  No potential
is reported: pressure on an open set of faces is not generally conservative in
the full displacement space.  Surface quadrature is 3 x 3 Gauss.
"""

from itertools import product

import numpy as np
from scipy.sparse import coo_matrix


def validate_faces(mesh: dict, faces) -> list[tuple[int, int, int]]:
    """Reject duplicate, internal, invalid, or nonmanifold face selections."""
    nodes = np.asarray(mesh["nodes"])
    cells = np.asarray(mesh["elements"])
    if nodes.ndim != 2 or nodes.shape[1] != 3 or not np.all(np.isfinite(nodes)):
        raise ValueError("pressure mesh requires finite three-dimensional nodes")
    if (cells.ndim != 2 or cells.shape[1] != 27 or not np.issubdtype(cells.dtype, np.integer)
            or np.any(cells < 0) or np.any(cells >= len(nodes))):
        raise ValueError("pressure mesh requires valid Q2 element connectivity")
    local = np.array(list(product((-1, 0, 1), repeat=3)))
    ownership, face_keys = {}, {}
    for element, cell in enumerate(cells):
        if len(np.unique(cell)) != 27:
            raise ValueError("Q2 element contains duplicate node indices")
        for axis in range(3):
            for side in (-1, 1):
                key = tuple(sorted(cell[local[:, axis] == side].tolist()))
                face_keys[element, axis, side] = key
                ownership[key] = ownership.get(key, 0) + 1
    if any(count > 2 for count in ownership.values()):
        raise ValueError("nonmanifold Q2 face topology")
    try:
        requested = list(faces)
    except TypeError as error:
        raise ValueError("pressure faces must be an iterable of triples") from error
    selected, seen = [], set()
    for face in requested:
        if (not isinstance(face, (tuple, list, np.ndarray)) or len(face) != 3
                or any(isinstance(value, (bool, np.bool_)) or not isinstance(value, (int, np.integer)) for value in face)):
            raise ValueError("pressure face must be an integer (element, axis, side) triple")
        element, axis, side = (int(value) for value in face)
        item = (element, axis, side)
        if not 0 <= element < len(cells) or axis not in (0, 1, 2) or side not in (-1, 1):
            raise ValueError("pressure face element, axis, or side is invalid")
        if item in seen:
            raise ValueError("duplicate pressure face")
        if ownership[face_keys[item]] != 1:
            raise ValueError("pressure can only act on external faces, not an internal face")
        seen.add(item)
        selected.append(item)
    return selected


def assemble_pressure(mesh: dict, displacement, faces, pressure: float, *, with_tangent=True) -> dict:
    """Return displacement force, df/du CSR, selected area, and resultant."""
    from .mixed_hex import shape_functions

    if isinstance(pressure, (bool, np.bool_)) or not np.isscalar(pressure) or np.iscomplexobj(pressure):
        raise ValueError("pressure must be a finite real scalar")
    try:
        pressure = float(pressure)
    except (TypeError, ValueError) as error:
        raise ValueError("pressure must be a finite real scalar") from error
    if not np.isfinite(pressure):
        raise ValueError("pressure must be a finite real scalar")
    selected = validate_faces(mesh, faces)
    reference = np.asarray(mesh["nodes"], dtype=float)
    displacement = np.asarray(displacement)
    if np.iscomplexobj(displacement) or displacement.shape not in (reference.shape, (3 * len(reference),)):
        raise ValueError("pressure displacement must be real and have nodal xyz shape")
    displacement = np.asarray(displacement, dtype=float).reshape(-1, 3)
    if not np.all(np.isfinite(displacement)):
        raise ValueError("pressure displacement is nonfinite")
    current = reference + displacement
    abscissae, gauss_weights = np.polynomial.legendre.leggauss(3)
    indices = np.array(list(product(range(3), repeat=2)))
    weights = np.prod(gauss_weights[indices], axis=1)
    force = np.zeros(3 * len(reference))
    rows, columns, entries, areas = [], [], [], []
    for element, axis, side in selected:
        first, second = (axis + 1) % 3, (axis + 2) % 3
        points = np.empty((9, 3))
        points[:, axis] = side
        points[:, first] = abscissae[indices[:, 0]]
        points[:, second] = abscissae[indices[:, 1]]
        basis = shape_functions(points)
        values, derivative = basis["q2"], basis["q2_derivatives"]
        cell = mesh["elements"][element]
        jacobian0 = np.einsum("ai,qaJ->qiJ", reference[cell], derivative)
        jacobian = np.einsum("ai,qaJ->qiJ", current[cell], derivative)
        determinant0, determinant = np.linalg.det(jacobian0), np.linalg.det(jacobian)
        if (not np.all(np.isfinite(jacobian0)) or not np.all(np.isfinite(jacobian))
                or not np.all(np.isfinite(determinant0)) or not np.all(np.isfinite(determinant))
                or np.any(determinant0 <= 0) or np.any(determinant <= 0)):
            raise ValueError("pressure face has nonfinite or nonpositive reference or current Jacobian")
        tangent_first, tangent_second = jacobian[:, :, first], jacobian[:, :, second]
        area_vector = side * np.cross(tangent_first, tangent_second)
        magnitudes = np.linalg.norm(area_vector, axis=1)
        if np.any(magnitudes <= 0) or not np.all(np.isfinite(magnitudes)):
            raise ValueError("degenerate pressure surface quadrature")
        local_force = -pressure * np.einsum("qa,qi,q->ai", values, area_vector, weights)
        dofs = (3 * cell[:, None] + np.arange(3)).ravel()
        np.add.at(force, dofs, local_force.ravel())
        areas.append(float(weights @ magnitudes))
        if with_tangent:
            # d(t1 x t2)/du_bj = dNb/ds1 (ej x t2) + dNb/ds2 (t1 x ej).
            first_cross = np.swapaxes(np.cross(np.eye(3)[None], tangent_second[:, None]), 1, 2)
            second_cross = np.swapaxes(np.cross(tangent_first[:, None], np.eye(3)[None]), 1, 2)
            derivative_area = side * (
                derivative[:, :, first, None, None] * first_cross[:, None]
                + derivative[:, :, second, None, None] * second_cross[:, None])
            local_tangent = -pressure * np.einsum("qa,qbij,q->aibj", values, derivative_area, weights).reshape(81, 81)
            rows.append(np.repeat(dofs, 81))
            columns.append(np.tile(dofs, 81))
            entries.append(local_tangent.ravel())
    tangent = None
    if with_tangent:
        tangent = (coo_matrix((np.concatenate(entries), (np.concatenate(rows), np.concatenate(columns))),
                             shape=(len(force), len(force))).tocsr() if entries
                   else coo_matrix((len(force), len(force))).tocsr())
    return {"force": force, "tangent": tangent, "current_area": float(sum(areas)),
            "face_areas": np.asarray(areas), "faces": np.asarray(selected, dtype=np.int64).reshape(-1, 3),
            "resultant": force.reshape(-1, 3).sum(axis=0), "energy_available": False,
            "energy_note": "No pressure potential assumed for a possibly open face set."}
