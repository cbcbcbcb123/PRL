---
record_id: M1-DYNAMIC-EXTERNAL-LOAD-CONTRACT-V01
status: approved
authorized_at: 2026-08-11
authorized_by: human_final_reviewer
scope: unloaded-to-loaded single-cell periodic mechanics
upstream_gate: M1-DYNAMIC-LIMIT-CYCLE-V01
formal_gate_change: false
---

# M1 单细胞轴向外载验收合同 v01

## 1. 科学问题

在已收敛的单细胞周期极限环上，分别加入外部弹性阻力和外部黏性阻力，回答：

- 环境刚度如何改变峰值缩短、输出力和每周期做功；
- 环境黏性如何改变缩短幅度、相位延迟和外部耗散；
- 外载下是否仍保持精确体积、稳定网格和周期极限环。

本阶段仍是集中参数外载端口，不宣称已经建立显式ECM或心胶连续体。

## 2. 轴向端口

以两端加权质心在参考纤维轴 \(\mathbf e_0\) 上的投影距离为广义位移：

\[
q(\mathbf x)=\mathbf e_0\cdot
\left(\sum_i w_i^+\mathbf x_i-\sum_i w_i^-\mathbf x_i\right),
\qquad q_0=L_0.
\]

该坐标的节点梯度为常量：

\[
\nabla_{\mathbf x_i}q=(w_i^+-w_i^-)\mathbf e_0.
\]

固定参考轴使弹簧和阻尼的功率端口明确，避免把细胞整体转动误计为轴向做功。

## 3. 外部弹性和黏性

外部弹簧：

\[
E_{\mathrm{ext}}^{e}=\frac12K_{\mathrm{ext}}(q-q_0)^2.
\]

外部阻尼：

\[
\mathcal D_{\mathrm{ext}}^{v}=C_{\mathrm{ext}}\dot q^2.
\]

作用于细胞、沿伸长方向为正的广义抵抗力为：

\[
F_{\mathrm{resist}}=K_{\mathrm{ext}}(q_0-q)-C_{\mathrm{ext}}\dot q.
\]

缩短阶段 \(\dot q<0\) 时，弹性项和黏性项均抵抗缩短；舒张阶段黏性项改变符号并抵抗伸长。

## 4. 无量纲标度

弹性标度取分布式纤维沿参考轴的小应变估计：

\[
K_0=\frac{k_f}{L_0^2}
\sum_e A_e\cos^4\theta_e.
\]

当前网格和参数下 \(K_0=10.0036\)。定义 \(K_{\mathrm{ext}}=\hat K K_0\)。

黏性标度取参考构型在均匀轴向速度模式下的细胞表面阻尼：

\[
C_0=\eta\sum_i w_i
\left[\frac{(\mathbf X_i-\mathbf X_c)\cdot\mathbf e_0}{L_0}\right]^2.
\]

当前模型下 \(C_0=0.279529\)。定义 \(C_{\mathrm{ext}}=\hat C C_0\)。

## 5. 工况矩阵

20步/周期、最多6周期筛选：

- 无外载：\((\hat K,\hat C)=(0,0)\)，复用既有结果；
- 纯弹性：\(\hat K=0.25,0.5,1,2\)，\(\hat C=0\)；
- 纯黏性：\(\hat C=0.25,0.5,1,2\)，\(\hat K=0\)。

40步/周期正式复核：

- 纯弹性代表工况 \((\hat K,\hat C)=(1,0)\)；
- 纯黏性代表工况 \((\hat K,\hat C)=(0,1)\)；
- 周期数采用20步筛选所需稳定周期再加一个完整周期，最少5周期、最多8周期；
- 无外载40步结果复用 `formal_40x5`。

## 6. 验收条件

### 6.1 退化和端口符号

- \(\hat K=\hat C=0\) 时必须退化为既有求解器；
- 弹簧能量和外部黏性耗散逐步非负；
- 缩短阶段外部黏性抵抗力为正，伸长阶段为负；
- 弹性抵抗力随缩短增加。

### 6.2 数值和几何

- 所有接受工况最大体积比误差不超过 `1e-8`；
- 最大动态KKT残差不超过 `1e-5`；
- 最小面面积比不低于0.05，无翻转或退化面；
- 物理耗散逐步非负；
- 正式工况按既有极限环定义连续两次周期转移通过。

### 6.3 能量

稳定周期满足：

- 逐步绝对能量缺陷占正主动输入不超过1%；
- 净主动功与“细胞内部黏性耗散 + 外部黏性耗散”之差，在扣除周期弹簧储能净变化后不超过1%；
- 纯弹性稳定周期的弹簧净储能变化接近零；
- 纯黏性工况外部耗散严格为正。

### 6.4 可检验趋势

- 随 \(\hat K\) 增大，稳定周期峰值缩短不得增加，峰值弹性抵抗力不得下降；
- 随 \(\hat C\) 增大，峰值缩短不得增加，相位延迟不得下降，外部黏性耗散不得下降；
- 20步与40步代表工况的峰值缩短和相位延迟差均不超过0.1个百分点；
- 若筛选最高负载造成的峰值缩短变化仍小于无载值的5%，则只能说明当前范围负载偏弱，不能宣称已覆盖等长极限。

## 7. 输出

- 求解器：`src/route_h/distributed_active_dynamics.py`
- 测试：`tests/stage2/test_distributed_active_dynamics.py`
- 脚本：`scripts/run_m1_dynamic_external_load_v01.py`
- 结果：`results/route_h/m1_dynamic_external_load_v01/`
- 阶段记录：`project_control/m1_dynamic_external_load_v01.md`

## 8. 范围外

- 显式ECM、心胶或黏附点空间分布；
- 恒力afterload、长度钳制和真实实验装置标定；
- 弹簧—阻尼组合扫描；
- 真实钙瞬变、Hill速度关系和长度依赖激活；
- 50%主动应变。
