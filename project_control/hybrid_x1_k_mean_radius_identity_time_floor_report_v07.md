---
report_id: REPORT-PRL-HYBRID-X1-K-V07-DIAGNOSIS
status: passed_structural_mean_radius_identity_and_time_floor_diagnosis
contract: CONTRACT-PRL-HYBRID-X1-K-V07-DIAGNOSIS
contract_commit: 668465c9f554850d0624eef474c49b8514c21cce
result_package_commit: f4df24c840f357fc06a45c4406bc55b9817199b9
fork_commit: e2ed64a26bb5d7c2d878772564fb5ffcca343c3a
x1_k_passed: false
not_executed: [R1, C1, F1, downstream_coupling]
---

# X1-K v07 Family C mean-radius 结构恒等式与时间底噪诊断报告

## 结论

v07 的全部新门禁通过，唯一允许状态为 `passed_structural_mean_radius_identity_and_time_floor_diagnosis`。四层初始结构审计在机器精度内满足 Euler 面积齐次恒等式和 control-area mean-radius 初始速度恒等式；source levels 1、4 的四档时间响应呈一阶收敛，Richardson 外推满足预注册误差阈值。

这不是 X1-K 通过。v06 仍是 `failed_family_c_smooth_short_trajectory_analytic_radius_nonmonotonic`；没有运行 R1、C1、F1、remesh/contact、ECM/flow 长耦合或参数标定。

合同先行提交并推送为 `668465c9f554850d0624eef474c49b8514c21cce`，结果包提交并推送为 `f4df24c840f357fc06a45c4406bc55b9817199b9`。受控 fork 保持 `e2ed64a26bb5d7c2d878772564fb5ffcca343c3a`。响应后没有改变 `M_C`、力、阻尼、registered owner、`dt`、`T`、source levels 或既有阈值。

## 1. Euler 二次齐次推导

固定拓扑三角表面在统一缩放 `x_i -> lambda x_i` 下满足

```text
A(lambda x) = lambda^2 A(x).
```

Euler 齐次函数定理因此给出

```text
sum_i x_i · partial(A)/partial(x_i) = 2A.
```

真实公共 surface-tension 力使用注册能量 `Psi=gamma*A`，所以

```text
F_i = -partial(gamma A)/partial(x_i),
sum_i x_i · F_i = -2 gamma A.
```

每个三角形面积以 `A_f/3` 分给三个顶点，故独立 barycentric dual area 精确满足 `sum_i A_i=sum_f A_f=A`。v07 冻结的无量纲残差为

```text
r_H = |sum_i x_i·F_i + 2 gamma A|/(2 gamma A).
```

该推导只证明统一缩放方向的 Euler 收缩关系；它不是逐自由度有限差分方向导数全集，也不证明包含其他能量 owner 时的总力恒等式。

## 2. 初始 control-area mean-radius 的权重导数相消

定义

```text
Rbar = N/A,
N = sum_i A_i r_i,
r_i = |x_i|.
```

Family C 的初始顶点全部投影到同一球面，因此 `r_i=R0` 且 `N=R0 A`。对时间求导：

```text
dN/dt = R0 dA/dt + sum_i A_i dr_i/dt,
dRbar/dt
 = [(R0 dA/dt + sum_i A_i dr_i/dt)A - R0 A dA/dt]/A^2
 = sum_i A_i dr_i/dt/A.
```

取 `n_i=x_i/R0`、`v_i=F_i/(zeta_A A_i)`，结合 Euler 收缩关系：

```text
vbar_r = sum_i A_i(v_i·n_i)/sum_i A_i
       = [sum_i x_i·F_i]/(zeta_A R0 A)
       = -2 gamma/(zeta_A R0).
```

冻结残差为

```text
r_v = |vbar_r + 2 gamma/(zeta_A R0)|
      /(2 gamma/(zeta_A R0)).
```

权重导数项只在这一初始等半径时刻相消。离开等半径状态后 `r_i` 一般不相同，因此不得将机器精度残差外推为一般非球网格或全轨迹恒等式。

## 3. 四层结构审计结果

| source level | `h_rms` | `r_H` | `r_v` | net-force residual |
|---:|---:|---:|---:|---:|
| 1 | 0.5846466 | 3.5734e-16 | 0 | 5.3303e-17 |
| 2 | 0.3007587 | 7.8817e-16 | 2.1684e-16 | 7.3760e-17 |
| 3 | 0.1514741 | 1.9976e-15 | 1.3010e-15 | 3.3283e-16 |
| 4 | 0.0758752 | 4.2017e-15 | 1.7347e-15 | 2.2130e-16 |

四层 `|sum_i A_i/A-1|` 最大为 `4.22e-15`，最大半径不一致为 `3.33e-16`。审计前后最大位置位移为 0，position/state hashes 逐层一致，调用后 force-buffer norm 为 0。所有结构门禁通过。

## 4. 时间响应与 Richardson 结果

固定 `R0=1,gamma=0.02,zeta_A=10,T=0.02`，解析 mean-radius ratio 为 `0.99991999679974397`。每层运行 `dt={4e-4,2e-4,1e-4,5e-5}`，对应 `50/100/200/400` steps。

| level | `D0,D1,D2` | `p_t,0,p_t,1` | Richardson error |
|---:|---|---|---:|
| 1 | 3.2166e-11, 1.6082e-11, 8.0419e-12 | 1.00010, 0.99983 | 7.7320e-12 |
| 4 | 3.2010e-11, 1.6001e-11, 8.0029e-12 | 1.00032, 0.99959 | 1.3256e-13 |

两层的三项 raw 差均严格递减，两个阶均在 `[0.75,1.25]`，且三项差并未全部进入 `<=1e-13` 的共同舍入平台。跨网格 Richardson 差为 `7.5995e-12<=1e-10`。时间门禁通过。

八条轨迹保存 `1508` 行全局、`1508` 行局部和 `1508` 行能量时序。v06 的 area、volume、registered-energy、orientation、triangle quality、face-area、cache、centroid、`surface_tension_only` 能量账本和 extraordinary-vertex 局部指标均作为只读控制通过。

## 5. 与 v06 失败的关系

v06 mean-radius excursion-normalized 四层解析误差继续冻结为

```text
1.0439287051e-7,
1.6965749578e-7,
1.9311834534e-7,
1.9840834643e-7,
```

空间观测阶继续为 `-0.7305867,-0.1888362,-0.0390903`。v07 证明当前 raw mean-radius 响应含有清楚的一阶时间误差，并可由 Richardson 显著消除；它只解释时间底噪来源，不重判 v06 已冻结的跨 `h` 解析单调/阶门禁，也不证明主离散的全轨迹空间收敛。

## 6. TDD、证据与复算

第一轮 RED 因缺少公开只读 `audit_spherical_mean_radius_structural_identity` seam 而编译失败；最小 GREEN 后，单层只读 tracer 和四层结构门禁通过。第二轮 RED 因缺少公开 `MeanRadiusTimeFloorThresholds` 与 `evaluate_mean_radius_time_floor` 而编译失败；最小 GREEN 的合成一阶 tracer 通过，之后才生成正式八轨迹响应。

原始 CTest 输出、逐步 CSV、结构/时间 criteria、能量 ledger、RED/GREEN 证据与复算命令均位于 `results/hybrid/x1_k_mean_radius_v07/`。

完整回归结果为：parent C++ `52/55`，只有 v02 D1、v04 Family B、v06 Family C 三个预期历史冻结失败，v07 新增测试 `4/4` 通过且意外失败为 0；受控 fork `134/134`；owned `prl_core` 在 `-Wall -Wextra -Wpedantic -Werror` 下构建通过；Python `63/63`；新增 exporter 的 Ruff 通过。导出器复算 `4` 条结构记录以及 `1508/1508/1508` 条全局、局部、能量记录，逐行能量账本闭合。

## 7. Claim guard

唯一允许表述是：“在冻结 Family C case 中，初始等半径球面的 mean-radius 结构恒等式与两个网格层级的短时一阶时间底噪诊断通过。”

不得宣称 X1-K 通过、长期稳定、生理有效、完整 cell–ECM/FSI、EFE、参数标定或心脏发育机制成立。Route H Gate A v01 继续为 `failed_invalid_numerics`；v02 D1、v04 Family B 和 v06 的历史失败均保持不变。
