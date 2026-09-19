# Docker 恢复 v01：已核查，等待精确路径授权

日期：2026-09-19。用户已要求“继续，修复Docker”。
本次诊断 `passed`，实际修复 `not_run`，运行时 `blocked`，原四工况仍 `not_run`。
依据 `cb-docker-windows-runtime` 与 `cb-diagnose`，不再用普通重启复现已知1920。
本页冻结一项供用户裁决的恢复措施，不自动复用9月17日隔离权限。

## 当前事实与候选机制

[18:41只读实机快照](evidence/docker_recovery_20260919_v01/preflight.json)：
原五个套接字仍为零字节 ReparsePoint，ACL读取1920；Linux Server=null、WSL Stopped。
日志仍指向18:06那次Ingest启动失败，本次0启动、0停止进程、0修复、0容器/求解/GPU。
现存6个Docker进程均属于那次失败及其错误报告窗口，不能据其存在认定引擎可用。

本机 Desktop/backend 二进制版本均为 `4.89.0.238018`。
`EnableDockerAI=false`、`EnableInference=false` 已存在，因此“不加核验就再次关闭AI”不是本机的新修复。
没有改设置，完整设置内容不上传，仅记录相关字段及文件哈希。

[Docker问题库 #531](https://github.com/docker/desktop-feedback/issues/531)有相同的1920和父目录隔离报告，
但它是用户问题报告，不是维护者确认的本机根因或成功保证。
[官方发布说明](https://docs.docker.com/desktop/release-notes/#4890)在4.89.0/4.90.0均提到遗留socket启动修复；
本机4.89.0依然复发，故不能只凭“有更新版本”承诺升级根治。本次不下载或升级。

直接故障是宿主runtime套接字处理失败；不把它归咎于FEM或材料。
异常关闭、文件系统/套接字生命周期或仍有残留进程等深层机制尚未在本机区分。
可证伪的本次恢复假设：结束确认的失败进程并隔离两个旧runtime根后，
一次干净启动可恢复API；若仍失败，停止该候选，不自动轮换目录或改WSL。

## 仅有两个拟隔离目标

完整机器可读冻结清单：
[frozen_manifest.json](evidence/docker_recovery_20260919_v01/frozen_manifest.json)。
清单 SHA-256：`9f281fabde61c7fa2f7a3d0fee90e92303f3297983fbbb58cce2806b68439cd7`。

| 源绝对路径 | 目标绝对路径 | 当前内容 |
|---|---|---|
| `C:\Users\chenb\AppData\Local\Docker\run` | `C:\Users\chenb\AppData\Local\Docker\run.quarantine-20260919-repair-v01` | 4个runtime套接字，报告逻辑大小0 bytes |
| `C:\Users\chenb\AppData\Local\docker-secrets-engine` | `C:\Users\chenb\AppData\Local\docker-secrets-engine.quarantine-20260919-repair-v01` | 1个runtime套接字，报告逻辑大小0 bytes |

两个根及其现存父链均不是目录链接，目标均不存在；子对象5个均为ReparsePoint，不读取或跟随。
0普通文件、0子目录；不存在可诚实计算的内容哈希，0 bytes元数据不能证明内容无价值。
这些路径不在PRL Git中；整目录同父重命名保留对象，不永久删除。旧隔离包原样保留。
这是一项可回退的临时恢复候选，不是已证明的长效修复；新源目录出现后不得直接覆盖回滚。

## 待授权的完整执行边界

1. 只对本次列出的Docker实例先使用一次[官方正常退出](https://docs.docker.com/reference/cli/docker/desktop/stop/)：
   `docker desktop stop --timeout 30`。若仍有残留，仅允许核验PID、路径、创建时间一致后，
   对清单中的 `22412/51316/8604/35180/33872/48576` 使用 `Stop-Process -Force`。
   已退出者跳过，PID复用、额外Docker实例或身份变化则停止，不按名称通配杀进程。
2. 重新核验冻结目录内容；只用 `System.IO.Directory.Move` 同父移动上表两目录。
   每项后验源消失、目标存在且对象元数据相符。新对象、源重新显露、目标已存在、
   任何部分失败或状态漂移即停；不额外循环隔离。
3. 仅正常启动现有 Docker Desktop 一次，隐藏窗口；最多180秒有界等待。
   只读检查本机API、WSL和当前合同固定镜像，不创建容器或执行FEM/JIT。
   失败不再启动；成功也只记运行时恢复，长期不复发仍未验证。

严禁：删除文件、改ACL、改设置、安装/更新/拉取、重启Windows、WSL shutdown/unregister、
挂载、GPU、动 `Docker\wsl`/VHDX/镜像/数据卷/其他旧隔离包。
Docker正常启停产生的自身runtime/log状态由应用管理；本次不手动修改它们。
不复制整个Docker数据目录，也不做未经批准的外部备份。

## 用户确认用语

`确认执行 Docker恢复20260919-v01：批准冻结清单中的6个Docker进程处置、2个精确目录的System.IO.Directory.Move隔离，以及一次启动和只读验收；不删除、不升级、不改设置、不触碰Docker\wsl或数据卷，不运行容器/FEM。`

上述确认后才进行实际操作。原科学四工况授权保留，环境恢复与科学验收分开。
