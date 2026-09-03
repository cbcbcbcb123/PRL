---
plan_id: PLAN-PAPER2-M0-M1-IDEALIZED-MODEL-V01
status: approved
planner: Codex Executor
approved_by: human_final_reviewer
approved_at: 2026-09-03
executor: Codex current task
inspector: pending_human_m1_gate
authorization_source_thread: 01a05560-ad09-7393-8587-46725eade6df
execution_scope: m0_compatibility_audit_and_m1_cpu_idealized_strip_only
---

# Paper 2 M0–M1 理想体模型执行计划 v01

## Goal

在不改动旧 A1、共享求解核心和冻结结果的前提下，完成 Paper 2 正式架构的第一套可运行最小模型：

`心室腔面规定牵引 → 心室内膜 DCM → 黏弹 ECM FEM → 主动心肌 FEM → 外部支撑端口`。

M0 只做兼容性审计；M1 建立无量纲、CPU、小规模、平直条带的二维运动学/一维空间离散模型，用于冻结力、功率、作用—反作用和能量账本语义，不作生理定量或投稿级收敛主张。

## Inputs

- `02_论文2_理论型_v2.pdf`（内部版本 v3.0）的 Figure 1–2、统一变量字典和功率账本；
- `project_control/CURRENT_STATUS.md`；
- `project_control/t0_figure1_theory_contract_v01.md`；
- `docs/theory/t0_dcm_fem_dcm_energy_interface_v01.md`；
- `project_control/prl_figure2_spatial_tolerance_validation_contract_v02.md`；
- `project_control/prl_figure2_v02_time_discretization_freeze_record_v01.md`；
- 旧主动 preferred-length / distributed active-strain 实现及功率导数测试；
- A1 失败记录和 `results/hybrid/prl_figure2_spatial_tolerance_st1_v01_20260901/A1/summary.json`。

## Frozen Worktree Record

执行前只读盘点：

- `git status --porcelain=v1`：1140 项；
- 已跟踪未暂存文件：7 项；
- 已暂存文件：0 项；
- 未跟踪文件：13909 个，其中 `results/` 13327 个；
- 7 个已跟踪改动为既有 `project_control`、`scripts` 和 `src/hybrid` 工作，不属于本执行包。

本包不清理、不移动、不删除、不重置、不覆盖上述材料；实现只进入新的 `paper2_m1` 模块、测试和版本化结果目录。

## Outputs

1. `project_control/paper2_m0_compatibility_audit_v01.md`；
2. `src/paper2_m1/`：M1 独立理想化条带模型；
3. `tests/paper2_m1/`：最小物理、功率与确定性测试；
4. `scripts/run_paper2_m1_idealized_strip_v01.py`：CPU 运行入口；
5. `results/paper2_m1/idealized_strip_v01_20260903/`：create-new 运行结果；
6. `project_control/paper2_m0_m1_idealized_model_execution_log_v01.md`；
7. `project_control/CURRENT_STATUS.md` 中新增 Paper 2 M1 人类门状态，不改写旧 A1 事实。

## Model Choice And Frozen Ports

### Geometry and discretization

- 参考条带沿 `x` 方向离散，各层节点具有切向 `u_x` 与法向 `u_y` 两个自由度；
- 心内膜用逐节点/逐连接的 DCM 链表示；
- ECM 与心肌用独立 P1 条带有限元装配；
- 两个界面使用同位置节点和同一集中求积权重，M1 不处理非匹配网格映射。

### Active myocardium choice

采用连续体主动本征应变（active eigenstrain）基线，而不是主动应力。理由是既有 Route H 和分布式纤维机制均以规定 preferred length/metric 的能量导数和控制器输入功率为冻结语义；M1 将其转换为连续心肌 FEM 的

`Psi_myo = 1/2 ∫ E_m (epsilon_x + a)^2 dx`，

其中正 `a` 表示负的目标轴向应变。由同一势能得到内力与 `P_active = (partial Psi_myo / partial a) adot`，避免在身份转换首步同时改变主动端口语义。

### Luminal and support ports

- 腔面单位法向固定为从内膜指向腔内的 `n_lum = +e_y`；
- 腔面对组织的规定牵引为 `t_lum = -p n_lum + tau e_x`；
- `P_lum = ∫ t_lum · v_endo dGamma`；
- 外边界规定牵引是独立 `P_ext` 端口；固定基座弹簧属于储能，固定基座速度为零，不记作外部功。

### Interfaces and ledger

- `Gamma_endo-ECM` 与 `Gamma_ECM-myo` 的弹性势分别产生严格成对反力；
- 两侧节点力之和、力矩及界面功率按同一权重审计；
- ECM 为标准线性固体：平衡弹簧加 Maxwell 支路内部应变 `Z`；
- 采用隐式中点离散，逐步核对

`Delta E_stored + D_ECM + D_endo + D_myo = W_lum + W_ext + W_active + R_num`。

所有量在 M1 为无量纲验证量；压力和剪切分量保持独立。

## Implementation Steps

1. 完成 M0 兼容性审计，明确可迁移端口、只可作历史基线的证据和不可迁移的 A1 结论；
2. 在新模块装配 DCM 连接、P1 FEM、SLS 内变量、双界面与外支撑；
3. 实现隐式中点时间推进及逐步/周期积分功率账本；
4. 输出心肌缩短、三层位移、ECM `Z`、DCM 连接力、双界面牵引及幅值—相位传递；
5. 执行零驱动、三类分离驱动、符号/反力、被动极限、耗散、确定性和最小时间/网格敏感性检查；
6. 生成版本化结果与诊断图；
7. 写执行日志并停在 M1 Human Gate。

## Impacted Files Or Modules

仅新增 `src/paper2_m1`、`tests/paper2_m1`、一个独立脚本、版本化结果和项目控制记录。若必须修改 `src/hybrid`、`src/route_h` 或旧结果，本执行立即停止并报告；当前计划不需要该修改。

## Test Plan

1. 零驱动参考态保持零位移、零 `Z`、零界面力；
2. 仅主动心肌驱动产生心肌缩短并向上游两层传递；
3. 仅腔面法向压力只直接加载内膜法向自由度；
4. 仅腔面剪切只直接加载内膜切向自由度；
5. 两界面逐节点作用—反作用闭合，压力/剪切符号与功率共轭一致；
6. 被动极限稳定，SLS 与各层阻尼耗散非负；
7. 逐步和周期积分账本残差达到浮点误差量级；
8. 相同输入重复运行逐数组一致；
9. 只做 `T64/T128` 与小/大一档网格敏感性；明确其不是收敛证明。

## Risks

- 条带模型不是完整二维/三维实体，不能宣称器官尺度或局部应力真实性；
- DCM 链只保留离散连接与逐细胞读数，不含完整细胞膜面积、体积和拓扑重排；
- 同位置界面不能替代后续非匹配 DCM–FEM 映射验证；
- 线性无量纲 SLS 只冻结记账和相位语义，不能直接拟合 cardiac jelly；
- 很小的敏感性误差不能被表述为空间/时间收敛。

## Acceptance Criteria

1. 不修改共享核心和旧 A1 证据；
2. 所有最小物理/数值测试通过；
3. 压力、剪切、主动和外支撑功率独立输出；
4. 双界面作用—反作用误差不超过 `1e-12`；
5. 逐步绝对功率账本残差不超过 `1e-11`，所有耗散不小于 `-1e-14`；
6. 确定性重放逐数组一致；
7. 时间/网格敏感性只作为初筛记录，不冒充正式收敛；
8. 结果进入人类 M1 Gate，未获批准不进入真实二维/三维主动心肌 FEM。

## Out Of Scope

- GPU worker；
- 双向 FSI、移动域 CFD 或真实流场；
- 整心室、真实几何或器官尺度；
- 实验拟合、疾病参数、`De–H` 扫描或参数海；
- A1 追加周期、阈值放宽、旧 ST2/ST3；
- Figure 3–6、共同极限正式比较或 EFE 生物学结论；
- Git 提交、推送、拉取、发布及任何删除/清理。

## Required Memory Updates

本执行不直接写稳定项目记忆。只有人类接受 M1 并完成独立检查后，才可把主动心肌 FEM 身份、端口符号和功率账本作为稳定结论。
