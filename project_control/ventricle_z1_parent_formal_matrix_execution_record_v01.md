---
document_id: PRL-VENTRICLE-Z1-PARENT-FORMAL-MATRIX-EXECUTION-RECORD-V01
status: failed
recorded_at: 2026-09-12
contract: project_control/ventricle_z1_parent_formal_matrix_contract_v01.md
authorization: project_control/ventricle_z1_parent_formal_matrix_authorization_v01.md
latest_result: results/ventricle_z1/parent_formal_v04_20260912
---

# 父级 Z1 正式矩阵执行记录 v01

## 结论

父级 Z1 正式矩阵在动态加载前的零载平衡门以 **FAIL_NUMERICAL** 停止；父级 Z1 保持 **UNRESOLVED**。
长轴心肌的代表性零载平衡可建立，但 `4:4:1` 扁平心内膜在冻结的完整组合被动项与厚度方向有限端区下离开可接受网格集合。

最终 v04 诊断从参考态逐级恢复非参考被动项。在完整项比例 `1.0` 时：

- 自由节点最大残力 `2.148510e-8 N`，高于 `1e-14 N` 门；
- 最小三角形角 `1.792924657e-5 deg`，低于 `15 deg` 门；
- 翻面 `8`，要求为 `0`；
- 最近数值信赖域边界仍相距 `0.422547 L0`，所以失败不是坐标边界被激活造成的假象。

独立验证从五个原始 NPZ 状态重算了最小角与翻面数，状态为 `PASS_VERIFICATION_OF_FAILURE`。失败图和门禁图均通过人工目视检查。

## 尝试谱系

| 版本 | 状态 | 说明 |
|---|---|---|
| `parent_formal_v01_20260912` | `FAILED_RUNNER_INPUT` | 预登记遗漏继承的 `target_volume_m3`，建模前停止；无数值结果 |
| `parent_formal_v02_20260912` | `FAILED_EQUILIBRIUM_SOLVER_BRANCH` | 无界搜索进入退化分支；优化器终止标志被残力门拒绝 |
| `parent_formal_v03_20260912` | `FAILED_EQUILIBRIUM_CONVERGENCE` | 有界搜索未在 140 次迭代内达到残力门 |
| `parent_formal_v04_20260912` | `FAIL_NUMERICAL` | 数值延拓复现真实几何失败；保留原始网格、图与独立复核 |

所有失败包均保留；没有删除、覆盖或把失败改名为通过。

## 实际边界条件

厚度方向两端各取总跨距 15% 的有限材料端区并固定在零载位置，其他节点自由。该设置避免钉单点奇异；
零载平衡使用完整组合势能。正式动态原拟采用双端对称 5% 加载—持载—卸载—恢复和双面积加权过阻尼，
但因前置几何门失败而 **NOT_RUN**，所以本轮没有物理时间点、能量账本或网格/时间/体积罚细化结果。

## 解释边界与下一步

这不是“扁平细胞在真实组织中必然塌陷”的生物结论，而是当前合成 `4:4:1` 初始网格、各向同性参考边度量、
恒表面张力、弯曲项和冻结参数组合不能给出可接受的受支撑零载平衡。Z1-B 的孤立参考形状分量通过、Z1-C 的规定运动接触通过、
父本构梯度/能量修复通过仍在各自原范围内有效，但不能替代完整组合平衡。

下一最小切片应先建立**预应力兼容参考态或各向异性参考面材料**，并在不改变冻结科学门的前提下让扁平细胞通过零载平衡、
最小角和无翻面门；随后新版本重跑正式矩阵。多细胞主动周期拉伸、Z2、ECM、CFD 与 FSI 未启动。

## 证据入口

- `results/ventricle_z1/parent_formal_v04_20260912/index.html`
- `results/ventricle_z1/parent_formal_v04_20260912/report.md`
- `results/ventricle_z1/parent_formal_v04_20260912/summary.json`
- `results/ventricle_z1/parent_formal_v04_20260912/diagnostics/continuation_diagnostic.csv`
- `results/ventricle_z1/parent_formal_v04_20260912/verification/independent_verification.json`
