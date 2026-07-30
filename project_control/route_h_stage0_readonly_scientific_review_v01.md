---
inspection_id: INSP-PRL-ROUTE-H-STAGE0-READONLY-V01
plan_id: PLAN-PRL-ROUTE-H-DCM-ECM-STAGE0-STAGE2-V01
execution_id: EXEC-PRL-ROUTE-H-STAGE0-V01
freeze_id: FREEZE-PRL-ROUTE-H-STAGE0-V01
inspector: Codex current task, same-agent read-only scientific review
independence: not_independent
inspected_at: 2026-07-29T09:07:58+08:00
status: revision_required
related_memory_entries: []
---

# Route H Stage 0 冻结合同只读科学检查 v01

## 结论

`revision_required`。

冻结合同的主动功率修订、中心力对、cohesive 势端点连续性和 ECM 内部变量耗散方向可以复推，
但当前文件仍不能无歧义地生成 Stage 1 的参考构形、接触算子和 Gate C/E 几何。Stage 1 必须
保持未授权。

本报告由原执行任务进行，只读且没有修改七个冻结产物，但不是独立 Inspector 结论，不能满足
计划中“独立检查”的最终门禁。

## Plan completion

- 七个冻结产物 SHA-256：7/7 与
  `project_control/route_h_stage0_freeze_record_v01.md` 一致；
- JSON/CSV：可解析；
- 15 个 case：全部保持 `not_run_unauthorized`；
- Stage 1、Stage 2：均为 `false`；
- solver、notebook、结果、图片：均未创建；
- 历史 continuum/v03/v06/Stage 4：没有成为 Route H 运行时依赖或 pass evidence。

## 通过的科学检查

### 1. 主动控制功率

对

\[
\Psi_{\rm act}=\frac12k_f(L_f-L_f^\star)^2
\]

有

\[
\frac{\partial\Psi_{\rm act}}{\partial L_f^\star}
=-k_f(L_f-L_f^\star).
\]

因此在

\[
\dot\Psi+D=P_{\rm ext}+P_{\rm active\ control}
\]

的右端输入约定下，

\[
P_{\rm active\ control}
=-k_f(L_f-L_f^\star)\dot L_f^\star.
\]

manufactured 值 \(k_f=10\)、\(L_f=1\)、\(L_f^\star=0.9\)、
\(\dot L_f^\star=-0.1\) 给出 \(P_{\rm active\ control}=0.1>0\)。冻结符号正确。

### 2. 锚点中心力对

采用

\[
d=c^+-c^-,
\qquad
L_f=\|d\|,
\qquad
f_{\rm current}=d/\|d\|
\]

时，两侧 resultant 沿同一中心线且等大反向，零净力、零净力矩。对
\(d=(1,0.2,0)\) 的数值复核给出净力矩
\(2.78\times10^{-17}\)，在浮点容差内为零。

### 3. 规则化 normal cohesive 势

对 \(0\le s=g/g_c\le1\) 使用

\[
q(s)=1-3s^2+2s^3
\]

时，\(q(0)=1\)、\(q(1)=0\)、\(q'(0)=q'(1)=0\)。normal 势在
\(g=0\) 和 \(g=g_c\) 处值与一阶导数连续；中间段
\(\partial\phi/\partial g>0\)，对应吸引；\(g<0\) 时
\(\partial\phi/\partial g=k_{\rm rep}g<0\)，对应排斥。标量势的分支符号成立。

### 4. ECM 能量与耗散方向

\[
W_{\rm eq}
=\frac{\mu_{\rm eq}}2(\operatorname{tr}\bar C-3)
+\frac{\kappa_{\rm eq}}2(\ln J)^2
\]

只依赖 \(C=F^TF\) 与 \(J\)，满足刚体客观性，并在 \(F=I\) 时为零。

若

\[
\eta_{\rm ve}\dot Z=-\frac{\partial W_{\rm ve}}{\partial Z},
\]

则

\[
D_{\rm ECM}
=-\frac{\partial W_{\rm ve}}{\partial Z}:\dot Z
=\eta_{\rm ve}\|\dot Z\|^2\ge0.
\]

耗散方向正确；但 \(Z(0)\) 尚未登记，见阻断问题 B1。

### 5. 端口与状态隔离

- 平面 canonical patch 假设下，\(n_{\rm lum}=-e_z\) 时
  \(t_p=-pn_{\rm lum}=pe_z\)；
- \(P_{\rm lum}=I-n_{\rm lum}\otimes n_{\rm lum}\) 可消除 WSS 法向分量；
- pressure/WSS 只拥有 endocardial apical port；
- \(A\) 与 \(H_{\rm ECM}\) 是不同字段，未启用密度闭合；
- \(\chi_E\) 不进入机械功率；
- \(j_{\rm myo}=0\)，只注册映射测试。

## Blocking findings

### B1 — 参考态与内部变量初始化不完整

当前合同登记了 \(V_0\)、face-type \(A_0\)、hinge \(\theta_0\)、两组 anchor patches 和
ECM 内部变量 \(Z\)，但 specialization 没有给出：

1. anchor patch 的材料面选择规则；
2. \(A_{0,s}\) 与 \(\theta_{0,e}\) 从参考网格生成和冻结的规则；
3. \(Z(0)\)；
4. reference mesh、face identity、anchor identity 的最终哈希；
5. rounded endocardial mesh 的实际体积与登记 \(V_0=0.25\) 如何一致。

后果：两个实现者可生成不同的锚点、预应力、初始黏弹应力和主动轴，却都声称符合 v01。

要求的 v02 修订：

- 参考面面积、hinge angle 和 \(V_0\) 默认取最终参考网格的精确离散值；
- 明确哪些 case 有意施加预应力，默认应为 stress-free；
- 冻结 anchor patch 的几何选择规则和最小分离阈值；
- 取 \(Z(0)=\operatorname{dev}\bar C(0)\)，除非另行登记预应力；
- 参考网格生成后、任何响应前记录 mesh/identity/anchor hashes。

### B2 — 动态排斥搜索与材料黏附配对被混为一个 pair 规则

合同同时规定：

- deterministic geometric candidate search；
- bound pair set 在轨迹前冻结；
- 轨迹中禁止 pair birth/death。

若该冻结规则也作用于 steric repulsion，初始不相邻的细胞后来接近时可能没有排斥 pair；
若只作用于 tangential tether，当前 schema 又没有把两类 pair 明确分开。

另外，`force on A=(d phi/dg)n` 只在 contact normal/contact point 固定时是完整梯度。
对随几何变化的 face–face gap，能量一致力必须是完整离散梯度

\[
f_A=-\nabla_{x_A}U_{\rm pair},
\qquad
f_B=-\nabla_{x_B}U_{\rm pair},
\]

包含 gap、normal、contact point、面积权重和 tangential projector 的位置导数。

要求的 v02 修订：

- `steric_candidate_pairs`：每步确定性更新，负责所有潜在碰撞；
- `material_adhesion_tethers`：结果前冻结并哈希，负责 basal shear transfer；
- 明确 tether 失活、重新接触和 cutoff 的能量/耗散处理；
- 力统一由完整 pair energy 的解析梯度或自动微分产生，不能只手写
  \((d\phi/dg)n\)。

### B3 — Gate C 的 support 与已登记 myocardium–ECM 界面冲突

合同登记：

```text
myocardium.basal_ecm <-> ECM.outer_facing
myocardium.opposite_outer <-> compliant surrounding myocardium
```

但 `C0_ZERO_SANDWICH` 与 `C1_ACTIVE_SANDWICH` 把 support 写为
`ECM outer compliant support`。这会让 ECM outer-facing 同时承担 myocardium adhesion
和环境 support，导致边界 owner 与功率 owner 重叠。

要求的 v02 修订：

- Gate C primary 将 compliant support 放在
  `myocardium.opposite_outer`；
- 若 sandwich 需要固定/支撑 ECM 的另一面，必须定义为独立 test fixture port，
  使用不同 surface identity，并单独进入功率账本；
- 同一面不得同时被 cell–ECM interface 和 environment support 拥有。

### B4 — 完整 patch 几何、曲率假设和边界分配不足

specialization 没有 `complete_patch` 定义。Gate E 目前缺少：

- endocardial/myocardial cell 数和面内排列；
- patch 的 \(L_x,L_y\)；
- ECM 面内范围、厚度方向节点分层和界面对齐规则；
- lateral 边界究竟是自由、compliant 还是 periodic；
- compliant support 具体作用于哪些 face identities；
- one-layer primary 与 two-layer sensitivity 的取舍；
- reference patch 是严格平面还是弯曲。

同时，\(n_{\rm lum}=-e_z\) 只能作为平面 canonical patch 的统一法向。若使用曲面 patch，
应改为各 apical face 的局部当前外法向 \(n_a\)，\(e_z\) 仅保留层次方向。

要求的 v02 修订：

- v01 numerical route 明确选择“平面 canonical patch”或“曲面 patch”之一；
- 若选择平面 route，冻结 exact cell tiling、patch dimensions、ECM mesh layout 和
  face-owner map；
- Gate E 的 `support: compliant` 必须展开成精确 surface identity 和端口；
- periodic 只保留为同几何、同参数的 sensitivity case。

## Unapproved changes

无。检查没有修改冻结合同、specialization、cases、ledger、registry、坐标文件或用户决定记录。
本报告是唯一新增文件。

## Evidence and quality boundary

- 本检查支持核心主动功率符号和中心力对，但不构成数值验证；
- cohesive 势只验证了标量分支与端点连续性，完整离散接触力尚未定义；
- ECM 耗散只验证了 gradient-flow 方向，未验证离散积分或 time stepping；
- 没有生成任何 response，因此不存在 parameter tuning 或结果后选择。

## Required memory updates

无。未授权 stable Memory。

## Remaining risks and next gate

Stage 0 v01 保持 frozen 作为历史版本，但 inspection 状态为 `revision_required`。

若用户决定继续，应只授权创建 Stage 0 v02，修复 B1–B4 并重新冻结；该授权不得被解释为
Stage 1、solver、mesh generation、case execution 或独立 inspection 授权。

