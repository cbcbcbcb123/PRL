---
report_id: REPORT-PRL-HYBRID-X1-K-V09-R1-FAILURE
contract_commit: f7701d59ce3e1c94737e3b0a276205ed70fae6f8
parent_before_r1: 3d0a8217e869213e34223d7206f4588e7b6e9aca
cell_engine_commit: e2ed64a26bb5d7c2d878772564fb5ffcca343c3a
status: failed_r1_geometry_cache_force_finite_gate
x1_k_passed: false
c1_f1: not_executed
downstream_authorized: false
---

# X1-K v09 R1 remesh-on robustness 失败冻结报告

## 1. 裁决

v09 R1 冻结为 `failed_r1_geometry_cache_force_finite_gate`。首个硬失败发生在 remesh-on 的 step 3：

```text
normalized surface-centroid drift = 0.08373679738719757
frozen threshold                 = 0.01
```

正式响应保留非零退出码 `1`。R1 未通过，X1-K 仍为 false；C1/F1 与 downstream 均未执行、未授权。

## 2. 实际生产路径与事件顺序

两条轨迹使用相同 8-vertex/12-face 单细胞、主动材料、`dt=6.25e-4`、8 steps 与 barycentric-dual-area damping。fixed 分支完整运行 8 steps。remesh 分支严格执行：

1. step 2 owned motion 后，真实 `local_mesh_refiner::split_edge(edge(0,1))`；
2. 同步 `RemeshEvent` 经生产 `MyocardialMaterialTransferSink`；revision `0 -> 1`；
3. step 3 motion 前，真实 `merge_edge(edge(0, split_node))`；
4. 第二个同步事件与材料迁移完成；revision `1 -> 2`；
5. step 3 owned motion 后触发首个几何门禁失败并立即停止。

没有 adaptive remesh、retry、换 edge、坐标恢复、私有注入、伪造事件或阈值调整；受控 fork 未修改。

## 3. 首失败归因

step 2 split 后，fixed 与 remesh 的几何及四个 QoI 仍在舍入精度内一致：area-ratio difference 为 `1.11e-16`，volume-ratio difference 为 `0`，axis difference 为 `1.20e-16`，active-energy difference 为 `4.82e-15`。

step 3 的冻结 merge 不是 split 的几何逆操作。上游 `merge_edge` 删除所选 edge 的两个端点，并在二者 midpoint 新建节点。对 `edge(0, split_node)`，新节点位于原 split edge 的四分之一位置，而不是恢复原 vertex 0。结果为：

```text
surface area ratio             = 0.9149120577912477
volume ratio                   = 0.8749875042125971
normalized surface-centroid drift = 0.08373679738719757
```

这是真实算法行为，不是非有限状态或 cache 错误。step 3 的同级控制均先通过：finite=true，orientation=`0.8086111690 > 0`，triangle quality=`0.6704712803 >= 0.05`，face-area ratio=`0.6933714742 >= 1e-4`，cache residual=`1.54e-16 <= 1e-12`，force-buffer norm=`0`，volume ratio 仍在 `[0.5,1.5]`。

## 4. QoI 与 J1 的停止语义

QoI gate 与 J1 gate 均为 `not_adjudicated_due_to_first_failure`，不得写成通过。

`qoi_comparison.csv` 只保存首失败前后已有状态的 diagnostic-only 复算，不是 gate verdict。step 3 的诊断差为：axis `2.12e-6`、area `8.51e-2`、volume `1.25e-1`、active energy `8.46e-5`；其中 area/volume 已明显超过 `2e-3`，但首失败仍按执行顺序登记为 centroid safety gate。

J1 event ledger 只是已观测 supporting evidence：2 events（1 split/0 swap/1 merge），signed/sum-absolute/max-absolute inter-event change 均为 `0`，`sum(abs(epsilon_alg))=5.20417e-17`，minimum fiber alignment=`1`，maximum rebind error=`1.11022e-16`。这些数值不得越过首失败升级为 J1 gate pass。

## 5. TDD 与失败回归

RED 首先证明缺少 PRL public R1 runner。最小 GREEN 只新增 PRL-owned runner/audit/export/test，串接真实 fork cell/refiner、同步 event、生产 material sink 与 owned step；没有扩展 fork API。

正式模式 `--formal-response` 复现精确科学失败并退出 `1`。常规 CTest 则断言：

- 精确 status=`failed_r1_geometry_cache_force_finite_gate`；
- first failure step=`3`；
- centroid 数值保持 `0.08373679738719757`；
- peer safety controls 均通过；
- QoI/J1 未裁决；
- 原始 event ledger 保留；
- 正式响应退出码为 `1`。

因此 v09 回归测试自身通过，不把正确冻结的科学失败错误计入新的软件回归失败。

## 6. 软件验证

原始日志与 `.exitcode` 均在 `results/hybrid/x1_k_r1_remesh_robustness_v09/verification/`，由 parser 读取并记录 SHA-256、字节数与真实计数：

- parent CTest：53/56，通过；仅 v02/v04/v06 三项历史失败，v09 回归通过；
- controlled fork：134/134；
- strict：`prl_core` 与 v09 source/regression 均以 `-Wall -Wextra -Wpedantic -Werror` 编译通过；
- Python：78/78；
- tracked Python Ruff：通过；
- focused regression：退出 `0`；formal response：退出 `1`。

## 7. 证据与边界

机器入口为 `results/hybrid/x1_k_r1_remesh_robustness_v09/summary.json`。逐步状态、events、material transfer、remesh ledger、diagnostic-only QoI、criteria、配置、provenance、正式响应与复算命令均在同一版本包。

历史语义不变：Route H Gate A v01=`failed_invalid_numerics`；v02/v04/v06 历史失败不改写；v08=`failed_adjudicator_contract_incomplete`；v08r1 只接受为 revised fixed-topology D1/S1 acceptance。不得进入 C1/F1、ECM/flow 长耦合、参数标定或长期、生理、FSI、EFE、发育机制 claim。
