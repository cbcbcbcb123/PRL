---
plan_id: PLAN-PAPER2-M2-ACTIVE-MYO-FEM-IDENTITY-V01
status: approved
planner: Codex current supervisor task
approved_by: human_final_reviewer
approved_at: 2026-09-03
executor: Executor | Paper 2 M0-M1 理想体模型
inspector: pending_independent_scientific_inspection
upstream:
  - project_control/paper2_m1_acceptance_and_m2_contract_authorization_decision_v01.md
  - project_control/paper2_m0_compatibility_audit_v01.md
  - project_control/paper2_m0_m1_idealized_model_execution_log_v01.md
  - D:/我的坚果云/33 My Projects/Projects/@ YQ/@ 规划文件/02_论文2_理论型_v3.pdf
execution_authorized: m2a_only
current_lifecycle: execution
---

# Paper 2 M2：主动心肌 DCM→FEM 身份转换合同 v01

## 1. Goal

在不改变心内膜 DCM、ECM 本构、腔侧载荷、外支撑和功率端口的条件下，仅替换
心肌表示，检验旧 preferred-length 心肌 DCM 与新主动本征应变心肌 FEM 是否在
共同宏观极限下给出一致的缩短、界面牵引、相位、能量和功率响应。

M2 分成两个不可自动连跳的门：

- **M2A：真实二维直接身份转换。** 在平直矩形层状域中直接比较心肌 DCM 与二维
  主动心肌 FEM；其余域和输入完全同构。
- **M2B：三维有限变形验证。** 只有 M2A 获人类接受后，才可在三维理想心肌壁块中
  验证相同主动应变映射、近不可压缩性、纤维方向和功率语义。M2B 不自动获批。

该合同不研究 De–H 状态律，不比较心内膜 DCM 与 all-FEM，也不加入流体求解。

## 2. Scientific question and bounded claim

### Question

当几何、被动切线刚度、激活时序、总主动功、外载和界面离散全部受控时，将离散
心肌 preferred length

`L_f*=L_f0(1-a)`

替换为连续主动本征应变，是否保持预注册宏观端点和功率端口？

### Allowed claim if passed

只允许声称：在预注册的二维理想域、激活和载荷范围内，主动心肌 FEM 是旧心肌 DCM
的有界宏观替代；旧证据只能按逐端点误差上界迁移。

### Forbidden claim

不得声称新 FEM 已经是生理真实心肌、在所有几何或参数下等价、已经验证 EFE、已经
证明 DCM 不必要，或已经建立 Nature Physics 级普适规律。

## 3. Inputs

1. M1 冻结的端口、法向、主动本征应变和离散功率语义；
2. 旧心肌 DCM 的 preferred-length/metric 能量及其主动功定义；
3. 项目现有 CPU `dolfinx/dolfinx:v0.11.0` 路径和已接受的共同求积设计；
4. 最新论文2文件 v3（内部 v4.0）的 Figure 1–3、Figure 5 和执行门；
5. 所有 M1 和旧 A1 失败证据，只作设计输入，不作 M2 通过证据。

未经单独批准，不引入实验参数、真实心室几何、PIV/CFD 数据或新的外部求解器。

## 4. Frozen model identity

### Shared domains

- 心内膜：同一 DCM 链/网，节点、连接、阻尼和读出完全相同；
- ECM：同一二维黏弹 FEM 域、SLS 参数、时间离散和内部变量初态；
- 腔侧：同一规定牵引 `t_lum=-p n_lum+tau e_x`；
- 外侧：同一支撑与 `P_ext` 端口；
- 界面：同一位置、同一求积、同一耦合刚度和转置力映射。

### Comparison arms

- **Arm DCM：** 心肌域使用沿共同纤维方向布置的离散 preferred-length 网络；
- **Arm FEM：** 心肌域使用二维连续 FEM 和主动本征应变。

唯一允许改变的字段是 `myocardium_representation`。若几何、ECM、内膜、载荷、
支撑、时间步、采样、求积、容差或激活时序发生差异，该对照无效。

## 5. Active-strain mapping

M2A 继续使用 M1 已冻结的 active-strain 路线，不同时比较 active stress。

### Small-strain bridge

沿纤维方向 `f0`：

`epsilon_active = -a (f0 tensor f0)`，

使均匀纤维线段的目标缩短与 `L_f*=L_f0(1-a)` 在小应变一阶一致。

### M2B finite-strain candidate

三维阶段拟采用乘法分解 `F=Fe Fa`，并令

`Fa=(1-a) f0 tensor f0 + (1-a)^(-1/2)(I-f0 tensor f0)`，

以保持主动变换 `det(Fa)=1`。该式必须先通过量纲、行列式、`a→0`、均匀缩短和
功率导数的独立复核；M2A 通过不自动批准这一三维形式。

### Calibration and held-out quantities

只允许使用两个校准约束：

1. 小扰动被动切线刚度；
2. 一个基准主动周期的总主动功。

缩短波形、界面牵引、相位、储能/耗散分配、空间场和组合载荷响应全部为留出端点，
不得参与参数拟合。

## 6. M2A geometry and numerical design

### Geometry

- 二维平面应变矩形层状域，仅作为身份转换试验台；
- 周期方向为 `x`，层厚方向为 `y`；
- 心内膜 DCM 位于腔侧，ECM 和心肌为具有非零厚度的二维域；
- 纤维基准方向为 `e_x`；
- 第一版使用匹配界面以隔离心肌表示，非匹配界面另设后续合同。

### Discretization ladder

- 三层嵌套空间离散：沿 `x` 和厚度方向同步加密；粗网格必须严格嵌入细网格；
- 时间路径：`T64→T128→T256`，仅在前一层全部硬门通过后进入下一层；
- C0/C1 容差配置沿用项目同义字段，任何求解器参数必须由一个不可变配置对象贯穿；
- 只用 CPU。不得启动 GPU worker。

具体单元数、自由度和预计耗时必须先由只读/轻量预检冻结；若单个端点预计超过批准
资源预算，返回人类门，不静默缩网格或放宽容差。

## 7. Pre-registered cases

M2A 只执行以下有限工况，不做参数扫描：

1. `ID-P0`：零驱动与刚体/约束检查；
2. `ID-P1`：被动单轴小扰动，用于唯一的被动刚度校准；
3. `ID-A1`：均匀主动驱动、无腔侧载荷，用于总主动功校准；
4. `ID-A2`：同一主动波形的周期响应，留出缩短、牵引、相位和能量；
5. `ID-LN`：仅腔侧法向牵引；
6. `ID-LS`：仅腔侧切向牵引；
7. `ID-C0`：主动驱动与腔侧牵引同相组合；
8. `ID-CQ`：主动驱动与腔侧牵引相差 `pi/2`；
9. `ID-S1`：单一预定义空间激活模式，检验界面场和热点位置是否由表示差异改变。

`ID-C0/ID-CQ/ID-S1` 不用于调参。任何新增工况必须返回人类门。

## 8. Outputs and common observables

每个 Arm、每个工况、每个离散端点必须使用共同采样和共同单位输出：

- 心肌自由缩短、受限缩短及位移/应变场；
- ECM 位移、应变、应力、`Z` 和耗散；
- 心内膜 DCM 节点位移、连接力和机械历史；
- ECM–心肌与心内膜–ECM 界面牵引波形；
- 输入—响应增益、相位和相干性；
- `P_active`、`P_lum`、`P_ext`、储能、各耗散和 `R_num`；
- 每周期状态差、空间误差、时间误差和 C0/C1 差；
- DCM 与 FEM 的逐端点差异及合并数值不确定度。

## 9. Error definitions and proposed gates

以下阈值均为**合同提案**，只有人类批准后才冻结。

### Exact or structural gates

- 单位、法向、牵引正号和主动功导数：全部通过；
- 界面作用—反作用相对误差 `<=1e-10`；
- 功率共轭与总账本归一化残差 `<=1e-8`；
- 所有物理耗散 `>=-1e-12`（归一化单位）；
- 零驱动状态范数 `<=1e-10`；
- `ID-P1` 的均匀应变制造解相对误差 `<=1e-6`。

### Numerical credibility gates

- 三层空间路径和 `T64/T128/T256` 必须方向一致；
- 最细两层每个主端点差 `<=1%`，且不得出现误差反增或热点跨单元跳变；
- C0/C1 主端点差 `<=0.5%`；
- 周期状态：所有冻结波形和内部变量的相对差 `<=1e-3`；
- 若上述任一门失败，不计算跨模型等价性结论。

### Cross-representation identity gates

在校准工况之外，Arm DCM 与 Arm FEM 必须同时满足：

- 峰值缩短相对差 `<=5%`；
- 缩短波形和共同界面牵引的归一化 `L2` 差 `<=5%`；
- 基频相位差绝对值 `<=0.05 rad`，且相干性先通过预注册门；
- 周期总储能变化和总耗散相对差分别 `<=10%`；
- 留出组合载荷下主要增益相对差 `<=10%`；
- `ID-S1` 热点中心差不超过一个最细共同单元，且不存在未解释的热点分裂差异。

每项同时报告绝对差、相对差和合并数值不确定度。若分母接近零，禁止使用相对误差，
改用合同冻结的绝对尺度。

## 10. Decision logic

- **GO-ID：** 所有结构门、数值门和留出身份门通过。允许把列明端点的旧证据按
  实测误差上界迁移，并起草 M2B 合同执行附录。
- **MAYBE-ID：** 结构/数值门通过，但部分留出端点为 `5–15%` 差异，且差异稳定、
  可解释。保留 FEM 作为正式模型，但不得迁移相应旧证据；先收缩可迁移端点。
- **NO-GO-ID：** 功率/作用反作用/周期/收敛失败，或关键留出端点差异 `>15%`。
  不得继续三维；记录失败并定位映射、本构或离散原因。

GO-ID 不表示 M2B 自动执行；M2A 结果必须独立检查并由人类批准。

## 11. M2B conditional scope

仅当 M2A 获 GO-ID 后，才允许提交 M2B 执行附录。M2B 的最小范围为：

1. 三维矩形心肌壁块和单一均匀纤维方向；
2. active-strain 行列式、均匀缩短和被动/主动制造解；
3. 近不可压缩参数敏感性与体积误差；
4. 三维界面牵引和功率共轭；
5. 一个主动工况、一个腔侧载荷工况和一个组合工况；
6. CPU 资源预检和最小嵌套网格。

M2B 不包含椭圆心室、纤维旋转、流体、De–H 扫描或实验参数。

## 12. Implementation Steps

若本合同获批，Executor 只能按以下顺序执行 M2A：

1. 写轻量资源/依赖预检和不可变配置；
2. 建立二维同构比较域和两个心肌表示；
3. 完成 `ID-P0/P1` 制造解与被动刚度校准；
4. 完成 `ID-A1` 主动功校准并冻结映射；
5. 依序运行留出 `ID-A2/LN/LS/C0/CQ/S1`；
6. 完成空间、时间、容差和周期门；
7. 生成逐端点等价矩阵、失败剖面和版本化结果包；
8. 写执行日志并停止在 M2A Inspector/Human Gate。

任何硬门失败即 fail closed；不得自动调参、扩大网格、增加周期或改变阈值。

## 13. Impacted Files Or Modules

优先新增：

- `src/paper2_m2/`；
- `tests/paper2_m2/`；
- `scripts/run_paper2_m2_identity_2d_v01.py`；
- `results/paper2_m2/identity_2d_vNN_YYYYMMDD/`；
- M2A execution log、inspection report 和 Human Gate 记录。

默认不修改 `src/hybrid`、`src/route_h`、`src/paper2_m1`、旧结果或旧合同。若共享接口
修改不可避免，必须先提交 deviation，列出文件、原因、回归范围和回退方案。

## 14. Test Plan

- 主动映射：`a=0`、小应变一阶等价、`det(Fa)=1` 候选式；
- 二维制造解：均匀拉伸、均匀主动缩短、压力/剪切分离；
- 接口：作用—反作用、同点/转置映射、界面功率；
- SLS：内部变量更新、被动松弛和非负耗散；
- 数值：嵌套空间、T64/T128/T256、C0/C1、周期门；
- 身份：九个预注册工况的逐端点差异；
- 确定性：相同输入逐数组重放；
- 回归：M1 七项测试和旧功率账本测试不得退化。

## 15. Risks and falsifiers

1. 两个参数即可匹配校准端点，但留出牵引/相位显著不同，说明表示不等价；
2. DCM 网络各向异性或尺度效应不能由简单连续本构吸收；
3. 周期差异可能来自 SLS 初态而不是心肌表示；
4. 匹配界面可能掩盖非匹配投影误差；
5. 线性二维通过不保证三维有限变形有效；
6. 若差异只在数值误差带内，不能包装成新的物理效应；
7. 若热点随网格跳变，不得讨论局部化。

## 16. Acceptance Criteria

M2A 进入人类门前必须同时具备：

1. 所有输入、两个 Arm 和唯一差异字段可审计；
2. 校准量与留出量严格分离；
3. 九个工况、三层空间、三层时间和 C0/C1 的完整矩阵或明确失败停止点；
4. 每个硬门和身份门给出原始值、阈值和判定；
5. 总功率、界面功率和耗散闭合；
6. 不把旧 A1 或 M1 结果当作 M2 通过证据；
7. 独立 Inspector 给出 `accepted / accepted_with_caveats / revision_required / blocked`；
8. 人类决定 GO-ID、MAYBE-ID 或 NO-GO-ID。

## 17. Out Of Scope

- 本合同草案本身不授权任何求解；
- GPU worker；
- M2B 自动执行；
- active-stress/active-strain 模型选择比较；
- 非匹配界面正式验证；
- 圆环、椭圆、长椭球和真实心室；
- CFD、单向耦合、双向 FSI；
- De–H–Pi_f–Delta_phi 扫描；
- 心内膜三模型共同极限、实验拟合或 EFE 结论；
- 删除、覆盖、清理、Git 提交/推送或发布。

## 18. Required Memory Updates

本合同和后续执行均不直接写稳定记忆。只有 M2A 经独立检查和人类接受后，才可把
主动应变映射、可迁移端点及其误差上界作为候选记忆；M2B 必须另行验收。
