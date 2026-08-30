---
plan_id: PLAN-PRL-INDEPENDENT-THEORY-MAINLINE-V01
status: approved_active
planner: codex_current_task
requested_by: human_final_reviewer
approved_by: human_final_reviewer
approved_at: 2026-08-27
parent_decision: project_control/prl_independent_theory_mainline_decision_v01.md
current_lifecycle: prl_figure2_spatial_tolerance_contract_v02_human_review
paper_role: independent_theory_first
downstream_application: EFE_Nature_experiment_first
current_authorization: drafting_only_no_spatial_or_tolerance_execution
current_contract: project_control/prl_figure2_spatial_tolerance_validation_contract_v02.md
---

# PRL 独立理论主线执行计划 v01

## 1. 科学问题与论文身份

PRL 研究一个独立于 EFE 病名的物理问题：周期主动组织通过有限厚度、可松弛的黏弹夹层驱动被动边界时，机械信息如何被传递、滤波、延迟和局部化；何时连续介质足够，何时必须保留细胞尺度身份和异质性。

论文身份是 **理论—计算主导、最小实验校准与独立检验支撑**。EFE Nature 是 **实验—疾病机制主导、调用已冻结理论框架**。两者共享接口，不共享中心结论。

## 2. 最小理论系统

`active myocardial cells/surface → finite-thickness viscoelastic interlayer → passive endocardial cells/surface`

### 快时间输入

- 主动应变/首选长度的幅值、频率、波形和空间异质性；
- 夹层厚度、剪切/体积刚度、黏弹松弛时间与水化替代机制；
- 双界面黏附、滑移、脱黏前响应和外部支承；
- 细胞尺度、异质性相关长度与边界几何。

### 主要输出

- 三层位移、形变、界面牵引和作用—反作用；
- 幅值传递率、相位差、峰值时序、牵引热点和空间相关长度；
- 储能、耗散、功率闭合和黏弹内部变量；
- 离散—连续误差、适用域和失败边界。

### 候选无量纲组

- `De = tau_relax / T_beat`：夹层记忆与心搏周期之比；
- `H = h_interlayer / L`：夹层相对厚度；
- `K = k_interface L / E_interlayer`：界面连接相对刚度；
- `R = E_boundary / E_interlayer`：被动边界与夹层刚度比；
- `epsilon_c = d_cell / ell_mech`：细胞尺寸与机械平滑长度之比；
- `CV_A` 与 `ell_A/d_cell`：主动异质性幅度和相关长度。

符号、量纲和具体归一化必须在正式 Figure 1 前冻结；目前不得把候选组写成已验证控制律。

## 3. 论文图主线

### Figure 1 — 最小系统、方程与无量纲结构

- 三层几何、功率端口、主动驱动和黏弹记忆；
- 方程、边界/界面条件和候选无量纲组；
- 连续—离散模型层级及允许主张。

**通过门：** 方程、单位、符号、被动/无黏性/快速松弛/刚性界面等极限全部闭合。

### Figure 2 — 数值正确性与时间/空间连续极限

- 已冻结的 T16/T32/T64 结果及 Figure 2 v01；
- 当前获批的 T128 定向验证；
- 后续另行批准的空间、容差和功率闭合证据；
- 所有失败项与不可辨识项显式保留。

**当前状态：** P5 的严格失败作为历史证据保留；P6 已于 2026-08-30 通过
T128 Human Gate，Figure 2 v02 冻结为时间离散阶段 FINAL。当前只获准起草空间
与容差验证合同，尚未授权任何空间或容差计算。

### Figure 3 — 传递函数与动力学状态图

- `De–H–K–R` 中的幅值衰减、相位滞后、牵引局部化和耗散；
- 周期波形和场分布的代表性状态；
- 解析/降阶近似与三维数值的对应。

**通过门：** 规律跨越多个网格、边界和参数量级；不允许只展示挑选参数的漂亮轨迹。

### Figure 4 — 全 FEM 共同极限与离散—连续适用边界

- cell-resolved all-FEM、homogenized all-FEM 与 DCM–FEM 的共同极限；
- 相同平均主动载荷、不同细胞分布的反事实比较；
- `epsilon_c–CV_A–ell_A/d_cell` 适用域；
- 若均质 FEM 足够预测局部输出，DCM 降级为实现工具。

**通过门：** 先通过匹配本构与共同极限，再讨论细胞身份的增量价值。N1-2d 仍需单独批准。

### Figure 5 — 最小实验校准、独立检验与可迁移预测

- `PRL-Cal` 只给量级和参数范围；
- `PRL-Val` 检验冻结模型对相位、衰减、热点或扰动方向的预测；
- 至少一个未参与参数选择的个体、时相或扰动；
- 明确预测失败和适用边界。

**通过门：** 校准/验证分区预先登记，模型在解盲前冻结；不得调用 `EFE-Discovery` 或 `EFE-Blind` 追求 PRL 拟合。

## 4. 执行顺序与 Human Gates

1. **P6 时间门：** 已完成并于 2026-08-30 通过 T128 Human Gate；
2. **空间与容差门：** 合同草案已获准起草，检查 DCM 表面、ECM 体网格、界面 footprint、容差、功率闭合与边界敏感性；草案本身不授权执行；
3. **共同极限门：** 另行批准 N1-2d，完成 all-FEM 对照和离散—连续适用域；
4. **理论状态图门：** 冻结无量纲组后做最小参数设计，不做无界参数海；
5. **PRL-Cal 门：** 只读实验需求清单与校准协议通过后，才接入实验量级；
6. **PRL-Val 冻结门：** 代码、方程、参数和统计判据冻结后解盲；
7. **投稿冻结门：** 形成版本化理论包、可复算图包、限制声明和作者终审。

每个门均保持“人类批准—执行—独立核验—人类接受”的顺序；阶段完成不自动升级论文结论。

## 5. EFE Nature 的接口

PRL 发表/冻结后向 EFE Nature 只提供以下稳定接口：

| 接口 | PRL 输出 | EFE Nature 用途 |
|---|---|---|
| `FrameworkVersion` | 方程、适用域和失败边界 | 证明分析框架先于疾病数据存在 |
| `GeometryAdapter` | 从 4D 轮廓/位移到三层输入的转换 | 个体化力学重建 |
| `MechanicalHistory` | 相位、幅值、牵引、耗散、记忆核 | 与病灶、谱系和细胞状态对齐 |
| `ProspectiveRule` | 热点/时间窗/方向性预测 | EFE-Blind 前瞻检验 |
| `ModelBoundary` | 不适用条件和替代机制 | 解释失败或升级模型，而非隐藏偏差 |

EFE Nature 不得直接继承 PRL 的“普适性”作为疾病因果证据。疾病因果必须由谱系、扰动、救援和人源验证独立建立。

## 6. 当前禁止扩展

除 P6 P0–P3 外，当前计划不自动授权 T256、空间细化、参数扫描、N1-2d、N1-3、慢重塑、Node 2–4、GPU worker、新求解器或人类 EFE 数据拟合。任何扩展必须在对应 Human Gate 后另立前瞻性合同。
