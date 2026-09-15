---
decision_id: DEC-PAPER2-MYOCARDIAL-DCM-RETIRE-FEM-ONLY-ARCHITECTURE-V01
status: approved_by_human
decider: human
decided_at: 2026-09-04
human_instruction: 心肌_DCM_从项目中完全去掉
supersedes_route: role_separated_hybrid_with_myocardial_DCM_comparator
accepted_prior_evidence: project_control/paper2_m2a_v07_supervisor_acceptance_and_model_architecture_human_gate_v01.md
next_plan: project_control/paper2_v08_myocardial_fem_only_architecture_migration_contract_v01.md
execution_authorized: v08_fem_only_active_architecture_migration_and_parity_only
---

# Paper 2 心肌 DCM 退役与 FEM-only 主动心肌架构决定 v01

## 1. 人类决定

从 Paper 2 当前生产架构、后续理论模型、数值实验、参数空间、论文图和器官级扩展中
完全去掉“心肌 DCM”。上一版“心肌 DCM 可作为机制 comparator”的建议不再成立。

从本决定起，唯一允许的生产角色为：

| 组织层 | 唯一模型角色 |
|---|---|
| 心内膜 | DCM / 离散细胞链 |
| 心肌 | 主动 FEM 连续体 |
| ECM / cardiac jelly | 黏弹 FEM 连续体 |
| 腔内流体 | 后续独立合同分层加入；当前不执行 |

## 2. 立即终止的路线

以下内容从活跃项目中退役，不再继续或迁移：

- 心肌 `DCM` 生产分支及其被动/主动缩放参数；
- DCM–FEM 心肌 identity、转换、重新标定或 identity retry；
- 心肌 DCM 端点、参数扫描、三维扩展与器官级 patch；
- 以“心肌 DCM 相对 FEM 的增量价值”为目标的 Figure 4；
- M2B 三维 identity 路线；
- 用 v06.1/v07 的差异反推新 FEM 参数以恢复 identity。

旧主线 v02 中涉及 DCM–FEM 心肌共同极限和心肌 DCM patch 的部分由本决定取代。

## 3. 历史证据处置

v01–v07 的合同、源码、测试、执行记录和结果包已构成带哈希的失败—诊断证据链。为保持
科研可审计性，本阶段不物理删除、不移动、不覆盖这些文件；它们统一标记为
`retired_historical_evidence`，固定在提交
`34908b299475ee81d9cb2fccca0b191e22fa965a` 所代表的历史状态。

保留不等于继续使用：

- 新生产包不得导入、调用或配置旧心肌 DCM 分支；
- 新模拟不得生成 `myocardium=DCM` 端点；
- 新论文主线不得把 v01–v07 作为新架构的验证数据；
- 历史结论只允许用于解释为什么路线被终止，不用于支持新模型物理真实性。

若未来要求从磁盘和 Git 工作树物理删除历史证据，必须另列精确路径、可恢复性和远端
影响后获得单独确认；本决定不授权该不可恢复清理。

## 4. 新科学主线

生产问题改为：主动心肌 FEM 如何通过黏弹 ECM，把时空异质的主动应变传递给离散心内膜
DCM，并在之后与腔内流体载荷耦合。

粗粒化问题仍可研究，但只能在 FEM 家族内部比较：

- cell-resolved / meso-resolved active FEM；
- homogenized active FEM；
- 不同主动场相关长度、各向异性和 ECM 松弛尺度。

不得重新引入心肌 DCM 作为比较臂。候选物理命题相应收窄为“主动场粗粒化与界面传递
是否不对易”，而不是“DCM 与 FEM 是否等价”。

## 5. v08 授权

批准 v08 只完成新的 FEM-only 主动心肌生产命名空间、旧路线隔离、FEM→FEM 数值等价
迁移门和主线 v03 文档。v08 不授权新物理参数扫描、三维、整心房或流体。

允许使用已验证的本地 `dolfinx/dolfinx:v0.11.0` CPU 容器、禁网、单进程完成迁移
等价检查；不得启动 GPU worker。

## 6. 完成标准

只有同时满足以下条件，才能宣称“心肌 DCM 已从活跃项目完全去掉”：

1. 新生产 API 不存在 `representation` 选择，也不能接受 `myocardium=DCM`；
2. 新生产源码不包含心肌 DCM 网络、缩放或校准实现；
3. 新生产运行时不导入旧 `paper2_m2` 双表示模块；
4. 新端点键和结果 schema 不再含心肌表示轴或 identity 指标；
5. 新 FEM-only 实现通过对旧 FEM 臂的严格迁移等价门；
6. 主线 v03、CURRENT_STATUS 和自动监督只指向新架构；
7. 旧 v01–v07 被清楚标记为历史退役证据，且没有被删除或改写。
