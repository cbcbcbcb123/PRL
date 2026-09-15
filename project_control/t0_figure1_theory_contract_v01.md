---
plan_id: PLAN-PRL-T0-FIGURE1-THEORY-V01
status: approved
planner: Codex project supervisor
approved_by: human_final_reviewer
approved_at: 2026-08-11
executor: Codex current task
inspector: pending_human_figure_gate
upstream:
  - project_control/m1_dynamic_external_load_v01.md
  - planning/publication_routes_v02/DCM_FEM_pure_theory_plan_v02.docx
preserves:
  - project_control/external_scientific_review_constraints_v01.md
  - project_control/hybrid_x1_k_r1_midpoint_collapse_diagnostic_failure_report_v10.md
---

# T0 / Figure 1 v01 理论合同

## Goal

建立固定发育时期、快速心搏尺度下的 DCM–FEM–DCM 统一功率一致框架，明确主动心肌细胞、连续 cardiac-jelly ECM、被动心内膜细胞及两类非匹配界面的控制变量、作用反作用、能量账本和退化极限。

本阶段的核心问题是：细胞主动功如何通过单侧接触界面无伪功地进入连续 ECM，并进一步传给第二层细胞。

## Inputs

- 已通过的单心肌细胞周期极限环；
- 已通过的集中参数弹簧/阻尼外载；
- 纯理论论文路线 v02 的 Figure 1 主张；
- 心脏特异接触边界：心肌基底面主要接触 cardiac jelly，侧面主要承担细胞—细胞连接；
- X1-K 仍未通过、下游长耦合未授权的冻结边界。

## Outputs

1. `docs/theory/t0_dcm_fem_dcm_energy_interface_v01.md`：控制方程、界面虚功、能量账本、量纲和退化极限；
2. `figures/theory/t0_figure1_unified_framework_v01.png`：Figure 1 审阅图；
3. `figures/theory/t0_figure1_unified_framework_v01.svg`：可编辑矢量版本；
4. `project_control/t0_figure1_execution_log_v01.md`：执行与自检记录。

## Implementation Steps

1. 用抽象 DCM 势能、主动功率和耗散表示现有单细胞内核，避免在 T0 改写已接受的单细胞本构；
2. 用有限变形、近不可压缩、带内部变量的热力学一致黏弹连续体表示 cardiac jelly；
3. 在非匹配 DCM/FEM 表面定义同一点求积的位移差、界面储能和界面耗散势；
4. 由同一界面势对两侧自由度求导，得到严格作用反作用和离散功率抵消；
5. 建立三层总能量—功率账本；
6. 验证自由细胞、完全黏结、单侧一维 ECM 弹簧/阻尼、刚性环境和去除心内膜等退化极限；
7. 生成 Figure 1 v01，仅表达理论结构，不呈现模拟数据。

## Impacted Files Or Modules

本阶段只新增理论、绘图和项目控制文件，不修改现有求解器、冻结结果、测试、SimuCell3D fork 或 X1-K 证据。

## Test Plan

- 检查每个功率项单位均为能量/时间；
- 检查界面两侧离散力的符号和作用反作用；
- 检查界面功率之和等于界面储能率与非负耗散的负值；
- 检查均匀一维 ECM 极限恢复 `K_ext=EA/H` 和 `C_ext=eta*A/H`；
- 检查接触方向张量满足 `tr(M_A)=phi_A`；
- 渲染并目视检查 PNG/SVG 的图文、裁切和可读性。

本轮自检不是独立科学检验；理论包必须停在人类 Figure Decision Gate。

## Risks

- 将“近不可压缩”误写成局部厚度不变；
- 在同一基线中同时堆叠黏弹、孔弹和流固耦合，造成参数不可识别；
- 用惩罚刚度产生的数值依赖冒充界面物理；
- 将四面包埋通用工况误当作早期心肌的主要生理接触；
- 用理论图或局部恒等式替代数值收敛和生物学验证。

## Acceptance Criteria

Figure 1 v01 进入下一门前必须同时满足：

1. 所有变量、法向方向、牵引正负号和外功符号明确；
2. 非匹配界面通过同一求积与转置映射闭合功率；
3. 总能量账本没有遗漏界面储能、界面耗散、主动功或腔压功；
4. 自由细胞和一维弹簧/阻尼退化极限与既有 M1 结果的模型语义一致；
5. 单侧接触和四面包埋只改变接触集合/方向分布，不改变基础耦合定律；
6. 图注明确“理论结构、非模拟结果、未完成生理验证”；
7. 获得人类终审的保留、修改、替换或停止决定。

## Out Of Scope

- 心肌细胞层、完整三层求解、器官几何和参数相图；
- ECM 孔弹性、双相流、真实血流 FSI；
- 生长、分裂、ECM 分泌、降解、EndMT 和慢发育反馈；
- EFE 形成机制和疾病因果；
- 修复或改判 X1-K。

## Required Memory Updates

只有 Figure 1 经人类终审接受并完成后续独立科学检查，才允许把其方程和 claim 作为稳定项目记忆。本合同自身不修改既有稳定结论。

