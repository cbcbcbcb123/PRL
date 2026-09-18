---
document_id: PRL-FEM-CONTOUR-DG2-EXECUTION-V01
status: passed
delivery_status: passed
date: 2026-09-18
contract: project_control/ventricle_fem_contour_dg2_contract_v01.md
result: E:/Temp-Projects/PRL-results/ventricle_fem/f6s1s7_contour_dg2_v01_20260918
---

# F6-S1-S7：原外轮廓零载/首压力的两网格资格通过

按用户“确认，继续”及[冻结合同](ventricle_fem_contour_dg2_contract_v01.md)，
仅M0/M1零载及p/mu=0.02，4次求解全部接受；0圆环重算、0原生微测、0网格生成。
一次122.067秒容器，单CPU、8GiB、禁网、0GPU、0自动重跑。
复用原图像外轮廓和原保存粗细网格，不平滑边界；内腔和三层界面仍是构造，非测量。
P2/DG2、六阶积分、平面应变有限变形NH，mu=1/kappa=1000，Ta=0。
内壁随动压力、外壁自由；A固定ux/uy、B固定uy。三层被动材料相同且未标定。

## 数值结果

| 同一p/mu=0.02 | M0粗网格 | M1细网格 |
|---|---:|---:|
| 三角形数 | 3541 | 14164 |
| 腔面积变化 | +20.056188% | +20.105502% |
| 壁局部max\|J−1\| | 0.323434% | 0.358062% |
| 原局部体积门 | passed，<=1% | passed，<=1% |
| 旧CG1局部max\|J−1\|，仍failed | 6.71167% | 11.15248% |
| 独立自由力残量 | 1.691e-14 | 3.295e-14 |
| max\|J−1−p_m/kappa\| | 1.911e-13 | 3.470e-13 |

40项独立范围/复核检查通过；逐态F/J/应力/力、弱压力、反力、虚功及局部体积原门全部保持。
粗细腔面积变化差0.000493142（0.0493142个百分点），相对差0.245277%，低于原0.002/5%门。
两网格正压均10次Newton更新，MUMPS实际ICNTL(14)=100、INFOG=0；零载0次更新，
因子状态not_run/null，没有访问未建立或陈旧因子。共24个真实Newton向量全部保存并独立重算。

同一几何/材料下，仅改变局部压力表示后体积超限消除，支持旧CG1局部体积约束未充分分辨的解释。
这不是严格不可压极限inf-sup证明，也不能直接推广至三维P2四面体。
细网格局部J峰值仍比粗网格高，未证明应力热点或多级渐近收敛。
目前只通过首压力两级切片，完整轮廓被动压力序列仍not_run；不把面积一致当成所有场量收敛。

## 图件、附加几何筛查与交付问题

两套Notebook、结构/形变/应力/局部J的600dpi PNG和SVG均通过执行、CB样式及目检。
实际1倍形变；每网格仅零载/首压力两态，4个图中状态均真实保存，没有生理时间或插值假帧。
按目检对凹口作只读附加筛查：每条实际二次边界边用24/48段采样，4态均未发现边界自交，
内腔保持包含关系。受压细网格采样最小壁间距0.0769453 L；这是采样筛查，不是精确曲线全局单射证明。
原始代码和输入哈希在包内analysis/boundary_screen.py、boundary_screen.json，不新增平衡。

首次交付冻结因主机/容器报告比较failed，原失败记录保留：仅M0的
pressure_area_difference_work相差1.3322676e-12，所有40项门和分类一致。
该量是p*(A_plus−A_minus)/(2h)，h=1e-5，差分消减放大浮点舍入。
交付比较器仅对该诊断显示量采用16*机器epsilon*|p|*max(1,|A|)/h的舍入余量；
其余数值仍rtol=1e-10/atol=1e-12，所有分类精确一致，原物理门/原报告/求解源均未改。
保留修复前1failed+6passed回归及全部日志；修复后110tests+21subtests passed。
最终同一保存报告的比较与冻结通过，没有重新启动容器或重算FEM。

## 完整性与复核

1194个父/祖先文件、102个正式调用文件、50项无关修改保持；32份输入/源副本哈希匹配。
结果包164文件、184,644,758 bytes（约176.09MiB），其中163个manifest条目；SHA-256：
`524b1560a9ba63a0b99a19f20188cdaf704bd05a0d507a65e32c1cf21ccf0704`。
代码仓冻结前2,036,548,773 bytes（含既有Git/证据/缓存），低于3GiB；结果外置，不进入GitHub。
无安装/拉取/Docker修复/推送/删除；旧failed包不改写。

复核入口（不会调用求解器）：设置PYTHONPATH=src后，
`python -B -X utf8 -m prl verify fem-fenicsx-contour-pressure`。
完整正式调用见结果command.json，求解源快照及配置同时保留；run为create-only，不能原地重跑。

见[结构、真实状态与Notebook](../../PRL-results/ventricle_fem/f6s1s7_contour_dg2_v01_20260918/index.html)、
[独立复核](../../PRL-results/ventricle_fem/f6s1s7_contour_dg2_v01_20260918/post_verification.json)、
[跨平台字段比较](../../PRL-results/ventricle_fem/f6s1s7_contour_dg2_v01_20260918/cross_platform_agreement.json)。

## 唯一下一步（待确认）

复用本轮两个网格已接受p/mu=0.02态，仅补原被动压力0.04/0.06/0.08，最多6个新态。
同一几何、材料、P2/DG2和1%门，单CPU/0GPU、首失败即停；不重跑零载/0.02或圆环。
完整被动资格通过后再裁决主动心肌收缩，不在本轮夹带主动、三维、FSI或生长。
当前是未标定二维固体资格，不是实验吻合或生物学验证。

本次临时目录E:\Temp-Projects\PRL\tmp\f6s1s7_checks及结果figure_runtime有任务所有权说明，
交付后保留，未获准删除；本轮不发起新的清理批次。
