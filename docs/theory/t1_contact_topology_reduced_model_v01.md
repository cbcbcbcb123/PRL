---
theory_id: THEORY-PRL-T1-CONTACT-TOPOLOGY-REDUCED-MODEL-V01
status: working_draft_for_human_figure_gate
scope: analytical_contact_topology_test
evidence_level: reduced_theory_not_dcm_fem_simulation
contract: project_control/t1_figure2_contact_topology_contract_v01.md
---

# T1 v01：单侧接触为何不同于对称包埋

## 1. 核心发现

接触面积分数 \(\phi_A\) 和法向二阶矩 \(\mathbf M_A\) 不能完整表示“哪一侧接触”。因为 \(\mathbf n\otimes\mathbf n\) 对 \(\mathbf n\to-\mathbf n\) 不变，二阶矩会丢失上下/内外的有符号极性。

需要同时定义刚度加权极性向量

\[
\mathbf p_K
=\frac{1}{K_\Gamma^{\mathrm{eff}}}
\int_{\Gamma_{\mathrm{ECM}}}
k_\Gamma(\mathbf x)\,\mathbf n(\mathbf x)\,dA.
\]

全周或反射对称包埋通常有 \(\mathbf p_K\simeq\mathbf0\)；单侧基底接触则有 \(\mathbf p_K\ne\mathbf0\)。因此 T0 的 \(\phi_A+\mathbf M_A\) 是必要但可能不充分的描述，Figure 1 暂定稿需要保留修订接口。

## 2. 最小伸长—弯曲模型

把细胞约化为厚度 \(2a\) 的主动细长体：

- 中性面轴向应变：\(\varepsilon\)；
- 主动本征应变：\(\varepsilon_a(t)<0\)；
- 曲率：\(\kappa\)，无量纲曲率 \(\widehat\kappa=a\kappa\)；
- 轴向刚度：\(S\)；
- 弯曲刚度：\(B\)；
- 基底/负侧接触刚度：\(K_-\)；
- 顶侧/正侧接触刚度：\(K_+\)。

上下两侧的轴向变形分别为 \(\varepsilon+\widehat\kappa\) 和 \(\varepsilon-\widehat\kappa\)。总能量取

\[
\Psi
=\frac12S(\varepsilon-\varepsilon_a)^2
+\frac12\frac{B}{a^2}\widehat\kappa^2
+\frac12K_-(\varepsilon+\widehat\kappa)^2
+\frac12K_+(\varepsilon-\widehat\kappa)^2.
\]

定义

\[
K=K_-+K_+,
\qquad
m=\frac{K_--K_+}{K}\in[-1,1],
\]

其中 \(m\) 是两侧模型中的有符号接触极性：

- 单侧基底接触：\(m=1\)；
- 对称两侧包埋：\(m=0\)；
- 单侧顶面接触：\(m=-1\)。

能量展开为

\[
\Psi
=\frac12S(\varepsilon-\varepsilon_a)^2
+\frac12\frac{B}{a^2}\widehat\kappa^2
+\frac12K\left(
\varepsilon^2+\widehat\kappa^2
+2m\varepsilon\widehat\kappa
\right).
\]

关键交叉项是 \(Km\varepsilon\widehat\kappa\)。对称包埋因 \(m=0\) 严格消去该项；单侧接触破坏反射对称性，允许主动缩短诱发弯曲。

## 3. 闭式解

定义两个无量纲参数

\[
\Lambda=\frac{K}{S},
\qquad
\beta=\frac{B}{Sa^2}.
\]

能量极小条件给出

\[
\begin{bmatrix}
1+\Lambda & \Lambda m\\
\Lambda m & \beta+\Lambda
\end{bmatrix}
\begin{bmatrix}
\varepsilon\\
\widehat\kappa
\end{bmatrix}
=
\begin{bmatrix}
\varepsilon_a\\
0
\end{bmatrix}.
\]

稳定性行列式为

\[
\Delta=(1+\Lambda)(\beta+\Lambda)-\Lambda^2m^2>0.
\]

在 \(\Lambda>0\)、\(\beta>0\)、\(|m|\le1\) 时该最小模型保持正定。闭式解为

\[
\boxed{
\frac{\varepsilon}{\varepsilon_a}
=\frac{\beta+\Lambda}{\Delta}
},
\qquad
\boxed{
\frac{\widehat\kappa}{\varepsilon_a}
=-\frac{\Lambda m}{\Delta}
}.
\]

## 4. 配对预测

### 4.1 对称包埋

\[
m=0:
\qquad
\frac{\varepsilon}{\varepsilon_a}=\frac{1}{1+\Lambda},
\qquad
\widehat\kappa=0.
\]

等效环境只能抑制轴向缩短，不诱发确定方向的弯曲。

### 4.2 单侧接触

\[
m=1:
\qquad
\frac{\varepsilon}{\varepsilon_a}
=\frac{\beta+\Lambda}{\beta(1+\Lambda)+\Lambda},
\]

\[
\frac{\widehat\kappa}{\varepsilon_a}
=-\frac{\Lambda}{\beta(1+\Lambda)+\Lambda}.
\]

由于细胞可以通过弯曲释放部分对称轴向约束，在相同总 \(K\) 下，单侧接触的轴向缩短幅度不小于对称包埋。相对于对称包埋的缩短增益为

\[
\frac{(\varepsilon/\varepsilon_a)_{m=1}}
{(\varepsilon/\varepsilon_a)_{m=0}}-1
=\frac{\Lambda^2}{\beta(1+\Lambda)+\Lambda}.
\]

该增益在细胞容易弯曲（\(\beta\) 小）且 ECM 约束显著（\(\Lambda\) 大）时最强。

## 5. 必须成立的极限

1. \(\Lambda\to0\)：\(\varepsilon\to\varepsilon_a\)、\(\widehat\kappa\to0\)，恢复自由主动细胞；
2. \(m\to0\)：伸长—弯曲交叉项消失；
3. \(\beta\to\infty\)：弯曲受抑，单侧与对称包埋的轴向响应趋同；
4. \(m\to-m\)：缩短幅度不变、曲率方向反转；
5. 相同 \(K\) 下改变 \(m\) 才是拓扑比较，若同时改变 \(K\) 就不能把差异归因于接触极性。

## 6. Figure 2 v01 的可证伪主张

> 在总接触刚度匹配时，单侧 ECM 接触因破坏反射对称性而产生伸长—弯曲耦合；对称包埋不产生该一阶耦合。拓扑效应由有符号接触极性控制，而不能只由接触面积或无符号二阶法向矩表示。

未来固定拓扑 DCM–FEM 配对算例应检验：

- 单侧接触是否产生稳定方向的细胞弯曲和偏心牵引；
- 翻转接触面是否翻转曲率而基本保持缩短幅度；
- 提高细胞弯曲刚度是否使单侧和包埋响应收敛；
- 匹配总界面刚度后，接触极性是否仍提高持出工况的预测能力。

## 7. 证据边界

本模型是小应变、两侧弹性基础上的解析约化，不是三维 DCM–FEM 结果。它没有描述真实细胞横向截面、黏附点离散性、非线性接触、体积约束、ECM 三维变形或黏性相位。其作用是提出最小对称性机制和可否证趋势，而不是给出真实斑马鱼心肌细胞的定量曲率。

