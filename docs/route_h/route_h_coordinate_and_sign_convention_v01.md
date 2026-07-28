---
document_id: COORD-SIGN-PRL-ROUTE-H-STAGE0-V01
contract_id: CONTRACT-PRL-ROUTE-H-STAGE0-V01
status: frozen_stage0_pending_independent_inspection
created_at: 2026-07-28T16:04:19+08:00
---

# Route H 坐标、法向、牵引与主动功率约定 v01

## 1. 适用边界

本文只冻结 Route H 的坐标、载荷端口和功率符号。它不实现求解器，不产生数值轨迹，
也不把历史 continuum、v03、v06 或 Stage 4 结果升级为 DCM–ECM 证据。

## 2. 右手坐标与层次

参考构形采用右手基底 \((e_x,e_y,e_z)\)：

- \(e_z\) 从 lumen 指向外侧心肌；
- \(e_x\) 是参考状态的主要心肌面内材料方向；
- \(e_y=e_z\times e_x\)。

从 lumen 到外侧依次为：

```text
blood lumen
→ explicit endocardial DCM cells
→ independent finite-deformation cardiac-jelly ECM
→ explicit active myocardial DCM cells
→ compliant surrounding myocardium
```

每个细胞都是独立、闭合、watertight、定向一致的三角曲面。细胞之间、细胞与 ECM
之间不共享顶点。面类型是材料身份，不能在看到结果后依据瞬时法向或接触对象重贴标签。

## 3. 心内膜顶面法向与血压

心内膜细胞的曲面外法向在 lumen-facing apical face 上定义为

\[
n_{\rm lum}=-e_z.
\]

若 \(p\ge0\) 是血液对壁面的压强幅值，则作用在固体 apical face 上的牵引是

\[
t_p=-p\,n_{\rm lum}=p\,e_z.
\]

对三角面 \(a\)，采用一致的一点面平均离散：

\[
f_{p,a\to i}=\frac{A_a}{3}t_{p,a},
\qquad i\in a.
\]

因此平面 patch 的压力 resultant 必须纯法向。血压只拥有
`endocardium.apical_lumen` 端口，ECM 没有直接血压端口。

## 4. 壁面剪切

定义 apical 切平面投影

\[
P_{\rm lum}=I-n_{\rm lum}\otimes n_{\rm lum}.
\]

WSS 牵引是

\[
t_\tau=P_{\rm lum}\tau_w,
\qquad
f_{\tau,a\to i}=\frac{A_a}{3}t_{\tau,a}.
\]

WSS resultant 的法向分量必须在数值容差内为零。WSS 同样只作用于心内膜 apical face；
它通过心内膜细胞、细胞连接及 basal adhesion 向 ECM 传递。

## 5. 面功率

令三角面平均速度

\[
v_a=\frac{v_i+v_j+v_k}{3}.
\]

两个机械端口分别登记：

\[
P_p=\sum_{a\in\Gamma_{\rm apical}}A_a\,t_{p,a}\cdot v_a,
\qquad
P_\tau=\sum_{a\in\Gamma_{\rm apical}}A_a\,t_{\tau,a}\cdot v_a.
\]

压力和 WSS 不合并成一个“血流功率”，从而可以审计方向、消融和双重计数。

## 6. 内部接触与黏附

对任一 cell–cell 或 cell–ECM 配对，A、B 两侧的力必须由同一个配对势产生：

\[
f_A=-f_B.
\]

配对力只在局部子系统之间传递功率；对整个 patch 求和时它不是外功。v01 primary
采用规则化势，不使用硬接触 KKT 作为主路线。最大穿透是验收指标，不能被解释为允许穿透。

basal 切向传力来自材料配对的保守切向 tether；不得为获得预期法向响应而另加人工
法向 \(q\)。

## 7. 主动 preferred-length：发现的符号冲突

v01 计划写为

\[
\Psi_{\rm act}=\frac12k_f(L_f-L_f^\star)^2,
\qquad
L_f^\star=L_f^0(1-\alpha),
\]

并把主动功率写成

\[
P_{\rm act}^{\rm plan}
=-\frac{\partial\Psi_{\rm act}}{\partial L_f^\star}\dot L_f^\star.
\]

但是若总能量写成 \(\Psi(q,L_f^\star)\)，内部力为
\(f_{\rm int}=-\partial_q\Psi\)，则

\[
\dot\Psi
=-f_{\rm int}\cdot\dot q
+\frac{\partial\Psi}{\partial L_f^\star}\dot L_f^\star.
\]

在

\[
\dot\Psi+D=P_{\rm ext}+P_{\rm active\ control}
\]

的右端输入功率约定下，应有

\[
P_{\rm active\ control}
=\frac{\partial\Psi_{\rm act}}{\partial L_f^\star}\dot L_f^\star
=-k_f(L_f-L_f^\star)\dot L_f^\star.
\]

激活缩短阶段通常有 \(L_f>L_f^\star\)、\(\dot L_f^\star<0\)，所以上式为正输入功率。
计划原式在同一状态下为负，不能同时作为右端“输入功率”。

因此本项尚未冻结。建议采用无前导负号的右端输入功率定义；若用户希望保留计划原式，
则必须把它改名为 actuator extraction power，并以相反符号进入总账。

## 8. 主动双锚点：发现的净力矩冲突

计划定义

\[
L_f=(c^+-c^-)\cdot f
\]

并要求锚点力零净力、零净力矩。若 \(f\) 固定，锚点质心上的等大反向力沿 \(f\)：

\[
f_+=-\lambda f,\qquad f_-=\lambda f,
\]

则净力为零，但净力矩为

\[
M=(c^+-c^-)\times(-\lambda f),
\]

只有当 \(c^+-c^-\parallel f\) 时才为零。一般变形后这一条件不自动成立。

建议用材料锚点身份定义轴线，并采用

\[
d=c^+-c^-,
\qquad
L_f=\|d\|,
\qquad
f_{\rm current}=\frac{d}{\|d\|}.
\]

这样锚点力是中心力对，天然满足零净力与零净力矩，同时允许轴线随刚体转动客观更新。
参考材料方向仍由两组锚点身份保存，不依赖结果后重贴标签。

## 9. Orientation-reversal manufactured checks

Stage 1 前必须预先实现但当前不得运行以下检查：

1. 反转三角面节点顺序后，几何预处理应恢复一致外法向；物理压力牵引不变。
2. 将整个 patch 做刚体旋转，所有保守能量不变，压力/WSS resultant 同步旋转。
3. 将 \(e_x\) 与 WSS 一起旋转，切向投影后不得产生法向泄漏。
4. 主动锚点轴整体刚体旋转后，\(L_f\)、主动能和主动功率不变。
5. 所有内部配对在全局求和后净力与净力矩为零。

## 10. 冻结决定与当前门禁

用户于 2026-07-28 明确批准：

- 右端主动输入功率采用
  \(\partial\Psi/\partial L_f^\star\,\dot L_f^\star\)；
- 主动长度采用锚点质心距离 \(\|c^+-c^-\|\)，使锚点力成为中心力对。

因此本坐标与符号合同已在 Stage 0 冻结。该冻结不等于独立科学 inspection，也不授权
Stage 1；在另行批准前不得实现求解器。
