---
execution_id: EXEC-EFE-NODE0-MINIMAL-THEORY-V01
plan_id: EFE-THEORY-MAINLINE-NODES-V01
executor: codex_primary_single_agent
started_at: 2026-08-13
completed_at: 2026-08-13
status: completed
inspection_status: accepted_by_human_gate_0_figure1_provisional
deviation_records: []
---

# EFE Node 0 v01 执行记录

## Approved plan reference

人类终审于 2026-08-13 批准 `project_control/efe_theory_mainline_node_plan_v01.md`，并明确授权开始 Node 0。本轮没有执行 Node 1–4、求解器修改、参数扫描、数据拟合或双向 FSI。

## Files changed

- `project_control/efe_theory_mainline_node_plan_v01.md`：登记人类批准和 Gate 0 边界；
- `project_control/efe_mainline_authorization_decision_v01.md`：记录主应用切换为 EFE；
- `project_control/research_mainline_three_node_plan_v02.md`：标记为 `superseded`，内容保留；
- `project_control/publication_three_node_single_paper_decision_v01.md`：标记为 `superseded`，内容保留；
- `docs/theory/efe_node0_minimal_theory_contract_v01.md`：Node 0 最小理论合同；
- `project_control/efe_node0_figure1_brief_v01.md`：Figure 1 科研绘图规格；
- `scripts/build_efe_node0_figure1_v01.py`：确定性 PNG/SVG 生成脚本；
- `figures/theory/efe_node0_figure1_fast_slow_framework_v01.png`；
- `figures/theory/efe_node0_figure1_fast_slow_framework_v01.svg`；
- `project_control/efe_node0_execution_log_v01.md`。

未删除、覆盖或改判任何历史失败包、Route H 冻结证据、X1-K 结果、M1 数值结果或旧 Figure 1 文件。

## Scientific decisions made within Node 0

1. 采用心腔—心内膜 DCM—cardiac-jelly/fibrous ECM FEM—主动心肌 DCM 的层次；
2. 压力和 WSS 采用规定载荷，第一版不是双向 FSI；
3. 用代表性心搏映射快时间，用细胞状态/ECM 方程推进慢时间；
4. 完整模型中 `h_EFE` 是由几何和生长张量导出的观测量，不与 `F_g` 重复作为独立状态；
5. 注册 `H1-Endo`、`H2-Mes`、`H3-Mixed` 三个来源竞争变体；
6. 快时间功率账本复用已审阅 T0 的同一点求积和转置界面映射；
7. 慢时间化学供能与重塑耗散不伪装进快时间能量账本，留待 Node 2 单独建立；
8. 在 Jacobian、分岔、持出预测完成前，不使用已证实的“双稳态、机械记忆、临界转变”表述。

## Checks run

### 1. 方程边界方向

- 对 `q_E/q_M` 的最小动力学检查：`q=0` 时向区间内，`q=1` 时向区间内；
- 对 `rho_c/rho_el` 的饱和产生—降解式检查：`rho=0` 时非负，`rho=rho_max` 时非正；
- 胶原取向律在 `tr(A_c)=1` 时的迹变化绝对值为 `3.469e-17`；
- 纯振荡切向牵引的 OSI 数值检查为 `0.5`，符合定义范围。

### 2. 功率符号与量纲

- 采用固体指向心腔的外法向 `n_L`，压力牵引为 `-p n_L`；
- `P_p=-integral p n_L dot v_e da` 与 `P_wss=integral tau_w dot v_e da` 均为功率；
- preferred-length 主动输入符号与既有 T0/Route H 约定一致；
- `R_num` 单列为离散残差，不计作物理耗散。

### 3. 数学与文本完整性

- 显示公式定界符 `\[` 与 `\]` 数量一致；
- H1/H2/H3、十个极限/反事实、Falsifiers、实验映射和 Human Gate 0 均存在；
- Node 1 前置硬门明确保留 X1-K。

### 4. Figure 1

- 绘图脚本 `py_compile`：通过；
- PNG：`3960 x 2640`，比例严格为 `3:2`；
- SVG：XML 解析通过；
- 原始分辨率目视检查：四个 panel 完整，无裁切；压力与 WSS 分开；快慢时间分开；三种细胞来源并列；病理状态明确标为 candidate；底部声明不是模拟或实验结果。

## Gate-critical hashes

- Theory Markdown：`C419AE19C3C544B06CA87B83734B3A262205F7FD4223A047EB176EC69CB0666B`
- Figure PNG：`179C34291031D5F1B3CFAAD33B886EA65EF43C4A8F0FC73EA6548E5A404E7FFF`
- Figure SVG：`3C86C2F144994697CC0370953E879BD6437E107FB96948455214FA28C4861342`

这些哈希只标识本次 Gate 0 交付版本，不把工作草案升级为冻结科学证据。

## Deviations

无范围偏差。Figure 1 采用确定性 Matplotlib/SVG 生成，而不是生成式位图，因为本图以精确层次、数学标签和可编辑性为主；绘图规格仍按批准的普通论文科研审阅风格执行。

## Remaining risks

- 细胞来源尚无谱系数据裁决；
- 单相黏弹与孔弹/HA 水化机制尚未比较；
- Node 0 只定义慢时间方程形式，尚未建立慢时间自由能/耗散账本；
- X1-K 尚未通过，完整快速三层长轨迹仍未授权；
- Figure 1 已由人类 Gate 0 暂定保留；它仍是理论结构示意，不是模拟、实验或疾病因果证据。

## Next lifecycle state

Human Gate 0 已完成：Node 0 v01 被接受，Figure 1 暂定保留，并仅授权起草 Node 1 合同。Node 1 数值执行仍未授权；X1-K 硬门继续有效。
