---
decision_id: DECISION-EFE-NODE1-N1-2C-T64-ACCEPT-P5-V01
status: approved
decider: human_final_reviewer
decided_at: 2026-08-26
related_plan: project_control/efe_node1_n1_2c_time_refinement_contract_v01.md
related_inspection: project_control/efe_node1_n1_2c_t64_execution_and_review_request_v01.md
memory_target: efe_node1_n1_2c_lifecycle
---

# EFE Node 1 N1-2c T64 接受与 P5 授权决定 v01

人类终审回复“继续”。结合紧邻 Human Gate T64 的建议，解释并冻结为：

1. 接受 T64 cycle 2 为 N1-2c 的 T64 周期稳态候选；
2. 接受 T32→T64 重采样只用于暖启动、正式 T64 证据来自 128 个新求解事务的
   证据边界；
3. 接受并冻结 T64 阶段诊断图 v01 为当前 FINAL；
4. 批准 P5：只读取已接受的 T16 cycle 8、T32 cycle 2 与 T64 cycle 2，执行三档
   时间裁决、观察阶或不可辨识判定，并制作正式时间收敛 Figure 2；
5. P5 完成后停在 N1-2c Final Human Gate；未经新决定，不把 T64 写入稳定项目
   记忆，也不进入 N1-2d；
6. P5 不授权 T128、任何新心搏周期、空间细化、参数扫描、N1-2d、N1-3、Node 2、
   GPU worker或新外部求解器。

## P5 冻结派生场公式

结果 schema 未直接保存的场只允许从冻结顶点、拓扑、材料参数和内部变量后处理：

1. 每个 ECM 四面体的变形梯度按正式模型同一式
   `F = Ds @ Dm_inverse`；`J = det(F)`；
2. 主应变定义为 Green–Lagrange 应变
   `E = 0.5 * (F.T @ F - I)` 的最大特征值；
3. 第一 Piola 应力 `P` 使用正式 ECM 本构
   `density_and_first_piola`，Cauchy 应力为 `sigma = P @ F.T / J`，比较其最大
   主值；
4. 相邻状态间离散耗散沿用正式 SLS 更新：
   `eta_ve * ||(Z_n - Z_(n-1))/dt||^2 * V0 * dt`；
5. 两界面牵引从正式 tether 本构返回的配对结点力重建，以参考权重归一化；其
   法向和切向分量使用冻结物质映射及当前 master face 唯一定义的
   `normal, t1, t2`，与正式 tether 求值路径一致；
6. 位移以各时间级自身 phase 0 为基准；场差只在精确共有相位
   `0, 0.25, 0.5, 0.75, 1` 计算；
7. 不执行平滑、滤波、最近索引替代、热点后选择或新参数拟合。

上述派生只用于 P5 时间离散比较，不改变模型、求解状态或先前接受的结果。
