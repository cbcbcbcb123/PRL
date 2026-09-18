---
document_id: PRL-FEM-CONTOUR-PASSIVE-CONTRACT-V01
status: adopted
accepted_at: 2026-09-18
authority: user 继续 after the explicit six-remaining-passive-state proposal
---

# F6-S1-S8：从已接受原轮廓态补齐被动压力序列

复用F6-S1-S7的M0/M1零载与p/mu=0.02，不重新求解。仅依次计算
M0的0.04/0.06/0.08，再计算M1的0.04/0.06/0.08，最多6个新平衡。
每态独立物理门通过才能继续；M1每态同时检查与同载荷M0的面积响应门。
首个失败即停止，保留失败/最后有效态与所有真实Newton向量，不自动重跑。

## 冻结输入及不变项

父包manifest SHA-256为524b1560a9ba63a0b99a19f20188cdaf704bd05a0d507a65e32c1cf21ccf0704。
原3541/14164三角形网格直接复用，禁止Gmsh、重细分、边界平滑。
同一Ring内核、P2/DG2、六阶积分、平面应变有限变形NH，mu=1、kappa=1000、Ta=0；
内壁随动压力、外壁自由、A固定ux/uy与B固定uy；MUMPS ICNTL(14)=100。
当前三层同被动参数且未标定，只有外轮廓来自72 hpf Fish 4图像，内腔和层界为构造。
恢复前必须逐项检查原/新网格全部坐标、单元、层、边界、固定点和混合空间DOF映射相同。
原1%局部J、正J、平衡残量、弱压力、DG2点态约束、F/J/应力/力、反力及虚功门不变。
逐压力粗细面积响应差绝对<=0.002且相对<=5%；非圆形不套用圆环解析解。
不将两个网格级别的通过表述为热点或渐近收敛、实验吻合或三维资格。

## 运行和交付

create-only结果：E:\Temp-Projects\PRL-results\ventricle_fem\f6s1s8_contour_passive_v01_20260918。
只启动一次固定本地FEniCSx镜像容器，1CPU/8GiB/0GPU/禁网，1200秒上限。
准入预计512MiB、停止保全64MiB、磁盘余量10GiB、代码仓3GiB；无安装、拉取、重启或Docker修复。
运行锁外核验父/祖先及50项无关修改哈希；运行后独立复核原始保存状态，禁止修改冻结父包。
结构与形变/应力/J图采用可执行Notebook及600dpi PNG/SVG，真实1倍形变。
最多展示每网格5个真实载荷态；缺失态明确not_run、失败态保持failed；加载级非生理时间。
本地main精确阶段提交，不推送、删除或搬移；不运行主动、圆环、3D、FSI、生长或额外原生微测。
完整被动资格通过后再提出主动心肌收缩切片，不以本合同自动授权。
