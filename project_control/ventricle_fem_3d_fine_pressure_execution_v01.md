---
document_id: PRL-F6-S2-D1-3D-FINE-PRESSURE-EXECUTION-V01
status: failed
date: 2026-09-18
contract: project_control/ventricle_fem_3d_fine_pressure_contract_v01.md
nonlinear_equilibrium: passed
fine_zero: passed
fine_pressure_acceptance: failed
evidence_delivery: passed
---

# 同压力粗细网格诊断：整体响应接近，基底局部门仍失败

## 实际执行

只新增已有M1的zero和pressure_1两次SNES，0主动张力；M0原失败数据逐字节保留，无重算。
半椭球、三层同mu=1/kappa=1000、P2/P1、六阶积分、全固定基底/外壁自由与随动压力不变。
生产求解器、协议及原独立力学验证文件与父包交付快照SHA-256一致，未复制新内核。
M1输入几何原件复制，3960四面体、6083个位移节点、19119混合DOF。

一次44.488051秒固定本地容器，1CPU/8GiB/禁网/0GPU；无OOM、自动重跑、Docker修复或拉取。
无载0次Newton、J=1、passed；p/mu=0.01、Ta=0经3次Newton平衡，
自由残差1.39655e-16、MUMPS passed，独立自由残差1.58117e-16、场量最大差1.24e-15。
首压力仍仅local_volume检查failed，按约定停止；新增尝试2、接受1（仅zero）。
压力Newton 0/1/2/3、各态初始/全混合向量/u/p/F/J/应力/残差及原失败完整保存。

## 对照结果

| 指标 | M0（原始保留） | M1（本次） |
|---|---:|---:|
| 四面体数 | 1344 | 3960 |
| 腔体积相对各自无载增加 | 1.089525% | 1.105919% |
| 最大位移/L | 0.004041971 | 0.004139627 |
| 采样max abs(J-1) | 1.522743% | 1.449560% |
| 积分点max abs(J-1) | 1.314813% | 1.255314% |
| 超过原1%门的单元 | 96/1344 | 120/3960 |
| 非基底相邻区域max abs(J-1) | 0.529615% | 0.459731% |
| 压力态裁决 | failed | failed |

腔体积响应绝对差0.000163936（0.016394个百分点），相对差1.482348%，
通过预先固定的0.002绝对且5%相对参考门；不能替代两网格均失败的局部体积门。
最大局部失真仅改善4.805976%，没有解决问题。
超限单元全部有固定基底顶点；M1心内膜72、ECM48、心肌0。
不同网格单元数/体积不同，不能直接用120>96断言整体变差。

## 科学解释与边界

确认：弱平衡收敛和整体响应接近，并不保证局部近不可压质量；
问题在本次细网格仍集中于基底邻近区域，不是未收敛、MUMPS或已修正接口故障。
两网格的曲面近似也变化，不是同边界几何纯h细化；不能分离几何、夹持、压力空间贡献，
也不能称渐近/热点收敛。当前证据不支持简单继续同类加密就能解决局部门。
没有放宽1%门、提高kappa、降低压力或松开夹持，也没有继续主动、生长、FSI。
两次科学状态只对应加载级，没有生理时间；三层/几何/参数未实验标定。

## 交付验收

运行前后91项测试passed；主机与容器verify报告在计算前冻结容差内一致。
cb-diagnose用于单变量失败诊断，不擅自实施物理修复；
cb-paper-figure-workflow/cb-plot-unified-style用于实际数据副本、Notebook、600dpi PNG/SVG及目检。
图为两套真实参考结构和同压力态的应力/J，1倍形变、共用轴限/色标、无平滑。
原始两载荷级及Newton状态均留存；不伪造五个平衡态。

结果包E:\Temp-Projects\PRL-results\ventricle_fem\f6s2d1_3d_fine_pressure_v01_20260918：
128文件41,493,908 bytes（约39.57MiB），127项manifest；SHA-256：
7bd712585b82c5ca4689f56292536a918b060ace2acf9051790ecba9a790e0f4。
1940父/祖先文件、75调用文件、50项无关修改及执行源码哈希保持；代码仓低于3GiB。
本地main精确提交，不推送；无删除、安装、拉取、GPU或工作区外未授权输出。
tmp/f6s2d1_checks检查缓存保留，删除仍须另行列单审批，不处理任何旧目录。

[结构与场量对照](../../PRL-results/ventricle_fem/f6s2d1_3d_fine_pressure_v01_20260918/index.html) ·
[独立粗细诊断](../../PRL-results/ventricle_fem/f6s2d1_3d_fine_pressure_v01_20260918/mesh_diagnostic.json) ·
[原始失败](../../PRL-results/ventricle_fem/f6s2d1_3d_fine_pressure_v01_20260918/failure.json)。
只读复核：`python -B -X utf8 -m prl verify fem-idealized-3d --fine-first-pressure`，预期failed。
相应run为create-only拒绝重跑；两态已用尽，本记录不授权新加载。

## 唯一下一步：先形成体积约束离散资格方案（待确认）

保留材料、载荷和基底，先审查并冻结更局部的体积约束离散单变量方案。
包括三维压力表示所需阶次、自由度/稳定性、近不可压锁死及小基准门；
不能直接把二维通过的压力空间当作三维资格。方案审查不启动新的FEM。
小基准/同载壳执行另按明确合同确认，再决定是否需要基底约束对照。
