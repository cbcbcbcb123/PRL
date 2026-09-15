---
decision_id: DEC-PRL-ROUTE-H-STAGE0-ACTIVE-SIGN-AXIS-V01
status: approved
decider: user
decided_at: 2026-07-28T16:15:31+08:00
related_plan: PLAN-PRL-ROUTE-H-DCM-ECM-STAGE0-STAGE2-V01
related_inspection:
memory_target:
---

# Route H Stage 0 主动机制的两个阻断性决定

## 背景

用户已授权开始 Stage 0，但未授权 Stage 1 求解器或 Stage 2 数值计算。Stage 0 复核发现，
v01 计划的主动 preferred-length 段落有两个在实现前必须解决的内部一致性问题。

## 决定 1：主动控制输入功率的符号

计划采用

\[
\Psi_{\rm act}=\frac12k_f(L_f-L_f^\star)^2
\]

并把主动功率写为

\[
-\frac{\partial\Psi_{\rm act}}{\partial L_f^\star}\dot L_f^\star.
\]

若主动功率位于

\[
\dot\Psi+D=P_{\rm ext}+P_{\rm active\ control}
\]

的右端，则能量链式法则要求

\[
P_{\rm active\ control}
=\frac{\partial\Psi_{\rm act}}{\partial L_f^\star}\dot L_f^\star
=-k_f(L_f-L_f^\star)\dot L_f^\star.
\]

在 preferred length 缩短阶段，\(L_f>L_f^\star\) 且
\(\dot L_f^\star<0\)，该量为正，符合“控制器向系统输入功率”的含义。

建议决定：

> 右端主动输入功率采用
> \(P_{\rm active\ control}
> =(\partial\Psi_{\rm act}/\partial L_f^\star)\dot L_f^\star\)。

## 决定 2：主动轴线与零净力矩

若

\[
L_f=(c^+-c^-)\cdot f
\]

且 \(f\) 固定，则等大反向锚点力一般会产生

\[
M=(c^+-c^-)\times(-\lambda f)\ne0.
\]

这与计划要求的零净内部力矩不兼容。

建议决定：

\[
d=c^+-c^-,
\qquad
L_f=\|d\|,
\qquad
f_{\rm current}=d/\|d\|.
\]

两组材料锚点身份仍然固定，但当前轴线随锚点做客观转动；锚点力成为中心力对，因此零净力、
零净力矩。

建议决定：

> 主动长度采用两组材料锚点的质心距离
> \(L_f=\|c^+-c^-\|\)，当前主动轴为
> \(f_{\rm current}=(c^+-c^-)/L_f\)。

## 文件结构偏差

用户清理并批准了新的最简项目骨架。原计划中的旧 `03_分析与代码/...` 输出路径已不存在，
本次 Stage 0 使用以下等价映射：

| 原语义 | 当前路径 |
|---|---|
| 模型合同和特化 | `src/route_h/` |
| 预注册 cases | `data/route_h/` |
| 坐标、符号和功率账本 | `docs/route_h/` |
| 验证注册表 | `tests/route_h/` |
| 执行与决定记录 | `project_control/` |

该映射不改变模型方程或授权边界。

## 用户决定

用户于 2026-07-28 明确回复：

> 确认采用两个 Stage 0 修订并冻结 Stage 0；暂不授权 Stage 1

因此两个决定均已生效：

- 合同采用修订后的主动输入功率符号；
- 合同采用锚点质心距离和随动中心轴；
- Stage 0 标记为 frozen；
- Stage 1、Stage 2 及全部 case 仍未授权；
- 本次冻结不冒充独立科学 inspection。
