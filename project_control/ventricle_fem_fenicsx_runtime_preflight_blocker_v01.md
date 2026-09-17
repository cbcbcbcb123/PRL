---
document_id: PRL-FEM-FENICSX-RUNTIME-PREFLIGHT-BLOCKER-V01
status: blocked
checked_at: 2026-09-17
scientific_execution: not_run
containers_created: 0
fem_solves: 0
---

# F6-S0 G0｜Docker/FEniCSx 运行时预检阻断

用户明确允许启动 Docker Desktop，并仅检查和使用本机已有的
`dolfinx/dolfinx:v0.11.0` CPU镜像；禁止联网下载、安装和GPU。Docker Desktop进程成功启动，
但Linux引擎没有建立API，因而没有执行镜像检查、容器创建、DOLFINx导入、JIT或FEM求解。

宿主日志记录的首要错误为：

```text
starting services: initializing Ingest server:
listening on unix://C:/Users/chenb/AppData/Local/Docker/run/sailor-ingest.sock:
rename .../sailor-ingest.sock .../sailor-ingest.sock.stale:
The file cannot be accessed by the system.
```

随后backend停止所有本地engine并报告unexpected error。`docker version`只返回client，server
不可达；WSL列表中的`docker-desktop`为Stopped。现场只读检查发现：

| 路径 | 字节 | 属性 | 最后写入 |
|---|---:|---|---|
| `C:\Users\chenb\AppData\Local\Docker\run\sailor-ingest.sock` | 0 | Archive, ReparsePoint | 2026-09-09 21:55:07 |
| `C:\Users\chenb\AppData\Local\Docker\run\sailor-ingest.sock.stale` | 0 | Archive, ReparsePoint | 2026-09-08 09:36:11 |

它们位于项目外，且当前授权不允许移动或删除。因此本轮严格停止：0容器、0镜像变更、0结果目录、
0科学求解。该状态是宿主运行时`blocked`，不是FEniCSx数值失败。

若用户授权最小修复，必须先结束本轮Docker Desktop/backend进程，再对上述两个精确路径执行
另行批准的操作；不得清理整个`run`目录，不得恢复出厂设置、更新Docker、拉取镜像或修改其他
用户目录。修复后首先重新启动Docker并只读核验本地tag及实际image ID；若镜像不存在或漂移，
停止并报告，不联网获取。

历史记录显示该项目曾使用固定image ID
`sha256:2ae4bfbc0d9077268880faf04c72750528bee986c94ab223a2c159969bd56fa8`，但它只是历史证据，
不能替代本轮当前核验。
