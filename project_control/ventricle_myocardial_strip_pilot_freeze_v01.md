# Z1-MYO-STRIP-L5-A pilot 诊断与正式离散冻结 v01

- 日期：2026-09-13
- 状态：`formal_run_ready`
- 适用合同：`ventricle_myocardial_strip_contract_v01.md`

## 保留的 pilot

| pilot | 结果 | 解释 |
|---|---|---|
| `CENTER_SMOKE` | `diagnostic_only` | 仅 5 步预平衡，初始夹持反力未消除。 |
| `CENTER_SETTLE200_SEG50` | `not_converged` | 加载过快，反力峰值明显晚于激活峰值。 |
| `CENTER_SETTLE200_SEG500` | `not_converged` | 放慢 10 倍后仍有明显相位滞后。 |
| `CENTER_DAMP010_SEG500` | `failed_numerical_route` | 将阻尼降至 0.1 后显式更新出现交替大残差；禁止用于正式结果。 |
| `CENTER_HOLD400` | `not_converged` | 每个相位固定松弛 400 步后自由节点残差仍达 `4.1e-3`。 |
| `CENTER_HOLD2000` | `accepted_pilot` | 峰值反力回到峰值激活相位；保存状态自由节点最大残差不超过 `7.6e-4`。 |

## 正式冻结

- 表面阻尼密度：1.0；不采用低阻尼加速。
- 请求步长：0.02；自适应位移上限为当前最短边的 8%。
- 零激活预平衡：1000 请求步。
- 每个八分之一相位段：50 步连续加载，随后在目标相位固定松弛 2000 步。
- 每个工况保存 9 个状态：`phi=0, 0.125, ..., 1.0`。
- 新增保存状态收敛门禁：所有工况所有保存状态最大自由节点力 `<= 1.0e-3`。
- 新增循环恢复诊断：末态与初态端部反力差不超过该工况峰值主动反力增量的 10%；若失败，不改写成生物迟滞，先标记为数值未充分恢复。
- 中心激活可测力传递阈值：`CENTER` 峰值主动端部反力增量 `>= 0.01`。

正式运行仍为 CPU 单线程、create-only；不得覆盖以上任何 pilot。
