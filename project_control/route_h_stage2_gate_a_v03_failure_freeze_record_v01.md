---
freeze_id: FREEZE-PRL-ROUTE-H-STAGE2-GATE-A-V03-FAILURE-V01
status: frozen_failed_gate
frozen_at: 2026-08-05T01:21:07+08:00
gate_id: A
gate_status: failed_invalid_numerics
failed_run_id: A1_ACTIVE_dt0.02
failure_step: 86
failure_time: 1.72
last_accepted_time: 1.70
manifest_id: MANIFEST-PRL-ROUTE-H-STAGE2-GATE-A-V03-FAILURE-V01
manifest_sha256: 5A42F79E42684F5A28C94036713E73F3F235D6C8EA49B39B7838F409B32FE51A
package_sha256: 90E877F2259BBAD5C364A308A6D800CCF4F5E6DE6F980B4B050DDFD578DBA22B
file_count: 51
preserves: FREEZE-PRL-ROUTE-H-STAGE2-GATE-A-FAILURE-V01
---

# Route H Stage 2 Gate A M1 v03 失败冻结记录 v01

M1 v03 证据包冻结为 `failed_invalid_numerics`。本冻结不覆盖 Gate A v01 失败包，
而是保存新的数值接受机制、RED–GREEN 测试、正式 fail-fast 轨迹、step86 只读诊断、
科研审阅图版本包、执行记录和同任务只读自检。

冻结事实：

- A0 `dt=0.01` 完整到达 `t=5.0`；
- A1 `dt=0.02` 修复原 step79 后接受至 step85、`t=1.70`；
- step86、`t=1.72` returned residual `1.980868094e-8 > 1e-8`；
- 162 次目标评估的最小 trial residual 为 `1.310584667e-8`，0 次达标；
- rejected candidate 有限、正体积、无翻面和退化；
- 按合同未继续 `dt=0.01/0.005`，Gate A 未通过。

本冻结可证明 M1 v03 对旧失效机制的修复和新数值限制的定位，不能证明完整自由收缩、
time refinement、生理有效性或下游 Gate。后续若获用户批准，必须另建 M1 v04 合同并
保持本包、原 Gate A v01 包和 `1e-8` residual 门槛不变。
