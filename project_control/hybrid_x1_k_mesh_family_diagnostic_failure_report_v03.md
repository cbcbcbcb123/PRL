---
report_id: REPORT-PRL-HYBRID-X1-K-V03-DIAGNOSTIC
status: failed_family_A_asymptotic_diagnosis
first_failed_criterion: family_A_excluded_legacy_cache_ratio
contract_commit: 354972f75638c641abd1c28efb3256ad5724d262
family_B: not_executed_due_to_family_A_hard_failure
---

# X1-K v03 mesh-family asymptotic diagnosis 失败报告

## 结论

v03 在 Family A 停止，状态为 `failed_family_A_asymptotic_diagnosis`。标准 projected icosphere levels 2–5 的 mesh-quality、global normal/tangential L2 渐近性、预注册单方向 `gamma*A` 残差与净力均通过；首个失败是 excluded upstream legacy float cache 在 level 5 的 `0.5*gamma*A` 比值误差超过合同阈值。没有运行 Family B，也没有进入任何轨迹。

## Family A 全局结果

| source level | h_rms | direction residual | legacy ratio | normal L2 | tangential L2 | net force |
|---:|---:|---:|---:|---:|---:|---:|
| 2 | `0.2999543` | `6.329e-10` | `0.5000004336` | `0.0335635` | `0.0108750` | `6.383e-17` |
| 3 | `0.1510470` | `3.309e-9` | `0.5000007030` | `0.0174043` | `0.00485703` | `4.560e-16` |
| 4 | `0.0756584` | `8.200e-10` | `0.4999994061` | `0.00878087` | `0.00187265` | `3.138e-16` |
| 5 | `0.0378461` | `6.822e-8` | `0.5000023612` | `0.00440032` | `0.000687636` | `1.817e-15` |

方向残差四层全部 `<=1e-7`，属于冻结 consistency plateau；它只支持该单一方向，不构成逐自由度完整 `-grad(gamma A)` 证明。normal 阶为 `0.9573,0.9896,0.9974`；tangential 阶为 `1.1749,1.3785,1.4463`。finest 两项均远低于 `2e-2`。mesh proxy 全部通过：Euler=2、closed manifold、strict outward/star-shaped face、positive signed volume、minimum q `>=0.9742`、minimum-face/mean-area `>=0.9278`、实际 `h` 严格递减。

## 首个失败

合同还冻结 legacy cache ratio 相对 `0.5` 的误差 `<=1e-6`。level 5 观测比值 `0.50000236120481867`，误差 `2.36120481867e-6`，因此 `legacy_cache_exclusion_passed=false`，Family A 硬失败。

该 cache 在 upstream 中以 `float` 累加 20480 个面，只用于 plotting；PRL registered owner 仍是 double precision `gamma*A`。方向导数 residual 已进入 plateau，所以当前失败分类是“excluded legacy energy instrumentation 的分辨率/累积精度”，不是力梯度、质量集总渐近段、参数化族或网格质量失败。合同不允许因其被排除就事后忽略该阈值。

## valence / symmetry-class 诊断

逐 valence 数据显示 12 个 valence-5 extraordinary vertices 的 normal absolute error mean 从 `0.1345` 变为 `0.1457`，没有逐点收敛；valence-6 主体的 RMS 从 `8.64e-3` 降至 `3.55e-4`。全局 L2 收敛因此不能升级为 uniform/pointwise convergence。逐 class 数据共 `146` 行，class count 为 `4,10,30,102`，原始聚合均随交付保存。

## 停止与 claim guard

Family B 标记 `not_executed_due_to_family_A_hard_failure`；smooth S1、R1、C1、F1 继续未执行。v02 D1 必须继续失败，X1-K 仍未通过。Route H Gate A v01 保持 `failed_invalid_numerics`。不得宣称 symmetry-broken support、主离散完整通过、长期稳定、生理有效或完整 cell–ECM/FSI/EFE 机制成立。

## 冻结复跑结果

- Docker C++ 全量回归：`43/45`；仅 v02 D1 与本 v03 Family A 两个冻结硬失败，无意外失败；
- strict owned `prl_core` 构建：通过；
- Python：`63/63`；
- tracked Python 与 v03 exporter Ruff：通过。

## 可复算命令

```powershell
docker run --rm --entrypoint sh -v "${PWD}:/workspace" -w /workspace prl-simucell3d-x0:38af451 -lc "cmake --build cpp/build-linux-x1h --target prl_short_trajectory_integration_test -j2"
docker run --rm --entrypoint sh -v "${PWD}:/workspace" -w /workspace prl-simucell3d-x0:38af451 -lc "ctest --test-dir cpp/build-linux-x1h -R prl_x1k_v03_family_a_asymptotic_diagnosis --output-on-failure"
python scripts/export_x1k_v03_diagnosis.py --log cpp/build-linux-x1h/Testing/Temporary/LastTest.log --output-dir results/hybrid/x1_k_mesh_family_v03
```
