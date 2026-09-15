# Route H Stage 0 v02 — 坐标、法向、接触与功率符号约定

## 1. 状态与适用范围

- 文档状态：`frozen_stage0_pending_independent_inspection`
- 合同：`CONTRACT-PRL-ROUTE-H-STAGE0-V02`
- 参考几何：`GEOMETRY-PRL-ROUTE-H-STAGE0-V02`
- 证据级别：无量纲机制合同；没有网格实例、求解器或数值结果。
- Stage 1：**未授权**。本文只冻结定义，不能据此开始实现或计算。

## 2. 参考坐标和层次

采用右手正交基：

- `e_x=(1,0,0)`：参考态心肌细胞主轴；
- `e_y=(0,1,0)`：第二个面内方向；
- `e_z=(0,0,1)`：从心腔指向外侧心肌。

主模型是平坦局部贴片。按 `z` 从小到大依次为：血腔、心内膜 DCM 单层、独立 ECM 薄体、心肌 DCM 单层、顺应性周围心肌。曲面贴片不属于 v02；若引入曲率，必须建立新的几何版本。

冻结的完整贴片范围为：

`x∈[0,3]`，`y∈[0,1.8]`，`z∈[-0.24,0.76]`。

心内膜顶端参考外法向为 `n_lum0=-e_z`。所有材料面身份在参考网格上一次性赋值，之后不得依据变形后的朝向重标。

## 3. 当前法向与血流载荷

设 `n_a(x)` 为由当前、保持一致定向的心内膜顶端三角面计算的外法向。

压力 `p_hat≥0` 的随形牵引为

`t_p=-p_hat n_a(x)`。

因此在平坦参考态，`t_p=+p_hat e_z`，即压力把心内膜推向 ECM。压力只能作用于 `endocardium.apical_lumen`；不得直接施加在 ECM 上。

壁面剪切应力采用当前切向投影：

`t_tau=[I-n_a(x)⊗n_a(x)] tau_w_hat`。

它同样只能作用于 `endocardium.apical_lumen`。必须分别检查压力的切向泄漏和 WSS 的法向泄漏。

端口功率统一定义为“外界对模型做功为正”：

`P_pressure=Σ A_face t_p·v_face`，

`P_WSS=Σ A_face t_tau·v_face`。

## 4. 主动首选长度

每个心肌细胞有两个冻结的材料锚定面集 `Gamma_minus` 与 `Gamma_plus`。采用固定的参考三角面积及其三分之一节点重心权重，计算当前材料点的加权质心 `c_minus` 和 `c_plus`：

`d=c_plus-c_minus`，

`Lf=||d||`，

`f=d/Lf`，

`Lf_star=Lf0(1-alpha(t))`。

主动能为

`Psi_active=0.5 kf (Lf-Lf_star)^2`。

该形式产生沿 `d` 的等大反向中心力，因此净内力和净内力矩均为零。主动控制器位于功率等式右端，其输入功率冻结为

`P_active=(∂Psi_active/∂Lf_star) Lf_star_dot`

`=-kf(Lf-Lf_star)Lf_star_dot`。

不能再次取负号。`gamma_s` 在 v02 中全部为零，也不得承担主动收缩。

## 5. 无预应力参考态

参考网格实例一旦获准生成，必须从最终定向网格直接登记：

- 每个细胞的精确 `V0`；
- 每类材料面的精确 `A0`；
- 每条铰链的精确 `theta0`；
- 每个心肌细胞的锚定面 ID、质心和 `Lf0`；
- ECM 的 `F0=I`、`J0=1` 与 `Z0=dev(C_bar0)=0`。

所有注册界面的参考间隙均为零；黏附法向势在 `g=0` 的导数为零；切向材料滑移为零；支撑参考点等于参考节点位置；`alpha=0` 时 `Lf_star=Lf0`。这些条件与 `gamma_s=0` 一起定义无预应力参考态。

任何求解器或响应之前，必须封存顶点、定向面、面身份、锚点、ECM 四面体、边界身份、材料黏附配对与支撑所有者的 SHA-256。v02 不授权生成这些实例。

## 6. 接触与黏附的两套配对

### 6.1 动态排斥配对

排斥候选在每个接受状态重新进行确定性几何搜索。其势为

`phi_rep=0.5 k_rep max(-g,0)^2`。

动态配对只承担防穿透，不产生黏附；后来接近的表面只能获得排斥，不能自动形成新黏附。

### 6.2 冻结材料黏附配对

黏附配对由参考几何按“相互最近 + 字典序破同距”建立，在整条轨迹内冻结并哈希。不得出生、死亡或转移所有者。

法向黏附势为：

- `g<0`：`phi_adh_n=-w_adh`；
- `0≤g≤g_c`：`phi_adh_n=-w_adh(1-3s^2+2s^3)`，`s=g/g_c`；
- `g>g_c`：`phi_adh_n=0`。

主面由实体—面—积分点 ID 的字典序确定。用当前主面两条有向边构造确定性正交切向基 `t1,t2`。若 `r` 是从主材料点到从材料点的当前分离，材料滑移为

`delta_t=[r·t1-r0·t10, r·t2-r0·t20]`。

切向势为

`phi_adh_t=0.5 k_t a(g)||delta_t||^2`，

其中 `a(g)=1`（`g<0`），在 `0≤g≤g_c` 采用同一三次函数，超过截止距离为零。整体刚体运动下 `delta_t=0`。

每个离散配对力必须是对应势对所有参与节点坐标的**完整负梯度**，包括间隙、法向、材料/最近点、插值权重、投影和切向基的导数。可用解析微分或自动微分，但必须通过方向导数检验。

## 7. ECM 符号

`F` 为有限变形梯度，`C=F^T F`，`J=det(F)>0`，`C_bar=J^(-2/3)C`。

`W_eq=0.5 mu_eq[tr(C_bar)-3]+0.5 kappa_eq(ln J)^2`，

`W_ve=0.25 mu_ve||dev(C_bar)-Z||_F^2`。

内部变量满足

`eta_ve Z_dot=-∂W_ve/∂Z`，

故

`D_ECM=-∂W_ve/∂Z:Z_dot=eta_ve||Z_dot||_F^2≥0`。

`A_hat` 与 `H_ECM_hat` 是相互独立、冻结的变量；`j_myo=0`。

## 8. 边界端口与唯一所有者

| 场景 | 端口/边界 | 唯一所有者 |
|---|---|---|
| 完整贴片血流 | 压力、WSS | `endocardium.apical_lumen` |
| 完整贴片外侧支撑 | 外侧顺应支撑 | `myocardium.opposite_outer` |
| 完整贴片侧向支撑 | 周边侧向顺应支撑 | 周边心肌细胞的向外 `lateral` 面 |
| Gate C | 顺应支撑 | `myocardium.opposite_outer` |
| Gate C | ECM 心腔侧 | 无端口，零牵引 |
| Gate D | `P_FIXTURE_D` 测试夹具 | `ECM.outer_facing_boundary` |
| Gate E 周期敏感性 | 面内成对约束 | 成对材料节点；侧向支撑关闭，外侧支撑保留 |

Gate D 夹具不是周围心肌，不能继承到完整贴片。一个界面面不得同时拥有环境支撑；一个积分贡献必须恰有一个配对所有者；内部作用—反作用不得登记为外部功率。

## 9. 总功率平衡

冻结的全局形式为

`d(Psi_cell+Psi_active+Psi_ECM+Psi_steric+Psi_adhesion+Psi_support)/dt`

`+D_cell+D_ECM+D_support`

`=P_active+P_pressure+P_WSS+P_environment+P_fixture_D`。

注册的支撑参考位置固定，因此 `P_environment=0`，Gate D 中 `P_fixture_D=0`；但相应的支撑能和支撑耗散仍必须登记。`chi_E`、`A_hat/H_ECM_hat` 周转、`j_myo`、内部接触转移和零功率数值规约均不进入右端外部输入。

## 10. 冻结边界

本文只定义并冻结 Stage 0 v02。网格实例化、代码、求解、响应、收敛结果和机制结论均未生成。Stage 1 仍被明确锁定。
