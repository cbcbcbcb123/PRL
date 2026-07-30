"""Passive closed-surface DCM energy and analytic nodal forces."""

from __future__ import annotations

from dataclasses import dataclass
import math

import numpy as np
from numpy.typing import NDArray

from .geometry import triangle_geometry


FloatArray = NDArray[np.float64]
IntArray = NDArray[np.int64]


@dataclass(frozen=True)
class HingeReference:
    vertices: IntArray
    theta0: FloatArray


@dataclass(frozen=True)
class CellReference:
    vertices: FloatArray
    faces: IntArray
    primary: IntArray
    directional: IntArray
    area_group_keys: IntArray
    area0: FloatArray
    volume0: float
    hinges: HingeReference


def _unit(vector: FloatArray) -> tuple[FloatArray, float]:
    length = float(np.linalg.norm(vector))
    if length <= 0.0:
        raise ValueError("degenerate geometric primitive")
    return vector / length, length


def triangle_area_gradients(a: FloatArray, b: FloatArray, c: FloatArray) -> tuple[float, FloatArray]:
    normal, twice_area = _unit(np.cross(b - a, c - a))
    gradients = np.asarray([
        0.5 * np.cross(b - c, normal),
        0.5 * np.cross(c - a, normal),
        0.5 * np.cross(a - b, normal),
    ])
    return 0.5 * twice_area, gradients


def surface_volume_and_gradient(vertices: FloatArray, faces: IntArray) -> tuple[float, FloatArray]:
    gradient = np.zeros_like(vertices)
    volume = 0.0
    for face in faces:
        a, b, c = vertices[face]
        volume += float(np.dot(a, np.cross(b, c))) / 6.0
        gradient[face[0]] += np.cross(b, c) / 6.0
        gradient[face[1]] += np.cross(c, a) / 6.0
        gradient[face[2]] += np.cross(a, b) / 6.0
    return volume, gradient


def _hinge_angle_gradient(local: FloatArray) -> tuple[float, FloatArray]:
    """Oriented angle and its reverse-mode gradient for [x0,x1,x2,x3].

    Faces are (x0,x1,x2) and (x1,x0,x3), so their shared edge is oppositely
    oriented as required by an outward manifold.
    """
    x0, x1, x2, x3 = local
    edge = x1 - x0
    tangent, edge_length = _unit(edge)
    raw0 = np.cross(x1 - x0, x2 - x0)
    raw1 = np.cross(x0 - x1, x3 - x1)
    normal0, length0 = _unit(raw0)
    normal1, length1 = _unit(raw1)
    sine = float(np.dot(tangent, np.cross(normal0, normal1)))
    cosine = float(np.dot(normal0, normal1))
    theta = math.atan2(sine, cosine)
    denominator = sine * sine + cosine * cosine
    sine_bar = cosine / denominator
    cosine_bar = -sine / denominator
    tangent_bar = sine_bar * np.cross(normal0, normal1)
    normal0_bar = sine_bar * np.cross(normal1, tangent) + cosine_bar * normal1
    normal1_bar = sine_bar * np.cross(tangent, normal0) + cosine_bar * normal0
    raw0_bar = (normal0_bar - normal0 * np.dot(normal0, normal0_bar)) / length0
    raw1_bar = (normal1_bar - normal1 * np.dot(normal1, normal1_bar)) / length1
    edge_bar = (tangent_bar - tangent * np.dot(tangent, tangent_bar)) / edge_length
    gradient = np.zeros((4, 3), dtype=np.float64)

    left0, right0 = x1 - x0, x2 - x0
    left0_bar = np.cross(right0, raw0_bar)
    right0_bar = np.cross(raw0_bar, left0)
    gradient[1] += left0_bar
    gradient[2] += right0_bar
    gradient[0] -= left0_bar + right0_bar

    left1, right1 = x0 - x1, x3 - x1
    left1_bar = np.cross(right1, raw1_bar)
    right1_bar = np.cross(raw1_bar, left1)
    gradient[0] += left1_bar
    gradient[3] += right1_bar
    gradient[1] -= left1_bar + right1_bar

    gradient[1] += edge_bar
    gradient[0] -= edge_bar
    return theta, gradient


def build_hinges(vertices: FloatArray, faces: IntArray) -> HingeReference:
    owners: dict[tuple[int, int], list[tuple[int, int, int]]] = {}
    for face_id, (a, b, c) in enumerate(faces.tolist()):
        for left, right, opposite in ((a, b, c), (b, c, a), (c, a, b)):
            owners.setdefault((min(left, right), max(left, right)), []).append(
                (face_id, left, right, opposite)
            )
    hinge_vertices: list[list[int]] = []
    theta0: list[float] = []
    for edge in sorted(owners):
        records = owners[edge]
        if len(records) != 2:
            raise ValueError(f"nonmanifold edge {edge}")
        first = records[0]
        second = records[1]
        if first[1] != second[2] or first[2] != second[1]:
            raise ValueError(f"inconsistent face orientation at edge {edge}")
        local_ids = [first[1], first[2], first[3], second[3]]
        angle, _ = _hinge_angle_gradient(vertices[local_ids])
        hinge_vertices.append(local_ids)
        theta0.append(angle)
    return HingeReference(
        np.asarray(hinge_vertices, dtype=np.int64),
        np.asarray(theta0, dtype=np.float64),
    )


def build_cell_reference(
    vertices: FloatArray,
    faces: IntArray,
    primary: IntArray,
    directional: IntArray,
) -> CellReference:
    group_codes = primary * 10 + directional
    group_keys = np.unique(group_codes)
    face_areas, _ = triangle_geometry(vertices, faces)
    area0 = np.asarray([face_areas[group_codes == key].sum() for key in group_keys])
    volume0, _ = surface_volume_and_gradient(vertices, faces)
    if volume0 <= 0.0:
        raise ValueError("reference cell volume must be positive")
    return CellReference(
        vertices=np.asarray(vertices, dtype=np.float64).copy(),
        faces=np.asarray(faces, dtype=np.int64).copy(),
        primary=np.asarray(primary, dtype=np.int64).copy(),
        directional=np.asarray(directional, dtype=np.int64).copy(),
        area_group_keys=np.asarray(group_keys, dtype=np.int64),
        area0=area0,
        volume0=volume0,
        hinges=build_hinges(vertices, faces),
    )


def area_energy_gradient(
    vertices: FloatArray,
    reference: CellReference,
    k_area: float,
) -> tuple[float, FloatArray]:
    group_codes = reference.primary * 10 + reference.directional
    face_areas = np.empty(len(reference.faces), dtype=np.float64)
    face_gradients = np.empty((len(reference.faces), 3, 3), dtype=np.float64)
    for face_id, face in enumerate(reference.faces):
        face_areas[face_id], face_gradients[face_id] = triangle_area_gradients(
            *vertices[face]
        )
    energy = 0.0
    gradient = np.zeros_like(vertices)
    for key, target in zip(reference.area_group_keys, reference.area0, strict=True):
        selected = np.flatnonzero(group_codes == key)
        area = float(face_areas[selected].sum())
        strain = area / target - 1.0
        energy += 0.5 * k_area * target * strain * strain
        coefficient = k_area * strain
        for face_id in selected:
            gradient[reference.faces[face_id]] += coefficient * face_gradients[face_id]
    return energy, gradient


def volume_energy_gradient(
    vertices: FloatArray,
    reference: CellReference,
    k_volume: float,
) -> tuple[float, FloatArray]:
    volume, volume_gradient = surface_volume_and_gradient(vertices, reference.faces)
    strain = volume / reference.volume0 - 1.0
    energy = 0.5 * k_volume * reference.volume0 * strain * strain
    return energy, k_volume * strain * volume_gradient


def bending_energy_gradient(
    vertices: FloatArray,
    reference: CellReference,
    k_bend: float,
) -> tuple[float, FloatArray]:
    energy = 0.0
    gradient = np.zeros_like(vertices)
    for hinge_id, local_ids in enumerate(reference.hinges.vertices):
        local = vertices[local_ids]
        angle, angle_gradient = _hinge_angle_gradient(local)
        delta = math.atan2(
            math.sin(angle - reference.hinges.theta0[hinge_id]),
            math.cos(angle - reference.hinges.theta0[hinge_id]),
        )
        edge = local[1] - local[0]
        edge_length = float(np.linalg.norm(edge))
        area0, area_gradient0 = triangle_area_gradients(local[0], local[1], local[2])
        area1_raw, raw_gradient1 = triangle_area_gradients(local[1], local[0], local[3])
        area_diamond = area0 + area1_raw
        prefactor = edge_length * edge_length / area_diamond
        energy += 0.5 * k_bend * prefactor * delta * delta

        prefactor_gradient = np.zeros((4, 3), dtype=np.float64)
        edge_direction = edge / edge_length
        prefactor_gradient[1] += 2.0 * edge_length * edge_direction / area_diamond
        prefactor_gradient[0] -= 2.0 * edge_length * edge_direction / area_diamond
        diamond_gradient = np.zeros((4, 3), dtype=np.float64)
        diamond_gradient[[0, 1, 2]] += area_gradient0
        diamond_gradient[[1, 0, 3]] += raw_gradient1
        prefactor_gradient -= (
            edge_length * edge_length / (area_diamond * area_diamond)
        ) * diamond_gradient
        local_gradient = (
            0.5 * k_bend * delta * delta * prefactor_gradient
            + k_bend * prefactor * delta * angle_gradient
        )
        for local_id, global_id in enumerate(local_ids):
            gradient[global_id] += local_gradient[local_id]
    return energy, gradient


def passive_energy_force(
    vertices: FloatArray,
    reference: CellReference,
    *,
    k_area: float = 1.0,
    k_bend: float = 0.01,
    k_volume: float = 100.0,
) -> tuple[dict[str, float], FloatArray]:
    area, area_gradient = area_energy_gradient(vertices, reference, k_area)
    bend, bend_gradient = bending_energy_gradient(vertices, reference, k_bend)
    volume, volume_gradient = volume_energy_gradient(vertices, reference, k_volume)
    energies = {
        "cell_area": area,
        "cell_bend": bend,
        "cell_volume": volume,
        "cell_total": area + bend + volume,
    }
    return energies, -(area_gradient + bend_gradient + volume_gradient)


def nodal_drag_dissipation(velocity: FloatArray, dual_weights: FloatArray, drag: float = 1.0) -> float:
    return float(drag * np.sum(dual_weights[:, None] * velocity * velocity))

