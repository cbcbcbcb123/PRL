# Docker恢复20260919-v01：引擎与固定镜像已恢复

执行日期：2026-09-19。仅宿主运行时恢复 `passed`；长期不复发 `unknown`；科学执行 `not_run`。
本页补充[冻结修复清单](docker_recovery_20260919_v01.md)，不改写其“当时待批准”文本。
用户随后明确[批准该精确范围](evidence/docker_recovery_20260919_v01/authorization.md)，
清单SHA-256仍为 `9f281fabde61c7fa2f7a3d0fee90e92303f3297983fbbb58cce2806b68439cd7`。

## 实际操作与保留的失败

1. 两个根、五个子对象、六个进程的路径/创建时间和保护文件哈希重新核验通过。
2. 一次 `docker desktop stop --timeout 30` 卡住；10:50:43 UTC时已至少57秒未返回，
   并未按声明期限退出。中断本任务自己的执行会话后，其CLI进程46884/5752均消失，
   六个原Docker实例身份及两个源目录不变，移动/启动均为0。
   [超时失败记录](evidence/docker_recovery_20260919_v01/graceful_stop_interruption.json)保留。
3. 使用用户已批准的残留进程处置，不重新发起正常退出：核验后仅显式停止主进程22412，
   其余列出的子进程随之退出；未扩大到新PID或其他程序。
4. 10:53:30 UTC，严格按清单以 `System.IO.Directory.Move` 隔离两个根；
   每次均确认源消失、隔离目录存在、原4+1对象元数据相符。
5. 10:53:31 UTC只启动一次现有Desktop（隐藏窗口，PID7788）。没有第二次启动、安装、
   更新、拉取、删除或设置/权限修改。

完整逐项事件：[execution.jsonl](evidence/docker_recovery_20260919_v01/execution.jsonl)。
执行脚本有create-only注册和已消耗拒绝保护；续行仅针对同一次退出命令卡住后的获准fallback，
不是另一次修复重跑。下次正常退出命令应加执行器层硬超时，不能只相信Docker自身的timeout参数。

## 冻结验收项

| 项目 | 结果 |
|---|---|
| 本机Linux Engine API | passed，Docker Engine 29.7.2，Desktop 4.89.0 (238018) |
| `docker info` | passed，Linux/x86_64；307个现有容器，运行中0，镜像10 |
| WSL docker-desktop | Running，version 2 |
| 当前合同固定本地镜像 | passed，`dolfinx/dolfinx:v0.11.0`，ID与当前运行器IMAGE完全一致 |
| Desktop/backend二进制及settings-store.json | 前后SHA-256一致 |
| 两个旧runtime根 | 按精确授权移动，5个原对象元数据保持；未永久删除 |
| 原Docker\wsl与旧隔离目录 | 仍存在，未手动移动/删除/改写 |
| 容器/JIT/FEM/GPU | 本次均0，未执行科学批次 |

证据：[API与镜像](evidence/docker_recovery_20260919_v01/post_start_readiness.json)、
[info](evidence/docker_recovery_20260919_v01/engine_info.json)、
[后验元数据及保护哈希](evidence/docker_recovery_20260919_v01/postcheck.json)。
[最终核验与证据哈希](evidence/docker_recovery_20260919_v01/verification.json)还验证了重复执行拒绝、
208个受保护文件和导航链接；逐项执行原始JSONL按字节保留，不被Git换行规范化。
没有全量读取VHDX或不可访问socket，不能把元数据核验冒充原始内容校验。
Docker正常启动会自行创建runtime/log并打开其数据盘；“未触碰”指没有直接操作其数据盘或内容。

## 重要：ACL警告仍保留，不误判健康引擎

原始doctor输出仍为 `preflight_status=blocked`，但其中API和镜像均 `passed`。
原因：18:53刚生成、正在工作的5个新套接字，ACL读取同样返回1920；
新日志已出现Ingest listening、Secrets Engine ready，且引擎API正常。
这些是真实反例：**仅ACL错误1920不能证明套接字已损坏或Docker不可用**。
之前的直接故障依据是启动日志中的处理失败与Engine API不可用共同出现，而不是仅元数据。

本次按冻结合同的API/info/WSL/镜像验收项接受“运行时恢复”，同时原样保留保守脚本的blocked。
未修改全局技能、未放宽科学误差门，也没有把一次恢复宣称为永久修复。
不要因活跃套接字的ACL警告再停止健康引擎、隔离目录或启动修复循环。
下一次启动前仍核对当前API、真实新日志及历史；新故障需要新的精确裁决。

## 下一步

Docker保持运行。下一科学工作为原已批准四工况控制批次，仍0/4求解，配置/阈值不改。
本次授权明确不运行容器/FEM，因此到只读镜像验收结束；不把引擎恢复当作FEniCSx或科学通过。
隔离目录保留在清单所列位置，不能自动清理或直接覆盖回滚。
