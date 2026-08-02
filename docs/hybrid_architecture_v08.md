---
architecture_id: ARCH-PRL-HYBRID-V08
status: frozen_x1_e_active_mechanics_port
frozen_at: 2026-08-02
inherits_interface: ARCH-PRL-HYBRID-V07
cell_engine_commit: 1ae6b27c785b3d4eabff136e3c8c588c2abc76ab
---

# PRL 自有长期混合架构 v08

本版本冻结 X1-E：单细胞心肌主动收缩已形成自有 C++17 最小力学闭环。它把持久材料点上的激活状态和纤维方向，转换为可审计的主动能量、顶点力与激活输入功率，并通过真实 `local_mesh_refiner` 验证重网格前后语义不变。

## 主动收缩路径

```text
frozen C1 activation protocol
        │ [alpha, alpha_rate]
        ▼
revision-safe material-point state update
        │ persistent material-point ID + fiber director
        ▼
preferred-length contraction unit
        │ persistent minus/plus anchors + fixed reference length
        ▼
active energy / input power / central anchor-force pair
        │ barycentric scatter through current hosts
        ▼
persistent-vertex nodal forces + conservation audit
        │
        └── real local_mesh_refiner event
              → material rebind → same contraction-unit semantics
```

## 冻结的主动机制

X1-E 沿用 Route H 已冻结的 preferred-length 机制，不切换为 active stress、active strain 或 active curvature：

\[
L_f=\|c_+-c_-\|,\qquad
L_f^*=L_{f0}(1-\alpha),
\]

\[
\Psi_f=\tfrac12 k_f(L_f-L_f^*)^2,\qquad
P_{\mathrm{act}}=-k_f(L_f-L_f^*)\dot L_f^*.
\]

`c_-` 与 `c_+` 由两个持久材料点的当前宿主三角形和重心坐标确定；`L_f0` 在 contraction unit 建立时冻结，不随之后的重网格改变。中央力对先作用于材料点锚点，再按当前重心坐标散射到 persistent vertex ID，因此理论合力与合矩为零。

激活状态固定为 `[alpha, alpha_rate]`，由 controller material point 持有；`alpha` 必须在 `[0, 0.2]` 内。C1 protocol 为：`t<1` 静息、`1≤t<2` 余弦上升、`2≤t<3` 平台、`3≤t<4` 余弦释放、`t≥4` 归零，并支持只作时间平移的 delay。

## 身份、版本与失败语义

- contraction unit、材料点和表面顶点各自拥有稳定 ID；拓扑局部编号不是生物学身份。
- `update_active_state` 必须携带 expected mesh revision；陈旧 revision、未知材料点或非有限状态均在提交前拒绝。
- 主动力学求值要求 mesh 与 material 的 cell ID、revision 完全相等。
- controller 纤维必须非零，当前锚点轴与纤维方向的绝对夹角余弦不得低于 unit 冻结阈值。
- 每次求值输出总能量、输入功率、合力残差、合矩残差、最小轴—纤维对齐度和最大激活度。
- remesh callback 失败仍沿用 v06 的 fatal-step 语义：拓扑编辑不回滚，上层必须终止该步并由检查点恢复。

## X1-E 验证边界

制造解在 `L_f0=L_f=0.5`、`k_f=10`、`t=1.5`、`alpha_peak=0.1` 下得到：`alpha=0.05`、`L_f*=0.475`、`Psi_f=0.003125`、`P_act=0.00625*pi`。主动顶点力与能量方向导数的相对误差不超过 `1e-9`；刚体旋转和平移下能量、功率与旋转后的力在 `1e-14` 容差内一致。

真实 edge swap 测试使用同一冻结 contraction unit：mesh/material revision 从 0 同步推进到 1，重网格前后锚点长度、优选长度、主动能量和输入功率差均不超过 `1e-12`，且合力、合矩残差不超过 `1e-12`。

## 未宣告与下一切片

X1-E 冻结的是主动**力学端口**，不是已经发生收缩位移的完整时间轨迹。它尚未把主动节点力注入 cell engine 的被动力/阻尼装配，也没有求解几何更新、接触、体积 ECM 或血流。Route H Stage 2 Gate A 的 `failed_invalid_numerics` 历史结论保持不变，X1-E 不能解释为 Gate A 已恢复通过或得到生理结论。

下一安全切片为 X1-F：只建立主动节点力进入 cell force assembly 的单步注入 seam 和功率账本，先验证单步符号、版本与失败传播；不直接启动长轨迹，也不同时接入 ECM 或血流。
