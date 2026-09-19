---
document_id: PRL-MIXED-CUBE-CONTROL-EXECUTION-V01
date: 2026-09-19
status: blocked
scientific_cases: not_run
native_container_invocations: 0
equilibrium_solves: 0
automatic_retries: 0
runtime_start_attempts: 1
runtime_start_status: failed
---

# 四工况代码就绪；一次正常启动失败，科学运行仍阻断

当前结论：用户批准的一次Docker正常启动已经执行，因Ingest套接字访问异常失败。
四工况仍0容器/0求解，原计算授权未消耗；正常启动权限已用完，不能再启动或修复。
本页早先的“尚未启动”段落为先前预检历史，本次更新见末尾。

用户已确认[完整四工况](ventricle_mixed_cube_control_batch_v01.md)。本次在同一求解器增加
可表示的非均匀体积patch与等体积剪切解析场；不改本构、材料、P2/P1、积分、正J保护或原误差门。
独立NumPy梯度/Hessian/体力、非均匀面力与固定面反力、配置隔离与停止政策测试通过，
共65项宿主测试passed；原生实现验证与四工况科学判断均not_run，不能以宿主测试替代。

## 真实阻断点

执行统一入口时，第一次只读`docker version`返回客户端信息但Server=null，
`dockerDesktopLinuxEngine`管道不存在。返回发生在结果目录创建和容器启动之前。
只读复核：无Docker Desktop/backend/vmmemWSL进程，com.docker.service为Stopped/Manual。
日志在2026-09-19 10:02（UTC+8）记录idle模式、graceful shutdown及引擎停止；
尚不能确定稍后Desktop进程退出的原因，也不能把现有零字节ReparsePoint套接字直接判成损坏。
没有证据允许沿用9月17日的旧目录隔离授权。本次未启动或修复Docker。

证据：[预检与只读诊断](evidence/mixed_cube_controls_v01_preflight/preflight.json)、
[65项测试原始输出](evidence/mixed_cube_controls_v01_preflight/host_tests.txt)。

0新容器、0平衡求解、0GPU、0自动重跑；结果目录仍不存在。
四工况计算授权尚未消耗。已询问是否允许只启动现有Docker Desktop一次；
若用户允许且预检通过，再执行原四工况，不扩大或重新申请科学矩阵。
若启动失败则停止，不移动/删除运行时路径，不安装/更新/拉取，不改变Docker设置。

## 已保存与未完成

工程：控制场及统一run/verify入口已实现，65项宿主测试passed。
原v03完整配置读回一致；668个保护文件及50项既有无关改动哈希通过，驾驶舱链接通过。
完整性记录见[只读验收](evidence/mixed_cube_controls_v01_preflight/integrity.json)。
科学：原八工况与原心室1%门failed不变；新四工况及其结果图not_run。
没有用解析场或插值图伪装成新平衡结果。现有保存态诊断图仍可查看。
前一阶段已普通推送main至`a887f3ce19314b4257e5602605066eb933948e9f`，远端回读一致，既有标签不变。
本次代码与blocked记录随后普通推送至`a468bc11385d3e330665114381581b284698055f`并回读一致，
详见[发布快照核验](evidence/mixed_cube_controls_v01_preflight/publication_readback.json)。发布passed不代表四工况已运行。

## 续行授权：仅正常启动Docker一次（2026-09-19）

用户对“允许仅启动现有Docker Desktop一次，不修复、不安装或拉取；启动成功后继续原四工况”
明确回复“同意，继续”。该授权仅覆盖一次现有程序启动，成功后续用原四工况权限；失败即停。
启动前再次只读核查：无Desktop/backend进程，docker-desktop/WSL2为Stopped；
run中的4个套接字及secrets engine.sock的ACL读取均返回error1920。
这新增了套接字访问异常证据，但尚未取得本次启动后的错误日志；不以旧授权移动任何目录。
本次将仅正常启动一次核验，不重启循环、不修复/删除/隔离、不改设置、不拉取/安装/更新。

## 本次启动裁决：failed，四工况继续not_run

2026-09-19 18:06:25（UTC+8）仅调用一次`Start-Process -WindowStyle Hidden`，
目标是原已安装的`C:\Program Files\Docker\Docker\Docker Desktop.exe`，启动PID 22412。
没有第二次启动、手动启动backend、安装、更新、拉取、套接字隔离/删除或权限修改。

本次新日志10:06:28 UTC记录初始化失败，10:06:59 UTC明确记录`backend crashed`：

```text
starting services: initializing Ingest server:
listening on unix://C:/Users/chenb/AppData/Local/Docker/run/sailor-ingest.sock:
rename .../sailor-ingest.sock .../sailor-ingest.sock.stale:
The file cannot be accessed by the system.
```

结合启动前五个套接字ACL读取error1920，可确认与旧记录相同类型的宿主套接字访问故障；
这是本次Docker启动失败的直接原因，不是FEniCSx、材料、网格或收敛失败。
为什么套接字在关闭后反复不可访问，仍unknown；不能据此擅自改ACL、Windows、WSL或Docker设置。
终末只读`docker version`仍Server=null、Linux引擎管道缺失。
错误报告UI及部分backend进程仍可见；没有自行终止它们，更不能把进程存在当引擎就绪。

[启动/错误/完整性证据](evidence/mixed_cube_controls_v01_startup/startup.json)保存三条精确日志的行号与哈希。
`backend_failure.log`是原样三行轻量摘录，与本次摘要一起同步；完整Docker日志未复制进项目或上传。
本轮无FEM、JIT、GPU；未生成伪装成结果的结构/变形图。旧图与旧失败均保持。
668个保护文件（含50项旧改动）、9项控制源码/测试哈希及原四工况配置复核passed；
之前65项宿主测试仍是宿主实现检查，不是本次原生验收。本轮没有改动科学代码。

下一步需要单独裁决运行环境恢复方式。重复隔离旧套接字未构成长效修复，本次不再自动轮换目录。
可另行审议受控Docker修复或替代运行环境；两者都不在本次“一次正常启动”授权内。
运行环境就绪后才继续原四工况，不重新扩张科学矩阵，不修改原阈值。

## 用户提醒后的历史交叉核对

全局2026-09-17修复记忆与项目内[实际修复执行记录](ventricle_fem_fenicsx_runtime_repair_execution_v01.md)一致：
当时按两次精确授权隔离`Docker/run`和`docker-secrets-engine`，第二次后正常启动成功，
固定FEniCSx镜像通过只读核验；没有动`Docker/wsl`、VHDX、镜像和数据卷。
记忆已明确error1920必须停止无效启动，且受控修复后再次复发时不要循环目录轮换。
本轮虽未超出用户批准的一次正常启动，但启动前ACL已报1920；更有效的执行顺序本应直接报告
已命中历史故障签名并转入恢复方案裁决，而非再把正常启动当作排查未开机的方法。
后续同签名执行只读阻断，不沿用旧路径授权、不盲目启动，不把暂时恢复当成长效修复。
