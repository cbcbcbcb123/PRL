---
decision_id: DECISION-EFE-NODE1-N1-2-AUTHORIZATION-V01
status: approved
decider: human_final_reviewer
decided_at: 2026-08-19
related_plan: project_control/efe_node1_fast_trilayer_mechanics_contract_v01.md
related_acceptance: project_control/efe_node1_n1_1a_footprint_acceptance_decision_v01.md
---

# EFE Node 1 N1-2 人类执行授权

## Decision

人类终审在接受 N1-1A 后明确同意进行下一步骤。依照已批准的 Node 1
合同，本决定授权执行 `N1-2：周期稳态与数值收敛`。

## Frozen execution scope

1. 使用 `F150` 作为全局响应与周期计算的生产 ECM 横向足迹；
2. 连续运行完整心搏周期，直到相邻两周期关键波形归一化 `L2 <= 1e-3`；
3. 执行每周期 `16/32/64` 步时间收敛，检查积分统计量、相位和耗散；
4. 执行至少两档求解/耦合容差；
5. 执行 ECM 厚度方向 `4/6/8` 层并同步控制横向单元质量；
6. 执行 DCM 基线与约四倍表面面数的等效能量离散；必要时才追加第三档；
7. `F200` 只用于最终局部位移、应力和界面牵引热点复核；
8. 保留所有失败、未收敛和追加离散层级，不选择性丢弃敏感指标；
9. 形成可复算源数据、门限表和 N1-2 阶段科研审阅图。

## Frozen acceptance criteria

- 单工况继续满足 Node 1 合同中的 KKT、体积、几何、接触与正 `J` 硬门；
- 中—细时间步积分统计量差 `<= 2%`；
- 相位差变化 `<= 0.01` 周期；
- 耗散变化 `<= 5%`；
- 中—细空间网格细胞全局读数差 `<= 1%`；
- ECM/界面能量积分、95 分位应力和牵引差 `<= 10%`；
- 候选热点质心移动 `<= 0.1L`。

## Authorization boundary

本决定不授权 N1-3 载荷分解与参数筛选、N1-4 材料竞争、N1-5 Figure 2
定稿、Node 2、实验拟合、双向 FSI、远程 Git 或发布操作。N1-2 阶段图和
门限结果完成后必须返回人类终审。
