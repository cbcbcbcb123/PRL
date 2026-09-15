---
execution_id: PRL-FIG2-SPATIAL-TOLERANCE-ST1-PHASE0-KKT-DIAGNOSTIC-EXEC-V01
plan_id: PRL-FIG2-SPATIAL-TOLERANCE-ST1-PHASE0-KKT-DIAGNOSTIC-V01
executor: codex_current_task
started_at: 2026-09-01
completed_at: 2026-09-01
status: completed_with_deviation
deviation_records:
  - two_initial_test_invocations_failed_before_collection_and_were_corrected
next_gate: human_warm_start_v02_repair_decision
---

# PRL Figure 2 ST1：相位 0 KKT 诊断执行与人类门 v01

## Approved plan reference

执行依据：
`project_control/prl_figure2_spatial_tolerance_st1_phase0_kkt_diagnostic_contract_v01.md`。
人类于 2026-09-01 回复“同意，继续”，批准此前明确提出的相位 0 诊断范围。

## 结论

一次配置完全相同的额外 80-iteration continuation 将 E1 相位 0 归一化 KKT
残差从 `1.9647424237527947e-05` 降至 `9.986340629229005e-06`，下降因子
`0.5082773450859985`，并通过冻结的 C0 KKT 门 `1e-05` 及全部体积/几何硬门。

这支持“原 80 次 capture 预算偏紧”，不支持“E0→E1 映射状态无法达到机械平衡”
这一强结论。但通过裕量很小：仅低于门限 `1.3659370770995684e-08`，约为门限的
`0.1366%`；同时 L-BFGS 仍因达到 80 次上限退出，`optimizer_success=false`。
因此当前结果是入口诊断，不是稳健暖启动，也不是 A1 证据。

## Commands or tools used

- 本地 CPU Python：相关静态/回归测试；
- Docker CPU 镜像 `dolfinx/dolfinx:v0.11.0`：一次相位 0 continuation；
- 容器 `prl-st1-e1-phase0-kkt-diag-v01-20260901` 已正常退出；
- 未启用 GPU、未切换后端、未运行 T64。

## Files changed

- `project_control/prl_figure2_spatial_tolerance_st1_phase0_kkt_diagnostic_contract_v01.md`；
- `scripts/diagnose_prl_figure2_spatial_warm_start_kkt_v01.py`；
- `tests/hybrid/test_prl_figure2_spatial_st1_entry.py`；
- 本执行与人类门记录；
- `project_control/CURRENT_STATUS.md`。

## Tests or checks run

- 最终相关回归：`38 passed in 72.39s`；
- 输入 target case、C0 profile digest 和 checkpoint array digest 均匹配；
- 初始 checkpoint array digest：
  `3495939b8e9c267bb2b08ff63e84e606de71be6bdf75c48ef1b8b4f53a2d70b0`；
- 最终体积约束残差：`0.0`；
- 最小 ECM Jacobian：`0.9993643014185013`；
- 最小间隙：`0.039094842047559496`；
- 心肌/心内膜最小面面积比：`0.9999450426334442` / `0.9994548812874139`；
- A1/B1/A2/B2 输出根目录不存在，正式事务数仍为 0。

## Deviations

第一次测试引用了不存在的旧测试文件名，未收集测试；第二次因本地解释器未显式加入
项目 `src` 而在 collection 阶段停止。两次均未执行科学计算，也未产生正式结果。
纠正为显式项目导入路径后，计划内 38 项测试全部通过。

## Blockers

诊断 checkpoint 标记为 `diagnostic_only=true`，且
`may_seed_st1_endpoint_without_new_human_decision=false`。在新的人类决定前，不得用它
启动 A1，也不得静默把 capture budget 从 80 改为 160。

## Outputs produced

- `results/hybrid/prl_figure2_spatial_tolerance_st1_e1_phase0_kkt_diagnostic_v01_20260901/summary.json`；
- 同目录 `diagnostic_checkpoint.npz`，仅供审计；
- 诊断 checkpoint digest：
  `aa722952ee551baec9276de8a3df17049f945af0c4774d06850a28604d7681a5`。

## Human Gate 建议

建议接受诊断结论，并只批准暖启动入口 v02 的最小修复：从原映射初值开始，固定执行
两个连续的 80-iteration C0 capture block，逐 block 记录 KKT、优化器状态和几何门；
仍使用 `1e-05` 门，不允许自动第三 block、Newton、fallback 或算法切换。

修复入口和测试通过后，用全新的 E1 暖启动目录重算；若通过，可依既有 ST1 授权进入
A1/B1。E2 应在 E1 入口和 A1/B1 行为确认后再用同一规则构造，不提前计算。

## Evidence boundary

本诊断只说明 E1 相位 0 在累计两段相同 L-BFGS 预算后可擦线达到 C0 KKT 门；它不
证明 A1 周期稳定、C1 容差稳定、E2 空间稳定或 Figure 2 空间收敛。
