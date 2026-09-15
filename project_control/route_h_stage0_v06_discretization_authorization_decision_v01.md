---
decision_id: DEC-PRL-ROUTE-H-STAGE0-V06-DISCRETIZATION-V01
status: approved
decider: user
decided_at: 2026-07-31T09:35:21+08:00
related_preflight: PREFLIGHT-PRL-ROUTE-H-STAGE2-DISCRETIZATION-V01
related_plan: PLAN-PRL-ROUTE-H-DCM-ECM-STAGE0-STAGE2-V01
working_branch: codex/stage0-v06-discretization
---

# Route H Stage 0 v06 空间离散族授权决定

## 用户决定

用户明确回复：

> 批准 v06 方案，继续

据此批准执行
`project_control/route_h_stage2_preflight_discretization_block_v01.md`
第 2 节所列的 v06 修订：

| level | cell surface subdivision | 每细胞 vertices/faces | ECM intervals `(n_x,n_y,n_z)` |
|---|---:|---:|---:|
| coarse | 1 | 42 / 80 | 6 / 4 / 2 |
| base | 2 | 162 / 320 | 12 / 8 / 2 |
| fine | 3 | 642 / 1280 | 24 / 16 / 4 |

## 连续执行授权

允许在不再逐项请示的情况下完成：

1. v06 生成器参数化与三套 identity-bearing geometry materialization；
2. face identity、anchor、tether、source map、boundary owner 与 gauge arrays 的封存；
3. base 对 v05 的逐字节复用检查；
4. manifold、orientation、positive tetra、reference force/moment、zero steric、
   coverage、hash replay 与最后两级 `<=3%` 空间细化判据注册；
5. 同一 v06 路线内的普通生成/校验修复、版本递增、冻结和单工作者只读检查；
6. 正常 commit/push 和阶段 GitHub 同步；
7. v06 无 blocking finding 后，关闭 `STAGE2-DISCRETIZATION-BLOCK`，返回已授权的
   Stage 2 并严格从 Gate A 开始。

## 不变边界

- v01–v05 历史冻结文件与 Stage 1 v02 证据保持不可变；
- 不改 patch bounds、细胞数、方程、力学无量纲参数、接触/黏附势、血流载荷、
  功率账本或 Gate A–E 顺序；
- 不新增 periodic case、turnover、非零 `j_myo`、参数 sweep、生理标定或论文 claim；
- 不删除项目材料、不重写 Git 历史、不 force push；
- 命中新的科学 falsifier、必须改变上述不变边界或需要新的核心路线选择时立即停机。
