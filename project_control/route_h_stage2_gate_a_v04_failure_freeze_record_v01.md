---
freeze_id: FREEZE-PRL-ROUTE-H-STAGE2-GATE-A-V04-FAILURE-V01
status: frozen_failed_gate
frozen_at: 2026-08-09
gate_id: A
gate_status: failed_invalid_numerics
failed_run_id: A1_ACTIVE_dt0.02
failure_step: 194
failure_time: 3.88
last_accepted_time: 3.86
contract_id: CONTRACT-PRL-ROUTE-H-STAGE2-GATE-A-CURVATURE-MEMORY-V04
preserves: FREEZE-PRL-ROUTE-H-STAGE2-GATE-A-V03-FAILURE-V01
---

# Route H Stage 2 Gate A M1 v04 失败冻结记录

M1 v04 正式套件在 `A1_ACTIVE, dt=0.02` 的 step 194、`t=3.88` 因 projected residual `1.199104775e-8` 超过冻结门槛 `1e-8` 而停止。最后接受节点为 step 193、`t=3.86`。

失败候选有限、正体积、0 翻面、0 退化面，relative volume `0.999902226`；候选未写入有效轨迹。`dt=0.01` 与 `dt=0.005` 未运行，time refinement 不存在，Gate A 未通过。

本冻结保留 v03 全部失败证据。后续任何诊断、预条件或直接平衡求解必须建立新版本，不得覆盖 v04 源码、正式结果、图版本包或本冻结记录，也不得放宽 residual、gauge、体积或几何门槛。
