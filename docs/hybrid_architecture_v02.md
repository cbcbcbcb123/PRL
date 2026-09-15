---
architecture_id: ARCH-PRL-HYBRID-V02
status: frozen_x0_cd_interface
frozen_at: 2026-08-01
supersedes_for_future_work: hybrid_architecture_v01.md
upstream_forked: false
---

# PRL 自有长期混合架构 v02

## 总体结构

```text
Python research layer
  cases | calibration | parameter studies | analysis | evidence export
                         |
                         v  coarse stable API
PRL C++ core
  cell engine port
  remesh event + myocardial material-state transfer
  active cardiomyocyte mechanics
  nonmatching cell–ECM coupling and power ledger
  tetrahedral finite-strain viscoelastic ECM
  coupled driver
                         |
                         v  replaceable adapter
SimuCell3D-derived topology/remesh/contact algorithms
```

Route H 继续作为小规模 reference/oracle，不承担大规模生产路径，也不覆盖其已冻结的 Stage 2 Gate A 数值失败。

## X0-C 冻结接口

公共 C++ 合同位于 `cpp/include/prl/core/remesh_contract.hpp`，Python 可执行参考位于 `src/hybrid/remesh_transfer.py`。

事件规则：

1. 一个事件只表达一个已接受的 `edge_split`、`edge_swap` 或 `edge_merge`；
2. `after_revision > before_revision`；
3. 事件、before snapshot 和 after snapshot 必须属于同一稳定 cell ID；
4. adapter 同步发出事件，在下一次拓扑编辑前完成状态迁移与审计；
5. 公共数据仅使用 PRL value types，不暴露上游指针或临时 face ID。

材料场规则：

- 区域限定为 apical、basal、lateral；
- 主动状态按 persistent material-point ID 精确复制；
- 纤维先投影到新宿主面的切平面，再单位化，并以原方向选择 director 符号；
- 迁移后必须报告区域保持率、主动状态残差、纤维模长误差、切向误差、最小方向对齐度和几何重绑定误差；
- 无法在冻结距离内重绑定、输入纤维不切向或投影退化时 fail-fast。

## X0-D 冻结接口

`CellECMVerticalSlice` 封装一个闭合双流形细胞表面、持久材料点 tether 和一个独立四面体 ECM patch。其公共行为包括：

- 对 cell surface remesh 前后保持 tether 能量和合力；
- 将 tether 局部力散射到 cell 与 ECM 两侧；
- 同时返回 ECM 体力、Jacobian、作用—反作用残差和功率审计；
- 对开放细胞表面、非正 ECM Jacobian 和 cell–ECM 穿透 fail-fast；
- 总能量方向导数与总力一致。

## C++/Python 边界

当前 Python 实现是接口的可执行科学规范，不是最终大规模内循环。进入生产迁移后：

- remesh、contact、active mechanics、tether assembly、ECM assembly 和 coupled step 位于 C++；
- Python 仅提交一个算例/参数包并接收批量状态或结果；
- NumPy reference/oracle 保留，用于 manufactured tests、交叉验证和回归诊断。

## 阶段状态

| 阶段 | 状态 | 说明 |
|---|---|---|
| X0-A | passed | 上游来源、许可证、构建和 remesh tests 已验证 |
| X0-B | passed | topology-independent material registry 已验证 |
| X0-C | passed | 心肌材料场与 C++ adapter 合同已由测试冻结 |
| X0-D | passed | 单细胞—体积 ECM 垂直切片已通过守恒门槛 |
| X0-E | pending | 尚未创建受控 fork；只在正式迁移决策后执行 |
