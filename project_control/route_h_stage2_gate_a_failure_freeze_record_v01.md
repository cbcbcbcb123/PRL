---
freeze_id: FREEZE-PRL-ROUTE-H-STAGE2-GATE-A-FAILURE-V01
status: frozen_failed_gate
frozen_at: 2026-07-31T10:55:00+08:00
gate_id: A
gate_status: failed_invalid_numerics
downstream_status: blocked
manifest_id: MANIFEST-PRL-ROUTE-H-STAGE2-GATE-A-FAILURE-V01
manifest_sha256: 3DF39A53396BAD7C0BCF3D770562D181212291B9C7984E3C96A929895D65982C
package_sha256: 7B698C824EE67E9011A0D046E1B9F2E48106902E3B784C7E65AD3078E2012137
file_count: 29
---

# Route H Stage 2 Gate A 失败冻结记录 v01

Gate A v01 证据包冻结为 `failed_invalid_numerics`。冻结对象包含：

- v01/v02 数值方法决定；
- 数学等价的被动力批量化实现、active implementation、Gate A solver 与唯一
  public solver entry；
- manufactured verifier、38 项测试 JUnit 和数值 metrics；
- A0 500 步全节点 coordinates、time series、summary 与 manifest；
- A1 `dt=0.02` fail-fast stdout/stderr 和 failure acceptance；
- v07 verification registry、执行记录和只读科学代码检查；
- v06 contract、specialization、discretization family seal 与 Stage 0 freeze seal。

正式 A1 没有重跑；数值参数、阈值和 dt 没有在正式运行后修改。Gate B–E
保持阻断。

本冻结包不能证明主动单细胞 response、time refinement 或下游耦合通过。若用户
授权后续诊断，必须新建 Gate A v02 诊断/方法版本并保留本失败包不变。
