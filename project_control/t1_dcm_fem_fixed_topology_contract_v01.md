---
record_id: T1-DCM-FEM-FIXED-TOPOLOGY-CONTRACT-V01
status: approved
authorized_at: 2026-08-11
authorized_by: human_final_reviewer
scope: fixed-topology quasi-static active DCM coupled to explicit tetrahedral FEM ECM
upstream:
  - project_control/t1_figure2_contact_topology_contract_v01.md
  - project_control/t1_figure2_execution_log_v01.md
preserves:
  - project_control/external_scientific_review_constraints_v01.md
  - project_control/hybrid_x1_k_r1_midpoint_collapse_diagnostic_failure_report_v10.md
formal_x1_k_gate_change: false
---

# T1 固定拓扑 DCM–FEM 接触极性 benchmark 合同 v01

## 1. 科学问题

在真实的主动 DCM 单细胞、有限变形四面体 FEM ECM 和功率一致材料 tether 中，检验解析 Figure 2 的最低风险预测：

1. 把同一个单侧 ECM patch 从细胞基底面镜像到顶面，轴向缩短应保持一致，弯曲方向应反转；
2. 将总 tether 积分权重平均分配到上下两侧，反射对称性应抵消一阶弯曲；
3. 上述趋势必须在固定拓扑、正 Jacobian、精确细胞体积和界面功率闭合条件下出现。

本阶段不以单侧与双侧的轴向缩短差作为主证据，因为双侧构型包含两块 ECM 体；只有完成等效轴向刚度校准后，才能把缩短差异归因于拓扑。

## 2. 复用组件

- 主动 DCM：`route_h.distributed_active_cell` 的分布式纤维主动应变；
- 被动 DCM：现有全局面积、弯曲和网格质量能量，细胞体积用等式约束精确保持；
- FEM ECM：`route_h.ecm_finite_strain` 的四面体有限变形能量；
- 界面：`hybrid.cell_ecm_coupling` 的参考材料 tether，同一点投影、作用反作用和能量导数；
- 求解：增量激活下的准静态联合极小化，细胞和 ECM 同时作为未知量，ECM 远端固定。

## 3. 几何与拓扑

细胞使用当前 M1 参考网格，不改变节点、三角面或材料参数。

ECM patch 为覆盖细胞轴向—横向投影的规则四面体层：

- 基底 patch 位于细胞最小 `y` 面外侧；
- 顶面 patch 是其关于细胞中面的严格镜像；
- 远离细胞的 ECM 外表面固定；
- 所有计算期间拓扑不变，不执行 split/swap/merge。

正式工况：

| 工况 | 接触面 | ECM | tether 权重 |
|---|---|---|---|
| free | 无 | 无 | 0 |
| basal | 基底面 | 下侧一块 | 每个基底面完整参考面积 |
| apical | 顶面 | 上侧一块镜像 ECM | 每个顶面完整参考面积 |
| symmetric | 上下两面 | 上下两块镜像 ECM | 每侧参考面积乘 1/2，总积分权重与单侧相同 |

## 4. 材料和加载

- 峰值主动应变参数：`activation = 0.20`；
- 激活增量：`0, 0.05, 0.10, 0.15, 0.20`；
- 细胞材料沿用通过 M1 准静态门的参数：纤维 `10.0`、全局面积 `0.1`、弯曲 `0.01`、网格质量 `0.05`；
- ECM 首轮采用纯弹性峰值基线：`mu_eq = 1.0`、`kappa_eq = 20.0`、`mu_ve = 0.0`；
- tether：同一 `adhesion_work`、`opening_cutoff` 和 `tangential_stiffness`，只按上表改变接触集合与权重；
- 本轮不加入黏性、周期相位或内部变量演化。

若初始参数导致首个非零激活步越过几何门，允许在正式结果前做一次显式标记的低风险 screening，选择更小 tether 刚度或激活峰值；不得隐藏失败或只保留漂亮工况。

## 5. 主观测量

- 轴向缩短：沿现有纤维轴的两端加权距离变化；
- 弯曲：轴向左端、中部、右端表面节点加权中心线的中点弓高及抛物线曲率代理；
- ECM：位移模、第一 Piola 应力/能量密度代理、最小和最大 Jacobian；
- 界面：tether 牵引合力、合矩、最小 gap、耦合能；
- 守恒：细胞体积误差、KKT 残差、界面 pair force/moment residual、总能量方向导数。

## 6. 预注册主门

正式峰值工况必须同时满足：

### 6.1 镜像物理门

- basal 与 apical 的峰值轴向缩短绝对差不超过 `0.2` 个百分点；
- 两者弓高/曲率符号相反；
- 两者曲率绝对值相对差不超过 `10%`；
- symmetric 曲率绝对值不超过单侧平均绝对曲率的 `10%`。

### 6.2 几何和求解门

- 所有工况优化器成功；
- 最大细胞体积比误差 `<= 1e-8`；
- 最大归一化 KKT 残差 `<= 1e-5`；
- 最小细胞面面积比 `>= 0.05`，无翻转或退化面；
- 所有 ECM 四面体 `J > 0`；
- 最小 cell–ECM gap `>= -1e-12`。

### 6.3 界面与能量门

- pair force residual `<= 1e-10`；
- pair moment residual `<= 1e-10`；
- 联合总能量对随机许可方向的中心差分误差 `<= 1e-5`；
- reference activation `0` 时除允许的常数黏附基准能外，力学残差为零。

## 7. 输出

- 实现：`src/hybrid/fixed_topology_active_cell_ecm.py`；
- 测试：`tests/hybrid/test_fixed_topology_active_cell_ecm.py`；
- 运行脚本：`scripts/run_t1_dcm_fem_fixed_topology_v01.py`；
- 结果：`results/hybrid/t1_dcm_fem_fixed_topology_v01/`；
- 阶段记录与审阅图：执行后新增，不覆盖 Figure 2 解析结果。

## 8. Claim guard

本 benchmark 即使通过，也只允许声称：固定拓扑、准静态、未标定参数下，显式 DCM–FEM 实现复现或否定接触极性的镜像对称性预测。

不得声称：

- X1-K、重网格鲁棒性或长时间稳定性已经通过；
- 单侧与双侧缩短差已完成等效刚度控制；
- 已建立 cardiac-jelly 黏弹相位、完整三层、在体斑马鱼、EFE 或发育机制。

