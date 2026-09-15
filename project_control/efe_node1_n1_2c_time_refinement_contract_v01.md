---
plan_id: PLAN-EFE-NODE1-N1-2C-TIME-REFINEMENT-V01
status: accepted_completed_with_p6_followup
planner: codex_current_task
approved_by: human_final_reviewer
approved_at: 2026-08-26
executor: codex_current_task
inspector: human_final_reviewer
related_memory_entries: []
execution_authorized: completed_no_further_execution
latest_authorization: project_control/prl_independent_theory_mainline_decision_v01.md
latest_inspection: project_control/prl_p6_t128_execution_and_human_gate_review_v01.md
followup_plan: project_control/efe_node1_n1_2c_p6_t128_targeted_validation_contract_v01.md
final_acceptance: project_control/prl_p6_t128_acceptance_and_spatial_tolerance_drafting_authorization_decision_v01.md
required_parent_decision: accept_r5_t16_periodic_candidate
---

# EFE Node 1 N1-2c：T16/T32/T64 时间细化合同 v01

## Goal

在完全固定 D0/E0/F150 几何、材料、激活、界面、求解门和空间离散的前提下，
分别获得 T16、T32、T64 的周期稳态解，分离“同一时间步内的周期误差”和“不同
时间步之间的离散误差”，判定当前健康三层快速心搏基线是否达到 Node 1 预登记的
时间收敛标准。

本合同只回答：

> 当前 D0/E0/F150 周期解对时间离散是否足够稳定，哪些全局、局部和黏弹记忆
> 读数可以进入后续全 FEM 共同极限及机制扫描。

不回答空间收敛、参数有效性、EFE 机制、实验一致性或 DCM 必要性。

## Lifecycle And Hard Preconditions

当前生命周期为 `p6_draft_pending_human_review`。P0–P2 已完成并经人类终审
接受；P3–P4 的 T64 暖启动和两个周期也已执行完成并由人类接受；P5 三档时间
裁决已由人类接受，正式 Figure 2 v01 已冻结为 FINAL。预登记总门未完全通过。
P6 T128 定向验证合同仅已起草，T128 仍未授权。T32 证据见
`project_control/efe_node1_n1_2c_t32_execution_and_review_request_v01.md`，最新授权见
`project_control/efe_node1_n1_2c_p5_acceptance_and_p6_drafting_authorization_decision_v01.md`，
T64 审阅材料见
`project_control/efe_node1_n1_2c_t64_execution_and_review_request_v01.md`，P5 最终
审阅材料见
`project_control/efe_node1_n1_2c_p5_time_adjudication_execution_and_review_request_v01.md`。
P6 草案见
`project_control/efe_node1_n1_2c_p6_t128_targeted_validation_contract_v01.md`。

执行前必须同时满足：

1. 人类终审以受控决定记录接受 R5 为有效 T16 周期稳态候选；
2. 人类批准本合同及首批仅 T32 的执行范围；
3. R5 warm start、cycle 7/8、源脚本指纹、门限和结果目录保持可读；
4. 不修改或覆盖 R5 已用于证据的 gate-critical 脚本；
5. T32 所需 CPU 容器、磁盘和最长运行窗口经执行前检查；
6. 若任何阶段拟启动 GPU worker，必须按项目规则另行提前获得人类确认；本合同
   预计使用现有 CPU FEniCSx/PETSc 路线，不需要 GPU。

## Inputs

### Frozen scientific input

- `D0` 心肌细胞、`E0` ECM、F150 横向 footprint；
- 周期 `T=1`，峰值激活 `0.20`，同一解析余弦波形和相位原点；
- `mu_ve=0.5`、`eta_ve=0.5`、同一有限应变 SLS 更新；
- 同一心肌/心内膜面积、弯曲、主动纤维、精确体积约束；
- 同一双界面 tether/contact、周围支承、材料参数和网格；
- Picard 最大 12 次，KKT `<=1e-5`，raw coupling `<=1e-4`；
- 体积残差 `<=1e-8`、`min J>=0.5`、`min gap>=-1e-12`、
  最小面面积比 `>=0.05`；
- 周期门：四条波形和周期末完整 ECM `Z` 均 `<=1e-3`。

除时间步数外，任何物理、空间或求解门限变化都属于未授权偏差。

### T16 reference

正式参考仅允许使用经人类接受后的：

- `results/hybrid/efe_node1_n1_2b_r5_reperiodized_warm_start_v01_20260820/`；
- `results/hybrid/efe_node1_n1_2b_r5_transactional_cycle_v01_20260820/cycle_08/`；
- R5 cycle 8 的相位时序、状态、末态检查点和源指纹。

R5 当前为 `completed_periodic_candidate_pending_human_review`；在接受决定产生前，
这些文件只能用于合同设计，不能作为 T32 正式输入。

## Outputs

1. 不修改 R5 代码的 N1-2c 专用时间细化入口和测试；
2. T16→T32、T32→T64 的可审计周期历史重采样和 SLS 暖启动；
3. T32、T64 每级最多两个正式事务验证周期；
4. 各级周期稳态门和逐步几何/求解器安全门；
5. T16/T32/T64 的统一相位比较、积分量、峰值、相位、耗散和局部场差；
6. 观察阶、Richardson 估计或“不可估计/非单调”的明确记录；
7. 成本、敏感相位、失败停止状态和未运行级别；
8. 一张阶段科研审阅图及可复算 Figure 包；
9. 执行报告和人类终审请求。

## Core Definitions

### 1. 两类误差必须分开

对每个时间级别 `Tk`：

1. **周期误差**：同一 `Tk` 最后两个连续周期之差；
2. **时间离散误差**：已分别过周期门的 `T16/T32/T64` 最后周期之差。

周期门通过不能替代时间离散门，T32 与 T16 接近也不能证明 T32 自身达到周期态。

### 2. 时间级别

| Label | Steps/cycle | `dt/T` | Formal role |
|---|---:|---:|---|
| T16 | 16 | `1/16` | 已完成、待人类接受的粗级 |
| T32 | 32 | `1/32` | 首个待批准执行的中级 |
| T64 | 64 | `1/64` | 仅在 T32 通过并经新的人类门后执行的细级 |

T64 不由本合同的 T32 批准自动触发。

### 3. 统一比较规则

- 标量周期波形使用冻结的 4097 点公共相位网格和线性插值；
- T16/T32/T64 共有的 `t/T = 0, 0.25, 0.5, 0.75, 1` 相位用于三维场
  直接比较，不使用最近索引替代；
- 峰值相位使用同一 4097 点 dense-linear 规则；
- 周期积分使用同一梯形规则；
- 所有相对差采用对称归一化，分母为两者范数最大值并设定固定机器零保护；
- 任何新增滤波、平滑、选择性相位剔除或结果后插值规则均禁止。

### 4. 时间细化观测量

全局/波形：

- 轴向缩短；
- 最大和 p95 双界面牵引；
- 总储能、ECM 平衡能、黏弹能；
- ECM `||Z||`；
- cycle dissipation；
- `min/max J`、min gap、面积比、体积误差；
- KKT、raw coupling、迭代次数和单步耗时。

场量：

- 心肌、ECM、心内膜位移；
- ECM `J`、主应变、Cauchy 应力和耗散；
- 两界面法向/切向牵引及其 p95；
- ECM 内部变量 `Z`。

若当前结果 schema 尚不含某个场量，必须在执行前预注册派生公式并从冻结状态重新
计算，不能用新增模型求解替代后处理。

## Implementation Steps

### P0 — 非执行准备与代码隔离

1. 新建 N1-2c 专用 driver/helper，不修改 R5 gate-critical 脚本；
2. 将 `steps_per_cycle`、运行标签、输出 schema 和相位打印从常量改为 N1-2c
   专用显式参数；
3. 保留每步新鲜 worker、父 oracle、create-only 提交和输入摘要不变；
4. 每个时间级别使用独立输出根目录，若已存在即 fail-closed；
5. 结果中封存 N1-2c 父/worker/后处理源指纹及其直接输入摘要；
6. 用合成无求解数据先测试 16→32→64 相位、目录和比较逻辑。

现有 R5 driver 把 `STEPS_PER_CYCLE=16` 写成常量；现有 warm-start initializer
要求源 history 长度等于目标步数。因此直接传 `--steps 32/64` 不成立，必须先
完成下述受控重采样。

### P1 — T16→T32 可审计暖启动

1. 从经接受的 R5 cycle 8 读取 17 个闭周期状态；
2. 用冻结的逐坐标周期线性规则将 ECM 几何历史映射到 33 个相位；
3. 不插值或拟合新物理参数；末态 cell variables/contact multipliers 仅作为
   phase-zero 重平衡初猜；
4. 在 33 相位冻结 ECM 几何上，用 `dt=1/32` 的同一 exact SLS recurrence
   解析求其离散周期 `Z`；
5. phase zero 重新机械平衡，并用 R5 同一父 oracle 审计 KKT、体积、`J`、gap、
   面质量及 `Z` 对称/无迹；
6. 重采样审计至少记录源/目标相位、端点差、几何插值残差、冻结几何周期残差、
   candidate `Z` 差和 create-only digest；
7. 暖启动只是初态，不计作 T32 周期或时间收敛证据。

### P2 — T32 两周期 pilot

1. 从接受的 T32 暖启动执行 `cycle_01–02`，共 64 个顺序事务；
2. 每步新鲜 CPU worker，输入只来自上一步接受检查点；
3. 任一步失败立即停止，不提交候选，不跨步续算，不自动放宽门限；
4. cycle 1→2 应用原五项 `<=1e-3` 周期门；
5. 若 T32 两周期未过周期门，停止并提交失败/未稳态证据；不得自动追加周期、
   重新解析周期化或进入 T64；
6. 若通过，生成 T16↔T32 的**预览比较**，但不宣称三档时间收敛。

### Human Gate T32

人类终审决定：

- 接受/拒绝 T32 周期态；
- 是否接受重采样暖启动只用于加速而未污染正式周期；
- 是否保留 T16↔T32 预览；
- 是否批准 P3–P4 的 T64 暖启动与两个周期。

### P3 — T32→T64 可审计暖启动

仅在 Human Gate T32 批准后执行，与 P1 相同，但源为接受的 T32 最后周期，目标
为 65 相位和 `dt=1/64`。不允许直接从 T16 跳到 T64 作为正式细级初态。

### P4 — T64 两周期

1. 执行 `cycle_01–02`，共 128 个顺序事务；
2. 使用与 T32 完全相同的父 oracle、事务和停止规则；
3. cycle 1→2 通过五项周期门后，才进入三档时间比较；
4. 若未通过，停止，不自动追加周期或进入 T128。

### P5 — 三档时间裁决与审阅图

1. 比较各自最后一个已过周期门的周期；
2. 计算 T16↔T32、T32↔T64 的波形、积分、峰值、相位、耗散和场误差；
3. 对高于机器/求解噪声且符号一致的标量，计算

\[
p=\log_2\frac{|Q_{16}-Q_{32}|}{|Q_{32}-Q_{64}|}.
\]

4. 只有差值单调、分母不接近零且观察阶稳定时才报告 Richardson 外推；否则写
   `order_not_identifiable` 或 `nonmonotone_time_refinement`；
5. 生成科研审阅图，至少包括周期波形叠加、误差门、耗散/相位、敏感相位残差、
   三维峰值场差及结论边界；
6. 在人类终审前不把 T64 写入稳定项目记忆或正式论文 Figure 2。

## Sensitive Phases And Solver Monitoring

R5 已识别以下必须保留的相位诊断：

| R5 phase | T32 step | T64 step | R5 evidence |
|---:|---:|---:|---|
| `0.25` | 8 | 16 | cycle 8 step 4 fallback，约 `492.67 s` |
| `0.6875` | 22 | 44 | cycle 8 step 11 KKT `9.4701e-6`，接近门限 |
| `0.8125` | 26 | 52 | cycle 7 step 13，10 次耦合迭代 |
| `0.875` | 28 | 56 | cycle 7 step 14 KKT `8.8584e-6` |

每个时间级别必须单列这些相位的 KKT、raw coupling、迭代路线、fallback、耗时、
`min J` 和 gap。细化后相位位置改变不是删除诊断的理由。

## Cost And Resource Estimate

R5 两个 T16 周期共 32 个事务，动态部分耗时 `2918.89 s`，平均约
`91.2 s/transaction`；单个敏感事务最高约 `492.67 s`。

在不承诺线性缩放的前提下，CPU-only 暂估：

| Stage | Transactions | Nominal wall-time | Conservative window |
|---|---:|---:|---:|
| T32 two cycles | 64 | 约 `1.6 h` | `1.5–3 h` |
| T64 two cycles | 128 | 约 `3.2 h` | `3–6 h` |
| 合计动态 | 192 | 约 `4.8 h` | `4.5–9 h` |

暖启动、JIT、核验和绘图另计。时间步具有因果依赖，周期内事务不得并行。若成本
预估在 P1/P3 后明显失效，应停止并向人类报告，不以降低门限或跳过相位控成本。

## Provisional Acceptance Criteria

### A. 每级周期态

- 所有正式事务通过父 oracle 并 create-only 提交；
- 最后两个连续周期的轴向缩短、最大界面牵引、总储能、ECM `||Z||` 波形差及
  周期末完整 `Z` 均 `<=1e-3`；
- 所有单步原 KKT、coupling、体积、`J`、gap、面质量、对称/无迹和耗散门通过；
- worker PID 在同一运行中唯一，源指纹一致。

### B. T32↔T64 正式时间门

沿用 Node 1 总合同并补足局部场诊断：

| Quantity | Gate |
|---|---:|
| 关键周期波形归一化 L2 差 | `<=2%` |
| 周期积分统计量差 | `<=2%` |
| 峰值幅值差 | `<=2%` |
| 峰值相位差 | `<=0.01T` |
| cycle dissipation 差 | `<=5%` |
| 共有相位的位移/界面牵引 p95/ECM 能量场摘要差 | `<=5%`（局部热点另单列） |

T16↔T32 只用于显示粗级误差下降趋势，不替代中—细门。

### C. 收敛裁决

只有以下条件均满足才允许表述“当前基线通过时间收敛门”：

1. T16、T32、T64 分别通过周期门；
2. T32↔T64 通过全部正式时间门；
3. 安全量和功率/耗散账本不随细化恶化；
4. 无关键指标呈无法解释的非单调发散；
5. 敏感相位仍通过原求解器门，且 fallback 被完整报告。

观察阶不是硬门；不能识别观察阶时如实报告，但不得伪造二阶或渐近区结论。

## Stop Conditions

发生以下任一情况立即停止当前级别并保留结果：

1. 暖启动父审计失败或重采样端点/相位不一致；
2. 任一步 worker 非零退出、父 oracle 失败、输入被修改或候选摘要不匹配；
3. KKT、coupling、体积、`J`、gap、面质量、`Z` 结构或耗散门失败；
4. 两个正式周期未过周期门；
5. 需要改变模型、网格、材料、波形、最大迭代数、门限或 fallback 逻辑；
6. 输出目录冲突、源码指纹漂移或输入来源不是上一级接受结果；
7. 实际成本超出批准窗口，或后续需要 GPU/新的外部资源；
8. T32 未被人类接受却准备进入 T64；
9. T64 未通过却准备自动进入 T128。

失败后只允许生成审计和终审材料，不允许同一授权内修复后续跑。

## Impacted Files Or Modules

执行获批后预计新增，而非覆盖：

- `src/hybrid/efe_time_refinement.py`：历史重采样、跨时间级比较和裁决；
- `scripts/prepare_efe_node1_n1_2c_time_refinement_warm_start_v01.py`；
- `scripts/run_efe_node1_n1_2c_transactional_cycle_v01.py`；
- `scripts/postprocess_efe_node1_n1_2c_time_refinement_v01.py`；
- `tests/hybrid/test_efe_time_refinement.py` 及相关事务测试；
- `results/hybrid/efe_node1_n1_2c_*` 的不可覆盖结果目录；
- `02_图表/Figures/` 中新的 N1-2c 版本化 Figure 包；
- `project_control/` 中分阶段执行、检查和决定记录。

R5 driver、warm-start driver、结果目录和已冻结 Figure 包不在修改范围内。

## Test Plan

1. `steps_per_cycle=16/32/64` 产生精确相位、`dt`、activation 和
   activation rate；
2. 线性周期几何的 16→32→64 重采样恢复公共相位且端点规则固定；
3. 常量和单谐波 manufactured history 的 SLS 周期初态与解析解一致；
4. 重采样暖启动的 source hash、相位数、周期残差、`Z` 结构和 create-only
   提交 fail-closed；
5. T32/T64 driver 分别要求 64/128 个唯一 worker 事务；
6. 任一步失败不产生接受检查点，输入摘要不变；
7. 4097 相位波形、峰值相位、周期积分和共有相位场比较使用冻结规则；
8. 零差、机器零、非单调差和不可识别观察阶均有测试；
9. R5 相关回归和源指纹保持，不修改既有正式脚本；
10. Ruff、相关 pytest、JSON/CSV/NPZ、Figure 包执行和视觉核验通过。

## Risks

1. **粗级暖启动偏置**：解析重采样只加速，正式证据必须来自新时间级的完全耦合
   周期；
2. **端点非完全闭合**：R5 周期差虽过门但不是机器零；必须记录源端点差，不能
   强行平均端点后隐瞒；
3. **时间细化改变 solver 路径**：相同物理解可能触发不同 fallback；报告而不把
   solver route 当作物理差异；
4. **局部场未保存**：应从冻结状态以预注册后处理复算，禁止结果后选择热点；
5. **观察阶不可辨识**：接近机器/求解噪声或非单调时不作阶数宣告；
6. **计算成本**：T64 为顺序 CPU 长任务，必须经过 T32 人类门；
7. **KKT 裕量小**：R5 phase `0.6875` 距门较近，细化后仍可能失败；
8. **时间与空间误差混淆**：本合同固定空间离散；通过后仍不能宣称空间收敛。

## Acceptance Criteria

本计划被人类批准后，首批执行授权默认只覆盖：

1. P0 的 N1-2c 专用实现和测试；
2. P1 的 T16→T32 暖启动；
3. P2 的 T32 两周期、T16↔T32 预览和阶段审阅图；
4. 到 Human Gate T32 停止。

T64 必须由新的明确人类决定授权。完整 N1-2c 只有在 T64 周期态、三档比较、
Figure 包、独立检查和人类终审均完成后才可接受。

## Out Of Scope

- 当前不执行任何 T32/T64 计算；
- 不修改 R5 正式脚本、结果、门限或 Figure 包；
- 不改变 DCM/ECM 网格、footprint、材料、激活、支承、界面或容差；
- 不执行 T128、D1/E1、F200、空间收敛、参数扫描、N1-2d、N1-3 或 Node 2；
- 不启动 GPU worker、外部求解器安装、Git 提交/推送或正式投稿；
- 不把 T16↔T32 两级接近称为正式时间收敛。

## Required Memory Updates

1. 只有 R5 人类接受决定产生后，T16 才可进入稳定输入记忆；
2. T32/T64 各自只有在执行、检查和人类接受后才能稳定；
3. 非单调、未稳态、求解失败和成本中止都必须作为负结果保留；
4. N1-2d 全 FEM 方案只能读取人类接受的最后时间级，不能读取未接受 pilot；
5. Figure 2 的时间收敛 panel 必须等待 N1-2c 最终 Human Gate。

## Requested Human Decision

建议当前只批准：

> 接受 R5 为 T16 周期稳态候选，批准 N1-2c P0–P2：实现专用时间细化入口，
> 构造可审计 T32 暖启动并执行两个 T32 事务周期；到 Human Gate T32 停止。

该批准不包含 T64。T32 结果、成本和敏感相位经审阅后，再决定是否进入 P3–P4。
