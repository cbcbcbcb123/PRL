---
document_id: PRL-VENTRICLE-Z1A-SPHERE-BASELINE-CONTRACT-V01
status: frozen
frozen_at: 2026-09-11
parent_stage: Z1
execution_scope: cpu_bounded_read_only_external_kernel
---

# Z1-A 球形保守力与 Laplace 基准合同 v01

## 目标

在不修改唯一 `muse_dcm` 内核的条件下，隔离验证球形细胞所需的体积保守力与恒表面张力。该子门用于判断旧 Z1 阻断是否来自全部被动力路径，还是仅来自弯曲、全局面积和各向异性参考态。

## 冻结模型

使用三档闭合 icosphere（80/320/1280 面），等体积半径 `R0=4.5e-6 m`。只允许：

\[
E_V=K\left[V\ln(V/V_0)-V+V_0\right],\qquad E_\gamma=\gamma A,
\]

其中 `K=6000 Pa`、`gamma=5e-5 N/m`。由唯一内核输出节点力；独立验证器从几何状态重算上述工作共轭能量。弯曲、全局面积弹性、主动、接触、ECM 和流体均关闭。

内核现有 `pressure_energy` 与 `surface_tension_energy` 字段继续作为已知诊断项记录，不能替代独立能量，也不能因字段不一致改写力—能量结果。

## 实验与门

1. 三档网格闭合、朝向、体积和最小角；
2. 体积项、表面张力项及二者组合的随机方向中心差分：每项最佳相对误差 `<=1e-6`；
3. 非坐标轴刚体旋转和平移：能量、力协变、合力和合矩相对残差 `<=1e-10`；
4. 表面张力节点力拟合体积梯度反力，比较 `Delta p=2 gamma/R`：fine 相对误差 `<=2%`；
5. medium→fine 的拟合压差相对变化 `<=2%`，且 coarse→medium→fine 的解析误差单调下降；
6. fine 节点力—拟合压力残差 `<=2%`。

任一必需门失败则 Z1-A 为 `FAIL_NUMERICAL`。全部通过时 Z1-A 可为 `PASS`，但父阶段 Z1 仍因参考态、弯曲/面积路径和正式加载未完成保持 `BLOCKED_DEPENDENCY`。

## 预算与输出

- CPU 最多 4 线程，总墙钟上限 600 s；GPU、网络和外部仓库写入禁止；
- 输出：冻结预登记、原始 CSV/NPZ、结构 PNG/SVG、定量结果 PNG/SVG、机器摘要、独立验证、日志、HTML 和执行记录；
- 不运行主动、动态松弛、多细胞拥挤或 Z2。

