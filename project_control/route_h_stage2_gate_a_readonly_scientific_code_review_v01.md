---
review_id: REVIEW-PRL-ROUTE-H-STAGE2-GATE-A-V01
status: reviewed_failed_gate
review_mode: readonly_after_formal_failure
reviewed_at: 2026-07-31
---

# Route H Stage 2 Gate A 只读科学与代码检查 v01

## 结论

Gate A **不通过**。失败结论由冻结的 numerical residual gate 直接触发，不是由
轴向缩短、横向响应或体积等科研 response 指标触发；这些指标在
`invalid_numerics` 后没有资格评价。Gate B–E 必须保持未运行。

## 已确认

1. active preferred-length energy、analytic force、input-power sign 与合同一致。
2. active force 为中心内力；manufactured net force/moment 与 rigid objectivity
   均低于 `1e-10`。
3. 六约束 gauge 使用冻结 dual-area weights；失败步 gauge residual
   `4.634497e-20`，不是失败来源。
4. A0 在 500 步内保持 reference zero state；其全轨迹证据已持久化并有 SHA-256。
5. 被动力批量化保持 scalar kernel 数值等价，且 33 项 Stage 1 测试（含新增等价
   测试）和 5 项 Stage 2 manufactured tests 共 38 项通过。
6. 正式 A1 首档未使用 retry，未修改容差或参数；停止顺序符合预注册。

## 阻断发现

### F-A1：冻结求解器未达到 physical residual gate

- observed：`1.488435e-8`
- limit：`1e-8`
- ratio：`1.488435`
- disposition：`fail Gate A; block Gate B–E`

这表示 v02 的单次 L-BFGS-B 增量势求解在至少一个正式 A1 时间步没有提供足够
可靠的离散平衡解。不能把该步当作 accepted state，也不能用其 response 评价
模型机制。

### F-A2：失败节点的 partial trajectory 未持久化

fail-fast exception 发生在 runner 返回 trajectory 之前，因此只保留 residual、
gauge residual 与 optimizer message，未保留失败时间节点和最后一个 accepted
state。该证据缺口不改变 F-A1 的门槛判定，但降低后续诊断定位能力。为避免正式
response 重跑，本阶段不补算。

### F-A3：v02 决定时间戳元数据更正

运行时决定文件 hash 为
`CF5C6D6708035210403F5E5C1B4912B91A8B47B81F9E694048F8452B4106CFB2`。
只读检查发现 `decided_at` 误晚于运行，随后仅更正该时间戳；更正后 hash 为
`9C53EB3DA0FF59280DB071577EBC7EB27B4EB9AC62324BF50EA09E555F0359F3`。
方法正文与运行代码未改变。

## 不允许的解释

- 不能宣称 A1 contraction/transverse/volume/power 或 time refinement 通过；
- 不能把 `1.488435e-8` 四舍五入为通过；
- 不能把 preflight response 当作正式 case；
- 不能在本冻结包内调整 `gtol`、`ftol`、residual limit、dt 或主动参数；
- 不能启动 Gate B–E。

下一步若继续，必须由新的明确决定授权“Gate A 数值诊断/方法修订”，并创建新
版本；不得覆盖本失败包。
