from __future__ import annotations

import numpy as np

from route_h.dcm_cell import (
    _hinge_angle_gradient,
    _hinge_angle_gradients_bulk,
    build_cell_reference,
)


def test_vectorized_hinges_match_sealed_scalar_kernel(bundle):
    arrays, _ = bundle
    cell_id = 6
    vertices = arrays["cell_vertices"][cell_id]
    reference = build_cell_reference(
        vertices,
        arrays["cell_faces"][cell_id],
        arrays["cell_primary_identity"][cell_id],
        arrays["cell_directional_identity"][cell_id],
    )
    rng = np.random.default_rng(20260731)
    perturbed = vertices + 1.0e-4 * rng.standard_normal(vertices.shape)
    local = perturbed[reference.hinges.vertices]
    vector_angles, vector_gradients = _hinge_angle_gradients_bulk(local)
    scalar = [_hinge_angle_gradient(item) for item in local]
    scalar_angles = np.asarray([item[0] for item in scalar])
    scalar_gradients = np.asarray([item[1] for item in scalar])
    assert np.allclose(vector_angles, scalar_angles, rtol=0.0, atol=5.0e-16)
    assert np.allclose(
        vector_gradients,
        scalar_gradients,
        rtol=0.0,
        atol=1.0e-14,
    )
