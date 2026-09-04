"""Read-only decomposition of the frozen Paper 2 M2A v06.1 NO-GO-ID result."""

from __future__ import annotations

import hashlib
import math
from pathlib import Path
from typing import Any

import numpy as np

from .identity_gate_v06 import endpoint_key, relative_difference
from .interface_projection import constant_traction_projection_manufactured_check


HOLDOUT_CASES = ("ID-A2", "ID-LN", "ID-LS", "ID-C0", "ID-CQ", "ID-S1")
PURE_MODE_CASES = ("ID-A2", "ID-LN", "ID-LS")
COMBINED_CASES = ("ID-C0", "ID-CQ")
INTERFACE_KEYS = {
    "myocardium_ecm": "myocardium_ecm_common_traction",
    "endocardium_ecm": "endocardium_ecm_common_traction",
}
FAILED_TRACTION_RECORDS = (
    ("ID-A2", "myocardium_ecm"),
    ("ID-A2", "endocardium_ecm"),
    ("ID-S1", "myocardium_ecm"),
    ("ID-S1", "endocardium_ecm"),
)
COMPONENT_NAMES = ("x", "y")
NORM_FLOOR = 1.0e-10
PARSEVAL_TOLERANCE = 1.0e-12
DIAGNOSTIC_PASS_TOLERANCE = 0.05
MODE_MISMATCH_THRESHOLD = 0.15


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def finite_tree(value: Any) -> bool:
    if isinstance(value, float):
        return math.isfinite(value)
    if isinstance(value, dict):
        return all(finite_tree(item) for item in value.values())
    if isinstance(value, (list, tuple)):
        return all(finite_tree(item) for item in value)
    return True


def common_widths(common_x: np.ndarray) -> np.ndarray:
    coordinates = np.asarray(common_x, dtype=np.float64)
    widths = np.diff(coordinates)
    if coordinates.ndim != 1 or len(coordinates) != 65:
        raise ValueError("v07 requires exactly 64 common interface segments")
    if np.any(widths <= 0.0):
        raise ValueError("common interface coordinates must be strictly increasing")
    return widths


def weighted_space_time_inner(
    value_a: np.ndarray, value_b: np.ndarray, widths: np.ndarray
) -> complex:
    value_a = np.asarray(value_a)
    value_b = np.asarray(value_b)
    widths = np.asarray(widths, dtype=np.float64)
    if value_a.shape != value_b.shape or value_a.ndim not in (2, 3):
        raise ValueError("space-time inputs must share shape (space[, component], time)")
    if value_a.shape[0] != widths.size:
        raise ValueError("space weights do not match the first array axis")
    weight_shape = (widths.size,) + (1,) * (value_a.ndim - 1)
    return complex(
        np.sum(
            widths.reshape(weight_shape) * np.conjugate(value_a) * value_b
        )
        / value_a.shape[-1]
    )


def weighted_space_inner(
    value_a: np.ndarray, value_b: np.ndarray, widths: np.ndarray
) -> complex:
    value_a = np.asarray(value_a)
    value_b = np.asarray(value_b)
    widths = np.asarray(widths, dtype=np.float64)
    if value_a.shape != value_b.shape or value_a.ndim not in (1, 2):
        raise ValueError("spatial inputs must share shape (space[, component])")
    if value_a.shape[0] != widths.size:
        raise ValueError("space weights do not match the first array axis")
    weight_shape = (widths.size,) + (1,) * (value_a.ndim - 1)
    return complex(
        np.sum(widths.reshape(weight_shape) * np.conjugate(value_a) * value_b)
    )


def temporal_inner(value_a: np.ndarray, value_b: np.ndarray) -> complex:
    value_a = np.asarray(value_a)
    value_b = np.asarray(value_b)
    if value_a.shape != value_b.shape or value_a.ndim != 1:
        raise ValueError("temporal inputs must be one-dimensional and shape matched")
    return complex(np.mean(np.conjugate(value_a) * value_b))


def _norm_from_inner(value: complex) -> float:
    return float(math.sqrt(max(float(value.real), 0.0)))


def weighted_space_time_norm(value: np.ndarray, widths: np.ndarray) -> float:
    return _norm_from_inner(weighted_space_time_inner(value, value, widths))


def weighted_space_norm(value: np.ndarray, widths: np.ndarray) -> float:
    return _norm_from_inner(weighted_space_inner(value, value, widths))


def temporal_norm(value: np.ndarray) -> float:
    return _norm_from_inner(temporal_inner(value, value))


def _space_time_relative_difference(
    value_a: np.ndarray,
    value_b: np.ndarray,
    widths: np.ndarray,
    floor: float = NORM_FLOOR,
) -> float:
    return weighted_space_time_norm(value_a - value_b, widths) / max(
        weighted_space_time_norm(value_a, widths),
        weighted_space_time_norm(value_b, widths),
        floor,
    )


def _space_relative_difference(
    value_a: np.ndarray,
    value_b: np.ndarray,
    widths: np.ndarray,
    floor: float = NORM_FLOOR,
) -> float:
    return weighted_space_norm(value_a - value_b, widths) / max(
        weighted_space_norm(value_a, widths),
        weighted_space_norm(value_b, widths),
        floor,
    )


def _temporal_relative_difference(
    value_a: np.ndarray, value_b: np.ndarray, floor: float = NORM_FLOOR
) -> float:
    return temporal_norm(value_a - value_b) / max(
        temporal_norm(value_a), temporal_norm(value_b), floor
    )


def _space_time_difference_record(
    value_a: np.ndarray,
    value_b: np.ndarray,
    widths: np.ndarray,
    floor: float = NORM_FLOOR,
) -> dict[str, Any]:
    norm_a = weighted_space_time_norm(value_a, widths)
    norm_b = weighted_space_time_norm(value_b, widths)
    absolute = weighted_space_time_norm(value_a - value_b, widths)
    near_zero = max(norm_a, norm_b) <= floor
    return {
        "status": "NEAR_ZERO_COMPONENT" if near_zero else "FINITE_COMPONENT",
        "dcm_norm": norm_a,
        "fem_norm": norm_b,
        "absolute_difference_norm": absolute,
        "normalized_l2_difference": None
        if near_zero
        else absolute / max(norm_a, norm_b, floor),
    }


def _space_difference_record(
    value_a: np.ndarray,
    value_b: np.ndarray,
    widths: np.ndarray,
    floor: float = NORM_FLOOR,
) -> dict[str, Any]:
    norm_a = weighted_space_norm(value_a, widths)
    norm_b = weighted_space_norm(value_b, widths)
    absolute = weighted_space_norm(value_a - value_b, widths)
    near_zero = max(norm_a, norm_b) <= floor
    return {
        "status": "NEAR_ZERO_COMPONENT" if near_zero else "FINITE_COMPONENT",
        "dcm_norm": norm_a,
        "fem_norm": norm_b,
        "absolute_difference_norm": absolute,
        "normalized_l2_difference": None
        if near_zero
        else absolute / max(norm_a, norm_b, floor),
    }


def _complex_payload(value: complex) -> dict[str, float]:
    return {"real": float(value.real), "imag": float(value.imag)}


def _complex_field_payload(value: np.ndarray) -> dict[str, Any]:
    array = np.asarray(value, dtype=np.complex128)
    if array.ndim == 0:
        return _complex_payload(complex(array))
    return {"real": array.real.tolist(), "imag": array.imag.tolist()}


def _real_field_payload(value: np.ndarray | float) -> float | list[float]:
    array = np.asarray(value, dtype=np.float64)
    return float(array) if array.ndim == 0 else array.tolist()


def _dominance_label(shares: dict[str, float], threshold: float = 0.60) -> str:
    if not shares or max(shares.values()) < threshold:
        return "UNRESOLVED_MIXTURE"
    return max(shares, key=shares.get)


def component_record(
    dcm: np.ndarray,
    fem: np.ndarray,
    widths: np.ndarray,
    *,
    total_dcm_energy: float,
    total_fem_energy: float,
    floor: float = NORM_FLOOR,
) -> dict[str, Any]:
    dcm_norm = weighted_space_time_norm(dcm, widths)
    fem_norm = weighted_space_time_norm(fem, widths)
    near_zero = max(dcm_norm, fem_norm) <= floor
    if near_zero:
        return {
            "status": "NEAR_ZERO_COMPONENT",
            "dcm_norm": dcm_norm,
            "fem_norm": fem_norm,
            "absolute_difference_norm": weighted_space_time_norm(dcm - fem, widths),
            "normalized_l2_difference": None,
            "weighted_cosine": None,
            "dcm_energy_fraction": 0.0
            if total_dcm_energy <= floor**2
            else dcm_norm**2 / total_dcm_energy,
            "fem_energy_fraction": 0.0
            if total_fem_energy <= floor**2
            else fem_norm**2 / total_fem_energy,
        }
    inner = weighted_space_time_inner(dcm, fem, widths)
    cosine = float(inner.real / max(dcm_norm * fem_norm, floor**2))
    return {
        "status": "FINITE_COMPONENT",
        "dcm_norm": dcm_norm,
        "fem_norm": fem_norm,
        "absolute_difference_norm": weighted_space_time_norm(dcm - fem, widths),
        "normalized_l2_difference": _space_time_relative_difference(
            dcm, fem, widths, floor
        ),
        "weighted_cosine": float(np.clip(cosine, -1.0, 1.0)),
        "dcm_energy_fraction": dcm_norm**2 / max(total_dcm_energy, floor**2),
        "fem_energy_fraction": fem_norm**2 / max(total_fem_energy, floor**2),
    }


def traction_record_diagnostic(
    *,
    case_id: str,
    interface: str,
    dcm: np.ndarray,
    fem: np.ndarray,
    common_x: np.ndarray,
    floor: float = NORM_FLOOR,
) -> dict[str, Any]:
    dcm = np.asarray(dcm, dtype=np.float64)
    fem = np.asarray(fem, dtype=np.float64)
    if dcm.shape != (64, 2, 256) or fem.shape != dcm.shape:
        raise ValueError("v07 traction records must have shape (64, 2, 256)")
    widths = common_widths(common_x)
    dcm_norm = weighted_space_time_norm(dcm, widths)
    fem_norm = weighted_space_time_norm(fem, widths)
    inner = weighted_space_time_inner(dcm, fem, widths)
    alpha = float(inner.real / max(dcm_norm**2, floor**2))
    scaled_residual = weighted_space_time_norm(fem - alpha * dcm, widths) / max(
        fem_norm, floor
    )
    cosine = float(inner.real / max(dcm_norm * fem_norm, floor**2))
    cosine = float(np.clip(cosine, -1.0, 1.0))
    total_dcm_energy = dcm_norm**2
    total_fem_energy = fem_norm**2
    components = {
        component_name: component_record(
            dcm[:, component_index, :],
            fem[:, component_index, :],
            widths,
            total_dcm_energy=total_dcm_energy,
            total_fem_energy=total_fem_energy,
            floor=floor,
        )
        for component_index, component_name in enumerate(COMPONENT_NAMES)
    }
    average_component_energy = {
        name: 0.5
        * (
            record["dcm_energy_fraction"] + record["fem_energy_fraction"]
        )
        for name, record in components.items()
    }
    return {
        "record_id": f"{case_id}__{interface}",
        "case_id": case_id,
        "interface": interface,
        "array_order": ["space", "component", "time"],
        "component_order": ["x", "y"],
        "dcm_norm": dcm_norm,
        "fem_norm": fem_norm,
        "fem_to_dcm_norm_ratio": fem_norm / max(dcm_norm, floor),
        "normalized_l2_difference": _space_time_relative_difference(
            dcm, fem, widths, floor
        ),
        "weighted_cosine": cosine,
        "vector_direction_error_rad": math.acos(cosine),
        "sign_consistent": bool(cosine >= 0.0 and alpha >= 0.0),
        "per_record_optimal_real_scale": alpha,
        "optimal_scale_residual_over_fem_norm": scaled_residual,
        "dominant_component": max(average_component_energy, key=average_component_energy.get),
        "components": components,
    }


def build_traction_scale_direction_components(
    observations: dict[str, dict[str, dict[str, Any]]]
) -> tuple[dict[str, Any], list[tuple[str, np.ndarray, np.ndarray, np.ndarray]]]:
    records: dict[str, Any] = {}
    failed_arrays: list[tuple[str, np.ndarray, np.ndarray, np.ndarray]] = []
    for case_id in HOLDOUT_CASES:
        for interface, observation_key in INTERFACE_KEYS.items():
            obs_dcm = observations[case_id]["DCM"]
            obs_fem = observations[case_id]["FEM"]
            record = traction_record_diagnostic(
                case_id=case_id,
                interface=interface,
                dcm=obs_dcm[observation_key],
                fem=obs_fem[observation_key],
                common_x=obs_dcm["common_x"],
            )
            records[record["record_id"]] = record
            if (case_id, interface) in FAILED_TRACTION_RECORDS:
                failed_arrays.append(
                    (
                        record["record_id"],
                        obs_dcm[observation_key],
                        obs_fem[observation_key],
                        common_widths(obs_dcm["common_x"]),
                    )
                )

    numerator = sum(
        weighted_space_time_inner(dcm, fem, widths).real
        for _, dcm, fem, widths in failed_arrays
    )
    denominator = sum(
        weighted_space_time_inner(dcm, dcm, widths).real
        for _, dcm, _, widths in failed_arrays
    )
    global_alpha = float(numerator / max(denominator, NORM_FLOOR**2))
    global_records: dict[str, Any] = {}
    for record_id, dcm, fem, widths in failed_arrays:
        fem_norm = weighted_space_time_norm(fem, widths)
        optimal_alpha = records[record_id]["per_record_optimal_real_scale"]
        global_records[record_id] = {
            "global_scale_residual_over_fem_norm": (
                weighted_space_time_norm(fem - global_alpha * dcm, widths)
                / max(fem_norm, NORM_FLOOR)
            ),
            "per_record_optimal_scale": optimal_alpha,
            "optimal_scale_relative_difference_from_global": relative_difference(
                optimal_alpha, global_alpha, NORM_FLOOR
            ),
        }
    global_scale_audit = {
        "record_ids": [record_id for record_id, *_ in failed_arrays],
        "global_optimal_real_scale": global_alpha,
        "records": global_records,
        "all_global_scale_residuals_le_5pct": all(
            record["global_scale_residual_over_fem_norm"]
            <= DIAGNOSTIC_PASS_TOLERANCE
            for record in global_records.values()
        ),
        "all_optimal_scales_within_5pct_of_global": all(
            record["optimal_scale_relative_difference_from_global"]
            <= DIAGNOSTIC_PASS_TOLERANCE
            for record in global_records.values()
        ),
        "diagnostic_only_not_model_parameter": True,
    }
    payload = {
        "schema": "paper2_m2a_v07_traction_scale_direction_components",
        "weighting": {
            "space": "64_common_segment_arc_length",
            "time": "equal_weight_first_T256_cycle",
            "normalization_floor": NORM_FLOOR,
        },
        "records": records,
        "formal_failed_traction_global_scale_audit": global_scale_audit,
    }
    return payload, failed_arrays


def signed_permutation_matrices() -> list[dict[str, Any]]:
    matrices: list[dict[str, Any]] = []
    for swapped in (False, True):
        for first_sign in (-1, 1):
            for second_sign in (-1, 1):
                if swapped:
                    matrix = np.asarray(
                        ((0.0, float(first_sign)), (float(second_sign), 0.0))
                    )
                    name = f"swap__x_from_y_{first_sign:+d}__y_from_x_{second_sign:+d}"
                else:
                    matrix = np.diag((float(first_sign), float(second_sign)))
                    name = f"noswap__x_{first_sign:+d}__y_{second_sign:+d}"
                matrices.append(
                    {
                        "name": name,
                        "matrix": matrix,
                        "is_identity": bool(np.array_equal(matrix, np.eye(2))),
                    }
                )
    return matrices


def _apply_component_basis(matrix: np.ndarray, field: np.ndarray) -> np.ndarray:
    return np.einsum("ab,sbt->sat", matrix, field)


def build_signed_permutation_basis_audit(
    failed_arrays: list[tuple[str, np.ndarray, np.ndarray, np.ndarray]]
) -> dict[str, Any]:
    candidates: dict[str, Any] = {}
    for candidate in signed_permutation_matrices():
        matrix = candidate["matrix"]
        per_record: dict[str, float] = {}
        total_difference_energy = 0.0
        total_dcm_energy = 0.0
        total_fem_energy = 0.0
        for record_id, dcm, fem, widths in failed_arrays:
            transformed = _apply_component_basis(matrix, dcm)
            per_record[record_id] = _space_time_relative_difference(
                transformed, fem, widths
            )
            total_difference_energy += weighted_space_time_norm(
                transformed - fem, widths
            ) ** 2
            total_dcm_energy += weighted_space_time_norm(transformed, widths) ** 2
            total_fem_energy += weighted_space_time_norm(fem, widths) ** 2
        candidates[candidate["name"]] = {
            "matrix": matrix.tolist(),
            "is_identity": candidate["is_identity"],
            "per_record_normalized_l2": per_record,
            "maximum_record_residual": max(per_record.values()),
            "global_concatenated_residual": math.sqrt(total_difference_energy)
            / max(math.sqrt(total_dcm_energy), math.sqrt(total_fem_energy), NORM_FLOOR),
        }
    best_name = min(
        candidates,
        key=lambda name: (
            candidates[name]["global_concatenated_residual"],
            candidates[name]["maximum_record_residual"],
            name,
        ),
    )
    per_record_best: dict[str, Any] = {}
    for record_id, *_ in failed_arrays:
        record_best = min(
            candidates,
            key=lambda name: candidates[name]["per_record_normalized_l2"][record_id],
        )
        per_record_best[record_id] = {
            "matrix_name": record_best,
            "matrix": candidates[record_best]["matrix"],
            "normalized_l2_residual": candidates[record_best][
                "per_record_normalized_l2"
            ][record_id],
        }
    best = candidates[best_name]
    return {
        "schema": "paper2_m2a_v07_signed_permutation_basis_audit",
        "candidate_count": len(candidates),
        "general_rotation_or_affine_search_used": False,
        "matrices_applied_to": "complete_DCM_traction_vector_only",
        "candidates": candidates,
        "per_record_best": per_record_best,
        "common_best": {
            "matrix_name": best_name,
            **best,
            "is_nonidentity": not best["is_identity"],
            "all_failed_traction_records_le_5pct": (
                best["maximum_record_residual"] <= DIAGNOSTIC_PASS_TOLERANCE
            ),
        },
    }


def _spatial_decomposition(field: np.ndarray, widths: np.ndarray) -> dict[str, np.ndarray]:
    length = float(np.sum(widths))
    spatial_mean = np.sum(widths[:, None] * field, axis=0) / length
    mean_field = np.broadcast_to(spatial_mean[None, :], field.shape).copy()
    return {"mean": mean_field, "heterogeneity": field - mean_field}


def _temporal_decomposition(field: np.ndarray) -> dict[str, np.ndarray]:
    samples = field.shape[-1]
    dc = np.mean(field, axis=-1)
    coefficient = np.fft.rfft(field, axis=-1)[..., 1] / samples
    phase = np.exp(2.0j * np.pi * np.arange(samples) / samples)
    fundamental = 2.0 * np.real(coefficient[..., None] * phase)
    dc_field = np.broadcast_to(dc[..., None], field.shape).copy()
    higher = field - dc_field - fundamental
    return {
        "dc": dc_field,
        "fundamental": fundamental,
        "higher_harmonics": higher,
        "fundamental_complex_field": coefficient,
    }


def _energy_fractions(
    parts: dict[str, np.ndarray], total: np.ndarray, widths: np.ndarray
) -> tuple[dict[str, float], float]:
    total_energy = weighted_space_time_norm(total, widths) ** 2
    part_energy = {
        name: weighted_space_time_norm(field, widths) ** 2
        for name, field in parts.items()
        if name != "fundamental_complex_field"
    }
    closure = abs(sum(part_energy.values()) - total_energy) / max(
        total_energy, NORM_FLOOR**2
    )
    fractions = {
        name: energy / max(total_energy, NORM_FLOOR**2)
        for name, energy in part_energy.items()
    }
    return fractions, closure


def _complex_spatial_comparison(
    dcm: np.ndarray, fem: np.ndarray, widths: np.ndarray
) -> dict[str, Any]:
    dcm_norm = weighted_space_norm(dcm, widths)
    fem_norm = weighted_space_norm(fem, widths)
    near_zero = max(dcm_norm, fem_norm) <= NORM_FLOOR
    applicable = min(dcm_norm, fem_norm) > NORM_FLOOR
    correlation = (
        weighted_space_inner(dcm, fem, widths) / (dcm_norm * fem_norm)
        if applicable
        else 0.0j
    )
    return {
        "dcm_norm": dcm_norm,
        "fem_norm": fem_norm,
        "fem_to_dcm_amplitude_ratio": fem_norm / max(dcm_norm, NORM_FLOOR),
        "status": "NEAR_ZERO_COMPONENT" if near_zero else "FINITE_COMPONENT",
        "absolute_complex_field_difference_norm": weighted_space_norm(
            dcm - fem, widths
        ),
        "normalized_complex_field_difference": None
        if near_zero
        else _space_relative_difference(dcm, fem, widths),
        "weighted_complex_correlation": _complex_payload(complex(correlation)),
        "weighted_complex_correlation_magnitude": abs(complex(correlation)),
        "absolute_phase_difference_rad": abs(float(np.angle(correlation)))
        if applicable
        else None,
        "applicable": applicable,
    }


def mode_decomposition_record(
    *,
    case_id: str,
    interface: str,
    component: str,
    dcm: np.ndarray,
    fem: np.ndarray,
    common_x: np.ndarray,
) -> dict[str, Any]:
    widths = common_widths(common_x)
    spatial_dcm = _spatial_decomposition(dcm, widths)
    spatial_fem = _spatial_decomposition(fem, widths)
    spatial_fractions_dcm, spatial_closure_dcm = _energy_fractions(
        spatial_dcm, dcm, widths
    )
    spatial_fractions_fem, spatial_closure_fem = _energy_fractions(
        spatial_fem, fem, widths
    )
    spatial_difference_energies = {
        name: weighted_space_time_norm(
            spatial_dcm[name] - spatial_fem[name], widths
        )
        ** 2
        for name in ("mean", "heterogeneity")
    }
    spatial_difference_total = sum(spatial_difference_energies.values())
    spatial_difference_shares = {
        name: energy / max(spatial_difference_total, NORM_FLOOR**2)
        for name, energy in spatial_difference_energies.items()
    }

    temporal_dcm = _temporal_decomposition(dcm)
    temporal_fem = _temporal_decomposition(fem)
    temporal_fractions_dcm, temporal_closure_dcm = _energy_fractions(
        temporal_dcm, dcm, widths
    )
    temporal_fractions_fem, temporal_closure_fem = _energy_fractions(
        temporal_fem, fem, widths
    )
    temporal_names = ("dc", "fundamental", "higher_harmonics")
    temporal_difference_energies = {
        name: weighted_space_time_norm(
            temporal_dcm[name] - temporal_fem[name], widths
        )
        ** 2
        for name in temporal_names
    }
    temporal_difference_total = sum(temporal_difference_energies.values())
    temporal_difference_shares = {
        name: energy / max(temporal_difference_total, NORM_FLOOR**2)
        for name, energy in temporal_difference_energies.items()
    }
    full_difference = _space_time_difference_record(dcm, fem, widths)
    return {
        "record_id": f"{case_id}__{interface}__{component}",
        "case_id": case_id,
        "interface": interface,
        "component": component,
        "full_component_difference": full_difference,
        "spatial": {
            "dcm_energy_fractions": spatial_fractions_dcm,
            "fem_energy_fractions": spatial_fractions_fem,
            "dcm_energy_closure_relative_error": spatial_closure_dcm,
            "fem_energy_closure_relative_error": spatial_closure_fem,
            "mean_field_difference": _space_time_difference_record(
                spatial_dcm["mean"], spatial_fem["mean"], widths
            ),
            "heterogeneity_difference": _space_time_difference_record(
                spatial_dcm["heterogeneity"], spatial_fem["heterogeneity"], widths
            ),
            "difference_energy_shares": spatial_difference_shares,
            "difference_localization": _dominance_label(spatial_difference_shares),
        },
        "temporal": {
            "dcm_energy_fractions": temporal_fractions_dcm,
            "fem_energy_fractions": temporal_fractions_fem,
            "dcm_parseval_relative_error": temporal_closure_dcm,
            "fem_parseval_relative_error": temporal_closure_fem,
            "dc_difference": _space_time_difference_record(
                temporal_dcm["dc"], temporal_fem["dc"], widths
            ),
            "fundamental_difference": _space_time_difference_record(
                temporal_dcm["fundamental"], temporal_fem["fundamental"], widths
            ),
            "higher_harmonic_difference": _space_time_difference_record(
                temporal_dcm["higher_harmonics"],
                temporal_fem["higher_harmonics"],
                widths,
            ),
            "fundamental_complex_comparison": _complex_spatial_comparison(
                temporal_dcm["fundamental_complex_field"],
                temporal_fem["fundamental_complex_field"],
                widths,
            ),
            "difference_energy_shares": temporal_difference_shares,
            "difference_localization": _dominance_label(temporal_difference_shares),
        },
    }


def build_spatiotemporal_mode_decomposition(
    observations: dict[str, dict[str, dict[str, Any]]]
) -> dict[str, Any]:
    records: dict[str, Any] = {}
    for case_id in HOLDOUT_CASES:
        for interface, observation_key in INTERFACE_KEYS.items():
            obs_dcm = observations[case_id]["DCM"]
            obs_fem = observations[case_id]["FEM"]
            for component_index, component in enumerate(COMPONENT_NAMES):
                record = mode_decomposition_record(
                    case_id=case_id,
                    interface=interface,
                    component=component,
                    dcm=obs_dcm[observation_key][:, component_index, :],
                    fem=obs_fem[observation_key][:, component_index, :],
                    common_x=obs_dcm["common_x"],
                )
                records[record["record_id"]] = record
    parseval_errors = [
        record["temporal"][key]
        for record in records.values()
        for key in ("dcm_parseval_relative_error", "fem_parseval_relative_error")
    ]
    spatial_closure_errors = [
        record["spatial"][key]
        for record in records.values()
        for key in (
            "dcm_energy_closure_relative_error",
            "fem_energy_closure_relative_error",
        )
    ]
    return {
        "schema": "paper2_m2a_v07_spatiotemporal_mode_decomposition",
        "record_count": len(records),
        "records": records,
        "parseval_tolerance": PARSEVAL_TOLERANCE,
        "maximum_parseval_relative_error": max(parseval_errors),
        "maximum_spatial_orthogonality_closure_relative_error": max(
            spatial_closure_errors
        ),
        "all_energy_closures_pass": bool(
            max(parseval_errors + spatial_closure_errors) <= PARSEVAL_TOLERANCE
        ),
    }


def fundamental_coefficient(signal: np.ndarray) -> np.ndarray:
    values = np.asarray(signal)
    return np.fft.rfft(values, axis=-1)[..., 1] / values.shape[-1]


def _scalar_complex_comparison(dcm: complex, fem: complex) -> dict[str, Any]:
    denominator = max(abs(dcm), abs(fem), NORM_FLOOR)
    near_zero = max(abs(dcm), abs(fem)) <= NORM_FLOOR
    return {
        "status": "NEAR_ZERO_COMPONENT" if near_zero else "FINITE_COMPONENT",
        "dcm": _complex_payload(dcm),
        "fem": _complex_payload(fem),
        "dcm_amplitude": 2.0 * abs(dcm),
        "fem_amplitude": 2.0 * abs(fem),
        "absolute_complex_difference": abs(dcm - fem),
        "normalized_complex_difference": None
        if near_zero
        else abs(dcm - fem) / denominator,
        "absolute_phase_difference_rad": abs(
            float(np.angle(np.exp(1.0j * (np.angle(dcm) - np.angle(fem)))))
        )
        if min(abs(dcm), abs(fem)) > NORM_FLOOR
        else None,
    }


def _scalar_transfer_entry(
    dcm: np.ndarray, fem: np.ndarray, *, unit: str
) -> dict[str, Any]:
    dcm_coefficient = complex(fundamental_coefficient(dcm))
    fem_coefficient = complex(fundamental_coefficient(fem))
    return {
        "unit": unit,
        "fundamental": _scalar_complex_comparison(dcm_coefficient, fem_coefficient),
    }


def _traction_modal_transfer_entry(
    dcm: np.ndarray, fem: np.ndarray, widths: np.ndarray
) -> dict[str, Any]:
    dcm_dc = np.mean(dcm, axis=-1)
    fem_dc = np.mean(fem, axis=-1)
    dcm_c1 = fundamental_coefficient(dcm)
    fem_c1 = fundamental_coefficient(fem)
    dc_difference = _space_difference_record(dcm_dc, fem_dc, widths)
    return {
        "unit": "nondimensional_interface_traction_density",
        "dc_spatial_field": {
            "dcm": _real_field_payload(dcm_dc),
            "fem": _real_field_payload(fem_dc),
            **dc_difference,
        },
        "fundamental_complex_spatial_field": {
            "dcm": _complex_field_payload(dcm_c1),
            "fem": _complex_field_payload(fem_c1),
            **_complex_spatial_comparison(dcm_c1, fem_c1, widths),
        },
    }


def build_pure_mode_transfer_audit(
    observations: dict[str, dict[str, dict[str, Any]]],
    summaries_t256: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    cases: dict[str, Any] = {}
    for case_id in PURE_MODE_CASES:
        dcm = observations[case_id]["DCM"]
        fem = observations[case_id]["FEM"]
        peak_dcm = float(np.max(dcm["limited_shortening"]))
        peak_fem = float(np.max(fem["limited_shortening"]))
        peak_near_zero = max(abs(peak_dcm), abs(peak_fem)) <= 1.0e-6
        entries: dict[str, Any] = {
            "peak_limited_shortening": {
                "unit": "nondimensional_macro_strain",
                "status": "NEAR_ZERO_COMPONENT"
                if peak_near_zero
                else "FINITE_COMPONENT",
                "dcm": peak_dcm,
                "fem": peak_fem,
                "absolute_difference": abs(peak_dcm - peak_fem),
                "relative_difference": None
                if peak_near_zero
                else relative_difference(peak_dcm, peak_fem, 1.0e-6),
            },
            "shortening_fundamental": _scalar_transfer_entry(
                dcm["limited_shortening"],
                fem["limited_shortening"],
                unit="nondimensional_macro_strain",
            ),
            "normal_displacement_fundamental": _scalar_transfer_entry(
                dcm["mean_endocardial_normal_displacement"],
                fem["mean_endocardial_normal_displacement"],
                unit="nondimensional_length",
            ),
            "tangential_displacement_fundamental": _scalar_transfer_entry(
                dcm["mean_endocardial_tangential_displacement"],
                fem["mean_endocardial_tangential_displacement"],
                unit="nondimensional_length",
            ),
        }
        widths = common_widths(dcm["common_x"])
        for interface, observation_key in INTERFACE_KEYS.items():
            entries[interface] = {
                component: _traction_modal_transfer_entry(
                    dcm[observation_key][:, component_index, :],
                    fem[observation_key][:, component_index, :],
                    widths,
                )
                for component_index, component in enumerate(COMPONENT_NAMES)
            }
        dcm_summary = summaries_t256[endpoint_key(case_id, "DCM", "S4", 256)]
        fem_summary = summaries_t256[endpoint_key(case_id, "FEM", "S4", 256)]
        dcm_dissipation = float(
            dcm_summary["ledger"]["total_drag_dissipation"]
            + dcm_summary["ledger"]["total_sls_dissipation"]
        )
        fem_dissipation = float(
            fem_summary["ledger"]["total_drag_dissipation"]
            + fem_summary["ledger"]["total_sls_dissipation"]
        )
        dcm_storage = float(dcm_summary["ledger"]["cycle_energy_change"])
        fem_storage = float(fem_summary["ledger"]["cycle_energy_change"])
        entries["cycle_dissipation"] = {
            "unit": "nondimensional_energy_per_cycle",
            "dcm": dcm_dissipation,
            "fem": fem_dissipation,
            "relative_difference": relative_difference(
                dcm_dissipation, fem_dissipation, NORM_FLOOR
            ),
        }
        entries["cycle_stored_energy_change"] = {
            "unit": "nondimensional_energy",
            "dcm": dcm_storage,
            "fem": fem_storage,
            "absolute_difference": abs(dcm_storage - fem_storage),
            "comparison_rule": "absolute_near_zero",
        }
        cases[case_id] = {
            "mode": {
                "ID-A2": "pure_active",
                "ID-LN": "pure_normal_load",
                "ID-LS": "pure_tangential_load",
            }[case_id],
            "entries": entries,
        }
    return {
        "schema": "paper2_m2a_v07_pure_mode_transfer_audit",
        "units_system": "nondimensional_M2A_identity_benchmark",
        "different_physical_quantities_combined_into_one_norm": False,
        "cases": cases,
    }


def _modal_field(values: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    array = np.asarray(values)
    return np.mean(array, axis=-1), fundamental_coefficient(array)


def _field_norm(value: np.ndarray | complex, widths: np.ndarray | None) -> float:
    array = np.asarray(value)
    if array.ndim == 0:
        return float(abs(complex(array)))
    if widths is None:
        raise ValueError("spatial fields require common-segment weights")
    return weighted_space_norm(array, widths)


def _field_relative_difference(
    value_a: np.ndarray | complex,
    value_b: np.ndarray | complex,
    widths: np.ndarray | None,
) -> float:
    return _field_norm(np.asarray(value_a) - np.asarray(value_b), widths) / max(
        _field_norm(value_a, widths), _field_norm(value_b, widths), NORM_FLOOR
    )


def _field_difference_record(
    value_a: np.ndarray | complex,
    value_b: np.ndarray | complex,
    widths: np.ndarray | None,
    floor: float = NORM_FLOOR,
) -> dict[str, Any]:
    norm_a = _field_norm(value_a, widths)
    norm_b = _field_norm(value_b, widths)
    absolute = _field_norm(np.asarray(value_a) - np.asarray(value_b), widths)
    near_zero = max(norm_a, norm_b) <= floor
    return {
        "status": "NEAR_ZERO_COMPONENT" if near_zero else "FINITE_COMPONENT",
        "observed_norm": norm_a,
        "predicted_norm": norm_b,
        "absolute_difference_norm": absolute,
        "normalized_l2_difference": None
        if near_zero
        else absolute / max(norm_a, norm_b, floor),
    }


def _sampled_series_difference_record(
    value_a: np.ndarray,
    value_b: np.ndarray,
    widths: np.ndarray | None,
    floor: float = NORM_FLOOR,
) -> dict[str, Any]:
    value_a = np.asarray(value_a)
    value_b = np.asarray(value_b)
    if value_a.shape != value_b.shape:
        raise ValueError("sampled series must share shape")
    if value_a.ndim == 1:
        norm_a = temporal_norm(value_a)
        norm_b = temporal_norm(value_b)
        absolute = temporal_norm(value_a - value_b)
    elif value_a.ndim == 2 and widths is not None:
        norm_a = weighted_space_time_norm(value_a, widths)
        norm_b = weighted_space_time_norm(value_b, widths)
        absolute = weighted_space_time_norm(value_a - value_b, widths)
    else:
        raise ValueError("sampled series must be temporal or space-time")
    near_zero = max(norm_a, norm_b) <= floor
    return {
        "status": "NEAR_ZERO_COMPONENT" if near_zero else "FINITE_COMPONENT",
        "T128_norm": norm_a,
        "T256_on_T128_norm": norm_b,
        "absolute_difference_norm": absolute,
        "normalized_l2_difference": None
        if near_zero
        else absolute / max(norm_a, norm_b, floor),
    }


def superposition_modal_record(
    *,
    observed: np.ndarray,
    active: np.ndarray,
    normal: np.ndarray,
    normal_phase_multiplier: complex,
    coarse_observed: np.ndarray,
    widths: np.ndarray | None,
) -> dict[str, Any]:
    observed_dc, observed_c1 = _modal_field(observed)
    active_dc, active_c1 = _modal_field(active)
    normal_dc, normal_c1 = _modal_field(normal)
    predicted_dc = active_dc + normal_dc
    predicted_c1 = active_c1 + normal_phase_multiplier * normal_c1
    dc_difference = _field_difference_record(observed_dc, predicted_dc, widths)
    fundamental_difference = _field_difference_record(
        observed_c1, predicted_c1, widths
    )
    observed_modal_norm = math.sqrt(
        _field_norm(observed_dc, widths) ** 2
        + 2.0 * _field_norm(observed_c1, widths) ** 2
    )
    predicted_modal_norm = math.sqrt(
        _field_norm(predicted_dc, widths) ** 2
        + 2.0 * _field_norm(predicted_c1, widths) ** 2
    )
    modal_absolute = math.sqrt(
        _field_norm(observed_dc - predicted_dc, widths) ** 2
        + 2.0 * _field_norm(observed_c1 - predicted_c1, widths) ** 2
    )
    modal_near_zero = max(observed_modal_norm, predicted_modal_norm) <= NORM_FLOOR
    modal_difference = {
        "status": (
            "NEAR_ZERO_COMPONENT" if modal_near_zero else "FINITE_COMPONENT"
        ),
        "observed_norm": observed_modal_norm,
        "predicted_norm": predicted_modal_norm,
        "absolute_difference_norm": modal_absolute,
        "normalized_l2_difference": None
        if modal_near_zero
        else modal_absolute
        / max(observed_modal_norm, predicted_modal_norm, NORM_FLOOR),
    }
    fine_on_coarse = np.asarray(observed)[..., ::2]
    coarse_observed = np.asarray(coarse_observed)
    if fine_on_coarse.shape != coarse_observed.shape:
        raise ValueError("T256 samples do not nest the T128 first cycle")
    temporal_change = _sampled_series_difference_record(
        coarse_observed,
        fine_on_coarse,
        widths,
    )
    return {
        "observed_dc": _real_field_payload(observed_dc),
        "predicted_dc_from_A2_plus_LN": _real_field_payload(predicted_dc),
        "observed_fundamental": _complex_field_payload(observed_c1),
        "predicted_fundamental_from_A2_plus_phased_LN": _complex_field_payload(
            predicted_c1
        ),
        "dc_difference": dc_difference,
        "fundamental_difference": fundamental_difference,
        "combined_dc_fundamental_difference": modal_difference,
        "T128_to_T256_change": temporal_change,
    }


def build_superposition_audit(
    observations_t128: dict[str, dict[str, dict[str, Any]]],
    observations_t256: dict[str, dict[str, dict[str, Any]]],
) -> dict[str, Any]:
    cases: dict[str, Any] = {}
    for combined_case in COMBINED_CASES:
        phase_multiplier = 1.0 + 0.0j if combined_case == "ID-C0" else 0.0 + 1.0j
        case_payload: dict[str, Any] = {
            "source_composition": (
                "active_plus_in_phase_normal"
                if combined_case == "ID-C0"
                else "active_plus_quarter_phase_normal"
            ),
            "normal_fundamental_phase_multiplier": _complex_payload(
                phase_multiplier
            ),
            "representations": {},
        }
        for representation in ("DCM", "FEM"):
            combined = observations_t256[combined_case][representation]
            active = observations_t256["ID-A2"][representation]
            normal = observations_t256["ID-LN"][representation]
            coarse = observations_t128[combined_case][representation]
            entries: dict[str, Any] = {}
            for name, observation_key in (
                ("limited_shortening", "limited_shortening"),
                (
                    "normal_displacement",
                    "mean_endocardial_normal_displacement",
                ),
                (
                    "tangential_displacement",
                    "mean_endocardial_tangential_displacement",
                ),
            ):
                entries[name] = superposition_modal_record(
                    observed=combined[observation_key],
                    active=active[observation_key],
                    normal=normal[observation_key],
                    normal_phase_multiplier=phase_multiplier,
                    coarse_observed=coarse[observation_key],
                    widths=None,
                )
            widths = common_widths(combined["common_x"])
            for interface, observation_key in INTERFACE_KEYS.items():
                entries[interface] = {}
                for component_index, component in enumerate(COMPONENT_NAMES):
                    entries[interface][component] = superposition_modal_record(
                        observed=combined[observation_key][:, component_index, :],
                        active=active[observation_key][:, component_index, :],
                        normal=normal[observation_key][:, component_index, :],
                        normal_phase_multiplier=phase_multiplier,
                        coarse_observed=coarse[observation_key][
                            :, component_index, :
                        ],
                        widths=widths,
                    )
            case_payload["representations"][representation] = entries
        cases[combined_case] = case_payload
    all_records = [
        record
        for case in cases.values()
        for representation in case["representations"].values()
        for name, value in representation.items()
        for record in (
            list(value.values()) if name in INTERFACE_KEYS else [value]
        )
    ]
    return {
        "schema": "paper2_m2a_v07_superposition_audit",
        "linear_response_assumed_for_identity": False,
        "phase_rule_source": "src/paper2_m2/identity_2d.py:_case_components",
        "cases": cases,
        "maximum_combined_modal_residual": max(
            value
            for record in all_records
            if (
                value := record["combined_dc_fundamental_difference"][
                    "normalized_l2_difference"
                ]
            )
            is not None
        ),
        "maximum_T128_to_T256_normalized_change": max(
            value
            for record in all_records
            if (
                value := record["T128_to_T256_change"][
                    "normalized_l2_difference"
                ]
            )
            is not None
        ),
        "maximum_near_zero_T128_to_T256_absolute_change": max(
            (
                record["T128_to_T256_change"]["absolute_difference_norm"]
                for record in all_records
                if record["T128_to_T256_change"]["status"]
                == "NEAR_ZERO_COMPONENT"
            ),
            default=0.0,
        ),
    }


def _source_span(path: Path, symbol: str) -> dict[str, Any]:
    lines = path.read_text(encoding="utf-8").splitlines()
    starts = (
        f"def {symbol}(",
        f"class {symbol}:",
    )
    start_index = next(
        index for index, line in enumerate(lines) if line.startswith(starts)
    )
    end_index = len(lines)
    for index in range(start_index + 1, len(lines)):
        if lines[index].startswith(("def ", "class ", "@dataclass")):
            end_index = index
            break
    return {
        "path": path.as_posix(),
        "symbol": symbol,
        "line_start": start_index + 1,
        "line_end": end_index,
        "sha256": sha256_file(path),
    }


def build_source_formula_audit(project_root: Path) -> dict[str, Any]:
    relative_paths = {
        "config": "src/paper2_m2/config.py",
        "mechanics": "src/paper2_m2/identity_2d.py",
        "v02_checks": "src/paper2_m2/identity_2d_v02.py",
        "v05_projection": "src/paper2_m2/identity_2d_v05.py",
        "common_projection": "src/paper2_m2/interface_projection.py",
        "v06_identity": "src/paper2_m2/identity_gate_v06.py",
    }
    paths = {name: project_root / relative for name, relative in relative_paths.items()}
    text = {name: path.read_text(encoding="utf-8") for name, path in paths.items()}
    checks = {
        "shared_penalty_traction_formula_present": all(
            token in text["mechanics"]
            for token in (
                "def _interface_tractions(",
                "ecm_myocardium_interface_stiffness * (",
                "myo - ecm_bottom",
                "endocardium_ecm_interface_stiffness * (",
                "endo - ecm_top",
            )
        ),
        "extractor_has_no_representation_branch": "representation"
        not in text["mechanics"].split("def _interface_tractions(", 1)[1].split(
            "def _fundamental", 1
        )[0],
        "nondimensional_units_declared": (
            '"system": "nondimensional_M2A_identity_benchmark"'
            in text["v02_checks"]
        ),
        "sign_convention_declared": (
            '"interface_traction": "positive_on_first_named_domain"'
            in text["v02_checks"]
        ),
        "reference_interface_weights_present": all(
            token in text["mechanics"]
            for token in (
                "interface_weights = np.full(",
                "interface_weights[[0, -1]] *= 0.5",
                "diagonal = np.repeat(stiffness * weights, 2)",
            )
        ),
        "component_order_xy_present": all(
            token in text["mechanics"]
            for token in (
                "force_normal[1::2]",
                "force_tangent[0::2]",
            )
        ),
        "combined_load_phase_rule_present": all(
            token in text["mechanics"]
            for token in (
                'case_id in {"ID-LN", "ID-C0", "ID-CQ"}',
                'phase = math.pi / 2.0 if case_id == "ID-CQ" else 0.0',
            )
        ),
        "conservative_common_projection_present": all(
            token in text["common_projection"]
            for token in (
                "exact integral average",
                "common_segment_space_time_l2",
                "piecewise_linear_integral",
            )
        ),
        "v06_first_cycle_and_64_segment_projection_present": all(
            token in text["v06_identity"]
            for token in (
                "project_traction_first_cycle",
                "native_nodes = 129",
                "common_segments: int = 64",
            )
        ),
    }
    projection_check = constant_traction_projection_manufactured_check(
        native_segments=128, common_segments=64
    )
    unexpected = [name for name, passed in checks.items() if not passed]
    if not projection_check["pass"]:
        unexpected.append("common_projection_manufactured_conservation_failure")
    sources = {
        relative_paths[name]: sha256_file(path) for name, path in paths.items()
    }
    evidence = {
        "interface_energy_and_weights": _source_span(paths["mechanics"], "_interface_matrix"),
        "representation_assembly": _source_span(paths["mechanics"], "build_system_for_level"),
        "load_components": _source_span(paths["mechanics"], "_case_components"),
        "traction_extractor": _source_span(paths["mechanics"], "_interface_tractions"),
        "array_export": _source_span(paths["mechanics"], "simulate_endpoint"),
        "units_and_sign": _source_span(paths["v02_checks"], "global_structural_checks"),
        "common_projection": _source_span(
            paths["common_projection"], "project_piecewise_linear_to_common_segments"
        ),
        "common_space_time_norm": _source_span(
            paths["common_projection"], "common_segment_space_time_l2"
        ),
        "v06_projection_entry": _source_span(
            paths["v06_identity"], "project_traction_first_cycle"
        ),
    }
    for record in evidence.values():
        record["path"] = str(Path(record["path"]).relative_to(project_root).as_posix())
    return {
        "schema": "paper2_m2a_v07_source_formula_audit",
        "source_sha256": sources,
        "machine_checks": checks,
        "unexpected_inconsistencies": unexpected,
        "extraction_audit_clean": not unexpected,
        "coordinate_convention": {
            "component_0": "x_tangential",
            "component_1": "y_normal",
            "shared_by_DCM_and_FEM": True,
            "evidence_supports_nonidentity_signed_permutation": False,
        },
        "stress_or_traction_measure": {
            "type": "shared_linear_penalty_interface_traction_density",
            "formula_myocardium_ecm": "k_myo_ecm * (u_myo - u_ecm_bottom)",
            "formula_endocardium_ecm": "k_endo_ecm * (u_endo - u_ecm_top)",
            "Cauchy_or_Piola_conversion_used": False,
            "interpretation": (
                "The exported interface observable is the shared penalty-spring "
                "traction-like density, not a separately recovered continuum stress."
            ),
        },
        "sign_and_interface_sides": {
            "stored_sign": "positive_on_first_named_domain",
            "opposite_side_reaction": "implicit_negative_energy_gradient_pair",
            "same_extractor_for_DCM_and_FEM": True,
        },
        "units": {
            "system": "nondimensional_M2A_identity_benchmark",
            "length": "nondimensional_length",
            "time": "nondimensional_time_with_period_1",
            "traction": "nondimensional_interface_traction_density",
            "force": "traction_density_times_reference_interface_length",
            "out_of_plane_thickness": "implicit_unit_thickness_plane_strain",
        },
        "sampling_and_weights": {
            "native": "129_reference_interface_nodes_P1",
            "interface_energy": "reference_trapezoidal_nodal_weights",
            "exported_traction": "unweighted_nodal_traction_density",
            "common_projection": "64_reference_segments_exact_P1_integral_average",
            "identity_norm": "reference_segment_length_and_equal_time_weight",
            "reference_or_current_measure": "reference_interface_measure",
        },
        "interface_extraction_symmetry": {
            "same_displacement_jump_formula": True,
            "same_reference_weights": True,
            "intentional_stiffness_values": {
                "myocardium_ecm": 8.0,
                "endocardium_ecm": 7.0,
            },
        },
        "projection_conservation_check": projection_check,
        "evidence": evidence,
    }


def classify_diagnostic_conditions(conditions: dict[str, bool]) -> str:
    candidate_order = (
        "NORMALIZATION_DOMINANT",
        "COMPONENT_BASIS_CANDIDATE",
        "EXTRACTION_IMPLEMENTATION_CANDIDATE",
        "MODE_SELECTIVE_CONSTITUTIVE_MISMATCH",
    )
    satisfied = [label for label in candidate_order if conditions.get(label, False)]
    if len(satisfied) >= 2:
        return "MIXED"
    if len(satisfied) == 1:
        return satisfied[0]
    return "INCONCLUSIVE"


def build_diagnostic_classification(
    *,
    traction_audit: dict[str, Any],
    basis_audit: dict[str, Any],
    mode_audit: dict[str, Any],
    source_audit: dict[str, Any],
) -> dict[str, Any]:
    global_scale = traction_audit["formal_failed_traction_global_scale_audit"]
    common_basis = basis_audit["common_best"]
    extraction_clean = bool(source_audit["extraction_audit_clean"])
    basis_evidence = bool(
        source_audit["coordinate_convention"][
            "evidence_supports_nonidentity_signed_permutation"
        ]
    )
    pure_active_failure_records = (
        "ID-A2__myocardium_ecm",
        "ID-A2__endocardium_ecm",
    )
    persistent_records = [
        record_id
        for record_id in pure_active_failure_records
        if global_scale["records"][record_id][
            "global_scale_residual_over_fem_norm"
        ]
        > MODE_MISMATCH_THRESHOLD
        and common_basis["per_record_normalized_l2"][record_id]
        > MODE_MISMATCH_THRESHOLD
    ]
    localized_mode_records = [
        record_id
        for record_id, record in mode_audit["records"].items()
        if record_id.startswith("ID-A2__")
        and record["full_component_difference"]["normalized_l2_difference"]
        is not None
        and record["full_component_difference"]["normalized_l2_difference"]
        > MODE_MISMATCH_THRESHOLD
        and (
            record["spatial"]["difference_localization"] != "UNRESOLVED_MIXTURE"
            or record["temporal"]["difference_localization"]
            != "UNRESOLVED_MIXTURE"
        )
    ]
    conditions = {
        "NORMALIZATION_DOMINANT": bool(
            common_basis["is_identity"]
            and global_scale["all_global_scale_residuals_le_5pct"]
            and global_scale["all_optimal_scales_within_5pct_of_global"]
            and extraction_clean
        ),
        "COMPONENT_BASIS_CANDIDATE": bool(
            common_basis["is_nonidentity"]
            and common_basis["all_failed_traction_records_le_5pct"]
            and basis_evidence
        ),
        "EXTRACTION_IMPLEMENTATION_CANDIDATE": bool(
            not extraction_clean
            and bool(source_audit["unexpected_inconsistencies"])
        ),
        "MODE_SELECTIVE_CONSTITUTIVE_MISMATCH": bool(
            extraction_clean and persistent_records and localized_mode_records
        ),
    }
    label = classify_diagnostic_conditions(conditions)
    return {
        "schema": "paper2_m2a_v07_diagnostic_classification",
        "diagnostic_label": label,
        "v06_1_identity_decision": "NO-GO-ID",
        "v06_1_identity_decision_changed": False,
        "thresholds_are_diagnostic_not_identity_gates": True,
        "conditions": conditions,
        "condition_count_true": sum(conditions.values()),
        "support": {
            "global_scale": global_scale,
            "common_signed_permutation": common_basis,
            "persistent_pure_active_failure_records": persistent_records,
            "localized_pure_active_component_records": localized_mode_records,
            "extraction_audit_clean": extraction_clean,
        },
        "counterevidence": {
            "normalization": {
                "all_global_scale_residuals_le_5pct": global_scale[
                    "all_global_scale_residuals_le_5pct"
                ],
                "all_optimal_scales_within_5pct_of_global": global_scale[
                    "all_optimal_scales_within_5pct_of_global"
                ],
            },
            "component_basis": {
                "common_best_is_nonidentity": common_basis["is_nonidentity"],
                "common_best_all_records_le_5pct": common_basis[
                    "all_failed_traction_records_le_5pct"
                ],
                "compatible_source_evidence": basis_evidence,
            },
            "extraction_implementation": {
                "unexpected_inconsistencies": source_audit[
                    "unexpected_inconsistencies"
                ]
            },
        },
        "evidence_boundary": (
            "This is a retrospective diagnostic label for the frozen idealized 2D "
            "v06.1 NO-GO-ID evidence. It is not a new identity decision, model repair, "
            "physiological validation, or evidence for 3D, organ-scale, EFE, fluid, "
            "experimental, or clinical claims."
        ),
    }
