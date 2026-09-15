---
record_id: T1-DCM-FEM-FIXED-TOPOLOGY-SCREENING-V01
status: passed_coarse_screening
executed_at: 2026-08-11
contract: project_control/t1_dcm_fem_fixed_topology_contract_v01.md
evidence_level: coarse_fixed_topology_screening_not_spatially_converged
formal_x1_k_gate_change: false
---

# T1 固定拓扑 DCM–FEM 阶段筛查记录 v01

## 1. 本轮实际完成内容

本轮已经不再停留于解析约化模型，而是执行了显式联合求解：

- 主动 DCM 心肌细胞：分布式轴向主动纤维，峰值激活 `0.20`；
- 连续 ECM：四面体有限变形 FEM，`mu_eq=1.0`、`kappa_eq=20.0`、`mu_ve=0.0`；
- 界面：材料点 tether、作用反作用一致、显式非穿透不等式约束；
- 工况：free、basal、apical、symmetric；
- 激活路径：`0, 0.05, 0.10, 0.15, 0.20`；
- ECM 粗网格：`patch_divisions=(3,1,2)`；
- 本轮为固定拓扑、准静态、粗筛查，不包含 remeshing、周期稳态或空间收敛声明。

## 2. 计算过程中的一次可解释失败与修复

最初目标函数仍沿用界面评价器的“试探态穿透即拒绝”策略，SLSQP 在首个非零激活步的线搜索中遇到负 gap。该问题没有通过降低精度或隐藏失败处理，而是把每个 tether 的 `gap >= 0` 作为显式不等式约束，并实现解析 Jacobian。

完成全部状态后，原始运行器又将活动非穿透约束产生的反力错误计入 KKT 未平衡力，只使用体积等式乘子，因此得到约 `6e-4–1e-3` 的伪 KKT 失败。重新审计时联合求解体积等式乘子和非负 gap 乘子，峰值归一化 KKT 降至 `1.80e-6–1.94e-6`，且互补残差小于 `9e-14`。原始输出被保留；修正结果另存为 `*_constrained_kkt.*`，没有覆盖失败痕迹。

## 3. 峰值结果

| 工况 | 轴向缩短 | 有符号曲率代理 | KKT | 活动 gap 数 | 最小 ECM J |
|---|---:|---:|---:|---:|---:|
| free | 15.6764% | 近零 | 既有 M1 审计 | — | — |
| basal | 15.6196% | -4.4298e-3 | 1.9369e-6 | 2 | 0.994745 |
| apical | 15.6196% | +4.4300e-3 | 1.8259e-6 | 2 | 0.994729 |
| symmetric | 15.6193% | +1.3440e-7 | 1.7979e-6 | 4 | 0.997311 |

补充数值指标：

- 最大细胞体积比误差：小于 `1e-12`；
- 最小细胞面面积比：`0.8770`；
- 最小 gap：`7.71e-11`，未穿透；
- pair force / pair moment residual：均为 `1e-18` 量级；
- basal 与自由细胞峰值缩短差：`-0.0568` 个百分点，当前粗参数下 ECM 对总缩短的影响较弱，但已产生可分辨的偏心弯曲反应。

## 4. 预注册镜像门结果

- basal/apical 缩短差：`3.99e-7` 个百分点，门槛 `<=0.2`，通过；
- basal/apical 曲率符号相反，通过；
- 两者曲率绝对值相对差：`4.95e-5`，门槛 `<=0.10`，通过；
- symmetric 曲率 / 单侧平均曲率：`3.03e-5`，门槛 `<=0.10`，通过；
- 全部耦合状态与自由对照完成，固定拓扑粗筛查通过。

这说明 Figure 2 的最低风险预测已经被真实 DCM–FEM 求解复现：有符号接触极性控制弯曲方向，而镜像对称接触消除一阶弯曲；总接触面积/权重匹配时，轴向缩短基本不随镜像方向改变。

## 5. 可复现证据

- 实现：`src/hybrid/fixed_topology_active_cell_ecm.py`
- 界面兼容修改：`src/hybrid/cell_ecm_coupling.py`
- 单元与回归测试：`tests/hybrid/test_fixed_topology_active_cell_ecm.py`、`tests/hybrid/test_cell_ecm_vertical_slice.py`
- 原始运行：`scripts/run_t1_dcm_fem_fixed_topology_v01.py`
- 约束审计：`scripts/postprocess_t1_dcm_fem_fixed_topology_v01.py`
- 阶段图：`scripts/build_t1_dcm_fem_fixed_topology_figure_v01.py`
- 结果目录：`results/hybrid/t1_dcm_fem_fixed_topology_v01/`
- 当前测试：`14 passed`。

## 6. Claim guard 与下一门

当前只允许声称：在未标定参数、固定拓扑、准静态和粗 FEM 网格下，显式 DCM–FEM 框架再现了解析模型预言的接触极性镜像关系，并通过体积、非穿透、正 Jacobian、KKT 与界面平衡门。

当前仍不允许声称：

- ECM 空间离散已经收敛；
- 单侧/双侧工况已经完成等效刚度校准；
- X1-K remeshing 鲁棒性已经通过；
- 已建立完整 cardiac jelly 黏弹性、内膜层、周期心搏或在体斑马鱼模型。

建议下一门为 T1.1：在保持固定拓扑的前提下，执行 ECM 网格加密与等效刚度校准，验证曲率和缩短对 FEM 离散、patch 厚度、`mu_eq/kappa_eq` 及 tether 刚度的收敛与敏感性。通过后再进入黏弹 cardiac jelly 与内膜薄层。
