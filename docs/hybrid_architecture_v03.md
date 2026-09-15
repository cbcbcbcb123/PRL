---
architecture_id: ARCH-PRL-HYBRID-V03
status: frozen_x0_e_owned_fork
frozen_at: 2026-08-01
inherits_interface: ARCH-PRL-HYBRID-V02
upstream_forked: true
---

# PRL 自有长期混合架构 v03

本版本继承 `hybrid_architecture_v02.md` 已由 X0-C/D 测试冻结的 C++/Python 边界、remesh event、心肌材料状态迁移和单细胞—体积 ECM 耦合接口。本版本只冻结 X0-E 的代码所有权与仓库拓扑，不改变任何 X0-C/D 数值门槛。

## 仓库拓扑

```text
official SimuCell3D
  git.bsse.ethz.ch/.../2024_runser_simucell3d.git
                 |
                 v reviewed import only
prl-cell-engine:upstream/main
  immutable reviewed upstream mirror
                 |
                 v explicit integration
prl-cell-engine:main
  PRL-owned cell/remesh/contact engine
                 |
                 v pinned Git submodule commit
PRL:external/simucell3d
```

| 项目 | 冻结值 |
|---|---|
| owned repository | `https://github.com/cbcbcbcb123/prl-cell-engine` |
| visibility | private |
| official upstream base | `38af45154070b2b08dcdb25cbe629de499f382d9` |
| immutable baseline tag | `upstream-simucell3d-38af451` |
| upstream mirror branch | `upstream/main` |
| owned integration branch | `main` |
| first owned commit | `39436dc` |
| license | BSD 3-Clause retained |

## 所有权边界

- `prl-cell-engine`：闭合细胞表面、接触、局部重网格、逐操作事件 hook、相关并行与性能；
- PRL parent：材料点状态、主动心肌、四面体 ECM、cell–ECM/flow 耦合、总求解器、Python 科研层和证据链；
- Route H：只作为小规模 reference/oracle，历史冻结状态不变。

## 分支与更新纪律

1. `upstream/main` 只接受审查后的官方上游快进，不承载 PRL 修改；
2. `main` 保持官方基线为祖先，所有 PRL 修改通过独立 feature branch 和测试进入；
3. 禁止重写 `main`、`upstream/main` 和 baseline tag；
4. parent PRL 始终固定精确 submodule commit，不跟随浮动分支运行；
5. 每个 cell-engine 发布必须记录上游 base、测试命令、数值行为和 parent submodule commit。

## 下一安全切片

X1-A 只在受控 fork 内加深一个 seam：让上游 `split_edge`、`swap_edge`、`merge_edge` 在每次操作被接受后同步发出 PRL `RemeshEvent`。本切片不同时迁移 ECM、主动收缩或完整 coupled driver。
