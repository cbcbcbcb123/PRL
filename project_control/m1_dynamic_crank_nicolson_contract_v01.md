---
record_id: M1-DYNAMIC-CRANK-NICOLSON-CONTRACT-V01
status: approved
authorized_at: 2026-08-11
authorized_by: human_final_reviewer
scope: single-cell second-order overdamped time integration
formal_gate_change: false
---

# M1 二阶 Crank–Nicolson 动态积分验收合同 v01

## 1. 目标

在不改变单细胞几何、材料参数、主动纤维本构、体积约束和刚体规范的前提下，用二阶 Crank–Nicolson 时间积分替代一阶 backward Euler，降低时间离散造成的附加能量耗散，并保持收缩形态与相位响应稳定。

本合同只验证模型时间内的数值精度，不把周期或阻尼换算为真实秒、真实心率或真实黏度。

## 2. 固定条件

- 周期：1.0；周期数：1；
- 峰值主动应变：20%；纤维刚度：10.0；阻尼：1.0；
- 全局面积、弯曲和网格正则刚度：0.1、0.01、0.05；
- 精确体积等式约束和六个刚体自由度规范保持不变；
- 时间分辨率：20、40、80 步/周期；
- 一阶 20/40/80 结果只作为冻结对照，不被覆盖。

## 3. 二阶离散

对过阻尼约束梯度流，使用端点平均的机械力与约束反力：

\[
\eta\mathbf W\frac{\mathbf x_{n+1}-\mathbf x_n}{\Delta t}
+\frac{1}{2}\left(\mathbf f_n+\mathbf f_{n+1}\right)=0,
\qquad g_V(\mathbf x_{n+1})=0,
\]

其中 \(\mathbf f\) 包含储能梯度和体积约束反力。新时刻仍通过受约束优化求解，上一时刻的已平衡约束反力以线性项进入离散泛函。

主动功使用端点梯形积分：

\[
W_{a,n}=\frac{a_{n+1}-a_n}{2}
\left[
\partial_a E(\mathbf x_n,a_n)
+\partial_a E(\mathbf x_{n+1},a_{n+1})
\right].
\]

能量缺陷按

\[
r_n=E_{n+1}-E_n+D_n-W_{a,n}
\]

审计。由于二阶方法的 \(r_n\) 可以有符号，必须同时报告净缺陷 \(|\sum r_n|\) 和逐步绝对缺陷 \(\sum|r_n|\)，不得用正负抵消替代精度证明。

## 4. 验收条件

1. 原有 backward Euler 回归测试全部通过，默认入口数值行为不变。
2. 20/40/80 三组均完整到达周期末；所有优化器成功。
3. 最大体积比误差不超过 `1e-8`，最大动态 KKT 残差不超过 `1e-5`，最小面面积比不低于 0.05，无翻转或退化面。
4. 物理黏性耗散逐步非负。
5. 20 步时，逐步绝对能量缺陷占总正主动输入不超过 10%；随 20→40→80 加密应单调下降。
6. 插值峰值缩短和插值相位延迟的三层观测阶原则上应不低于 1.5；若最细两层差值已低于 `1e-4`，则记录为进入优化器/后处理分辨率平台，不强行计算阶数。
7. 40 步二阶方案的墙钟时间低于既有一阶 80 步基线 2391 秒。

任一几何、约束或求解器条件失败，则本阶段失败；能量或观测阶条件失败，则保留结果作为诊断证据，但不得宣称二阶时间精度门通过。

## 5. 输出

- 实现：`src/route_h/distributed_active_dynamics.py`
- 回归测试：`tests/stage2/test_distributed_active_dynamics.py`
- 正式脚本：`scripts/run_m1_dynamic_crank_nicolson_v01.py`
- 结果目录：`results/route_h/m1_dynamic_crank_nicolson_v01/`
- 阶段记录：`project_control/m1_dynamic_crank_nicolson_v01.md`

## 6. 范围外

- 多周期极限环；
- ECM、心胶、心内膜或多细胞耦合；
- 阻尼、周期和材料参数的实验标定；
- 论文级统一绘图风格。
