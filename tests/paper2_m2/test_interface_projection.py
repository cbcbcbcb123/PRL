from __future__ import annotations

import numpy as np

from paper2_m2.interface_projection import (
    common_segment_integral,
    constant_traction_projection_manufactured_check,
    piecewise_linear_integral,
    project_piecewise_linear_to_common_segments,
)


def test_constant_traction_manufactured_checks_pass_for_s2_and_s3() -> None:
    for native_segments in (32, 64):
        result = constant_traction_projection_manufactured_check(
            native_segments=native_segments,
            common_segments=32,
        )
        assert result["pass"] is True
        assert result["sign_preserved"] is True
        assert result["integrated_force_abs_error"] <= 1.0e-12
        assert result["discrete_interface_work_abs_error"] <= 1.0e-12


def test_projection_conserves_each_component_for_nonconstant_field() -> None:
    native_x = np.linspace(-0.5, 0.5, 65)
    common_x = np.linspace(-0.5, 0.5, 33)
    values = np.column_stack(
        (
            1.0 + native_x + 0.2 * native_x**2,
            -0.5 + 0.3 * native_x - native_x**3,
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


def test_projection_rejects_non_nested_common_grid() -> None:
    native_x = np.linspace(-0.5, 0.5, 65)
    common_x = np.linspace(-0.5, 0.5, 34)
    values = np.ones((65, 2))
    try:
        project_piecewise_linear_to_common_segments(native_x, values, common_x)
    except ValueError as error:
        assert "nested" in str(error)
    else:
        raise AssertionError("non-nested projection must fail")
