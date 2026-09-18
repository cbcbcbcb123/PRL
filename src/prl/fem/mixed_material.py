"""Shared three-dimensional mixed NH energy; no backend or solver ownership."""


def passive_energy(F, J, pressure, mu, kappa, inner):
    """Exact former VentricularSolid expression; ``inner`` is the backend inner product."""
    return mu/2*(J**(-2/3)*inner(F, F)-3)+pressure*(J-1)-pressure**2/(2*kappa)
