---
plan_id: PLAN-PRL-T1-FIGURE2-CONTACT-TOPOLOGY-V01
status: approved
planner: Codex project supervisor
approved_by: human_final_reviewer
approved_at: 2026-08-11
executor: Codex current task
inspector: pending_human_figure_gate
upstream:
  - project_control/t0_figure1_provisional_decision_v01.md
  - docs/theory/t0_dcm_fem_dcm_energy_interface_v01.md
preserves:
  - project_control/external_scientific_review_constraints_v01.md
  - project_control/hybrid_x1_k_r1_midpoint_collapse_diagnostic_failure_report_v10.md
---

# T1 / Figure 2 v01 接触拓扑理论合同

## Goal

在接触面积、总界面刚度、细胞主动应变和材料参数匹配时，解析判断“单侧基底接触”和“对称两侧/全周包埋”是否产生不同的缩短—弯曲响应，并给出进入显式 DCM–FEM 成对算例前的可证伪预测。

## Scientific Question

单侧 ECM 接触的影响是否能被一个等效标量外载完全替代，还是因为上下/内外反射对称性被破坏而出现新的伸长—弯曲耦合？

## Matched Comparison

- 相同细胞轴向刚度、弯曲刚度和主动本征应变；
- 相同总接触刚度 `K=K_minus+K_plus`；
- 相同快时间尺度，不加入生长和重塑；
- 单侧工况：`K_minus=K, K_plus=0`；
- 对称包埋最小代理：`K_minus=K_plus=K/2`；
- 真实三维四面/全周接触留给后续显式成对算例。

## Outputs

1. `docs/theory/t1_contact_topology_reduced_model_v01.md`：可解析伸长—弯曲模型；
2. `figures/theory/t1_figure2_contact_topology_v01.png`：Figure 2 审阅图；
3. `figures/theory/t1_figure2_contact_topology_v01.svg`：可编辑矢量图；
4. `scripts/build_t1_figure2_contact_topology_v01.py`：可复算绘图；
5. `project_control/t1_figure2_execution_log_v01.md`：执行与自检记录。

## Implementation Steps

1. 将单细胞约化为具有主动本征应变、轴向刚度和弯曲刚度的细长体；
2. 将上下两侧 ECM 连接约化为总刚度相等但极性不同的弹性基础；
3. 推导伸长与无量纲曲率的二次能量、稳定性条件和闭式解；
4. 证明对称包埋的伸长—弯曲交叉项因反射对称性消失，单侧接触则保留；
5. 评估 Figure 1 中面积方向二阶张量是否足以编码“哪一侧接触”；
6. 生成参数曲线和状态图，明确线性约化模型的适用边界。

## Test Plan

- 对能量求导并与 2×2 线性平衡方程核对；
- 用直接线性求解核对闭式解；
- 检查 Hessian 行列式为正的稳定域；
- 检查 `m=0` 时曲率严格为零；
- 检查 `K->0` 时恢复自由主动应变；
- 检查弯曲刚度趋无穷时单侧和对称响应收敛；
- 检查图中只显示解析理论，不混入 DCM–FEM 模拟数据。

## Falsifier

如果在接触面积和总刚度匹配的显式三维算例中：

- 单侧接触不产生可分辨的弯曲/牵引偏心；或
- 观察差异完全由总刚度标量解释；或
- 解析预测的极性趋势在加密后反转，

则“接触拓扑是独立控制变量”的主张必须删除或收窄。

## Acceptance Criteria

1. 闭式解、直接线性求解和能量极小值一致；
2. 明确区分接触面积、方向二阶矩和有符号极性；
3. 给出至少一个非平凡、可由未来 DCM–FEM 算例否证的预测；
4. 全部结果在正定稳定域内；
5. 获得人类 Figure 2 Decision Gate 决定后，才起草显式固定拓扑 benchmark；
6. 不把约化梁模型直接解释成真实心肌细胞的定量预测。

## Risks

- 用二阶方向张量错误地代表上下极性；
- 把二维两侧模型等同于完整三维包埋；
- 在小应变梁模型中使用过大的曲率；
- 未匹配总界面刚度就比较两个拓扑；
- 把解析趋势图冒充细胞或 ECM 数值结果。

## Out Of Scope

- 显式 DCM–FEM 求解、重网格和长轨迹；
- 非线性黏附断裂、接触脱开和摩擦；
- 心肌细胞层、心内膜层和器官几何；
- 参数标定、实验拟合、EFE 和慢发育。

## Required Memory Updates

Figure 2 经人类接受前，新增的接触极性向量和伸长—弯曲定律均保持 proposed 状态。若接受，应在 Figure 1 v02 中补充“面积分数 + 有符号极性 + 二阶方向矩”的拓扑描述。

