from __future__ import annotations

import numpy as np

from paper2_m2.interface_projection import (
    common_segment_integral,
    constant_traction_projection_manufactured_check,
    piecewise_linear_integral,
    project_piecewise_linear_to_common_segments,
)


def test_s4_common_projection_manufactured_checks_pass() -> None:
    for native_segments in (64, 128):
        result = constant_traction_projection_manufactured_check(
            native_segments=native_segments,
            common_segments=64,
        )
        assert result["pass"] is True
        assert result["sign_preserved"] is True
        assert result["integrated_force_abs_error"] <= 1.0e-12
        assert result["discrete_interface_work_abs_error"] <= 1.0e-12


def test_s4_projection_conserves_nonconstant_vector_traction() -> None:
    native_x = np.linspace(-0.5, 0.5, 129)
    common_x = np.linspace(-0.5, 0.5, 65)
    values = np.column_stack(
        (
            0.7 + 0.4 * native_x + 0.3 * native_x**2,
            -0.2 + 0.6 * native_x - 0.5 * native_x**3,
        )
    )
    projected = project_piecewise_linear_to_common_segments(
        native_x, values, common_x
    )
    np.testing.assert_allclose(
        common_segment_integral(common_x, projected),
        piecewise_linear_integral(native_x, values),
        atol=1.0e-14,
        rtol=1.0e-14,
    )


def test_s4_projection_rejects_non_nested_common_grid() -> None:
    native_x = np.linspace(-0.5, 0.5, 129)
    common_x = np.linspace(-0.5, 0.5, 66)
    values = np.ones((129, 2))
    try:
        project_piecewise_linear_to_common_segments(native_x, values, common_x)
    except ValueError as error:
        assert "nested" in str(error)
    else:
        raise AssertionError("non-nested projection must fail")
