---
report_id: REPORT-PRL-HYBRID-X1-E-V01
status: passed_frozen
completed_at: 2026-08-02
parent_branch: codex/simucell3d-hybrid-feasibility
cell_engine_commit: 1ae6b27c785b3d4eabff136e3c8c588c2abc76ab
result_id: PRL-HYBRID-X1-E-ACTIVE-MECHANICS-V01
---

# Hybrid X1-E 单细胞主动收缩 C++ 最小闭环报告 v01

## 结论

X1-E 已完成并冻结。父项目新增独立 `active_myocardial_mechanics` 公共模块，以 persistent material-point anchors 为主动单元，以 controller material point 上的激活状态与纤维方向为控制输入，输出主动能量、激活输入功率、persistent-vertex nodal forces 和守恒审计。

真实 `local_mesh_refiner` edge swap 已与该模块串成端到端路径。材料重绑定后复用同一冻结 contraction unit，无需把主动状态复制到临时 node/face，也无需在 fork 中植入项目特定生物学字段。

## TDD 证据

1. preferred-length tracer RED：新增行为测试首先因公共头 `prl/core/active_myocardial_mechanics.hpp` 不存在而编译失败；实现模块后制造解转绿。
2. revision-safe state RED：材料 sink 测试首先因 `update_active_state` 不存在而编译失败；实现带 expected revision 的原子更新后转绿。
3. mechanics GREEN：解析能量/力/功率、能量方向导数、刚体客观性与 C1 protocol 节点全部通过显式运行时断言。
4. real-remesh GREEN：真实 edge swap 触发材料迁移后，主动几何量、能量、功率和守恒量在冻结容差内不变。

## 实现合同

- `ActiveContractionUnit` 只保存稳定 unit ID、三个材料点 ID、冻结参考长度、刚度和最低纤维对齐度；
- `build_active_contraction_unit` 只在 mesh/material cell 与 revision 对齐时建立参考；
- `evaluate_active_contraction` 从当前材料宿主解析锚点，把中央力按重心权重散射到 persistent vertices；
- controller active state 的唯一冻结形状为 `[alpha, alpha_rate]`；
- `MyocardialMaterialTransferSink::update_active_state` 在 per-cell lock 内检查 expected revision 后提交；
- 输出 audit 包含能量、功率、合力、合矩、对齐度和激活上界。

## 定量验收

| 检查 | 结果 |
|---|---|
| C1 rest/ramp/hold/release/delay | passed |
| manufactured energy / force / power | exact within `1e-12` |
| force vs. energy directional derivative | relative error `≤1e-9` |
| rigid translation/rotation objectivity | difference `≤1e-14` |
| revision-safe active-state update | passed in Release and Debug |
| real `local_mesh_refiner` remesh invariance | difference `≤1e-12` |
| parent C++ CTest with cell-engine integration | `20/20 passed` |
| owned C++ core `-Wall -Wextra -Wpedantic -Werror` | `13/13 passed` |
| parent Python hybrid + Stage 0/1/2 | `63 passed` |

## 科学与工程边界

本阶段复用了 Route H 的制造解主动机制，但没有复用其失败轨迹，也没有改变 Stage 2 Gate A 的冻结状态。当前 C++ 模块是能被求解器消费的力与功率端口，不是完整 cell timestep：尚未与 cell engine 被动力、阻尼、约束和位置更新合并，因此不能声称已经生成收缩形变、射血、ECM 反馈或血流响应。

`external/simucell3d` 本阶段保持在提交 `1ae6b27c785b3d4eabff136e3c8c588c2abc76ab`，没有新增 fork 修改。下一安全切片为 X1-F 单步 active-force assembly seam；只有其单步残差、功率符号和失败传播冻结后，才考虑短时轨迹。
