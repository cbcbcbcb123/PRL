# EFE Node 1 N1-2 execution v01

## Lifecycle

- authorization:
  `project_control/efe_node1_n1_2_authorization_decision_v01.md`
- lifecycle: `n1_2b_r3_completed_awaiting_human_review`
- date: `2026-08-20`
- formal N1-2 evidence: `n1_2a_accepted_r2_transaction_seam_r3_two_cycles_completed_not_stable`

## Completed implementation preparation

1. 稀疏平衡诊断入口已参数化为 DCM `D0/D1`、ECM `E0/E1/E2` 和任意
   已批准横向足迹；
2. 新增逐周期封存、固定点耦合、统一 4097 相位插值和对称归一化 L2 判据；
3. 新增周期内变量解析暖启动工具，但尚未用于正式证据；
4. 相关测试共 `21 passed`，新增/修改文件 Ruff 通过。

## Reference-backend runtime evidence

- 4 步工程烟雾测试因 `0 -> 0.10` 过粗跳变失败并主动停止；
- 16 步烟雾测试证明前三个相位可满足 KKT 与黏弹固定点门；
- “捕获达到合同 KKT 即跳过稀疏精化”使固定点残差停在 `7.06e-4`，被否决；
- 免精化门收紧到 KKT `<=1e-7` 后，前三个相位再次通过；
- 第四相位 `a=0.10` 连续三次精化仍为 `1.93e-4 -> 6.78e-5 ->
  5.38e-5`，未过 `1e-5`；每次约 `68–124 s`；
- L-BFGS 逆 Hessian 的矩阵自由 Newton 对照超过 180 s 未返回，作为运行时
  劣势路线停止。

所有失败和主动中止目录均保留，未删除或覆盖。

## Disposition

参考后端足以作为小网格正确性基准，但当前不适合直接承担正式
`D1/E1/32-step` 多周期与空间收敛。人类终审已于 2026-08-19 批准
`project_control/efe_node1_n1_2_fem_backend_spike_proposal_v01.md`；当前只执行
受控 FEniCSx/PETSc 等价性与速度试验。

N1-3 及以后仍未授权。

## FEniCSx backend spike outcome

- Phase A 的 M0、均匀仿射 patch、F150 峰值 ECM 场评估全部通过；
- 完整 F150 峰值耦合在 80 次捕获 + 稀疏 Newton 路线通过物理门；
- 冷启动（含首次 UFL JIT）端到端加速 `5.64x`，摊销加速 `6.49x`；
- 结果见
  `project_control/efe_node1_n1_2_fenicsx_backend_spike_report_v01.md`；
- 人类终审已接受迁移 spike 并授权 backend productionization P1；
- P1 执行检查现已完成，报告见
  `project_control/efe_node1_n1_2_backend_productionization_p1_execution_v01.md`；
- 人类终审已接受 P1，决定见
  `project_control/efe_node1_n1_2_backend_productionization_p1_acceptance_decision_v01.md`。

## N1-2a authorization

人类终审已于 2026-08-19 接受 P1，并批准执行 D0/E0/F150、16-step 的
完全耦合黏弹性单周期 pilot。批准计划见
`project_control/efe_node1_n1_2a_fenicsx_16step_pilot_plan_v01.md`。32-step 与
D1/E1 仍未获得本阶段执行授权。

## N1-2a outcome

D0/E0/F150、16-step 的首个完全耦合黏弹性 warmup cycle 已完成，17 个接受
相位全部通过硬门。执行和偏差记录见
`project_control/efe_node1_n1_2a_fenicsx_16step_pilot_execution_v01.md`；
当前等待人类终审
`project_control/efe_node1_n1_2a_fenicsx_16step_pilot_review_request_v01.md`。

人类终审于 2026-08-20 接受 N1-2a，并批准 N1-2b 周期稳态验证。决定和
批准计划分别见：

- `project_control/efe_node1_n1_2a_acceptance_and_n1_2b_authorization_decision_v01.md`；
- `project_control/efe_node1_n1_2b_cycle_stability_plan_v01.md`。

N1-2b 已完成一次受控执行：解析周期 `Z` 暖启动通过；两个完整 T16 周期
通过全部状态硬门，但相邻周期的牵引、`Z` 波形及周期末 `Z` 未通过周期门；
周期 3 在第 4 步达到 12 次外层耦合后，KKT 通过而 `r_Z` 未通过，按合同
停止。执行与终审请求见：

- `project_control/efe_node1_n1_2b_cycle_stability_execution_v01.md`；
- `project_control/efe_node1_n1_2b_cycle_stability_review_request_v01.md`。

人类终审于 2026-08-20 接受 N1-2b 受控负结果，并批准 N1-2b-r1a 失败步
固定点修复 pilot。决定与计划见：

- `project_control/efe_node1_n1_2b_acceptance_and_r1a_authorization_decision_v01.md`；
- `project_control/efe_node1_n1_2b_r1a_fixed_point_repair_plan_v01.md`。

正式周期稳态证据仍为 `not_accepted`。r1a 只允许复演周期 3 step 4，不授权
完整周期重算、T32、D1/E1 或后续节点。

## N1-2b-r1a outcome

r1a 已完成。受保护 Aitken 在 4 次外层迭代后通过原始固定点门；为排除冷
启动混杂而执行的同环境新 Picard 对照在 3 次后通过，并与 Aitken 收敛到
同一固定点。因此 Aitken 没有加速优势，不建议生产化；历史 12 次 Picard
失败应重新归类为尚未隔离的冷/热执行路径敏感性。

执行报告和终审请求见：

- `project_control/efe_node1_n1_2b_r1a_fixed_point_repair_execution_v01.md`；
- `project_control/efe_node1_n1_2b_r1a_fixed_point_repair_review_request_v01.md`。

正式周期稳态证据仍为 `not_accepted`。当前等待人类终审是否接受 r1a 诊断
结论并授权 r1b 冷/热后端路径敏感性审计；完整周期仍未授权。

人类终审于 2026-08-20 接受 r1a 诊断结论、不采用 Aitken，并批准 r1b
冷/热后端路径敏感性审计。决定与批准计划见：

- `project_control/efe_node1_n1_2b_r1a_acceptance_and_r1b_authorization_decision_v01.md`；
- `project_control/efe_node1_n1_2b_r1b_path_sensitivity_audit_plan_v01.md`。

r1b 只允许复演同一个失败步及读取此前冻结状态，不授权完整周期重算。

## N1-2b-r1b outcome

r1b 已完成。3 个冷后端和 3 个顺序重放 35 个接受态的后端对同一 ECM
状态给出完全相同的能量、力、`J` 和切线；3 次冷 Picard 与 3 次预热
Picard 的逐轮状态和终态逐元素相同，均在 3 次外层迭代通过。

历史长进程失败未复现。首个封存差异在第 1 轮捕获后仅 `1.20e-7`，当前
稀疏求解器的三次独立复演会确定性放大约 `87x`；原历史轨迹表观放大约
`149x`。因此后端缓存和运行间随机漂移不是当前证据支持的原因，剩余问题是
未封存源码/运行时或内部求解路径的微差及非线性放大。

执行报告和终审请求见：

- `project_control/efe_node1_n1_2b_r1b_path_sensitivity_audit_execution_v01.md`；
- `project_control/efe_node1_n1_2b_r1b_path_sensitivity_audit_review_request_v01.md`。

正式周期稳态证据仍为 `not_accepted`。当前等待人类终审是否接受 r1b 并
授权 r2 事务性 time-step worker 单步集成 pilot；完整周期仍未授权。

人类终审于 2026-08-20 接受 r1b 并批准 r2 事务性 time-step worker 单步
集成 pilot。决定与计划见：

- `project_control/efe_node1_n1_2b_r1b_acceptance_and_r2_authorization_decision_v01.md`；
- `project_control/efe_node1_n1_2b_r2_transactional_step_worker_plan_v01.md`。

r2 只允许 3 次单步成功事务和 1 次失败回滚负控，不授权完整周期。

## N1-2b-r2 outcome

r2 已完成。3 个不同 PID 的全新 worker 均从周期 3 已接受 step 3 启动，
在第 3 次未松弛 Picard 外层迭代通过；三个候选、r1b 参考终态和三个
create-only 提交检查点逐元素完全相同。父进程独立复核 KKT、原始 `r_Z`、
体积、`J`、gap、面面积和 `Z` 结构门后才提交，二次提交同一路径均被拒绝。

一次受控失败 worker 非零退出并保留 staging 候选，但没有产生接受检查点，
输入摘要前后不变。执行报告和终审请求见：

- `project_control/efe_node1_n1_2b_r2_transactional_step_worker_execution_v01.md`；
- `project_control/efe_node1_n1_2b_r2_transactional_step_worker_review_request_v01.md`。

相关回归 `62 passed`，Ruff 通过。正式周期稳态证据仍为 `not_accepted`。
当前等待人类终审是否接受 r2，并授权 r3 从已接受 cycle 2 末态以事务 worker
重算 cycle 3–4；在获得授权前不迁移周期 driver、不运行完整周期。

人类终审于 2026-08-20 接受 r2 并批准 r3。决定和批准计划见：

- `project_control/efe_node1_n1_2b_r2_acceptance_and_r3_authorization_decision_v01.md`；
- `project_control/efe_node1_n1_2b_r3_transactional_cycle_plan_v01.md`。

r3 只允许从原 cycle 2 接受末态以事务 worker 重算 cycle 3–4；不授权自动
重试、门限修改、T32、D1/E1 或后续节点。

## N1-2b-r3 outcome

r3 已完成。正式 v02 运行使用 32 个不同 PID 的新鲜 worker 完成 cycle 3–4；
32 个父 oracle、SLS/耗散一致性门和 create-only 提交全部通过。cycle 3→4
的轴向缩短和储能波形差已分别降到 `7.39e-6` 和 `1.12e-5`，但牵引差
`1.106e-3`、`Z` 范数波形差 `2.644e-2` 和周期末完整 `Z` 差 `2.281e-2`
未过 `1e-3` 门。因此正式周期稳态证据仍为 `not_accepted`。

首次 v01 运行发生 JSON 布尔序列化偏差；该目录未拼接或复用，修复后从原
cycle 2 末态完整重启 v02。执行报告、偏差记录和终审请求见：

- `project_control/efe_node1_n1_2b_r3_transactional_cycle_execution_v01.md`；
- `project_control/efe_node1_n1_2b_r3_deviation_dev001_v01.md`；
- `project_control/efe_node1_n1_2b_r3_transactional_cycle_review_request_v01.md`。

相关回归 `69 passed`，Ruff 通过。当前等待人类终审是否接受 r3 受控未稳态
结果，并授权 r4 使用 cycle 4 实际 ECM 几何历史解析 re-periodization 后
执行两个事务验证周期。
