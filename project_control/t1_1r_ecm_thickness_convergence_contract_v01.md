---
plan_id: T1.1R-ECM-THICKNESS-CONVERGENCE-CONTRACT-V01
status: approved
planner: codex_primary_single_agent
approved_by: human_final_reviewer
approved_at: 2026-08-12
executor: codex_primary_single_agent
inspector: human_final_reviewer
related_memory_entries: []
upstream:
  - project_control/t1_1_ecm_mesh_stiffness_contract_v01.md
  - project_control/t1_1_ecm_mesh_stiffness_execution_v01.md
formal_x1_k_gate_change: false
---

# T1.1R ECM 厚度收敛修复合同 v01

## Goal

在不修改 T1.1 失败记录和不改变模型物理参数的前提下，继续增加三维 ECM 厚度方向自由度，判断耦合 ECM 储能、界面位移与细胞弯曲是否趋于稳定。

## Inputs

- 复用 T1.1 的 `L1T=(5,2,4)` 峰值结果作为 `Y2`；
- 新增 `Y3=(5,3,4)` 与 `Y4=(5,4,4)`；
- basal 单侧接触；
- 三维 DCM 细胞网格、ECM 几何厚度、材料参数、tether 参数和远端固定边界均保持不变；
- `mu_eq=1.0`、`kappa_eq=20.0`、`mu_ve=0.0`；
- 激活路径 `0, 0.10, 0.20`；
- 固定拓扑、准静态联合求解。

## Outputs

- `Y3`、`Y4` 全部状态及审计指标；
- `Y2→Y3`、`Y3→Y4` 的缩短、曲率、ECM 储能和最大 ECM 位移变化；
- 厚度方向阶段审阅图；
- 通过、失败或趋势不确定的有界结论。

## Implementation Steps

1. 复用现有 DCM–FEM 求解器，不改变核心能量和约束；
2. 生成 `(5,3,4)` 与 `(5,4,4)` 四面体 ECM；
3. 按 `0→0.10→0.20` continuation 求解；
4. 对每个状态执行体积、KKT、gap、Jacobian、表面质量和界面平衡审计；
5. 将 Y2、Y3、Y4 统一比较并生成阶段图。

## Impacted Files Or Modules

- 新增运行、汇总与绘图脚本；
- 新增结果目录与执行记录；
- 不修改 T1.1 原始结果；
- 除非发现独立可复现的求解器错误，否则不修改核心 DCM–FEM 实现。

## Test Plan

- 运行现有相关回归测试；
- 检查每个新状态均通过原 T1 数值门；
- 检查结果文件、图和汇总可重新生成；
- `git diff --check` 检查新增源码和记录。

## Acceptance Criteria

主要收敛判断采用最新两级 `Y3→Y4`：

- 峰值缩短差 `<=0.10` 个百分点；
- 峰值曲率绝对值相对差 `<=5%`；
- 峰值 ECM 储能相对差 `<=10%`；
- 最大 ECM 位移相对差 `<=10%`；
- ECM 储能和最大位移的 `Y3→Y4` 差异不得大于各自的 `Y2→Y3` 差异；
- Y3、Y4 全部状态通过原 T1 数值与物理门。

若全部通过，只允许称为“在测试的 Y2–Y4 厚度序列上达到工程网格不敏感”，不称为严格渐近收敛或 GCI。

## Risks

- 点式/稀疏 tether 可能激发局部高梯度，使线性四面体储能收敛慢；
- Y4 仍可能不足以解析厚度边界层；
- 若能量不收敛，原因可能是需要联合面内—厚度加密，而非单独厚度加密；
- 数值几何稳定不等于材料参数具有生物学标定意义。

## Out Of Scope

- 不改变 tether 正则化、接触面积离散或材料模型；
- 不增加黏弹性、动态时间积分、内膜层或心腔压力；
- 不执行 remeshing/X1-K；
- 不拟合实验参数；
- 不把本轮自动升级为完整 Figure 3 论文证据。

## Required Memory Updates

本轮结果先作为待人类终审的执行证据记录；只有人类接受后，才更新为稳定项目结论。
