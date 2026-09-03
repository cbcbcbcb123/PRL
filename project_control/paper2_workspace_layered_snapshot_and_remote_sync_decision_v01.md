---
decision_id: DEC-PAPER2-WORKSPACE-SNAPSHOT-REMOTE-SYNC-V01
status: approved_by_human_final_reviewer
decider: human_final_reviewer
decided_at: 2026-09-03
branch: codex/simucell3d-hybrid-feasibility
upstream: origin/codex/simucell3d-hybrid-feasibility
verified_base_commit: fc6094aca113ab1e183c51623eb4561b6745c483
executor_thread_id: 019fc73d-393d-71a3-98cb-d3c0cd0c8eda
---

# Paper 2 工作区分层快照与远端同步决定 v01

## 1. Decision

人类终审人批准形成一个可审查、可回退的 Paper 2 M0--M2A 阶段快照，并将该快照
推送到当前上游分支。此次操作只解决工作区版本化与远端同步，不改变 S3 的
`OBSERVABLE_DEPENDENT` 科学裁决，不恢复任何模型执行授权。

计划提交说明为：

`feat(paper2): snapshot M0-M2A identity model evidence`

## 2. Authorized inclusion scope

只允许精确纳入以下内容：

1. Paper 2 M1/M2 源码：`src/paper2_m1/`、`src/paper2_m2/`；
2. 对应测试：`tests/paper2_m1/`、`tests/paper2_m2/`；
3. 对应执行与预检脚本：
   - `scripts/run_paper2_m1_idealized_strip_v01.py`；
   - `scripts/preflight_paper2_m2a_fenicsx_2d_v01.py`；
   - `scripts/run_paper2_m2_identity_2d_v01.py`；
   - `scripts/run_paper2_m2a_s3_interface_traction_diagnostic_v01.py`；
4. `project_control/CURRENT_STATUS.md`；
5. 全部 `project_control/paper2_*.md`，包括本决定；
6. 当前 Paper 2 主线文件：
   - `project_control/prl_independent_theory_mainline_plan_v02.md`；
   - `project_control/prl_independent_theory_mainline_supplement_decision_v02.md`；
7. `results/paper2_m1/` 与 `results/paper2_m2/` 内的轻量证据文件，仅限
   `.json`、`.png`、`.csv`、`.svg`、`.md`、`.txt`。

## 3. Explicit exclusions

以下内容不得进入本次暂存或提交：

- `results/paper2_m1/`、`results/paper2_m2/` 内的 `.npz`、`.npy` 原始数组；
- `tmp/`、`planning/`、`02_图表/`、`artifacts/`、`figures/`；
- `results/` 内除 `paper2_m1/`、`paper2_m2/` 轻量证据以外的全部内容；
- 任何历史大结果、缓存、环境或运行时产物；
- 以下七个进入本任务前已经存在的已跟踪修改：
  1. `project_control/prl_figure2_spatial_tolerance_validation_contract_v02.md`；
  2. `scripts/diagnose_efe_node1_sparse_preconditioner_v01.py`；
  3. `scripts/run_efe_node1_n1_2_periodic_case_v01.py`；
  4. `scripts/run_efe_node1_n1_2b_r1a_fixed_point_pilot_v01.py`；
  5. `scripts/run_efe_node1_n1_2b_r3_transactional_cycle_v01.py`；
  6. `src/hybrid/efe_fast_trilayer.py`；
  7. `src/hybrid/efe_fast_trilayer_solver.py`。

不清理、不移动、不覆盖任何排除项；它们继续留在原工作区。

## 4. Pre-commit gates

提交前必须全部满足：

1. 重新获取远端引用，当前分支相对上游为 ahead 0 / behind 0；若出现分叉则停止；
2. 仅以逐路径方式暂存，不得从仓库根目录批量暂存；
3. 输出并审查暂存文件清单与统计，确认第 3 节所有排除项均未暂存；
4. 运行 `tests/paper2_m1` 与 `tests/paper2_m2`，测试必须通过；
5. 校验本次纳入的 JSON 均可解析；
6. 测试失败、证据文件损坏或暂存范围污染时，停止在提交前并报告。

## 5. Commit and push boundary

- 只创建本决定指定的一个阶段快照提交；
- 只推送 `HEAD` 到 `origin/codex/simucell3d-hybrid-feasibility`；
- 禁止强制推送，不执行合并、变基或拉取集成；
- 推送后重新核验本地与远端提交标识一致、ahead 0 / behind 0；
- 提交和推送不构成 T128/T256、M2B、三维、整心房、CFD/FSI、GPU 或其他计算授权。
