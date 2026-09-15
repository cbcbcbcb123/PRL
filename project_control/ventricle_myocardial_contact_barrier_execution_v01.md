---
status: passed
date: 2026-09-14
stage: Z1-MYO-CONTACT-BARRIER-V01
parent_Z1: blocked
---

# 正间隙排斥修订：双胞短程验证通过

依用户“同意，按照上述建议，开始继续修订”和[冻结合同](ventricle_myocardial_contact_barrier_contract_v01.md)，本轮在唯一SimuCell3D核心增加显式启用的正间隙面排斥势及三角面距离保护，采用新探针与新动力学目标。没有更改原胞内材料或恢复参考形状膜能。16胞整片未重跑。

## 实际构成

END端对端、SIDE侧邻，每例2个194节点/384面闭合心肌细胞，初始正间隙.070，全自由边界。皮质.160、体积模量30、面积模量.050、弯曲0，恒定方向骨架预应力.060；无周期收缩。黏附ka=.04、捕获距离.35不变，另加rho=.14、kr=.16的TriMem启发归一化屏障。rho尚未生物标定，不等于真实膜厚。

核心接触仍为对称表面求积、最近目标面唯一归属及完整面积导数。步进安全使用顶点—面、边—边、边穿面的三角距离；对不同细胞和同胞非共享节点面，按2*vmax*dt<=.8*dmin约束整个线性步的可能相对运动，而非只检查端点。三角高度限制独立保护退化，不改变胞内材料或加入参考边长弹簧。共享节点相邻面的普遍折叠排除尚未证明；未引入WCA高度能或换网格拓扑。

## 结果

| 项目 | 状态 | 证据范围 |
|---|---|---|
| 21次静态/几何调用 | passed | 近端排斥、远端黏附、远场零、独立黏附开关、力/矩守恒、能量差分、求积细化 |
| 旧失败网格回归 | passed | 新面检查分别拒绝旧END/SIDE穿透末态 |
| 4条完整双胞轨迹 | passed | END/SIDE × dt上限.02/.01，算法坐标0至1 |
| 停止恢复试验 | passed | 第38步、坐标.38停止，39个完整状态及768面拓扑均可读取 |
| 16胞性能优化及静态平衡 | not_run | 不继承双胞通过；本轮未授权整片重跑 |
| 生物学/父Z1 | blocked | 无参数与时间标定，无合格组织平衡态 |

四条正式轨迹共约117秒CPU单线程，峰值工作集均低于8MB。粗档52步/53个完整状态，细档100步/101个完整状态，额外事件拆步确保0/.25/.5/.75/1全部为实际求解状态。每个接受步都保存并flush节点，拓扑写出即flush。强制进程崩溃/系统掉电时的原子快照恢复不在本次通过范围。

最小面间距：END细档.0580452、SIDE细档.0699749；四例全程最小.0580123。独立五事件状态的胞内包含点、胞间穿面及非相邻自交见证均为0；每步保存坐标重算的相对位移/旧最短距离最大.234961，小于.8界限。四条轨迹未触发步长裁切；主动裁切的距离界限通过几何自测试，但更激进真实轨迹仍not_run。

全程体积误差<=.30154%、最小角>=28.7085度。步长减半末态位移L2差END .135185%、SIDE .147612%。能量差分最大相对误差4.78341e-6（四个平移/面积变化方向，不代表所有非光滑最近特征切换）。保存坐标重算对偶面积误差<=4.44e-16，做功/阻尼代数残差<=4.45e-16。

细档逐胞长轴变化：END两胞均+1.6934%，SIDE两胞均+3.0472%；这是当前恒定骨架和接触下的短程重排，**不是周期缩短**。末态最大自由节点力约.1972/.1983，远高于旧组织平衡门.001；不得称为平衡态。

## 测试、追溯与交付

- 编译：`cmake --build b/z1m0a --config Release --target prl_myo_contact_barrier_probe_v01 prl_myo_contact_barrier_relaxation_v01 -j 2`，exit0。TEMP/TMP限定项目内tmp/contact_barrier_v01_build；该目录保留OWNERSHIP，未删除。
- 执行：`python -B -X utf8 scripts/run_myo_contact_barrier_v01.py static`、`... dynamics`，均exit0；每次实际原生命令/退出码/耗时在结果ledger。
- 独立核验：`python -B -X utf8 scripts/verify_myo_contact_barrier_v01.py`，完成四条轨迹后的verdict_final passed。
- 行为测试：`python -B -X utf8 tests/test_myo_contact_positive_gap_v01.py` 2/2；`python -B -X utf8 tests/test_myo_sheet_contact_repair_v02.py` 3/3。前者先用旧实际输出得到预期失败+0.0683374，再验证新实际输出排斥；后者为历史证据回归，不冒充新核心全量测试。
- 一次离线核验误在第四条轨迹结束前启动，三例账本被标为不完整failed。原D/verdict.json保留不动，D/interim_verification_note.md解释原因；修正核验器为执行完成后才裁决，最终报告独立命名D/verdict_final.json。没有重跑轨迹或更改门限。
- 原Q探针v03和原动力学v01可执行文件与旧冻结SHA256一致。核心源有授权修订，不能再声称工作区核心与旧哈希相同；project_control/evidence/contact_barrier_v01_previous_core.cpp.txt为修订前读取文本的规范化快照，**非旧文件字节级备份**，不编译为第二内核。
- [总裁决](../results/ventricle_z1/z1_myo_contact_barrier_v01_20260914/verdict.json)、[完整独立复核](../results/ventricle_z1/z1_myo_contact_barrier_v01_20260914/D/verdict_final.json)、[图文页](../results/ventricle_z1/z1_myo_contact_barrier_v01_20260914/index.html)、[图像验收](../results/ventricle_z1/z1_myo_contact_barrier_v01_20260914/visual_qa.json)。11组PNG/SVG和5帧GIF，算法坐标明确非生理时间；压力为逐胞标量，接触牵引不是完整应力张量。

## 唯一下一步

冻结“长期双胞接触/形态稳定性与整片扩展前性能资格”切片：确认更长松弛、相邻面折叠门禁和真实主动步长裁切行为，并测量/优化扩展所需的接触候选筛选开销。上述资格及新整片合同获批后，再执行16胞静态维持。本轮短程passed不覆盖这一阶段。
