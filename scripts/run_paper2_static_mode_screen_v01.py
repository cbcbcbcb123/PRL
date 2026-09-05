"""Run the preregistered finite static activation-mode screen.

This entry point is deliberately narrow: six passive FEM systems, one sparse
factorization and five static activation-derivative right-hand sides per
system.  It does not run a cycle, a frequency sweep, feedback, or holdouts.
"""

from __future__ import annotations

import argparse
from dataclasses import asdict, replace
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import sys
import time
from typing import Any

import numpy as np
from scipy import linalg
from scipy.sparse import csr_matrix
from scipy.sparse import linalg as sparse_linalg


SCHEMA = "paper2_static_mode_screen_v01"
EXPECTED_CODE_VERSION = "2f1c9deebfb6d6a474ffe3ad52576b568cfc877c"
EXPECTED_LAUNCH_CHECKOUT = "5ba44386c28cf75964d168b34dc69d08adc1ea9a"
PLAN_RELATIVE = Path("project_control/prl_independent_theory_mainline_plan_v04.md")
PLAN_SHA256 = "5b4bb166b56a4d40a9c36ca8b7d5484e55bc329a1cdb651dc2679e9ce0c0c2e3"
BRIEF_RELATIVE = Path("results/paper2_science_pilot/v01_20260905/science_brief.md")
BRIEF_SHA256 = "f5b377572af56e062ffde9069b530f19ceb4098bf91ca12dd655c8f172218c69"
RESULT_RELATIVE = Path("results/paper2_static_mode_screen/v01_20260905")
SOURCE_RELATIVES = (
    Path("src/paper2_hybrid/config.py"),
    Path("src/paper2_hybrid/model.py"),
)
EXPECTED_PRODUCTION_SOURCE_HASHES = {
    "src/paper2_hybrid/config.py": "0a83aedbabeb944b89f9584511dac5a597401327a68ac5c6411cb30e81ced6fe",
    "src/paper2_hybrid/model.py": "d43129c746c133294fcc92149d519a6c94bd633f2be54c898beea5d23190e800",
}
EXPECTED_IMAGE = "dolfinx/dolfinx:v0.11.0"
EXPECTED_IMAGE_ID = (
    "sha256:2ae4bfbc0d9077268880faf04c72750528bee986c94ab223a2c159969bd56fa8"
)
EXPECTED_CONTAINER_NAME = "prl-paper2-static-mode-screen-v01-20260905"
EXPECTED_PYTHONPATH = (
    "/workspace/src:/usr/local/dolfinx-real/lib/python3.12/dist-packages:"
    "/usr/local/lib:"
)
THICKNESS_RATIOS = (0.1, 0.26, 0.6)
SPATIAL_LABELS = ("S2", "S3")
MODE_LABELS = ("uniform", "cos_k", "sin_k", "cos_2k", "sin_2k")
NUMERICAL_BUDGET_SECONDS = 300.0
OLD_FEM_AND_FAILURE_CHARGE_SECONDS = 161.8682304820104
PROJECT_STOP_REESTIMATE_SECONDS = 7200.0
RELATIVE_RESIDUAL_TOLERANCE = 1.0e-7
BACKWARD_ERROR_TOLERANCE = 1.0e-12
IDENTITY_TOLERANCE = 1.0e-12
R_ASYMMETRY_TOLERANCE = 1.0e-10
SPECTRUM_RELATIVE_TOLERANCE = 1.0e-8


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _jsonable(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, Path):
        return value.as_posix()
    return value


def _write_json_exclusive(path: Path, payload: Any) -> None:
    with path.open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(
            _jsonable(payload),
            handle,
            ensure_ascii=False,
            sort_keys=True,
            indent=2,
            allow_nan=False,
        )
        handle.write("\n")


def _write_npz_exclusive(path: Path, arrays: dict[str, np.ndarray]) -> None:
    for name, value in arrays.items():
        array = np.asarray(value)
        if np.issubdtype(array.dtype, np.number) and not np.all(np.isfinite(array)):
            raise RuntimeError(f"non-finite NPZ array: {name}")
    with path.open("xb") as handle:
        np.savez_compressed(handle, **arrays)


def _relative_error(left: np.ndarray | float, right: np.ndarray | float) -> float:
    left_array = np.asarray(left, dtype=np.float64)
    right_array = np.asarray(right, dtype=np.float64)
    difference = left_array - right_array
    if difference.ndim == 0:
        numerator = abs(float(difference))
        denominator = max(abs(float(left_array)), abs(float(right_array)), 1.0e-30)
    elif difference.ndim == 1:
        numerator = float(np.linalg.norm(difference, ord=2))
        denominator = max(
            float(np.linalg.norm(left_array, ord=2)),
            float(np.linalg.norm(right_array, ord=2)),
            1.0e-30,
        )
    else:
        numerator = float(np.linalg.norm(difference, ord="fro"))
        denominator = max(
            float(np.linalg.norm(left_array, ord="fro")),
            float(np.linalg.norm(right_array, ord="fro")),
            1.0e-30,
        )
    return numerator / denominator


def _sparse_frobenius(matrix: csr_matrix) -> float:
    return float(np.sqrt(np.dot(matrix.data, matrix.data)))


def _sparse_relative_asymmetry(matrix: csr_matrix, denominator_floor: float) -> float:
    difference = (matrix - matrix.T).tocsr()
    numerator = _sparse_frobenius(difference)
    denominator = max(_sparse_frobenius(matrix), denominator_floor, 1.0e-30)
    return numerator / denominator


def _plane_strain_moduli(young_modulus: float, poisson_ratio: float) -> tuple[float, float, float]:
    shear_modulus = young_modulus / (2.0 * (1.0 + poisson_ratio))
    lame_lambda = (
        young_modulus
        * poisson_ratio
        / ((1.0 + poisson_ratio) * (1.0 - 2.0 * poisson_ratio))
    )
    c_xxxx = lame_lambda + 2.0 * shear_modulus
    return lame_lambda, shear_modulus, c_xxxx


def _activation_basis(x_values: np.ndarray, length: float) -> np.ndarray:
    wavenumber = 2.0 * math.pi / length
    return np.column_stack(
        (
            np.ones_like(x_values),
            math.sqrt(2.0) * np.cos(wavenumber * x_values),
            math.sqrt(2.0) * np.sin(wavenumber * x_values),
            math.sqrt(2.0) * np.cos(2.0 * wavenumber * x_values),
            math.sqrt(2.0) * np.sin(2.0 * wavenumber * x_values),
        )
    )


def _static_p1_metrics(x_values: np.ndarray, field_values: np.ndarray, length: float) -> dict[str, Any]:
    """Exact segment integration of a real native P1 static derivative field."""

    x_nodes = np.asarray(x_values, dtype=np.float64)
    field = np.asarray(field_values, dtype=np.float64)
    if x_nodes.ndim != 1 or field.ndim != 1 or x_nodes.shape != field.shape:
        raise ValueError("static P1 inputs must be matching one-dimensional arrays")
    if len(x_nodes) < 2 or not np.all(np.isfinite(x_nodes)) or not np.all(np.isfinite(field)):
        raise ValueError("static P1 inputs are invalid")
    segment_widths = np.diff(x_nodes)
    if not np.all(segment_widths > 0.0):
        raise ValueError("static P1 coordinates are not strictly increasing")
    coordinate_tolerance = 5.0e-12 * max(1.0, abs(length))
    if not math.isclose(float(x_nodes[0]), -0.5 * length, rel_tol=0.0, abs_tol=coordinate_tolerance):
        raise ValueError("left interface coordinate does not match -L/2")
    if not math.isclose(float(x_nodes[-1]), 0.5 * length, rel_tol=0.0, abs_tol=coordinate_tolerance):
        raise ValueError("right interface coordinate does not match L/2")

    slopes = np.diff(field) / segment_widths
    intercepts = field[:-1] - slopes * x_nodes[:-1]
    left = x_nodes[:-1]
    right = x_nodes[1:]
    wavenumber = 2.0 * math.pi / length

    integral_constant = float(
        np.sum(0.5 * (field[:-1] + field[1:]) * segment_widths)
    )
    primitive_cos = lambda values: np.sin(wavenumber * values) / wavenumber
    primitive_x_cos = lambda values: (
        values * np.sin(wavenumber * values) / wavenumber
        + np.cos(wavenumber * values) / (wavenumber**2)
    )
    primitive_sin = lambda values: -np.cos(wavenumber * values) / wavenumber
    primitive_x_sin = lambda values: (
        -values * np.cos(wavenumber * values) / wavenumber
        + np.sin(wavenumber * values) / (wavenumber**2)
    )
    integral_cos = float(
        np.sum(
            slopes * (primitive_x_cos(right) - primitive_x_cos(left))
            + intercepts * (primitive_cos(right) - primitive_cos(left))
        )
    )
    integral_sin = float(
        np.sum(
            slopes * (primitive_x_sin(right) - primitive_x_sin(left))
            + intercepts * (primitive_sin(right) - primitive_sin(left))
        )
    )
    rms_squared = float(
        np.sum(
            segment_widths
            * (
                field[:-1] * field[:-1]
                + field[:-1] * field[1:]
                + field[1:] * field[1:]
            )
            / 3.0
        )
        / length
    )
    endpoint_absolute = abs(float(field[-1] - field[0]))
    endpoint_scale = max(float(np.max(np.abs(field))), 1.0e-30)
    uniform_spacing_error = float(
        np.max(np.abs(segment_widths - np.mean(segment_widths)))
        / max(float(np.mean(segment_widths)), np.finfo(np.float64).tiny)
    )
    return {
        "definition": {
            "field": "static y-traction derivative on the endocardium-ECM interface in code sign",
            "integration": "exact analytic integration of the native real piecewise-linear interpolant",
            "c0": "L^-1 integral f dx",
            "c_cos": "2 L^-1 integral f cos(2 pi x/L) dx",
            "c_sin": "2 L^-1 integral f sin(2 pi x/L) dx",
            "rms": "sqrt(sum dx*(f_left^2+f_left*f_right+f_right^2)/(3L))",
        },
        "c0": integral_constant / length,
        "c_cos": 2.0 * integral_cos / length,
        "c_sin": 2.0 * integral_sin / length,
        "spatial_rms": math.sqrt(max(rms_squared, 0.0)),
        "coordinate_domain": [float(x_nodes[0]), float(x_nodes[-1])],
        "node_count": int(len(x_nodes)),
        "uniform_spacing_relative_error": uniform_spacing_error,
        "periodic_endpoint_check": {
            "absolute_mismatch": endpoint_absolute,
            "relative_to_peak_field": endpoint_absolute / endpoint_scale,
            "used_as_assumption": False,
        },
    }


def _generalized_residual(
    matrix_r: np.ndarray,
    matrix_w: np.ndarray,
    eigenvalue: float,
    eigenvector: np.ndarray,
) -> float:
    left = matrix_r @ eigenvector
    right = eigenvalue * (matrix_w @ eigenvector)
    return float(
        np.linalg.norm(left - right)
        / max(np.linalg.norm(left), np.linalg.norm(right), 1.0e-30)
    )


def _orient(vector: np.ndarray) -> np.ndarray:
    result = np.asarray(vector, dtype=np.float64).copy()
    pivot = int(np.argmax(np.abs(result)))
    if result[pivot] < 0.0:
        result *= -1.0
    return result


def _spectral_analysis(matrix_r_raw: np.ndarray, matrix_w: np.ndarray, c_xxxx: float) -> dict[str, Any]:
    matrix_r_symmetric = 0.5 * (matrix_r_raw + matrix_r_raw.T)
    w_values, w_vectors = linalg.eigh(matrix_w, check_finite=True)
    if float(w_values[0]) <= 0.0:
        raise RuntimeError("W is not positive definite")
    w_half = (w_vectors * np.sqrt(w_values)) @ w_vectors.T
    w_inverse_half = (w_vectors * (1.0 / np.sqrt(w_values))) @ w_vectors.T
    whitened = w_inverse_half @ matrix_r_symmetric @ w_inverse_half
    whitened = 0.5 * (whitened + whitened.T)
    full_values, full_white_vectors = linalg.eigh(whitened, check_finite=True)
    full_vectors = w_inverse_half @ full_white_vectors
    for column in range(full_vectors.shape[1]):
        full_vectors[:, column] = _orient(full_vectors[:, column])

    uniform_basis = np.zeros(5, dtype=np.float64)
    uniform_basis[0] = 1.0
    normalized_uniform_white = w_half @ uniform_basis / math.sqrt(float(matrix_w[0, 0]))
    projector = np.eye(5) - np.outer(normalized_uniform_white, normalized_uniform_white)
    coupling = float(
        np.linalg.norm(projector @ whitened @ normalized_uniform_white) / c_xxxx
    )

    nonuniform_basis = np.zeros((5, 4), dtype=np.float64)
    for local_column, source_column in enumerate(range(1, 5)):
        nonuniform_basis[source_column, local_column] = 1.0
        nonuniform_basis[0, local_column] = -matrix_w[0, source_column] / matrix_w[0, 0]
    nonuniform_r = nonuniform_basis.T @ matrix_r_symmetric @ nonuniform_basis
    nonuniform_w = nonuniform_basis.T @ matrix_w @ nonuniform_basis
    nonuniform_values, nonuniform_vectors = linalg.eigh(
        nonuniform_r, nonuniform_w, check_finite=True
    )
    main_reduced_coefficients = nonuniform_vectors[:, -1]
    main_reduced_coefficients /= math.sqrt(
        float(main_reduced_coefficients @ nonuniform_w @ main_reduced_coefficients)
    )
    main_coefficients = nonuniform_basis @ main_reduced_coefficients
    oriented_main = _orient(main_coefficients)
    if float(np.dot(oriented_main, main_coefficients)) < 0.0:
        main_reduced_coefficients *= -1.0
    main_coefficients = oriented_main
    lambda_nonuniform = float(nonuniform_values[-1])

    first_basis = nonuniform_basis[:, :2]
    first_r = first_basis.T @ matrix_r_symmetric @ first_basis
    first_w = first_basis.T @ matrix_w @ first_basis
    first_values, first_vectors = linalg.eigh(first_r, first_w, check_finite=True)
    first_reduced_coefficients = first_vectors[:, -1]
    first_reduced_coefficients /= math.sqrt(
        float(first_reduced_coefficients @ first_w @ first_reduced_coefficients)
    )
    first_coefficients = first_basis @ first_reduced_coefficients
    oriented_first = _orient(first_coefficients)
    if float(np.dot(oriented_first, first_coefficients)) < 0.0:
        first_reduced_coefficients *= -1.0
    first_coefficients = oriented_first

    full_residuals = [
        _generalized_residual(matrix_r_symmetric, matrix_w, float(value), full_vectors[:, index])
        for index, value in enumerate(full_values)
    ]
    main_residual = _generalized_residual(
        nonuniform_r,
        nonuniform_w,
        lambda_nonuniform,
        main_reduced_coefficients,
    )
    first_residual = _generalized_residual(
        first_r,
        first_w,
        float(first_values[-1]),
        first_reduced_coefficients,
    )
    uniform_response = float(matrix_r_raw[0, 0] / matrix_w[0, 0])
    eigenvalue_gap = float(nonuniform_values[-1] - nonuniform_values[-2])
    return {
        "matrix_r_symmetric": matrix_r_symmetric,
        "matrix_whitened": whitened,
        "w_eigenvalues": w_values,
        "w_condition_number": float(w_values[-1] / w_values[0]),
        "full_eigenvalues": full_values,
        "full_eigenvectors": full_vectors,
        "full_generalized_residuals": np.asarray(full_residuals),
        "maximum_full_generalized_residual": max(full_residuals),
        "uniform_response_m0": uniform_response,
        "lambda_nonuniform": lambda_nonuniform,
        "delta": lambda_nonuniform - uniform_response,
        "nonuniform_eigenvalues": nonuniform_values,
        "main_nonuniform_coefficients": main_coefficients,
        "main_nonuniform_w_norm_squared": float(main_coefficients @ matrix_w @ main_coefficients),
        "main_nonuniform_discrete_mean": float(matrix_w[0, :] @ main_coefficients),
        "main_nonuniform_eigenvalue_gap": eigenvalue_gap,
        "main_nonuniform_near_degenerate": bool(eigenvalue_gap <= 1.0e-8 * c_xxxx),
        "main_nonuniform_generalized_residual": main_residual,
        "n1_eigenvalues": first_values,
        "n1_lambda_max": float(first_values[-1]),
        "n1_max_coefficients": first_coefficients,
        "n1_generalized_residual": first_residual,
        "mean_nonmean_coupling_over_d": coupling,
        "normalized_uniform_white": normalized_uniform_white,
    }


def _self_test() -> dict[str, Any]:
    length = 1.0
    segments = 32
    x_nodes = np.linspace(-0.5 * length, 0.5 * length, segments + 1)
    wavenumber = 2.0 * math.pi / length
    field = 2.3 + 1.2 * np.cos(wavenumber * x_nodes) - 0.8 * np.sin(wavenumber * x_nodes)
    metrics = _static_p1_metrics(x_nodes, field, length)
    p1_factor = float(np.sinc(1.0 / segments) ** 2)
    p1_errors = {
        "constant": abs(metrics["c0"] - 2.3),
        "cosine": abs(metrics["c_cos"] - 1.2 * p1_factor),
        "sine": abs(metrics["c_sin"] + 0.8 * p1_factor),
    }
    matrix_w = np.asarray(
        (
            (1.0, 0.08, -0.03, 0.02, 0.01),
            (0.08, 1.1, 0.02, 0.0, -0.01),
            (-0.03, 0.02, 0.9, 0.01, 0.0),
            (0.02, 0.0, 0.01, 1.05, 0.03),
            (0.01, -0.01, 0.0, 0.03, 0.95),
        ),
        dtype=np.float64,
    )
    diagonal_response = np.diag((0.45, 0.62, 0.58, 0.40, 0.35))
    matrix_r = matrix_w @ diagonal_response @ matrix_w
    matrix_r = 0.5 * (matrix_r + matrix_r.T)
    spectrum = _spectral_analysis(matrix_r, matrix_w, 1.0)
    spectral_checks = {
        "w_norm": abs(spectrum["main_nonuniform_w_norm_squared"] - 1.0),
        "discrete_mean": abs(spectrum["main_nonuniform_discrete_mean"]),
        "residual": spectrum["main_nonuniform_generalized_residual"],
    }
    tolerance = 3.0e-12
    return {
        "pass": bool(max((*p1_errors.values(), *spectral_checks.values())) <= tolerance),
        "tolerance": tolerance,
        "p1_errors": p1_errors,
        "spectral_checks": spectral_checks,
    }


def _build_source_columns(system: Any) -> dict[str, Any]:
    config = system.config
    myocardium = system.myocardium_mesh
    cell_x = np.asarray(myocardium.cell_centroids[:, 0], dtype=np.float64)
    cell_areas = np.asarray(myocardium.cell_areas, dtype=np.float64)
    basis_phi = _activation_basis(cell_x, config.length)
    lame_lambda, shear_modulus, c_xxxx = _plane_strain_moduli(
        config.myocardium_young_modulus, config.myocardium_poisson_ratio
    )
    weighted_stress = np.zeros((3 * len(cell_areas), 5), dtype=np.float64)
    weighted_stress[0::3, :] = cell_areas[:, None] * c_xxxx * basis_phi
    weighted_stress[1::3, :] = cell_areas[:, None] * lame_lambda * basis_phi
    active_full = np.asarray(myocardium.strain_operator.T @ weighted_stress)
    matrix_h = np.asarray(system.myocardium_transform.T @ active_full)
    matrix_w = basis_phi.T @ (cell_areas[:, None] * basis_phi)
    matrix_w /= config.length * config.myocardium_thickness
    matrix_d_raw = c_xxxx * basis_phi.T @ (cell_areas[:, None] * basis_phi)
    return {
        "matrix_h": matrix_h,
        "matrix_w": matrix_w,
        "matrix_d_raw": matrix_d_raw,
        "basis_phi": basis_phi,
        "cell_x": cell_x,
        "cell_areas": cell_areas,
        "lame_lambda": lame_lambda,
        "shear_modulus": shear_modulus,
        "c_xxxx": c_xxxx,
    }


def _solve_five(matrix_a: csr_matrix, matrix_h: np.ndarray) -> dict[str, Any]:
    factor_start = time.perf_counter()
    factor = sparse_linalg.splu(matrix_a.tocsc())
    factor_seconds = time.perf_counter() - factor_start
    right_hand_sides = -matrix_h
    solve_start = time.perf_counter()
    matrix_q = np.asarray(factor.solve(right_hand_sides), dtype=np.float64)
    solve_seconds = time.perf_counter() - solve_start
    residual_matrix = np.asarray(matrix_a @ matrix_q - right_hand_sides)
    matrix_inf_norm = float(np.max(np.asarray(np.abs(matrix_a).sum(axis=1)).ravel()))
    relative_residuals: list[float] = []
    backward_errors: list[float] = []
    for column in range(5):
        residual = residual_matrix[:, column]
        solution = matrix_q[:, column]
        right_hand_side = right_hand_sides[:, column]
        relative_residuals.append(
            float(
                np.linalg.norm(residual, ord=2)
                / max(np.linalg.norm(right_hand_side, ord=2), 1.0e-30)
            )
        )
        denominator = (
            matrix_inf_norm * float(np.linalg.norm(solution, ord=np.inf))
            + float(np.linalg.norm(right_hand_side, ord=np.inf))
        )
        backward_errors.append(
            float(np.linalg.norm(residual, ord=np.inf) / max(denominator, 1.0e-30))
        )
    return {
        "matrix_q": matrix_q,
        "right_hand_sides": right_hand_sides,
        "residual_matrix": residual_matrix,
        "relative_residuals": np.asarray(relative_residuals),
        "backward_errors": np.asarray(backward_errors),
        "factor_seconds": factor_seconds,
        "solve_seconds": solve_seconds,
        "factorization_count": 1,
        "rhs_count": 5,
    }


def _traction_observations(system: Any, matrix_q: np.ndarray, matrix_w: np.ndarray, main_z: np.ndarray) -> dict[str, Any]:
    endocardium_rows, ecm_top_rows = system.endocardium_ecm_rows
    endocardium = np.asarray(system.endocardium_transform[endocardium_rows] @ matrix_q)
    ecm_top = np.asarray(system.ecm_transform[ecm_top_rows] @ matrix_q)
    traction = system.config.endocardium_ecm_interface_stiffness * (endocardium - ecm_top)
    node_count = len(system.interface_weights)
    traction_y_raw = traction.reshape(node_count, 2, 5)[:, 1, :]
    x_nodes = np.asarray(
        system.ecm_mesh.dof_coordinates[system.ecm_mesh.top_nodes, 0], dtype=np.float64
    )
    normalizers = np.sqrt(np.diag(matrix_w))
    traction_y_normalized = traction_y_raw / normalizers[None, :]
    macro_raw = np.asarray(matrix_q[system.macro_strain_index, :], dtype=np.float64)
    macro_normalized = macro_raw / normalizers
    column_metrics = [
        _static_p1_metrics(x_nodes, traction_y_normalized[:, column], system.config.length)
        for column in range(5)
    ]
    main_state = matrix_q @ main_z
    main_traction_y = traction_y_raw @ main_z
    main_metrics = _static_p1_metrics(x_nodes, main_traction_y, system.config.length)
    return {
        "x_interface": x_nodes,
        "normalizers": normalizers,
        "macro_strain_raw": macro_raw,
        "macro_strain_normalized": macro_normalized,
        "traction_y_code_raw": traction_y_raw,
        "traction_y_code_normalized": traction_y_normalized,
        "column_metrics": column_metrics,
        "main_state": main_state,
        "main_macro_strain": float(main_state[system.macro_strain_index]),
        "main_traction_y_code": main_traction_y,
        "main_metrics": main_metrics,
    }


def _system_name(thickness_ratio: float, spatial_label: str) -> str:
    thickness_token = str(thickness_ratio).replace(".", "p")
    return f"h{thickness_token}__{spatial_label.lower()}"


def _execute_system(
    *,
    model_module: Any,
    active_config: Any,
    thickness_ratio: float,
    spatial_label: str,
    numerical_start: float,
) -> tuple[dict[str, Any], dict[str, np.ndarray]]:
    config = replace(
        active_config,
        length=1.0,
        myocardium_thickness=0.2,
        ecm_thickness=thickness_ratio,
        period=1.0,
        ecm_relaxation_time=0.2,
        endocardial_axial_stiffness=0.8,
    ).checked()
    assembly_start = time.perf_counter()
    system = model_module.build_system(
        spatial_label=spatial_label,
        active_profile="uniform",
        config=config,
    )
    assembly_seconds = time.perf_counter() - assembly_start
    if time.perf_counter() - numerical_start > NUMERICAL_BUDGET_SECONDS:
        raise RuntimeError("300-second numerical budget exceeded after assembly")

    sources = _build_source_columns(system)
    matrix_a = system.matrix_a.tocsr()
    solve = _solve_five(matrix_a, sources["matrix_h"])
    if time.perf_counter() - numerical_start > NUMERICAL_BUDGET_SECONDS:
        raise RuntimeError("300-second numerical budget exceeded after solve")

    length_thickness = config.length * config.myocardium_thickness
    matrix_r_raw = (
        sources["matrix_d_raw"] + sources["matrix_h"].T @ solve["matrix_q"]
    ) / length_thickness
    spectral = _spectral_analysis(matrix_r_raw, sources["matrix_w"], sources["c_xxxx"])
    observations = _traction_observations(
        system,
        solve["matrix_q"],
        sources["matrix_w"],
        spectral["main_nonuniform_coefficients"],
    )
    if time.perf_counter() - numerical_start > NUMERICAL_BUDGET_SECONDS:
        raise RuntimeError("300-second numerical budget exceeded after observations")

    identity_errors = {
        "uniform_H_column_vs_production": _relative_error(
            sources["matrix_h"][:, 0], system.active_vector_h
        ),
        "D_raw_00_vs_production": _relative_error(
            sources["matrix_d_raw"][0, 0], system.active_scalar_c
        ),
        "D_raw_over_area_vs_dW": _relative_error(
            sources["matrix_d_raw"] / length_thickness,
            sources["c_xxxx"] * sources["matrix_w"],
        ),
    }
    identity_pass = all(value <= IDENTITY_TOLERANCE for value in identity_errors.values())
    r_asymmetry_numerator = float(
        np.linalg.norm(matrix_r_raw - matrix_r_raw.T, ord="fro")
    )
    r_asymmetry_denominator = max(
        float(np.linalg.norm(matrix_r_raw, ord="fro")),
        sources["c_xxxx"],
    )
    r_relative_asymmetry = r_asymmetry_numerator / r_asymmetry_denominator
    matrix_a_relative_asymmetry = _sparse_relative_asymmetry(matrix_a, sources["c_xxxx"])
    residual_pass = bool(np.max(solve["relative_residuals"]) <= RELATIVE_RESIDUAL_TOLERANCE)
    backward_pass = bool(np.max(solve["backward_errors"]) <= BACKWARD_ERROR_TOLERANCE)
    r_symmetry_pass = bool(r_relative_asymmetry <= R_ASYMMETRY_TOLERANCE)
    w_positive_pass = bool(float(spectral["w_eigenvalues"][0]) > 0.0)
    lower_bound = -SPECTRUM_RELATIVE_TOLERANCE * sources["c_xxxx"]
    upper_bound = (1.0 + SPECTRUM_RELATIVE_TOLERANCE) * sources["c_xxxx"]
    spectrum_pass = bool(
        float(spectral["full_eigenvalues"][0]) >= lower_bound
        and float(spectral["full_eigenvalues"][-1]) <= upper_bound
    )
    retention_checks = {
        "macro_degree_retained": bool(0 <= system.macro_strain_index < system.state_size),
        "ecm_internal_variables_retained": bool(
            system.ecm_internal_slice.stop > system.ecm_internal_slice.start
        ),
        "support_retained": bool(system.matrix_support.nnz > 0),
        "myocardium_ecm_interface_retained": bool(
            system.component_matrices["interface_myocardium_ecm"].nnz > 0
        ),
        "endocardium_ecm_interface_retained": bool(
            system.component_matrices["interface_endocardium_ecm"].nnz > 0
        ),
    }
    all_finite = all(
        np.all(np.isfinite(value))
        for value in (
            matrix_a.data,
            sources["matrix_h"],
            sources["matrix_w"],
            sources["matrix_d_raw"],
            solve["matrix_q"],
            solve["residual_matrix"],
            matrix_r_raw,
            spectral["full_eigenvalues"],
            observations["traction_y_code_raw"],
        )
    )
    gate_checks = {
        "all_values_finite": all_finite,
        "relative_residual": residual_pass,
        "normwise_backward_error": backward_pass,
        "three_identities": identity_pass,
        "W_positive_definite": w_positive_pass,
        "R_raw_relative_asymmetry": r_symmetry_pass,
        "five_mode_spectrum_bounds": spectrum_pass,
        "required_degrees_and_couplings_retained": all(retention_checks.values()),
    }
    all_gates_pass = all(gate_checks.values())
    total_elapsed = time.perf_counter() - numerical_start

    system_json = {
        "schema": SCHEMA,
        "status": "COMPLETED_SYSTEM" if all_gates_pass else "FAILED_PREREGISTERED_STRUCTURE_GATE",
        "system": {
            "thickness_ratio_H": thickness_ratio,
            "spatial_label": spatial_label,
            "mesh": asdict(config.spatial(spatial_label)),
            "state_size": system.state_size,
            "matrix_a_shape": list(matrix_a.shape),
            "matrix_a_nnz": matrix_a.nnz,
            "matrix_a_relative_asymmetry": matrix_a_relative_asymmetry,
            "active_profile_used_for_production_identity": "uniform",
            "config": config.canonical_payload(),
            "config_digest": config.digest(),
            "retention_checks": retention_checks,
        },
        "source_definition": {
            "mode_labels": MODE_LABELS,
            "basis": "[1,sqrt(2)cos(kx),sqrt(2)sin(kx),sqrt(2)cos(2kx),sqrt(2)sin(2kx)]",
            "k": 2.0 * math.pi / config.length,
            "sampling": "existing myocardium triangle centroids and cell areas",
            "unit_columns": "linear static response derivatives, not physiological unit activation",
            "comparison": "same activation RMS under the true discrete W metric",
        },
        "material_scalar": {
            "lame_lambda_myocardium": sources["lame_lambda"],
            "shear_modulus_myocardium": sources["shear_modulus"],
            "d_C_xxxx": sources["c_xxxx"],
            "myocardium_area_from_cells": float(np.sum(sources["cell_areas"])),
            "nominal_L_times_h_m": length_thickness,
        },
        "solver": {
            "factorization": "scipy.sparse.linalg.splu SuperLU",
            "factorization_count": solve["factorization_count"],
            "rhs_count": solve["rhs_count"],
            "relative_residuals": solve["relative_residuals"],
            "maximum_relative_residual": float(np.max(solve["relative_residuals"])),
            "relative_residual_tolerance": RELATIVE_RESIDUAL_TOLERANCE,
            "normwise_backward_errors": solve["backward_errors"],
            "maximum_normwise_backward_error": float(np.max(solve["backward_errors"])),
            "normwise_backward_error_tolerance": BACKWARD_ERROR_TOLERANCE,
        },
        "structural_checks": {
            "identity_relative_errors": identity_errors,
            "identity_tolerance": IDENTITY_TOLERANCE,
            "R_raw_relative_asymmetry": r_relative_asymmetry,
            "R_raw_relative_asymmetry_definition": "||R-R^T||_F/max(||R||_F,d)",
            "R_raw_relative_asymmetry_tolerance": R_ASYMMETRY_TOLERANCE,
            "W_eigenvalues": spectral["w_eigenvalues"],
            "W_condition_number": spectral["w_condition_number"],
            "spectrum_bounds": [lower_bound, upper_bound],
            "gate_checks": gate_checks,
            "all_preregistered_gates_pass": all_gates_pass,
        },
        "spectral_results": {
            "full_five_mode_generalized_eigenvalues": spectral["full_eigenvalues"],
            "full_lambda_max_is_trivial_containment_not_positive_gate": float(
                spectral["full_eigenvalues"][-1]
            ),
            "uniform_response_m0": spectral["uniform_response_m0"],
            "lambda_nonuniform": spectral["lambda_nonuniform"],
            "Delta_lambda_nonuniform_minus_m0": spectral["delta"],
            "main_nonuniform_coefficients_z": spectral["main_nonuniform_coefficients"],
            "main_nonuniform_W_norm_squared": spectral[
                "main_nonuniform_w_norm_squared"
            ],
            "main_nonuniform_discrete_mean_W0z": spectral[
                "main_nonuniform_discrete_mean"
            ],
            "main_nonuniform_eigenvalue_gap": spectral[
                "main_nonuniform_eigenvalue_gap"
            ],
            "main_nonuniform_near_degenerate": spectral[
                "main_nonuniform_near_degenerate"
            ],
            "n1_lambda_max_after_discrete_mean_removal": spectral["n1_lambda_max"],
            "n1_max_coefficients": spectral["n1_max_coefficients"],
            "mean_nonmean_coupling_W_whitened_over_d": spectral[
                "mean_nonmean_coupling_over_d"
            ],
            "generalized_eigen_residuals": {
                "constrained_residual_definition": (
                    "reduced Gram-subspace residual; the full-space residual may contain "
                    "the discrete-mean constraint multiplier"
                ),
                "full_five_mode": spectral["full_generalized_residuals"],
                "maximum_full": spectral["maximum_full_generalized_residual"],
                "main_nonuniform": spectral["main_nonuniform_generalized_residual"],
                "n1": spectral["n1_generalized_residual"],
            },
        },
        "observations": {
            "sign_convention": {
                "reported": "t_y_code=k_upper*(u_y_endo-u_y_ecm_top)",
                "physical_traction_on_endocardium": "negative of reported code-sign traction",
            },
            "normalization": "each unit column divided by sqrt(W_jj); main z satisfies z^T W z=1",
            "unit_column_macro_strain_normalized": observations[
                "macro_strain_normalized"
            ],
            "unit_column_endocardium_y_traction_metrics_normalized": {
                label: observations["column_metrics"][index]
                for index, label in enumerate(MODE_LABELS)
            },
            "main_nonuniform": {
                "macro_strain": observations["main_macro_strain"],
                "endocardium_y_traction_metrics": observations["main_metrics"],
            },
        },
        "timing": {
            "assembly_seconds": assembly_seconds,
            "factorization_seconds": solve["factor_seconds"],
            "five_rhs_solve_seconds": solve["solve_seconds"],
            "batch_numerical_elapsed_seconds_at_system_end": total_elapsed,
            "batch_numerical_budget_seconds": NUMERICAL_BUDGET_SECONDS,
        },
        "claim_boundary": {
            "static_only_s_equals_zero": True,
            "drag_and_relaxation_rate_do_not_enter_static_solution": True,
            "ecm_relaxation_time_recorded_but_not_a_memory_test": True,
            "not_equal_input_power_or_equal_macro_shortening": True,
            "not_endocardial_traction_dominance_gate": True,
            "not_feedback_instability_or_dynamic_criticality": True,
            "not_continuous_spectrum_convergence": True,
            "not_blind_and_no_holdout_read": True,
            "not_nature_physics_novelty_or_validation": True,
        },
    }
    arrays = {
        "matrix_a_data": matrix_a.data,
        "matrix_a_indices": matrix_a.indices,
        "matrix_a_indptr": matrix_a.indptr,
        "matrix_a_shape": np.asarray(matrix_a.shape, dtype=np.int64),
        "H_a": sources["matrix_h"],
        "Q": solve["matrix_q"],
        "right_hand_sides": solve["right_hand_sides"],
        "linear_residuals": solve["residual_matrix"],
        "W": sources["matrix_w"],
        "D_raw": sources["matrix_d_raw"],
        "R_raw": matrix_r_raw,
        "R_symmetric": spectral["matrix_r_symmetric"],
        "R_whitened": spectral["matrix_whitened"],
        "full_eigenvalues": spectral["full_eigenvalues"],
        "full_eigenvectors": spectral["full_eigenvectors"],
        "nonuniform_eigenvalues": spectral["nonuniform_eigenvalues"],
        "main_nonuniform_coefficients_z": spectral["main_nonuniform_coefficients"],
        "n1_eigenvalues": spectral["n1_eigenvalues"],
        "n1_max_coefficients": spectral["n1_max_coefficients"],
        "basis_phi_at_myocardium_cell_centroids": sources["basis_phi"],
        "myocardium_cell_centroid_x": sources["cell_x"],
        "myocardium_cell_areas": sources["cell_areas"],
        "x_interface_nodes": observations["x_interface"],
        "column_input_rms_sqrt_Wjj": observations["normalizers"],
        "macro_strain_unit_columns_raw": observations["macro_strain_raw"],
        "macro_strain_unit_columns_normalized": observations[
            "macro_strain_normalized"
        ],
        "endocardium_y_traction_code_unit_columns_raw": observations[
            "traction_y_code_raw"
        ],
        "endocardium_y_traction_code_unit_columns_normalized": observations[
            "traction_y_code_normalized"
        ],
        "main_nonuniform_state": observations["main_state"],
        "main_nonuniform_endocardium_y_traction_code": observations[
            "main_traction_y_code"
        ],
    }
    return system_json, arrays


def _source_ledger(repo_root: Path) -> dict[str, dict[str, str]]:
    paths = (PLAN_RELATIVE, BRIEF_RELATIVE, *SOURCE_RELATIVES, Path(__file__).resolve().relative_to(repo_root))
    return {
        path.as_posix(): {"sha256": _sha256(repo_root / path)}
        for path in paths
    }


def _write_final_files(
    *,
    output_directory: Path,
    repo_root: Path,
    status: str,
    records: list[dict[str, Any]],
    file_paths: list[Path],
    numerical_elapsed: float,
    failure: dict[str, Any] | None,
    self_test: dict[str, Any],
) -> None:
    by_thickness: list[dict[str, Any]] = []
    if status == "COMPLETED_STATIC_SCREEN_NO_SCIENTIFIC_PASS_GATE":
        lookup = {
            (float(record["system"]["thickness_ratio_H"]), record["system"]["spatial_label"]): record
            for record in records
        }
        for thickness_ratio in THICKNESS_RATIOS:
            coarse = lookup[(thickness_ratio, "S2")]["spectral_results"]
            fine = lookup[(thickness_ratio, "S3")]["spectral_results"]
            c_xxxx = next(
                record["material_scalar"]["d_C_xxxx"]
                for record in records
                if float(record["system"]["thickness_ratio_H"]) == thickness_ratio
            )
            error_proxy = abs(
                fine["lambda_nonuniform"] - coarse["lambda_nonuniform"]
            ) + abs(fine["uniform_response_m0"] - coarse["uniform_response_m0"])
            floor = 1.0e-12 * c_xxxx
            threshold = 2.0 * max(error_proxy, floor)
            delta_fine = fine["Delta_lambda_nonuniform_minus_m0"]
            if delta_fine > threshold:
                classification = "STATIC_NONUNIFORM_CANDIDATE"
            elif delta_fine < -threshold:
                classification = "UNIFORM_DOMINANT_IN_TESTED_SUBSPACE"
            else:
                classification = "INCONCLUSIVE"
            by_thickness.append(
                {
                    "thickness_ratio_H": thickness_ratio,
                    "m0_S2": coarse["uniform_response_m0"],
                    "m0_S3": fine["uniform_response_m0"],
                    "lambda_non_S2": coarse["lambda_nonuniform"],
                    "lambda_non_S3": fine["lambda_nonuniform"],
                    "Delta_S2": coarse["Delta_lambda_nonuniform_minus_m0"],
                    "Delta_S3": delta_fine,
                    "E_delta": error_proxy,
                    "floor_1e_minus_12_d": floor,
                    "two_times_max_error_or_floor": threshold,
                    "classification": classification,
                }
            )

    positive_count = sum(
        item["classification"] == "STATIC_NONUNIFORM_CANDIDATE"
        for item in by_thickness
    )
    continuation = (
        "CANDIDATE_REQUIRES_SOURCE_EXPLANATION_NO_FEEDBACK_AUTHORIZED"
        if positive_count > 0
        else "STOP_STATIC_PRIORITY_SMALL_SCOPE_CLAIM_PER_PREREGISTRATION"
    ) if by_thickness else "STOPPED_FAIL_CLOSED_BEFORE_THREE_STATE_DECISION"
    summary = {
        "schema": SCHEMA,
        "status": status,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "scientific_question": (
            "Does a finite zero-discrete-mean activation subspace have a larger static "
            "energy-conjugate mean-myocardial-stress response than uniform activation?"
        ),
        "frozen_inputs": {
            "preregistration_and_frozen_production_baseline": EXPECTED_CODE_VERSION,
            "actual_checkout_at_launch": EXPECTED_LAUNCH_CHECKOUT,
            "identity_drift_decision": (
                "actual checkout differs only by the dispatched-task CURRENT_STATUS record; "
                "scientific files and direct production sources are byte-locked"
            ),
            "plan_path": PLAN_RELATIVE.as_posix(),
            "plan_sha256": PLAN_SHA256,
            "brief_path": BRIEF_RELATIVE.as_posix(),
            "brief_sha256": BRIEF_SHA256,
            "H": THICKNESS_RATIOS,
            "spatial_labels": SPATIAL_LABELS,
            "mode_labels": MODE_LABELS,
            "s": 0.0,
        },
        "execution_count_ledger": {
            "old_completed_periodic_cases": 46,
            "new_completed_static_system_assemblies": len(records),
            "new_completed_static_rhs": 5 * len(records),
            "counts_are_not_equivalent_cases": True,
        },
        "three_state_decisions": by_thickness,
        "positive_candidate_count": positive_count,
        "continuation_rule_result": continuation,
        "failure": failure,
        "resource_accounting": {
            "batch_numerical_elapsed_seconds": numerical_elapsed,
            "batch_budget_seconds": NUMERICAL_BUDGET_SECONDS,
            "old_fem_and_failure_charge_seconds": OLD_FEM_AND_FAILURE_CHARGE_SECONDS,
            "project_cumulative_fem_and_failure_charge_seconds": (
                OLD_FEM_AND_FAILURE_CHARGE_SECONDS + numerical_elapsed
            ),
            "project_stop_reestimate_seconds": PROJECT_STOP_REESTIMATE_SECONDS,
            "cpu_limit": 1,
            "memory_limit_gib": 8,
            "gpu": "not_used",
            "network": "disabled_by_container",
        },
        "all_completed_system_structure_gates_pass": bool(
            records
            and all(
                record["structural_checks"]["all_preregistered_gates_pass"]
                for record in records
            )
        ),
        "self_test": self_test,
        "next_gate": "SUPERVISOR_REVIEW_STOP",
        "claim_boundary": {
            "finite_five_mode_static_screen_only": True,
            "full_five_dimensional_lambda_max_not_used_as_positive_gate": True,
            "not_a_strict_discretization_error_bound": True,
            "not_feedback_dynamics_or_pole_analysis": True,
            "not_equal_power_or_equal_shortening": True,
            "not_ecm_memory_selection": True,
            "not_holdout_or_blind_prediction": True,
            "not_a_paper_pass_or_nature_physics_novelty": True,
            "no_automatic_v02_extra_points_or_feedback": True,
        },
    }
    summary_path = output_directory / "summary.json"
    _write_json_exclusive(summary_path, summary)
    file_paths.append(summary_path)
    result_ledger = {
        path.relative_to(output_directory).as_posix(): {
            "sha256": _sha256(path),
            "bytes": path.stat().st_size,
        }
        for path in file_paths
    }
    manifest = {
        "schema": SCHEMA,
        "status": status,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "frozen_code_version": EXPECTED_CODE_VERSION,
        "actual_checkout_at_launch": EXPECTED_LAUNCH_CHECKOUT,
        "trial_runner_identity": {
            "path": Path(__file__).resolve().relative_to(repo_root).as_posix(),
            "sha256": _sha256(Path(__file__).resolve()),
            "not_claimed_to_exist_in_frozen_baseline": True,
        },
        "source_ledger": _source_ledger(repo_root),
        "result_ledger_excluding_manifest": result_ledger,
        "container_contract": {
            "image": EXPECTED_IMAGE,
            "image_id": EXPECTED_IMAGE_ID,
            "container_name": EXPECTED_CONTAINER_NAME,
            "pythonpath": EXPECTED_PYTHONPATH,
            "root_filesystem": "read_only",
            "project_mount": "read_only_except_exact_result_bind",
            "docker_socket": "not_mounted",
            "network": "none",
            "gpu": "not_used",
            "cpu_limit": 1,
            "memory_limit_gib": 8,
        },
        "runtime": {
            "python": platform.python_version(),
            "numpy": np.__version__,
            "scipy": __import__("scipy").__version__,
            "pythonpath_observed": os.environ.get("PYTHONPATH"),
            "thread_environment": {
                name: os.environ.get(name)
                for name in (
                    "OMP_NUM_THREADS",
                    "OPENBLAS_NUM_THREADS",
                    "MKL_NUM_THREADS",
                    "NUMEXPR_NUM_THREADS",
                )
            },
        },
        "evidence_boundary": {
            "original_four_holdouts": "LOCKED_NOT_READ",
            "no_periodic_or_frequency_solution": True,
            "no_feedback_implementation": True,
            "no_production_api_or_default_change": True,
            "no_plot_or_extra_report_tree": True,
            "npz_not_for_git": True,
        },
    }
    _write_json_exclusive(output_directory / "manifest.json", manifest)


def run(output_directory: Path, code_version: str) -> int:
    repo_root = Path(__file__).resolve().parents[1]
    expected_output = (repo_root / RESULT_RELATIVE).resolve()
    if output_directory.resolve() != expected_output:
        raise RuntimeError("output boundary mismatch")
    if not output_directory.is_dir():
        raise RuntimeError("exact precreated result directory is required")
    if any(output_directory.iterdir()):
        raise RuntimeError("result directory is not empty; create-only contract failed")
    if code_version != EXPECTED_CODE_VERSION:
        raise RuntimeError("frozen code version mismatch")
    if os.environ.get("PAPER2_STATIC_ACTUAL_CHECKOUT") != EXPECTED_LAUNCH_CHECKOUT:
        raise RuntimeError("actual launch checkout identity mismatch")
    if _sha256(repo_root / PLAN_RELATIVE) != PLAN_SHA256:
        raise RuntimeError("frozen main-plan hash mismatch")
    if _sha256(repo_root / BRIEF_RELATIVE) != BRIEF_SHA256:
        raise RuntimeError("frozen science-brief hash mismatch")
    for relative_path, expected_hash in EXPECTED_PRODUCTION_SOURCE_HASHES.items():
        if _sha256(repo_root / relative_path) != expected_hash:
            raise RuntimeError(f"frozen direct production source hash mismatch: {relative_path}")
    if os.environ.get("PYTHONPATH") != EXPECTED_PYTHONPATH:
        raise RuntimeError("frozen container PYTHONPATH mismatch")
    for variable in (
        "OMP_NUM_THREADS",
        "OPENBLAS_NUM_THREADS",
        "MKL_NUM_THREADS",
        "NUMEXPR_NUM_THREADS",
    ):
        if os.environ.get(variable) != "1":
            raise RuntimeError(f"single-CPU thread environment mismatch: {variable}")
    self_test = _self_test()
    if not self_test["pass"]:
        raise RuntimeError("static P1/spectral self-test failed")

    from paper2_hybrid import config as config_module
    from paper2_hybrid import model as model_module

    active_config = config_module.ACTIVE_CONFIG
    if not (
        active_config.length == 1.0
        and active_config.myocardium_thickness == 0.2
        and active_config.period == 1.0
        and active_config.endocardial_axial_stiffness == 0.8
    ):
        raise RuntimeError("ACTIVE_CONFIG fixed-input drift")

    records: list[dict[str, Any]] = []
    file_paths: list[Path] = []
    failure: dict[str, Any] | None = None
    numerical_start = time.perf_counter()
    try:
        for thickness_ratio in THICKNESS_RATIOS:
            for spatial_label in SPATIAL_LABELS:
                system_name = _system_name(thickness_ratio, spatial_label)
                system_json, arrays = _execute_system(
                    model_module=model_module,
                    active_config=active_config,
                    thickness_ratio=thickness_ratio,
                    spatial_label=spatial_label,
                    numerical_start=numerical_start,
                )
                npz_path = output_directory / f"{system_name}.npz"
                _write_npz_exclusive(npz_path, arrays)
                system_json["npz"] = {
                    "path": npz_path.relative_to(repo_root).as_posix(),
                    "sha256": _sha256(npz_path),
                    "bytes": npz_path.stat().st_size,
                }
                json_path = output_directory / f"{system_name}.json"
                _write_json_exclusive(json_path, system_json)
                file_paths.extend((npz_path, json_path))
                records.append(system_json)
                if not system_json["structural_checks"]["all_preregistered_gates_pass"]:
                    failure = {
                        "type": "PREREGISTERED_STRUCTURE_GATE_FAILURE",
                        "system": system_name,
                        "message": "stopped before any later assembly; no tolerance change or retry",
                    }
                    break
            if failure is not None:
                break
        numerical_elapsed = time.perf_counter() - numerical_start
        if numerical_elapsed > NUMERICAL_BUDGET_SECONDS and failure is None:
            failure = {
                "type": "NUMERICAL_BUDGET_EXCEEDED",
                "elapsed_seconds": numerical_elapsed,
                "budget_seconds": NUMERICAL_BUDGET_SECONDS,
                "message": "no automatic retry or extension",
            }
    except BaseException as error:
        numerical_elapsed = time.perf_counter() - numerical_start
        failure = {
            "type": type(error).__name__,
            "message": str(error),
            "stopped_after_completed_systems": len(records),
            "no_automatic_retry_or_extension": True,
        }

    if _sha256(repo_root / PLAN_RELATIVE) != PLAN_SHA256:
        failure = {"type": "MAIN_PLAN_CHANGED_DURING_EXECUTION", "no_retry": True}
    if _sha256(repo_root / BRIEF_RELATIVE) != BRIEF_SHA256:
        failure = {"type": "SCIENCE_BRIEF_CHANGED_DURING_EXECUTION", "no_retry": True}
    for relative_path, expected_hash in EXPECTED_PRODUCTION_SOURCE_HASHES.items():
        if _sha256(repo_root / relative_path) != expected_hash:
            failure = {
                "type": "DIRECT_PRODUCTION_SOURCE_CHANGED_DURING_EXECUTION",
                "path": relative_path,
                "no_retry": True,
            }
    completed = failure is None and len(records) == 6
    status = (
        "COMPLETED_STATIC_SCREEN_NO_SCIENTIFIC_PASS_GATE"
        if completed
        else "ABORTED_FAIL_CLOSED"
    )
    _write_final_files(
        output_directory=output_directory,
        repo_root=repo_root,
        status=status,
        records=records,
        file_paths=file_paths,
        numerical_elapsed=numerical_elapsed,
        failure=failure,
        self_test=self_test,
    )
    if completed:
        print(
            f"STATIC_SCREEN_DONE assemblies=6 rhs=30 elapsed={numerical_elapsed:.6f}",
            flush=True,
        )
        return 0
    print(f"STATIC_SCREEN_ABORTED {failure}", file=sys.stderr, flush=True)
    return 1


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--code-version")
    arguments = parser.parse_args()
    if arguments.self_test:
        report = _self_test()
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0 if report["pass"] else 1
    if arguments.output is None or arguments.code_version is None:
        parser.error("--output and --code-version are required unless --self-test is used")
    return run(arguments.output, arguments.code_version)


if __name__ == "__main__":
    sys.exit(main())
