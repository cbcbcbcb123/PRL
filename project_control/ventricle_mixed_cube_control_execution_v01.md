---
document_id: PRL-MIXED-CUBE-CONTROL-EXECUTION-V01
date: 2026-09-19
status: blocked
scientific_cases: not_run
native_container_invocations: 0
equilibrium_solves: 0
automatic_retries: 0
---

# 四工况代码就绪；运行时预检阻断

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
