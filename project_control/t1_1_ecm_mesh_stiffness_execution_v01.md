---
execution_id: T1.1-ECM-MESH-STIFFNESS-EXECUTION-V01
plan_id: T1.1-ECM-MESH-STIFFNESS-CONTRACT-V01
executor: codex_primary_single_agent
started_at: 2026-08-11
completed_at: 2026-08-12
status: completed
scientific_gate: failed
independent_inspection: pending_human_review
deviation_records: []
---

# T1.1 ECM 网格敏感性与等效刚度执行记录 v01

## 1. 批准依据与执行边界

依据 `project_control/t1_1_ecm_mesh_stiffness_contract_v01.md`，完成了固定拓扑、准静态、纯弹性 DCM–FEM 的 ECM 面内加密、厚度加密、隔离刚度校准和 calibrated symmetric 工况。没有执行 remeshing、动态周期、黏弹内变量演化、内膜层或参数拟合。

## 2. 实际完成的计算

| 工况 | patch divisions | 四面体数 | 状态 | 峰值缩短 | 峰值曲率代理 | 峰值 ECM 能量 |
|---|---:|---:|---|---:|---:|---:|
| L0 basal | `(3,1,2)` | 36 | 复用上游通过状态 | 15.61959% | -4.42981e-3 | 1.22360e-5 |
| L1 basal | `(5,1,4)` | 120 | completed | 15.61906% | -4.40383e-3 | 1.11087e-5 |
| L2 basal | `(7,1,6)` | 252 | completed | 15.62006% | -4.48287e-3 | 1.12312e-5 |
| L1T basal | `(5,2,4)` | 240 | completed | 15.62118% | -4.25351e-3 | 2.27977e-5 |
| L1 calibrated symmetric | `(5,1,4)`×2 | 240 | completed | 15.61818% | +2.96931e-7 | 1.12636e-5 |

所有新耦合状态均通过体积、完整 KKT、gap、正 Jacobian、表面质量、pair force 和 pair moment 门。峰值 KKT 位于 `2.41e-6–3.67e-6`；最小 ECM Jacobian 为 `0.99286`。

## 3. 预注册门结果

### 3.1 面内加密 L1→L2：通过

- 缩短差：`0.000998` 个百分点，门槛 `<=0.10`；
- 曲率相对差：`1.7787%`，门槛 `<=5%`；
- ECM 能量相对差：`1.0963%`，门槛 `<=10%`。

### 3.2 厚度加密 L1→L1T：形态通过、能量失败

- 缩短差：`0.002123` 个百分点，通过；
- 曲率相对差：`3.4727%`，通过；
- ECM 能量相对差：`68.9489%`，超过 `10%` 门槛，失败。

因此当前可以认为细胞缩短和有符号曲率对已测试离散较稳定，但不能认为 ECM 内部储能已在厚度方向收敛。

### 3.3 等效刚度后的 symmetric：拓扑门通过

- 每侧 ECM 使用 `mu_eq=0.5`、`kappa_eq=10.0`；
- 与 L1 basal 缩短差：`0.000881` 个百分点，门槛 `<=0.20`；
- symmetric / basal 曲率比：`6.7426e-5`，门槛 `<=0.10`。

说明双侧 ECM 的并联刚度减半校准没有破坏接触极性结论，对称接触仍消除一阶弯曲。

## 4. 隔离刚度校准的浮点阈值说明

未校准双侧 ECM 的反力和能量理论上为单侧两倍；半模量后应与单侧一致。`1e-3` 与 `5e-3` 位移下均在 `1e-14` 量级相对误差内匹配。最小位移 `1e-4` 下：

- 反力相对误差：`4.44e-14`；
- 能量绝对差：约 `1.24e-18`；
- 因单侧能量仅 `9.33e-9`，相对误差为 `1.332e-10`，略高于预注册 `1e-10`。

原始机器级门结果保留为失败，没有事后修改阈值。该项是极小能量下的相对误差底噪，不是本阶段的实质性科学失败；实质失败为 L1→L1T 的 `68.95%` 耦合 ECM 储能差。

## 5. 厚度失败诊断

附加只读诊断比较了 L1 与 L1T：

- 参考 ECM 体积绝对差：`2.78e-17`；
- 相同仿射剪切场的能量相对差：`1.99e-12`；
- 相同仿射剪切场的反力相对差：`3.87e-14`；
- 耦合状态中 L1T 界面最大位移为 `0.00560`，L1 为 `0.00296`。

因此厚度能量差不是重复体积、网格生成错误或有限元积分缩放错误。L1T 的内部层解析出了 L1 单层线性厚度场无法表达的局部非仿射顺应变形。需要继续厚度加密才能判断该能量向何处收敛。

## 6. 代码、结果和检查

- 核心实现：`src/hybrid/fixed_topology_active_cell_ecm.py`；
- 测试：`tests/hybrid/test_fixed_topology_active_cell_ecm.py`；
- 主运行：`scripts/run_t1_1_ecm_mesh_stiffness_v01.py`；
- 厚度诊断：`scripts/audit_t1_1_ecm_thickness_v01.py`；
- 阶段图：`scripts/build_t1_1_ecm_mesh_stiffness_figure_v01.py`；
- 结果：`results/hybrid/t1_1_ecm_mesh_stiffness_v01/`；
- 当前相关回归：`18 passed`。

## 7. 结论边界与下一决策门

T1.1 按原合同执行完毕，但总体 scientific gate 为失败。保留的正结论是：缩短、弯曲方向、面内加密与等效双侧刚度响应稳定。不能将 ECM 能量用于论文定量结论，也不能宣布三维 ECM 空间收敛。

建议另行批准 T1.1R 厚度收敛修复，而不是修改原合同：固定 L1 面内网格 `(5,*,4)`，继续计算 `y=3`、`y=4`，以 L1T (`y=2`) 为新起点检查 ECM 能量、界面位移和曲率；若仍不收敛，再联合加密面内和厚度方向，或检查近点 tether 载荷的正则化需求。
