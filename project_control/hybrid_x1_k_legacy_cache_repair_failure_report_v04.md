---
report_id: REPORT-PRL-HYBRID-X1-K-V04-DIAGNOSTIC
status: failed_family_B_parameterized_diagnosis
first_failed_criterion: family_B_source_level_2_maximum_edge_ratio
contract_commit: 4314566
fork_commit: e2ed64a26bb5d7c2d878772564fb5ffcca343c3a
---

# X1-K v04 legacy-cache repair + Family B 诊断失败报告

## 结论

legacy cache 精度修复成功，修复后的 Family A 在 v03 原阈值下全部通过；Family B 在预注册 mesh shape-regularity gate 失败，因此 v04 状态必须为 `failed_family_B_parameterized_diagnosis`，不能写为 instrumentation-repair 后的 mesh-family diagnosis 通过。没有进入任何新轨迹、R1、C1 或 F1。

## RED → GREEN

修复前 fork 公共测试复现：getter 为 float，level-5 legacy ratio=`0.50000236120481867`，误差=`2.3612048186683054e-6`。独立面积梯度公式相对真实节点力的归一化残差为 `9.67e-18`。

最小修复只把 surface-tension cache 存储/getter/reset 提升为 double。修复后 ratio=`0.49999999999998201`，误差=`1.7985612998927536e-14`；registered energy、方向残差、normal/tangential L2、净力、节点力公式残差和 force-buffer cleanup 均在冻结 `1e-12` 归一化容差内不变。fork 全量 `134/134`。

## 修复后 Family A

Family A 的 normal 阶仍为 `0.9573,0.9896,0.9974`，tangential 阶为 `1.1749,1.3785,1.4463`；finest error 分别为 `0.0044003` 与 `0.00068764`。四层 legacy ratio 相对 `0.5` 的最大误差降为 `1.7986e-14`。mesh、方向、cache、normal/tangent 和净力门禁全部通过。

这不覆盖 v03 在 f718682 上的 float-cache 失败事实，也不恢复 X1-K。

## Family B 首个失败

| source level | h_max/h_min | normal L2 | tangential L2 | cache ratio | class count |
|---:|---:|---:|---:|---:|---:|
| 1 | `1.926917` | `0.0620343` | `0.0476959` | `0.5000000000000001` | 21 |
| 2 | `2.045973` | `0.0370524` | `0.0175689` | `0.5000000000000004` | 81 |
| 3 | `2.111595` | `0.0192800` | `0.00609552` | `0.5000000000000003` | 321 |
| 4 | `2.134482` | `0.00972000` | `0.00211256` | `0.4999999999999983` | 1281 |

冻结阈值为 `h_max/h_min<=2.0`；首个失败是 source level 2 的 `2.04597312684296`。levels 3、4 也失败。其余 geometry proxy 均通过：minimum q `>=0.8886`，minimum-face/mean-area `>=0.5386`，orientation/topology/radius checks 通过。

Family B 的 normal 阶为 `0.7771,0.9531,0.9908`，tangential 阶为 `1.5060,1.5444,1.5330`；方向 consistency plateau、legacy cache 与净力均通过。因此失败分类是固定 SPD parameterized family 的预注册 edge-ratio shape-regularity proxy，不是力梯度、质量集总渐近性、cache repair 或 force balance 失败。禁止看结果后调整 M 或阈值。

## extraordinary-vertex 风险

Family A 的 valence-5 normal absolute error mean 为 `0.1345 -> 0.1457`；Family B 为 `0.1085 -> 0.1542`。global L2 收敛仍不能证明 pointwise/uniform convergence。未来轨迹门禁必须包含 extraordinary-vertex 局部质量/速度审计，本任务不运行轨迹。

## 验证与 claim guard

- parent C++：`45/47`；仅冻结的 v02 D1 与 v04 Family B 失败；
- fork C++：`134/134`；
- strict owned `prl_core`：通过；
- Python：`63/63`；Ruff：通过。

X1-K 仍未通过；Route H Gate A v01 保持 `failed_invalid_numerics`。不得宣称 mesh-family diagnosis、pointwise convergence、长期稳定、生理有效或完整 cell–ECM/FSI/EFE 机制成立。

## 可复算命令

```powershell
docker run --rm --entrypoint sh -v "${PWD}:/workspace" -w /workspace/external/simucell3d prl-simucell3d-x0:38af451 -lc "cmake --build build-x1k-v04 -j2 && ctest --test-dir build-x1k-v04 --output-on-failure"
docker run --rm --entrypoint sh -v "${PWD}:/workspace" -w /workspace prl-simucell3d-x0:38af451 -lc "cmake --build cpp/build-linux-x1h -j2 && ctest --test-dir cpp/build-linux-x1h --output-on-failure"
python scripts/export_x1k_v04_diagnosis.py --log cpp/build-linux-x1h/Testing/Temporary/LastTest.log --output-dir results/hybrid/x1_k_mesh_family_v04
```
