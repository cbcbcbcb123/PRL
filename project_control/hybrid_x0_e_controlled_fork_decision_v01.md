---
decision_id: DECISION-PRL-HYBRID-X0-E-V01
status: accepted_executed
decided_at: 2026-08-01
authorization_source: user directive to execute controlled fork at X0-E
parent_branch: codex/simucell3d-hybrid-feasibility
owned_repository: https://github.com/cbcbcbcb123/prl-cell-engine
---

# Hybrid X0-E 受控 fork 决策与执行记录 v01

## 决策

正式采用“PRL 自有 C++ 高性能内核 + Python 科研层”的混合架构作为长期目标。SimuCell3D 不再是不可控的外部产品边界，而是受控 fork 的算法祖先。现有 Route H 保留为 reference/oracle，不作为大规模生产引擎，也不改写其已冻结结果。

## 决策依据

- X0-A：官方来源、BSD-3、构建和 5 项 remesh tests 已验证；
- X0-B：topology-independent material registry 已通过 ID/state/weight、合力和力矩守恒；
- X0-C：split/swap/merge 的区域、纤维和主动状态语义已由 Python 行为测试及 C++17 合同冻结；
- X0-D：单闭合细胞—单四面体 ECM 垂直切片已通过合力、力矩、能量导数、功率、非穿透和正 Jacobian 门槛；
- 上游 remesher 没有满足冻结合同的逐操作同步事件 hook，因此继续只用外部 submodule 会让私有实现泄漏到材料状态迁移层。

## 已执行操作

1. 创建私有仓库 `https://github.com/cbcbcbcb123/prl-cell-engine`；
2. 完整保留官方上游 4 个提交的历史，以 `38af45154070b2b08dcdb25cbe629de499f382d9` 为基线；
3. 创建只读镜像分支 `upstream/main`；
4. 创建不可变基线 tag `upstream-simucell3d-38af451`；
5. 在 owned `main` 增加 fork policy，首个 owned commit 为 `39436dc`；
6. PRL 的 `external/simucell3d` submodule URL 改为 owned repository，并继续固定精确 commit；
7. 未在 fork bootstrap 中修改任何力学、接触或 remesh 算法。

## 验收

| 检查 | 结果 |
|---|---|
| official base remains ancestor of owned main | passed |
| upstream mirror points to official base | passed |
| baseline tag points to official base | passed |
| BSD-3 license retained | passed |
| parent submodule uses owned remote | passed |
| owned fork GitHub Actions CMake run at `39436dc` | passed |
| parent X0-C/D tests | `14 passed` |
| parent Stage 0/1/2 regression | `49 passed` |
| parent C++ contract test | `1/1 passed` |

## 未宣告内容

X0-E 只完成所有权迁移和受控 fork bootstrap。它不代表逐操作 event hook、C++ 状态迁移实现、多细胞规模、主动收缩、流体耦合、长期积分或生理标定已经完成。

## 下一阶段

进入 X1-A：在 `prl-cell-engine` 中为 split/swap/merge 增加同步 remesh event hook，并以 PRL 的 `RemeshEventSink` 行为合同和上游 remesh tests 保护该修改。
