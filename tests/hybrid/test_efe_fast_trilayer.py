from __future__ import annotations

import numpy as np
import pytest

from hybrid.efe_fast_trilayer import (
    build_fast_trilayer_model,
    evaluate_fast_trilayer_state,
    reference_evaluation,
    rigidly_transform_model,
)
from route_h.geometry import triangle_geometry


@pytest.fixture(scope="module")
def model():
    return build_fast_trilayer_model(dcm_level="D0", ecm_level="E0")


def test_n1_1_reference_geometry_is_a_true_shared_three_layer(model) -> None:
    assert model.myocyte.vertices.shape == (162, 3)
    assert model.endocardium.vertices.shape == (162, 3)
    assert model.myocyte.faces.shape == (320, 3)
    assert model.endocardium.faces.shape == (320, 3)
    assert model.ecm_reference.vertices.shape == (150, 3)
    assert model.ecm_reference.tetrahedra.shape == (480, 4)
    assert len(model.myocyte_interface.tethers) > 0
    assert len(model.endocardial_interface.tethers) > 0
    assert np.intersect1d(
        model.myocyte_interface.registry.point_ids,
        model.endocardial_interface.registry.point_ids,
    ).size == 0
    assert model.ecm_reference is not None
    assert np.ptp(model.myocyte.vertices[:, 1]) == pytest.approx(0.60)
    assert np.ptp(model.endocardium.vertices[:, 1]) == pytest.approx(0.20)
    assert model.jelly_thickness == pytest.approx(0.30)
    assert model.ecm_footprint_scale == pytest.approx(1.0)
    assert model.ecm_divisions == (5, 4, 4)


@pytest.mark.parametrize(
    ("scale", "expected_span", "expected_divisions", "vertex_count", "tet_count"),
    (
        (1.5, (1.50, 0.30, 0.84), (8, 4, 6), 315, 1152),
        (2.0, (2.00, 0.30, 1.12), (10, 4, 8), 495, 1920),
    ),
)
def test_n1_1a_wide_footprint_preserves_thickness_and_element_size(
    model,
    scale,
    expected_span,
    expected_divisions,
    vertex_count,
    tet_count,
) -> None:
    wide = build_fast_trilayer_model(
        dcm_level="D0",
        ecm_level="E0",
        ecm_footprint_scale=scale,
    )
    assert np.ptp(wide.ecm_reference.vertices, axis=0) == pytest.approx(
        expected_span
    )
    assert wide.ecm_divisions == expected_divisions
    assert len(wide.ecm_reference.vertices) == vertex_count
    assert len(wide.ecm_reference.tetrahedra) == tet_count
    assert np.ptp(wide.myocyte.vertices, axis=0) == pytest.approx(
        np.ptp(model.myocyte.vertices, axis=0)
    )
    assert np.ptp(wide.endocardium.vertices, axis=0) == pytest.approx(
        np.ptp(model.endocardium.vertices, axis=0)
    )
    assert len(wide.myocyte_interface.tethers) == len(
        model.myocyte_interface.tethers
    )
    assert len(wide.endocardial_interface.tethers) == len(
        model.endocardial_interface.tethers
    )
    reference = reference_evaluation(wide)
    assert np.linalg.norm(reference.myocyte_force) <= 1.0e-12
    assert np.linalg.norm(reference.ecm_force) <= 1.0e-12
    assert np.linalg.norm(reference.endocardial_force) <= 1.0e-12
    assert reference.minimum_ecm_jacobian == pytest.approx(1.0, abs=1.0e-14)


def test_m0_reference_state_has_zero_force_and_valid_geometry(model) -> None:
    evaluation = reference_evaluation(model)
    assert np.linalg.norm(evaluation.myocyte_force) <= 1.0e-12
    assert np.linalg.norm(evaluation.ecm_force) <= 1.0e-12
    assert np.linalg.norm(evaluation.endocardial_force) <= 1.0e-12
    assert evaluation.myocyte_volume_ratio == pytest.approx(1.0, abs=1.0e-14)
    assert evaluation.endocardial_volume_ratio == pytest.approx(1.0, abs=1.0e-14)
    assert evaluation.minimum_ecm_jacobian == pytest.approx(1.0, abs=1.0e-14)
    assert evaluation.maximum_ecm_jacobian == pytest.approx(1.0, abs=1.0e-14)
    frozen_reference_gap = min(
        *(tether.reference_gap for tether in model.myocyte_interface.tethers),
        *(tether.reference_gap for tether in model.endocardial_interface.tethers),
    )
    assert evaluation.minimum_gap == pytest.approx(
        frozen_reference_gap, abs=1.0e-14
    )
    assert evaluation.pair_force_residual_mj <= 1.0e-12
    assert evaluation.pair_moment_residual_mj <= 1.0e-12
    assert evaluation.pair_force_residual_je <= 1.0e-12
    assert evaluation.pair_moment_residual_je <= 1.0e-12


def test_m1_complete_reference_is_rigidly_objective(model) -> None:
    angle = 0.37
    rotation = np.asarray(
        [
            [np.cos(angle), -np.sin(angle), 0.0],
            [np.sin(angle), np.cos(angle), 0.0],
            [0.0, 0.0, 1.0],
        ]
    )
    transformed = rigidly_transform_model(
        model,
        rotation,
        np.asarray([0.3, -0.2, 0.4]),
    )
    baseline = reference_evaluation(model)
    moved = reference_evaluation(transformed)
    assert moved.total_stored_energy == pytest.approx(
        baseline.total_stored_energy, abs=1.0e-12
    )
    assert np.linalg.norm(moved.myocyte_force) <= 1.0e-12
    assert np.linalg.norm(moved.ecm_force) <= 1.0e-12
    assert np.linalg.norm(moved.endocardial_force) <= 1.0e-12


def test_m3_and_m7_both_interfaces_close_force_and_moment(model) -> None:
    myocyte = model.myocyte.vertices.copy()
    endocardium = model.endocardium.vertices.copy()
    ecm = model.ecm_reference.vertices.copy()
    ecm[:, 0] += 2.0e-4 * (
        ecm[:, 1] - float(ecm[:, 1].mean())
    ) / model.jelly_thickness
    evaluation = evaluate_fast_trilayer_state(
        model,
        myocyte,
        ecm,
        endocardium,
    )
    assert evaluation.pair_force_residual_mj <= 1.0e-10
    assert evaluation.pair_moment_residual_mj <= 1.0e-10
    assert evaluation.pair_force_residual_je <= 1.0e-10
    assert evaluation.pair_moment_residual_je <= 1.0e-10
    internal_resultant = (
        evaluation.myocyte_force.sum(axis=0)
        + evaluation.ecm_force.sum(axis=0)
        + evaluation.endocardial_force.sum(axis=0)
        - evaluation.support_force.sum(axis=0)
    )
    assert np.linalg.norm(internal_resultant) <= 1.0e-10


def test_m4_stored_energy_directional_derivative(model) -> None:
    rng = np.random.default_rng(20260817)
    myocyte_vertices = model.myocyte.vertices.copy()
    ecm_vertices = model.ecm_reference.vertices.copy()
    endocardial_vertices = model.endocardium.vertices.copy()
    myocyte_vertices[:, 0] += 0.002 * model.myocyte.vertices[:, 1]
    ecm_vertices[:, 0] += 0.004 * model.ecm_reference.vertices[:, 1]
    endocardial_vertices[:, 0] += 0.003 * model.endocardium.vertices[:, 1]
    myocyte_direction = rng.normal(size=model.myocyte.vertices.shape)
    ecm_direction = rng.normal(size=model.ecm_reference.vertices.shape)
    endocardial_direction = rng.normal(size=model.endocardium.vertices.shape)
    directions = (myocyte_direction, ecm_direction, endocardial_direction)
    norm = np.sqrt(sum(float(np.sum(value * value)) for value in directions))
    directions = tuple(value / norm for value in directions)
    epsilon = 1.0e-7

    def energy(sign: float) -> float:
        return evaluate_fast_trilayer_state(
            model,
            myocyte_vertices + sign * epsilon * directions[0],
            ecm_vertices + sign * epsilon * directions[1],
            endocardial_vertices + sign * epsilon * directions[2],
            reject_penetration=False,
        ).total_stored_energy

    evaluation = evaluate_fast_trilayer_state(
        model,
        myocyte_vertices,
        ecm_vertices,
        endocardial_vertices,
        reject_penetration=False,
    )
    analytic = float(
        np.sum(evaluation.myocyte_energy_gradient * directions[0])
        + np.sum(evaluation.ecm_energy_gradient * directions[1])
        + np.sum(evaluation.endocardial_energy_gradient * directions[2])
    )
    finite_difference = (energy(1.0) - energy(-1.0)) / (2.0 * epsilon)
    relative_error = abs(finite_difference - analytic) / max(
        1.0e-12, abs(finite_difference), abs(analytic)
    )
    assert relative_error <= 1.0e-5


def test_m8_pressure_and_wss_are_applied_only_to_lumen_faces(model) -> None:
    pressure = 0.05
    wss = np.asarray([0.02, 0.0, 0.0])
    evaluation = evaluate_fast_trilayer_state(
        model,
        model.myocyte.vertices,
        model.ecm_reference.vertices,
        model.endocardium.vertices,
        pressure=pressure,
        wss_command=wss,
    )
    selected_faces = model.endocardium.faces[model.endocardial_lumen_face_ids]
    areas, normals = triangle_geometry(model.endocardium.vertices, selected_faces)
    expected_pressure = np.sum(-pressure * areas[:, None] * normals, axis=0)
    tangential = wss - normals * (normals @ wss)[:, None]
    expected_wss = np.sum(areas[:, None] * tangential, axis=0)
    assert evaluation.pressure_force.sum(axis=0) == pytest.approx(
        expected_pressure, abs=1.0e-12
    )
    assert evaluation.wss_force.sum(axis=0) == pytest.approx(
        expected_wss, abs=1.0e-12
    )
    assert np.linalg.norm(evaluation.pressure_force) > 0.0
    assert np.linalg.norm(evaluation.wss_force) > 0.0
    assert np.linalg.norm(evaluation.myocyte_force) <= 1.0e-12
    assert np.linalg.norm(evaluation.ecm_force) <= 1.0e-12
