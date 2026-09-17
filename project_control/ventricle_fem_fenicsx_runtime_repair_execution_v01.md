---
document_id: PRL-FEM-FENICSX-RUNTIME-REPAIR-EXECUTION-V01
status: passed_host_runtime_recovery
executed_at: 2026-09-17
supersedes_current_blocker: project_control/ventricle_fem_fenicsx_runtime_preflight_blocker_v01.md
scientific_execution: not_run
containers_created: 0
fem_solves: 0
---

# F6-S0 G0｜Docker/FEniCSx 主机运行时隔离修复执行记录

## 裁决

Docker Desktop 主机运行时恢复为可用，本机固定 FEniCSx 镜像身份已核验。该结果只解除
`ventricle_fem_fenicsx_runtime_preflight_blocker_v01.md` 记录的 Windows AF_UNIX 运行时阻断，
不等于 F6-S0 的完整 G0 通过，更不等于 G1/G2 或任何科学资格通过。

- Docker Desktop：`4.89.0 (238018)`；
- Docker Engine：`29.7.2`，server `linux/x86_64`；
- WSL `docker-desktop`：`Running`，version 2；
- 本地镜像：`dolfinx/dolfinx:v0.11.0`；
- image ID：`sha256:2ae4bfbc0d9077268880faf04c72750528bee986c94ab223a2c159969bd56fa8`。

FEniCSx 容器导入、JIT、微型装配、G1被动圆环和G2主动张力均为 `not_run`。没有容器创建、
镜像拉取、安装、更新、GPU调用或FEM求解。

## 获准操作与结果

第一次获准隔离使用 `System.IO.Directory.Move`，把以下两个运行时目录移入可逆隔离位置：

- `C:\Users\chenb\AppData\Local\Docker\run`
  → `C:\Users\chenb\AppData\Local\Docker\run.quarantine-20260917-f6s0-v01`；
- `C:\Users\chenb\AppData\Local\docker-secrets-engine`
  → `C:\Users\chenb\AppData\Local\docker-secrets-engine.quarantine-20260917-f6s0-v01`。

第一次获准启动后，Docker越过 `sailor-ingest`，但原位置又显露出一个不同文件标识、时间更早的
`docker-secrets-engine` 目录，随后在其 `engine.sock` 上再次报 Windows error 1920。按路径授权边界
停止运行，重新盘点并取得第二批精确授权，没有把第一次授权扩展到新显露的对象。

第二次获准隔离把新运行时残留移到：

- `C:\Users\chenb\AppData\Local\Docker\run.quarantine-20260917-f6s0-v02`；
- `C:\Users\chenb\AppData\Local\docker-secrets-engine.quarantine-20260917-f6s0-v02`。

随后只启动一次 Docker。Engine API、WSL发行版和固定本地镜像检查全部成功；Docker在原运行时
位置重新生成当前有效socket。四个隔离目录全部保留，未执行永久删除。

## 安全边界复核

- `C:\Users\chenb\AppData\Local\Docker\wsl` 始终存在，未移动、删除或改写；
- 没有触碰镜像、volume、VHDX或无关用户目录；
- 没有拉取镜像、安装依赖、更新Docker、启用GPU或联网获取求解器；
- 没有创建容器，没有执行DOLFINx导入、FFCx JIT或科学计算；
- Docker当前保持运行，供下一次另行授权的G0容器资格使用；
- 四个隔离目录不是可自动清理缓存，删除须另列精确清单并重新取得授权。

## 下一步

按 `ventricle_fem_fenicsx_ring_active_contract_v01.md` 另行确认执行 F6-S0。首先只执行 G0：
固定image ID、`--pull=never`、单CPU、禁网、0 GPU，在受限容器中核验DOLFINx/PETSc/FFCx版本、
JIT和微型装配。G0失败即保全停止；G0通过后，G1/G2是否继续仍按有效合同和用户授权执行。
