---
document_id: PRL-FEM-RING-RESUME-EXECUTION-V02
status: passed
executed_at: 2026-09-18
contract: project_control/ventricle_fem_ring_resume_contract_v02.md
engineering_execution: passed
first_coarse_ring_pressure: passed
mesh_convergence: not_run
contour: not_run
biological_validation: not_run
result_root: E:/Temp-Projects/PRL-results/ventricle_fem/f6s1s4_ring_first_pressure_v02_20260918
---

# F6-S1-S4 v02：首个圆环受压平衡恢复，原门限不变

同环境真实接口先验通过后，唯一一次原圆环首压力平衡通过。此前监测与选项生命周期问题
在本次实际PETSc/MUMPS调用中得到复验，不再只依赖协议测试。
本阶段只接受粗圆环的一个压力点，不代表整个压力空间、实际轮廓或生物学已经验证。

## 不变的模型与范围

二维平面应变、有限变形近不可压Neo-Hookean；mu=1、kappa=1000，均为未标定无量纲参数。
M0为64周向×径向1/1/5分层、896个三角形、1920个位移节点；P2位移/DG2压力。
内壁随动压力p/mu=0.02、外壁自由，A固定ux/uy、B固定uy去除刚体运动。
三层暂用相同被动材料，主动幅值Ta=0。压力是给定边界，不是流体求解产生的压力。
原保存零载仅验证和读取为初值，不重算；1%局部体积等全部门限不放宽。

## 执行与独立核验

固定镜像SHA：`2ae4bfbc0d9077268880faf04c72750528bee986c94ab223a2c159969bd56fa8`。
一次21.891秒容器调用，单CPU、8GiB、禁网、0GPU；FEM求解段约0.554秒。
1次非线性尝试、1个接受平衡、0次零载重算/自动重跑。9项容器安全配置通过。

1. 6自由度对角方程夹具调用真实生产monitor与因子选项绑定，不含FEM模型。
   已知解误差1.92e-16、相对残量4.66e-17，实际MUMPS ICNTL(14)=100、INFOG(1)=0。
   12项接口核验通过。该夹具为合成工程证据，不是心室平衡或生物学结果。
2. 原圆环从精确保留零载续算，3次Newton更新后SNES=2；KSP=4、PC=0、MUMPS INFOG(1/2)=0，余量100。
   保存全部4个实际监测状态；独立核验初值、末态及混合映射一致。
3. 21项范围/来源核验与20项末态力学检查通过；原零载18项门保持。
   容器验证和宿主只读复核均通过，宿主复核没有新增FEM求解或全局矩阵分解。

| 独立结果 | 数值 | 原约束或含义 |
|---|---:|---|
| 腔室面积变化 | +4.675918128% | 腔室面积，不是壁组织体积 |
| max abs(J−1) | 0.002628443% | 小于原1%门，全部积分点检查 |
| J范围 | 1.0000218135–1.0000262844 | 正Jacobian、近体积保持 |
| 独立自由力残量 | 1.70e-14 | 小于2e-6 |
| 弱压力残量 | 2.82e-16 | 小于1e-8 |
| DG2点态体积约束误差 | 2.67e-14 | 小于1e-9 |
| 相对解析腔面积响应误差 | 0.0566923% | 小于5%；解析为不可压圆环参照 |
| 相对保留CG1面积响应差 | 0.00123356% | 小于5%；不是粗细网格收敛 |

腔室可以通过壁变形扩大而壁体积基本保持；面积响应和局部J是不同检验。
最大节点位移约0.0298316 L，含点规范所选择的平移，不可解读为2.98%应变。
旧CG1同粗圆环局部J偏差0.01336%也通过1%门；本轮不能宣称解决了旧真实外轮廓6.71%/11.15%的失败。

## 图件与可复算性

保存真实结构/载荷、1倍形变、等效Cauchy应力及局部J网格图，以及共享应力色标的全部4个Newton状态。
k=0为施压初猜，k=1/2仍未平衡，只有k=3为接受态。没有生理时间标定，不补造第5帧或心动动画。
Notebook从版本包物理复制的网格及u/p向量，使用独立NumPy力学快照重算F/J/应力；不调用求解器。
位移图为单元六节点模长均值；应力为积分点等效应力均值；局部J为逐单元积分点最大值，验收仍检查全体积分点。
不平滑、不改变数据，600 dpi PNG和SVG均完成样式及可视检查。

[本地结果总览与两套Notebook](../../PRL-results/ventricle_fem/f6s1s4_ring_first_pressure_v02_20260918/index.html)；
[独立复核](../../PRL-results/ventricle_fem/f6s1s4_ring_first_pressure_v02_20260918/post_verification.json)。
图件运行缓存登记在结果内figure_runtime；未授权删除，计入最终占用。

## 复核、保全及命令

事前62测试+21子测试，绘图数据回归增加后63测试+21子测试通过。
709个父/祖先文件（包括原v01失败包）及50项无关工作区变更保持哈希。
正式调用文件、源快照、Notebook、图件和日志由最终manifest逐项冻结；小索引在仓库，原始结果不进Git。
最终完整清单、字节数、哈希见结果manifest及导航登记，不在冻结文件中形成自身哈希循环。

运行命令（已消耗，本目录create-only，不能用于重跑）：
`python -B -X utf8 -m prl run fem-fenicsx-pressure --resume-first-ring --resume-revision 2 --workspace E:\Temp-Projects\PRL`。

只读复核：
`python -B -X utf8 -m prl verify fem-fenicsx-pressure --resume-first-ring --resume-revision 2 --workspace E:\Temp-Projects\PRL`。

测试：
`python -B -X utf8 -m pytest -q -p no:cacheprovider tests/prl/test_fenicsx_linear_system.py tests/prl/test_fenicsx_linear_system_render.py tests/prl/test_fenicsx_pressure.py tests/prl/test_fenicsx_ring.py tests/prl/test_fem_only_cli.py`。

没有额外压力/細网格/轮廓/主动/三维/FSI/生长计算；没有Docker修复、安装、拉取、删除或推送。
阶段直接在main精确本地提交；不纳入50项无关修改。

## 唯一下一步：完成被动固体资格，再回原轮廓

待确认后，从本次保留p/mu=0.02继续原粗网格0.04/0.06/0.08，并做原细网格零载及0.02/0.04/0.06/0.08：
合计最多8个新平衡，不重算本次接受态。材料、边界、离散方法和1%门不变，单CPU、失败即停、不自动重跑。
先检查全压力序列的局部J、解析响应和粗细差异，再裁决原轮廓；不在这一提议中夹带主动/三维/FSI/生长。
当前三维发育与双向FSI仍为后续主线，不恢复DCM，也不将静态公开资料称为自有实验验证。
