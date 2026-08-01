---
adr_id: ADR-PRL-0001
title: 自有 C++ 高性能内核与 Python 科研层
status: accepted
accepted_at: 2026-08-01
decision_owner: project user
applies_from: X0-C
fork_gate: X0-E
---

# ADR-PRL-0001：自有 C++ 高性能内核与 Python 科研层

## 背景

SimuCell3D 提供了闭合细胞表面、接触和局部动态重网格能力，但上游代码是论文配套实现，不能直接承担本项目长期的软件边界。本项目还需要跨重网格保存心肌区域、纤维方向、主动状态和 tether 身份，并与独立四面体 ECM、后续血流求解器建立守恒耦合。

如果业务代码直接依赖上游 face ID、指针或类层次，重网格细节会扩散到主动收缩、ECM 和耦合模块；如果立即从零重写，网格拓扑、接触与并行复杂度不会消失，只会全部转移给本项目。

## 决策

1. 项目按自有长期平台建设，产品边界是 PRL cardiac-cell–ECM–flow model，而不是“SimuCell3D 修改版”。
2. 高性能计算内核使用 C++17；Python 负责算例配置、参数扫描、校准、分析、可视化和可复算证据。
3. Python/C++ 只通过粗粒度公共接口交换状态；禁止在逐节点、逐面或逐时间步内循环中频繁跨语言调用。
4. SimuCell3D 在 X0-C/D 期间保持固定提交、只读依赖，通过 PRL 自有 value types 和 adapter seam 隔离；上游指针、临时 face ID 和内部类不得越过公共边界。
5. 每个被接受的 edge split、edge swap、edge merge 必须产生一个同步 `RemeshEvent`，携带同一细胞的 before/after revision 和 PRL-owned mesh snapshots。后续拓扑操作不得早于该事件的状态迁移与审计完成。
6. 生物学状态由 persistent material-point ID 拥有；网格只负责定位。区域身份、主动状态、纤维方向和 reference weight 均不得由 face ID 拥有。
7. X0-C/D 用公共行为测试冻结接口。X0-E 才允许建立保留历史与 BSD-3 归属的受控 fork。

## 长期组件边界

| 自有组件 | 责任 | 稳定入口 |
|---|---|---|
| cell engine port | 闭合细胞表面、接触候选、重网格事件 | `RemeshEventSink` 与 PRL mesh snapshot |
| material-state transfer | persistent ID、区域、纤维、主动状态、reference weight | 一次事件一次 transfer + audit |
| active myocardium | 激活、纤维主动张力、细胞内状态更新 | material-point state update |
| cell–ECM coupling | 非匹配 tether、作用—反作用、非穿透、功率端口 | coupled evaluation/audit |
| tetrahedral ECM | 有限变形超弹—黏弹本构与内部变量 | energy/force/state update |
| coupled driver | 时间积分、求解顺序、失败策略、功率总账 | coarse simulation step |
| Python research layer | 配置、实验、校准、分析、证据导出 | coarse run/evaluate API |

## X0-E 受控 fork 条件

满足以下任一条件时，X0-E 应采用受控 fork，而不是继续堆叠外部补丁：

- 必须修改 SimuCell3D remesher 内部才能逐操作发出同步事件；
- 需要在三个或以上上游模块携带非平凡补丁；
- 上游私有类型或生命周期无法被 adapter 隔离；
- 上游构建、并行或测试入口无法满足本项目 CI；
- 无可用的持续上游合并路径。

受控 fork 必须保留上游提交历史、许可证和来源说明，并在行为测试保护下逐模块替换；不得一次性重写全部 remesher/contact 实现。

## 后果

- 优点：科学状态所有权、守恒审计和长期演进权归本项目；上游算法可替换；C++ 保留规模性能，Python 保留科研可用性。
- 成本：项目必须维护 C++ 工具链、CI、ABI/API 版本、性能基准和许可证记录。
- 当前限制：X0-C/D 只冻结接口与单细胞—单 ECM patch 垂直切片，不宣告多细胞规模、主动收缩、完整时间积分、血流耦合或生理标定完成。
