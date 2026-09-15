---
execution_id: EXEC-EFE-NODE1-N1-2B-R5-FINAL-REPERIODIZATION-V01
status: completed_periodic_candidate_pending_human_review
executed_at: 2026-08-20
executor: codex_current_task
approved_plan: project_control/efe_node1_n1_2b_r5_final_reperiodization_plan_v01.md
authorization: project_control/efe_node1_n1_2b_r4_acceptance_and_r5_authorization_decision_v01.md
inspector: human_final_reviewer
---

# EFE Node 1 N1-2b-r5 最后一次解析周期化执行报告 v01

## Executive result

R5 按批准合同完成。解析周期化暖启动通过全部父审计；随后 cycle 7–8 的
32/32 个新鲜 worker 事务均通过并以 create-only 方式提交。Cycle 7→8 的四条
波形差和周期末完整 ECM 内部变量差均不高于预登记门 `1e-3`，因此形成
**D0/E0/F150、T16 的周期稳态候选**，等待人类终审。

这不是时间步、空间网格或参数域收敛结论。

## 1. Frozen contract

- 模型：D0 心肌细胞 + E0 三维黏弹性 ECM + 内膜边界结构；
- ECM footprint scale：`1.5`（F150）；
- 周期与离散：`T=1`、16 steps/cycle、`dt=0.0625`；
- 激活峰值：`0.20`；
- 黏弹参数：`mu_ve=0.5`、`eta_ve=0.5`；
- 外层 Picard 上限：12；
- 周期门：四条整周期波形和周期末完整 `Z` 均 `<=1e-3`；
- 求解器、门限、材料、加载和网格均未改变。

## 2. R5 periodic warm start

源状态仅取正式 R4 cycle 6。冻结几何上的解析周期化结果为：

| Audit item | Value | Gate | Result |
|---|---:|---:|---|
| Frozen geometry periodicity residual | `5.4471e-16` | `<=1e-12` | pass |
| Candidate internal-state difference | `0` | `<=1e-12` | pass |
| Phase-zero normalized KKT | `3.1929e-6` | `<=1e-5` | pass |
| Volume residual | `1.1102e-16` | `<=1e-8` | pass |
| Minimum ECM Jacobian | `0.999031` | `>=0.5` | pass |
| Minimum gap | `0.0391312` | `>=-1e-12` | pass |

暖启动提交摘要 SHA-256：
`64caf6243677c62c64b3bfb8c10392058aa172ec7e9c864a338f47fc3aafbfda`。

该暖启动本身不被当作周期稳定性证据；稳定性仅由后续两个完全耦合周期判定。

## 3. Transactional cycles

| Item | Cycle 7 | Cycle 8 |
|---|---:|---:|
| Compared with | cycle 6 | cycle 7 |
| Accepted transactions | 16/16 | 16/16 |
| Maximum waveform difference | `6.8259e-3` | `5.9357e-4` |
| Cycle-end full `Z` difference | `8.4737e-4` | `5.8544e-4` |
| Dissipation | `2.48760e-6` | `2.48746e-6` |
| Maximum KKT | `8.8584e-6` | `9.4701e-6` |
| Minimum ECM Jacobian | `0.987726` | `0.987725` |
| Minimum gap | `0.0155226` | `0.0155228` |
| Maximum coupling residual | `8.3645e-5` | `8.3447e-5` |
| Peak axial shortening | `0.116882` | `0.116882` |
| Peak interface traction | `0.0977111` | `0.0977095` |
| Solve time | `1433.34 s` | `1469.22 s` |

完整执行耗时 `2918.89 s`。32 个 worker PID 全部唯一；32 个事务摘要均存在。
Cycle 8 末态 create-only 提交摘要 SHA-256：
`70bc31fc714eaae21c18faec1bfc98607c800d2c987a0e619ccdcc66d8d681d5`。

## 4. Pre-registered five-gate decision

| Cycle 7→8 metric | Value | Gate | Result |
|---|---:|---:|---|
| Axial-shortening waveform | `2.7478e-6` | `<=1e-3` | pass |
| Maximum interface-traction waveform | `2.5706e-5` | `<=1e-3` | pass |
| Total stored-energy waveform | `2.5005e-7` | `<=1e-3` | pass |
| ECM `||Z||` waveform | `5.9357e-4` | `<=1e-3` | pass |
| Cycle-end full `Z` | `5.8544e-4` | `<=1e-3` | pass |

结论：**5/5 pass**。宏观变形、界面力传递、储能和 ECM 黏弹记忆在最后两个
周期内同时满足原门限。

## 5. Solver margins and retained risks

通过不等于求解器已经宽裕：

- Cycle 8 step 11 的 KKT 为 `9.4701e-6`，距 `1e-5` 门仅约 5.3% 裕量；
- Cycle 7 step 13 使用 10 次耦合迭代并耗时 `350.80 s`；
- Cycle 7 step 14 使用 7 次迭代，KKT `8.8584e-6`；
- Cycle 8 step 4 使用 10 次迭代，包含 extended capture + DF-SANE fallback，
  耗时 `492.67 s`；其最终 `r_Z=2.504e-6`、KKT `2.626e-9`，事务有效；
- 上述相位必须在 T32 时间细化中继续单独监控，不能因 R5 通过而删除诊断。

这些是数值鲁棒性风险，不推翻已通过的 R5 事务，但限制其外推。

## 6. Verification and evidence package

- 相关混合模型、事务、周期、FEniCSx 和 manufactured tests：`49 passed`；
- R5 参数化切片测试：`20 passed`；
- Ruff：通过；
- 图版本包自动执行、自动核验和人工/代理视觉检查：通过并冻结；
- 审阅图：
  `02_图表/Figures/Fig2_n1_2_t16_cycle_stability/`
  `Fig2_n1_2_t16_cycle_stability_v01_20260820/`；
- 正式结果：
  `results/hybrid/efe_node1_n1_2b_r5_reperiodized_warm_start_v01_20260820/`
  与
  `results/hybrid/efe_node1_n1_2b_r5_transactional_cycle_v01_20260820/`。

## 7. Evidence boundary

本次只证明当前代码、当前三维 D0/E0/F150 模型在 T16 下形成满足预登记门的
周期候选。尚未证明：

1. T16 已达到时间离散收敛；
2. D0/E0 或 F150 已达到空间/几何收敛；
3. 该结果适用于其他 ECM 刚度、黏度、厚度、接触范围或激活强度；
4. 模型已解释 EFE 的生物学机制或与实验量化吻合；
5. Node 1 已整体完成。

未经人类终审，不写入正式项目记忆，也不进入 T32、参数扫描、N1-3 或 Node 2。
