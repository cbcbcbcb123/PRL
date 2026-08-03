---
report_id: REPORT-PRL-HYBRID-X1-K-V06-S1
status: failed_family_c_smooth_short_trajectory_analytic_radius_nonmonotonic
contract: CONTRACT-PRL-HYBRID-X1-K-V06-S1
contract_commit: ae80a0b6c77309fcfc6c3b2a19d8dbeb68af90b8
fork_commit: e2ed64a26bb5d7c2d878772564fb5ffcca343c3a
x1_k_passed: false
not_executed: [R1, C1, F1, downstream_coupling]
---

# X1-K v06 Family C 光滑球面短轨迹失败报告

## 结论

v06 在首个硬失败处停止并冻结，状态为 `failed_family_c_smooth_short_trajectory_analytic_radius_nonmonotonic`。Family C 四层轨迹与 finest `dt/2` 均完整运行，但 control-area mean radius 的 excursion-normalized 四层解析误差随网格加密增加，违反预注册的非增与相邻阶 `>=0.5` 门禁。因此 v06 不通过、X1-K 不通过；没有运行 R1、C1、F1 或任何下游耦合。

合同先行提交并推送为 `ae80a0b6c77309fcfc6c3b2a19d8dbeb68af90b8`。响应后没有改变阈值、`dt`、`T`、source levels、`M_C`、力、阻尼、registered owner 或旧测试。受控 fork 保持 `e2ed64a`，本切片未修改 fork。

## 冻结执行矩阵

- Family C：固定 `M_C`，source levels `1,2,3,4`；实际 `h_rms/R0=0.5846466,0.3007587,0.1514741,0.0758752`；
- 物理量：`R0=1,gamma=0.02,zeta_A=10`；
- 四层共同 `dt=1e-4,T=2e-2,200 steps`；finest 另跑 `dt=5e-5,400 steps`；
- fixed topology，无 remesh、contact 或 active；
- 真实公共 surface-tension 力入口、`zeta_i=zeta_A A_i` 和既有 owned overdamped commit 路径。

每个 run 保存 step 0 至终步。总计 `1205` 个全局时序行、`1205` 个局部时序行和 `1205` 个能量 ledger 行；原始 CTest 输出也随包冻结。

## 首个失败

control-area mean-radius ratio 的四层最终 response 为：

```text
0.99991999680809573,
0.99991999681331711,
0.99991999681519406,
0.99991999681561727.
```

解析值为 `0.99991999679974397`。按每层实际 step-0 response 的解析 excursion 归一化后，误差为：

```text
1.0439287051e-7,
1.6965749578e-7,
1.9311834534e-7,
1.9840834643e-7.
```

它们不满足非增；用实际 `h_rms` 计算的阶为 `-0.73059,-0.18884,-0.03909`，全部低于 `0.5`。四层也不处在共同 normalized `1e-10` plateau。finest 精度本身远低于 `0.02`，相邻网格差和两个广义自收敛阶 `1.5658,2.1766` 通过，但不能抵消解析误差门禁失败。

## 其余门禁结果

| 门禁 | 冻结观测 | 结果 |
|---|---:|---|
| area analytic finest error | `8.1691e-5` | passed |
| volume analytic finest error | `5.4207e-6` | passed |
| registered-energy analytic finest error | `8.1691e-5` | passed |
| 四个 QoI generalized self convergence | 最低 `1.4914` | passed |
| finest time pollution | 四项满足 raw plateau 或 `delta<=0.25 proxy` | passed |
| minimum oriented alignment | `0.999999973` | passed |
| global minimum triangle quality | `0.937503` | passed |
| minimum face-area ratio | `0.999828` | passed |
| maximum cache residual | `1.1654e-16` | passed |
| maximum centroid drift/R0 | `1.6882e-15` | passed |
| positive energy residual/Psi0 | `3.3249e-11` | passed |
| local extraordinary-vertex risk bounds | 全部阈内 | passed |
| force buffers cleared | 所有样本 true | passed |

能量账本 coverage 严格限定为 `surface_tension_only`：registered 为 `gamma*A` 和 `D_zeta`；legacy `0.5*gamma*A` cache、membrane、bending、pressure、contact、active、ECM 和 flow 均排除。不得写成 full owned-step total-energy inequality。

## extraordinary-vertex 风险

全程最大 valence-5 与 closed-one-ring radial excursion error 都为 `0.149073<0.25`；最大 radial error/initial incident-edge mean 为 `1.85323e-4<5e-4`；最大一环边缩放误差为 `8.11597e-6<5e-4`；最低局部质量比为 `0.9999959>0.90`。

这些局部短时界通过不代表 pointwise 收敛。逐步 CSV 继续保存 valence-5/closed-ring normal-error energy fraction、area-weighted RMS 与 pointwise maximum；面积权重缩小不得解释为 extraordinary-vertex 速度变准。

## 失败归因边界

mean-radius 的 raw 最终解析误差仅约 `8.35e-12` 至 `1.59e-11`。finest `dt` 与 `dt/2` 的 raw 差为 `8.00e-12`，`dt/2` 对解析解的 raw space proxy 为 `7.87e-12`，二者按合同属于 raw `1e-10` time plateau。因此当前证据更支持：control-area mean radius 接近离散不变量，空间误差被时间积分、浮点舍入与误差抵消的共同底噪污染。它不支持把失败归因为已证明的 surface force、dual-area damping 或主离散缺陷，也不支持物理不稳定结论。

但空间解析 gate 的共同 plateau 冻结在 excursion-normalized `1e-10`；当前约 `1e-7`，所以不能用上述诊断事后改判。导师如需进一步区分，必须另建新版本合同；v06 保持失败。

## TDD 与可复算命令

RED 1 因缺少 Family C 轨迹/局部审计 public seam 编译失败；最小 GREEN 后单步 tracer 通过。RED 2 因缺少统一 thresholds/evaluator 编译失败；最小 GREEN 的第一次正式响应即产生上述失败。两个 RED 证据均随包冻结。

冻结后完整回归结果：parent C++ 为 `48/51`，仅 v02 D1、v04 Family B 与新 v06 三个预期冻结失败，意外失败为 0；受控 fork 为 `134/134`；owned `prl_core` 在 `-Wall -Wextra -Wpedantic -Werror` 下构建通过；Python 为 `63/63`；新增 exporter 的 Ruff 通过。

```powershell
docker run --rm --entrypoint sh -v "${PWD}:/workspace" -w /workspace prl-simucell3d-x0:38af451 -lc "cmake --build cpp/build-linux-x1h --target prl_short_trajectory_integration_test -j2"
docker run --rm --entrypoint sh -v "${PWD}:/workspace" -w /workspace prl-simucell3d-x0:38af451 -lc "ctest --test-dir cpp/build-linux-x1h -V -R '^prl_x1k_v06_family_c_short_trajectory_gate$'"
python scripts/export_x1k_v06_trajectory.py --log cpp/build-linux-x1h/Testing/Temporary/LastTest.log --output-dir results/hybrid/x1_k_family_c_trajectory_v06
docker run --rm --entrypoint sh -v "${PWD}:/workspace" -w /workspace prl-simucell3d-x0:38af451 -lc "cmake --build cpp/build-linux-x1h -j2 && ctest --test-dir cpp/build-linux-x1h --output-on-failure"
docker run --rm --entrypoint sh -v "${PWD}:/workspace" -w /workspace/external/simucell3d prl-simucell3d-x0:38af451 -lc "cmake --build build-x1k-v04 -j2 && ctest --test-dir build-x1k-v04 --output-on-failure"
$env:PYTHONPATH='src'; python -m pytest -q
python -m ruff check scripts/export_x1k_v06_trajectory.py
```

## 历史与 claim guard

v01–v05 文件不覆盖；v02 D1 继续是 `failed_instantaneous_smooth_surface_refinement`，v04 Family B 继续是 `failed_family_B_parameterized_diagnosis`，v05 继续只是 `passed_quality_controlled_symmetry_broken_global_L2_diagnosis`，Route H Gate A v01 继续是 `failed_invalid_numerics`。

唯一允许的表述是：“冻结 Family C 短轨迹的绝大多数全局、时间、能量和局部风险门禁通过，但 mean-radius 四层解析误差门禁失败，因此 v06 和 X1-K 未通过。”不得宣称长期稳定、生理有效、完整 cell–ECM/FSI、EFE、参数标定或心脏发育机制成立。
