---
decision_id: DEC-PRL-ROUTE-H-STAGE2-NUMERICAL-METHOD-V01
status: superseded_preexecution
decider: Codex numerical selection within user-approved Stage 2 scope
decided_at: 2026-07-31T10:30:00+08:00
stage2_authorization: DEC-PRL-ROUTE-H-STAGE2-AUTHORIZATION-V01
effective_contract: CONTRACT-PRL-ROUTE-H-STAGE0-V06
effective_freeze: FREEZE-PRL-ROUTE-H-STAGE0-V06-V02
response_runs_before_decision: 0
superseded_by: DEC-PRL-ROUTE-H-STAGE2-NUMERICAL-METHOD-V02
---

# Route H Stage 2 数值方法与 Gate A 客观指标决定 v01

> 预执行处置：本版在非注册短轨迹 preflight 中因 SciPy `ftol` 提前停止而淘汰，
> 未运行任何正式 A0/A1 response；由 v02 取代，不得用于正式结果。

## 1. 决定边界

v06 v02 已关闭 PreStage2 discretization block。v06 specialization 要求在 Stage 1
获批后、任何 Stage 2 response 前选择一个 implicit overdamped family。本决定在
Gate A response 数为 0 时锁定该 family；后续不能按结果改变。

本决定不改变方程、无量纲参数、载荷、接触、时间步、阈值或 Gate 顺序。

## 2. Fully implicit backward Euler

对只有保守内力和 nodal drag 的 Gate A，每个时间步在全局六约束零功率 gauge 的
null-space 内求

\[
x_{n+1}=\arg\min_x\left[
\Psi_{\rm passive}(x)+\Psi_{\rm active}(x,t_{n+1})
+\frac{\zeta}{2\Delta t}\sum_i w_i\|x_i-x_{n,i}\|^2
\right].
\]

其中：

- \(\zeta=1\)，保持冻结的 myocardial nodal drag；
- \(w_i\) 是 v06 base bundle 封存的 reference vertex dual-area weights；
- gauge matrix \(G\) 使用相同 reference weights；
- 每步严格施加 \(G(x_{n+1}-x_n)=0\)；
- null-space basis 由 binary64 SVD 一次确定，之后固定；
- 增量势解析梯度为
  \(-f_{\rm passive}-f_{\rm active}
  +\zeta w(x_{n+1}-x_n)/\Delta t\)；
- 使用 SciPy L-BFGS-B 在 null-space coordinates 中求解；
- 为避免 SciPy 的相对函数下降停止式在无量纲势能远小于 1 时提前满足，传给
  optimizer 的 objective 与 analytic gradient 同时固定乘以 `1e8`
  （即 projected-residual gate `1e-8` 的倒数）；该正比例缩放不改变极小点，
  physical residual 仍用未缩放量计算；
- 固定 `maxiter=200`、`maxls=40`、`maxcor=20`、`ftol=1e-13`、
  `gtol=1e-9`；
- projected overdamped residual 必须
  `<=1e-8`，比注册的 static-equilibrium `1e-6` 更严格；
- gauge increment residual 必须 `<=1e-12`；
- 非有限量、optimizer failure 且残差未通过、体积退化或未达到上述残差时，
  case 状态为 `invalid_numerics` 并停止 Gate A。

Gate A 不使用 adaptive time step、response-dependent retry、parameter sweep 或
阈值修改。固定运行 `dt=0.02, 0.01, 0.005`；base report 使用 `0.01`，time-refinement
正式比较 `0.01` 与 `0.005`。

上述 objective scaling 由 `duration=1.2, dt=0.02` 的非注册 solver preflight
发现并在任何正式 A0/A1 case 运行前锁定；该 preflight 不进入 response 指标或
Gate A 验收。正式运行后禁止再改 scaling。

后续含非保守 blood load/contact 的 gate 仍属于同一 fully implicit backward-Euler
family，但必须在进入相应 gate 前用该 gate 的 manufactured residual tests 固定其
非保守 residual assembly；本决定不提前运行它们。

## 3. 主动 preferred-length 离散

固定 reference area-barycentric anchor weights：

\[
c^\pm=\sum_i w_i^\pm x_i,\quad
d=c^+-c^-,\quad L_f=\|d\|,\quad f=d/L_f .
\]

\[
L_f^\star=L_{f0}[1-\alpha(t)],\qquad
\Psi_{\rm active}=\frac12k_f(L_f-L_f^\star)^2.
\]

主动输入功率保持合同符号：

\[
P_{\rm active}
=\frac{\partial\Psi_{\rm active}}{\partial L_f^\star}\dot L_f^\star
=-k_f(L_f-L_f^\star)\dot L_f^\star .
\]

必须通过 analytic directional derivative、zero net force、zero net moment、rigid
objectivity 和 power-sign manufactured tests。

## 4. Gate A 客观 response metrics

### 轴向

\[
q_{\rm axial}(t)=1-L_f(t)/L_{f0};
\]

报告全轨迹最大值。通过范围保持 `[0.01,0.20]`。

### 两个横向尺度

使用冻结 dual-area weights 计算当前 weighted centroid 与 covariance \(C\)。令当前
主动轴为 \(f\)，\(P=I-f\otimes f\)，取 \(PCP\) 的两个正本征值
\(\lambda_1\ge\lambda_2\)，与 reference 状态对应排序本征值比较：

\[
s_k(t)=\sqrt{\lambda_k(t)/\lambda_{k0}}-1,\quad k=1,2.
\]

该定义对整体平移和旋转客观。Gate A 在 peak-activation plateau 的固定末端节点
`t=3.0` 评价两个尺度：两者均须非负（容差 `-1e-10`），至少一个须
`>0.01`。该节点定义在任何 response 运行前锁定，不从轨迹中择优挑选。

### 体积与刚体漂移

- volume error：`max_t |V(t)/V0-1| <=0.005`；
- centroid drift：冻结 dual-area centroid 相对 reference 的最大位移除以 `Lf0`，
  必须 `<=1e-4`；
- active force/moment residual：均 `<=1e-10`。

### 账本

节点速度在 `t_{n+1}` 定义为 backward increment
`(x_{n+1}-x_n)/dt`，`t0` 速度为 0。每个 accepted time node 记录：

- passive/active stored energy；
- \(D_{\rm cell}=\zeta\sum_iw_i\|v_i\|^2\)；
- \(P_{\rm active}\)；
- gauge power（必须为 0）。

沿冻结时间节点使用 composite trapezoidal rule，integrated normalized power
residual 必须 `<=0.005`。各耗散必须 `>=-1e-10`。

## 5. Time refinement

对 `dt=0.01` 与 `0.005` 比较：

- peak axial shortening；
- plateau 两个 transverse scale changes；
- maximum volume error；
- integrated active work；
- total dissipation；
- integrated normalized power residual（零目标残差；两档分别按 `<=0.005`
  绝对门槛验收，其档间差异只作诊断，不对接近零的残差作相对除法）。

非零量使用合同冻结公式
`|q_0.01-q_0.005|/max(1e-8,|q_0.01|,|q_0.005|)` 并要求 `<=0.02`；
net force、net moment、centroid drift、gauge residual、integrated normalized power
residual 等零目标量继续使用各自绝对阈值。

## 6. 停机条件

以下任一情况判 Gate A 失败并阻断 Gate B：

1. preferred-length analytic force/power/zero-moment test 失败；
2. A0 不能保持 reference zero state；
3. A1 轴向、横向、体积、漂移、残差、耗散、功率或 time-refinement 任一阈值失败；
4. 只有改变 \(k_f\)、\(\alpha_{\rm peak}\)、被动参数、drag、时间步、metric 或 optimizer
   tolerance 才能通过；
5. 需要换用主动应力、主动曲率或内部纤维等新机制。
