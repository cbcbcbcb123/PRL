---
document_id: PRL-F6-S2-IDEALIZED-3D-EXECUTION-V01
status: failed
date: 2026-09-18
contract: project_control/ventricle_fem_idealized_3d_contract_v01.md
engineering_execution: failed
evidence_delivery: passed
biological_validation: not_run
---

# 三维结构建成；无载接口失败，保留并离线修正

## 模型和实际执行

真正三维z<=0半椭球壳，外半轴(1,1,1.5)，不是二维挤出或实测心室。
径向界面20/27、21/27、22/27、1，构造心内膜/ECM/心肌三域。
P2位移/P1连续压力四面体、有限变形NH，mu=1、kappa=1000未标定。
基底环全位移固定、外壁自由，计划内壁随动压力与仅心肌域的切平面分散主动张力。
主动结构张量A=(I-n0⊗n0)/2；不是原二维单环向纤维，也不是实测螺旋纤维。

M0/M1输入几何为1344/3960四面体，几何/面邻接/分层门passed。
相对解析腔体积误差6.259416%/2.822721%，满足预定8%/4%几何门；这不是力学收敛。
M0构造2169个位移节点、6507位移DOF、325压力DOF，共6832混合DOF。
压力/主动/总切线方向误差6.61785e-9 / 3.73433e-10 / 4.19953e-11通过；
这些小扰动导数检查不等于加载平衡。检查复用既有数值工具，其压力系数0.04不是额外平衡态。

只进行一次26.462148秒容器调用，固定本地镜像、1CPU/8GiB/禁网/0GPU。
M0无载SNES收敛理由2、0次Newton更新，自由残差1.23676685e-16。
随后的独立复核抛IndexError；按首失败停止，没有第二次容器/科学调用。
原定余13态（M0六个加载态、M1七态）全部not_run。

## 原因、修复和证据等级

新三维适配器遗漏了原二维代码已经使用的collapse映射flatten：
真实mixed_u_map形状(1,6507)，mixed_p_map为(1,325)，保存pressure为(1,325)。
独立三维读取器用一维单元索引访问第一维，出现`index 1 is out of bounds for axis 0 with size 1`。
不是已观察到的材料失稳、网格翻转或Docker故障。
无载0Newton未执行LU，MUMPS选项未用警告也不能作为MUMPS失败证据。

遵循cb-diagnose的实际载荷回放：保留原源代码与原失败，用同一原数组可复现同一异常；
先记录失败回归，再规范化生产映射，独立读取明确允许(N,)或(1,N)，其他形状拒绝。
增加混合映射一致性检查，没有修改力学方程、参数、积分规则或原门限。
修复后的读取器从未改写的原数组离线核验无载态passed：u=0、J=1，26项状态检查通过。
**修复后的生产适配器未在容器重执行；压力/主动/网格响应资格均not_run。**
原native verification/failure及53项调用文件保持；不把原failed改写为passed。

运行前76测试通过；真实布局回归修复后80通过，加显示不修改原网格测试后81通过。
这些测试包括合成力学、实际布局、现有二维回归，不是额外科学平衡。
首次测试命令误列不存在的文件，因此未收集；首次图件校验缺“不适用”颜色字段，因此未执行Notebook。
两项均在记录中保留；后续修正只涉及测试调用和图件描述，不改原数值证据。

## 图件与保全

使用cb-paper-figure-workflow及cb-plot-unified-style从原3D网格/u/p物理副本独立复算，
交付可执行Notebook、600dpi PNG、可编辑SVG并通过视觉验收。
剖开只移除显示侧，原计算对象是完整壳；实际1倍坐标。只有1个真实无载态，不伪造5帧。

结果包：`E:\Temp-Projects\PRL-results\ventricle_fem\f6s2_idealized_3d_v01_20260918`。
98文件，10,616,566 bytes，manifest直接覆盖97文件；SHA-256：
`991710ecfb62d72bca971f8254199f119518d8fe199312e1bcea7949645d3e42`。
1719父/祖先文件、50项无关修改及输入全部保持；代码仓约2.038GB，低于3GiB。
无删除、安装、拉取、外部归档、GPU、远端推送；临时目录tmp/f6s2_checks保留待另行精确审批清理。

[真实结构与无载结果](../../PRL-results/ventricle_fem/f6s2_idealized_3d_v01_20260918/index.html) ·
[原失败](../../PRL-results/ventricle_fem/f6s2_idealized_3d_v01_20260918/failure.json) ·
[接口回放](../../PRL-results/ventricle_fem/f6s2_idealized_3d_v01_20260918/interface_diagnosis.json) ·
[离线复核](../../PRL-results/ventricle_fem/f6s2_idealized_3d_v01_20260918/post_verification.json)。

## 唯一下一步（需确认）

有界续算余13态；先以修正适配器重新建立同一M0空间并核对精确DOF映射，
只读复用已保存M0无载向量，不重新求解该态。然后按原压力/主动/组合阶梯及M1次序执行。
仍首失败停止、单CPU/0GPU/不自动重跑，不扩大参数、门限或增加FSI/生长。
新的create-only续算包和合同在确认后冻结；当前原run入口继续拒绝重跑此包。
