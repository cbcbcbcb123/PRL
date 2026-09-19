---
document_id: PRL-MIXED-CUBE-POSITIVE-J-V03
date: 2026-09-19
status: failed
guard_native_and_independent_verification: passed
field_qualification: failed
remaining_execution_authority: none
authority: user replied 同意，继续 to positive-J trial-step repair and separate accuracy diagnosis
new_FEM_authorization: user_confirmed_positive_J_same_eight_case_v03_20260919
maximum_container_invocations: 1
maximum_SNES_calls: 8
automatic_retries: 0
---

# 接受前正J保护及同基准复验

本批承接[v02失败](ventricle_mixed_cube_benchmark_v02.md)及用户最新确认。
只改变立方体基准的Newton候选步准入，不修改本构、μ/κ、网格、积分、精确场、载荷、
P2/P1、初值、收敛容差、30次Newton上限或原场精度门；不修改原心室求解器。

## 固定范围

- 同一2个非零patch及n=2/4/8 × κ=100/1000六个MMS；从零初值，各一次SNES。
- 一次固定镜像容器，1CPU/8GiB/0GPU/禁网，1800秒（末120秒停止保全）；0自动重跑。
- 既有运行时先只读检查；不安装、拉取、更新、Docker修复、删除或推送。
- create-only结果根：`E:\Temp-Projects\PRL-results\ventricle_fem\mixed_cube_benchmark_v03_20260919`。
  沿用已批准外部结果库；预估256MiB+64MiB停止保全+10GiB磁盘余量，代码仓3GiB门保持。
- 全部v01/v02证据、原心室失败、专家原件及50项旧改动保留并核验哈希。
- patch或接口/映射/有效状态安全错误停止整批；普通MMS精度/收敛失败保全后可继续
  原矩阵独立例。不新增n=16、初值延拓、参数扫描、薄层、心室、主动、生长或FSI。

## 接受前保护的算法与可证伪检查

PETSc的`setLineSearchPreCheck`可在线性求解后、回溯前调整方向；更新符号为X−λY。
在原生产积分点与原额外56点，由原生UFL的F表达式分别求当前F和方向增量D。
对每个空间采样点，J(t)=det(F+tD)为三次多项式。通过行列式多线性计算幂系数c0..c3，
区间t∈[0,α]上的Bernstein系数为：

`[c0, c0+αc1/3, c0+2αc1/3+α²c2/3, c0+αc1+α²c2+α³c3]`。

四个系数均大于1e−12才接受该方向尺度；否则从α=1逐次减半，最多20次。
该裕量是浮点候选保护，严于原J>0门，不是放宽原门。找不到安全段、当前态非法或非有限则停止，
不使用零步伪造成功。整段判据避免“起终点皆正，中间经过负J”的情况；保守拒绝可能发生。
缩放整条混合方向后交回原PETSc BT残差回溯（λ≤1），不替代原接受态监测与独立终态验证。
空间仍为采样检查，**不证明单元内处处正J或全局单射**。

先做解析系数/区间反例/无效初态/减半上限回归，再用v02保存的实际失效段回放。
原生运行记录每次precheck前的X、Y、尺度、系数界及接受态；离线验证不得导入生产保护判据，
独立重建F并用三次多项式的驻点检查整个候选区间，同时核对接受更新确在被保护方向段内。
这两个原生绑定/独立读回门不通过，不声称保护修复通过。

## 精度诊断（不追加求解）

分别记录原8工况裁决；与v02已有5终态比较场量，不能假定算法修复改善离散误差。
在同一保存网格上插值解析u*/p*，用原独立高阶积分计算其L2/H1/J误差，与实际解并列。
插值不是平衡解，也不是最佳逼近误差下界；不能从一个误差比值直接断言inf-sup或锁死。
不因n=8失败临时增加网格，不把κ依赖的制造载荷解释为固定载荷材料试验。

交付原始状态/失败/日志/源码、一个实际结构及诊断PNG/SVG页（已采纳160dpi探索例外）、
独立核验、分层结论。更新导航并本地main阶段提交；不更新全局记忆，除非另获用户要求。

## 接口依据

- [PETSc precheck语义](https://petsc.org/main/manualpages/SNES/SNESLineSearchSetPreCheck/)
- [petsc4py回调源码](https://raw.githubusercontent.com/petsc/petsc/v3.24.0/src/binding/petsc4py/src/petsc4py/PETSc/petscsnes.pxi)
- [PETSc BT实现](https://petsc.org/main/src/snes/linesearch/impls/bt/linesearchbt.c.html)

在线文档只指导适配，实际接口以本地固定镜像的版本/原生回调核验为准。

## 启动前检查

新增保护模块之前，3项回归因模块不存在失败；实现后54项针对性宿主检查通过。
v02真实失效段（最后有效迭代0→无效迭代1）只读回放：原整段终点min J=−0.17637238547，
保护选α=0.5，Bernstein下界0.23874133156；独立驻点检查给相同区间最小值，
多项式额外点校验差8.88e−16。此回放不是新的平衡解，也不声称还原v02未保存的原始Newton方向。
原生回调及完整求解仍需本次唯一容器验证，不能提前标记passed。

## 实际执行及裁决

以上为启动前登记；本节记录一次执行结果，不改写运行时源码快照。
固定镜像72.0377秒，PETSc 3.25.1/DOLFINx 0.11.0.post0，1CPU/8GiB/0GPU/禁网。
6次SNES尝试、5个有效平衡态；κ=1000 n=2保护耗尽，n=4/8 not_run。无重跑、超时或OOM。

### 保护实现passed，但高κ平衡failed

原生回调保存32个候选X/Y，31个获准并成为接受步，其中14次缩短方向；第32个拒绝。
独立实现不调用生产Bernstein判据，而在每个空间采样点拟合det(F+sD)并检查全部内部驻点。
31条获准区间均正，实际接受步均在对应区间；拒绝前当前向量与最后接受态逐值相同。
37个初始/接受状态全部读回，原生产积分点及额外点J均正；空间采样不是全域保证。

高κ粗网格共初始0+14个接受步，最后min J=1.61661221766e−7、
最大节点位移0.280163L、残差0.41464179237。下一候选α=2^−20仍有路径J=−2.31773023302e−8，
独立验证21个预登记尺度均无法通过，故按20次上限停止。不增加上限、不接受负J。
PETSc error101来自precheck有意拒绝，不是旧表达式接口错误。
该近退化状态没有平衡资格，不能解释为心肌柔软或生理变形。

### 精度诊断：不能由安全保护解决

两个非零patch再次passed。κ=100 n=2/4/8的全部指标与v02逐值相同，
最细u L2/H1/J RMS仍为4.323879%/43.648528%/0.156182%，原2%/15%/0.1%门failed不变。
同n=8网格的解析场节点插值相应误差为0.196674%/2.378501%/0.005284%。
这排除了“仅仅靠步长保护即可修好场精度”，并表明空间表示误差不是唯一问题；
不能直接证明锁死、inf-sup或本构失效。插值非平衡，压力插值误差4.769877%反而大于FEM的2.073301%。

### 交付与边界

[结构与诊断页](../../PRL-results/ventricle_fem/mixed_cube_benchmark_v03_20260919/index.html) ·
[完整八工况报告](../../PRL-results/ventricle_fem/mixed_cube_benchmark_v03_20260919/README.md) ·
[路径核验](../../PRL-results/ventricle_fem/mixed_cube_benchmark_v03_20260919/path_readback.json)。

54项宿主测试passed；24份原生执行源码、全部原始状态/候选/失败、独立分析和可重绘PNG/SVG保存。
统一风格按已采纳160dpi探索例外交付，布局/目检passed，投稿600dpi检查failed照录；无数据删点或门限放宽。
434保护文件（含全部v01/v02包）及50旧改动不变。无删除/安装/拉取/GPU/远端推送。
本地main阶段提交；没有新的全局记忆写入。原心室1%门failed未改变，三维主动/生长/FSI未执行。

唯一下一步建议：从已有状态分离制造载荷积分与混合压力约束的误差放大，
再预注册必要的独立网格或混合形式对照；不继续盲目增加减半次数。
本次一次容器权限已消耗，不能自动续跑剩余两例或加密n=16。

封存：外部包205文件、17568141 bytes，manifest含204项载荷；SHA-256：
`084a675f13501added2e056f5bc3cca125a2298f09d290240282fc2b570b77b0`。
离线分析/独立路径核验/终态核验JSON与全部派生数组重算逐值一致；执行后未更改原生数值源码。
