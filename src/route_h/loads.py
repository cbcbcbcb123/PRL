"""Blood traction ports and fixed-reference Kelvin–Voigt supports."""

from __future__ import annotations

import numpy as np
from numpy.typing import NDArray

from .geometry import triangle_geometry


FloatArray = NDArray[np.float64]
IntArray = NDArray[np.int64]


def blood_nodal_force(
    vertices: FloatArray,
    faces: IntArray,
    face_ids: IntArray,
    *,
    pressure: float = 0.0,
    wss_command: FloatArray | None = None,
) -> tuple[FloatArray, FloatArray]:
    """Assemble pressure and WSS from one current-area barycenter block."""
    if wss_command is None:
        wss_command = np.zeros(3)
    pressure_force = np.zeros_like(vertices)
    wss_force = np.zeros_like(vertices)
    selected_faces = faces[face_ids]
    areas, normals = triangle_geometry(vertices, selected_faces)
    for local_id, face in enumerate(selected_faces):
        normal = normals[local_id]
        pressure_traction = -pressure * normal
        wss_traction = wss_command - normal * np.dot(normal, wss_command)
        pressure_force[face] += areas[local_id] * pressure_traction / 3.0
        wss_force[face] += areas[local_id] * wss_traction / 3.0
    return pressure_force, wss_force


def force_power(force: FloatArray, velocity: FloatArray) -> float:
    return float(np.sum(force * velocity))


def face_block_power(
    vertices: FloatArray,
    faces: IntArray,
    face_ids: IntArray,
    velocity: FloatArray,
    traction_by_face: FloatArray,
) -> float:
    selected_faces = faces[face_ids]
    areas, _ = triangle_geometry(vertices, selected_faces)
    face_velocity = velocity[selected_faces].mean(axis=1)
    return float(np.sum(areas[:, None] * traction_by_face * face_velocity))


def support_weights(
    reference_vertices: FloatArray,
    faces: IntArray,
    face_ids: IntArray,
) -> FloatArray:
    selected = faces[face_ids]
    areas, _ = triangle_geometry(reference_vertices, selected)
    weights = np.zeros(len(reference_vertices), dtype=np.float64)
    for face, area in zip(selected, areas, strict=True):
        weights[face] += area / 3.0
    return weights


def kelvin_voigt_support(
    vertices: FloatArray,
    velocity: FloatArray,
    reference_vertices: FloatArray,
    weights: FloatArray,
    stiffness: FloatArray,
    damping: FloatArray,
) -> tuple[float, FloatArray, float]:
    displacement = vertices - reference_vertices
    elastic_product = displacement @ stiffness.T
    damping_product = velocity @ damping.T
    energy = 0.5 * float(np.sum(weights[:, None] * displacement * elastic_product))
    force = -weights[:, None] * (elastic_product + damping_product)
    dissipation = float(np.sum(weights[:, None] * velocity * damping_product))
    return energy, force, dissipation


def flow_sensor_rate(
    chi_e: float,
    wss_command: FloatArray,
    *,
    tau_chi: float = 1.0,
) -> float:
    magnitude = float(np.linalg.norm(wss_command))
    command = magnitude / (1.0 + magnitude)
    return (command - chi_e) / tau_chi

