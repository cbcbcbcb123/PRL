---
execution_id: EXE-PAPER2-M2A-V07-IDENTITY-NO-GO-DIAGNOSTIC-V01
plan_id: PLAN-PAPER2-M2-IDENTITY-FAILURE-DIAGNOSTIC-V07
authorization: DEC-PAPER2-M2A-V06-1-NO-GO-ACCEPT-V07-DIAGNOSTIC-V01
executor: Codex Executor
started_at: 2026-09-04
completed_at: 2026-09-04
status: completed_at_supervisor_gate
formal_diagnostic_label: MODE_SELECTIVE_CONSTITUTIVE_MISMATCH
frozen_identity_decision: NO-GO-ID
deviation_records: []
---

# Paper 2 M2A v07 identity NO-GO 只读诊断执行记录 v01

## 1. Approved plan reference

本执行依据：

- v07 只读诊断合同：
  `project_control/paper2_m2_active_myocardial_fem_identity_failure_diagnostic_contract_v07.md`；
- v06.1 Supervisor 验收与 v07 授权决定：
  `project_control/paper2_m2a_v06_1_no_go_identity_supervisor_acceptance_and_v07_diagnostic_decision_v01.md`；
- v06.1 冻结 identity 结果：
  `results/paper2_m2/identity_gate_v06_v02_20260904/`；
- 冻结 T128/T256 源包：
  `results/paper2_m2/identity_2d_v04_t128_v02_20260903/` 与
  `results/paper2_m2/identity_2d_v05_t256_v02_20260904/`；
- 执行 Git 基线与同名远端分支：
  `7c1c1fcbe8ec424f953b18daab7fe682b2c10cfc`。

授权仅允许读取既有 v06.1/T128/T256 证据，分解正式失败牵引记录并审计生产提取源码。
不允许重算端点、改变 identity、拟合模型参数、修订实现或进入 M2B。

## 2. Files changed and outputs produced

新增实现与测试：

- `src/paper2_m2/identity_no_go_diagnostic_v07.py`；
- `scripts/run_paper2_m2_identity_no_go_diagnostic_v07.py`；
- `tests/paper2_m2/test_identity_no_go_diagnostic_v07.py`。

新增 create-only 正式结果包：

- `results/paper2_m2/identity_no_go_diagnostic_v07_v01_20260904/`。

结果包含 12 个 JSON；hash ledger 列出其余 11 个文件且文件集合、字节数与 SHA-256
逐项一致。没有生成 NPZ。v06.1、T128、T256 结果包和冻结生产源码的执行前后哈希一致。
未执行 Git add、commit 或 push；工作树中原有无关修改和未跟踪结果均未改动。

## 3. Tests and checks

- v07 定向测试：`22 passed in 1.43 s`；
- v04-v06.1 协议、共同投影、源锁和 v07 轻量回归：`74 passed in 13.97 s`；
- Ruff：3 个新增文件全部通过；
- 傅里叶 Parseval 最大相对闭合误差：
  `4.1076386281334604e-16 < 1e-12`；
- 空间均值/异质分解最大正交闭合误差：
  `4.1316445308972675e-16 < 1e-12`；
- 8 个 signed-permutation 矩阵均被穷举；近零分量按合同只报告绝对差，不参与不稳定
  相对差分类；
- 正式包 12/12 JSON 可严格解析且全部数值有限；hash ledger 11/11 复算一致；
- 正式只读后处理耗时 `13.776534800010268 s < 600 s`，峰值内存
  `0.050426483154296875 GiB < 8 GiB`；单 CPU 进程，未使用 Docker、GPU、网络、
  外部求解器或端点重算。

## 4. Formal diagnostic classification

正式诊断标签：`MODE_SELECTIVE_CONSTITUTIVE_MISMATCH`。四个合同候选条件中仅该条件为
真；v06.1 的正式 `NO-GO-ID` 保持不变。

### 4.1 统一归一化解释被否定

四条正式失败牵引记录的共同最优实标量为 `1.094511367664237`，但应用后各记录残差为：

| 正式失败记录 | 共同标量后残差 | 逐记录最优标量 | 逐记录最优标量后残差 |
|---|---:|---:|---:|
| `ID-A2__myocardium_ecm` | `1.1462822611` | `0.4646701445` | `0.7905789767` |
| `ID-A2__endocardium_ecm` | `1.9168933799` | `0.2847384113` | `0.7890933080` |
| `ID-S1__myocardium_ecm` | `0.1078104652` | `1.1208747290` | `0.1052426580` |
| `ID-S1__endocardium_ecm` | `0.2511301257` | `1.0600855463` | `0.2491529829` |

因此不存在一个共同幅值因子把四条记录同时降至 `<=5%`，而且 A2 的逐记录最优比例
与共同比例相差 `57.55% / 73.98%`。该标量仅用于诊断，没有写回模型参数。

### 4.2 坐标基和提取实现解释被否定

8 个允许的有限正交基中，共同最优仍是 identity：
`[[1, 0], [0, 1]]`。其拼接残差为 `0.2021687541`，四条记录最大残差仍为
`0.8040305799`，不存在共同的非 identity signed-permutation 使四条记录全部降至
`<=5%`。

生产源码审计未发现单位、符号、测度、权重、分量顺序、共同投影或两种表示之间的
非预期分支。两臂使用同一个线性 penalty 界面牵引密度提取式；符号为
`positive_on_first_named_domain`，`x` 为切向、`y` 为法向，空间范数与投影使用同一
64 段参考界面弧长权。该量是共享 penalty traction density，不是从 Cauchy/Piola
应力重新恢复的牵引。

### 4.3 差异定位到激励模式和物理分量

纯主动模式 `ID-A2` 的两侧牵引在任一统一比例或共同有限坐标基之后仍远高于 `15%`。
机器分类定位的纯主动分量为：

- `ID-A2__myocardium_ecm__x`：差异以空间异质项、时间 DC 为主；
- `ID-A2__myocardium_ecm__y`：差异以空间均值、时间基频为主；
- `ID-A2__endocardium_ecm__y`：差异以空间均值、时间基频为主。

原始向量方向证据也支持这不是单纯幅值问题：A2 两侧加权余弦仅为
`0.6123600915 / 0.6142733523`，对应方向差约 `0.9118 / 0.9093 rad`；S1 两侧方向更接近，
但共同或逐记录缩放后仍分别留下 `>10%` 和 `>24%` 的形状/方向残差。

## 5. Pure-mode and superposition checks

`ID-A2`、`ID-LN`、`ID-LS` 的缩短、位移、两侧 `x/y` 牵引、周期耗散和储能变化均按
物理量分开审计，没有把不同单位量合并成一个范数。

`ID-C0/ID-CQ` 对 A2+LN 的 DC/基频重构最大残差仅
`0.0023057714266971428`。这说明在当前冻结小扰动基准内，组合载荷的主要 DC/基频响应
基本可由纯模式叠加解释；它不证明模型整体线性，也不改变 identity 失败。

报告的最大 T128→T256 相对变化为 `0.10708356610715435`，来自幅值约
`1.68e-10` 的 FEM 切向位移；其绝对变化仅 `1.8030974495878513e-11`，按合同固定
`1e-10` 分母/近零判据仍属于有限分量。该数值不用于 v07 分类，也不被解释为新的时间
收敛失败。

## 6. Resources and hashes

关键正式结果 SHA-256：

- `traction_scale_direction_components.json`：
  `c9a0395325dd1cf846a2850b349f82e6d0d63888efcd90440a298d3b86696c25`；
- `spatiotemporal_mode_decomposition.json`：
  `89a2c0d9d5f5828b40dedd5188de7ed619375ed485599be1c699a7d58a692b9d`；
- `signed_permutation_basis_audit.json`：
  `c422c3663ecf5b895ded72c171610f63a43acd6c8db296769ebf1819ff9e5a54`；
- `superposition_audit.json`：
  `aac142de68a902dd0b53562c439a23b2257c7b959401c3d993b9f64ef4f4f4ae`；
- `source_formula_audit.json`：
  `7be1a9557369bdca8bc6651be6b8f6373e5ef9ce5b8dbd9bbb13d64110164b97`；
- `diagnostic_classification.json`：
  `276a92ae8e07750d9c4da4e8376c0f2f85896d479fa6d6c755597a03e2b154db`；
- `pass_summary.json`：
  `a1b22def3a3dc2e260709608899cc33d1c6adc5331c622ed6dd4d18ed79537ab`；
- `run_manifest.json`：
  `90205cf15422726e46cbced909f6138a2405cd8a16bf2cb3f5d1f3a6d2b888d1`。

新增实现 SHA-256：

- `identity_no_go_diagnostic_v07.py`：
  `650fe3eb0fbf4d859e222be2f91068d796eed20f46e920b56529b39accb08243`；
- v07 runner：
  `5b4fdcadd261f433c2b661f48a8f57abe63805443e417206753b2f311d129f35`；
- v07 tests：
  `48a2aa4578fff2cd0b982e9e5c9b64978e23b128ae850091130682300249755c`。

## 7. Evidence boundary and stop state

本标签只说明：在冻结理想化二维、六留出、S4/T256/D0 基准中，DCM 与主动心肌 FEM
的差异不能由单一归一化、允许的有限坐标基或已审计的提取实现解释；差异具有明确的
模式与分量选择性，因此当前证据最支持两种心肌表示的本构响应并不等价。

它不是模型修复，不判定哪种表示“正确”，也不构成三维、整心房、生理标定、EFE、实验、
流体或临床证据。执行已停止在 Supervisor Gate；没有授权或运行 identity retry、
重新标定、模型/提取修改、M2B、三维、整心房、CFD/FSI、GPU worker、新外部求解器或
参数扫描。
