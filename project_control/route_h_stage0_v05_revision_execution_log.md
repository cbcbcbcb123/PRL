---
execution_id: EXEC-PRL-ROUTE-H-STAGE0-V05
executor: Codex current task; approved single-task Stage 1 repair
started_at: 2026-07-30T20:08:00+08:00
completed_at: 2026-07-30T20:12:00+08:00
status: completed
deviation_records: []
---

# Route H Stage 0 v05 浮点并列勘误执行记录

## 1. 触发

Stage 1 reference materialization 在任何 solver 或 response 之前触发
`V05-FACE-TIE-001`：数学上三轴等权的角方向受到 binary64 舍入影响，
使 face 159 被标为 `lateral_x_plus`，其镜像 face 63 却被标为
`apical_lumen`（心肌模板为 `basal_ecm`）。

在 998 个 cell-neighbor master-face ray 检查中，共有 10 个重复实例因此不能命中
合同要求的 mirrored slave subtype。故 v04 的 reference bundle seal 不能成立。

## 2. 修订

新增而不覆盖 v04：

- 绝对分量差不超过 `8*eps_binary64` 时视为并列；
- 固定按 `z → x → y` 解析并列；
- 非并列方向继续使用 v04 原规则。

该修订只影响 8 个数学对称角方向的 material face identity。cell/ECM 坐标、
拓扑、方程、参数、载荷、contact/adhesion、source-map 和测试阈值均不变。

## 3. 制造检查

- corner directions in tie band：8；
- z-dominant corner identities：8/8；
- lateral directional counts：x-/x+/y-/y+ 各 52；
- registered same-layer neighbor master rays：998；
- illegal or missing required-subtype hit：0；
- v04 frozen files modified：0。

## 4. 授权边界

本次是已批准 Stage 1 内的同路线普通阻断修复，不改变科学对象或接触机制。
Stage 1 reference materialization 可在 v05 只读检查通过后继续；Stage 2 仍未授权。
