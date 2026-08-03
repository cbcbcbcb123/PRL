---
architecture_id: PRL-HYBRID-ARCH-V21
status: frozen_x1_k_v08_revised_fixed_topology_acceptance
contract: CONTRACT-PRL-HYBRID-X1-K-V08-ADJUDICATION
contract_commit: 929973c99d4971c3a151f3e0db8ef7931580293f
fork_commit: e2ed64a26bb5d7c2d878772564fb5ffcca343c3a
x1_k_passed: false
downstream_authorized: false
---

# Hybrid architecture v21 — 固定拓扑原始证据裁决层

## 新增层与不变层

v08 没有改变 C++、受控 fork、力、阻尼、registered owner、legacy cache、已有 evaluator 或历史测试。它在 PRL-owned Python 层增加一个 fail-closed adjudicator：

```text
v05 raw CSV @ 51d606b       v06 raw CSV @ eb3c973       v07 raw CSV @ f4df24c
8 files / Family C D1       10 files / S1 + controls    5 files / structure + time
          \                         |                         /
           +------------------------+------------------------+
                                    |
                                    v
                     byte-exact evidence integrity
              SHA-256 + rows + exact schema + finite values
                region/run/step/global-local-energy closure
                    independent energy-ledger replay
                                    |
                                    v
                     revised D1 global-L2 adjudication
                                    |
                                    v
              revised S1 structure/time + retained QoI gates
                                    |
                                    v
        historical status lane                 revised acceptance lane
   Route H/v02/v04/v06 remain failed     D1/S1 can pass in a new role
                                    |
                                    v
          passed_revised_fixed_topology_d1_s1_acceptance
          X1-K=false; R1/C1/F1=not_executed; downstream=false
```

公共入口 `hybrid.fixed_topology_adjudication.adjudicate_fixed_topology_evidence` 只读取冻结 CSV。任一 required file 缺失、hash/rows/schema 不符、出现非有限值、key 不闭合或 ledger 不能复算，都会抛出 `EvidenceIntegrityError`；不会返回部分科学通过。

## 修订 acceptance role

D1 不再使用 v02 规则 icosphere 全四层瞬时门禁，而使用 v05 已预注册、对称破缺且质量受控的 Family C area-weighted global-L2 语义。valence-5 点态误差从 `0.10957` 增至 `0.14907`，因此 pointwise/uniform claim 永久为 false。

S1 的 mean radius 不再承担跨 `h` 解析空间阶角色。新角色由两部分组成：初始等半径球面 Euler/mean-radius 结构恒等式，以及 source levels 1、4 的一阶时间一致性与 Richardson 门禁。v06 的负空间阶保留在历史 lane，不参与新 S1 聚合。

area、volume、registered-energy 的 v06 空间解析/自收敛、时间污染，以及 v06/v07 全部逐步几何、缓存、`surface_tension_only` ledger、force-clear 和 extraordinary-vertex 局部门禁均从 raw CSV 复算，未放宽阈值。

## Claim boundary

v08 只说明冻结固定拓扑证据在新的数学角色下通过 D1/S1。它不是 X1-K 总通过，不包含 R1 remesh、C1 contact 或 F1 failure persistence，也不授权长期稳定、生理、ECM/flow、FSI、EFE、标定或心脏发育机制结论。
