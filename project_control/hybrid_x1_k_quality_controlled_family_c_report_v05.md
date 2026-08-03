---
report_id: REPORT-PRL-HYBRID-X1-K-V05-DIAGNOSTIC
status: passed_quality_controlled_symmetry_broken_global_L2_diagnosis
contract_commit: 4d2cad4ab77cb4d9410348283e07212092d31c24
fork_commit: e2ed64a26bb5d7c2d878772564fb5ffcca343c3a
preserved_x1_k_status: failed_instantaneous_smooth_surface_refinement
---

# X1-K v05 Family C 诊断报告

## 结论

Family C 在全部预注册门禁下通过，状态冻结为 `passed_quality_controlled_symmetry_broken_global_L2_diagnosis`。这是一次瞬时、面积加权 global L2 的 mesh-family 诊断通过，不是 X1-K acceptance。X1-K 仍未通过；没有执行新的 smooth S1、R1、C1、F1 或任何后续轨迹。

旧证据保持不变：v02 D1 继续硬失败，v04 Family B 继续因 source level 2 首次出现 `h_max/h_min=2.045973>2.0` 而失败，Route H Gate A v01 继续是 `failed_invalid_numerics`。受控 fork 仍为 `e2ed64a`，本切片没有 fork 修改。

## 合同先行与 TDD

合同先行提交并推送为 `4d2cad4ab77cb4d9410348283e07212092d31c24`。合同在任何 Family C 网格响应前冻结了 `M_C`、levels 1–4、全部旧阈值、几何类规则与局部误差能量定义。

RED 在纯合成 audit 上因缺少以下公共行为而编译失败：节点实际 control area、物理 normal error、response-pre valence-5 closed-one-ring membership、四层局部能量聚合器与 symmetry-breaking gate。GREEN 只增加这些只读诊断字段、聚合器、Family C 测试入口和导出器；真实力、阻尼、cache、registered owner 与旧 evaluator 未改变。

## Family C 冻结矩阵

```text
M_C = [[1.000, 0.050, 0.025],
       [0.050, 1.050, 0.040],
       [0.025, 0.040, 0.950]].
```

顺序主子式为 `1,1.0475,0.99296875`，故为 SPD 且 `det>0`。特征值为 `0.934772496,0.969099738,1.096127763`，`kappa_2=1.172614478`。由于 `M_C-I=0.5(M_B-I)`，相对单位映射的谱偏移精确减半；没有依据响应调矩阵。

## 硬门禁结果

| 量 | 四层/极值 | 阈值 | 结果 |
|---|---:|---:|---|
| `h_max/h_min` | `1.4785,1.5498,1.5878,1.5980` | `<=2.0` | passed |
| minimum triangle quality | `0.937503` | `>=0.05` | passed |
| minimum face/mean area | `0.705570` | `>=0.01` | passed |
| maximum radius deviation | `3.33e-16` | `<=1e-12` | passed |
| maximum directional residual | `3.217e-8` | plateau `<=1e-7` | passed |
| maximum legacy ratio error | `1.776e-15` | `<=1e-6` | passed |
| maximum net-force residual | `3.328e-16` | `<=1e-12` | passed |
| class count | `21,81,321,1281` | `>=floor(N/2)` | passed |
| maximum class size | `2,2,2,2` | `<=2` | passed |

normal global L2 为 `0.058544,0.034411,0.017858,0.009008`，相邻实际 `h_rms` 阶为 `0.7995,0.9563,0.9898`。tangential global L2 为 `0.024079,0.012883,0.005192,0.001935`，阶为 `0.9409,1.3250,1.4280`。两者均四层非增、非 plateau 阶 `>=0.5` 且 finest `<0.02`。

closed manifold、Euler=2、正 signed volume、逐面 origin contribution、outward alignment 与 no-self-intersection proxy 全部通过。局部 error energy 全部 finite/nonnegative；`E_v5+E_v6=E_total` 的浮点闭合门禁通过。

## valence-5 与 closed-one-ring 风险

valence-5 pointwise maximum relative normal error 为 `0.1096,0.1380,0.1468,0.1491`，没有点态收敛。`E_v5` 的观测阶虽为 `1.2067,1.8276,1.9583`，但其总误差能量占比从 `0.7518` 增至 `0.9745`；这反映 control area 权重缩小，并不证明 extraordinary vertices 的速度误差下降。

valence-5 closed one-ring 在 levels 2–4 含 `72` 个顶点，其 error-energy 阶为 `1.5826,1.8750,1.9619`，但 pointwise maximum 同样升至 `0.1491`。因此结果严格限制为 area-weighted global L2，不得称为 uniform/pointwise convergence 或动力学有效。

## 验证

- parent C++：`47/49`；仅 v02 D1 与 v04 Family B 两个冻结失败，v05 两项测试通过；
- owned `prl_core`：`-Wall -Wextra -Wpedantic -Werror` 构建通过；
- controlled fork：`134/134`；HEAD/upstream 均为 `e2ed64a`；
- Python：`63/63`；tracked Python 与 v05 exporter Ruff 通过；
- 受保护的 `figures/` 与两个用户脚本仍未跟踪且未触碰。

## 可复算命令

```powershell
docker run --rm --entrypoint sh -v "${PWD}:/workspace" -w /workspace prl-simucell3d-x0:38af451 -lc "cmake --build cpp/build-linux-x1h -j2 && ctest --test-dir cpp/build-linux-x1h -V -R prl_x1k_v05_family_c_quality_controlled_diagnosis"
python scripts/export_x1k_v05_diagnosis.py --log cpp/build-linux-x1h/Testing/Temporary/LastTest.log --output-dir results/hybrid/x1_k_mesh_family_v05
docker run --rm --entrypoint sh -v "${PWD}:/workspace" -w /workspace prl-simucell3d-x0:38af451 -lc "cmake --build cpp/build-linux-x1h -j2 && ctest --test-dir cpp/build-linux-x1h --output-on-failure"
docker run --rm --entrypoint sh -v "${PWD}:/workspace" -w /workspace/external/simucell3d prl-simucell3d-x0:38af451 -lc "cmake --build build-x1k-v04 -j2 && ctest --test-dir build-x1k-v04 --output-on-failure"
$env:PYTHONPATH='src'; python -m pytest -q
```

## Claim guard

唯一允许的正面表述是：冻结 Family C 在预注册质量、对称破缺、方向、面积加权 global L2、净力与局部能量账本门禁下通过。不得升级为 X1-K 通过、点态收敛、长期稳定、生理有效、完整 cell–ECM/FSI、EFE 或心脏发育机制成立。
