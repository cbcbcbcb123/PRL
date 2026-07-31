---
plan_id: PLAN-PRL-HYBRID-SIMUCELL3D-ECM-X0-V01
status: authorized_in_progress
authorized_at: 2026-07-31
authorization_source: user-approved hybrid recommendation
decision_gate: X0-E
---

# SimuCell3D–体积 ECM 混合架构可行性阶段 X0 v01

## 1. 已批准的方向

本阶段验证下列目标架构，不修改或覆盖既有 Route H 冻结证据：

`lumen → SimuCell3D-compatible endocardial cell engine → independent tetrahedral ECM → SimuCell3D-compatible myocardial cell engine → surroundings`

- 细胞侧负责独立闭合表面、接触、动态重网格、极性和主动收缩；
- ECM 侧继续使用独立三维四面体有限变形连续体；
- 非匹配界面负责 cell–ECM 作用—反作用、材料点身份和功率传递；
- 既有 Route H 是小规模 reference/oracle，不再承担大规模路线承诺。

## 2. 不可破坏的边界

1. `FREEZE-PRL-ROUTE-H-STAGE2-GATE-A-FAILURE-V01` 保持不变；
2. Route H Gate B–E 继续 blocked；
3. 本阶段不宣告主动收缩、完整 patch、生理标定或论文机制通过；
4. 不把 SimuCell3D 的闭合曲面 ECM 等同于本项目的体积 ECM；
5. 不因重网格丢失细胞极性、纤维方向、tether 身份或 reference weight；
6. 不把重网格造成的能量跳变隐藏在物理耗散中。

## 3. 工作包

### X0-A — 上游来源与可构建性

- 以 Git submodule 固定 SimuCell3D 官方源码提交；
- 核对许可证、构建方式、测试入口、Python binding 和 OpenMP；
- 运行上游 remeshing 单元测试，或如实记录本机工具链阻塞。

### X0-B — 重网格安全的材料点注册表

- 材料点 ID、标签、状态和 reference weight 独立于 face ID；
- topology-only split/swap 后，以几何投影重新绑定 face+barycentric；
- nodal force scatter 必须保持材料点合力与合力矩。

### X0-C — 心肌材料场扩展 seam

- 将 apical/basal/lateral 身份、主动纤维方向和主动状态定义为可转移材料场；
- 审核 upstream split/swap/merge 对离散 face type 的现有处理；
- 为 C++ 扩展形成最小接口，不在未验证前全面 fork 上游。

### X0-D — 单细胞—体积 ECM 垂直切片

- 一个可重网格闭合细胞表面；
- 一个独立四面体 ECM patch；
- 持久材料点 tether、作用—反作用和非穿透；
- 检查能量方向导数、合力、合力矩和功率残差。

### X0-E — 正式迁移决策

仅在 X0-A–D 的证据完成后决定是否把主模型迁移到混合架构。该决策是本阶段唯一需要再次请示的路线关口。

## 4. 冻结验收量

| gate | 验收量 | v01 门槛 |
|---|---|---:|
| X0-A | upstream commit/licence 可追溯 | exact / BSD-3 |
| X0-A | upstream remesh tests | pass，或记录可复现工具链 blocker |
| X0-B | topology-only rebind ID/state/weight retention | 100% |
| X0-B | topology-only material-point position error | `<=1e-12` |
| X0-B | force resultant residual | `<=1e-12` |
| X0-B | moment residual | `<=1e-12` |
| X0-C | split/swap/merge material semantics | explicit and tested |
| X0-D | pair force and moment residual | `<=1e-10` |
| X0-D | force directional-derivative residual | `<=1e-6` |
| X0-D | normalized integrated power residual | `<=5e-3` |

所有残差均使用 `max(1, characteristic magnitude)` 归一化；任何门槛调整必须新建版本，不能改写 v01 结果。

## 5. 阶段同步策略

- X0-A/B 完成后形成一次独立提交并同步远端；
- X0-C/D 完成后形成第二次独立提交并同步远端；
- X0-E 只提交决策和证据索引，不重写历史结果。
