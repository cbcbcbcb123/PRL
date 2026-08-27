"""Stage 2 preferred-length activation and objective single-cell metrics."""

from __future__ import annotations

from dataclasses import dataclass
import math

import numpy as np
from numpy.typing import NDArray

from .geometry import triangle_geometry


FloatArray = NDArray[np.float64]
IntArray = NDArray[np.int64]


@dataclass(frozen=True)
class ActiveReference:
    vertices: FloatArray
    minus_weights: FloatArray
    plus_weights: FloatArray
    length0: float
    axis0: FloatArray


@dataclass(frozen=True)
class ActiveState:
    length: float
    axis: FloatArray
    preferred_length: float
    preferred_length_rate: float
    alpha: float
    alpha_rate: float


def base_envelope(time: float) -> tuple[float, float]:
    """Return the frozen C1 activation envelope and its time derivative."""
    if time < 1.0 or time >= 4.0:
        return 0.0, 0.0
    if time < 2.0:
        phase = math.pi * (time - 1.0)
        return 0.5 * (1.0 - math.cos(phase)), 0.5 * math.pi * math.sin(phase)
    if time < 3.0:
        return 1.0, 0.0
    phase = math.pi * (time - 3.0)
    return 0.5 * (1.0 + math.cos(phase)), -0.5 * math.pi * math.sin(phase)


def activation_protocol(
    time: float,
    *,
    delay: float = 0.0,
    alpha_peak: float = 0.1,
) -> tuple[float, float]:
    envelope, envelope_rate = base_envelope(time - delay)
    return alpha_peak * envelope, alpha_peak * envelope_rate


def _anchor_vertex_weights(
    vertices: FloatArray,
    faces: IntArray,
    face_ids: IntArray,
) -> FloatArray:
    if len(face_ids) == 0:
        raise ValueError("active anchor patch must be nonempty")
    areas, _ = triangle_geometry(vertices, faces)
    weights = np.zeros(len(vertices), dtype=np.float64)
    for face_id in face_ids:
        weights[faces[face_id]] += areas[face_id] / 3.0
    total = float(weights.sum())
    if total <= 0.0:
        raise ValueError("active anchor weights must have positive sum")
    return weights / total


def build_active_reference(
    vertices: FloatArray,
    faces: IntArray,
    minus_face_ids: IntArray,
    plus_face_ids: IntArray,
) -> ActiveReference:
    minus = _anchor_vertex_weights(vertices, faces, minus_face_ids)
    plus = _anchor_vertex_weights(vertices, faces, plus_face_ids)
    difference = plus @ vertices - minus @ vertices
    length0 = float(np.linalg.norm(difference))
    if length0 <= 0.0:
        raise ValueError("active anchor length must be positive")
    return ActiveReference(
        vertices=np.asarray(vertices, dtype=np.float64).copy(),
        minus_weights=minus,
        plus_weights=plus,
        length0=length0,
        axis0=difference / length0,
    )


def anchor_length_axis(
    vertices: FloatArray,
    reference: ActiveReference,
) -> tuple[float, FloatArray]:
    difference = (
        reference.plus_weights @ vertices
        - reference.minus_weights @ vertices
    )
    length = float(np.linalg.norm(difference))
    if length <= 0.0:
        raise ValueError("active anchor length became nonpositive")
    return length, difference / length


def active_energy_force(
    vertices: FloatArray,
    reference: ActiveReference,
    *,
    alpha: float,
    alpha_rate: float = 0.0,
    k_f: float = 10.0,
    alpha_limit: float = 0.2,
) -> tuple[float, FloatArray, ActiveState]:
    if not math.isfinite(alpha_limit) or alpha_limit <= 0.0:
        raise ValueError("activation limit must be finite and positive")
    if not math.isfinite(alpha) or not 0.0 <= alpha <= alpha_limit:
        raise ValueError(
            f"activation must remain inside [0,{alpha_limit:g}]"
        )
    length, axis = anchor_length_axis(vertices, reference)
    preferred = reference.length0 * (1.0 - alpha)
    preferred_rate = -reference.length0 * alpha_rate
    mismatch = length - preferred
    energy = 0.5 * k_f * mismatch * mismatch
    coefficient = k_f * mismatch
    force = (
        coefficient * reference.minus_weights[:, None] * axis[None, :]
        - coefficient * reference.plus_weights[:, None] * axis[None, :]
    )
    return (
        energy,
        force,
        ActiveState(
            length=length,
            axis=axis,
            preferred_length=preferred,
            preferred_length_rate=preferred_rate,
            alpha=alpha,
            alpha_rate=alpha_rate,
        ),
    )


def active_input_power(
    state: ActiveState,
    *,
    k_f: float = 10.0,
) -> float:
    return float(
        -k_f
        * (state.length - state.preferred_length)
        * state.preferred_length_rate
    )


def weighted_centroid(
    vertices: FloatArray,
    weights: FloatArray,
) -> FloatArray:
    total = float(weights.sum())
    if total <= 0.0 or len(weights) != len(vertices):
        raise ValueError("invalid objective-metric weights")
    return np.sum(weights[:, None] * vertices, axis=0) / total


def _transverse_eigenvalues(
    vertices: FloatArray,
    axis: FloatArray,
    weights: FloatArray,
) -> FloatArray:
    centroid = weighted_centroid(vertices, weights)
    centered = vertices - centroid
    covariance = (
        (weights[:, None] * centered).T @ centered / float(weights.sum())
    )
    projector = np.eye(3) - np.outer(axis, axis)
    projected = projector @ covariance @ projector
    eigenvalues = np.linalg.eigvalsh(0.5 * (projected + projected.T))
    transverse = np.asarray(eigenvalues[-2:][::-1], dtype=np.float64)
    if np.any(transverse <= 0.0):
        raise ValueError("transverse covariance is not positive")
    return transverse


def transverse_scale_changes(
    vertices: FloatArray,
    reference: ActiveReference,
    dual_weights: FloatArray,
) -> FloatArray:
    _, axis = anchor_length_axis(vertices, reference)
    current = _transverse_eigenvalues(vertices, axis, dual_weights)
    target = _transverse_eigenvalues(
        reference.vertices,
        reference.axis0,
        dual_weights,
    )
    return np.sqrt(current / target) - 1.0
