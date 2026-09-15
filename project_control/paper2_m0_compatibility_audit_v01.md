---
audit_id: AUDIT-PAPER2-M0-COMPATIBILITY-V01
status: completed
auditor: Codex Executor
audited_at: 2026-09-03
plan_id: PLAN-PAPER2-M0-M1-IDEALIZED-MODEL-V01
evidence_level: read_only_compatibility_audit
---

# Paper 2 M0 兼容性审计 v01

## Disposition

旧三层 DCM–FEM–DCM 基线可迁移的是端口、符号、同点求积、SLS 内变量和离散功率核对方法；旧模型身份、A1 周期结果和 Figure 2 时间离散结论均不能迁移为新“心内膜 DCM–ECM FEM–主动心肌 FEM”架构的验证证据。

M0 判定：`COMPATIBLE_FOR_NEW_IDEALIZED_IMPLEMENTATION_WITH_NON_MIGRATABLE_EVIDENCE`。

## Preserved A1 Truth

A1=`D0/E1/F150/T64/C0` 的历史事实保持不变：

- 两个 T64 事务周期共 128 个接受步骤；
- 所有单步 KKT、体积、几何、接触和耦合门通过；
- cycle 2 相对 cycle 1 的轴向缩短差 `1.6361831777152713e-05` 和总储能差 `2.8352039870006292e-05` 通过；
- 界面牵引差 `0.0025315164319015906`、ECM `Z` 波形差 `0.029995152686445863`、周期末 `Z` 差 `0.06865344881818877` 未通过 `1e-3` 周期门；
- A1 状态仍为 `failed_st1_case_gate`，不追加周期、不放宽门限、不进入旧 ST2/ST3。

只读证据哈希：

- A1 summary SHA256：`6a69a0fba15d6e3bc3ba5d49a9a56eb1c826f1b418d65bcb96b9207f5d7d93b0`；
- A1 failure record SHA256：`387b861a4add681d24781736731e2dc07ba4c6350f6779272e7023cadace3ff6`。

## Compatibility Matrix

| 对象 | M0 判定 | M1 用法 | 证据边界 |
|---|---|---|---|
| 固定发育时期、快速心搏时间尺度 | 可迁移 | 保持几何、材料和拓扑在周期内固定 | 不代表慢发育或 EFE 形成 |
| 法向与腔面牵引分解 | 可迁移并重冻结 | `t_lum=-p n_lum+tau e_x` | M1 为规定牵引，无流体求解 |
| 同点求积与转置/成对界面力 | 可迁移 | 两个同位置界面用同一集中权重 | 尚未验证非匹配网格映射 |
| 作用—反作用与界面功率抵消 | 可迁移 | 逐节点测试两侧力严格相反 | 只证明当前线性界面装配 |
| ECM SLS 内变量与非负耗散 | 可迁移 | P1 ECM 加平衡/Maxwell 支路 | 参数为无量纲验证值，非材料标定 |
| 主动 preferred-length/metric 的能量导数 | 端口语义可迁移 | 转为心肌 FEM 主动本征应变 | 旧 DCM 位移/牵引结果不可迁移 |
| 压力、剪切、主动、外支撑分账 | 必须迁移 | 独立 `P_lum/P_active/P_ext` | 不得把主动功并入外功 |
| 隐式中点与离散账本核对 | 方法可迁移 | 新模型重新做逐步恒等式测试 | 旧 Figure 2 误差数值不是新架构证据 |
| Figure 2 v02 时间离散 FINAL | 不可迁移为新架构结论 | 仅作验证设计先例 | SHA256 `3c2ff4c...61ebf2`；模型身份已变 |
| A1 128-step 运行 | 不可迁移 | 只保留失败基线与风险提示 | 不能说新架构通过 T128/周期门 |
| 旧心肌 DCM 与心内膜 DCM | 模型身份不可迁移 | M1 只保留内膜 DCM；心肌改 FEM | 正是本轮身份转换的核心 |
| 旧三维几何、体积约束、接触拓扑 | 不迁移 | M1 用低维平直条带 | 后续真实 2D/3D 必须重新验证 |

## Geometry And Sampling Audit

1. 旧几何是三维闭合 DCM 表面加四面体 ECM；M1 是沿条带方向的 P1 空间离散，每个节点保留切向和法向两个位移分量。
2. M1 的双界面节点共置，因此同点求积可直接闭合；这只验证最小功率语义，不能替代后续 DCM–FEM 非匹配投影、共同求积和转置映射测试。
3. 旧 D0/D1、E1/E2、F150/F200N 的嵌套关系、网格哈希和采样密度不用于 M1。

## Active-Form Audit

旧 Route H 集中机制使用 `L_f*=L_f0(1-alpha)`，输入功率为 `-k_f(L_f-L_f*) L_f*_dot`；后续分布式纤维把同一语义写成 preferred metric，并提供 `partial Psi/partial alpha`。因此 M1 选择连续心肌 FEM 主动本征应变：

`Psi_myo = 1/2 ∫ E_m (epsilon_x+a)^2 dx`，

`P_active = (partial Psi_myo/partial a) adot`。

它是对旧 preferred-length 端口的连续体身份转换，不是凭偏好切换为新的主动应力规律。主动应力可在后续独立模型比较中出现，但不在 M1 同时引入。

## Power-Port Audit

M1 冻结如下功率共轭：

- `P_lum = f_lum · v_endo`，压力与剪切分别保留；
- `P_ext = f_ext · v_myo`；
- `P_active = (partial Psi/partial a) adot`；
- 固定基座支撑弹簧计入储能，固定端速度为零；
- ECM SLS、心内膜阻尼和心肌阻尼分别计非负耗散；
- 数值残差 `R_num` 是闭合误差，不与物理耗散合并。

## Non-Migratable Evidence

以下材料仍有历史价值，但不得作为 M1 新架构通过证据：

1. A1 的 128 个接受步骤、峰值缩短、界面牵引和周期差；
2. Figure 2 v02 的 T16/T32/T64/T128 时间离散冻结；
3. 旧 DCM 心肌的体积、面积、拓扑和重网格门；
4. 旧四面体 ECM 的空间层级与 FEniCSx 容差结论；
5. 旧模型任何“周期稳定”“三维”“全 FEM 对照”表述。

## Authorization Check

本审计只授权进入 M1 新模块；不授权 A1 再周期化、旧 ST2/ST3、GPU、CFD、真实几何、参数扫描、共同极限正式计算、Git 提交或发布。
