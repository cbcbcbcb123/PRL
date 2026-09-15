# Z1-TF v03 evidence-content render repair addendum

- Status: adopted for execution
- Recorded: 2026-09-12
- Original physics contract: `project_control/ventricle_trilayer_shape_formation_pilot_contract_v01.md`
- Prior failure records:
  - `project_control/ventricle_trilayer_shape_formation_pilot_v01_failure_record.md`
  - `project_control/ventricle_trilayer_shape_formation_pilot_v02_failure_record.md`

## Scope

Create `results/ventricle_z1/tissue_formation_pilot_v03_20260912` from the same hash-checked v01 computational evidence. Preserve the v03 quantitative axis box at 10 × 5 inches and the enlarged safe canvas margins. Before plotting, explicitly convert cell indices and shape metrics from CSV strings to numeric values. Save `figures/z1tf_shape_mechanism_comparison_data.json` with every plotted central-cell value and median.

The independent verifier must compare that figure-data JSON against `cell_metrics.csv` and must confirm that each plotted series contains four finite central-cell values. No simulated state, parameter, frozen gate, or scientific status may change. v01 and v02 remain immutable failure evidence.
