---
document_id: PRL-FEM-FENICSX-CONTOUR-PASSIVE-EXECUTION-V01
status: failed
executed_at: 2026-09-17
contract: project_control/ventricle_fem_fenicsx_contour_passive_contract_v01.md
result: results/ventricle_fem/f6s1_contour_passive_v01_20260917
geometry_gate: failed
passive_mechanics: not_run
active_mechanics: not_run
equilibrium_solves: 0
automatic_retries: 0
---

# F6-S1：已接回外轮廓，薄层网格质量门失败

本阶段未求解压力响应，不能用网格图声称已有真实轮廓形变、应力或心跳。

## 已完成及停止原因

读取已保全的72 hpf Fish 4、z=39外轮廓；保持原始源哈希、归一化尺度和
20/27、21/27、22/27、1的构造内腔/层界比例。三层全为同一未标定NH材料的计划，
没有真实内腔、壁厚、纤维或分层材料标定。

只读几何试验表明直接把圆环网格拉到轮廓会产生约5度单元。固定本地镜像中已有
Gmsh 4.15.2，故未安装软件，改用共形非结构三角形。正式唯一容器生成1042顶点、
1828单元的粗网格；细网格仅在内存中四分构造，粗网格门失败后未保存或求解它。

| 检查 | 结果 | 裁决 |
|---|---:|---|
| 对源mask IoU | 99.5882% | passed，要求≥98% |
| 对原始轮廓采样Hausdorff | 1.66974微米 | passed，要求≤2微米 |
| 正面积、闭合边、共享层界、标签及分层面积 | 全部通过 | passed |
| 最小单元角 | 12.8687度 | failed，要求≥20度 |
| 未通过角度门的单元 | 45/1828，约2.46% | failed |

45个尖瘦单元全部位于两个薄构造层：心内膜20/366、ECM25/354；心肌0/1108，
心肌区最小角32.969度。分布支持优先检查薄层宽度与边界节点间距/局部剖分的适配，
但尚未证明一种具体修复必然有效。失败发生在力学之前，不支持材料或求解器失稳判断。

## 执行、证据与图件

一次只读模块探针、一次正式科学容器；正式调用9.131秒，0平衡求解、0自动重试。
固定镜像身份及全部容器资源检查passed：1 CPU、8 GiB、禁网、只读根和项目、0 GPU。
218个父包文件哈希保持，F5原局部J失败和F6-S0圆环通过均未重写。

共用FEniCSx装配器增加显式几何输入接口；材料、压力势和原力学阈值不改。
独立审计关闭非圆几何不适用的圆柱解析比较，其余原残量/局部J/网格响应门保留。
153个相关开发测试及27个子测试passed；没有把单元测试通过当成真实轮廓力学通过。

图件由正式保存网格生成：结构、未通过单元位置、分层角度CDF三面板。
图中红色表示网格质量未通过，不是应力。依照绘图技能，保留逐字节数据副本、
可编辑Notebook、实际使用的代码/样式快照、600 dpi PNG和可编辑SVG；执行、样式和目检分别验收。
绘图调版没有重生成网格或求解。失败原包及正式调用源快照不变。

见[结果页](../results/ventricle_fem/f6s1_contour_passive_v01_20260917/index.html)、
[几何门](../results/ventricle_fem/f6s1_contour_passive_v01_20260917/raw/M0_geometry_preflight.json)、
[原失败](../results/ventricle_fem/f6s1_contour_passive_v01_20260917/failure.json)。

## 唯一下一步

新有界切片F6-S1-M：只改善薄构造层的边界节点间距与质量剖分，保持同一128段多边形、
层界、材料、载荷、20度与1%局部J门不变。均匀四分会保持三角形角度，不能修复本次尖角；
应优先让局部边长与薄层法向宽度匹配并做受约束的质量优化。
先通过几何门后再进行原10态被动压力资格，不预先恢复主动收缩。

本次单次调用已结束，不自动第二次尝试；下一次几何生成/求解须确认新的有界范围。
无拉取、安装、删除、GPU、DCM或自动推送；阶段按现行决定直接本地提交main。

## 交付验收及临时保留

最终包41个清单项SHA-256复核一致；独立重读F6-S0的82项门仍passed，0重新求解。
本阶段约7.71 MB，工作区约2,001,197,182 bytes（1.864 GiB），低于2 GiB目标和3 GiB硬限。
驾驶舱严格验证21个HTML链接、312个证据路径，缺失0。

本次新建的临时目录候选为
`E:\Temp-Projects\PRL\results\ventricle_fem\f6s1_contour_passive_v01_20260917\figure_runtime`。
它仅含本次Notebook运行配置/缓存和所有权说明，3文件/81,857 bytes，无原始数据或唯一图件；
当前按原规则保留，未执行删除。如后续清理需先重新检查Git/链接属性并明确确认该精确目录。
正式Notebook、数据副本、PNG/SVG均在独立figures版本包，不能随此缓存清理。
