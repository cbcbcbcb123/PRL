---
decision_request_id: DECISION-REQUEST-EFE-NODE1-N1-2B-R2-TRANSACTIONAL-STEP-WORKER-V01
status: approved_by_human_final_reviewer
requested_at: 2026-08-20
related_plan: project_control/efe_node1_n1_2b_r2_transactional_step_worker_plan_v01.md
related_execution: project_control/efe_node1_n1_2b_r2_transactional_step_worker_execution_v01.md
formal_n1_2_cycle_stability_evidence: not_accepted
---

# EFE Node 1 N1-2b-r2 事务性 time-step worker 终审请求 v01

## Recommended decision

建议人类终审：

1. 接受 r2 为有效、可复算的单步事务 seam 验证；
2. 接受“3 个独立新进程产生同一冻结固定点，且只在父进程复核后提交”；
3. 接受“受控 worker 失败保留 staging 证据、没有提交、没有改变输入”；
4. 不把 r2 解释为完整周期稳定或 N1-2 已完成；
5. 批准下一步 `N1-2b-r3`：把已验证的事务 worker 接入周期 driver，并从
   已接受的 cycle 2 末态重新计算 cycle 3 和 cycle 4。

## Why r3 should restart at the cycle-2 endpoint

不建议从旧 cycle 3 step 3 中途拼接。虽然该检查点可用于单步诊断，但中途
拼接会让完整波形、周期耗散账本和逐步提交来源跨越两种执行架构。以旧
cycle 2 的 `accepted_step_016.npz` 为唯一输入，事务性重算 cycle 3–4，
才能形成连续、同构、可审计的两个周期，并可分别计算 cycle 2→3 与
cycle 3→4 的预登记周期差。

## Proposed r3 frozen boundary

- 模型仍为 D0/E0/F150、T16、峰值激活 `0.20`、`mu_ve=eta_ve=0.5`；
- 输入为已接受的 cycle 2 末态；只重算 cycle 3 和 cycle 4；
- 每个时间步都启动全新 worker，形成 staging candidate；
- 父进程逐步复核 KKT `<=1e-5`、原始 `r_Z<=1e-4`、体积、`J`、gap、
  面面积、耗散和 `Z` 结构门，通过后才 create-only 提交；
- 任一步失败立即停止并保留证据，不自动重试、不放宽门、不改变算法；
- cycle 2→3、cycle 3→4 均按原登记 4097 相位插值和对称归一化 L2 规则
  比较四条波形及周期末 `Z`；
- 只有 cycle 3→4 的全部五项周期门均 `<=1e-3`，才可作为 N1-2 周期稳定
  候选提交人类终审；
- r3 完成后停止，不自动进入 T32、D1/E1 或 N1-3。

## Why this is now the right mainline step

r1a/r1b 已把失败从“固定点不可解”缩小为长生命周期执行路径问题，r2 又把
单步的运行环境、复核和提交边界显式化。继续做更多单步复演的边际信息已低；
现在应把 seam 接入周期主线，用两个连续完整周期回答原始科学问题：该
黏弹性 cell–ECM 系统在 T16 下是否到达极限周期。

## Not requested

- 不请求采用 Aitken、Anderson 或改变 Picard；
- 不请求自动生产重试、门限放宽或跨主机事务；
- 不请求 T32/T64、D1/E1、F200、参数扫描、N1-3、Node 2；
- 不请求实验拟合、论文终稿、Git 或发布。

## Exact human gate

请求人类终审明确回复是否接受：

> 接受 r2 单步事务 seam；批准 r3 将事务 worker 接入周期 driver，并从已接受
> cycle 2 末态重算 D0/E0/F150、T16 的 cycle 3–4 周期稳定性验证。

在获得明确批准前，不迁移周期 driver，也不启动 cycle 3–4。

## Human decision

人类终审于 2026-08-20 明确回复“同意，继续”，接受 r2 单步事务 seam，
并批准 r3 按上述冻结边界接入周期 driver、从已接受 cycle 2 末态重算
cycle 3–4。T32、D1/E1、自动重试和后续节点仍未授权。

