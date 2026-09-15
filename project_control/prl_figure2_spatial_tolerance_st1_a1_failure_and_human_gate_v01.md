---
record_id: PRL-FIG2-SPATIAL-TOLERANCE-ST1-A1-FAILURE-HUMAN-GATE-V01
status: blocked_at_human_gate
recorded_at: 2026-09-01
authorized_scope: st1_a1_a2_b1_b2_only
failed_endpoint: A1_D0_E1_F150_T64_C0
failed_gate: cycle_stability
accepted_transaction_count: 128
single_step_hard_gates_passed: true
endpoint_passed: false
unstarted_endpoints:
  - B1
  - A2
  - B2
next_gate: human_a1_reperiodization_diagnostic_decision
---

# PRL Figure 2 ST1：A1 周期稳定性失败与人类门 v01

## 结论

A1=`D0/E1/F150/T64/C0` 已完成两个 create-only T64 事务周期，共 128 个已接受
事务。所有单步求解、KKT、体积、几何、接触、耦合和进程唯一性门通过，但 cycle 2
相对 cycle 1 的冻结周期稳定门失败，因此 A1 端点为 `failed_st1_case_gate`。

按合同 fail closed：不自动追加第三周期，不进入 B1、A2 或 B2，不放宽 `1e-3`
周期门。失败结果和两个周期 checkpoint 原样保留。

## 输入与运行边界

- 暖启动：
  `results/hybrid/prl_figure2_spatial_tolerance_st1_warm_e1_v04_20260901/periodic_warm_start_checkpoint.npz`；
- 工况：D0/E1/F150/T64/C0；
- 后端：`dolfinx/dolfinx:v0.11.0` CPU，FEniCSx；
- 两周期总耗时：约 `7372.23 s`；
- 容器 `prl-st1-a1-v01-20260901` 已退出；
- 未使用 GPU、fallback、Newton、新求解器或第三周期。

## 单步硬门

两个周期全部 128 步均接受：

- 最大 KKT：`1.1706795693494222e-07 <= 1e-05`；
- 最小 ECM Jacobian：`0.9872957718499488 >= 0.5`；
- 最小 gap：`0.017286454341830498 >= 0`；
- 最大 coupling residual：`1.1753073174001063e-05 <= 1e-04`；
- worker PID 全部唯一；
- cycle 2 峰值轴向缩短：`0.11690990812808477`；
- cycle 2 峰值界面牵引：`0.0936014294184112`。

因此本次失败不是单步发散、网格翻转、接触穿透或代数残差失败。

## 周期稳定性裁决

cycle 2 相对 cycle 1 的冻结差异为：

- axial shortening waveform：`1.6361831777152713e-05`，通过；
- total stored energy waveform：`2.8352039870006292e-05`，通过；
- interface traction waveform：`0.0025315164319015906`，失败；
- ECM internal `Z` norm waveform：`0.029995152686445863`，失败；
- cycle-end `Z` relative difference：`0.06865344881818877`，失败。

冻结门为每项 `<=1e-3`。主要未闭合量是黏弹内变量，而全局缩短和储能波形已经远低
于门限。cycle dissipation 从 `3.4591791319718776e-06` 变为
`3.234638952074366e-06`，仍有约 6.5% 变化，只作辅助诊断，不替代冻结五条门。

## 机制诊断与证据边界

E1 v04 暖启动的周期 `Z` 是沿 accepted R0 的 E0 几何历史映射到 E1 后构造；A1
的自洽耦合会产生略有不同的 E1 几何历史。因此初始 `Z` 虽对映射历史严格周期，却
不必是实际 E1 耦合轨道的周期固定点。

当前数据支持“黏弹记忆仍在向新的 E1 耦合固定点松弛”，但只有两个新周期，不能据此
可靠外推还需多少周期，也不能把未稳定 `Z` 忽略为不影响论文结果。

本失败不否定 E1 单步力学可解性，也不证明 A1 最终不存在周期解；它只证明“当前
暖启动＋最多两个周期”不足以通过预注册周期门。

## Human Gate 建议

建议仅批准一个 A1 再周期化诊断：

1. 只读使用已接受的 A1 cycle 2 完整 E1 几何历史；
2. 在同一 E1 网格上解析重建该耦合轨道对应的周期 SLS `Z`；
3. 检查周期残差、相位 0 机械一致性及与 cycle 2 末端 `Z` 的差异；
4. 不运行第三正式周期，不改 KKT/cycle 门，不启动 B1/A2/B2；
5. 诊断通过后，再另行决定是否构造 fresh A1 v02 两周期事务。

不建议直接批准第三周期：当前 cycle-end `Z` 差仍为 `6.87%`，盲目增加一个周期既
违反现有授权，也没有证据保证能降到 `0.1%`。

## 关键输出

- `results/hybrid/prl_figure2_spatial_tolerance_st1_v01_20260901/A1/summary.json`；
- 同目录 `transaction_engine/summary.json`；
- cycle 1 checkpoint digest：
  `fd4e54107abd7615f550096bb6c0307c56abc4a642fb4bb70b8a195068c90b98`；
- cycle 2 checkpoint digest：
  `d5ca68253ba2234d1db522b0499c09836748c4656ecf268e9f025e7e11d0cd32`。
