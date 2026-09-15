"""Fixed tissue roles for the active Paper 2 hybrid model."""

from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class TissueRoles:
    endocardium: str = "discrete_cell_chain"
    myocardium: str = "active_plane_strain_fem"
    ecm: str = "viscoelastic_plane_strain_fem"
    fluid: str = "absent_in_v08"

    def checked(self) -> "TissueRoles":
        expected = {
            "endocardium": "discrete_cell_chain",
            "myocardium": "active_plane_strain_fem",
            "ecm": "viscoelastic_plane_strain_fem",
            "fluid": "absent_in_v08",
        }
        if asdict(self) != expected:
            raise ValueError("the active tissue roles are fixed")
        return self

    def manifest(self) -> dict[str, str]:
        return asdict(self.checked())


ACTIVE_TISSUE_ROLES = TissueRoles().checked()
