---
document_id: PRL-F6-S2-D2B-EXECUTION-V01
status: failed
date: 2026-09-18
candidate: one_consumed_no_retry
FEM: not_run
new_FEM_solves: 0
---

# 同边界非结构化候选：几何保持，质量门未通过

依据[原合同](ventricle_fem_3d_unstructured_comparison_contract_v01.md)和
[本次采纳及固定选项](ventricle_fem_3d_unstructured_adoption_v01.md)，仅运行一个候选。
本轮是网格工程对照，不是心肌收缩、发育、细胞随机性或FSI结果。

## 结果

| 指标 | 原M1 | Gmsh候选U1 |
|---|---:|---:|
| 四面体 | 3960 | 2611 |
| 混合P2/P1预计自由度 | 19119 | 13483 |
| q=3r/R的5%分位 | 0.2382721 | 0.2488568 |
| q中位数 | 0.3272215 | 0.3505279 |
| 最差q | 0.2220354 | 0.0292329 |
| 最小内二面角 | 6.637914° | 6.811118° |
| 薄层基底区q的5%分位 | 0.2267100 | 0.2397507 |

边界和两个层界的三角形逐坐标集合、材料邻接完全一致；拓扑、正体积、
无重复/悬空顶点、资源门通过。内腔体积相对差0，各层最大相对差2.22e-16。
薄层基底的q05及最小角度非下降门通过，但全体q05仅提高**4.442271%**，
未达预设5%（目标0.2501857210），因此质量资格 **failed**。
此外少数ECM单元最差q降至0.02923；不能仅凭中位数或Gmsh日志判定优质。
DOF减少29.48%，不是同DOF严格拓扑因果对照，也未进行渐近收敛验证。

## 首失败与只读恢复

Gmsh 4.15.2成功完成一次Delaunay生成和一次显式默认优化，保存了
fixed_surfaces.msh、before_optimization.msh、candidate.msh及全部选项/日志。
随后输出适配器按原节点标签查找外壁，因Gmsh自动重编号触发KeyError(726)。
原调用与failure.json保持failed，未重新启动容器，未进行任何FEM。

使用已安装meshio 5.3.5读取该唯一candidate.msh，按**精确坐标**建立面片映射，
不舍入、不近邻粘合、不补点、不修改网格。offline/保存完整派生网格和独立质量核验。
上述质量门失败来自该只读复核，不是当时已成功执行的在线门。
生产适配器已改为精确坐标映射，新增重编号/坐标漂移/重复坐标回归；
修订后完整容器路径 **not_run**，不以单元测试代替再次实跑证明。

原三维M0/M1首压力失败1.5227%/1.4496%保持。U1无zero/pressure状态，
所以不能比较U1的J、应力或变形；图中只有实际参考网格及质量统计，没有伪造场量。

## 交付与复算

- [结果入口和真实结构/质量图](../../PRL-results/ventricle_fem/f6s2d2b_unstructured_v01_20260918/index.html)
- [独立网格比较](../../PRL-results/ventricle_fem/f6s2d2b_unstructured_v01_20260918/offline/mesh_comparison.json)
- [原失败](../../PRL-results/ventricle_fem/f6s2d2b_unstructured_v01_20260918/failure.json)
- [离线复核与交付审计](../../PRL-results/ventricle_fem/f6s2d2b_unstructured_v01_20260918/delivery_audit.json)
- [源代码](../src/prl/fem/unstructured_geometry.py)、[独立体网格核验](../src/prl/verification/mesh_equivalence.py)

只读复核：`python -B -X utf8 -m prl verify fem-unstructured-3d`。
运行命令`python -B -X utf8 -m prl run fem-unstructured-3d`已经消耗，create-only禁止重复。
132项测试、21项子测试passed；包括原力学/协议/CLI、接口重编号和首失败停机。
每个图版本保存物理复制数据、方法、Notebook、质量公式和样式，导出PNG/SVG并目检。
首次图件校验发现STYLE_SOURCE声明缺失，已在未冻结版本补全并重新执行；
目检发现图注与横轴标题邻接过近，增加显式底部空间后重新导出，无数据改动。

一容器7.934秒（容器内2.118秒）、单CPU、8GiB、禁网、0GPU、0自动重跑。
原输入、失败、执行源快照及全部受保护祖先不改写；确切保护计数及哈希见交付审计。
无关50项工作区修改保持。无删除、迁移、安装、拉取、Docker修复或推送。
任务临时检查目录`E:\Temp-Projects\PRL\tmp\f6s2d2b_checks`保留，未经确认不删除。

## 裁决与唯一下一步

停止本候选，不将4.44%改判为5%，也不为了passed继续调网格选项。
这是固定边界、固定尺寸规则下的一个反例，不证明所有非结构化网格无效，
更不证明“规则网格”就是原压力误差的根因。

建议下一步先形成**近不可压三维混合离散的小基准资格方案**：审查稳定性、
局部体积控制和夹持热点，再选定可验证的位移/压力空间；不是直接把二维DG方案
搬到三维。方案确认后再做有界基准，未授权新的求解、修改材料/边界或继续生长/FSI。
