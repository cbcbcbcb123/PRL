# Z1-TF v02 render/package repair addendum

- Status: adopted for execution
- Recorded: 2026-09-12
- Source failure: `project_control/ventricle_trilayer_shape_formation_pilot_v01_failure_record.md`
- Original physics contract: `project_control/ventricle_trilayer_shape_formation_pilot_contract_v01.md`

## Authorized repair scope

Create `results/ventricle_z1/tissue_formation_pilot_v02_20260912` without repeating the already completed 1028 s CPU simulation. Copy the v01 preregistration, parameters, condition tables, cell/iteration tables, and all 20 NPZ snapshots bit-for-bit after recording SHA-256 hashes. Re-render the requested figures with a larger canvas margin while preserving the confirmed 10 × 5 inch quantitative axis box, then generate the report, index, provenance, and independent verification.

This is a packaging/render repair only. It must not change the mesh states, physics parameters, frozen gates, or runner screening status. The v01 failure package remains intact. The v02 package must explicitly identify its v01 computational source and distinguish package verification from scientific screening.

## Stop boundary

Stop after independent verification and visual QA. Do not enter active cycling, physiological calibration, Z4, CFD, or FSI. Do not modify the MeshCell3D core, use GPU, install software, delete evidence, commit, or push.
