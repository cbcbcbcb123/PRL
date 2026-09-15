---
decision_id: DECISION-PRL-P6-T128-ACCEPTANCE-AND-SPATIAL-TOLERANCE-DRAFTING-V01
status: approved
decider: human_final_reviewer
decided_at: 2026-08-30
related_plan: project_control/efe_node1_n1_2c_p6_t128_targeted_validation_contract_v01.md
related_inspection: project_control/prl_p6_t128_execution_and_human_gate_review_v01.md
related_correction: project_control/prl_p6_t128_provenance_label_correction_v01.md
next_contract: project_control/prl_figure2_spatial_tolerance_validation_contract_v01.md
authorization: drafting_only_no_execution
---

# PRL P6 T128 接受与空间—容差合同起草授权 v01

## 人类终审决定

人类终审接受 P6 T128 结果及其有界结论，确认 Figure 2 v02 为
**时间离散阶段 FINAL**，并接受 T128 底层 `T16 only` 标签问题的加性勘误。

冻结表述为：

> 对固定 D0/E0/F150 几何、材料、界面、激活和空间离散，主要波形、幅值、
> 积分、耗散、适用三维场、周期闭合和黏弹记忆峰值相位在 T64→T128 比较下
> 达到 P6 预登记时间离散门。

P5 的严格失败记录继续作为历史证据保留，不被追溯改判。T64 可作为当前固定
基线常规幅值和场输出的生产级候选；对峰值相位敏感的终局复核仍保留 T128。

## Figure 2 v02 的冻结身份

Figure 2 v02 是“时间离散阶段最终包”，不是整篇论文 Figure 2 的最终版本。
它不证明空间收敛、容差独立性、功率闭合、材料标定、DCM–FEM 必要性、EFE
机制或实验一致性。后续若形成空间与容差证据，应另建 Figure 2 v03 工作包，
不得覆盖或改写 v02。

## 新授权

批准起草 `PRL Figure 2 空间与容差验证合同 v01`。该合同必须：

1. 以最小正交矩阵分别检验 ECM 体网格、DCM 表面、F150→F200 边界和求解容差；
2. 使用共同材料/物理域映射，不直接比较不同网格的节点数组；
3. 保留作用—反作用、合矩、周期稳态、安全门和功率闭合；
4. 分阶段返回人类审阅，并优先提交可解释的三维场图；
5. 保持 fail closed，不以追加网格、放宽门限或更换求解器自动绕过失败。

## 明确未授权

本决定只授权起草，不授权实现或计算。仍不授权：

- D1、E1、E2、F200 或任何空间细化实算；
- 耦合/求解容差扫描或严格容差周期；
- T128 细网格联合计算、T256 或追加周期；
- 参数扫描、N1-2d、N1-3、原 EFE Node 2–4；
- GPU worker、新外部求解器、Active-Foam 或双向 FSI。

下一步必须提交空间与容差合同草案，由人类终审另行决定是否批准其中最小的
预检阶段。
