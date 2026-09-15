# Z1-TF v02 render/package failure record

- Recorded: 2026-09-12
- Scope: `results/ventricle_z1/tissue_formation_pilot_v02_20260912`
- Package status: `failed`
- Parent Z1 status: `unresolved`

## Failure

The v02 command exited zero and the enlarged canvas passed the unified-style layout gate, but post-run log review found NumPy `Mean of empty slice` and `invalid value encountered in scalar divide` warnings. The render repair loaded `cell_metrics.csv` as strings while the reused selection helper compared `row` and `column` against integer indices. Consequently the quantitative figure filtered out all central-cell observations and plotted invalid medians.

This is an evidence-content failure, not a new simulation failure. The v01 computational NPZ/CSV evidence remains unchanged, and v02 is preserved rather than overwritten. A v03 package must type-convert the CSV fields before plotting, serialize the exact plotted values, and independently compare them with `cell_metrics.csv`.
