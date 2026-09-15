---
record_id: LOG-PRL-ROUTE-H-STAGE2-GATE-A-V01
status: completed_with_gate_failure
executed_at: 2026-07-31
effective_contract: CONTRACT-PRL-ROUTE-H-STAGE0-V06
effective_freeze: FREEZE-PRL-ROUTE-H-STAGE0-V06-V02
effective_method: DEC-PRL-ROUTE-H-STAGE2-NUMERICAL-METHOD-V02
---

# Route H Stage 2 Gate A 执行记录 v01

## 1. 范围

按用户已批准的 v06 与 Stage 2 授权，仅执行 Gate A。遵守 fail-fast：任何 A1
数值门槛失败即停止，不运行 Gate B–E，不修改参数、阈值、时间步或 optimizer，
不作 adaptive retry。

## 2. 正式运行前

1. 将原逐铰链 Python 循环改为数学等价的 binary64 批量计算。单次被动力评估由
   约 `0.390 s` 降至约 `0.00411 s`。
2. 新旧铰链角最大绝对差 `2.220446049250313e-16`，梯度最大绝对差
   `7.105427357601002e-15`。
3. active directional derivative relative error
   `6.560585841947075e-11`；net force `8.326673160748336e-17`；net moment
   `1.0001076121711529e-16`；rigid-objectivity 最大误差
   `6.661338147750939e-16`；loading input power 为正。
4. 38 项 Stage 1 + Gate A manufactured tests 全部通过，Ruff 通过。
5. v01 数值方法在两次非注册短轨迹 preflight 中被淘汰；没有生成正式 response。
   v02 在正式 response 数为 0 时冻结。v02 冻结后不再改变方法。

## 3. 正式执行

正式 runner 于 `2026-07-31T10:51:37+08:00` 启动。

- `A0_ZERO, dt=0.01, duration=5.0`：500 步通过；所有 response、能量、耗散、
  active power、volume error、centroid drift 均严格为 0；maximum projected
  residual `9.511724923123747e-17`。
- `A1_ACTIVE, dt=0.02`：在 fail-fast solver 内出现 physical projected
  overdamped residual `1.488435e-8`，超过冻结门槛 `1e-8`。同时 gauge increment
  residual `4.634497e-20` 通过 `1e-12` 门槛。optimizer 报告 `ABNORMAL`。
- runner 于 `2026-07-31T10:51:59+08:00` 非零退出。没有进行第二次 optimizer
  调用、retry、阈值修改或 A1 正式重跑。
- fail-fast runner 未持久化失败前的 A1 partial trajectory，因此失败时间节点
  不可从封存证据恢复；本缺口作为检查发现保留，不据此重跑。
- `A1 dt=0.01`、`A1 dt=0.005` 以及 time refinement 未运行。

## 4. 处置

Gate A 状态为 `failed_invalid_numerics`。按 v06 Gate 顺序，Gate B、C、D、E
全部阻断。已封存 A0 全节点 coordinates、time series、summary、manifest，
以及正式 stdout/stderr、失败 acceptance 和 verification results。

数值方法 v02 的 `decided_at` 曾误写为晚于实际运行的占位时间；正式运行后仅把
该元数据从 `11:15` 更正为实际运行前的 `10:49`，没有改变任何方法正文。失败
记录同时保留运行时 hash 与更正后 hash。
