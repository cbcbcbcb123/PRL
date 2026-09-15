---
report_id: REPORT-PRL-HYBRID-X1-K-V08-ADJUDICATION
status: passed_revised_fixed_topology_d1_s1_acceptance
contract: CONTRACT-PRL-HYBRID-X1-K-V08-ADJUDICATION
contract_commit: 929973c99d4971c3a151f3e0db8ef7931580293f
result_package_commit: 66ff245d2da06d083ef205e2a4fc471903205dbb
fork_commit: e2ed64a26bb5d7c2d878772564fb5ffcca343c3a
x1_k_passed: false
r1_c1_f1: not_executed
downstream_authorized: false
---

# X1-K v08 D1/S1 固定拓扑修订验收综合报告

## 结论

v08 只读裁决通过，唯一状态为 `passed_revised_fixed_topology_d1_s1_acceptance`。它建立了新的 D1/S1 acceptance role，没有回写旧结果：

- Route H Gate A v01 仍为 `failed_invalid_numerics`；
- v02 D1 仍为 `failed_instantaneous_smooth_surface_refinement`；
- v04 Family B 仍为 `failed_family_B_parameterized_diagnosis`；
- v06 mean-radius spatial gate 仍为 `failed_family_c_smooth_short_trajectory_analytic_radius_nonmonotonic`；
- X1-K 仍未通过，R1/C1/F1 未执行，下游未授权。

合同先行提交并推送为 `929973c99d4971c3a151f3e0db8ef7931580293f`。裁决没有修改 C++、fork、force、damping、registered owner、legacy cache、已有 evaluator/阈值或历史失败测试。

## 1. 原始证据完整性

adjudicator 直接读取 23 个 required CSV：v05 8 个、v06 10 个、v07 5 个；没有读取或信任任何版本的 `summary.json`。每个文件均与合同冻结的 source commit、SHA-256、数据行数和精确 schema 相符。

闭合检查包括：

- v05 四层/region/valence/one-ring/symmetry keys；
- v06 五条 run 共 `1205` 组 global/local/energy keys；
- v07 八条 run 共 `1508` 组 global/local/energy keys；
- 每条 run 的连续 step、`time=step*dt`、固定 `h` 和共同 `T=0.02`；
- 所有 CSV 的 NaN/Inf 禁止；
- v06 `1205` 行与 v07 `1508` 行 ledger 逐行重算 `delta_psi`、`delta_psi+D_zeta`、positive 与 cumulative positive residual。

任何字节篡改都会在科学判定前因 SHA-256 mismatch fail closed。TDD 已用第一份 v05 CSV 增加尾随换行验证该行为。

## 2. Revised D1：Family C global L2

四层实际 `h_rms` 为：

```text
0.5846465834, 0.3007587447, 0.1514741410, 0.0758752187.
```

normal area-weighted relative L2 errors 为：

```text
0.05854440, 0.03441056, 0.01785785, 0.00900842,
p = 0.79949, 0.95630, 0.98981.
```

tangential errors 为：

```text
0.02407901, 0.01288343, 0.00519212, 0.00193460,
p = 0.94087, 1.32499, 1.42804.
```

两组误差均四层非增、实际 `h` 阶均 `>=0.5`、finest `<0.02`。`q`、face/mean area、edge ratio、directional residual、excluded legacy-cache ratio、net force、symmetry class size/count、valence/error-energy 分区与 one-ring 闭合全部通过原阈值。

必须保留的 limitation：valence-5 pointwise maximum 为

```text
0.109567, 0.138023, 0.146827, 0.149074.
```

它没有随加密改善。D1 只通过 area-weighted global L2；`pointwise_convergence_claim_allowed=false`、`uniform_convergence_claim_allowed=false`，控制面积缩小不得写成点态速度变准。

## 3. Revised S1：mean radius

四层结构 primitive fields 重算的最大值为：

```text
max r_H = 4.2016853e-15 <= 1e-12,
max r_v = 1.7347235e-15 <= 1e-12.
```

dual-area closure、net force、初始半径一致性、position/state hashes、零位移和 force-clear 同时通过。

两层四档时间诊断为：

| source level | `D0,D1,D2` | `p_t,0,p_t,1` | Richardson error |
|---:|---|---|---:|
| 1 | 3.2166e-11, 1.6082e-11, 8.0419e-12 | 1.00010, 0.99983 | 7.7320e-12 |
| 4 | 3.2010e-11, 1.6001e-11, 8.0029e-12 | 1.00032, 0.99959 | 1.3256e-13 |

跨层 Richardson 差为 `7.5995e-12<=1e-10`。该证据只支持初始等半径结构恒等式和两层一阶时间一致性，不是一般非球网格或全轨迹恒等式。

v06 mean-radius 的 excursion-normalized 空间误差和负阶原样复报：

```text
errors = 1.04393e-7, 1.69657e-7, 1.93118e-7, 1.98408e-7,
orders = -0.73059, -0.18884, -0.03909,
status = historical_failed_not_rejudged.
```

## 4. Revised S1：其余 QoI

直接从 v06 四层 raw step final values 重算：

| QoI | analytic errors | actual-`h` orders | generalized self orders |
|---|---|---|---|
| area | 4.0048e-3 → 8.1691e-5 | 1.6393,1.9959,2.0739 | 1.4914,1.9705 |
| volume | 9.0906e-4 → 5.4207e-6 | 1.9274,2.6713,2.9057 | 1.7253,2.6311 |
| registered energy | 4.0048e-3 → 8.1691e-5 | 1.6393,1.9959,2.0739 | 1.4914,1.9705 |

三项解析误差和相邻网格差均非增，所有阶 `>=0.5`，finest `<0.02`。v06 finest `dt/dt2` 的 time difference 分别为 `1.5434e-11,2.4005e-11,1.5434e-11`，均满足原 `delta<=0.25*space_proxy` 门禁。

## 5. 逐步几何、能量与局部风险

v06/v07 全部 raw runs 共同通过：orientation、triangle quality、face-area ratio、cache、centroid、force-clear 与 extraordinary-vertex/one-ring 阈值。最大观测包括：

- 最低 triangle quality：`0.937503`；
- 最大 cache residual：`1.1654e-16`；
- 最大 centroid drift：`1.6882e-15`；
- 最大局部 excursion：`0.149073<0.25`；
- 最大 local radial error/initial h：`1.85388e-4<5e-4`；
- 最大 one-ring edge scaling error：`8.11598e-6<5e-4`；
- 最低 local quality ratio：`0.9999959>0.90`。

v06/v07 的最大 cumulative positive energy residual/Psi0 分别为 `3.3249e-11` 和 `1.3279e-10`，均低于 `1e-3`。coverage 严格为 `surface_tension_only`；registered 为 `gamma*A`、`D_zeta`，legacy cache、membrane、bending、pressure、contact、active、ECM、flow 均 excluded。

## 6. 决策矩阵与 TDD

最终 decision matrix 含：4 条 `historical_evidence`、49 条 `revised_acceptance`、1 条强制 `limitation`。历史 false 不进入新 acceptance 聚合；49 条 revised acceptance 无失败。

TDD 四轮 RED/GREEN：

1. RED：模块不存在；GREEN：缺失第一份 required evidence fail closed；
2. RED：真实 evidence 路径停在 `NotImplementedError`；GREEN：完整 raw-evidence 复算；
3. RED：篡改能拒绝但异常缺结构化 reason/path；GREEN：`sha256_mismatch` 与准确路径；
4. RED：decision matrix 只有一条历史行；GREEN：四项历史状态逐项分栏。

详细 RED 输出、复算命令、机器 summary、criteria、decision matrix、provenance manifest 和 ledger replay 均位于 `results/hybrid/x1_k_revised_fixed_topology_v08/`。

## 7. 完整回归验证

- parent CTest：`52/55`；仅 v02 D1、v04 Family B、v06 mean-radius spatial gate 三项历史冻结失败，无意外失败；
- controlled SimuCell3D fork：`134/134`；
- strict `prl_core` build：通过；
- tracked Python：`66/66`；v08 focused adjudicator：`3/3`；
- Ruff：通过。

这三项 parent 失败是必须保留的科学证据，并未被禁用、改判或纳入 revised D1/S1 acceptance 聚合。

## 8. Claim guard

唯一允许表述是：“冻结 v05–v07 固定拓扑原始证据在新的数学角色下通过 revised D1/S1 acceptance。”不得称为 X1-K 总通过，不得宣称长期稳定、生理有效、完整 cell–ECM/FSI、EFE、参数标定或心脏发育机制成立。
