---
execution_id: EXEC-PRL-ROUTE-H-STAGE2-GATE-A-PHYSICAL-ACCEPTANCE-V03
contract_id: CONTRACT-PRL-ROUTE-H-STAGE2-GATE-A-PHYSICAL-ACCEPTANCE-V03
executor: Codex current task
started_at: 2026-08-05T00:55:42+08:00
formal_run_started_at: 2026-08-05T01:05:48.556572+08:00
formal_run_completed_at: 2026-08-05T01:06:13.996599+08:00
completed_at: 2026-08-05T01:21:07+08:00
status: completed_failed_gate
formal_gate_status: failed_invalid_numerics
---

# Route H Stage 2 Gate A M1 v03 执行记录

## 批准与边界

用户于 2026-08-05 明确批准 M1 v03。本次在任何正式 v03 response 运行前登记
`route_h_stage2_gate_a_v03_physical_gate_acceptance_contract.md`。冻结力学、离散、参数、
时间步、L-BFGS-B 配置、Gate 指标与 residual/gauge 阈值均未修改；`stage2_gate_a.py`
和 Gate A v01 失败包保持不变。

唯一数值方法修订是：在单次 optimizer 的每个 objective/gradient evaluation 后检查
冻结物理门槛；第一个同时满足 residual、严格增量势下降、gauge 和几何门槛的候选可
直接结束 optimizer。每步仍只有一次 optimizer 调用，无 retry 或自适应时间步。

## RED–GREEN 实施

- RED：新增公共行为测试，要求 `A1_ACTIVE, dt=0.02` 到达原失败节点 `t=1.58`；
  v03 模块不存在时按预期 collection failure；
- GREEN：新增 `src/route_h/stage2_gate_a_v03.py`，原 step79 在第 72 次目标评估被
  `objective_evaluation_physical_gate` 接受；
- step79 复算：projected residual `8.709829056e-9`，gauge
  `3.732678002e-20`，增量势由 `6.921507308e-4` 严格下降至
  `5.939037050e-4`；signed volume 为正、0 翻面、0 退化面；
- 同一路径至 `t=1.58` 的测试与旧 activation/v02 observability 回归均通过。

## 正式套件结果

正式 runner 按 A0、A1 `dt=0.02`、A1 `dt=0.01`、A1 `dt=0.005` 顺序 fail-fast：

1. `A0_ZERO_dt0.01` 完整到达 `t=5.0`，500 步保持零响应；
2. `A1_ACTIVE_dt0.02` 通过原 step79，并完整接受至 step85、`t=1.70`；
3. step86、`t=1.72` 的 returned candidate residual 为
   `1.980868094e-8 > 1e-8`，判为 `failed_invalid_numerics`；
4. 按预注册 fail-fast，未运行 `dt=0.01/0.005`，因此没有 time refinement，也不能
   报告 Gate A 通过。

最后有效状态 `t=1.70`：activation `7.9389263%`，轴向缩短 `7.4077931%`，两横向
尺度变化 `+4.0236554%`、`+2.7760470%`，体积误差 `-0.0055383%`，projected
residual `7.410527972e-9`。已接受轨迹的最大 residual 为
`9.941432733e-9`，最大绝对体积误差 `1.182758408e-4`，最大归一化质心漂移
`1.014171120e-15`。

## step86 只读诊断

使用落盘的 step85 vertices 对 step86 做一次只读重放，不改变正式结果：

- 162 次 objective/gradient evaluations，65 次 callback accepted iterates；
- 最小 trial residual 为 `1.310584667e-8`，出现在 evaluation 71；
- 最小 callback residual 与 returned residual 均为 `1.980868094e-8`；
- `0/162` trial 达到 `1e-8` 物理门槛；
- 重放 returned candidate 与正式落盘 candidate 的最大坐标差为 `0`；
- 候选 signed volume `0.299980069`，relative volume `0.999952316`，最小面面积比
  `0.765937`，最小方向余弦 `0.995099`，0 翻面、0 退化面。

因此 step86 与 v02 step79 的失败机制不同：step79 是“已有 sub-gate trial 但 callback
未接受”的语义失配；step86 是冻结 L-BFGS-B 路径的所有 trial 均未达到 physical
residual gate。M1 v03 修订有效但不足以完成 5 s 轨迹。

## 持久化产物

- `src/route_h/stage2_gate_a_v03.py`；
- `tests/stage2/test_gate_a_v03.py`；
- `scripts/run_route_h_stage2_gate_a_v03.py`；
- `scripts/run_route_h_stage2_gate_a_v03_failure_diagnostic.py`；
- `results/route_h/stage2_gate_a_v03/` 下的正式轨迹、逐步审计、rejected candidate、
  acceptance、manifest 与 step86 trace；
- 两个 Figure 工作版本包，均含物理复制数据、methods、已执行 Notebook、600 dpi
  PNG、可编辑文字 SVG；自动校验与代理目视验收通过，尚待用户终审，不标记 final。

## 验证

- `pytest tests/stage2 -q`：`7 passed`；
- Ruff：v03 solver、test、runner、诊断脚本和残差图 renderer 全部通过；
- Gate A v01 failure manifest：`29/29` 路径、bytes 与 SHA-256 匹配；
- v03 accepted vertices、rejected candidate、CSV/JSON 均有限且维度一致；
- step86 诊断重放与正式 candidate 完全一致；
- 两个 Figure Notebook 执行、版本包自动校验和视觉 QA 通过；残差图 CB 统一风格
  manifest 通过。

## 报告层更正记录

正式 solver 运行后发现 runner 中审计字段
`no_failure_candidate_mixed_into_trajectory` 实际检查的是“是否不存在 failure”，字段名与
含义不一致。未重跑 solver，只将该报告层字段更正为
`failure_candidate_separate_from_accepted_trajectory=true`，并更新 acceptance 与 formal
manifest 哈希，同时把 runner 本身补入 source inputs。该更正不改变任何 coordinates、
residual、Gate 状态或科学结论。

## 结论与边界

M1 v03 状态为 `failed_invalid_numerics`。可支持的结论仅为：原 step79 接受语义失配已
修复；轨迹推进至 `t=1.70`；step86 的新限制是优化路径没有产生 sub-gate trial，且并非
几何崩坏。不能声称完整自由收缩轨迹、时间步自洽性、生理有效性或 Gate A 通过。

下一数值方法必须另建 M1 v04 合同并在运行前预注册，优先处理目标/梯度尺度与局部
conditioning 或使用直接求解 projected force balance；不得放宽 `1e-8` 门槛，也不得把
现有 rejected candidate 写入有效轨迹。
