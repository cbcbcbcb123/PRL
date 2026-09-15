# M1 dynamic external load v01 — stage review record

## Decision

- Stage status: `passed_external_load_stage_gate`.
- Scientific status: passed for an idealized fixed-stage single-cell axial
  spring/dashpot environment.
- Engineering status: correct and reproducible; the viscous case remains a
  performance-optimization target because SLSQP line searches require many
  objective evaluations.
- This record does not approve an explicit ECM, cardiac-jelly, endocardial,
  tissue, pressure, or developmental-growth interpretation.

## Frozen model

The environment acts through a translationally neutral generalized axial port.
The coordinate is the difference between weighted plus/minus end centroids
projected on the reference fibre axis:

\[
q=\mathbf e_0\cdot(\mathbf c_+-\mathbf c_-).
\]

The spring stores

\[
E_K=\frac12K(q-L_0)^2,
\]

and the dashpot dissipates

\[
\mathcal D_C=C\dot q^2.
\]

The generalized resisting force, positive in the extension direction, is

\[
F_{\mathrm{env}}=K(L_0-q)-C\dot q.
\]

The model-derived reference scales are:

- axial reference coordinate: `L0 = 0.9821932172260968`;
- elastic scale: `K0 = 10.003585782722789`;
- viscous scale: `C0 = 0.2795293946726318`.

Full definitions and pre-registered gates are in
`project_control/m1_dynamic_external_load_contract_v01.md`.

## Evidence generated

- Solver and energy ledger:
  `src/route_h/distributed_active_dynamics.py`.
- Regression tests:
  `tests/stage2/test_distributed_active_dynamics.py`.
- Reproducible runner and summarizer:
  `scripts/run_m1_dynamic_external_load_v01.py`.
- Machine-readable aggregate:
  `results/route_h/m1_dynamic_external_load_v01/summary.json`.
- Review figure:
  `results/route_h/m1_dynamic_external_load_v01/m1_dynamic_external_load_v01.png`.
- Each case directory contains `summary.json`, `cycle_metrics.csv`, and
  `vertices.npy`; no figure-only evidence is used.

## 20-step screening result

All cases used five or six cycles of Crank–Nicolson dynamics, the same cell,
activation peak `0.20`, and unchanged cell material parameters. Stable-cycle
metrics are:

| Environment | Ratio | Stable cycle | Peak shortening | Peak lag | Main external metric |
|---|---:|---:|---:|---:|---:|
| Unloaded | 0 | 4 | 15.3302% | 6.0750%T | — |
| Spring | 0.25 | 4 | 10.3363% | 4.0900%T | peak force 0.2537 |
| Spring | 0.50 | 4 | 7.8271% | 3.1964%T | peak force 0.3834 |
| Spring | 1.00 | 4 | 5.2832% | 2.3368%T | peak force 0.5165 |
| Spring | 2.00 | 4 | 3.2084% | 1.6657%T | peak force 0.6288 |
| Dashpot | 0.25 | 4 | 15.1520% | 7.4470%T | dissipation 0.00666 |
| Dashpot | 0.50 | 4 | 14.9447% | 8.7349%T | dissipation 0.01223 |
| Dashpot | 1.00 | 4 | 14.4851% | 11.0039%T | dissipation 0.02017 |
| Dashpot | 2.00 | 5 | 13.5674% | 14.4386%T | dissipation 0.02664 |

The four pre-registered trend gates all passed:

- spring ratio increased -> peak shortening decreased;
- spring ratio increased -> peak spring force increased;
- dashpot ratio increased -> peak shortening decreased;
- dashpot ratio increased -> external viscous dissipation increased.

The additional timing signature is mechanically distinct: spring stiffness
advanced the peak while viscosity delayed it.

## 40-step formal verification

| Metric | Spring, ratio 1 | Dashpot, ratio 1 | Gate |
|---|---:|---:|---:|
| Stable cycle | 4 | 4 | two consecutive transitions |
| Peak shortening | 5.28373% | 14.49283% | report |
| Peak lag | 2.32712%T | 10.94801%T | report |
| 20/40 peak difference | 0.00058 percentage point | 0.00772 percentage point | <= 0.1 |
| 20/40 lag difference | 0.00965 percentage point | 0.05589 percentage point | <= 0.1 |
| Energy defect / positive work | 0.00936% | 0.03694% | <= 1% |
| Maximum volume error | about 1e-13 | about 1e-13 | <= 1e-8 |
| Minimum face-area ratio | 0.88009 | 0.88055 | >= 0.05 |
| Maximum KKT residual | 2.04e-6 | 3.60e-6 | <= 1e-5 |
| Optimizer success | all | all | all required |

The formal dashpot force changed sign over a stable cycle
(`+0.10986` to `-0.10592`) while its dissipation remained nonnegative
(`0.02040` per stable cycle). The formal spring stored energy but introduced no
external viscous dissipation.

## How to read the review figure

- A–C use the same view and spatial scale. The unloaded cell reaches 15.33%
  shortening; the unit spring keeps it much longer at peak activation (5.28%
  shortening); the unit dashpot mainly delays motion and still reaches 14.49%.
- D is the amplitude response. The spring controls displacement much more
  strongly than the dashpot over the registered ratios.
- E is the timing response. Increasing spring stiffness advances the peak,
  whereas increasing viscosity delays it.
- F is the diagnostic mechanism panel. The spring produces a single-valued
  force–shortening line (recoverable stored energy). The dashpot produces a
  closed loop and changes force sign during shortening/re-extension; the loop
  represents dissipated work.

## Performance note

- 20-step ratio-1 spring: median 55 iterations/step, elapsed 698 s.
- 20-step ratio-1 dashpot: median 111 iterations/step, elapsed 2398 s.
- 40-step ratio-1 spring: median 55 iterations/step, elapsed 1758 s.
- 40-step ratio-1 dashpot: median 168 iterations/step, mean 1215 objective
  evaluations/step, elapsed 4592 s.

The viscous physics and energy ledger pass, but the current SLSQP formulation
is not yet an efficient production solver for large parameter sweeps. Future
engineering work should examine scaling/preconditioning, cached geometry
evaluations, and a solver with a suitable constrained Hessian; it must preserve
the accepted results before replacement.

## Interpretation boundary and next scientific step

This stage establishes that the single-cell model supports two identifiable,
energy-consistent environmental interactions at one fixed developmental stage:
recoverable axial elasticity and rate-dependent axial viscosity. The port is a
controlled idealization, not a claim that the real cardiac-jelly/endocardial
coupling is one-dimensional.

The next scientific gate should add a minimal explicit distributed environment
only after deciding which question is primary: substrate/ECM traction around a
single cardiomyocyte, or embryonic myocardial–cardiac-jelly–endocardial
coupling. These are different boundary-value problems and should not be mixed
in one implementation step.
