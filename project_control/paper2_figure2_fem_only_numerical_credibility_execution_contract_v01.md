---
contract_id: CONTRACT-PAPER2-FIGURE2-FEM-ONLY-NUMERICAL-CREDIBILITY-EXECUTION-V01
status: draft_for_independent_supervisor_review
created_at: 2026-09-04
created_by: executor
governance_mode: governed_computational_paper
baseline_commit: c52b2de7536a055699b2e23011fa221a6f2f1019
baseline_upstream_ahead_behind: 0/0
accepted_design_contract: project_control/paper2_figure2_fem_only_numerical_credibility_contract_v03.md
accepted_design_contract_sha256: 796de6a6cfa6167e30cae592128379206709ace720d4fcbe3ae80366fb504249
authorization_decision: project_control/paper2_figure2_fem_only_numerical_credibility_v03_supervisor_acceptance_and_execution_contract_decision_v01.md
authorization_decision_sha256: e854bcdddb0037d796b31ef1b4d54c5c20a5509a913bbe3fdb0b2c094014e4b5
current_status_sha256: 874cf0a230d4488b093952ef5d178a926ab104f0b2d24fd56358926b1ba68d80
active_architecture: endocardium_discrete_chain__myocardium_active_fem__ecm_viscoelastic_fem
evidence_level: prospective_execution_contract_not_implementation_or_numerical_evidence
implementation_authorized: none
execution_authorized: none
next_gate: independent_supervisor_review
---

# Paper 2 Figure 2 FEM-only 数值可信度执行合同 v01

## 0. 目的、当前边界与成功含义

本合同把已接受的 Figure 2 数值可信度合同 v03 转写成唯一、机器可判定、可审计的未来
实现与运行规范。它只规定将来拟新增的验证层、runner、测试、事务目录、资源预算和停止
码；本轮不实现、不测试、不运行、不创建结果目录，也不产生 Figure 2 数值证据。

未来只有同时满足下列条件，才可生成候选标签
`FIGURE2_FEM_ONLY_NUMERICAL_CREDIBILITY_PASS_V03`：

1. 核心模型、v03、执行合同、获批实现和运行环境前后锁一致；
2. 开发阶段严格按
   `G0 → G1 → G2 → G3 → G4a → G5 → G4b → G4 → G6 → G7` 通过；
3. 开发结果与规则 digest 已落盘并复核后，S1 才首次解盲；
4. S1 适用子门、资源、数组合同、hash ledger 和最终总裁决全部通过；
5. 独立 Supervisor 与人类终审随后接受。

该标签只证明当前二维 FEM-only 三层模型在冻结有限离散阶梯上的数值可信度，不证明
参数生理真实性、EFE 机制、三维心房、流体、实验验证或 Nature Physics 级普适规律。

## 1. 不可变输入与失效条件

### 1.1 已接受锚点

| 对象 | SHA-256 |
|---|---|
| Figure 2 v03 | `796de6a6cfa6167e30cae592128379206709ace720d4fcbe3ae80366fb504249` |
| v03 Supervisor 决定 | `e854bcdddb0037d796b31ef1b4d54c5c20a5509a913bbe3fdb0b2c094014e4b5` |
| Figure 1 v02 | `a669e142dfd0548bf3840e06482bbde9e339d8dd1d56a716f3c577b461ee61a7` |
| `src/paper2_hybrid/__init__.py` | `4626ee6f49cac099734728fe0dc2f3412ded11cf5066b32aff556cc39324783f` |
| `src/paper2_hybrid/config.py` | `0a83aedbabeb944b89f9584511dac5a597401327a68ac5c6411cb30e81ced6fe` |
| `src/paper2_hybrid/model.py` | `d43129c746c133294fcc92149d519a6c94bd633f2be54c898beea5d23190e800` |
| `src/paper2_hybrid/numerics.py` | `620381c4f0165801f2af03defe587e8381c9b6859f8bbd9d2f84198a555331e4` |
| `src/paper2_hybrid/projection.py` | `3bd590f0deef1fbe47cfdf01dea48664b25ff5a8716a546e4758bc4a0642176c` |
| `src/paper2_hybrid/protocol.py` | `f96d779cfcd6c76e9535f90a9941a6156b545d53a0270f04a564c68a304fe3ca` |
| `src/paper2_hybrid/roles.py` | `beb447ab12b8c433973ca807bba07331b8640b9fb9d4c944e3595510a3a501ec` |
| `src/paper2_hybrid/validation.py` | `6cfc1f383dbe92b6684eb1bd7f228610815ad67bd60ba1ecaaef8ab91cb1f0c5` |

以上八个 `paper2_hybrid` 文件是只读核心。新验证层只能调用它们，不得修改、复制后
替换生产方程，或通过 monkey patch 改写其运行语义。

### 1.2 立即失效条件

以下任一变化使本合同失效，必须先另立模型或协议变更合同：

- 模型方程、材料参数、几何、载荷、病例定义或组织角色变化；
- S2/S3/S4、T64/T128/T256、D0、阈值、floor、公共域或门禁 DAG 变化；
- 生产观测量、物理力方向、牵引提取、功率账本或热点定义变化；
- 心肌 DCM、representation、identity、旧 `paper2_m2` 运行依赖重新出现；
- 新求解器、迭代容差轴、GPU、网络、socket、三维、流体或参数扫描出现；
- 在 S1 解盲后改变任何规则、实现、阈值、参考层或输出 schema。

对应正式标签为 `SOURCE_OR_PROTOCOL_DRIFT_FAIL`、
`RETIRED_ROUTE_REINTRODUCED_FAIL` 或 `POST_HOC_GATE_CHANGE_FAIL`，且不得继续运行。

## 2. 将来唯一允许新增的实现文件

实现阶段若获独立授权，只允许新增以下精确文件；不得修改第 1.1 节八个核心文件：

| 文件 | 唯一职责 |
|---|---|
| `src/paper2_figure2/__init__.py` | 只导出执行协议、门禁和证据接口 |
| `src/paper2_figure2/spec.py` | 冻结病例、端点、DAG、尺度、floor、阈值、schema 和 stop code |
| `src/paper2_figure2/manufactured.py` | G0 装配、patch、SLS、主动共轭、矩阵惯性和零 RHS 检查 |
| `src/paper2_figure2/projection.py` | 任意嵌套方向的空间解析 P0 积分、周期中心化相位解析平均、步量交叠映射 |
| `src/paper2_figure2/observables.py` | 从只读 `paper2_hybrid` 端点提取冻结物理量并立即压缩；不定义新生产观测量 |
| `src/paper2_figure2/adjudication.py` | floor、比较器、G0–G7、S1 子门、混合差、热点和最终裁决 |
| `src/paper2_figure2/evidence.py` | create-only 写入、严格 JSON、NPZ registry、前后锁与 hash ledger |
| `scripts/run_paper2_figure2_fem_only_numerical_credibility_v01.py` | 唯一正式入口和无环事务编排 |
| `tests/paper2_figure2/test_spec_v01.py` | 协议、病例、端点计数、DAG、阈值与禁用路线 |
| `tests/paper2_figure2/test_source_lock_v01.py` | 核心只读 SHA、导入图、禁止符号和实现锁 |
| `tests/paper2_figure2/test_projection_v01.py` | 空间解析积分、中心化相位平均、交叠守恒和公共 L2 |
| `tests/paper2_figure2/test_manufactured_v01.py` | N1/N2 制造、谱、惯性、零模和零 RHS |
| `tests/paper2_figure2/test_adjudication_v01.py` | N1–N11、floor、方向、FAIL 标签与无环短路 |
| `tests/paper2_figure2/test_evidence_v01.py` | create-only、严格 JSON、NPZ、原子完成语义与 ledger |
| `tests/paper2_figure2/test_runtime_smoke_v01.py` | S2/P0 与 S2/A2 最小 FEniCSx/直接求解 smoke |

不得新增第二 runner、第二协议来源或第二结果 writer。若实现需要本表之外的文件，停止并
回到 Supervisor Gate。所有新增文件在正式运行前必须由独立实现验收决定记录精确字节数
与 SHA-256；没有该实现锁时 runner 以 `MISSING_VALIDATION_INTERFACE_FAIL` 退出。

未来实现验收的治理文件路径预留为
`project_control/paper2_figure2_fem_only_numerical_credibility_implementation_acceptance_and_execution_decision_v01.md`，
机器锁路径预留为
`project_control/paper2_figure2_fem_only_numerical_credibility_implementation_lock_v01.json`。
二者只能由后续 Supervisor 决定授权建立，不属于本轮文件；JSON 必须冻结验收 commit、
全部新增文件和第 1.1 节核心文件的字节数与 SHA-256。

## 3. 冻结病例、端点去重与生产调用

### 3.1 病例角色

- 开发集：`A2/LN/LS/C0/CQ`；
- 零状态：`P0`，只作真实零 RHS、floor 与 G1 诊断，不计作独立开发物理病例；
- 静态辅助：`P1`，只在 G0 patch/tangent 使用，不形成动态端点；
- 别名审计：`A1` 只证明当前输入与 A2 相同，不重复求解或计证据；
- 独立留出：`S1`，开发 digest 验证通过后才允许首次求解。

所有动态端点固定调用：

```text
paper2_hybrid.model.build_system(spatial_label=<S2|S3|S4>,
                                 active_profile=<uniform|S1>)
paper2_hybrid.numerics.simulate_endpoint(system=<system>,
                                         case_id=<case>,
                                         steps_per_cycle=<64|128|256>)
```

禁止调用 `paper2_hybrid.model.simulate_endpoint` 的旧账本路径；正式入口必须使用
`paper2_hybrid.numerics.simulate_endpoint`。D0 仍是固定 SuperLU provenance 标签，
不是 tolerance 扫描轴。

### 3.2 36 个开发/零状态动态端点

正式端点轴顺序写入 `case_matrix.json`，不得运行后重排：

| 索引 | 病例 | 空间 | 时间 | 数量 |
|---:|---|---|---|---:|
| 0 | P0 | S2 | T64 | 1 |
| 1–5 | A2、LN、LS、C0、CQ | S2 | T64 | 5 |
| 6–10 | A2、LN、LS、C0、CQ | S3 | T64 | 5 |
| 11–15 | A2、LN、LS、C0、CQ | S3 | T128 | 5 |
| 16–20 | A2、LN、LS、C0、CQ | S3 | T256 | 5 |
| 21–25 | A2、LN、LS、C0、CQ | S2 | T128 | 5 |
| 26–30 | A2、LN、LS、C0、CQ | S4 | T128 | 5 |
| 31–35 | A2、LN、LS、C0、CQ | S4 | T256 | 5 |

每个唯一端点只求解一次。G2/G3/G4a/G5/G6/G7 必须复用同一内存中的冻结压缩结果，
不得为不同门重复求解。开发物理端点为 35 个，另有 1 个 P0 端点。

### 3.3 4 个 S1 留出动态端点

| 留出索引 | 病例 | 空间 | 时间 |
|---:|---|---|---|
| 0 | S1 | S3 | T128 |
| 1 | S1 | S3 | T256 |
| 2 | S1 | S4 | T128 |
| 3 | S1 | S4 | T256 |

S1 端点列表可以在实现中冻结，但其任何求解对象、数组或结果在
`pre_holdout_digest.json` 已独占写入且复核成功前不得实例化。

### 3.4 静态 G0 工作量

G0 在 S2/S3/S4 各构建一个系统，完成 P0 真零 RHS、P1 affine patch、连续体/链 patch、
SLS DC/离散谐波制造、主动共轭、作用反作用与矩阵审计。它们是 3 个静态系统检查，
不增加第 3.2 节动态端点计数。

## 4. 唯一无环阶段图与通用阶段记录

### 4.1 唯一顺序

```text
PRECHECK
  -> G0
  -> G1
  -> G2
  -> G3
  -> G4a
  -> G5
  -> G4b
  -> G4 total
  -> G6
  -> G7
  -> pre_holdout_digest write + independent in-run re-read
  -> S1-G1
  -> S1-G4a
  -> S1-G5
  -> S1-G4b
  -> S1-G4
  -> S1-G6
  -> S1-G7
  -> FINAL
```

任一硬门失败立即短路。G4 只是真值表汇总，不调用求解器；G4a PASS 只放行 G5，G5
PASS 只放行 G4b，三者全 PASS 后 G4 才可 PASS。

### 4.2 每个机器检查的固定记录

每项检查必须产生以下严格 JSON 对象，字段不得缺失：

```json
{
  "check_id": "stable_unique_string",
  "gate_id": "G0|G1|G2|G3|G4a|G5|G4b|G4|G6|G7|S1-*|FINAL",
  "n_rule": "N1|N2|N3|N4|N5|N6|N7|N8|N9|N10|N11",
  "endpoint_ids": ["case__space__time__D0"],
  "quantity": "machine_name",
  "value": 0.0,
  "threshold": 0.0,
  "comparator": "le|lt|ge|gt|eq|bool_true|all_true",
  "scale": 1.0,
  "floor": 0.0,
  "applicability": "APPLICABLE|BELOW_RESOLUTION_FLOOR|NOT_APPLICABLE",
  "status": "PASS|FAIL|NOT_APPLICABLE",
  "failure_label": "LABEL_OR_NULL",
  "evidence_paths": ["relative/path"],
  "note": "non-interpretive machine note"
}
```

`value`、`threshold`、`scale` 和 `floor` 必须是有限 JSON 数；不适用量仍写有限占位 0，
并由 `applicability` 明确禁止解释。所有数组比较必须另记 numerator、denominator、权重、
参考端点和计算方向，禁止只写最终布尔值。

### 4.3 冻结 QoI registry

实现必须在 `spec.py` 中一次性冻结下列生产量，不得运行后增删：

- `limited_shortening` 波形；`free_shortening` 只标 `prescribed_input_comparator`；
- `mean_endocardial_displacement_x/y` 波形与基频；
- `myocardium_ecm`、`endocardium_ecm` 两界面的 x/y reported-side 牵引场与合力；
- 各单输入参照的 wrapped phase，以及多输入病例的分开参照相位；
- ECM `strain`、`internal_z`、`stress` 的有限性与积分范数；
- `maximum_ecm_von_mises_proxy`，名称和解释中必须保留 `proxy`；
- \(\Psi_m,\Psi_e,\Psi_n,\Psi_I,\Psi_{mat},\Psi_s\) 或经制造恒等式证明的等价分解；
- 主动/腔面/支撑功、drag/SLS 耗散、平衡缺陷、逐步与周期闭合；
- S1 \(\chi_D\)、热点集合、直接残差、后向误差、缩放谱、周期一致性和资源。

任何现有 `Endpoint.summary` 峰值只能作 sidecar；不得替代波形、公共场、积分或热点门。

## 5. 各阶段入口、输入、输出、依赖与停止

| 阶段 | 唯一入口条件 | 输入/新增求解 | 根目录正式输出 | PASS 后放行 | 主要停止标签 |
|---|---|---|---|---|---|
| PRECHECK | 新 run 根不存在；实现锁存在 | 只读哈希、环境、测试 | `manifest.json`, `provenance.json`, `case_matrix.json` | G0 | `OUTPUT_PATH_EXISTS_FAIL`, `SOURCE_OR_PROTOCOL_DRIFT_FAIL`, `RETIRED_ROUTE_REINTRODUCED_FAIL`, `MISSING_VALIDATION_INTERFACE_FAIL`, `CONTAINER_ID_MISMATCH_FAIL` |
| G0 | PRECHECK PASS | S2/S3/S4 静态系统 | `g0_static_manufactured.json` | G1 | `STATIC_OR_MANUFACTURED_FAIL`, `MATRIX_INERTIA_FAIL` |
| G1 | G0 PASS | 第 3.2 节索引 0–5 | `algebraic_audit.json` | G2 | `ALGEBRAIC_FAIL`, `NONFINITE_OUTPUT_FAIL` |
| G2 | G1 PASS | 新增索引 6–20 | `convergence_audit.json` 的 `G2` | G3 | `TIME_DISCRETIZATION_FAIL` |
| G3 | G2 PASS | 新增索引 21–30；复用既有 | 同文件 `G3` | G4a | `SPACE_DISCRETIZATION_FAIL` |
| G4a | G3 PASS | 新增索引 31–35；复用四角 | 同文件 `G4a` | G5 | `G4A_MIXED_FAIL` |
| G5 | G4a PASS | 不新增求解；公共投影 | `projection_audit.json` | G4b | `COMMON_PROJECTION_FAIL`, `UNEXPECTED_HIGHER_HARMONIC_FAIL` |
| G4b | G5 PASS | 不新增求解；公共场混合差 | `g4b_field_mixed_audit.json` | G4 | `G4B_FIELD_MIXED_FAIL` |
| G4 | G4b PASS | 真值表 | `g4_total_adjudication.json` | G6 | `G4_TOTAL_FAIL` |
| G6 | G4 PASS | 复用 35 个开发物理端点 | `power_audit.json` | G7 | `POWER_LEDGER_FAIL` |
| G7 | G6 PASS | 复用 35 个开发物理端点 | `periodic_audit.json` | digest | `PERIODIC_CONSISTENCY_FAIL` |
| digest | G7 PASS | 规则、实现、开发结果与数组内容哈希 | `pre_holdout_digest.json` | S1-G1 | `HOLDOUT_RULE_DRIFT_FAIL` |
| S1 | digest 重读一致 | 4 个留出端点一次求解 | `s1_holdout_audit.json` | FINAL | `S1_HOLDOUT_FAIL`；退化只写 claim-scoped `HOTSPOT_DEGENERATE` |
| FINAL | 所有适用门 PASS | 不新增求解 | `gate_summary.json`, `resource_audit.json`, `common_observables.npz`, summary, `hash_ledger.json` | Supervisor Gate | `ARRAY_CONTRACT_FAIL`, `RESOURCE_LIMIT_FAIL`, `NONFINITE_OUTPUT_FAIL` |

`HOTSPOT_DEGENERATE` 是唯一热点主张的 claim-scoped 撤销标签：若范围或覆盖前提不满足，
Hausdorff/Jaccard/峰值稳定性记 `NOT_APPLICABLE`，Figure 2 不得画唯一热点；它本身不把
其他数值可信度证据改成失败。若前提满足，则全部 N8 稳定性门是 S1 硬门，失败即
`S1_HOLDOUT_FAIL`。

G1 首先在索引 0–5 建立代数门；此后每个新端点在加入内存 registry 前都必须再次执行
N3。后续阶段的任一端点 N3 失败仍立即以 `ALGEBRAIC_FAIL` 短路，不能等到阶段末汇总。

## 6. 特征尺度、floor 与统一比较方向

### 6.1 冻结尺度与 floor

| 量类 | 尺度 |
|---|---|
| 位移 | \(S_u=a_0L\) |
| 应变、SLS 内变量、宏观/自由短缩 | \(S_\epsilon=a_0\) |
| 牵引/应力 | \(S_t=E_\infty a_0\) |
| 广义力、RHS、代数残量 | \(S_f=E_\infty a_0L\) |
| 每单位厚度储能/功 | \(S_W=E_\infty a_0^2L^2\) |
| 功率 | \(S_P=S_W/T\) |

每一量类的零噪声 \(N_Q\) 只由同算子 P0 真零 RHS 直接求解得到：

\[
F_Q=\max(10^{-12}S_Q,10N_Q).
\]

禁止使用固定 `1e-30`、非零病例、S1 或观察到的最小值定义 floor。`floors` 对象必须在
G1 后写入内存注册表并参与开发 digest；此后不可改变。

### 6.2 标量和公共场比较器

标量以第二个参数为参考：

\[
d_s(q,r)=\frac{|q-r|}{\max(|r|,F_Q)}.
\]

公共空间—相位场以 S4/T256 为参考：

\[
d_2(q,r)=\frac{\|q-r\|_{L^2(\mathcal D_c)}}
{\max(\|r\|_{L^2(\mathcal D_c)},F_Q\sqrt{|\mathcal D_c|})}.
\]

若参考不高于 floor，记录 `BELOW_RESOLUTION_FLOOR`，相对误差和观察阶均不适用；只有
绝对差不高于相应 \(F_Q\) 才 PASS。任何相位差必须用 wrapped `atan2`，且输入、输出
基频幅值均大于 `10*floor` 才适用。

相位参照固定为：A2 对主动输入，LN 对法向载荷，LS 对切向载荷，C0/CQ 对主动时钟并
另记法向载荷相位，S1 对主动输入。C0/CQ 不得被称为单输入传递函数；未达到幅值前提时
写 `PHASE_UNDEFINED_LOW_AMPLITUDE`，不得强置零。

## 7. N1–N11 机器裁决合同

### 7.1 N1 — 装配、制造、共轭和作用反作用

输出 `g0_static_manufactured.json.n_rules.N1`，对 S2/S3/S4 分别记录：

| 检查 | value | comparator | threshold | 失败标签 |
|---|---|---|---:|---|
| UFL—手工 \(B^TCB\) 相对 Frobenius 误差 | 非负有限数 | `le` | `1e-10` | `STATIC_OR_MANUFACTURED_FAIL` |
| 连续体 affine patch 相对误差 | 非负有限数 | `le` | `1e-10` | 同上 |
| 离散链 affine patch 相对误差 | 非负有限数 | `le` | `1e-10` | 同上 |
| SLS DC 制造解相对误差 | 非负有限数 | `le` | `1e-10` | 同上 |
| SLS 当前 CN 离散谐波制造解相对误差 | 非负有限数 | `le` | `1e-10` | 同上 |
| 主动共轭多步长中心差分平台最优相对误差 | 非负有限数 | `le` | `1e-7` | 同上 |
| \(A/G\) 相对非对称 | 非负有限数 | `le` | `1e-12` | 同上 |
| 制造界面作用反作用相对误差 | 非负有限数 | `le` | `1e-12` | 同上 |

P0 旁路数组、P1 人工宏观应变或当前宽松 `manufactured_solution_relative_tolerance` 均
不能替代上述新检查。

### 7.2 N2 — 缩放谱、惯性与刚体模态

对 \(K_{mat}\)、\(K_s\)、\(K_{mat}+K_s\) 和 \(G\) 写入矩阵维数、对角范围、所用算法、
残量、最小/最大缩放特征值及判定：

- 正对角缩放；任一应缩放对角非正即 `MATRIX_INERTIA_FAIL`；
- \(K_{mat}\) PSD：缩放最小特征值 `ge -1e-10`，并且
  `zero_mode_count eq 2`；零模阈值为 `abs(lambda) le 1e-10*lambda_max`；
- 两个零模与全局 x/y 平移的加权夹角残差均 `le 1e-8`，不得只数特征值；
- \(K_s\) 在受支撑子空间缩放，其完整未缩放惯性必须半正定；
- \(K_{mat}+K_s\) 与 \(G\) 严格 SPD：`lambda_min/lambda_max gt 1e-12`；
- 复谐波矩阵只审计可逆、残差和后向误差，不写 SPD。

稀疏谱算法必须记录请求特征对、容差和每个 Ritz 残量；若未能证明零模数与最小特征值，
状态为 FAIL，禁止把 eigensolver 未收敛当作缺失值跳过。

### 7.3 N3 — 固定直接代数求解

每个正式端点的 DC 与复谐波系统分别记录 RHS norm、残量 norm、相对残差、后向误差、
pivot/finite 状态：

- 非零 RHS：relative residual `le 1e-10`；
- normwise backward error `le 1e-12`；
- 真零 RHS：解、绝对残量与派生观测量分别 `le` 对应 floor；
- 无零 pivot、不可逆或非有限值。

正式验证层必须独立按 `1e-10` 验收；不得读取 `ACTIVE_PROTOCOL` 中 v08 的 `1e-7` 作为
Figure 2 门，也不得改变 SuperLU 内部行为。

### 7.4 N4 — 时间离散

对 S3 的 A2/LN/LS/C0/CQ，方向固定为 T64→T128→T256，参考为 T256。每个冻结全局
标量、公共波形、周期积分和相位分别记录两级差：

- T128–T256 误差 `le 2e-3`；
- wrapped 相位差 `le 1e-2 rad`；
- 高于 floor 时 `e_128_256 lt e_64_128`；
- 两级原始差均 `gt 10*F_Q` 时
  \(p_t=\log_2(e_{64,128}/e_{128,256})\) 且 `p_t ge 1.5`；
- 不适用观察阶必须显式标 `BELOW_RESOLUTION_FLOOR`。

任一适用量失败即 `TIME_DISCRETIZATION_FAIL`，不能用峰值 sidecar 覆盖波形失败。

### 7.5 N5 — 空间离散全局量

固定 T128，方向 S2→S3→S4，参考为 S4：

- S3–S4 全局 QoI `le 2e-2`；
- 高于 floor 时 `e_34 le 0.8*e_23`；
- 低于 floor 时按第 6.2 节绝对门。

任一适用量失败即 `SPACE_DISCRETIZATION_FAIL`。G3 不包含公共牵引场。

### 7.6 N6 — 四角混合差

G4a、G4b 和 S1 均使用同一四角：S3/T128、S3/T256、S4/T128、S4/T256。每项必须存
四个有符号输入、混合差 numerator、S4/T256 denominator、两个边际误差和 floor：

\[
\Delta_{st}Q=Q_{S4,T256}-Q_{S3,T256}-Q_{S4,T128}+Q_{S3,T128},
\]

\[
e_{st}\le0.5\max(e_t^{S4},e_s^{T256},10^{-12}).
\]

G4a 只处理标量、积分量和无需跨网格对应的波形；失败为 `G4A_MIXED_FAIL`。G4b 只处理
G5 后两界面两分量公共牵引场；任一项失败为 `G4B_FIELD_MIXED_FAIL`。

### 7.7 N7 — 128×256 公共域

每个界面、每个分量独立记录：

- 空间常量和线性制造场的段平均/合力绝对误差 `le 1e-12`；
- 原生—公共合力和功率相对误差 `le 1e-10`；
- 开发集 S3–S4 公共牵引场 `d2 le 5e-2`；
- 高于 floor 时 `d_34 le 0.8*d_23`；
- 公共数组、合力、L2、热点和 G4b 的内容 SHA 必须指向同一数组 registry 条目。

不允许合并两界面或 x/y 分量后判定。失败为 `COMMON_PROJECTION_FAIL`；发现高次谐波
高于 floor 时为 `UNEXPECTED_HIGHER_HARMONIC_FAIL`。

### 7.8 N8 — S1 峰值中心段热点

只使用 S1 的 `Q[:, interface=myocardium_ecm, component=x, phase=128]`，物理方向固定为
\(t_{e\to m,x}=-t_{me,x}^{rep}\)。先检查：

- 场范围 `gt 10*F_t`；
- 阈值集合 \(t_k\le t_{min}+0.05(t_{max}-t_{min})\) 的覆盖 `le 25%`。

若前提不满足，按第 5 节写 `HOTSPOT_DEGENERATE`。若满足，四角比较必须满足：

- 周期 Hausdorff `le L/32`；
- 长度加权 Jaccard `ge 0.5`；
- 峰值幅度相对差 `le 5e-2`。

任何替代点值、旧 `argmax` 摘要或牵引范数均不得进入热点裁决。

S1 耗散份额只在总耗散高于 floor 时定义：

\[
\chi_D=\frac{D_{SLS}}{D_{SLS}+D_{drag}},\qquad
D_{SLS}+D_{drag}>F_W.
\]

分母不高于 floor 时写 `CHI_D_UNDEFINED_LOW_DISSIPATION`，不强置 0 或 1，且该派生量
记 `NOT_APPLICABLE`。定义时在 S1-G4a 检查时间终局差 `le 2e-3`、空间终局差
`le 2e-2` 和 N6 的 `0.5` 混合差门。

### 7.9 N9 — 精确功率账本与耗散

每个开发物理端点与 S1 端点分别记录：

- `ledger_minus_equilibrium_work_relative` 最大值 `le 1e-10`；
- 每步和整周期归一闭合 `le 1e-8`；
- drag/SLS 每步耗散 `ge -1e-12*S_W`；
- 原生与公共步积分总和相对差 `le 1e-10`；
- 支撑外端口和总能分区产生同一周期结果。

逐步功/耗散必须使用第 8.3 节交叠映射；失败为 `POWER_LEDGER_FAIL`。

### 7.10 N10 — harmonic 周期一致性

每个非零开发端点和 S1 端点的两周期状态、两界面牵引与能量归一差均 `le 1e-10`；输入
周期端点也 `le 1e-10`。P0 另走真零门，记 `NOT_APPLICABLE`。结果必须标
`harmonic_periodic_solution_by_construction`，不得称任意初值吸引极限环。失败为
`PERIODIC_CONSISTENCY_FAIL`。

### 7.11 N11 — 资源与隔离

- 单 CPU/进程；BLAS/OpenMP/PETSc 线程均为 1；
- 根事务总 wall-clock `le 3600 s`；
- 峰值 RSS/cgroup memory `le 8 GiB`；
- 无网络、GPU、Docker socket、子求解器或外部写入；
- 任何非有限正式量立即 `NONFINITE_OUTPUT_FAIL`。

资源或隔离失败为 `RESOURCE_LIMIT_FAIL`，不得以科学门已通过为由继续。

## 8. 三类公共映射的唯一实现

### 8.1 空间解析 P0 平均

公共空间边界固定为 `linspace(-L/2,L/2,129)`。新投影器必须把原生分片线性场与每个
目标段求真实交点、逐子段解析积分后除以 `L/128`；S2/S3→128 属于目标更细，不能调用
现有只接受“目标节点嵌套于原生节点”的 v08 投影器伪造重复值。常量/线性制造、合力和
积分次序交换均须通过 N7。

### 8.2 周期中心化相位解析平均

对每个原生完整周期数组（去掉重复端点）先恢复 DC 与一阶复幅：

\[
Q_0=\frac1N\sum_{n=0}^{N-1}Q_n,\qquad
\widehat Q_1=\frac2N\sum_{n=0}^{N-1}Q_ne^{-i2\pi n/N}.
\]

原生数组用该 DC＋基频重建的误差及全部 \(|k|>1\) Fourier 能量必须不高于量类
floor，否则 `UNEXPECTED_HIGHER_HARMONIC_FAIL`。随后对

\[
I_j=[t_j-\Delta t_c/2,t_j+\Delta t_c/2)\pmod T,
\quad t_j=jT/256,
\]

只计算解析段平均

\[
Q_j=Q_0+\operatorname{Re}\!\left[
\widehat Q_1e^{i\omega t_j}
\frac{2\sin(\omega\Delta t_c/2)}{\omega\Delta t_c}\right].
\]

禁止端点、中心点、插值节点或 FFT 重采样值替代该积分。公共 L2、合力、N7、热点和
G4b 必须引用同一数组对象的内容 SHA。

### 8.3 步功/耗散交叠守恒映射

原生每步积分量先除以原生步长成为分段常量密度，再与第 8.2 节 256 个中心化目标段求
周期交叠并积分。`I0` 唯一拆为 `[0,T/512)` 与 `[T-T/512,T)`，边界不重复计权。每一
通道公共 256 段之和必须以相对误差 `le 1e-10` 复原原生整周期量。

此路径只用于主动功、腔面功、支撑功、物质能增量、drag 耗散、SLS 耗散、平衡缺陷功和
ledger residual；禁止对这些步积分量做单频重建，也禁止平均牵引乘平均速度。

## 9. create-only 父事务与子包原子性

### 9.1 唯一 run id 与根目录

首次正式执行唯一冻结：

```text
run_id = r01
results/paper2_figure2/
  fem_only_numerical_credibility_v03_20260904_r01/
```

宿主入口先确认根目录不存在，再以 `mkdir(exist_ok=False)` 创建；存在即
`OUTPUT_PATH_EXISTS_FAIL`，不得清空、覆盖、续接或复用。任何失败后的重试都必须另立
执行决定与新 run id，不能在本合同内自行改成 r02。

### 9.2 父 manifest 与逻辑子包

根 `manifest.json` 是唯一父 manifest，记录 run id、DAG、实现锁、端点轴、子包清单、
输入/输出依赖、当前状态和证据边界。固定子目录为：

```text
00_precheck/
01_g0/
02_g1/
03_g2/
04_g3/
05_g4_pipeline/
06_g6_g7_digest/
07_s1/
08_final/
```

每个子包只能独占创建一次，并按以下顺序写：

1. `stage_manifest.json`；
2. 该阶段检查/计时/内容哈希；
3. 成功时最后独占写 `stage_complete.json`，失败时最后独占写 `stage_failed.json`。

文件写入使用独占创建、flush 和 fsync；禁止覆盖式 `replace`。只有 completion 文件存在、
其依赖哈希匹配且该目录无 failed 文件，父 manifest 才可把子包视为完成。进程中断导致的
半写文件或缺少 completion 的目录永久记为 `INCOMPLETE_TRANSACTION`，不得续跑。

这些是单次进程中的阶段化证据包，不是多个可独立重跑的 3600 秒任务。所有阶段共享一个
总 wall-clock、一个内存门和同一只读源锁。

### 9.3 根完成与失败语义

- PASS 路径先写全部正式工件和 `pass_summary.json`，最后写 `hash_ledger.json`；
- FAIL 路径尽可能写 `failure_summary.json` 和当时已有工件，最后写只覆盖现有文件的
  `hash_ledger.json`；
- 根事务仅当 summary 与 ledger 同时存在、ledger 独立复算一致时才是完整事务；
- `hash_ledger.json` 不自哈希，列出其余每个文件的相对路径、字节数和 SHA-256；
- 运行后任何文件变化均使结果失效。

## 10. 根目录强制文件与严格 schema

| 文件 | 最小内容与写入时点 |
|---|---|
| `host_create_lock.json` | 宿主独占创建根目录时写入的 run id、项目相对目标、resolved-path SHA 和创建时间；不写绝对路径明文 |
| `manifest.json` | 父事务、合同/实现/DAG digest、端点轴、阶段状态、证据边界；PRECHECK 建立后只由 append-only 事件侧车补充，最终状态另写 summary |
| `manifest_events.jsonl` | append-only hash chain；逐阶段状态，不回写 manifest |
| `provenance.json` | Git、源锁、镜像、Python/FEniCSx/PETSc/SciPy/NumPy、容器参数、前后锁 |
| `case_matrix.json` | 36+4 精确端点、求解次序、复用关系、开发/留出分区 |
| `g0_static_manufactured.json` | N1/N2 全部记录 |
| `algebraic_audit.json` | G1/N3 与端点直接系统记录 |
| `convergence_audit.json` | G2、G3、G4a 和 N4/N5/N6 |
| `projection_audit.json` | G5/N7、解析段平均、交叠守恒、高次谐波和数组 registry |
| `g4b_field_mixed_audit.json` | 两界面两分量的四角公共场 N6 |
| `g4_total_adjudication.json` | G4a/G5/G4b 真值表与 G4 状态 |
| `power_audit.json` | G6/N9 的逐步、周期与公共映射 |
| `periodic_audit.json` | G7/N10 与 by-construction 标签 |
| `pre_holdout_digest.json` | 开发规则、实现、结果与内存数组内容哈希；必须先于任何 S1 求解 |
| `s1_holdout_audit.json` | S1-G1/G4a/G5/G4b/G4/G6/G7、N8 和 \(\chi_D\) |
| `resource_audit.json` | N11、阶段累计 wall-clock、峰值 RSS/cgroup、隔离证据 |
| `gate_summary.json` | 每门 PASS/FAIL/NOT_REACHED、首失败、适用/不适用项计数 |
| `common_observables.npz` | 第 11 节唯一强制公共数组包 |
| `pass_summary.json` 或 `failure_summary.json` | 恰有一个；正式标签、证据边界和 Supervisor Gate |
| `hash_ledger.json` | 最后写；除自身外全部文件的排序哈希账本 |

所有 JSON 必须 UTF-8、排序键、稳定分隔符，禁止 NaN、Infinity、重复键和绝对宿主路径。
manifest 初始内容本身不可改写；阶段状态使用 `manifest_events.jsonl` 逐行独占追加，每行
带前一行哈希形成链，最终状态由 summary 汇总。`manifest_events.jsonl` 也进入 ledger。

## 11. `common_observables.npz` 精确键、shape 与 dtype

### 11.1 坐标和端点轴

| key | shape | dtype | 含义 |
|---|---:|---|---|
| `formal_endpoint_id` | `(36,)` | `<U24` | 第 3.2 节固定顺序 |
| `s1_endpoint_id` | `(4,)` | `<U24` | 第 3.3 节固定顺序 |
| `space_edges` | `(129,)` | `float64` | `[-L/2,L/2]` 公共边界 |
| `space_centers` | `(128,)` | `float64` | 公共空间段中心，仅作坐标，不作取样 |
| `phase_centers` | `(256,)` | `float64` | `jT/256`，仅标记解析段中心 |
| `phase_bin_start_unwrapped` | `(256,)` | `float64` | `t_j-T/512` |
| `phase_bin_stop_unwrapped` | `(256,)` | `float64` | `t_j+T/512` |
| `interface_code` | `(2,)` | `int8` | `0=myocardium_ecm,1=endocardium_ecm` |
| `component_code` | `(2,)` | `int8` | `0=x,1=y` |
| `step_channel_code` | `(8,)` | `int8` | 第 11.3 节固定通道 |

字符串、code 到语义及物理方向的映射同时写入 `case_matrix.json` 和
`projection_audit.json`。不得把 `space_centers` 或 `phase_centers` 当采样值。

### 11.2 正式开发/零状态端点数组

| key | shape | dtype |
|---|---:|---|
| `formal_limited_shortening_p0` | `(36,256)` | `float64` |
| `formal_mean_endocardial_displacement_p0` | `(36,2,256)` | `float64` |
| `formal_traction_reported_side_p0` | `(36,2,2,128,256)` | `float64` |
| `formal_force_reported_side_p0` | `(36,2,2,256)` | `float64` |
| `formal_step_integrals_overlap_p0` | `(36,8,256)` | `float64` |
| `formal_native_steps_per_cycle` | `(36,)` | `int16` |

### 11.3 S1 留出数组

| key | shape | dtype |
|---|---:|---|
| `s1_limited_shortening_p0` | `(4,256)` | `float64` |
| `s1_mean_endocardial_displacement_p0` | `(4,2,256)` | `float64` |
| `s1_traction_reported_side_p0` | `(4,2,2,128,256)` | `float64` |
| `s1_force_reported_side_p0` | `(4,2,2,256)` | `float64` |
| `s1_step_integrals_overlap_p0` | `(4,8,256)` | `float64` |
| `s1_native_steps_per_cycle` | `(4,)` | `int16` |
| `s1_hotspot_traction_e_to_m_x` | `(4,128)` | `float64` |
| `s1_hotspot_mask` | `(4,128)` | `bool` |

`step_channel_code` 顺序固定为：主动功、腔面功、支撑功、物质能增量、drag 耗散、SLS
耗散、平衡缺陷功、ledger residual。另一界面侧物理力不得重复存储；manifest 必须规定
它是 `-1 * reported_side`。

### 11.4 数组约束

- NPZ 使用 `numpy.savez_compressed`，`allow_pickle=False` 可读，禁止 object dtype；
- 压缩后 `le 128 MiB`；本 schema 的主场未压缩预算约 43 MiB，留有坐标和压缩开销余量；
- 禁止全状态、系统矩阵、重复周期、逐单元 ECM 全场或第二份相同物理力；
- 每个数组 registry 记录 key、shape、dtype、C-order 内容 SHA、量纲、方向、生成路径；
- 内容 SHA 定义为 `sha256(dtype.str || canonical_shape_json || C_contiguous_bytes)`；
- NPZ 写后必须以 `allow_pickle=False` 重读，逐键复算 registry，再进入 ledger；
- 缺键、多键、错 shape/dtype、非有限值、超限或两时间路径混用即 `ARRAY_CONTRACT_FAIL`。

ECM 应变、SLS 内变量、应力、积分范数和二维 von Mises proxy 只以冻结标量/积分摘要进入
JSON；von Mises 必须保留 `proxy` 标签，不得把逐单元全场加入 NPZ。

## 12. 开发 digest 与 S1 解盲边界

### 12.1 digest 输入

`pre_holdout_digest.json` 至少包含并排序哈希：

1. v03、本执行合同、未来实现验收决定和全部获批新增文件；
2. 八个核心只读文件、角色、配置、病例、端点轴和容器镜像；
3. N1–N11、尺度、floor、阈值、比较方向、公共域、DAG 和 stop code；
4. G0、G1、G2、G3、G4a、G5、G4b、G4、G6、G7 的全部开发输出；
5. 36 个正式端点的内存压缩数组逐键内容 SHA；
6. S1 端点清单、预注册输出 schema 和子门规则，但不含任何 S1 求解结果。

### 12.2 两次校验和单向门

runner 用独占写入生成 digest，关闭文件后立即从磁盘重读、重算全部输入哈希；只有一致
才把 `06_g6_g7_digest/stage_complete.json` 写为 PASS。随后、且仅随后，才可构建 S1
系统和求解四端点。S1 开始前再次验证 digest 文件自身 SHA。

任何差异立即 `HOLDOUT_RULE_DRIFT_FAIL`。S1 失败或退化后不得返回开发阶段调规则，且
同一 run 不得再次解盲。

## 13. 容器入口、隔离和前后锁

### 13.1 宿主唯一入口

未来获准执行时，唯一宿主入口为：

```powershell
python scripts/run_paper2_figure2_fem_only_numerical_credibility_v01.py --host-launch --project-root E:\Temp-Projects\PRL --run-id r01
```

宿主入口必须先做只读镜像 ID、Git、源锁和目标不存在检查，再独占创建第 9.1 节根目录
及 `host_create_lock.json`。任何后续启动失败都冻结该目录；不得第二次使用 r01。

### 13.2 唯一 Docker 参数向量

宿主 runner 只能以参数数组（禁止 shell 拼接）启动以下等价命令：

```text
docker run
  --name paper2-figure2-nc-v03-r01
  --network none
  --cpus 1
  --memory 8g
  --memory-swap 8g
  --pids-limit 256
  --read-only
  --cap-drop ALL
  --security-opt no-new-privileges
  --tmpfs /root/.cache:rw,exec,nosuid,size=2g
  --mount type=bind,source=E:\Temp-Projects\PRL,target=/workspace,readonly
  --mount type=bind,source=E:\Temp-Projects\PRL\results\paper2_figure2\fem_only_numerical_credibility_v03_20260904_r01,target=/output
  --workdir /workspace
  --env OMP_NUM_THREADS=1
  --env OPENBLAS_NUM_THREADS=1
  --env MKL_NUM_THREADS=1
  --env NUMEXPR_NUM_THREADS=1
  --env PYTHONDONTWRITEBYTECODE=1
  dolfinx/dolfinx:v0.11.0
  python3 scripts/run_paper2_figure2_fem_only_numerical_credibility_v01.py
    --inside-container --project-root /workspace --output-root /output --run-id r01
    --implementation-lock /workspace/project_control/paper2_figure2_fem_only_numerical_credibility_implementation_lock_v01.json
```

Docker socket 不挂载；不出现 `--gpus`；只有源代码只读挂载和本次精确结果根可写挂载。
`/root/.cache` 是无宿主持久化的 JIT 临时内存盘；不得复制到项目外。
容器不自动删除；运行结束后保留为停止状态，其后清理必须另获人类明确批准。
启动前必须以 `docker image inspect` 只读核对本地 tag 的 image ID 精确等于
`sha256:2ae4bfbc0d9077268880faf04c72750528bee986c94ab223a2c159969bd56fa8`；不一致时
`CONTAINER_ID_MISMATCH_FAIL`，不得 pull、重标 tag 或把 image ID 误作 registry digest。

### 13.3 运行前后锁

前后均记录并比较：

- HEAD、upstream、ahead/behind 和 scoped status；
- v03、执行合同、实现验收决定、八个核心文件、全部新增实现/测试/runner 的 SHA；
- config/roles/cases/endpoint/DAG/schema digest；
- 镜像 ID 和运行库版本；
- CPU affinity、线程环境、cgroup memory、网络、GPU 与 socket 状态；
- 结果根之外没有新增或修改的项目文件。

正式开始时 HEAD 必须等于未来实现验收决定冻结的 commit，且 HEAD=upstream、0/0。前后
任一差异即 `SOURCE_OR_PROTOCOL_DRIFT_FAIL`。不得把仓库中既有无关未跟踪材料误判为
本次产物；必须使用运行前 scoped 快照逐项比较。

## 14. 最小测试顺序

正式 runner 在 PRECHECK 内按下列唯一顺序串行执行，任一失败即
`MISSING_VALIDATION_INTERFACE_FAIL`，不进入 G0：

1. `tests/paper2_figure2/test_spec_v01.py`；
2. `tests/paper2_figure2/test_source_lock_v01.py`；
3. `tests/paper2_figure2/test_projection_v01.py`；
4. `tests/paper2_figure2/test_adjudication_v01.py`；
5. `tests/paper2_figure2/test_evidence_v01.py`；
6. `tests/paper2_hybrid/test_static_architecture.py` 与
   `tests/paper2_hybrid/test_projection.py`；
7. `tests/paper2_figure2/test_manufactured_v01.py`；
8. `tests/paper2_figure2/test_runtime_smoke_v01.py` 与
   `tests/paper2_hybrid/test_fenicsx_runtime.py`。

pytest cache 禁用，临时目录固定在非持久 JIT tmpfs 的 `/root/.cache/pytest_tmp`，JUnit
只写入 `/output/00_precheck/pytest_junit.xml`。测试不得创建源码缓存、改核心文件或求解 S1，
也不得把 tmpfs 内容复制到结果或项目外。
`test_manufactured_v01.py` 只做 S2 最小单元 smoke，完整 S2/S3/S4 N1/N2 仍由 G0 执行。
测试通过只放行 G0，不是 Figure 2 PASS。

## 15. 端点数、内存与 wall-clock 可行性

### 15.1 经验锚点

冻结 v08 结果
`results/paper2_v08/fem_only_architecture_parity_v01_20260904/` 显示：6 个 S4/T64 FEM-only
端点各约 `25.74–26.05 s`，全阶段 `189.14686104100838 s`，峰值内存
`0.7554397583007812 GiB`。该证据只作资源规划，不迁移为 Figure 2 数值 PASS。

本合同共有 40 个唯一动态端点：S2 11 个、S3 17 个、S4 12 个；其中 S4/T128 6 个、
S4/T256 6 个。稀疏求解成本主要随空间规模变化，时间级别主要增加波形/账本后处理。
runner 必须逐端点提取压缩量后立即释放 `state_two_cycles` 和逐单元场，禁止保留 40 份
全状态。

### 15.2 阶段累计预算

下表是同一 3600 秒根事务的累计硬停止点，不是每阶段各有一份预算：

| 完成节点 | 预计累计 wall-clock | 硬累计上限 |
|---|---:|---:|
| PRECHECK | 180 s | 240 s |
| G0 | 600 s | 900 s |
| G1 | 660 s | 1050 s |
| G2 | 900 s | 1500 s |
| G3 | 1250 s | 2100 s |
| G4a/G5/G4b/G4 | 1800 s | 2850 s |
| G6/G7/digest | 2000 s | 3150 s |
| S1 | 2250 s | 3500 s |
| FINAL | 2400 s | 3600 s |

宿主进程对 Docker 施加 3600 秒总 timeout；容器在每个端点、谱任务和阶段边界前后检查
累计时间。达到硬累计上限时停止并写 `RESOURCE_LIMIT_FAIL`，不得为凑 PASS 跳过检查。

资源估算留有约 1200 秒余量，能够覆盖 S4 谱审计、公共投影、压缩与 I/O。若未来实现
验收的 smoke/benchmark 推断 95% 上界超过 3300 秒，Supervisor 必须在正式运行前拒绝
本合同并另立资源合同；不得运行后拆包或放宽 3600 秒门。

内存规划为：单个 S4/T256 全状态/矩阵与 JIT 峰值预计小于 3 GiB，公共数组约 50 MiB，
硬门 8 GiB。RSS 与 cgroup peak 取较大者；无法读取 cgroup 指标时不是自动 PASS。

## 16. 进程退出码与 FAIL 标签

| exit code | 唯一首失败类别 |
|---:|---|
| 0 | 全部适用门通过，候选 PASS 已完整写入；仍待 Supervisor |
| 10 | `SOURCE_OR_PROTOCOL_DRIFT_FAIL` |
| 11 | `RETIRED_ROUTE_REINTRODUCED_FAIL` |
| 12 | `MISSING_VALIDATION_INTERFACE_FAIL` |
| 20 | `STATIC_OR_MANUFACTURED_FAIL` |
| 21 | `MATRIX_INERTIA_FAIL` |
| 30 | `ALGEBRAIC_FAIL` |
| 40 | `TIME_DISCRETIZATION_FAIL` |
| 41 | `SPACE_DISCRETIZATION_FAIL` |
| 42 | `G4A_MIXED_FAIL` |
| 43 | `COMMON_PROJECTION_FAIL` |
| 44 | `UNEXPECTED_HIGHER_HARMONIC_FAIL` |
| 45 | `G4B_FIELD_MIXED_FAIL` |
| 46 | `G4_TOTAL_FAIL` |
| 50 | `POWER_LEDGER_FAIL` |
| 51 | `PERIODIC_CONSISTENCY_FAIL` |
| 60 | `S1_HOLDOUT_FAIL` |
| 61 | `HOLDOUT_RULE_DRIFT_FAIL` |
| 70 | `ARRAY_CONTRACT_FAIL` |
| 71 | `OUTPUT_PATH_EXISTS_FAIL` |
| 72 | `CONTAINER_ID_MISMATCH_FAIL` |
| 73 | `RESOURCE_LIMIT_FAIL` |
| 74 | `NONFINITE_OUTPUT_FAIL` |
| 75 | `POST_HOC_GATE_CHANGE_FAIL` |
| 99 | `UNCLASSIFIED_RUNTIME_FAIL`；不得生成任何科学结论 |

`HOTSPOT_DEGENERATE` 不占进程退出码；它按第 5 节撤销唯一热点子主张。对同一异常只记录
第一个因果 stop code，后续门全部 `NOT_REACHED`，禁止同时写 PASS。

## 17. 最终裁决与证据边界

FINAL 必须验证：

```text
G0, G1, G2, G3, G4a, G5, G4b, G4, G6, G7,
S1-G1, S1-G4a, S1-G5, S1-G4b, S1-G4, S1-G6, S1-G7,
source lock, implementation lock, resource, array contract,
hold-out digest, hash ledger
```

全部适用项 PASS 后，`pass_summary.json` 才可写
`FIGURE2_FEM_ONLY_NUMERICAL_CREDIBILITY_PASS_V03`。若热点退化，summary 同时写
`UNIQUE_HOTSPOT_CLAIM_WITHDRAWN`，Figure 2 面板 e 不得出现唯一热点。

正式运行完成后立即停在 Supervisor Gate，不自动制图、不更新 Figure 2 v02 FINAL、
不进入 Figure 3、不提交或推送。Supervisor 必须独立复算 ledger、数组 registry、关键
门和源后锁；只有人类终审后才决定是否冻结结果或制作 Figure 2 新版本。

## 18. 本轮验收门与停止边界

本执行合同草案只有在独立 Supervisor 确认以下全部成立后才可被接受：

1. 拟新增文件清单精确，八个核心文件保持只读；
2. 40 个端点去重与阶段复用正确，S1 只在 digest 后解盲；
3. DAG、N1–N11、floor、比较方向、FAIL 标签和退出码机器可判定；
4. create-only 父事务、子包完成语义、NPZ schema 和 hash ledger 无覆盖路径；
5. 容器命令满足单 CPU、8 GiB、3600 秒、无网络/GPU/socket；
6. 资源估算与历史锚点相容，且没有把 3600 秒误当作每子包预算；
7. 没有心肌 DCM、identity、第二求解器、参数扫描或新生产观测量；
8. 本文只是一份执行合同，不冒充实现、测试或数值 PASS。

本文件落盘后立即停止。本轮不授权写代码/测试、运行 solver/Docker、创建结果目录、
修改 v03/验收决定/CURRENT_STATUS/核心源码/旧证据，或执行 Git add、commit、push。
