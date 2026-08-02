---
report_id: REPORT-PRL-HYBRID-X1-I-V01
status: passed_frozen
completed_at: 2026-08-02
parent_branch: codex/simucell3d-hybrid-feasibility
cell_engine_branch: codex/cell-engine-integration-seam
cell_engine_commit: 2d4b2183f5966c2afe3f4234471e727fe5f9e68d
result_id: PRL-HYBRID-X1-I-SPATIAL-DAMPING-V01
governed_by: CONSTRAINT-PRL-EXTERNAL-SCIENTIFIC-REVIEW-V01
---

# Hybrid X1-I 阻尼空间一致性报告 v01

## 结论

X1-I 已完成并冻结。新的科学路径采用按重心双面积集总的节点阻尼 `zeta_i=zeta_A A_i`，并在受控 fork 与 PRL owned driver 间以显式类型传递。X1-G/H 的统一每节点阻尼接口被保留为历史兼容模式，历史结果和 Route H Gate A v01 失败包均未覆盖。

## TDD 证据

1. **RED 1**：先加入 fork 公共行为测试，构造同一闭合立方体的 coarse/base/fine 网格与恒定面力制造解；编译只因 `SurfaceDampingLaw` / `SurfaceDampingMeasure` 尚不存在而失败。
2. **GREEN 1**：实现 `A_i=(1/3) sum_f A_f`、`zeta_i=zeta_A A_i`、逐节点 mobility 和耗散账本；8/20/56 顶点三层网格的每个节点都得到解析位移 `(0.02,-0.01,0.005)`，容差 `1e-12`。
3. **RED 2**：在 PRL owned integration test 中先调用尚不存在的 `CellSurfaceDampingLaw`，确认父层不能表达或传递面积阻尼。
4. **GREEN 2**：PRL 配置映射到 fork primitive，并通过真实 `cell::apply_internal_forces(dt)`＋主动力的 owned 单步；阻尼度量、控制面积、有效节点阻尼、位置提交与力清理均进入审计。
5. **REFACTOR/compatibility**：保留原 `double` 重载并明确映射到 `uniform_per_vertex`，使 X1-G/H 数值回归保持不变；新轨迹必须显式选择双面积模式。

## 制造解与定量结果

共同参数：单位立方体表面、`t=(0.4,-0.2,0.1)`、`F_i=A_i t`、`dt=0.1`、`zeta_A=2`。解析逐顶点位移为 `(0.02,-0.01,0.005)`。

| level | vertices / faces | 控制面积和 | 节点阻尼 min / max | 力功 | 黏性耗散 | 逐顶点位移误差 |
|---|---:|---:|---:|---:|---:|---:|
| coarse | `8 / 12` | `6` | `1.3333333333333333 / 1.9999999999999998` | `0.063` | `0.063000000000000028` | `<=1e-12` |
| base | `20 / 36` | `6.0000000000000044` | `0.33333333333333331 / 1.3333333333333337` | `0.063000000000000028` | `0.063000000000000028` | `<=1e-12` |
| fine | `56 / 108` | `5.9999999999999929` | `0.1111111111111111 / 0.88888888888888917` | `0.062999999999999973` | `0.062999999999999973` | `<=1e-12` |

未面积加权的节点 `displacement_l2_norm` 随节点数变化，故未用作空间一致性门禁。空间一致性证据是逐顶点解析误差、控制面积分片和网格间力功一致性。

真实 owned 被动＋主动算例（8 顶点、12 面、`dt=1e-3`、`zeta_A=10`）记录：

| audit | value |
|---|---:|
| control area sum | `13.211102550927979` |
| minimum / maximum nodal damping | `11.009252125773315 / 22.018504251546631` |
| total force L2 | `1.8092040532021201` |
| displacement L2 | `1.1671963537361354e-4` |
| force work / viscous dissipation | `2.0756259441726845e-4 / 2.0756259441726845e-4` |

## 验证门禁

| 检查 | 结果 |
|---|---:|
| fork standalone CTest | `133/133 passed` |
| parent C++ CTest | `30/30 passed` |
| owned parent core `-Wall -Wextra -Wpedantic -Werror` | `13/13 passed` |
| fork X1-I source/test strict syntax compile | passed with inherited `ignored-qualifiers` and `unused-parameter` warnings downgraded |
| parent Python | `63/63 passed` |
| tracked Python Ruff | passed |
| diff / JSON checks | passed |

## 冻结接口与失败边界

- 控制面积从本步当前位置直接计算，不能由陈旧 face-area 缓存提供；
- 任一 used vertex 的控制面积、有效节点阻尼或 mobility 非有限/非正时，在位置写入和力清零前拒绝；
- pending geometry 仍须通过 X1-H 的正面积、正体积与有限 centroid 检查；
- 成功后仍原子提交位置、清零 used-node force buffer，并刷新 face/node/cell 几何缓存；
- 旧统一节点阻尼不是新的连续轨迹候选，只用于历史重放和兼容测试。

## Claim guard

X1-I 证明的是面积集总阻尼原语在一个恒定面力制造解上的 coarse/base/fine 空间一致性，以及该阻尼律能够穿过 PRL owned 单步的真实被动/主动装配路径。它不证明时间积分稳定或收敛、一般非线性力学解的空间收敛、离散能量不等式、连续收缩轨迹、重网格能量一致性、完整 cell–ECM/血流耦合、EFE 双稳态/机械记忆、发育机制、参数可识别性或生理预测。`W_F=D_zeta` 仍只作代数审计；Route H Gate A v01 仍为 `failed_invalid_numerics`。

下一安全阶段为 X1-J，且不得越过到 X1-K 或长耦合。
