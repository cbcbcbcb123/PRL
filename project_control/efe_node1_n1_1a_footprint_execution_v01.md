# EFE Node 1 N1-1A ECM footprint execution v01

## Lifecycle

- authorization:
  `project_control/efe_node1_n1_1a_footprint_authorization_v01.md`
- contract: `project_control/efe_node1_n1_1a_footprint_contract_v01.md`
- lifecycle: `n1_1a_accepted`
- status: `accepted_f150_with_f200_local_field_control`
- date: `2026-08-18`

N1-1A 的计算与阶段图已由人类终审接受；N1-2 未启动。

## Frozen geometry and discretization

| Case | ECM span `(x,y,z)` | Divisions | Vertices | Tetrahedra |
|---|---:|---:|---:|---:|
| `F100` | `(1.00,0.30,0.56)` | `(5,4,4)` | `150` | `480` |
| `F150` | `(1.50,0.30,0.84)` | `(8,4,6)` | `315` | `1152` |
| `F200` | `(2.00,0.30,1.12)` | `(10,4,8)` | `495` | `1920` |

The ECM footprint was expanded about the original `x-z` centre. Thickness,
both DCM geometries, material parameters, active command and material-point
counts were held fixed. The `x/z` divisions increased with footprint so the
audit did not confound boundary distance with element coarsening.

All three zero states retain zero force to floating-point tolerance and
minimum ECM `J=1`.

## Solver engineering evidence

The original unpreconditioned Newton--Krylov path was stopped after about five
minutes on the first F150 nonzero increment. A pure L-BFGS candidate produced
valid geometry but failed the KKT gate (`4.20e-4` at `a=0.02`).

The accepted scalable path uses:

1. bounded L-BFGS capture to enter the nonlinear convergence basin;
2. distance-two colored sparse tangent assembly;
3. sparse LU/Woodbury preconditioning;
4. Newton--Krylov refinement;
5. the unchanged contract-level KKT and geometry audit.

At F150 `a=0.02`, the refined KKT was `2.17e-11`. Higher loads required the
full capture before sparse refinement. F200 states used load-matched F150 field
transfer only as an initial guess; every F200 state was independently solved
and gated.

All abandoned and failed attempts remain in versioned result directories.

## Peak comparison at active command 0.20

| Case | Axial shortening | Maximum discrete interface traction | KKT | Minimum ECM J |
|---|---:|---:|---:|---:|
| `F100` | `11.6894%` | `0.09484` | `1.96e-08` | `0.987686` |
| `F150` | `11.6864%` | `0.10076` | `1.30e-08` | `0.988740` |
| `F200` | `11.6847%` | `0.10361` | `6.69e-09` | `0.989808` |

F150 to F200 differences:

- peak shortening: `0.0143%` relative, below the `2%` global gate;
- maximum interface traction: `2.746%` relative, below the `10%` interface
  gate;
- common-overlap displacement field: `6.973%` relative `L2` difference; this
  is reported as a local-field caveat, not relabelled as convergence.

## Disposition

1. Replace F100 as the future production geometry; retain it only as the
   narrow-domain control.
2. Adopt F150 as the production candidate for global response and future cycle
   calculations because the frozen global and interface gates pass.
3. Retain F200 for every final local displacement/stress/traction-hotspot claim.
   F150 is not declared locally field-converged.
4. Keep ECM thickness at `0.30`; thickness remains a separate future factor.

## Evidence

- summary:
  `results/hybrid/efe_node1_n1_1a_footprint_audit_v01_20260818/summary.json`
- source data:
  `results/hybrid/efe_node1_n1_1a_footprint_audit_v01_20260818/footprint_path_source_data.csv`
- PNG:
  `results/hybrid/efe_node1_n1_1a_footprint_audit_v01_20260818/n1_1a_ecm_footprint_stage_figure_v01.png`
- SVG:
  `results/hybrid/efe_node1_n1_1a_footprint_audit_v01_20260818/n1_1a_ecm_footprint_stage_figure_v01.svg`
- reproducible builder:
  `scripts/consolidate_plot_efe_node1_n1_1a_footprint_v01.py`

## Human decision

Human acceptance is recorded in
`project_control/efe_node1_n1_1a_footprint_acceptance_decision_v01.md`.
N1-2, time convergence, cycle stability, formal D1/E1 convergence, material
screening and publication actions remain unauthorized and were not started.
