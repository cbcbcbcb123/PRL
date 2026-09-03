---
execution_id: EXEC-PAPER2-M2A-DOCKER-RUNTIME-REPAIR-V01
decision_id: DEC-PAPER2-M2A-RUNTIME-RECOVERY-AUTONOMY-V01
status: completed
executed_at: 2026-09-03
next_gate: resume_m2a_preflight
---

# Paper 2 M2A Docker 运行时修复执行记录 v01

## Outcome

Docker Desktop Linux engine 已恢复，合同指定的 `dolfinx/dolfinx:v0.11.0`
CPU 容器已通过导入冒烟测试。M2A 可从原预检阶段继续。

## Reproduced failure

- Docker client `29.1.3` 可用，但 `desktop-linux` server pipe 不存在；
- 直接从当前 Codex 进程链启动 Docker Desktop 时，backend 在初始化服务阶段崩溃；
- 第一个确定错误为无法清理
  `C:\Users\chenb\AppData\Local\Docker\run\dockerInference`；
- 轮换该运行时目录后，启动推进到下一服务，但又在
  `C:\Users\chenb\AppData\Local\docker-secrets-engine\engine.sock`
  出现相同的 Windows error 1920；
- 两个对象均为零长度 Unix-socket reparse point，ACL 查询同样返回 error 1920；
- WSL `2.6.3.0`、kernel `6.6.87.2` 和 `docker-desktop` WSL2 分发本身存在。

## Minimal reversible repair

未删除、重置或覆盖 Docker 数据。以下故障运行时目录被改名保留：

- `C:\Users\chenb\AppData\Local\Docker\run.stale-20260903-1500`；
- `C:\Users\chenb\AppData\Local\docker-secrets-engine.stale-20260903-1502`；
- `C:\Users\chenb\AppData\Local\Docker\run.stale-20260903-1506-ai-disabled`；
- `C:\Users\chenb\AppData\Local\docker-secrets-engine.stale-20260903-1506-ai-disabled`。

Docker AI 可选模块由 `EnableDockerAI: true` 改为 `false`，避免本项目不需要的
AI/GPU 辅助进程；原设置文件 SHA256 为
`1D48CA1D5D0629A6315BEF740B2E97B0570E2A6E6B6B818D66F9CAA58F2B`，
修改后为
`0790887CABF9DAE1E62F1F373D1096E863879A85B064374C571FD7984E5F1C55`。

Docker Desktop 最终通过 Windows Explorer 桌面会话代理启动，避免直接继承当前
Codex 进程链。由于“关闭 Docker AI”与“桌面会话代理启动”在同一轮生效，当前证据
支持运行时 socket/启动上下文为故障域，但不把二者的独立贡献过度判定为唯一根因。

## Verification

- Docker client/server：`29.1.3 / 29.1.3`；
- Docker OS：Docker Desktop；kernel：`6.6.87.2-microsoft-standard-WSL2`；
- engine 资源：80 CPU，约 62.6 GiB memory；
- 镜像：`dolfinx/dolfinx:v0.11.0`；
- 镜像 ID：`sha256:2ae4bfbc0d9077268880faf04c72750528bee986c94ab223a2c159969bd56fa8`；
- CPU-only 容器导入：`dolfinx=0.11.0.post0`、`ufl=2026.1.0`、
  `petsc4py=3.25.1`；
- 冒烟容器正常退出；没有启动 GPU worker；没有修改容器、镜像或卷数据。

## Evidence boundary

本记录只证明批准的 M2A CPU 求解路径已恢复，不构成 M2A 数值结果、身份转换结论、
M2B 授权或旧 Figure 2 A1 再执行授权。
