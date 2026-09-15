---
document_id: PRL-MYO-LONG-DOUBLET-EXECUTION-V01
status: passed
date: 2026-09-14
scope: bounded_numerical_qualification_not_static_equilibrium
parent_Z1: blocked
---

# 长程双胞、实际步长裁切及静态性能执行记录

依用户“然后你继续任务”和[冻结合同](ventricle_myocardial_long_doublet_contract_v01.md)执行。当前切片已完成并消费；没有自动进入16胞动力学、异质性或噪声计算。此前原始数据、失败包和核心可执行文件保留。

## 真实模型与实施变化

END端向/SIDE侧邻各2胞，每胞194节点384三角面，全节点自由；无ECM、心内膜、腔压、夹持或周期载荷。皮质张力.160、bulk30、area.050、bending0；恒定方向骨架.060 diag(1,-.15,-.85)。保留独立黏附和正间隙屏障，无参考形状膜能。

本轮未改唯一SimuCell3D接触核心，沿用冻结的屏障动力学可执行文件。新增应用层完整快照折叠监测、执行/独立核验脚本，以及2/4/16胞静态计时探针和CMake独立目标。原核心与动力学二进制哈希由长程裁决核对。相邻共享边面法向余弦监测有2项回归测试，先缺实现失败，再实现后2/2通过；这不构成任意拓扑无折叠证明。

## 执行与裁决

| 范围 | 实际执行 | 裁决及边界 |
|---|---|---|
| 长程双胞 | END/SIDE × dt .02/.01，算法坐标0至5；4条 | 数值资格passed；总墙时438.472秒 |
| 实际自适应裁切 | END/SIDE，请求上限.20至坐标.8 | 各11个接受步，7次安全裁切；passed，非粗步长精度验证 |
| 静态性能 | 2/4/16胞各一次接触力计算 | profiling passed；无16胞状态推进，非统计缩放律 |
| 静态平衡 | 长程末态自由残力约.104，对照门.001 | failed：有限时域未收敛，不证明渐近不稳定 |
| 生物形态/父Z1 | 无参数标定及合格组织末态 | blocked |

粗档各253个完整状态，细档各501个；真实事件坐标0/1.25/2.5/3.75/5。全程体积误差<=0.333786%，最小三角角>=22.516179°；事件状态独立判内、三角穿越及非相邻自交未发现见证。共享边法向余弦最小0，未触发-.95门。步长减半末态位移差END0.051910%、SIDE0.053732%。这仅覆盖本次轨迹与检查范围，不宣称普遍不可穿透定理。

细档END每胞长轴约+6.3613%，SIDE约+12.2135%。这是恒定预应力下的形态重排/棱角变圆，不是周期缩短；包围盒长度、宽度、厚度可随棱角变圆同时增加而体积近似守恒。保持逐胞曲线，不用平均掩盖响应。

16胞静态CLI总耗时13.7353秒，其中几何安全检查1.4436秒，接触组装12.1500秒。一次性计时足以定位当前接触开销，但不能作为稳定统计性能结论。如果4000步保持此初态开销，仅两部分约15.1小时，这是外推而非实际运行记录。旧1800秒整片预算不足以按此速率完成；本轮没有优化、扩预算或放宽安全门。

## 命令、预算与证据

原始完整命令、退出码、资源与逐步账本见结果目录的execution_ledger.json、A/execution_ledger.json、P/verdict.json。正式科学调用为4+2条双胞轨迹和3次静态探针，全部CPU/exit0，无GPU。长程每例360秒/合计1440秒、2GiB资源门；附加阶段每例60秒/合计180秒。所有原始失败和冻结门保留。

主要入口：

- `python -B -X utf8 scripts/run_myo_long_doublet_v01.py`
- `python -B -X utf8 scripts/verify_myo_long_doublet_v01.py`
- `python -B -X utf8 scripts/run_myo_long_doublet_extensions_v01.py adaptive`
- `cmake --build b/z1m0a --config Release --target prl_myo_contact_scaling_probe_v01 -j 2`（TEMP/TMP均限定本项目新临时目录）
- `python -B -X utf8 scripts/run_myo_long_doublet_extensions_v01.py performance`
- `python -B -X utf8 scripts/render_myo_long_doublet_v01.py`
- `python -B -X utf8 scripts/render_myo_long_doublet_extensions_v01.py`
- `python -B -X utf8 scripts/package_myo_long_doublet_v01.py`

[总裁决](../results/ventricle_z1/z1_myo_long_doublet_v01_20260914/verdict.json)、[长程独立核验](../results/ventricle_z1/z1_myo_long_doublet_v01_20260914/long_verdict.json)、[实际裁切](../results/ventricle_z1/z1_myo_long_doublet_v01_20260914/A/verdict.json)、[静态性能](../results/ventricle_z1/z1_myo_long_doublet_v01_20260914/P/verdict.json)。

## 图像验收

交付15组PNG/SVG、5帧真实状态GIF，6张定量图采用统一风格并检查元数据。包含结构、逐胞形变、曲率、逐胞压力、接触牵引、残力、间距、网格角度、安全裁切和性能。接触牵引不是完整应力张量；算法松弛坐标不是生理时间。

首次渲染的间距图标签超出画布约0.5pt，风格检查拒绝；调整刻度后重绘通过，无改数值。人工查看压力图发现自动窄色域会夸大约1e-7的胞间差异，改为含零的压力色域后重绘，不改数据。代表图人工检查和结构/链接验证见[visual_qa.json](../results/ventricle_z1/z1_myo_long_doublet_v01_20260914/visual_qa.json)；live browser QA仍not_run。

## 不规则细胞文献与唯一下步

[文献及建议](../docs/myocardial_shape_variability_literature_v01.md)区分胞间形态差异、区域性界面结构、时间波动。优先引入有统计依据的体积/截面/端部错位和相容界面，再考虑区域力学及相关主动涨落。当前未生成随机几何或加入噪声，文献图形相似不算力学验证。

唯一下一执行建议：冻结接触计算性能优化切片，在不变力—能量、力矩、求积及防穿透门下优化候选筛选/最近面搜索，再评估可负担的双胞收敛与整片松弛；不得直接扩展高开销随机组织。

## 清理状态

用户批准删除的准确路径为 `E:\Temp-Projects\PRL\tmp\contact_barrier_v01_build`。只读检查仅有OWNERSHIP.md和空MSBuildTemp，无原始或唯一成果；但准确路径删除调用被执行工具在启动前以“blocked by policy”拒绝。因此状态blocked，目录未删除，未绕过。

本轮新建 `E:\Temp-Projects\PRL\tmp\myo_long_doublet_v01_build`，只含OWNERSHIP.md和空MSBuildTemp；唯一输出已在b/与results/保存。此路径未获删除批准，保留待确认。不删除任何旧目录或历史证据。
