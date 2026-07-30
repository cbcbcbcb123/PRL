"""Dynamic closed-surface steric contact and frozen material adhesion."""

from __future__ import annotations

from dataclasses import dataclass
import math
import numpy as np
from numpy.polynomial import polynomial as poly
from numpy.typing import NDArray


FloatArray = NDArray[np.float64]
IntArray = NDArray[np.int64]

FEATURE_ORDER = {
    "face_interior": 0,
    "edge_01": 1,
    "edge_12": 2,
    "edge_20": 3,
    "vertex_0": 4,
    "vertex_1": 5,
    "vertex_2": 6,
}


@dataclass(frozen=True)
class ClosestFeature:
    face_id: int
    barycentric: FloatArray
    region: str
    squared_distance: float


@dataclass(frozen=True)
class StericRecord:
    source_vertex_id: int
    target_face_id: int
    target_feature_region: str
    target_barycentric: FloatArray
    inside_outside_state: str
    signed_gap: float
    reference_weight: float


def closest_point_triangle(point: FloatArray, triangle: FloatArray) -> tuple[FloatArray, str]:
    """Exact piecewise closest point using Ericson's Voronoi-region tests."""
    a, b, c = triangle
    ab, ac = b - a, c - a
    ap = point - a
    d1, d2 = float(np.dot(ab, ap)), float(np.dot(ac, ap))
    if d1 <= 0.0 and d2 <= 0.0:
        return np.array([1.0, 0.0, 0.0]), "vertex_0"
    bp = point - b
    d3, d4 = float(np.dot(ab, bp)), float(np.dot(ac, bp))
    if d3 >= 0.0 and d4 <= d3:
        return np.array([0.0, 1.0, 0.0]), "vertex_1"
    vc = d1 * d4 - d3 * d2
    if vc <= 0.0 and d1 >= 0.0 and d3 <= 0.0:
        fraction = d1 / (d1 - d3)
        return np.array([1.0 - fraction, fraction, 0.0]), "edge_01"
    cp = point - c
    d5, d6 = float(np.dot(ab, cp)), float(np.dot(ac, cp))
    if d6 >= 0.0 and d5 <= d6:
        return np.array([0.0, 0.0, 1.0]), "vertex_2"
    vb = d5 * d2 - d1 * d6
    if vb <= 0.0 and d2 >= 0.0 and d6 <= 0.0:
        fraction = d2 / (d2 - d6)
        return np.array([1.0 - fraction, 0.0, fraction]), "edge_20"
    va = d3 * d6 - d5 * d4
    if va <= 0.0 and (d4 - d3) >= 0.0 and (d5 - d6) >= 0.0:
        fraction = (d4 - d3) / ((d4 - d3) + (d5 - d6))
        return np.array([0.0, 1.0 - fraction, fraction]), "edge_12"
    denominator = 1.0 / (va + vb + vc)
    v = vb * denominator
    w = vc * denominator
    return np.array([1.0 - v - w, v, w]), "face_interior"


def global_closest_feature(
    point: FloatArray,
    target_vertices: FloatArray,
    target_faces: IntArray,
) -> ClosestFeature:
    triangles = target_vertices[target_faces]
    if len(triangles) == 0:
        raise ValueError("target surface has no faces")
    a, b, c = triangles[:, 0], triangles[:, 1], triangles[:, 2]
    ab, ac = b - a, c - a
    ap = point - a
    d1 = np.einsum("ij,ij->i", ab, ap)
    d2 = np.einsum("ij,ij->i", ac, ap)
    bp = point - b
    d3 = np.einsum("ij,ij->i", ab, bp)
    d4 = np.einsum("ij,ij->i", ac, bp)
    cp = point - c
    d5 = np.einsum("ij,ij->i", ab, cp)
    d6 = np.einsum("ij,ij->i", ac, cp)
    va = d3 * d6 - d5 * d4
    vb = d5 * d2 - d1 * d6
    vc = d1 * d4 - d3 * d2
    barycentric = np.empty((len(triangles), 3), dtype=np.float64)
    regions = np.full(len(triangles), -1, dtype=np.int64)
    remaining = np.ones(len(triangles), dtype=bool)

    def assign(mask: NDArray[np.bool_], values: FloatArray, region: str) -> None:
        selected = remaining & mask
        barycentric[selected] = values[selected] if values.ndim == 2 else values
        regions[selected] = FEATURE_ORDER[region]
        remaining[selected] = False

    assign(
        (d1 <= 0.0) & (d2 <= 0.0),
        np.broadcast_to(np.array([1.0, 0.0, 0.0]), barycentric.shape),
        "vertex_0",
    )
    assign(
        (d3 >= 0.0) & (d4 <= d3),
        np.broadcast_to(np.array([0.0, 1.0, 0.0]), barycentric.shape),
        "vertex_1",
    )
    fraction = np.divide(d1, d1 - d3, out=np.zeros_like(d1), where=(d1 - d3) != 0.0)
    assign(
        (vc <= 0.0) & (d1 >= 0.0) & (d3 <= 0.0),
        np.column_stack((1.0 - fraction, fraction, np.zeros_like(fraction))),
        "edge_01",
    )
    assign(
        (d6 >= 0.0) & (d5 <= d6),
        np.broadcast_to(np.array([0.0, 0.0, 1.0]), barycentric.shape),
        "vertex_2",
    )
    fraction = np.divide(d2, d2 - d6, out=np.zeros_like(d2), where=(d2 - d6) != 0.0)
    assign(
        (vb <= 0.0) & (d2 >= 0.0) & (d6 <= 0.0),
        np.column_stack((1.0 - fraction, np.zeros_like(fraction), fraction)),
        "edge_20",
    )
    denominator = (d4 - d3) + (d5 - d6)
    fraction = np.divide(
        d4 - d3, denominator, out=np.zeros_like(denominator), where=denominator != 0.0
    )
    assign(
        (va <= 0.0) & ((d4 - d3) >= 0.0) & ((d5 - d6) >= 0.0),
        np.column_stack((np.zeros_like(fraction), 1.0 - fraction, fraction)),
        "edge_12",
    )
    denominator = va + vb + vc
    v = np.divide(vb, denominator, out=np.zeros_like(vb), where=denominator != 0.0)
    w = np.divide(vc, denominator, out=np.zeros_like(vc), where=denominator != 0.0)
    barycentric[remaining] = np.column_stack((1.0 - v - w, v, w))[remaining]
    regions[remaining] = FEATURE_ORDER["face_interior"]
    closest = np.einsum("ni,nij->nj", barycentric, triangles)
    difference = closest - point
    squared = np.einsum("ij,ij->i", difference, difference)
    face_id = int(np.argmin(squared))
    region_by_code = {value: key for key, value in FEATURE_ORDER.items()}
    return ClosestFeature(
        face_id,
        barycentric[face_id],
        region_by_code[int(regions[face_id])],
        float(squared[face_id]),
    )


def winding_number(point: FloatArray, vertices: FloatArray, faces: IntArray) -> float:
    triangle = vertices[faces] - point
    a, b, c = triangle[:, 0], triangle[:, 1], triangle[:, 2]
    na, nb, nc = np.linalg.norm(a, axis=1), np.linalg.norm(b, axis=1), np.linalg.norm(c, axis=1)
    numerator = np.einsum("ij,ij->i", a, np.cross(b, c))
    denominator = (
        na * nb * nc
        + np.einsum("ij,ij->i", a, b) * nc
        + np.einsum("ij,ij->i", b, c) * na
        + np.einsum("ij,ij->i", c, a) * nb
    )
    # np.sum preserves the ascending face-ID traversal of the input arrays.
    total = float(np.sum(2.0 * np.arctan2(numerator, denominator)))
    return abs(total) / (4.0 * math.pi)


def signed_surface_distance(
    point: FloatArray,
    target_vertices: FloatArray,
    target_faces: IntArray,
    *,
    boundary_tolerance: float = 1e-12,
    ambiguity_half_width: float = 1e-8,
) -> tuple[float, str, ClosestFeature]:
    owner = global_closest_feature(point, target_vertices, target_faces)
    distance = math.sqrt(max(owner.squared_distance, 0.0))
    if distance <= boundary_tolerance:
        return 0.0, "boundary", owner
    winding = winding_number(point, target_vertices, target_faces)
    if winding < 0.5 - ambiguity_half_width:
        return distance, "outside", owner
    if winding > 0.5 + ambiguity_half_width:
        return -distance, "inside", owner
    raise ValueError(f"ambiguous winding-number classification: {winding}")


def steric_pair_energy_force(
    source_vertices: FloatArray,
    source_vertex_ids: IntArray,
    source_weights: FloatArray,
    target_vertices: FloatArray,
    target_faces: IntArray,
    *,
    k_rep: float = 200.0,
) -> tuple[float, FloatArray, FloatArray, list[StericRecord]]:
    source_force = np.zeros_like(source_vertices)
    target_force = np.zeros_like(target_vertices)
    energy = 0.0
    records: list[StericRecord] = []
    for source_id in source_vertex_ids.tolist():
        point = source_vertices[source_id]
        gap, state, owner = signed_surface_distance(point, target_vertices, target_faces)
        weight = float(source_weights[source_id])
        records.append(StericRecord(
            source_id, owner.face_id, owner.region, owner.barycentric.copy(),
            state, gap, weight,
        ))
        if gap < 0.0:
            face = target_faces[owner.face_id]
            closest = owner.barycentric @ target_vertices[face]
            difference = point - closest
            energy += 0.5 * k_rep * weight * float(np.dot(difference, difference))
            gradient = k_rep * weight * difference
            source_force[source_id] -= gradient
            target_force[face] += owner.barycentric[:, None] * gradient
    return energy, source_force, target_force, records


def _adhesion_shape(opening: float, cutoff: float) -> tuple[float, float]:
    if opening < 0.0:
        return 1.0, 0.0
    if opening > cutoff:
        return 0.0, 0.0
    scaled = opening / cutoff
    value = 1.0 - 3.0 * scaled * scaled + 2.0 * scaled ** 3
    derivative = (-6.0 * scaled + 6.0 * scaled * scaled) / cutoff
    return value, derivative


def material_tether_energy_force_with_reference(
    master_vertices: FloatArray,
    master_face: IntArray,
    slave_vertices: FloatArray,
    slave_face: IntArray,
    *,
    reference_master_vertices: FloatArray,
    reference_slave_vertices: FloatArray,
    master_barycentric: FloatArray,
    slave_barycentric: FloatArray,
    reference_weight: float,
    g0_pair: float,
    normal_orientation_sign: float,
    reference_t1: FloatArray,
    reference_t2: FloatArray,
    adhesion_work: float,
    opening_cutoff: float = 0.08,
    tangential_stiffness: float = 0.5,
) -> tuple[dict[str, float], FloatArray, FloatArray, dict[str, FloatArray | float]]:
    """Tether evaluation with the frozen reference material projection.

    Kept separate from the low-level routine so deformation tests cannot
    accidentally recompute the natural slip from current coordinates.
    """
    reference_relative = (
        slave_barycentric @ reference_slave_vertices[slave_face]
        - master_barycentric @ reference_master_vertices[master_face]
    )
    # Evaluate the same chain explicitly, using immutable scalar projections.
    local_master = master_vertices[master_face]
    local_slave = slave_vertices[slave_face]
    master_point = master_barycentric @ local_master
    slave_point = slave_barycentric @ local_slave
    relative = slave_point - master_point
    edge = local_master[1] - local_master[0]
    edge_length = float(np.linalg.norm(edge))
    raw_normal = np.cross(edge, local_master[2] - local_master[0])
    normal_length = float(np.linalg.norm(raw_normal))
    if edge_length <= 0.0 or normal_length <= 0.0:
        raise ValueError("degenerate material tether master face")
    t1 = edge / edge_length
    unit_normal = raw_normal / normal_length
    normal = normal_orientation_sign * unit_normal
    t2 = np.cross(normal, t1)
    gap = float(np.dot(relative, normal))
    opening = gap - g0_pair
    slip = np.asarray([
        np.dot(relative, t1) - np.dot(reference_relative, reference_t1),
        np.dot(relative, t2) - np.dot(reference_relative, reference_t2),
    ])
    shape, shape_derivative = _adhesion_shape(opening, opening_cutoff)
    slip2 = float(np.dot(slip, slip))
    normal_energy = -reference_weight * adhesion_work * shape
    tangential_energy = 0.5 * reference_weight * tangential_stiffness * shape * slip2
    opening_bar = reference_weight * (
        -adhesion_work * shape_derivative
        + 0.5 * tangential_stiffness * shape_derivative * slip2
    )
    slip_bar = reference_weight * tangential_stiffness * shape * slip
    relative_bar = opening_bar * normal + slip_bar[0] * t1 + slip_bar[1] * t2
    normal_bar = opening_bar * relative + slip_bar[1] * np.cross(t1, relative)
    t1_bar = slip_bar[0] * relative + slip_bar[1] * np.cross(relative, normal)
    unit_normal_bar = normal_orientation_sign * normal_bar
    raw_bar = (unit_normal_bar - unit_normal * np.dot(unit_normal, unit_normal_bar)) / normal_length
    edge_bar = (t1_bar - t1 * np.dot(t1, t1_bar)) / edge_length
    other = local_master[2] - local_master[0]
    edge_from_normal_bar = np.cross(other, raw_bar)
    other_bar = np.cross(raw_bar, edge)
    master_gradient = np.zeros((3, 3), dtype=np.float64)
    master_gradient[1] += edge_from_normal_bar + edge_bar
    master_gradient[2] += other_bar
    master_gradient[0] -= edge_from_normal_bar + other_bar + edge_bar
    master_gradient -= master_barycentric[:, None] * relative_bar
    slave_gradient = slave_barycentric[:, None] * relative_bar
    return {
        "adhesion_normal": normal_energy,
        "adhesion_tangential": tangential_energy,
        "adhesion_total": normal_energy + tangential_energy,
    }, -master_gradient, -slave_gradient, {
        "gap": gap,
        "opening": opening,
        "slip": slip,
        "normal": normal,
        "t1": t1,
        "t2": t2,
    }


def pair_residuals(
    master_positions: FloatArray,
    master_force: FloatArray,
    slave_positions: FloatArray,
    slave_force: FloatArray,
    origin: FloatArray | None = None,
) -> tuple[float, float]:
    if origin is None:
        origin = np.zeros(3)
    resultant = master_force.sum(axis=0) + slave_force.sum(axis=0)
    moment = (
        np.cross(master_positions - origin, master_force).sum(axis=0)
        + np.cross(slave_positions - origin, slave_force).sum(axis=0)
    )
    scale = max(1.0, float(np.linalg.norm(master_force)) + float(np.linalg.norm(slave_force)))
    return float(np.linalg.norm(resultant) / scale), float(np.linalg.norm(moment) / scale)


def _linear_polynomial_vector(start: FloatArray, end: FloatArray) -> list[FloatArray]:
    return [np.asarray([start[i], end[i] - start[i]]) for i in range(3)]


def _poly_sub(left: list[FloatArray], right: list[FloatArray]) -> list[FloatArray]:
    return [poly.polysub(a, b) for a, b in zip(left, right, strict=True)]


def _poly_cross(left: list[FloatArray], right: list[FloatArray]) -> list[FloatArray]:
    return [
        poly.polysub(poly.polymul(left[1], right[2]), poly.polymul(left[2], right[1])),
        poly.polysub(poly.polymul(left[2], right[0]), poly.polymul(left[0], right[2])),
        poly.polysub(poly.polymul(left[0], right[1]), poly.polymul(left[1], right[0])),
    ]


def _poly_dot(left: list[FloatArray], right: list[FloatArray]) -> FloatArray:
    result = np.asarray([0.0])
    for a, b in zip(left, right, strict=True):
        result = poly.polyadd(result, poly.polymul(a, b))
    return result


def _real_unit_roots(coefficients: FloatArray) -> list[float]:
    trimmed = np.trim_zeros(coefficients, "b")
    if len(trimmed) <= 1:
        return []
    roots = poly.polyroots(trimmed)
    result = sorted({
        float(min(1.0, max(0.0, root.real)))
        for root in roots
        if abs(root.imag) <= 1e-9 and -1e-10 <= root.real <= 1.0 + 1e-10
    })
    return result


def _sign_crossing(coefficients: FloatArray, root: float) -> bool:
    step = min(1e-6, max(1e-10, 0.25 * min(root + 1e-12, 1.0 - root + 1e-12)))
    left = max(0.0, root - step)
    right = min(1.0, root + step)
    if left == right:
        return False
    return float(poly.polyval(left, coefficients) * poly.polyval(right, coefficients)) < 0.0


def _triangle_barycentric(point: FloatArray, triangle: FloatArray) -> FloatArray:
    a, b, c = triangle
    v0, v1, v2 = b - a, c - a, point - a
    d00, d01, d11 = np.dot(v0, v0), np.dot(v0, v1), np.dot(v1, v1)
    d20, d21 = np.dot(v2, v0), np.dot(v2, v1)
    denominator = d00 * d11 - d01 * d01
    if abs(denominator) <= 1e-18:
        return np.array([math.nan, math.nan, math.nan])
    v = (d11 * d20 - d01 * d21) / denominator
    w = (d00 * d21 - d01 * d20) / denominator
    return np.array([1.0 - v - w, v, w])


def proper_triangle_crossing_ccd(
    triangle_a_start: FloatArray,
    triangle_a_end: FloatArray,
    triangle_b_start: FloatArray,
    triangle_b_end: FloatArray,
    *,
    tolerance: float = 1e-9,
) -> bool:
    """Detect transverse linear-path vertex-face or edge-edge crossing.

    Candidate times are exact roots of the cubic coplanarity polynomials.
    A root is proper only if its oriented-side polynomial changes sign; an
    isolated tangency therefore remains allowed.
    """
    a_polys = [_linear_polynomial_vector(triangle_a_start[i], triangle_a_end[i]) for i in range(3)]
    b_polys = [_linear_polynomial_vector(triangle_b_start[i], triangle_b_end[i]) for i in range(3)]

    def vertex_face(vertex: list[FloatArray], face: list[list[FloatArray]]) -> bool:
        va = _poly_sub(vertex, face[0])
        edge1 = _poly_sub(face[1], face[0])
        edge2 = _poly_sub(face[2], face[0])
        coefficients = _poly_dot(va, _poly_cross(edge1, edge2))
        for root in _real_unit_roots(coefficients):
            if not _sign_crossing(coefficients, root):
                continue
            point = np.asarray([poly.polyval(root, component) for component in vertex])
            triangle = np.asarray([
                [poly.polyval(root, component) for component in row] for row in face
            ])
            bary = _triangle_barycentric(point, triangle)
            if np.all(bary >= -tolerance) and np.all(bary <= 1.0 + tolerance):
                return True
        return False

    for vertex in a_polys:
        if vertex_face(vertex, b_polys):
            return True
    for vertex in b_polys:
        if vertex_face(vertex, a_polys):
            return True

    edges = ((0, 1), (1, 2), (2, 0))
    for a0, a1 in edges:
        for b0, b1 in edges:
            pa, qa = a_polys[a0], a_polys[a1]
            pb, qb = b_polys[b0], b_polys[b1]
            coefficients = _poly_dot(
                _poly_sub(pb, pa),
                _poly_cross(_poly_sub(qa, pa), _poly_sub(qb, pb)),
            )
            for root in _real_unit_roots(coefficients):
                if not _sign_crossing(coefficients, root):
                    continue
                p = np.asarray([poly.polyval(root, component) for component in pa])
                q = np.asarray([poly.polyval(root, component) for component in qa])
                r = np.asarray([poly.polyval(root, component) for component in pb])
                s = np.asarray([poly.polyval(root, component) for component in qb])
                u, v = q - p, s - r
                matrix = np.column_stack((u, -v))
                parameters, *_ = np.linalg.lstsq(matrix, r - p, rcond=None)
                if (
                    -tolerance <= parameters[0] <= 1.0 + tolerance
                    and -tolerance <= parameters[1] <= 1.0 + tolerance
                    and np.linalg.norm(p + parameters[0] * u - r - parameters[1] * v) <= tolerance
                ):
                    return True
    return False


def _segment_triangle_transverse(
    start: FloatArray,
    end: FloatArray,
    triangle: FloatArray,
    tolerance: float,
) -> bool:
    a, b, c = triangle
    normal = np.cross(b - a, c - a)
    normal_length = float(np.linalg.norm(normal))
    if normal_length <= 0.0:
        return False
    side_start = float(np.dot(start - a, normal))
    side_end = float(np.dot(end - a, normal))
    side_tolerance = tolerance * normal_length
    if not (
        (side_start < -side_tolerance and side_end > side_tolerance)
        or (side_end < -side_tolerance and side_start > side_tolerance)
    ):
        return False
    fraction = side_start / (side_start - side_end)
    if fraction <= tolerance or fraction >= 1.0 - tolerance:
        return False
    point = start + fraction * (end - start)
    barycentric = _triangle_barycentric(point, triangle)
    return bool(
        np.all(barycentric >= -tolerance)
        and np.all(barycentric <= 1.0 + tolerance)
        and np.count_nonzero(barycentric > tolerance) >= 2
    )


def proper_triangle_intersection_static(
    triangle_a: FloatArray,
    triangle_b: FloatArray,
    *,
    tolerance: float = 1e-10,
) -> bool:
    """True only for a transverse side-sign-changing triangle crossing."""
    for left, right in ((0, 1), (1, 2), (2, 0)):
        if _segment_triangle_transverse(
            triangle_a[left], triangle_a[right], triangle_b, tolerance
        ):
            return True
        if _segment_triangle_transverse(
            triangle_b[left], triangle_b[right], triangle_a, tolerance
        ):
            return True
    return False


def count_surface_pair_proper_intersections(
    vertices_a: FloatArray,
    faces_a: IntArray,
    vertices_b: FloatArray,
    faces_b: IntArray,
    *,
    stop_after_first: bool = False,
) -> int:
    triangles_a = vertices_a[faces_a]
    triangles_b = vertices_b[faces_b]
    minimum_b = triangles_b.min(axis=1)
    maximum_b = triangles_b.max(axis=1)
    count = 0
    for triangle in triangles_a:
        minimum_a, maximum_a = triangle.min(axis=0), triangle.max(axis=0)
        candidates = np.flatnonzero(np.all(
            (maximum_b >= minimum_a) & (minimum_b <= maximum_a), axis=1
        ))
        for candidate in candidates:
            if proper_triangle_intersection_static(triangle, triangles_b[candidate]):
                count += 1
                if stop_after_first:
                    return count
    return count


def count_surface_self_intersections(
    vertices: FloatArray,
    faces: IntArray,
    *,
    stop_after_first: bool = False,
) -> int:
    triangles = vertices[faces]
    minimum = triangles.min(axis=1)
    maximum = triangles.max(axis=1)
    count = 0
    for first in range(len(faces)):
        candidates = np.flatnonzero(
            (np.arange(len(faces)) > first)
            & np.all((maximum >= minimum[first]) & (minimum <= maximum[first]), axis=1)
        )
        first_vertices = set(faces[first].tolist())
        for second in candidates:
            if first_vertices.intersection(faces[second].tolist()):
                continue
            if proper_triangle_intersection_static(triangles[first], triangles[second]):
                count += 1
                if stop_after_first:
                    return count
    return count
