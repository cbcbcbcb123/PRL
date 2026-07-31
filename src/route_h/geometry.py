"""Deterministic reference geometry and canonical bundle materialization."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import math
from pathlib import Path
from typing import Iterable

import numpy as np
from numpy.typing import NDArray

from .contracts import STAGE1_BUNDLE_ID, assert_stage0_inputs, repository_root


FloatArray = NDArray[np.float64]
IntArray = NDArray[np.int64]

PRIMARY_CODES = {
    "apical_lumen": 1,
    "basal_ecm": 2,
    "opposite_outer": 3,
    "lateral": 4,
}
DIRECTION_CODES = {
    "none": 0,
    "lateral_x_minus": 1,
    "lateral_x_plus": 2,
    "lateral_y_minus": 3,
    "lateral_y_plus": 4,
}
ECM_BOUNDARY_CODES = {
    "lumen_facing": 1,
    "outer_facing": 2,
    "lateral_x_minus": 3,
    "lateral_x_plus": 4,
    "lateral_y_minus": 5,
    "lateral_y_plus": 6,
}
OWNER_CODES = {
    "internal_interface": 0,
    "blood": 1,
    "outer_support": 2,
    "lateral_support": 3,
    "traction_free": 4,
}
INTERFACE_CODES = {"IF_ENDO_ECM": 1, "IF_MYO_ECM": 2, "IF_CELL_CELL": 3}


@dataclass(frozen=True)
class SurfaceTemplate:
    unit_vertices: FloatArray
    faces: IntArray


@dataclass(frozen=True)
class CellGeometry:
    entity_id: str
    layer: str
    grid_i: int
    grid_j: int
    vertices: FloatArray
    faces: IntArray
    primary: IntArray
    directional: IntArray
    anchor_minus: IntArray
    anchor_plus: IntArray


@dataclass(frozen=True)
class ECMGeometry:
    vertices: FloatArray
    tetrahedra: IntArray
    boundary_faces: IntArray
    boundary_identity: IntArray
    boundary_tetra: IntArray


def _normalized(vector: FloatArray) -> FloatArray:
    norm = math.sqrt(float(vector[0] * vector[0] + vector[1] * vector[1]) + float(vector[2] * vector[2]))
    if norm == 0.0:
        raise ValueError("zero vector cannot be normalized")
    return np.asarray(vector / norm, dtype=np.float64)


def icosphere_template(level: int = 2) -> SurfaceTemplate:
    if not isinstance(level, int) or level < 0:
        raise ValueError("icosphere subdivision level must be a nonnegative integer")
    phi = (1.0 + math.sqrt(5.0)) / 2.0
    raw = [
        (-1, phi, 0), (1, phi, 0), (-1, -phi, 0), (1, -phi, 0),
        (0, -1, phi), (0, 1, phi), (0, -1, -phi), (0, 1, -phi),
        (phi, 0, -1), (phi, 0, 1), (-phi, 0, -1), (-phi, 0, 1),
    ]
    vertices = [_normalized(np.asarray(row, dtype=np.float64)) for row in raw]
    faces: list[tuple[int, int, int]] = [
        (0, 11, 5), (0, 5, 1), (0, 1, 7), (0, 7, 10), (0, 10, 11),
        (1, 5, 9), (5, 11, 4), (11, 10, 2), (10, 7, 6), (7, 1, 8),
        (3, 9, 4), (3, 4, 2), (3, 2, 6), (3, 6, 8), (3, 8, 9),
        (4, 9, 5), (2, 4, 11), (6, 2, 10), (8, 6, 7), (9, 8, 1),
    ]
    for _ in range(level):
        midpoint_ids: dict[tuple[int, int], int] = {}
        children: list[tuple[int, int, int]] = []

        def midpoint(left: int, right: int) -> int:
            key = (min(left, right), max(left, right))
            if key not in midpoint_ids:
                point = _normalized((vertices[left] + vertices[right]) * 0.5)
                midpoint_ids[key] = len(vertices)
                vertices.append(point)
            return midpoint_ids[key]

        for v0, v1, v2 in faces:
            m01 = midpoint(v0, v1)
            m12 = midpoint(v1, v2)
            m20 = midpoint(v2, v0)
            children.extend([
                (v0, m01, m20),
                (v1, m12, m01),
                (v2, m20, m12),
                (m01, m12, m20),
            ])
        faces = children
    result = SurfaceTemplate(
        np.ascontiguousarray(vertices, dtype=np.float64),
        np.ascontiguousarray(faces, dtype=np.int64),
    )
    expected_vertices = 10 * (4 ** level) + 2
    expected_faces = 20 * (4 ** level)
    if (
        result.unit_vertices.shape != (expected_vertices, 3)
        or result.faces.shape != (expected_faces, 3)
    ):
        raise RuntimeError("icosphere count mismatch")
    return result


def _superellipsoid(
    unit_vertices: FloatArray,
    center: Iterable[float],
    axes: Iterable[float],
    *,
    snap_reference_planes: bool = False,
) -> FloatArray:
    output = np.empty_like(unit_vertices)
    center_array = np.asarray(tuple(center), dtype=np.float64)
    axes_array = np.asarray(tuple(axes), dtype=np.float64)
    for row_id, direction in enumerate(unit_vertices):
        powers = []
        for component in direction:
            q = abs(float(component))
            q2 = q * q
            q4 = q2 * q2
            powers.append(q4 * q4)
        summed_xy = powers[0] + powers[1]
        summed = summed_xy + powers[2]
        denominator = math.sqrt(math.sqrt(math.sqrt(summed)))
        output[row_id] = center_array + axes_array * direction / denominator
    if snap_reference_planes:
        for axis in range(3):
            for sign in (-1.0, 1.0):
                target = float(
                    round(
                        float(center_array[axis] + sign * axes_array[axis]),
                        15,
                    )
                )
                tolerance = (
                    8.0
                    * np.finfo(np.float64).eps
                    * max(1.0, abs(target))
                )
                selected = np.abs(output[:, axis] - target) <= tolerance
                output[selected, axis] = target
    output[output == 0.0] = 0.0
    return np.ascontiguousarray(output, dtype=np.float64)


def _face_labels(layer: str, unit_vertices: FloatArray, faces: IntArray) -> tuple[IntArray, IntArray]:
    primary = np.empty(len(faces), dtype=np.int64)
    directional = np.zeros(len(faces), dtype=np.int64)
    for face_id, face in enumerate(faces):
        u_bar = _normalized(unit_vertices[face].sum(axis=0))
        absolute = np.abs(u_bar)
        tie_tolerance = 8.0 * np.finfo(np.float64).eps
        if absolute[2] + tie_tolerance >= max(absolute[0], absolute[1]):
            if layer == "endocardial":
                label = "apical_lumen" if u_bar[2] < 0.0 else "basal_ecm"
            else:
                label = "basal_ecm" if u_bar[2] < 0.0 else "opposite_outer"
        else:
            label = "lateral"
        primary[face_id] = PRIMARY_CODES[label]
        if label == "lateral":
            if absolute[0] + tie_tolerance >= absolute[1]:
                subtype = "lateral_x_minus" if u_bar[0] < 0.0 else "lateral_x_plus"
            else:
                subtype = "lateral_y_minus" if u_bar[1] < 0.0 else "lateral_y_plus"
            directional[face_id] = DIRECTION_CODES[subtype]
    return primary, directional


def build_cells(
    subdivision_level: int = 2,
    *,
    snap_reference_planes: bool = False,
) -> list[CellGeometry]:
    template = icosphere_template(subdivision_level)
    cells: list[CellGeometry] = []
    for layer, nx, ny, axes in (
        ("endocardial", 3, 2, (0.5, 0.45, 0.12)),
        ("myocardial", 3, 3, (0.5, 0.3, 0.28)),
    ):
        primary, directional = _face_labels(layer, template.unit_vertices, template.faces)
        face_centers = np.asarray(
            [_normalized(template.unit_vertices[face].sum(axis=0)) for face in template.faces]
        )
        anchor_minus = np.flatnonzero(
            (primary == PRIMARY_CODES["lateral"]) & (face_centers[:, 0] <= -0.75)
        ).astype(np.int64)
        anchor_plus = np.flatnonzero(
            (primary == PRIMARY_CODES["lateral"]) & (face_centers[:, 0] >= 0.75)
        ).astype(np.int64)
        for j in range(ny):
            for i in range(nx):
                if layer == "endocardial":
                    center = (0.5 + i, 0.45 + 0.9 * j, -0.12)
                    entity_id = f"ENDO-{i}-{j}"
                    minus = np.empty(0, dtype=np.int64)
                    plus = np.empty(0, dtype=np.int64)
                else:
                    center = (0.5 + i, 0.3 + 0.6 * j, 0.48)
                    entity_id = f"MYO-{i}-{j}"
                    minus = anchor_minus.copy()
                    plus = anchor_plus.copy()
                cells.append(CellGeometry(
                    entity_id=entity_id,
                    layer=layer,
                    grid_i=i,
                    grid_j=j,
                    vertices=_superellipsoid(
                        template.unit_vertices,
                        center,
                        axes,
                        snap_reference_planes=snap_reference_planes,
                    ),
                    faces=template.faces.copy(),
                    primary=primary.copy(),
                    directional=directional.copy(),
                    anchor_minus=minus,
                    anchor_plus=plus,
                ))
    return cells


def triangle_geometry(vertices: FloatArray, faces: IntArray) -> tuple[FloatArray, FloatArray]:
    triangle = vertices[faces]
    raw = np.cross(triangle[:, 1] - triangle[:, 0], triangle[:, 2] - triangle[:, 0])
    twice_area = np.linalg.norm(raw, axis=1)
    if np.any(twice_area <= 0.0):
        raise ValueError("zero-area triangle")
    return 0.5 * twice_area, raw / twice_area[:, None]


def signed_surface_volume(vertices: FloatArray, faces: IntArray) -> float:
    triangle = vertices[faces]
    return float(np.einsum("ij,ij->i", triangle[:, 0], np.cross(triangle[:, 1], triangle[:, 2])).sum() / 6.0)


def triangle_quality(vertices: FloatArray, faces: IntArray) -> FloatArray:
    triangle = vertices[faces]
    lengths2 = (
        np.sum((triangle[:, 1] - triangle[:, 0]) ** 2, axis=1)
        + np.sum((triangle[:, 2] - triangle[:, 1]) ** 2, axis=1)
        + np.sum((triangle[:, 0] - triangle[:, 2]) ** 2, axis=1)
    )
    areas, _ = triangle_geometry(vertices, faces)
    return 4.0 * math.sqrt(3.0) * areas / lengths2


def surface_topology_report(faces: IntArray) -> dict[str, int]:
    edge_counts: dict[tuple[int, int], int] = {}
    oriented_counts: dict[tuple[int, int], int] = {}
    for a, b, c in faces.tolist():
        for left, right in ((a, b), (b, c), (c, a)):
            key = (min(left, right), max(left, right))
            edge_counts[key] = edge_counts.get(key, 0) + 1
            oriented_counts[(left, right)] = oriented_counts.get((left, right), 0) + 1
    bad_incidence = sum(count != 2 for count in edge_counts.values())
    bad_orientation = sum(
        oriented_counts.get((a, b), 0) != 1 or oriented_counts.get((b, a), 0) != 1
        for a, b in edge_counts
    )
    return {
        "edges": len(edge_counts),
        "bad_incidence": int(bad_incidence),
        "bad_orientation": int(bad_orientation),
    }


def _grid_vertex(i: int, j: int, k: int, nx: int = 12, ny: int = 8) -> int:
    return ((k * (ny + 1)) + j) * (nx + 1) + i


def build_ecm(nx: int = 12, ny: int = 8, nz: int = 2) -> ECMGeometry:
    if any(not isinstance(value, int) or value <= 0 for value in (nx, ny, nz)):
        raise ValueError("ECM interval counts must be positive integers")
    if nz < 2:
        raise ValueError("ECM requires at least two elements through thickness")
    dx, dy, dz = 3.0 / nx, 1.8 / ny, 0.2 / nz
    vertices = np.asarray([
        (dx * i, dy * j, dz * k)
        for k in range(nz + 1)
        for j in range(ny + 1)
        for i in range(nx + 1)
    ], dtype=np.float64)
    tetrahedra: list[list[int]] = []
    local_patterns = [
        (0, 1, 3, 7), (0, 1, 5, 7), (0, 2, 3, 7),
        (0, 2, 6, 7), (0, 4, 5, 7), (0, 4, 6, 7),
    ]
    for k in range(nz):
        for j in range(ny):
            for i in range(nx):
                local = [
                    _grid_vertex(i, j, k, nx, ny),
                    _grid_vertex(i + 1, j, k, nx, ny),
                    _grid_vertex(i, j + 1, k, nx, ny),
                    _grid_vertex(i + 1, j + 1, k, nx, ny),
                    _grid_vertex(i, j, k + 1, nx, ny),
                    _grid_vertex(i + 1, j, k + 1, nx, ny),
                    _grid_vertex(i, j + 1, k + 1, nx, ny),
                    _grid_vertex(i + 1, j + 1, k + 1, nx, ny),
                ]
                for pattern in local_patterns:
                    tet = [local[index] for index in pattern]
                    dm = np.column_stack((
                        vertices[tet[1]] - vertices[tet[0]],
                        vertices[tet[2]] - vertices[tet[0]],
                        vertices[tet[3]] - vertices[tet[0]],
                    ))
                    if np.linalg.det(dm) < 0.0:
                        tet[2], tet[3] = tet[3], tet[2]
                    tetrahedra.append(tet)
    tets = np.asarray(tetrahedra, dtype=np.int64)

    face_owners: dict[tuple[int, int, int], list[tuple[list[int], int]]] = {}
    for tet_id, (a, b, c, d) in enumerate(tets.tolist()):
        outward = ([b, c, d], [a, d, c], [a, b, d], [a, c, b])
        for face in outward:
            face_owners.setdefault(tuple(sorted(face)), []).append((face, tet_id))
    boundary_records = [
        (key, owners[0][0], owners[0][1])
        for key, owners in face_owners.items() if len(owners) == 1
    ]
    boundary_records.sort(key=lambda record: record[0])
    boundary_faces = np.asarray([record[1] for record in boundary_records], dtype=np.int64)
    boundary_tetra = np.asarray([record[2] for record in boundary_records], dtype=np.int64)
    identity = np.empty(len(boundary_faces), dtype=np.int64)
    for face_id, face in enumerate(boundary_faces):
        coordinates = vertices[face]
        if np.all(coordinates[:, 2] == 0.0):
            label = "lumen_facing"
        elif np.all(coordinates[:, 2] == 0.2):
            label = "outer_facing"
        elif np.all(coordinates[:, 0] == 0.0):
            label = "lateral_x_minus"
        elif np.all(coordinates[:, 0] == 3.0):
            label = "lateral_x_plus"
        elif np.all(coordinates[:, 1] == 0.0):
            label = "lateral_y_minus"
        elif np.all(coordinates[:, 1] == 1.8):
            label = "lateral_y_plus"
        else:
            raise RuntimeError(f"unclassified ECM boundary face {face_id}")
        identity[face_id] = ECM_BOUNDARY_CODES[label]
    expected_vertices = (nx + 1) * (ny + 1) * (nz + 1)
    expected_tetrahedra = 6 * nx * ny * nz
    if (
        vertices.shape != (expected_vertices, 3)
        or tets.shape != (expected_tetrahedra, 4)
    ):
        raise RuntimeError("ECM count mismatch")
    return ECMGeometry(vertices, tets, boundary_faces, identity, boundary_tetra)


def ray_triangle_hit(
    origin: FloatArray,
    direction: FloatArray,
    vertices: FloatArray,
    faces: IntArray,
    face_ids: IntArray,
    *,
    strictly_positive: bool,
) -> tuple[int, FloatArray, float]:
    best: tuple[float, int, FloatArray] | None = None
    tolerance = 1e-12
    for face_id in face_ids.tolist():
        a, b, c = vertices[faces[face_id]]
        edge1, edge2 = b - a, c - a
        p = np.cross(direction, edge2)
        determinant = float(np.dot(edge1, p))
        if abs(determinant) <= tolerance:
            continue
        inverse = 1.0 / determinant
        offset = origin - a
        u = float(np.dot(offset, p) * inverse)
        q = np.cross(offset, edge1)
        v = float(np.dot(direction, q) * inverse)
        distance = float(np.dot(edge2, q) * inverse)
        lower = tolerance if strictly_positive else -tolerance
        if distance < lower or u < -tolerance or v < -tolerance or u + v > 1.0 + tolerance:
            continue
        distance = max(distance, 0.0)
        barycentric = np.asarray((1.0 - u - v, u, v), dtype=np.float64)
        candidate = (distance, face_id, barycentric)
        if best is None or (candidate[0], candidate[1]) < (best[0], best[1]):
            best = candidate
    if best is None:
        raise RuntimeError("registered ray has no target hit")
    return best[1], best[2], best[0]


def ray_triangle_hit_vectorized(
    origin: FloatArray,
    direction: FloatArray,
    vertices: FloatArray,
    faces: IntArray,
    face_ids: IntArray,
    *,
    strictly_positive: bool,
) -> tuple[int, FloatArray, float]:
    """Vectorized equivalent of the frozen nearest-hit and face-ID tie rule."""
    candidate_faces = faces[face_ids]
    triangles = vertices[candidate_faces]
    edge1 = triangles[:, 1] - triangles[:, 0]
    edge2 = triangles[:, 2] - triangles[:, 0]
    direction_rows = np.broadcast_to(direction, edge2.shape)
    cross_direction_edge2 = np.cross(direction_rows, edge2)
    determinant = np.einsum("ij,ij->i", edge1, cross_direction_edge2)
    tolerance = 1e-12
    valid = np.abs(determinant) > tolerance
    inverse = np.zeros_like(determinant)
    inverse[valid] = 1.0 / determinant[valid]
    offset = origin[None, :] - triangles[:, 0]
    bary_u = np.einsum("ij,ij->i", offset, cross_direction_edge2) * inverse
    cross_offset_edge1 = np.cross(offset, edge1)
    bary_v = np.einsum("j,ij->i", direction, cross_offset_edge1) * inverse
    distance = np.einsum("ij,ij->i", edge2, cross_offset_edge1) * inverse
    lower = tolerance if strictly_positive else -tolerance
    valid &= distance >= lower
    valid &= bary_u >= -tolerance
    valid &= bary_v >= -tolerance
    valid &= bary_u + bary_v <= 1.0 + tolerance
    valid_ids = np.flatnonzero(valid)
    if len(valid_ids) == 0:
        raise RuntimeError("registered ray has no target hit")
    nonnegative_distance = np.maximum(distance[valid_ids], 0.0)
    order = np.lexsort((face_ids[valid_ids], nonnegative_distance))
    selected = int(valid_ids[int(order[0])])
    barycentric = np.asarray(
        (1.0 - bary_u[selected] - bary_v[selected], bary_u[selected], bary_v[selected]),
        dtype=np.float64,
    )
    return int(face_ids[selected]), barycentric, float(max(distance[selected], 0.0))


def vertex_dual_weights(vertices: FloatArray, faces: IntArray, selected_faces: IntArray | None = None) -> FloatArray:
    chosen = faces if selected_faces is None else faces[selected_faces]
    areas, _ = triangle_geometry(vertices, chosen)
    weights = np.zeros(len(vertices), dtype=np.float64)
    for face, area in zip(chosen, areas, strict=True):
        weights[face] += area / 3.0
    return weights


def _material_tethers(
    cells: list[CellGeometry],
    ecm: ECMGeometry,
    *,
    cell_ecm_maximum_gap: float = 0.05,
    cell_cell_maximum_gap: float = 0.15,
    vectorized_ray_search: bool = False,
) -> tuple[IntArray, FloatArray]:
    entity_index = {cell.entity_id: index for index, cell in enumerate(cells)}
    records: list[tuple[str, str, int, str, int, FloatArray, float, float, float, FloatArray, FloatArray]] = []
    ecm_entity = len(cells)
    hit_search = ray_triangle_hit_vectorized if vectorized_ray_search else ray_triangle_hit
    for cell in cells:
        if cell.layer == "endocardial":
            interface, direction, target_code = (
                "IF_ENDO_ECM",
                np.array([0., 0., 1.]),
                ECM_BOUNDARY_CODES["lumen_facing"],
            )
        else:
            interface, direction, target_code = (
                "IF_MYO_ECM",
                np.array([0., 0., -1.]),
                ECM_BOUNDARY_CODES["outer_facing"],
            )
        target_ids = np.flatnonzero(ecm.boundary_identity == target_code).astype(np.int64)
        areas, normals = triangle_geometry(cell.vertices, cell.faces)
        for face_id in np.flatnonzero(cell.primary == PRIMARY_CODES["basal_ecm"]).tolist():
            master_face = cell.faces[face_id]
            master_point = cell.vertices[master_face].mean(axis=0)
            target_face, target_bary, _ = hit_search(
                master_point, direction, ecm.vertices, ecm.boundary_faces, target_ids,
                strictly_positive=False,
            )
            slave_point = target_bary @ ecm.vertices[ecm.boundary_faces[target_face]]
            sign = 1.0 if float(np.dot(normals[face_id], slave_point - master_point)) >= 0.0 else -1.0
            normal = sign * normals[face_id]
            edge = cell.vertices[master_face[1]] - cell.vertices[master_face[0]]
            t1 = _normalized(edge)
            t2 = np.cross(normal, t1)
            gap = float(np.dot(slave_point - master_point, normal))
            if gap < -1e-12 or gap > cell_ecm_maximum_gap + 1e-12:
                raise RuntimeError(f"invalid natural gap {gap} for {cell.entity_id}:{face_id}")
            records.append((interface, cell.entity_id, face_id, "ECM", target_face, target_bary, areas[face_id], gap, sign, t1, t2))

    for layer, nx, ny in (("endocardial", 3, 2), ("myocardial", 3, 3)):
        layer_cells = {(cell.grid_i, cell.grid_j): cell for cell in cells if cell.layer == layer}
        for j in range(ny):
            for i in range(nx):
                master = layer_cells[(i, j)]
                for di, dj, master_subtype, slave_subtype, direction in (
                    (1, 0, "lateral_x_plus", "lateral_x_minus", np.array([1., 0., 0.])),
                    (0, 1, "lateral_y_plus", "lateral_y_minus", np.array([0., 1., 0.])),
                ):
                    if (i + di, j + dj) not in layer_cells:
                        continue
                    slave = layer_cells[(i + di, j + dj)]
                    slave_faces = np.flatnonzero(slave.directional == DIRECTION_CODES[slave_subtype]).astype(np.int64)
                    areas, normals = triangle_geometry(master.vertices, master.faces)
                    for face_id in np.flatnonzero(master.directional == DIRECTION_CODES[master_subtype]).tolist():
                        master_face = master.faces[face_id]
                        master_point = master.vertices[master_face].mean(axis=0)
                        try:
                            target_face, target_bary, _ = hit_search(
                                master_point, direction, slave.vertices, slave.faces, slave_faces,
                                strictly_positive=True,
                            )
                        except RuntimeError as error:
                            raise RuntimeError(
                                f"no cell-cell hit for {master.entity_id}:{face_id} "
                                f"toward {slave.entity_id} ({master_subtype}->{slave_subtype})"
                            ) from error
                        slave_point = target_bary @ slave.vertices[slave.faces[target_face]]
                        sign = 1.0 if float(np.dot(normals[face_id], slave_point - master_point)) >= 0.0 else -1.0
                        normal = sign * normals[face_id]
                        t1 = _normalized(master.vertices[master_face[1]] - master.vertices[master_face[0]])
                        t2 = np.cross(normal, t1)
                        gap = float(np.dot(slave_point - master_point, normal))
                        if gap < -1e-12 or gap > cell_cell_maximum_gap + 1e-12:
                            raise RuntimeError(f"invalid cell-cell natural gap {gap}")
                        records.append(("IF_CELL_CELL", master.entity_id, face_id, slave.entity_id, target_face, target_bary, areas[face_id], gap, sign, t1, t2))
    records.sort(key=lambda item: (item[0], item[1], item[2], item[3], item[4]))
    integer_rows: list[list[int]] = []
    float_rows: list[list[float]] = []
    for pair_id, item in enumerate(records):
        interface, master_id, master_face, slave_id, slave_face, slave_bary, weight, gap, sign, t1, t2 = item
        integer_rows.append([
            INTERFACE_CODES[interface], pair_id, entity_index[master_id], master_face,
            ecm_entity if slave_id == "ECM" else entity_index[slave_id], slave_face,
        ])
        float_rows.append([
            1 / 3, 1 / 3, 1 / 3, *slave_bary.tolist(), weight, gap, sign,
            *t1.tolist(), *t2.tolist(),
        ])
    return np.asarray(integer_rows, dtype=np.int64), np.asarray(float_rows, dtype=np.float64)


def _source_map(tether_int: IntArray, tether_float: FloatArray, cells: list[CellGeometry], ecm: ECMGeometry) -> tuple[IntArray, FloatArray]:
    rows_int: list[list[int]] = []
    rows_float: list[list[float]] = []
    candidates = np.flatnonzero(tether_int[:, 0] == INTERFACE_CODES["IF_MYO_ECM"])
    order = sorted(candidates.tolist(), key=lambda row: (
        tether_int[row, 2], tether_int[row, 3], tether_int[row, 5]
    ))
    for source_id, row in enumerate(order):
        target_face = int(tether_int[row, 5])
        rows_int.append([
            source_id, int(tether_int[row, 2]), int(tether_int[row, 3]),
            target_face, int(ecm.boundary_tetra[target_face]),
        ])
        rows_float.append([
            1 / 3, 1 / 3, 1 / 3,
            *tether_float[row, 3:6].tolist(),
            float(tether_float[row, 6]),
        ])
    return np.asarray(rows_int, dtype=np.int64), np.asarray(rows_float, dtype=np.float64)


def _owner_arrays(cells: list[CellGeometry], ecm: ECMGeometry) -> tuple[IntArray, IntArray]:
    face_count = len(cells[0].faces)
    if any(len(cell.faces) != face_count for cell in cells):
        raise ValueError("all cell templates must have the same face count")
    owners = np.full(
        (len(cells), face_count),
        OWNER_CODES["internal_interface"],
        dtype=np.int64,
    )
    for cell_id, cell in enumerate(cells):
        if cell.layer == "endocardial":
            owners[cell_id, cell.primary == PRIMARY_CODES["apical_lumen"]] = OWNER_CODES["blood"]
            owners[cell_id, cell.primary == PRIMARY_CODES["lateral"]] = OWNER_CODES["traction_free"]
        else:
            owners[cell_id, cell.primary == PRIMARY_CODES["opposite_outer"]] = OWNER_CODES["outer_support"]
            lateral = cell.primary == PRIMARY_CODES["lateral"]
            support = (
                ((cell.grid_i == 0) & (cell.directional == DIRECTION_CODES["lateral_x_minus"]))
                | ((cell.grid_i == 2) & (cell.directional == DIRECTION_CODES["lateral_x_plus"]))
                | ((cell.grid_j == 0) & (cell.directional == DIRECTION_CODES["lateral_y_minus"]))
                | ((cell.grid_j == 2) & (cell.directional == DIRECTION_CODES["lateral_y_plus"]))
            )
            owners[cell_id, lateral & support] = OWNER_CODES["lateral_support"]
    ecm_owner = np.full(len(ecm.boundary_faces), OWNER_CODES["internal_interface"], dtype=np.int64)
    lateral = ecm.boundary_identity >= ECM_BOUNDARY_CODES["lateral_x_minus"]
    ecm_owner[lateral] = OWNER_CODES["traction_free"]
    return owners, ecm_owner


def reference_arrays(
    subdivision_level: int = 2,
    ecm_intervals: tuple[int, int, int] = (12, 8, 2),
    *,
    cell_ecm_maximum_gap: float = 0.05,
    cell_cell_maximum_gap: float = 0.15,
    vectorized_ray_search: bool = False,
    snap_reference_planes: bool = False,
) -> tuple[dict[str, np.ndarray], dict[str, object]]:
    cells = build_cells(
        subdivision_level,
        snap_reference_planes=snap_reference_planes,
    )
    ecm = build_ecm(*ecm_intervals)
    tether_int, tether_float = _material_tethers(
        cells,
        ecm,
        cell_ecm_maximum_gap=cell_ecm_maximum_gap,
        cell_cell_maximum_gap=cell_cell_maximum_gap,
        vectorized_ray_search=vectorized_ray_search,
    )
    source_int, source_float = _source_map(tether_int, tether_float, cells, ecm)
    cell_owner, ecm_owner = _owner_arrays(cells, ecm)
    max_anchor = max(len(cell.anchor_minus) for cell in cells)
    anchor_minus = np.full((len(cells), max_anchor), -1, dtype=np.int64)
    anchor_plus = np.full((len(cells), max_anchor), -1, dtype=np.int64)
    anchor_counts = np.zeros((len(cells), 2), dtype=np.int64)
    for index, cell in enumerate(cells):
        anchor_minus[index, :len(cell.anchor_minus)] = cell.anchor_minus
        anchor_plus[index, :len(cell.anchor_plus)] = cell.anchor_plus
        anchor_counts[index] = (len(cell.anchor_minus), len(cell.anchor_plus))
    cell_dual = np.asarray([
        vertex_dual_weights(cell.vertices, cell.faces) for cell in cells
    ], dtype=np.float64)
    ecm_lumped_volume = np.zeros(len(ecm.vertices), dtype=np.float64)
    for tet in ecm.tetrahedra:
        dm = np.column_stack((
            ecm.vertices[tet[1]] - ecm.vertices[tet[0]],
            ecm.vertices[tet[2]] - ecm.vertices[tet[0]],
            ecm.vertices[tet[3]] - ecm.vertices[tet[0]],
        ))
        ecm_lumped_volume[tet] += np.linalg.det(dm) / 24.0
    exterior_vertices = np.unique(ecm.boundary_faces)
    arrays: dict[str, np.ndarray] = {
        "cell_vertices": np.asarray([cell.vertices for cell in cells], dtype=np.float64),
        "cell_faces": np.asarray([cell.faces for cell in cells], dtype=np.int64),
        "cell_primary_identity": np.asarray([cell.primary for cell in cells], dtype=np.int64),
        "cell_directional_identity": np.asarray([cell.directional for cell in cells], dtype=np.int64),
        "cell_anchor_minus_face_ids": anchor_minus,
        "cell_anchor_plus_face_ids": anchor_plus,
        "cell_anchor_counts": anchor_counts,
        "ecm_vertices": ecm.vertices,
        "ecm_tetrahedra": ecm.tetrahedra,
        "ecm_boundary_faces": ecm.boundary_faces,
        "ecm_boundary_identity": ecm.boundary_identity,
        "ecm_boundary_tetra": ecm.boundary_tetra,
        "material_tether_integer": tether_int,
        "material_tether_float": tether_float,
        "myocardial_source_map_integer": source_int,
        "myocardial_source_map_float": source_float,
        "cell_boundary_owner": cell_owner,
        "ecm_boundary_owner": ecm_owner,
        "cell_gauge_dual_area_weights": cell_dual,
        "ecm_gauge_lumped_volume_weights": ecm_lumped_volume,
        "ecm_exterior_vertex_ids": exterior_vertices.astype(np.int64),
        "ecm_exterior_vertex_dual_area_weights": vertex_dual_weights(
            ecm.vertices, ecm.boundary_faces
        ),
    }
    metadata: dict[str, object] = {
        "bundle_id": STAGE1_BUNDLE_ID,
        "contract_id": "CONTRACT-PRL-ROUTE-H-STAGE0-V05",
        "geometry_spec_id": "GEOMETRY-PRL-ROUTE-H-STAGE0-V05",
        "stage": 1,
        "active_mechanism_enabled": False,
        "full_patch_trajectory_enabled": False,
        "entity_ids": [cell.entity_id for cell in cells] + ["ECM"],
        "entity_layers": [cell.layer for cell in cells] + ["ecm"],
        "primary_codes": PRIMARY_CODES,
        "direction_codes": DIRECTION_CODES,
        "ecm_boundary_codes": ECM_BOUNDARY_CODES,
        "owner_codes": OWNER_CODES,
        "interface_codes": INTERFACE_CODES,
        "material_tether_integer_columns": [
            "interface_code", "pair_id", "master_entity_index", "master_face_id",
            "slave_entity_index", "slave_face_id",
        ],
        "material_tether_float_columns": [
            "master_bary_0", "master_bary_1", "master_bary_2",
            "slave_bary_0", "slave_bary_1", "slave_bary_2",
            "reference_weight", "g0_pair", "normal_orientation_sign",
            "reference_t1_x", "reference_t1_y", "reference_t1_z",
            "reference_t2_x", "reference_t2_y", "reference_t2_z",
        ],
        "source_map_integer_columns": [
            "source_map_id", "source_cell_index", "source_face_id",
            "target_ecm_face_id", "target_tetra_id",
        ],
        "source_map_float_columns": [
            "source_bary_0", "source_bary_1", "source_bary_2",
            "target_bary_0", "target_bary_1", "target_bary_2", "reference_weight",
        ],
    }
    return arrays, metadata


def _canonical_json_bytes(value: object) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")


def _canonical_array(array: np.ndarray) -> np.ndarray:
    if array.dtype.kind == "f":
        result = np.asarray(array, dtype="<f8", order="C").copy()
        result[result == 0.0] = 0.0
        if not np.all(np.isfinite(result)):
            raise ValueError("NaN and infinity are forbidden")
        return result
    return np.asarray(array, dtype="<i8", order="C")


def materialize_reference_bundle(output_dir: Path | None = None) -> dict[str, object]:
    root = repository_root()
    assert_stage0_inputs(root)
    destination = (
        root / "data/route_h/stage1_reference_bundle_v01"
        if output_dir is None else Path(output_dir)
    )
    destination.mkdir(parents=True, exist_ok=True)
    arrays, metadata = reference_arrays()
    metadata_bytes = _canonical_json_bytes(metadata)
    (destination / "metadata.json").write_bytes(metadata_bytes)
    file_records: list[dict[str, object]] = [{
        "name": "metadata",
        "path": "metadata.json",
        "kind": "canonical_json",
        "sha256": hashlib.sha256(metadata_bytes).hexdigest().upper(),
    }]
    for name in sorted(arrays):
        canonical = _canonical_array(arrays[name])
        filename = f"{name}.bin"
        payload = canonical.tobytes(order="C")
        (destination / filename).write_bytes(payload)
        file_records.append({
            "name": name,
            "path": filename,
            "dtype": "float64_le" if canonical.dtype.kind == "f" else "int64_le",
            "shape": list(canonical.shape),
            "sha256": hashlib.sha256(payload).hexdigest().upper(),
        })
    seal_payload = b"".join(
        f"{record['name']}\0{record['sha256']}\n".encode("utf-8")
        for record in sorted(file_records, key=lambda item: str(item["name"]))
    )
    manifest: dict[str, object] = {
        "bundle_id": STAGE1_BUNDLE_ID,
        "status": "materialized_stage1_candidate",
        "canonical_serialization": {
            "integer": "signed little-endian int64 C-order",
            "floating": "little-endian IEEE-754 binary64 C-order; negative zero canonicalized",
            "metadata": "UTF-8 canonical JSON",
            "hash": "SHA-256",
        },
        "files": file_records,
        "bundle_sha256": hashlib.sha256(seal_payload).hexdigest().upper(),
    }
    (destination / "manifest.json").write_bytes(_canonical_json_bytes(manifest))
    return manifest


def load_reference_bundle(bundle_dir: Path | None = None) -> tuple[dict[str, np.ndarray], dict[str, object]]:
    root = repository_root()
    location = (
        root / "data/route_h/stage1_reference_bundle_v01"
        if bundle_dir is None else Path(bundle_dir)
    )
    manifest = json.loads((location / "manifest.json").read_text(encoding="utf-8"))
    arrays: dict[str, np.ndarray] = {}
    verified_records: list[dict[str, object]] = []
    for record in manifest["files"]:
        payload = (location / record["path"]).read_bytes()
        observed = hashlib.sha256(payload).hexdigest().upper()
        if observed != record["sha256"]:
            raise RuntimeError(f"reference bundle hash mismatch: {record['path']}")
        verified_records.append(record)
        if "dtype" in record:
            dtype = "<f8" if record["dtype"] == "float64_le" else "<i8"
            arrays[record["name"]] = np.frombuffer(payload, dtype=dtype).reshape(record["shape"]).copy()
    seal_payload = b"".join(
        f"{record['name']}\0{record['sha256']}\n".encode("utf-8")
        for record in sorted(verified_records, key=lambda item: str(item["name"]))
    )
    if hashlib.sha256(seal_payload).hexdigest().upper() != manifest["bundle_sha256"]:
        raise RuntimeError("reference bundle seal mismatch")
    metadata = json.loads((location / "metadata.json").read_text(encoding="utf-8"))
    return arrays, metadata
