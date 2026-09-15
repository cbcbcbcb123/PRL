# EFE Node 1 N1-1 execution log v01

## Lifecycle

- lifecycle: `n1_1_human_figure_gate`
- authorization: `project_control/efe_node1_n1_1_authorization_decision_v01.md`
- current result: `computational_evidence_complete_awaiting_human_review`
- updated: `2026-08-18`
- scope: `D0/E0 development evidence only`

N1-1 的获批计算范围已执行完毕。当前必须停在阶段图人类检查点；本记录不构成
N1-2 授权。

## Implemented vertical slice

1. One active closed myocardial DCM, one shared 3D tetrahedral SLS ECM layer,
   and one passive closed endocardial DCM.
2. Two independently registered material interfaces, with the shared ECM bulk
   energy assembled exactly once.
3. Myocardial surrounding-tissue support and prescribed pressure/WSS follower
   ports acting only on the endocardial lumen surface.
4. Exact-volume coordinates for both closed DCM layers; surface area is not a
   hard conservation constraint.
5. Strict unilateral two-interface contact through augmented-Lagrangian and
   active-set projection/refinement, with gap, multiplier, complementarity and
   contact KKT audits retained separately.
6. Spectrally preconditioned equilibrium refinement with contractual KKT,
   geometry and volume gates independent of raw optimizer termination flags.
7. Staggered quasi-static/SLS cycle coupling: mechanical equilibrium at fixed
   internal state, exact SLS branch relaxation at fixed end-step deformation,
   and repeated solution until the internal-state and KKT gates both pass.

## Manufactured and regression verification

- M0/M1/M3/M4/M7/M8 remain represented by the trilayer and interface tests.
- Named M5 normal-port, M6 tangential-port, M9 SLS storage/loss and M11
  periodic-power fixtures were added in
  `src/hybrid/efe_node1_manufactured.py`.
- Latest focused run:
  `15 passed` for `test_efe_fast_trilayer.py`,
  `test_efe_fast_trilayer_solver.py` and
  `test_efe_node1_manufactured.py`.
- Ruff checks on all source, tests and scripts changed in this increment:
  passed.
- The M5/M6/M9/M11 tests are independent analytic/manufactured benchmarks;
  they do not substitute for D1/E1/D2/E2 spatial convergence or N1-2 cycle
  convergence.

## Load-path evidence

### Active-only

- Consolidated evidence:
  `results/hybrid/efe_node1_active_spectral_v01_20260818/`.
- Registered command peak reached: `a=0.20`.
- Peak axial shortening: `11.689%`.
- Peak-state KKT: `1.96e-08` in the monotonic active-path consolidation.
- Peak minimum ECM `J`: `0.987686`.
- Peak minimum interface gap: `0.017427`.

### Pressure-only

- Consolidated evidence:
  `results/hybrid/efe_node1_pressure_path_v01_20260818/`.
- Prescribed pressure command reached: `p=0.05`.
- Final KKT: `8.90e-06`; follower residual: `7.68e-12`.
- Strict minimum gap: approximately zero within floating-point tolerance.
- Active contacts: `22`, of which `16` lie on the endocardial interface.
- Minimum ECM `J`: `0.994516`; minimum endocardial face-area ratio:
  `0.833491`.

### WSS-only

- Consolidated evidence:
  `results/hybrid/efe_node1_wss_path_v01_20260818/`.
- Prescribed tangential command reached: `tau_x=0.020`.
- Final KKT: `9.14e-07`; follower residual: `3.83e-09`.
- Active contacts at peak: `6`; minimum ECM `J`: `0.995533`;
  minimum endocardial face-area ratio: `0.793916`.
- The observed shear-to-normal response and contact migration are D0/E0
  numerical observations only. They are not accepted as a robust mechanism
  until boundary and mesh checks are authorized and passed.

Pressure and WSS are prescribed follower loads, not bidirectional FSI and not
physiologically calibrated magnitudes.

## Single N1-1 development cycle

- Evidence directory:
  `results/hybrid/efe_node1_n1_1_development_cycle_v01_20260818/`.
- Configuration: D0/E0, one period, `16` steps, active-only peak `0.20`,
  SLS `mu_ve=0.5`, `eta_ve=0.5`, coupling tolerance `5e-4`.
- Status: `passed_n1_1_single_development_cycle_d0_e0`.
- Peak contraction at `t/T=0.5`: `11.6899%`.
- Peak discrete interface traction occurs at the same sampled phase. Its
  maximum is `0.0940545` on the myocardial--ECM interface, defined as material
  pair-force magnitude divided by the frozen reference quadrature area.
- Maximum KKT over all 17 stored states: `9.62e-06`.
- Maximum accepted coupling residual: `4.23e-04`.
- Minimum ECM `J`: `0.987491`; minimum gap: `0.017616`.
- Minimum myocardial/endocardial face-area ratios: `0.881703/0.995202`.
- Cycle-end residual shortening: `0.001144%`.
- Cycle-end ECM internal-variable norm: `0.163376`.
- Cumulative nonnegative dissipation proxy: `8.0773e-06`.

The internal SLS memory and positive dissipation are resolved. The contraction
and relaxation branches of the macroscopic activation--shortening curve are
nearly coincident at this D0/E0 parameter point; a visible whole-cell
hysteresis mechanism is therefore **not** claimed.

This is one route-connection cycle only. It is not a cycle-stable solution, a
16/32/64 time-step convergence result, a full three-layer power closure, a
mesh-converged result or physiological calibration.

## Human stage-figure gate

- PNG:
  `results/hybrid/efe_node1_n1_1_development_cycle_v01_20260818/n1_1_development_cycle_stage_figure_v01.png`
- SVG:
  `results/hybrid/efe_node1_n1_1_development_cycle_v01_20260818/n1_1_development_cycle_stage_figure_v01.svg`
- Figure source data:
  `results/hybrid/efe_node1_n1_1_development_cycle_v01_20260818/cycle_figure_source_data.csv`
- Full states:
  `results/hybrid/efe_node1_n1_1_development_cycle_v01_20260818/cycle_states.npz`
- Builder:
  `scripts/plot_efe_node1_n1_1_development_cycle_v01.py`.

The four top panels show reference geometry, peak contraction, peak discrete
interface traction and cycle-end residual ECM memory. Peak contraction and
peak interface traction coincide at `t/T=0.5`, so the two panels show the same
geometry with different computed fields rather than inventing a separate
phase.

## Preserved fail-closed evidence

All failed pressure/contact and early active-path directories remain present,
including pressure spectral versions v01--v16. Examples include unconstrained
penetration, negative-`J` rejection, contact KKT misses and follower-residual
misses. The passing pressure endpoint is v17. No failed directory was deleted.

## Gate disposition

- N1-1 numerical evidence: complete within the approved D0/E0 development
  scope.
- Human N1-1 stage-figure review: accepted before the N1-1A addendum.
- Human N1-1A footprint review: accepted; F150 is the global/cycle production
  candidate and F200 remains the local-field control.
- N1-2 through N1-5, Node 2, experimental fitting, bidirectional FSI, remote Git
  and publication actions: unauthorized and not started.
