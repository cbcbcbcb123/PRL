---
decision_id: DEC-PRL-ROUTE-H-STAGE2-NUMERICAL-METHOD-V02
status: approved_under_existing_stage2_authorization
decider: Codex numerical selection within user-approved Stage 2 scope
decided_at: 2026-07-31T10:49:00+08:00
stage2_authorization: DEC-PRL-ROUTE-H-STAGE2-AUTHORIZATION-V01
effective_contract: CONTRACT-PRL-ROUTE-H-STAGE0-V06
effective_freeze: FREEZE-PRL-ROUTE-H-STAGE0-V06-V02
supersedes: DEC-PRL-ROUTE-H-STAGE2-NUMERICAL-METHOD-V01
registered_response_runs_before_decision: 0
nonregistered_preflight_runs_before_decision: 2
---

# Route H Stage 2 数值方法与 Gate A 客观指标决定 v02

## 1. 处置与边界

v01 的两个 `duration=1.2, dt=0.02` 非注册 solver preflight 分别在 physical
projected residual `7.563281e-7` 和 `1.791728e-8` 时由 SciPy 相对函数下降条件
提前停止。二者均不进入 response 指标、Gate 验收或科研结论。没有运行正式
`A0_ZERO`、`A1_ACTIVE`，因此按 specialization 的 pre-response 方法选择条款，
本版在正式 response 数仍为 0 时取代 v01。

本版不改变方程、势能、无量纲参数、离散、时间步、protocol、Gate 指标、阈值或
Gate 顺序。v01 第 3–6 节的 active mechanism、客观 metrics、账本、time
refinement 与停机条件全部原样纳入本决定；唯一覆盖项是 optimizer 停止规则。

## 2. 冻结求解器

每步仍在 frozen global six-constraint gauge 的固定 binary64 SVD null space 内，
最小化 v01 定义的 fully implicit backward-Euler incremental potential。使用
未缩放 objective 与 analytic gradient，以及 SciPy L-BFGS-B：

- `maxiter=200`；
- `maxls=40`；
- `maxcor=20`；
- `ftol=0`，禁用会在小能量尺度上提前满足的函数下降停止式；
- `gtol=1e-10`。

选择 `gtol=1e-10` 的先验理由是：base cell 有 486 个坐标、6 个 gauge 约束，
null space 为 480 维；`||g||_2 <= sqrt(480)||g||_inf`，故该无穷范数目标给
`1e-8` physical projected 2-norm 门槛保留约 4.6 倍余量。最终验收始终重新计算
未缩放 physical projected overdamped residual，必须 `<=1e-8`；gauge increment
residual 必须 `<=1e-12`。

每次 L-BFGS-B accepted iterate 后，用同一未缩放 force blocks 计算 physical
projected residual；一旦 `<=1e-8`，通过固定 callback 正常停止该次 optimizer。
这是单次 optimizer 内的验收停止条件，不是 retry，也不放宽最终重新计算门槛。

不允许 adaptive time step、response-dependent retry 或第二次 optimizer 调用。
optimizer 报告不单独决定有效性；非有限量、physical residual 或 gauge residual
失败即为 `invalid_numerics`。

## 3. 正式运行与冻结

- A0 正式 case：`dt=0.01`, duration `5.0`；
- A1 正式 case：`dt=0.02, 0.01, 0.005`, duration `5.0`；
- base report：`dt=0.01`；
- time refinement：`0.01` 对 `0.005`；
- plateau transverse metrics：固定 `t=3.0`；
- 非零相对差：
  `|q_0.01-q_0.005|/max(1e-8,|q_0.01|,|q_0.005|)`；
- integrated normalized power residual 是零目标残差，两档分别按 `<=0.005`
  验收，其档间差异只报告、不作近零相对除法。

本决定后的短轨迹检查计入 solver manufactured verification；v02 首次 preflight
的最大 physical projected residual 为 `6.351304e-9`，gauge residual 为
`2.056461e-20`。从第一次正式 A0/A1 运行开始，禁止再改变 optimizer、参数、
阈值、metric 或时间步。
