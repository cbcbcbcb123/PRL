---
document_id: PRL-F6-S2-R-IDEALIZED-3D-EXECUTION-V01
status: failed
date: 2026-09-18
contract: project_control/ventricle_fem_idealized_3d_resume_contract_v01.md
native_interface_validation: passed
nonlinear_equilibrium: passed
loaded_state_acceptance: failed
evidence_delivery: passed
biological_validation: not_run
---

# F6-S2-R：原生接口通过，首压力局部体积门失败

## 模型及本次范围

仍为真正三维半椭球三层壳，外半轴(1,1,1.5)、界面20/27、21/27、22/27、1。
P2位移/P1连续压力四面体，有限变形NH，三层同mu=1、kappa=1000且未标定。
基底环全位移固定、外壁自由，内壁随动压力；主动张量与原合同一致但未到收缩分支。
不是实验心室，没有生理时间、流体或生长。

逐字节复用两套原输入几何；生产构造/solve/monitor与独立力学函数AST、几何及运行时哈希保持。
同一M0空间所有网格/层/边界/积分/DOF一致；两张混合映射只规范化已知行维度。
原M0无载混合向量不变，重新装配/求值与原数据一致，原生接口门passed；0次额外无载SNES。
旧F6-S2原接口失败包不改写，本包是新的续算证据。

## 实际结果

仅一次31.453212秒固定本地镜像容器，1CPU/8GiB/禁网/0GPU，无重跑、无OOM。
仅新增M0的pressure_1：p/mu=0.01、Ta=0。3次Newton，收敛理由2、自由残差1.690593e-16；
MUMPS状态passed，icntl14读回100。生产/独立F、J、应力误差均在1.33e-15内。

| 指标 | 结果 | 原门及裁决 |
|---|---:|---|
| 腔体积相对无载变化 | +1.089525% | 已计算，不是接受状态 |
| 最大位移/L | 0.004041971 | 真实1倍形变 |
| 积分点max abs(J-1) | 1.314813% | 也超过1% |
| 积分点与额外56点max abs(J-1) | 1.522743% | 1%门failed |
| 最小J | 0.98477257 | 正Jacobian passed |
| 独立自由力残差 | 1.9551e-16 | passed |
| 压力弱残差 | 1.8071e-18 | passed；不能替代逐点门 |

25项状态检查仅local_volume失败。首失败停止：新增尝试1、接受0、原无载复用1；
M0余5态及M1全部7态共12态not_run，主动加载、网格响应、生长、FSI和生物学验证均not_run。
保留压力态混合向量/u/p/F/J/应力、初态、Newton 0/1/2/3四个实际状态和原失败日志。

## 只读定位及未确认点

按cb-diagnose从保存数组独立重算，不追加FEM或修改物理实现。
96/1344单元超过1%门，全部是具有固定基底顶点的单元；
心内膜48个、ECM48个，心肌0个。非基底相邻960个单元的最大偏差0.529615%。
最差单元144、心内膜域、J=0.98477257；这说明失真集中于基底邻近第一圈，
并不声称最差采样点位于z=0约束面本身。

体积加权平均J-1为5.769975e-6；额外点上max abs(p_material/kappa)=1.7221e-5，
但max abs(J-1-p_material/kappa)=0.01522748。
确认：弱平衡及连续P1压力矩已满足，局部体积条件未满足；不是接口、未收敛或MUMPS故障。
基底约束、粗网格和压力空间各自贡献尚未分离，不能凭本次结果断言单一根因。
不提高kappa、不降低载荷规避、不放宽原1%门，也不直接切换三维不连续压力空间。

## 交付与保全

运行前85测试、交付后87测试通过；主机/容器独立报告按计算前合同容差一致。
cb-paper-figure-workflow及cb-plot-unified-style生成物理数据副本、可执行Notebook、600dpi PNG和SVG。
图中A是原结构，B/C为失败压力态真实1倍形变上的应力/局部J；D为原无载与该压力态响应。
只有两个实存加载级，不伪造5个平衡态；Newton迭代不称为生理时间。
首次图件校验因缺FIGURE_SIZE_IN元数据失败；只补图形元数据并重执行绘图，未改科学数据。

结果：E:\Temp-Projects\PRL-results\ventricle_fem\f6s2r_idealized_3d_resume_v01_20260918。
123文件17,765,106 bytes，manifest覆盖122项，SHA-256：
cb846ad96711d6706a7a9b2912ddf9100a65c2a3645e9dd7f7af14c0eafd455c。
1817父/祖先文件、71调用文件、50项无关修改及执行源代码哈希全部保持。
仓库约2.038GB，低于3GiB；结果不进Git。无安装、拉取、Docker修复、删除或推送。
本次tmp/f6s2r_checks仅含受控检查缓存，保留；任何删除仍需精确清单及单独确认。

[结构与结果图](../../PRL-results/ventricle_fem/f6s2r_idealized_3d_resume_v01_20260918/index.html) ·
[原失败](../../PRL-results/ventricle_fem/f6s2r_idealized_3d_resume_v01_20260918/failure.json) ·
[只读定位](../../PRL-results/ventricle_fem/f6s2r_idealized_3d_resume_v01_20260918/offline_diagnosis.json) ·
[独立复核](../../PRL-results/ventricle_fem/f6s2r_idealized_3d_resume_v01_20260918/post_verification.json)。

只读复核：`python -B -X utf8 -m prl verify fem-idealized-3d --resume-qualified-zero`，预期failed；
相应run是create-only，拒绝重复运行已冻结包。

## 唯一下一步（待确认，不在本次首失败后的授权内）

仅用已有M1几何做零载与同p=0.01两个状态，与保留M0失败比较。
保持材料、边界、离散和1%门，首失败停止，单CPU/0GPU，不进入主动、生长、FSI。
若细化明显降低失真，支持空间离散贡献；若无改善，再分别设计基底/压力空间对照。
即使两态通过，也仅是离散诊断，不自动取得全3D加载或生物学资格。
