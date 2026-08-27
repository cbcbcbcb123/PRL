---
decision_id: DECISION-EFE-N1-2D-ALL-FEM-COMMON-LIMIT-V01
status: approved
decider: human_final_reviewer
decided_at: 2026-08-25
related_plan: project_control/efe_n1_2d_all_fem_common_limit_and_discrete_continuum_plan_v01.md
related_inspection: not_started
memory_target: efe_theory_mainline_and_paper_figure_spine
execution_authorized: false
---

# EFE N1-2d 全 FEM 共同极限与离散—连续跨越决定 v01

人类终审已于 2026-08-25 明确同意把“全 FEM 如何验证 DCM–FEM、以及如何
证明何时需要显式离散细胞”的最新讨论写入项目，作为后续不得遗忘的主线增补。

据此决定：

1. 在 Node 1 数值收敛完成后、N1-3 全面机制/参数扫描前，设置
   `N1-2d：全 FEM 共同极限与离散—连续跨越`；
2. 采用三模型层级：cell-resolved all-FEM、homogenized all-FEM 与
   DCM–FEM–DCM；
3. 全 FEM 的首要用途是验证共同力学极限和混合界面，不把它当作生物学真值；
4. DCM 的必要性只能通过细胞颗粒性、细胞身份、异质机械历史、阈值状态转换和
   局部 ECM 源项带来的可检验信息增益来支持；
5. 论文不得表述“FEM 不能模拟细胞”或“DCM 天然比 FEM 更准确”；
6. 若均质 FEM 在相关范围内仍能预测局部牵引、超阈值细胞比例和 ECM 萌生位置，
   则 DCM 必要性主张必须降级，DCM 仅作为实现工具；
7. 本决定批准方案进入项目主线，但**不批准任何 FEM/DCM 新计算、GPU worker、
   外部求解器安装、参数扫描或论文图执行**。每个计算包仍须另立合同并经人类批准。

本决定是以下既有文件的增补，不覆盖或追溯修改它们：

- `project_control/efe_theory_mainline_node_plan_v01.md`；
- `project_control/research_mainline_three_node_plan_v02.md`；
- `project_control/efe_node1_fast_trilayer_mechanics_contract_v01.md`；
- `docs/theory/t0_dcm_fem_dcm_energy_interface_v01.md`。

