---
report_id: REPORT-PRL-HYBRID-X0-AB-V01
status: completed_x0_a_x0_b
reported_at: 2026-07-31
branch: codex/simucell3d-hybrid-feasibility
---

# Hybrid X0-A/B 执行报告 v01

## 结论

X0-A 和 X0-B 已完成，允许进入 X0-C；X0-C、X0-D 和正式迁移决策 X0-E 均未宣告通过。

Route H 的 Gate A 失败冻结包没有改动，Gate B–E 仍 blocked。

## X0-A — 上游来源、构建与 remesh 测试

- 官方源码固定为 submodule commit `38af45154070b2b08dcdb25cbe629de499f382d9`；
- BSD-3 license SHA-256：`04DFCCDCE4BDAE97AE45BA06FD2C2DA71E97B2CEB7DB5220EB5DDAC4CCBCF120`；
- Linux/GCC 9.4、CMake 3.16.3、Python binding disabled；
- `test_local_mesh_refiner` 构建通过；
- `can_be_merged_test`、`edge_swap_test`、`split_edge_test`、`merge_edge_test`、`get_triangle_score_test` 全部 exit 0；
- executable SHA-256：`889375BBCAFAC476B9B6FF2DD8E61D86584C7506DAE64C95F8E2392C3B70F87F`。

### 可移植性发现

1. 官方 Dockerfile 连续使用三个 `FROM`，实际只保留最后的 `python:3.10` stage；首次构建在本机 600 秒内未形成镜像；
2. CMake 4 需要额外 policy-minimum 兼容参数；
3. MSVC 默认 OpenMP 模式不接受源码的 `omp atomic write`；
4. C++17 源码仍使用已经移除的 `std::random_shuffle`；
5. `local_mesh_refiner.hpp` 在 C++17 `constexpr` 初始化中调用 `std::sqrt`，当前 MSVC 不接受。

这些问题不否定 Linux/GCC 上的功能，但说明主项目不能把 upstream build scripts 直接当作跨平台生产接口。

## X0-B — topology-independent material registry

已实现：

- persistent material-point ID；
- face+barycentric host 可重绑定；
- label、连续 state 和 reference weight 独立于 face ID；
- topology-only edge split/diagonal swap 后的精确几何重绑定；
- 超出 frozen distance 时 fail-fast；
- barycentric nodal scatter 的合力和合力矩守恒。

正式探针结果：

| metric | observed | limit | status |
|---|---:|---:|---|
| point position error | `0` | `1e-12` | passed |
| ID retention | `1.0` | `1.0` | passed |
| state residual | `0` | `0` | passed |
| weight residual | `0` | `0` | passed |
| force resultant residual | `1.0007415106216802e-16` | `1e-12` | passed |
| moment residual | `5.551115123125783e-17` | `1e-12` | passed |

## 回归检查

- `pytest -q tests/hybrid`：`4 passed`；
- `pytest -q tests/stage1 tests/stage2`：`38 passed`；
- upstream local-remesh tests：`5 passed`。

## 下一工作包

X0-C 将把当前注册表扩展为心肌材料场 seam：

1. apical/basal/lateral 离散身份；
2. 切平面主动纤维方向；
3. 主动状态变量；
4. split/swap/merge 后的方向投影、符号连续性和状态守恒；
5. 与 upstream remesh event 的 C++ adapter 合同。
