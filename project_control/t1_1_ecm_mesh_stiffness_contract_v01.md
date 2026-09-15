---
record_id: T1.1-ECM-MESH-STIFFNESS-CONTRACT-V01
status: approved
authorized_at: 2026-08-11
authorized_by: human_final_reviewer
upstream:
  - project_control/t1_dcm_fem_fixed_topology_contract_v01.md
  - project_control/t1_dcm_fem_fixed_topology_screening_v01.md
evidence_target: fixed_topology_mesh_sensitivity_and_equivalent_stiffness
formal_x1_k_gate_change: false
---

# T1.1 ECM 网格敏感性与等效刚度合同 v01

## 1. 目标

判断 T1 固定拓扑 DCM–FEM 得到的轴向缩短和接触极性弯曲是否依赖粗 ECM 网格，并把 symmetric 双侧 ECM 的总被动刚度校准到 basal 单侧 ECM，避免把两个并联 ECM patch 的刚度增量误认为接触拓扑效应。

## 2. 固定输入

- 细胞：沿用 M1 三维封闭 DCM 网格、主动纤维与体积约束；
- 峰值激活：`0.20`；新计算采用纯弹性准静态 continuation `0, 0.10, 0.20`；
- basal ECM：`mu_eq=1.0`、`kappa_eq=20.0`、`mu_ve=0.0`；
- tether：`tangential_stiffness=1.0`、`adhesion_work=0.02`、`opening_cutoff=0.12`；
- 拓扑固定，不执行 split/swap/merge/remeshing；
- 所有几何、体积、gap、KKT、pair force/moment 门沿用 T1。

## 3. 网格序列

| 标识 | patch divisions | 四面体数/patch | 用途 |
|---|---:|---:|---|
| L0 | `(3,1,2)` | 36 | 已通过的粗基准 |
| L1 | `(5,1,4)` | 120 | 面内中网格 |
| L2 | `(7,1,6)` | 252 | 面内细网格 |
| L1T | `(5,2,4)` | 240 | L1 的厚度方向检查 |

L0 直接复用 T1 的峰值证据，不重复求解。L1、L2、L1T 均计算 basal 工况。该序列只支持“面内加密 + 一次厚度敏感性检查”，不冒充严格渐近收敛或 GCI。

## 4. 等效刚度校准

双侧 symmetric 含两个几何相同的 ECM patch。在线性小扰动下，两块并联 patch 的总反力为单块的两倍；为匹配单侧总 ECM 刚度，预注册校准为每侧：

\[
\mu_{\mathrm{sym,side}}=\frac12\mu_{\mathrm{basal}},\qquad
\kappa_{\mathrm{sym,side}}=\frac12\kappa_{\mathrm{basal}}.
\]

tether 参考面积权重继续按每侧 `1/2`，总 tether 权重与 basal 相同。

先用隔离 ECM 的小幅轴向剪切试验验证：

- 未校准 symmetric / basal 总反力比约为 `2`；
- 半模量 symmetric / basal 总反力与能量相对差 `<=1e-10`。

随后在 L1 上运行 calibrated symmetric 的完整细胞–ECM 峰值计算。

## 5. 预注册判据

### 5.1 面内网格敏感性：L1 对 L2

- 峰值缩短绝对差 `<=0.10` 个百分点；
- 峰值曲率绝对值相对差 `<=5%`；
- ECM 峰值能量相对差 `<=10%`。

### 5.2 厚度敏感性：L1 对 L1T

- 峰值缩短绝对差 `<=0.10` 个百分点；
- 峰值曲率绝对值相对差 `<=5%`；
- ECM 峰值能量相对差 `<=10%`。

### 5.3 等效刚度后的拓扑检查

- calibrated symmetric 与 L1 basal 峰值缩短差 `<=0.20` 个百分点；
- calibrated symmetric 曲率绝对值不超过 L1 basal 的 `10%`；
- 所有状态通过原 T1 数值与物理门。

## 6. 输出

- 运行脚本：`scripts/run_t1_1_ecm_mesh_stiffness_v01.py`；
- 隔离 ECM 校准测试与单元测试；
- 结果目录：`results/hybrid/t1_1_ecm_mesh_stiffness_v01/`；
- 阶段审阅图与执行记录；
- 失败必须保留，不得通过改变阈值或只挑选通过网格隐藏。

## 7. Claim guard

即使全部通过，也只允许声称：在固定拓扑、准静态、未标定材料参数下，接触极性响应对所测试的 ECM 面内网格和一次厚度加密不敏感，且双侧并联 ECM 已完成最低阶等效刚度匹配。

不允许声称严格空间收敛、X1-K remeshing 通过、真实 cardiac-jelly 参数已标定、动态周期三层模型已完成或 EFE 机制已被证明。
