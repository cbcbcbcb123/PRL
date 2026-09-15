---
report_id: REPORT-EFE-NODE1-N1-2C-T32-V01
status: awaiting_human_gate_t32
executor: codex_current_task
execution_date: 2026-08-26
authorization: project_control/efe_node1_n1_2c_p0_p2_authorization_decision_v01.md
contract: project_control/efe_node1_n1_2c_time_refinement_contract_v01.md
execution_scope: p0_p1_p2_only
stopped_at: human_gate_t32
gpu_used: false
external_solver_added: false
---

# EFE Node 1 N1-2c T32 执行与 Human Gate 审阅请求 v01

## Executive conclusion

P0–P2 已按批准范围完成，且已停止在 Human Gate T32：

1. T16→T32 时间细化与审计入口通过测试，原 T16 公共相位在全部五组状态历史中
   逐数组 bitwise 保留；
2. T32 冻结几何 SLS 暖启动通过固定点和相位零父审计；
3. 两个 T32 全耦合事务周期共 64/64 步通过并 create-only 提交，所有 worker PID
   唯一；
4. T32 cycle 2 相对 cycle 1 的五项周期差均低于预登记 `1e-3`，因此可以提交为
   **T32 周期稳态候选**；
5. T16→T32 预览中，总储能波形差最大，为 `1.5759%`。只有两个时间级，尚不能
   判定时间收敛、观察阶或 Richardson 外推；
6. 未执行 T64、T128、空间细化、参数扫描、N1-2d、N1-3、Node 2、GPU worker
   或新外部求解器。

建议人类终审接受 T32 周期态和“重采样只作暖启动”的证据边界，并在需要完成
N1-2c 时间收敛链时另行批准 P3–P4。

## P0 — 专用时间细化入口

新增：

- `src/hybrid/efe_time_refinement.py`；
- `scripts/prepare_efe_node1_n1_2c_t32_warm_start_v01.py`；
- `scripts/run_efe_node1_n1_2c_t32_transactional_cycle_v01.py`；
- `tests/hybrid/test_efe_time_refinement.py`。

验证：

- N1-2c 定向测试：`33 passed`；
- 完整 `tests/hybrid` 回归：`102 passed in 166.93 s`；
- 新增模块和入口 Ruff：通过；
- 注册时间级只允许 16/32/64；16→32 的全部公共相位精确保留；非整数细化和
  非法级别 fail-closed。

工程偏差记录：为不修改 R5 gate-critical driver，T32 wrapper 在加载后把驱动的
`STEPS_PER_CYCLE` 显式设为 32，并将 wrapper/helper 指纹加入父证据集。旧驱动仅有
一处进度字符串仍显示 `/16`；worker 命令、相位、CSV、NPZ、summary 和事务数均经
独立核验为 32 步。该偏差只影响控制台显示，不改变数值输入或结果；T64 前应将其
消除为专用参数化打印，避免审阅歧义。

## P1 — T32 可审计暖启动

来源：接受的 R5 T16 cycle 8；目标：33 个闭周期相位、`dt/T=1/32`。

| Warm-start quantity | Value | Gate | Result |
|---|---:|---:|---|
| Frozen-geometry periodicity residual | `1.0243246582e-15` | `<=1e-12` | pass |
| Candidate internal-state difference | `0` | `<=1e-12` | pass |
| Phase-zero normalized KKT | `3.4346780299e-6` | `<=1e-5` | pass |
| Phase-zero volume residual | `0` | `<=1e-8` | pass |
| Phase-zero minimum ECM `J` | `0.9990252084` | `>=0.5` | pass |
| Phase-zero minimum gap | `0.03912735295` | `>=-1e-12` | pass |

暖启动 checkpoint 为 create-only，数组摘要：
`51fb3fa5564a9d97d62ac75f60fbb075b590c60fd53b975d6b44c40d1a9cfc6f`。

证据边界：重采样的中间相位只用于冻结几何黏弹固定点和相位零重平衡；所有正式
T32 动态证据均来自随后重新求解的 64 个全耦合事务，不把插值状态计作动态结果。

## P2 — 两个 T32 事务周期

执行环境：

- CPU-only FEniCSx/PETSc；
- image `dolfinx/dolfinx:v0.11.0`；
- digest `sha256:2ae4bfbc0d9077268880faf04c72750528bee986c94ab223a2c159969bd56fa8`；
- 容器 `prl-n1-2c-t32-warm-v01` 与 `prl-n1-2c-t32-cycles-v01` 均 exit 0；
- 两周期 wall time `3102.86 s`，cycle solve time 分别 `1492.69 s`、`1569.73 s`。

事务完整性：

- 2 cycles × 32 steps = 64 transactions；
- 64/64 parent oracle pass；
- 64 个 worker PID 唯一；
- 每周期 33 个相位样本；
- 两个 cycle-end checkpoint 均 create-only。

### T32 within-level periodic gate

| Cycle 2 vs 1 quantity | Difference | Gate | Margin to gate | Result |
|---|---:|---:|---:|---|
| Axial-shortening waveform | `1.7504745115e-7` | `<=1e-3` | `5712×` | pass |
| Maximum-interface-traction waveform | `9.5942819087e-6` | `<=1e-3` | `104×` | pass |
| Total-stored-energy waveform | `4.3900670115e-8` | `<=1e-3` | `22779×` | pass |
| ECM `||Z||` waveform | `1.0129482167e-4` | `<=1e-3` | `9.87×` | pass |
| Cycle-end full ECM `Z` | `1.0593502866e-4` | `<=1e-3` | `9.44×` | pass |

周期 2 的安全和主要物理读数：

- maximum KKT `5.7287113901e-8`；
- maximum raw coupling residual `4.6068876518e-5`；
- minimum ECM `J = 0.9877311093`；
- minimum gap `0.01551995332`；
- peak axial shortening `0.1168818493`（`11.6882%`）；
- peak interface traction `0.09772274091`；
- cycle dissipation `2.4782068059e-6`。

### Sensitive phases

T16/R5 曾敏感的 `t/T=0.6875` 与 `0.875` 在两个 T32 周期均通过，KKT 约为
`1.87e-8` 和 `4.03e-8`，未重现 T16 的近门限高 KKT。T32 cycle 2 step 6 需要
6 次耦合、约 134 s，但最终 coupling `2.59e-6`、KKT `2.93e-9`；这是孤立的求解
路径敏感，下一步即恢复常规 2 次耦合。不能把求解器路径改善解释为新物理机制。

## T16→T32 preview — not formal time convergence

比较冻结规则：4097 个共享相位、线性插值、对称归一化 L2。

| Quantity | T16 vs T32 difference |
|---|---:|
| Axial-shortening waveform | `0.635768%` |
| Maximum-interface-traction waveform | `0.628700%` |
| Total-stored-energy waveform | `1.575935%` |
| ECM `||Z||` waveform | `0.408657%` |

几何和牵引波形已较接近，但储能对时间步更敏感。当前只能说“从 T16 到 T32 的
变化被量化且低于 2%”，不能说“已时间收敛”；正式结论必须等待分别过周期门的
T64，并以 T32↔T64 的预登记门裁决。

## Figure and evidence package

阶段图版本包：
`02_图表/Figures/Fig2_n1_2_t32_time_refinement/Fig2_n1_2_t32_time_refinement_v01_20260826/`

- Notebook 已执行；PNG/SVG 自动核验和代理视觉 QA 通过；
- 当前状态为已验证工作版本，等待人类确认，不标记 FINAL；
- PNG SHA-256：`a81afb591635c336f98338dac073b7cd33fd69e9a50cf5ae37eca65ac08fea41`；
- SVG SHA-256：`fdcc8479edf26a427653c60451083ce03255f87127b6f97383969945aae65f19`。

正式结果：

- warm summary SHA-256：
  `fdd2252b3914245febbb1e74fe80f7356af771b467888190b7dd0f56c57f0093`；
- T32 root summary SHA-256：
  `0adc4093c73c1c02a9e6a4a74a6c56f87f1ab83ceac0c786f5ce09be87185a7e`。

## Human Gate T32 decision requested

请人类终审决定：

1. 接受或拒绝 T32 周期稳态候选；
2. 接受或拒绝“重采样只用于暖启动、未污染正式周期证据”的边界；
3. 接受或拒绝保留 T16→T32 预览和阶段图 v01；
4. 是否另行批准 P3–P4：T32→T64 暖启动与两个 T64 事务周期。

建议批准语句：

> 接受 N1-2c T32 周期稳态候选与阶段图 v01；接受重采样仅用于暖启动的证据边界；
> 批准 P3–P4：构造可审计 T64 暖启动并执行两个 T64 事务周期；到 Human Gate
> T64 停止。

该建议不授权 T128、空间细化、参数扫描、N1-2d、N1-3、Node 2、GPU 或新外部
求解器。
