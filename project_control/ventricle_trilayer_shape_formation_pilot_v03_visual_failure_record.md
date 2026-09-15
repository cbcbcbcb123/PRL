# Z1-TF v03 visual-QA failure record

- Recorded: 2026-09-12
- Scope: `results/ventricle_z1/tissue_formation_pilot_v03_20260912`
- Numerical/evidence verification: `passed`
- Visual QA: `failed`
- Parent Z1 status: `unresolved`

## Findings

Manual inspection of the rendered PNG files found three presentation defects despite the programmatic evidence checks passing:

1. `z1tf_model_structure.png`: the two-row legend overlaps the bottom explanatory sentence and clips into the canvas edge;
2. `z1tf_actual_mesh_evolution.png`: the legend and continuation-coordinate note compete for the same bottom band;
3. `z1tf_shape_mechanism_comparison.png`: the `No ECM attach` and `No cytoskeleton` tick labels overlap.

The plotted numeric values are valid and exactly match `cell_metrics.csv`; this is solely a visual-delivery failure. v03 is retained. A v04 render-only package may increase the reserved bottom bands and split long tick labels over two lines without changing the axis box, data, parameters, gates, or scientific status.
