---
decision_id: DECISION-EFE-NODE1-N1-1A-FOOTPRINT-V01
status: approved
decider: human_final_reviewer
decided_at: 2026-08-18
parent_authorization: project_control/efe_node1_n1_1_authorization_decision_v01.md
---

# EFE Node 1 N1-1A ECM footprint audit authorization

人类终审批准在进入 N1-2 前扩大 ECM 横向区域并执行边界敏感性审计。

本次授权覆盖：

1. 将 ECM 的 `x-z` 横向足迹参数化为 `1.0×/1.5×/2.0×`；
2. ECM 厚度保持 `0.30`，细胞与界面几何保持不变；
3. 随足迹扩大同步增加 `x/z` 网格数，避免把边界效应与单元粗化混淆；
4. 比较零态、峰值主动收缩、界面牵引、KKT、几何质量和边界敏感性；
5. 生成阶段审阅图并返回人类图审门。

本决定不授权 N1-2 周期稳态、16/32/64 时间收敛、正式 D1/E1 空间
收敛、材料参数筛选、厚度扫描、Node 2、实验拟合或双向 FSI。

