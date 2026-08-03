---
architecture_id: PRL-HYBRID-ARCH-V22
status: frozen_v08r1_adjudicator_repair
contract: CONTRACT-PRL-HYBRID-X1-K-V08R1-ADJUDICATOR-REPAIR
contract_commit: a500893e86c2d5415a48a8458a8a0c2f7eb721ce
fork_commit: e2ed64a26bb5d7c2d878772564fb5ffcca343c3a
x1_k_passed: false
downstream_authorized: false
---

# Hybrid architecture v22：v08r1 可审计证据裁决层

## 架构变化

v22 不改变任何力学路径。新增和修复均位于 PRL-owned Python 审计层：

```text
v05/v06/v07 frozen raw CSV
              |
              v
  current-file integrity
  SHA-256 / rows / schema / finite / key closure
              |
              v
  Git source-object integrity
  commit^{commit} exists
  commit:path is a blob
  source blob bytes == current raw bytes
  source_blob_id == current_blob_id
              |
              v
  semantic reconstruction
  v05 per-region fractions
  v05 global normal L2 from E/A/v_exact
  v05 four error-energy orders over actual h
  v06/v07 trajectories, QoI and ledgers
              |
              v
  revised D1/S1 decision lane
              |
              +------------------ limitation lane
              |                   pointwise series required
              |                   claims forced false
              |                   never gates D1
              v
  repaired scientific decision
              |
              v
  real verification evidence parser
  five logs + five exit codes + parsed counts/failures
              |
              v
passed_revised_fixed_topology_d1_s1_acceptance_after_adjudicator_repair
X1-K=false; R1/C1/F1=not_executed; downstream=false
```

## Fail-closed seam

`adjudicate_fixed_topology_evidence_after_repair` 是 v08r1 科学裁决入口。
`adjudicate_verification_evidence` 是机器验证入口。前者不读取 summary 自报，后者没有硬编码
通过数的回退路径。缺 Git object、blob 字节不一致、语义字段不闭合、日志/exit code 缺失或
测试集合不符都会抛出结构化异常，不返回部分通过。

EvidenceSpec 可在测试中注入，但生产默认仍是 23 个冻结 spec。篡改测试在临时 Git 仓中把
修改后的字节、SHA-256 与 source commit 同步冻结，从而证明 semantic reconstruction 独立于
字节完整性检查。

## 历史与 claim 边界

v08 的 `failed_adjudicator_contract_incomplete` 与 Route H、v02、v04、v06 历史失败均保留。
v08r1 只修复裁决软件，不增加新的物理证据，不构成 X1-K 通过，也不授权 remesh、contact、
failure persistence、ECM/flow、参数标定、长期稳定、生理、FSI、EFE 或心脏发育机制结论。
