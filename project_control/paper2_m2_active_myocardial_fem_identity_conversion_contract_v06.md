---
plan_id: PLAN-PAPER2-M2-ACTIVE-MYO-FEM-IDENTITY-V06
status: approved_under_human_standing_authority
approved_at: 2026-09-04
standing_authority: project_control/paper2_autonomous_execution_and_chart_reporting_decision_v01.md
authorization: project_control/paper2_m2a_v05_1_t256_supervisor_acceptance_and_identity_gate_decision_v01.md
source_t64: results/paper2_m2/identity_2d_v03_t64_v01_20260903/
source_t128: results/paper2_m2/identity_2d_v04_t128_v02_20260903/
source_t256: results/paper2_m2/identity_2d_v05_t256_v02_20260904/
result_path: results/paper2_m2/identity_gate_v06_v01_20260904/
executor_thread_id: 019fc73d-393d-71a3-98cb-d3c0cd0c8eda
execution_authorized: read_only_s4_t256_d0_identity_postprocessing_only
---

# Paper 2 M2A 主动心肌 FEM 身份转换合同 v06

## 1. 科学问题与结论边界

本阶段只回答：在冻结理想化二维体系、S4 最细空间层、T256、D0 直接求解器下，DCM 与
主动心肌 FEM 对预注册留出工况是否满足 v01 冻结的跨表示 identity 门。

本阶段不重新求解模型，不拟合参数，不改变共同投影，不用校准工况证明身份，也不回答
三维、整心房、生理标定、EFE 疾病机制、流体或 FSI 问题。

## 2. 前置条件与源锁

执行前必须同时满足：

1. v03/T64、v04/T128、v05.1/T256 三个成功包可读；
2. 三个包的 run manifest、hash ledger 和关键成功摘要可解析且与当前文件一致；
3. v05.1 记录的 54/54 端点、74/74 空间门、54/54 周期门、2/2 热点门和 74/74
   三层时间门均保持通过；
4. v01-v05.1 冻结实现及源结果哈希不变。

任一条件不满足即 `BLOCKED`，不得通过重算、覆盖或补写旧包恢复。

## 3. 比较集合

只比较 `S4/T256/D0` 的 DCM 与 FEM 两臂。

| 类型 | 工况 | 用法 |
|---|---|---|
| 结构控制 | `ID-P0` | 结构与零驱动一致性；不计入留出身份通过数 |
| 校准审计 | `ID-P1`, `ID-A1` | 只报告 audit-only；不得作为 identity 通过证据 |
| 预注册留出 | `ID-A2`, `ID-LN`, `ID-LS`, `ID-C0`, `ID-CQ`, `ID-S1` | 正式 identity 判定 |

所有正式门必须按工况和观测量逐条输出，不得只给汇总均值。

## 4. 冻结算子

### 4.1 标量相对差

对两臂标量 `x_DCM`、`x_FEM`：

`d_rel = abs(x_DCM - x_FEM) / max(abs(x_DCM), abs(x_FEM), floor)`。

冻结 floor：峰值缩短 `1e-6`，牵引 `1e-8`，能量与耗散 `1e-10`。同时报告绝对差。
当两臂绝对量均低于 floor 时，只用绝对门，不报告其相对差为身份失败。

### 4.2 周期窗口与波形

动态数组只取首个完整 T256 周期 `[0:256]`；不得包含重复周期终点。缩短波形差为：

`||u_DCM-u_FEM||_2 / max(||u_DCM||_2, ||u_FEM||_2, 1e-10)`。

### 4.3 共同界面牵引

两条界面均须独立比较：

- 心肌–ECM；
- 心内膜–ECM。

原生牵引数组按 `(129, 2, 256)` 解释。沿空间轴用守恒分段积分投影到冻结的 64 个共同
分段，再计算带共同弧长权的时空归一化 `L2` 差。禁止直接比较原生数组，也禁止把一条
界面代替“两条界面共同牵引”。

### 4.4 基频相位

相位信号冻结为：

- `ID-LN`：负法向位移；
- `ID-LS`：切向位移；
- 其余动态留出：缩短波形。

去均值后计算基频复幅值；两臂幅值均须大于 `1e-10`，否则相位门记为不适用并转入
结构/绝对量审计。适用时报告包裹到 `[-pi, pi]` 的相位差绝对值。

## 5. 正式 identity 门

对六个留出工况逐项应用：

| 门 | 阈值 |
|---|---:|
| 峰值缩短相对差 | `<= 5%` |
| 缩短波形归一化 L2 差 | `<= 5%` |
| 心肌–ECM 共同牵引归一化 L2 差 | `<= 5%` |
| 心内膜–ECM 共同牵引归一化 L2 差 | `<= 5%` |
| 基频相位差 | `<= 0.05 rad` |
| 周期总耗散相对差 | `<= 10%` |
| 周期总储能绝对差 | `<= 1e-10` |

组合载荷 `ID-C0`、`ID-CQ` 的主要增益相对差还必须 `<=10%`。`ID-S1` 的共同网格热点
中心差必须 `<=1/128`，且不得出现未解释的热点分裂。

`ecm_strain_at_peak`、`ecm_internal_z_at_peak`、`ecm_stress_at_peak` 只作诊断报告，因为
v01 没有为这些场量冻结 identity 阈值；不得据此新增通过或失败门。

## 6. 合并数值变化包络

每项 identity 差异同时报告数值变化包络，但不得从 identity 差异中扣除该包络：

- 标量：两臂各自 `S3→S4` 与 `T128→T256` 的绝对变化之和；
- 波形：两臂各自真实 T128→T256 波形差，加上冻结 S3→S4 标量空间代理；
- 两条共同牵引：按同一共同投影计算两臂 T128→T256 差，并加冻结空间代理；
- 相位、组合增益和热点：直接使用冻结摘要对应变化；
- 储能近零项使用绝对包络。

包络仅用于解释 identity 差异相对于数值变化的量级，不改变第 5 节阈值或分类。

## 7. 决策逻辑

- `GO-ID`：所有结构门、数值前置门和六个留出工况的所有适用 identity 门通过。
- `MAYBE-ID`：不存在 NO-GO 条件，但至少一项相对差超过正式阈值且 `<=15%`，或适用
  相位差为 `(0.05, 0.15] rad`；必须列出可迁移与不可迁移端点。
- `NO-GO-ID`：任一关键相对差 `>15%`、适用相位差 `>0.15 rad`、储能绝对门失败、
  `ID-S1` 热点门失败、已有结构/功率/作用反作用/周期/收敛门失效，或出现非有限值。
- `BLOCKED`：源锁、哈希、解析、路径或资源前置条件失败，导致无法完成完整判定。

不允许调整阈值以改变分类。`GO-ID` 也不构成 M2B 自动执行权。

## 8. Create-only 输出

目标目录：`results/paper2_m2/identity_gate_v06_v01_20260904/`。

至少输出：

- `preflight.json`；
- `identity_gate_by_case.json`；
- `identity_gate_summary.json`；
- `numerical_change_envelope.json`；
- `calibration_audit_only.json`；
- `field_diagnostics_audit_only.json`；
- `run_manifest.json`；
- `hash_ledger.json`；
- `pass_summary.json` 或 `failure_summary.json`。

输出只允许 JSON 和必要的小型文本日志；不得生成新 NPZ，不得修改任何源结果包。

## 9. 实现与测试

优先新增：

- `src/paper2_m2/protocol_v06.py`；
- `src/paper2_m2/identity_gate_v06.py`；
- `scripts/run_paper2_m2_identity_gate_v06.py`；
- `tests/paper2_m2/test_protocol_v06.py`；
- `tests/paper2_m2/test_identity_gate_v06.py`；
- `project_control/paper2_m2a_v06_identity_gate_execution_record_v01.md`。

测试至少覆盖：共同 64 分段守恒投影、两条界面分别计门、周期窗口、归一化 L2、近零
floor、相位包裹、校准工况 audit-only、GO/MAYBE/NO-GO/BLOCKED 边界和源锁 fail-closed。

## 10. 资源与停止条件

只允许 CPU 只读后处理，总时间上限 `600 s`，峰值内存上限 `8 GiB`，不得使用 GPU、
网络或新求解器。完成或失败后均须写执行记录并停止在 Supervisor Gate。

禁止继续 M2B、S5、三维、整心房、真实几何、流体/CFD/FSI、重新标定或参数扫描。

## 11. 证据边界

identity 结论只对本合同列明的理想化二维、冻结工况、观测量、空间层和时间层成立。
即使得到 `GO-ID`，也不证明细胞模型在所有载荷下等价，不证明真实心房/心室、EFE、
生理参数或实验系统，也不得把诊断场量升级为预注册身份门。
