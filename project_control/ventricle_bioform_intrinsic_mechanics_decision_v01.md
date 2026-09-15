---
document_id: PRL-VENTRICLE-BIOFORM-INTRINSIC-MECHANICS-DECISION-V01
status: adopted
decided_at: 2026-09-13
applies_to: forward myocardial and endocardial cell-shape qualification before renewed trilayer formation
supersedes_scientific_results: false
---

# 心室细胞形态机制修订决定 v01

## 用户决定

用户确认停止把组织内最终长轴/扁平外形当作孤立细胞的逐边参考形状，改为先分别建立并验证细胞类型特异的内在力学状态，再逐级加入最小生理环境和三层组织。执行顺序为：先心肌细胞，再心内膜细胞，最后重新装配心肌—ECM—心内膜三层。

本决定不覆盖或改判既有 `Z1-TF2-B`。其 `failed_numerical` 结果、全部失败轨迹、阈值和图片继续冻结。

## 新的科学定义

1. **不使用细胞表面参考形状。** 心肌和心内膜的逐边参考长度、逐面参考度量及目标最终网格均保持关闭。
2. **活细胞稳态不是纯被动形状能最小化。** 细胞外形由被动膜/皮质/体积项、主动或稳态细胞骨架应力、黏附与外部环境共同满足力平衡。
3. **心肌先验证内禀各向异性。** 第一子门使用一个从近球形起步的自由心肌 DCM，加入不依赖目标几何的对称细胞骨架预应力张量；它是肌原纤维、actomyosin、微管和中间丝合成作用的连续介质代理，不冒充分子分辨肌节网络。
4. **心内膜不要求悬浮自由细胞天然扁平。** 后续心内膜子门以悬浮细胞为圆化阴性对照，以 ECM 黏附和周期性连续小单层作为最小生理稳态。
5. **生物目标按发育时相和区域解释。** 第一目标限定为约 48 hpf 斑马鱼心室外弯曲区心肌细胞；内弯曲区作为区域对照。成人杆状心肌细胞不是本子门的统一目标。

## 与旧方向载荷的关系

`Z1-TF2-B` 中沿组织轴施加的静态节点载荷仅是方向性承载代理。新路线用闭合曲面上的张量牵引替代该代理：对常量对称张量 `Sigma_cyt`，每个三角面施加积分力 `A_f Sigma_cyt n_f` 并均分到三个顶点。闭合曲面上总力为零；张量对称时总力矩为零。该载荷不读取初始边长、最终形状或目标长宽比。

第一子门只验证合成的细胞骨架成形机制、旋转客观性、消融和数值收敛；缺少同期三维分割数据时，生物学标定状态保持 `blocked`。

## 执行与停止边界

- 当前授权只覆盖 `Z1-BIOFORM-MYO-A`：心肌自由态细胞骨架资格门、CPU 预检、一次冻结正式矩阵、独立复核、图片和驾驶舱同步。
- 不执行心内膜子门、ECM 黏附心肌子门、三层重跑、周期收缩、物理时间标定、CFD、FSI、GPU、软件安装、提交、推送或删除。
- 实现放在 PRL 项目内并复用唯一 `external/simucell3d/`；不得复制第二套内核。

## 文献边界

- Auman HJ et al. *Functional Modulation of Cardiac Form through Regionally Confined Cell Shape Changes*. PLOS Biology 5:e53 (2007). https://doi.org/10.1371/journal.pbio.0050053
- Ribeiro AJS et al. *Contractility of single cardiomyocytes differentiated from pluripotent stem cells depends on physiological shape and substrate stiffness*. PNAS 112:12705-12710 (2015). https://doi.org/10.1073/pnas.1508073112
- *Regionalized regulation of actomyosin organization influences cardiomyocyte cell shape changes during chamber curvature formation*. Nature Communications (2026). https://doi.org/10.1038/s41467-026-70384-5

这些论文支持“骨架、黏附/基底和外部力共同决定形态”的方向，但不提供本轮无量纲预应力参数，也不构成本模型的实验验证。
