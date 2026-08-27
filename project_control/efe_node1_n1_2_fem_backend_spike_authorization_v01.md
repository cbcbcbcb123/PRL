---
decision_id: DECISION-EFE-NODE1-N1-2-FENICSX-SPIKE-AUTHORIZATION-V01
status: approved
decider: human_final_reviewer
decided_at: 2026-08-19
related_plan: project_control/efe_node1_n1_2_fem_backend_spike_proposal_v01.md
related_inspection: null
memory_target: null
---

# EFE Node 1 N1-2 FEniCSx/PETSc 后端试验授权

## Decision

人类终审指示“继续”，批准执行
`project_control/efe_node1_n1_2_fem_backend_spike_proposal_v01.md`，并明确
批准拉取官方 FEniCSx/DOLFINx Docker 镜像所需的项目文件夹外 Docker
存储写入。

## Authorized scope

只执行提案中的 M0、均匀仿射 patch 和 `F150/D0/E0/a=0.20` 等价性与
速度基准。项目代码、适配器、结果和日志只写入 `E:/Temp-Projects/PRL`。

## Boundary

本决定不自动批准将 FEniCSx 定为生产后端，不授权正式
`D1/E1/32-step` N1-2 收敛矩阵，也不授权 FEBio plugin、N1-3、Node 2、
实验拟合、双向 FSI、远程 Git 或发布。
