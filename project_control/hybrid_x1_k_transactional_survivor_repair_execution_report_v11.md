---
execution_id: EXEC-PRL-HYBRID-X1-K-V11-TRANSACTIONAL-SURVIVOR-REPAIR
status: completed_awaiting_human_acceptance
executed_at: 2026-08-14
contract: project_control/hybrid_x1_k_transactional_survivor_repair_contract_v11.md
approval_decision: project_control/hybrid_x1_k_v11_approval_decision.md
result: passed_x1_k_v11_transactional_survivor_r1r_c1_f1
x1_k_passed: true
downstream_authorized: false
node1_n1_1_execution: pending_human_authorization
evidence: results/hybrid/x1_k_transactional_survivor_repair_v11/
---

# X1-K v11 事务化 remesh 与 survivor-collapse 执行报告

## 结论

X1-K v11 按 `baseline → transaction → survivor collapse → R1r → C1 → F1 → evidence/verification` 顺序执行，未遇到新的首失败，唯一允许的总状态为：

`passed_x1_k_v11_transactional_survivor_r1r_c1_f1`

因此新的受控记录可写 `x1_k_passed=true`，v08r1 的 revised D1/S1、R1r、C1、F1 和 F1R 均通过。v09/v10 的历史失败仍保持有效。本报告不自动授权 EFE Node 1 N1-1。

## 实现结果

### 事务化 remesh

- `RemeshEventSink` 新增 public `prepare_remesh → commit_prepared_remesh/reject_prepared_remesh` 能力，旧 `on_remesh` 路径保留；
- myocardial material sink 在 prepare 阶段只暂存迁移结果，commit 后才更新已提交材料状态；
- token 按 cell、before/after revision 和 preparation id 校验，过期、复用和跨 cell token 均被拒绝；
- candidate 3 在拓扑 eligible、材料回绑距离 `0.047434164902525666 > 1e-12` 时于 pre-commit 阶段拒绝；
- 拒绝前后 cell、material、transfer audit、energy defect、ledger 和 external workset 六类完整状态指纹逐项相等。

### 端点保留 collapse

- 新增调用者显式指定 persistent survivor 的 endpoint collapse；旧 midpoint merge 的 API 和几何语义不变；
- split 创建 persistent id `8`，collapse 保留 id `0` 并删除 id `8`；
- 阶段拓扑为 `8/12/18 → 9/14/21 → 8/12/18`（vertices/faces/edges）；
- 初末 active energy 为 `0.010789062500000019` 与 `0.010789062500000121`，差值在 `1e-12` 容差内；
- 非法 survivor、非流形边、退化/低质量/翻转候选均在提交前原子拒绝；两个 cell 的并发 survivor cycle 无状态串扰。

## 数值资格结果

### R1r

- 8 步短轨迹，`dt=6.25e-4`；step 2 split，step 3 endpoint-survivor collapse；
- fixed 与 remesh 最大轴向 QoI 差 `3.5850452080436452e-16`；面积比差 `2.2204460492503131e-16`；体积比差 `0`；active-energy 差 `1.4309898507116403e-14`；
- 两次 remesh 的累计绝对算法能量缺陷 `5.2041704279304213e-17`，最大回绑误差 `1.1102230246251565e-16`；
- 末态最小三角形质量 `0.6704384522371295`，最大 cache residual `8.7403430992795903e-18`，force buffer 为 `0`；
- QoI、J1 和 safety gate 全部通过。

### C1

- 10 步 contact-only 轨迹，`dt=1e-4`；
- 最大 penetration `0.0050000000000000044 < 1e-2`；
- 最大作用—反作用力残差 `5.5511151231257827e-17`，力矩残差 `2.2204460492503131e-16`；
- 接触功—黏性耗散最大 coverage residual `1.6940658945086007e-21`；
- 主动力、主动储能和被动力均显式为 `0`。

### F1 与 F1R

- F1 在 step 1 识别 `failed_non_finite_state`；失败前后状态 hash 均为 `7680911624141591325`，原子状态保持；
- F1R 证明 candidate 3 `topology_eligible=1`、`transfer_acceptable=0`、`operation_committed=0`，拒绝后同一实例仍能完成合法 survivor cycle 并到达 revision 2。

## 验证与证据完整性

- v11 focused：5/5；材料/事件 ABI：11/11；v09/v10 精确失败锁定：2/2；
- parent 全套：59/62；三个失败精确为冻结的 v02、v04、v06，新增失败为 0；
- controlled fork 全套：134/134；
- parent `prl_core` 与 R1r source 通过 full `-Werror`；fork local refiner 除四类已基线化的上游既有告警外，其余类别继续按 `-Werror`，原始告警日志已保留；
- Python：120 passed、1 个 v10 clean-fork 历史来源守卫失败；该失败由获批 v11 fork 修改导致，新增 Python 数值/schema/导入失败为 0；
- Ruff：通过；
- v08r1 的 23 个 required files、CSV schema/row count、SHA-256、source/current Git blob 和旧 verification logs 全部只读复核通过，未重跑旧科学轨迹；
- 所有命令 exitcode、原始日志和 SHA-256 见 `results/hybrid/x1_k_transactional_survivor_repair_v11/verification_summary.json`。

## 证据边界与下一门

本结果只证明冻结无量纲短轨迹的数值资格：事务原子性、材料迁移、remesh survivor 周期、短时 QoI/能量、安全门、接触基线和失败持久化。它不证明长期稳定性、生理参数有效性、双向 FSI、EFE 发病机制、实验拟合或 Nature Physics 级科学主张。

当前状态是 `completed_awaiting_human_acceptance`。只有人类终审接受本 v11 结果并单独授权 N1-1 后，才可开始 EFE Node 1 的正式三层动态计算。
