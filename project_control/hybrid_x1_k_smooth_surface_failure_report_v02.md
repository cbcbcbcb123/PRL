---
report_id: REPORT-PRL-HYBRID-X1-K-V02
status: failed_instantaneous_smooth_surface_refinement
contract: CONTRACT-PRL-HYBRID-X1-K-V02
contract_commit: c640d2a06c3e8642782bf8a258ca741741d8bae7
first_failed_case: D1_instantaneous_velocity
not_executed: [smooth_S1, R1, C1, F1]
---

# X1-K v02 光滑球面制造解失败报告

## 结论

X1-K v02 未通过。合同先于任何 v02 响应冻结并推送；D0 cube 诊断与 D1 `gamma*A` 方向导数通过，但 D1 四层瞬时速度误差违反“随 `h` 非增”的硬门禁。执行在首个失败处停止，没有运行 smooth S1、R1、C1 或 F1，没有改变网格层数、阈值、`dt`、`T` 或解析解。

## 已冻结的客观结果

四层 projected icosphere 的 `(vertices,faces)` 为 `(12,20)`、`(42,80)`、`(162,320)`、`(642,1280)`；实际 RMS chord `h` 为 `1.051462224238267`、`0.5833799767501565`、`0.2999543167525501`、`0.1510470367695401`。

方向导数归一化残差为：

`5.7811e-11, 2.7931e-12, 6.3294e-10, 3.3092e-9`。

四层均低于 `1e-7` consistency plateau；finest 也低于 `1e-6`。legacy cache / registered `gamma*A` 比值相对 `0.5` 的最大偏差为 `7.0297e-7 <=1e-6`，且 legacy cache 未进入能量 owner。

瞬时速度结果：

| level | normal relative L2 | tangential relative L2 | normalized net force |
|---:|---:|---:|---:|
| 0 | `1.3996989859860865e-16` | `2.0057290356172717e-16` | `4.4380061570295216e-17` |
| 1 | `5.738043558645111e-2` | `2.5044194914478364e-16` | `2.2688928423732637e-17` |
| 2 | `3.356352001836485e-2` | `1.0875028470750475e-2` | `6.382879252150122e-17` |
| 3 | `1.7404321862143909e-2` | `4.8570267730203174e-3` | `4.560319363353449e-16` |

normal 相邻阶为 `-57.1162, 0.80616, 0.95727`；tangential 相邻阶为 `-0.37693, -47.2063, 1.17492`。finest 两项均满足 `<=2e-2`，净力也全部满足 `<=1e-12`，但完整四层误差非增条件失败，故状态必须是 `failed_instantaneous_smooth_surface_refinement`。

## 失败归因

level 0 是规则正二十面体。对完全对称的顶点轨道，面积梯度力径向且每个 barycentric control area 相同；面积的二次齐次性使质量集总后的径向速度恰好等于连续球面值。这是 coarse symmetry-induced superconvergence，不代表 coarse 几何一般比 refined 几何更准确。

level 1 以后局部几何/顶点轨道不再给出同样的逐点消去，误差从机器精度重新出现；normal 在 level 1→2→3 以正阶下降，tangential 在 level 2→3 也以正阶下降。因合同冻结为“四层均非增”，不能事后丢弃 coarse 层或改用 asymptotic subset。

分类：主要是 manufactured geometry family 的对称超收敛与 lumped control-area 速度度量共同导致的 acceptance-design failure。`gamma*A` 方向导数已通过，因此没有证据把首个失败归为 surface force gradient 缺陷；该 gate 尚未推进时间，不能归为时间污染。

## 验证与复算命令

验证状态：parent C++ CTest 为 `41/42`，唯一失败是冻结 D1；PRL-owned `prl_core` 已在 `-Wall -Wextra -Wpedantic -Werror` 下编译。将同一 flags 全局施加到完整 integration target 时，外部 upstream `utils.hpp` 的 OpenMP pragma 触发 `unknown-pragmas`，因此不宣称完整 strict integration target 通过。Python 为 `63/63`，tracked Python Ruff 全部通过。v01 六个文件哈希与 v02 前记录完全一致。

容器镜像：`prl-simucell3d-x0:38af451`。从冻结提交构建并复现首个失败：

```powershell
docker run --rm --entrypoint sh -v "${PWD}:/workspace" -w /workspace prl-simucell3d-x0:38af451 -lc "cmake --build cpp/build-linux-x1h --target prl_short_trajectory_integration_test -j2"
docker run --rm --entrypoint sh -v "${PWD}:/workspace" -w /workspace prl-simucell3d-x0:38af451 -lc "ctest --test-dir cpp/build-linux-x1h -R prl_x1k_sphere_instantaneous_velocity_refinement --output-on-failure"
```

机器摘要、逐项判据与原始瞬时数据位于 `results/hybrid/x1_k_smooth_surface_v02/`。v01 文件未修改；用户未跟踪 `figures/` 与两个脚本未触碰。

## Claim guard

允许的陈述仅为：“cube 非光滑奇异族诊断被重现；真实 surface-tension force 与注册 `gamma*A` 在冻结方向导数精度内一致；冻结四层 icosphere 瞬时速度 acceptance 因 coarse 对称超收敛导致非单调而失败。”不得声称 smooth S1、X1-K、长期稳定、生理有效、完整 cell–ECM/FSI 或 EFE 机制已经通过。
