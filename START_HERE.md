---
document_id: PRL-START-HERE
status: current
updated_at: 2026-09-18
---

# PRL｜斑马鱼心室 FEM

## 目标与路线

用FEM研究斑马鱼心脏发育与心动、血流相互作用，不恢复DCM。
先理想化三维及公开资料，后续替换自有实验；当前几何尚未用morphoHeart标定。
路线：三维固体 → 生长公式及规定式三维生长 → 双向FSI → 力学生长/ECM反馈。
[路线决定](project_control/ventricle_3d_before_growth_decision_v01.md)不自动授权后续全部运行。

## 当前模型与结果

三维半椭球壳，心内膜/ECM/心肌三域；有限变形NH、P2位移/P1压力四面体。
基底环全固定、外壁自由、内腔随动压力；三维主动张力尚未运行。
mu=1、kappa=1000、几何与纤维分布均未标定，不是实验心室。

**已吸收专家意见并独立复核已有M0/M1压力态；没有新的FEM求解。**
离线诊断passed；原三维压力门仍failed。局部体积偏差可拆为材料压缩项p_m/κ与投影缺陷r。
细化后r的体积加权RMS从0.1651%降至0.1200%，但采样最大|J−1|仍为1.4496%，超过原1%门。
max|p_m/κ|仅0.002044%；弱压力方程收敛不等于逐点体积约束满足。

![真实M1结构、全部单元体积偏差及固定距离分区](../PRL-results/ventricle_fem/volume_projection_audit_v01_20260918/diagnostic.png)

[轻量图、原始状态来源与独立复算](../PRL-results/ventricle_fem/volume_projection_audit_v01_20260918/index.html) ·
[专家采纳、已完成分析与待确认批次](project_control/ventricle_volume_qualification_adoption_v01.md)

M1峰值点距基底0.302L；“超限单元邻接基底”不意味着偏差只在固定面。
固定距离分区中仍有一区RMS略升；不是纯h收敛或稳定性证明。
14项针对性数学测试、专家数字对照及原始数据读回复算通过；没有新的形变/心动结果。

## 主要难点与唯一下一步

材料压缩项不能单独解释局部偏差；离散压力空间、薄层、夹持和几何的贡献尚未分离。
原非结构化U1候选的质量门失败及适配器首失败仍保留，不追认通过。

**唯一下一步：一次确认后执行2个非零patch + 3网格×2κ制造解，共8个工况。**
保持当前三维P2/P1，先验证实现和误差收敛，再决定一个薄层鉴别；不直接照搬二维DG。
整批单CPU、0GPU、最多1800秒、无自动重跑；具体门限和停止规则已预注册。
新批次仍not_run、待确认；不修改原1%门，不运行心室主动、生长或FSI。

## 证据与存储

结果保存在已批准的E:\Temp-Projects\PRL-results，不进GitHub；本包21文件、1,664,438 bytes。
专家原件/附件9文件与原D1证据127文件哈希核验通过；不改原始材料和50项既有无关修改。
代码仓3GiB与磁盘余量保护保持；本地main阶段提交，不自动推送。无删除、安装、Docker或GPU。
探索图160dpi，投稿级600dpi检查明确未通过；不影响原始数字复算，不标为投稿终稿。

- [专家原件与补充材料](plan/active/EXP-20260918-FEM-review-v01/README.md)：原样保全，身份unknown。
- [原非结构化候选](../PRL-results/ventricle_fem/f6s2d2b_unstructured_v01_20260918/index.html)：质量failed，FEM not_run。
- [原三维压力失败](../PRL-results/ventricle_fem/f6s2d1_3d_fine_pressure_v01_20260918/index.html)：原场量与失败保留。
- [二维低压主动passed](../PRL-results/ventricle_fem/f6s1s9_contour_active_v01_20260918/index.html)：缩腔约1.85%，不是三维或实验心跳。
- [权威状态及历史](project_control/CURRENT_STATUS.md) · [驾驶舱](memory/project_cockpit/index.html)
