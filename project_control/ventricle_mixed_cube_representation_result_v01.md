---
document_id: PRL-MIXED-CUBE-REPRESENTATION-RESULT-V01
date: 2026-09-19
status: failed
failure_phase: native_export_mapping_before_first_solve
native_container_invocations: 1
equilibrium_solves: 0
automatic_retries: 0
offline_export_fix: passed
fixed_native_assembly: not_run
original_ventricular_qualification: failed
---

# 八工况在求解前停止：P3导出方向错误已离线修正，科学对照未运行

执行用户明确批准的[八工况合同](ventricle_mixed_cube_representation_batch_v01.md)，
SHA-256 `9a13d99182bb003bf0f944d4b2df92cb3530f30cc3bfb17533b074fba4a3fb0d`，
[批准单独记录](ventricle_mixed_cube_representation_authorization_v01.md)，原合同不改写。
1个固定本地容器、单CPU/8GiB、禁网、只读根/项目、0GPU、0重跑。
实际容器15.93085秒，无OOM；**SNES调用0次，八个工况全部not_run**。
第一例P3/P2 cubic patch在独立节点映射检查失败后整批停止，没有越过前置检查。
原始failure.json因构造函数未返回而case=null；progress.json和保存网格明确定位第一例，不补写原记录。

## 原因与修正范围

新导出接口把原生P3单元局部DOF顺序直接当成统一参考节点顺序。
P3每条边有两个内部节点，原生全局DOF映射包含边方向翻转；P2每边只有一个内部节点，旧测试未覆盖这一差异。
这是本次接口实现错误，不是Docker失败、材料过硬或非线性求解不收敛。
[Basix 0.11.0官方说明](https://docs.fenicsproject.org/basix/v0.11.0/python/_autosummary/basix.finite_element.html#basix.finite_element.FiniteElement.base_transformations)
明确展示三阶Lagrange边方向反转需要交换两个DOF；实际保存网格提供本项目直接证据。

- 48个真实四面体中22个导出映射失配，最大坐标错配0.16666666666666696 L。
- 压力节点映射、体/面积分权重原本通过；定位到位移节点排序。
- 新`canonical_nodal_cells`通过仿射几何建立唯一坐标双射，仅重排**导出的索引**，不移动节点，不修改原生函数空间、全局状态、载荷或本构。
- 原生索引和逐单元排列同时导出；独立验证器另外检查坐标映射及排列关系，不调用导出器自证。
- 同一个真实网格离线回放后最大坐标差3.3306690738754696e−16，原1e−12映射门不变。

真实失败网格以11263-byte字节一致夹具保留，SHA-256
`40ef6fdd009342fab48690514624d62ea0fb1d38c2767bc8a48783b70ab60d65`。
既有85项宿主测试曾通过但没覆盖原生方向置换；补上真实夹具、双射/不变性、一般三次交叉项梯度、兼容解析场离线残差，以及重复/偏移/非有限/退化拒绝测试后，92项通过。
这里的解析场回放是接口回归测试，**不是本批求得的平衡态**。
修正后的原生表达式、装配、切线及非线性求解均未再运行，不能宣称完整P3资格已通过。

## 误差—成本状态

| 工况 | 网格n | 混合DOF（拓扑预估） | 求解误差/耗时/峰值内存 | 求解状态 |
|---|---:|---:|---|---|
| cubic patch P3/P2, κ1000 | 2 | 1154，原生导出核对一致 | null | not_run |
| 原MMS P2/P1 Q8, κ100 | 8 | 15468 | null | not_run |
| 原MMS P3/P1, κ100 | 2/4/8 | 1056/6716/47604 | null | not_run |
| 原MMS P3/P2, κ100 | 2/4/8 | 1154/7320/51788 | null | not_run |

不能填0误差/0求解耗时来冒充结果，也不能推断P3/P2是否优于P3/P1。
压力表示贡献仍unknown；原MMS最细H1误差43.65%、原心室局部体积偏差1.4496%仍failed。
此前四控制passed保持；原1%心室门未放宽，主动/生长/FSI未运行。

## 保全、图件与运行时

完整包在`E:\Temp-Projects\PRL-results\ventricle_fem\mixed_cube_representation_v01_20260919`，
[不可变索引](result_index/mixed_cube_representation_v01_20260919.json)。
817保护文件含50个既有改动保持；31份运行时源码在`sources_at_execution`保存且哈希不变。
运行结束时工作源码核验通过；之后明确修改导出接口，修正源码另存`offline_fix_sources`，不覆盖失败执行版本。
以前本地9份未跟踪评审文件未删、未纳入本次提交；不新建评审包或桌面ZIP。

图件只展示实际初始网格和每单元映射错配，明确标记0求解；无压力、变形或Newton状态可展示。
Notebook、数据/代码快照与PNG/SVG均保存在结果库并执行、目检、冻结。
首轮Notebook参数命名校验失败保留，补齐参数后通过；图数据与渲染未改变。
沿用160dpi探索规格，通用600dpi投稿校验failed照录，不冒充投稿终稿。
`.render_runtime`属本批绘图暂存，未获删除授权，保留。

首次Docker只读doctor因镜像查询15秒超时保守blocked；后台日志随后显示现有引擎由节能模式自行唤醒，
耗时16.413秒。再读固定镜像ID/info通过且运行容器为0，才发起本次容器。
没有调用Desktop启动、退出、修复、隔离、安装、更新或拉取；本次失败直接来自Python映射检查。
运行时初次blocked记录保留，不根据活跃socket的1920 ACL警告再次修复。

## 唯一下一步与权限

先验证修正后的原生P3映射/装配/切线，通过后才继续完全相同八工况。
**本批一个容器额度已用尽，即使8次求解均未消耗也不能自动再开容器。**
需用户另行批准一次同矩阵续行；新create-only结果包保留本次失败，1CPU/8GiB、1800秒、0GPU、0自动重跑，
不启动/修复Docker、不运行心室/主动/生长/FSI。未获批准前仅离线交付和普通main同步。

复核命令（不启动Docker）：

```powershell
$env:PYTHONPATH='E:\Temp-Projects\PRL\src'
$env:PYTHONDONTWRITEBYTECODE='1'
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'
F:\python\python.exe -B -X utf8 -m pytest -q -p no:cacheprovider tests/prl/test_nodal_export.py tests/prl/test_mixed_cube_representation.py tests/prl/test_mixed_cube.py tests/prl/test_mixed_cube_controls.py tests/prl/test_saved_segment.py tests/prl/test_positive_j.py tests/prl/test_ventricle_3d.py tests/prl/test_volume_projection.py
```

源码、必要记录和小型失败夹具同步Git；原始结果、图件、Notebook和缓存不进入Git。
没有删除、安装/升级、GPU、全局memory改写或DCM前向运行。
