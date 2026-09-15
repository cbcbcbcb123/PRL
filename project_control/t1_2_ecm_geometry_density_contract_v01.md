---
plan_id: T1.2-ECM-GEOMETRY-DENSITY-CONTRACT-V01
status: approved
approved_by: human_final_reviewer
approved_at: 2026-08-12
executor: codex_primary_single_agent
inspector: human_final_reviewer
upstream:
  - project_control/t1_1r_ecm_thickness_convergence_execution_v01.md
evidence_target: separated_ecm_area_thickness_and_mesh_effects
formal_x1_k_gate_change: false
---

# T1.2 ECM 面积、厚度与网格密度解耦合同 v01

## Goal

在固定三维 DCM 细胞、固定接触区域和相同 ECM 材料下，分别改变 ECM 外延面积、物理厚度与网格密度，量化三者对细胞缩短、偏心弯曲、ECM 位移、储能和应力集中的影响。

## Cases

| 工况 | 面内线性尺度 | 物理面积比 | 厚度 | 网格 divisions | 角色 |
|---|---:|---:|---:|---:|---|
| B0 | 1.0 | 1.0 | 0.30 | `(5,4,4)` | 复用 Y4 基准 |
| A15 | 1.5 | 2.25 | 0.30 | `(7,4,6)` | 增加外延面积，近似保持单元尺度 |
| T15 | 1.0 | 1.0 | 0.45 | `(5,6,4)` | 增加物理厚度，保持层厚 0.075 |
| M15 | 1.0 | 1.0 | 0.30 | `(7,6,6)` | 几何不变，三方向加密 |

面内扩大以细胞投影中心为中心，在 `x,z` 两个方向等比例扩展。接触 material points、tether 参考权重和细胞接触面保持不变；新增 ECM 只提供更大的连续介质载荷扩散区域，不增加细胞—ECM 接触面积。

## Fixed Physics

- basal 单侧接触；
- 激活 `0,0.10,0.20`；
- `mu_eq=1.0`、`kappa_eq=20.0`、`mu_ve=0.0`；
- `tangential_stiffness=1.0`、`adhesion_work=0.02`、`opening_cutoff=0.12`；
- ECM 远离细胞的外表面固定，其余侧面自由；
- 固定拓扑、准静态联合求解。

## Primary Readouts

- 细胞：峰值轴向缩短、有符号曲率；
- ECM：最大位移、总储能、体积平均能量密度、`J` 范围；
- 应力：最大及 95% 分位 von Mises Cauchy 应力；
- 界面：总力范数、力矩范数、最小 gap；
- 数值：完整 KKT、体积误差、最小细胞面比、正 Jacobian、pair force/moment。

## Predictions

- 增大外延面积：增加横向载荷扩散空间，预计局部峰值应力下降；对细胞总缩短影响应小于局部场影响；
- 增加厚度：固定远端边界离细胞更远，整体更柔顺，预计 ECM 最大位移增加、界面约束减弱；
- 纯网格加密：不应系统性改变细胞缩短和曲率；若应力峰值继续升高但 95% 分位稳定，说明存在局部离散敏感性而非整体物理改变。

## Acceptance Criteria

### 数值门

所有新工况必须通过原 T1 的体积、完整 KKT、gap、正 Jacobian、细胞面质量与界面 pair force/moment 门。

### 网格独立性门 B0→M15

- 缩短差 `<=0.10` 个百分点；
- 曲率相对差 `<=5%`；
- ECM 总储能相对差 `<=10%`；
- 最大位移相对差 `<=10%`；
- von Mises 95% 分位相对差 `<=10%`。

面积和厚度工况属于物理敏感性，不预注册“变化必须小”的通过门；如实报告效应方向、幅度和是否伴随应力重新分布。

## Outputs

- 增加可参数化 ECM 面内范围的模型接口与回归测试；
- 三个新三维耦合工况；
- 每工况逐单元场摘要；
- 几何—离散对照阶段图；
- 执行记录与证据边界。

## Out Of Scope

- 不改变细胞接触面积或 tether 数量；
- 不加入内膜、黏弹性动态、流体压力、remeshing 或实验标定；
- 不执行面积×厚度全因子扫描；
- 不把模型单位应力解释为 Pa/kPa。
