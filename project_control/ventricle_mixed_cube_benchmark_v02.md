---
document_id: PRL-MIXED-CUBE-BENCHMARK-V02
date: 2026-09-19
status: failed
native_interface_retest: passed
nonzero_patch_qualification: passed
field_qualification: failed
actual_SNES_calls: 6
valid_terminal_equilibria: 5
remaining_execution_authority: none
new_FEM_authorization: user_confirmed_same_eight_case_v02_20260919
authority: user replied 同意，记忆 to one v02 eight-case rerun request
automatic_retries: 0
maximum_container_invocations: 1
maximum_SNES_calls: 8
---

# 同八工况v02：一次有界复验

用户最新回复“同意，记忆”，承接上一答复所请：允许修订版v02同八工况再运行一次，
保持原门限、单CPU、0GPU、无自动重跑；同时将v01教训写入指定Codex记忆更新目录。
本记录只激活[原合同B](ventricle_volume_qualification_adoption_v01.md)的同一矩阵，
不重写[v01失败记录](ventricle_mixed_cube_benchmark_execution_v01.md)，不扩展新物理工况。

- 2个非零patch及n=2/4/8 × κ=100/1000六MMS，所有方程/参数/门限逐字段与v01配置核对。
- 使用已提交的网格绑定零体力及逐表达式诊断候选修订，先表达式/独立装配/切线预检；通过才求解。
- 一次新容器，固定原镜像，单CPU/8GiB/0GPU/禁网，1800秒、保全预留120秒，最多8次SNES/每次30 Newton。
- patch失败或接口/映射/安全错误停止全批；patch通过后普通MMS数值精度失败按原合同继续其他预登记独立例。
- 无自动重试、安装、拉取、Docker修复、删除、心室重跑、薄层、主动、生长、FSI或推送。
- 独立结果根沿用前次提案冻结名称`E:\Temp-Projects\PRL-results\ventricle_fem\mixed_cube_benchmark_v02_20260918`；
  后缀是提案标识，实际执行日期为2026-09-19。create-only，不覆盖v01或任何现有包。
- 运行入口`python -B -X utf8 -m prl run fem-mixed-cube --batch v02`；默认v01入口仍拒绝重复运行。
- v01完整81文件列入保护，连同原208保护文件与50旧改动核验；不改原科学失败或专家原件。
- 按批准的探索交付保留全部数值/状态/配置/日志/源码，以及一页实际结构及裁决图，不制作投稿终稿。

当前执行结果尚未产生；后续本页追加实测结果，不把预检或宿主通过提前写为科学通过。

## 实际执行与独立复核（2026-09-19）

上述“尚未产生”是启动前记录；本节取代其当前状态，不追改原运行源码快照。
一次容器64.0257秒，单CPU/0GPU/禁网，实际6次SNES调用、5个有效终态、第6例安全失败，
后两例not_run。没有超时/OOM、重跑、安装、拉取、Docker修复、删除或推送。

两个非零patch完整passed，F/J/P/body原生表达式的坐标单元hash均为16933917893659141078。
旧接口症状未复现；v01原日志仍缺key，不把成功复验夸成直接重建旧故障。
六例已尝试工况的表达式/独立装配/切线预检均通过；五个终态方程/映射核验通过。

### κ=100：收敛趋势通过，精度资格failed

| 最细n=8指标 | 实测 | 原预注册门 |
|---|---:|---:|
| 位移L2相对误差 | 4.323879% | ≤2% |
| 位移H1半范数相对误差 | 43.648528% | ≤15% |
| 压力L2相对误差 | 2.073301% | ≤15% |
| J误差RMS | 0.156182% | ≤0.1% |

n=2/4/8误差单调下降，末段实测阶u L2/H1/p L2为4.1937/2.8197/2.1111，均达阶次门；
但位移及J绝对精度门未达。n=8自由残差约3.97e−15，仍不能替代场精度。
因此三个κ=100平衡态的工程一致性passed，与整个序列精度failed必须分开。

### κ=1000：粗网格第1个Newton步出现负J，停止依赖链

生产积分点min J=+0.02389913036；额外采样min J=−0.17637238547，6个单元检出负J，
最差参考坐标(0.5,0.5,0.5)。残差1.56432→1.09496下降，但最大节点位移已约0.205L。
安全监测器抛出异常，PETSc包装为error101；不是表达式接口又失败，也不宣称该状态是平衡解。
迭代0为最后已保存有效态；无效迭代1及failure_state均保全。κ=1000的n=4/8不运行。
原summary该组收敛not_run只表示没有完成三网格误差序列，不掩盖n=2实际安全failed。

这个对照证明：**只检查生产积分点或残差下降，可能漏掉P2场在其他位置的负Jacobian。**
它不证明全域单射、inf-sup失稳或固定载荷锁死；κ变化也改变了制造压力/体力/牵引。
不得去掉额外点检查或以放宽门限继续。小基准尚未合格，不进入薄层/原心室主动或生长。

### 保存与交付

[一页结构与定量诊断](../../PRL-results/ventricle_fem/mixed_cube_benchmark_v02_20260918/index.html) ·
[八工况完整表及复算](../../PRL-results/ventricle_fem/mixed_cube_benchmark_v02_20260918/README.md) ·
[分层裁决](../../PRL-results/ventricle_fem/mixed_cube_benchmark_v02_20260918/delivery_analysis.json)。

五个终态及24个监测状态已独立读回；离线分析及全部派生数组重算逐值一致。
运行前47项宿主检查passed，新增采样盲区/映射回归后49项passed；合成夹具初次参数选错已记录并修正，
没有改动生产门限或方程。统一风格发现对数残差跨16个数量级的默认次刻度为空，
只修显示定位器及J显示上限；原失败记录保留。160dpi探索布局/目检passed，投稿600dpi检查failed照录。

21份实际执行源码、5个终态、24个监测状态及所有失败证据保全。289个保护文件（含v01完整81文件）
与50项既有无关修改哈希保持；数值代码在原生运行后未修改，仅追加离线诊断、绘图和测试。
外部包145文件、16,593,908 bytes；manifest记录144项载荷，SHA-256：
`c59044955f3609509f8b8c61d620384ae800f9e2cebfa469d005cd61a9aaedda`。
结果不进Git，按长期授权仅本地main阶段提交。

用户要求的Codex记忆更新已写入：
`C:\Users\chenb\.codex\memories\extensions\ad_hoc\notes\20260919-001353-prl-fenicsx-expression-gate.md`。
区分v01候选原因、v02原生复验、误差资格、安全采样和一次容器权限，不授予未来运行。

## 唯一下一步（尚未授权）

先制定一个有界“试探步接受前正J保护＋同基准精度复验”的修订批次，再请用户一次确认。
保留原材料、P2/P1、精确解和精度门，不用更换心室形状掩盖基准失败。
正J步长保护只能处理本次安全失效，不承诺解决κ=100精度不足；后者仍需独立细化/误差机制验证。
本次一次容器权限已消耗，不能因为还差两个未运行工况而继续启动新容器。
