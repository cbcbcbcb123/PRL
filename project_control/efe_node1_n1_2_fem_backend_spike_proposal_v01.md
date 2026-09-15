---
proposal_id: PROPOSAL-EFE-NODE1-N1-2-FENICSX-BACKEND-SPIKE-V01
status: approved
proposed_at: 2026-08-19
approved_at: 2026-08-19
approval: project_control/efe_node1_n1_2_fem_backend_spike_authorization_v01.md
parent_authorization: project_control/efe_node1_n1_2_authorization_decision_v01.md
---

# EFE Node 1 N1-2 FEniCSx/PETSc 后端受控试验提案

## Trigger

当前参考后端在 `D0/E0/F150` 的 16 步暖启动中，每次稀疏精化约需
`68–124 s`；到 `a=0.10` 时连续三次精化的最新 KKT 仍为
`5.38e-5`，高于合同门 `1e-5`。正式 `D1/E1/32-step` 的节点、单元和
材料点数量更高，继续沿用 Python 单元循环和有限差分彩色切线不具备合理的
成本—证据比。

## Proposed architecture

保留现有 DCM、材料点注册、双界面身份、精确细胞体积约束和全部科学方程，
只替换 ECM FEM 的残量、Jacobian 和非线性线性代数后端：

`DCM / material-interface registry -> PETSc adapter -> FEniCSx ECM`

- 主后端候选：稳定版 `FEniCSx 0.11 + PETSc SNES`；
- 现有 Python 后端：继续作为 D0/E0 小网格参考与回归基准；
- FEBio：后续作为独立软组织 FEM 交叉验证候选，不在本 spike 中实现紧耦合。

## Authorized work requested

若人类批准，只允许：

1. 拉取官方 FEniCSx/DOLFINx Docker 镜像；
2. 在项目目录内增加最小 ECM backend adapter、容器运行入口和测试；
3. 复算 M0 零态、均匀仿射 patch、N1-1A `F150/D0/E0/a=0.20` 峰值；
4. 比较总能、ECM 内力、界面合力、位移、`min J`、KKT 与墙钟时间；
5. 只有物理一致性门全部通过且实测加速达到 `>=5x`，才提交是否迁移
   N1-2 正式计算的人类决定。

## Spike acceptance gates

- 零态内力与位移在机器精度范围；
- 均匀仿射 patch 的能量和合力相对差 `<=1e-8`；
- 峰值全局缩短相对差 `<=1%`；
- ECM 总能相对差 `<=1%`；
- 界面合力和 95 分位牵引相对差 `<=5%`；
- `min J` 绝对差 `<=0.01`；
- 两后端均满足原 KKT、体积和几何门；
- 相同硬件、相同状态的端到端墙钟加速 `>=5x`。

任一物理一致性门失败即停止，不得以速度优势替代正确性。速度小于 `5x` 时
保留为负结果，不迁移正式 N1-2。

## Environment and external-write boundary

当前 Windows Python 环境没有 `dolfinx/petsc4py/mpi4py/ufl/basix`；Docker
与 WSL2 可用，但本机尚无 DOLFINx 镜像。拉取容器镜像会在项目文件夹外写入
Docker 数据，因此必须由人类明确批准。项目代码、适配器、结果和日志仍只写在
`E:/Temp-Projects/PRL` 内。

## Out of scope

- 不改变 DCM/ECM 科学方程、本构参数或已接受 N1-1A 结果；
- 不执行正式 D1/E1/32-step N1-2 收敛矩阵；
- 不实现 FEBio C++ plugin；
- 不启动 N1-3、Node 2、实验拟合、双向 FSI 或发布；
- 不在 spike 通过前废弃参考后端。

## Human decision requested

是否批准本受控 FEniCSx/PETSc backend spike，并允许拉取官方 Docker 镜像？
