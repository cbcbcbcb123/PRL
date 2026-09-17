"""Objective 3-D isochoric hyperelastic material points and exact tangents.

This module supplies no volumetric penalty or pressure term: those belong to
the mixed displacement-pressure formulation.  All moduli remain in the same
arbitrary stress unit until independently calibrated.

``tangent[..., i, J, k, L]`` is the derivative of the first Piola stress
``P[..., i, J]`` with respect to ``F[..., k, L]``.  Both passive models use
``Cbar = det(F)**(-2/3) F.T F``.  The optional active term is specifically a
*Lagrangian*, energy-consistent tension, not a constant Cauchy fiber tension:
``W_active = T / 2 * (|F f0|**2 - 1)``.
"""

from collections.abc import Mapping

import numpy as np


def _parameter(material, name, *, allow_zero=False, default=None):
    value = material.get(name, default)
    if isinstance(value, (bool, np.bool_)):
        raise ValueError(f"{name} must be a finite real material parameter")
    try:
        value = float(value)
    except (TypeError, ValueError, OverflowError) as error:
        raise ValueError(f"{name} must be a finite real material parameter") from error
    if not np.isfinite(value) or value < 0.0 or (not allow_zero and value == 0.0):
        qualifier = "nonnegative" if allow_zero else "positive"
        raise ValueError(f"{name} must be finite and {qualifier}")
    return value


def _fiber_frame(fiber):
    supplied = np.asarray([1.0, 0.0, 0.0] if fiber is None else fiber)
    if np.iscomplexobj(supplied):
        raise ValueError("fiber must be a finite real vector of length three")
    direction = np.asarray(supplied, dtype=float)
    if direction.shape != (3,) or not np.all(np.isfinite(direction)):
        raise ValueError("fiber must be a finite real vector of length three")
    # Rescaling first avoids overflow/underflow when normalizing a valid vector.
    scale = np.max(np.abs(direction))
    if scale == 0.0:
        raise ValueError("fiber must be nonzero")
    direction = direction / scale
    direction /= np.linalg.norm(direction)
    auxiliary = np.eye(3)[np.argmin(np.abs(direction))]
    sheet = auxiliary - np.dot(auxiliary, direction) * direction
    sheet /= np.linalg.norm(sheet)
    normal = np.cross(direction, sheet)
    return np.column_stack((direction, sheet, normal))


def material_response(F, material, fiber=None):
    """Return batched ``energy``, ``P``, ``tangent``, and ``J`` arrays.

    Parameters
    ----------
    F : array_like, shape (..., 3, 3)
        Real deformation gradients with finite, strictly positive determinant.
    material : mapping
        ``{'model': 'neo_hookean', 'mu': positive}`` or
        ``{'model': 'guccione', 'C': positive, 'bff': positive,
        'bxx': positive, 'bfx': positive}``.  Either accepts optional
        ``active_tension >= 0`` (default zero).  Unused application metadata is
        permitted.  Guccione is transversely isotropic about ``fiber``.
    fiber : array_like, shape (3,), optional
        Uniform reference fiber direction, normalized internally.  Defaults to
        the first Cartesian axis.  It is not the deformed spatial direction.

    Notes
    -----
    With ``Ebar=(Cbar-I)/2`` expressed in a fiber/sheet/normal basis,
    ``Q=bff*Eff**2 + bxx*(Ess**2+Enn**2+Esn**2+Ens**2)
    + bfx*(Efs**2+Esf**2+Efn**2+Enf**2)`` and
    ``W_guccione=C/2*expm1(Q)``.  The doubled off-diagonal contributions are
    intentional.  Nine vectorized analytic directional derivatives assemble
    the exact material tangent; no numerical differencing is used here.
    """
    if not isinstance(material, Mapping):
        raise ValueError("material must be a mapping")
    model = material.get("model")
    if model not in ("neo_hookean", "guccione"):
        raise ValueError("model must be 'neo_hookean' or 'guccione'")
    tension = _parameter(material, "active_tension", allow_zero=True, default=0.0)
    frame = _fiber_frame(fiber)
    f0 = frame[:, 0]
    supplied = np.asarray(F)
    if np.iscomplexobj(supplied):
        raise ValueError("F must contain finite real deformation gradients")
    gradient = np.asarray(supplied, dtype=float)
    if gradient.ndim < 2 or gradient.shape[-2:] != (3, 3):
        raise ValueError("F must have shape (..., 3, 3)")
    if not np.all(np.isfinite(gradient)):
        raise ValueError("F must contain finite real deformation gradients")
    determinant = np.linalg.det(gradient)
    if not np.all(np.isfinite(determinant)) or np.any(determinant <= 0.0):
        raise ValueError("F must have a finite strictly positive determinant")

    inverse_transpose = np.swapaxes(np.linalg.inv(gradient), -1, -2)
    right_cauchy_green = np.swapaxes(gradient, -1, -2) @ gradient
    isochoric_factor = determinant ** (-2.0 / 3.0)
    cbar = isochoric_factor[..., None, None] * right_cauchy_green
    identity = np.eye(3)

    with np.errstate(over="raise", invalid="raise", divide="raise"):
        try:
            if model == "neo_hookean":
                modulus = _parameter(material, "mu")
                energy = 0.5 * modulus * (np.trace(cbar, axis1=-2, axis2=-1) - 3.0)
                sbar = np.broadcast_to(modulus * identity, gradient.shape)
                local_weighted_strain = None
            else:
                modulus = _parameter(material, "C")
                bff = _parameter(material, "bff")
                bxx = _parameter(material, "bxx")
                bfx = _parameter(material, "bfx")
                weights = np.array([[bff, bfx, bfx], [bfx, bxx, bxx], [bfx, bxx, bxx]])
                local_strain = frame.T @ (0.5 * (cbar - identity)) @ frame
                local_weighted_strain = weights * local_strain
                exponent = np.sum(local_weighted_strain * local_strain, axis=(-2, -1))
                exponential = np.exp(exponent)
                energy = 0.5 * modulus * np.expm1(exponent)
                sbar = (modulus * exponential)[..., None, None] * (
                    frame @ local_weighted_strain @ frame.T
                )

            contraction = np.sum(sbar * right_cauchy_green, axis=(-2, -1))
            projected_stress = gradient @ sbar - (
                contraction / 3.0
            )[..., None, None] * inverse_transpose
            first_piola = isochoric_factor[..., None, None] * projected_stress
            tangent = np.empty(gradient.shape[:-2] + (3, 3, 3, 3), dtype=float)

            for spatial_index in range(3):
                for reference_index in range(3):
                    direction = np.zeros((3, 3))
                    direction[spatial_index, reference_index] = 1.0
                    logarithmic_j_variation = inverse_transpose[..., spatial_index, reference_index]
                    factor_variation = -(2.0 / 3.0) * isochoric_factor * logarithmic_j_variation
                    c_variation = direction.T @ gradient + np.swapaxes(gradient, -1, -2) @ direction
                    if local_weighted_strain is None:
                        sbar_variation = np.zeros_like(gradient)
                    else:
                        cbar_variation = isochoric_factor[..., None, None] * (
                            c_variation
                            - (2.0 / 3.0) * logarithmic_j_variation[..., None, None] * right_cauchy_green
                        )
                        strain_variation = frame.T @ (0.5 * cbar_variation) @ frame
                        exponent_variation = 2.0 * np.sum(
                            local_weighted_strain * strain_variation, axis=(-2, -1)
                        )
                        weighted_variation = weights * strain_variation + (
                            exponent_variation[..., None, None] * local_weighted_strain
                        )
                        sbar_variation = (modulus * exponential)[..., None, None] * (
                            frame @ weighted_variation @ frame.T
                        )
                    contraction_variation = np.sum(
                        sbar_variation * right_cauchy_green + sbar * c_variation,
                        axis=(-2, -1),
                    )
                    inverse_variation = -inverse_transpose @ direction.T @ inverse_transpose
                    tangent[..., spatial_index, reference_index] = (
                        factor_variation[..., None, None] * projected_stress
                        + isochoric_factor[..., None, None] * (
                            direction @ sbar + gradient @ sbar_variation
                            - (contraction_variation / 3.0)[..., None, None] * inverse_transpose
                            - (contraction / 3.0)[..., None, None] * inverse_variation
                        )
                    )

            if tension:
                stretched_fiber = gradient @ f0
                energy = energy + 0.5 * tension * (
                    np.sum(stretched_fiber * stretched_fiber, axis=-1) - 1.0
                )
                first_piola = first_piola + tension * stretched_fiber[..., :, None] * f0
                tangent += tension * np.einsum("ik,J,L->iJkL", identity, f0, f0)
        except FloatingPointError as error:
            raise ValueError("material response overflowed or became nonfinite") from error

    outputs = {"energy": np.asarray(energy), "P": first_piola, "tangent": tangent, "J": determinant}
    if not all(np.all(np.isfinite(value)) for value in outputs.values()):
        raise ValueError("material response became nonfinite")
    return outputs
