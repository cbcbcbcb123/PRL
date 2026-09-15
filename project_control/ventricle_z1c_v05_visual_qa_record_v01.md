# Z1-C v05 visual-QA record

- Result package: `results/ventricle_z1/z1c_v05_20260911`
- Numerical state: `FAIL_NUMERICAL`
- Manual visual state: `SUPERSEDED_VISUAL_INTERPRETABILITY`
- Scientific evaluation remains valid; the package is retained and was not deleted or overwritten.

The first manual inspection found that the pressure panel normalized a roughly `1e-12 Pa` floating-point difference around `3.00075025 Pa` to the full color scale. Although the colorbar offset exposed the numerical range, the blue/yellow contrast could be misread as a material intercellular pressure difference.

Z1-C v06 therefore uses a shared physical pressure range beginning at zero and annotates the cell-uniform pressure. No contact, reference-state, or internal-force calculation was changed.
