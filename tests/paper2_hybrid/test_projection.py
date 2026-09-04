from __future__ import annotations

import numpy as np

from paper2_hybrid.projection import (
    common_segment_integral,
    constant_traction_projection_manufactured_check,
    piecewise_linear_integral,
    project_piecewise_linear_to_common_segments,
)


def test_constant_projection_manufactured_check() -> None:
    result = constant_traction_projection_manufactured_check(
        native_segments=128, common_segments=64
    )
    assert result["pass"] is True


def test_projection_preserves_vector_integral() -> None:
    native_x = np.linspace(-0.5, 0.5, 129)
    common_x = np.linspace(-0.5, 0.5, 65)
    values = np.column_stack((1.2 + 0.3 * native_x, -0.4 + 0.2 * native_x))
    projected = project_piecewise_linear_to_common_segments(
        native_x, values, common_x
    )
    np.testing.assert_allclose(
        common_segment_integral(common_x, projected),
        piecewise_linear_integral(native_x, values),
        atol=1.0e-14,
        rtol=0.0,
    )
