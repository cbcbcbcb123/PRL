---
execution_id: EXE-PAPER2-M2A-V06-IDENTITY-GATE-V01
plan_id: PLAN-PAPER2-M2-ACTIVE-MYO-FEM-IDENTITY-V06
executor: Codex Executor
started_at: 2026-09-04
completed_at: 2026-09-04
status: blocked
formal_decision: BLOCKED
failure_classification: T64_FROZEN_IMPLEMENTATION_HASH_MISMATCH
deviation_records: []
---

# Paper 2 M2A v06 identity gate 执行记录 v01

## 1. Approved plan reference

本执行依据：

- v05.1 Supervisor 验收与 v06 授权：
  `project_control/paper2_m2a_v05_1_t256_supervisor_acceptance_and_identity_gate_decision_v01.md`；
- v06 合同：
  `project_control/paper2_m2_active_myocardial_fem_identity_conversion_contract_v06.md`；
- 当前状态：`project_control/CURRENT_STATUS.md`；
- 持续授权：`project_control/paper2_autonomous_execution_and_chart_reporting_decision_v01.md`；
- 执行基线：`3356bbdccb0d6ba2fa78e488c8598592509c8539`，执行前与远端同名分支一致。

授权只允许读取冻结 T64、T128、T256 成功包，并比较 S4/T256/D0 的 DCM 与 FEM。
源锁、哈希、解析或资源前置条件任一失败，必须输出 `BLOCKED` 并停止；不得通过重算、
覆盖或补写旧包恢复。

## 2. Commands or tools used

- 只读核对 v06 合同、决定、当前状态、持续授权及 Git 基线；
- 检查三个冻结成功包的 manifest、hash ledger、成功摘要、端点摘要、结构门、数值门和
  动态留出清单；
- 新增 v06 纯后处理协议、identity 算子、runner 与测试；
- 宿主 CPU 单进程执行 v06 定向测试和旧协议/投影轻量回归；
- 正式入口只执行路径、源包、冻结实现、测试和 v01 增益算子前置锁；
- 对 create-only 失败包执行严格 JSON、有限值、SHA-256、字节数和文件类型审计。

未启动 DCM/FEM solver 或任何端点，未使用 Docker、GPU、网络或新求解器。

## 3. Files changed

新增：

- `src/paper2_m2/protocol_v06.py`；
- `src/paper2_m2/identity_gate_v06.py`；
- `scripts/run_paper2_m2_identity_gate_v06.py`；
- `tests/paper2_m2/test_protocol_v06.py`；
- `tests/paper2_m2/test_identity_gate_v06.py`；
- create-only 失败包：
  `results/paper2_m2/identity_gate_v06_v01_20260904/`；
- 本执行记录。

按合同更新 `project_control/CURRENT_STATUS.md`。未修改 v01-v05.1 实现、T64/T128/T256
源结果包或工作树中 7 项既有无关 tracked 修改。未执行 Git add/commit/push。

## 4. Tests or checks run

- Python 语法编译：通过；
- v06 定向测试：`18 passed in 0.88 s`；
- v03-v06 协议、路径、资源门、64 段投影及 v06 identity 回归：
  `37 passed in 5.01 s`；
- 覆盖内容包括：64 段守恒投影、两条界面分别计门、首周期窗口、归一化 L2、近零
  floor、相位包裹、校准工况 audit-only、GO/MAYBE/NO-GO/BLOCKED 边界、热点分裂、
  源锁 fail-closed；
- `ID-LN`/`ID-LS` 相位包络回归确认不把
  `shortening_phase_relative_to_activation_rad` 当作法向/切向位移的 S3→S4 空间分量；
- `combined_load_gain` 精确复用
  `scripts/run_paper2_m2_identity_2d_v01.py:545-568`：组合工况缩短基频幅值除以
  `max(ID-A2 幅值 + ID-LN 幅值, shortening floor)`；
- v01 增益源文件锁：期望和当前 SHA-256 均为
  `6d637e1b67a69c8a8c16a01267194f0f4a87502433bacd7522d0d9841e09a1a4`；
- 失败包 4 个 JSON 均可解析且数值有限，hash ledger 3/3 条目 SHA-256 与字节数一致，
  且没有 NPZ。
- 提交前 `git diff --check` 仅报告 v06 runner 和两个 v06 测试各有一个额外 EOF 空行；
  这三个文件的精确字节哈希已由本次失败包和本记录封存，因此为保持失败证据可复验，
  不在事后修改其字节。该格式警告不影响 18/18 与 37/37 测试结论。

## 5. Deviations

无正式实现或科学口径偏差。正式 `combined_load_gain` 没有采用前期内存探索中使用过的
activation 分母；该探索值未写入文件、代码或正式判定。最终实现和测试只使用冻结 v01
算子，因此不是事后选择指标。

按独立公式检查，`ID-LN`/`ID-LS` 的相位数值包络只保留真实 T128→T256 custom-signal
相位差，并明确记录缺少冻结 S3 custom-signal archive；不伪造空间相位分量。正式相位
identity 门本身未改变。

## 6. Blockers

正式入口在源锁阶段发现 T64 manifest 冻结实现哈希不一致：

- 路径：`tests/paper2_m2/test_protocol_v03.py`；
- T64 manifest 记录的期望 SHA-256：
  `4eb28d7c38f8606e590b1216b337fd5bbde3d0fe95afab43682d7d84e66bf25f`；
- 当前文件 SHA-256：
  `502a5c9273c1c5b1c95f9457ffc411ed710c99f0f4e169cc89a23b92f61bf5b5`；
- 当前文件无工作树修改；Git 记录显示其最后一次内容提交为
  `6ff45110d436367535e59e464f6911bf0bfaae97`；
- LF/CRLF 内存复核不能解释该差异，因此不能把它降级为换行误报。

T64 结果包本身的 23/23 ledger、54/54 端点、54/54 结构门、74/54/2 数值门、12 个动态
留出和 JSON 有限值均通过；T128 与 T256 源锁全部通过。阻塞仅来自合同要求的冻结实现
精确哈希不一致，但该条件足以触发 fail-closed。

由于目标目录现已保留此次失败证据，不能删除、覆盖或用同一路径重试。任何修复都需要
Supervisor 明确裁决该旧 manifest 不一致，并为重试指定新 create-only 路径。

## 7. Outputs produced

失败包：`results/paper2_m2/identity_gate_v06_v01_20260904/`。

正式输出：

- 决策：`BLOCKED`；
- 状态：`FAIL_CLOSED_AT_SUPERVISOR_GATE`；
- 阶段：源锁前置检查；
- identity 正式比较：未计算；
- solver/端点：未运行；
- 耗时：`7.56137230002787 s < 600 s`；
- 峰值内存：`0.03887939453125 GiB < 8 GiB`；
- GPU/网络：未使用。

关键 SHA-256：

- `preflight.json`：
  `eae4fc4b67cab1afccf67183e668024255cfb65b36ee586e3a2997e082103589`；
- `failure_summary.json`：
  `866f1522855e8c7d8a8d59c0e534df62389358c10322d795ea2294d9a726a183`；
- `run_manifest.json`：
  `050fc0623b1822cad92dbb00ad7fc28d6469bdac1ecc8ba78e3b08a29c316815`；
- `hash_ledger.json`：
  `f2d40ba386c82f43585e745c7ed0af87f092a3259b3556859fd8e4a852c26cd1`。

v06 实现与测试 SHA-256：

- `protocol_v06.py`：
  `e7803c3ed33c560662933c9e6ca37a2be11757489eddb388c76a8bf3f33966ce`；
- `identity_gate_v06.py`：
  `9b1894cc84a1bee77ce17e055a3f68a048fd93f6827caa24f3a1c42166535dd4`；
- v06 runner：
  `015f203eaa3dc5b1a21f43a03b5bc754f3031d0bdfa44f8cb18f45bb9acaf6c5`；
- `test_protocol_v06.py`：
  `c2dbc391b53e56916928d68cfa7821c795e0923d0d4654b124a33413f4442977`；
- `test_identity_gate_v06.py`：
  `7ca1900d053cddb0940200c384040258f780374bf4557dd7da955385c6a4dc2b`。

## 8. Evidence boundary and stop state

本次只证明 v06 后处理实现的定向测试通过，并记录一个 T64 冻结实现哈希前置阻塞。
由于完整源锁没有通过，不能从任何探索性内存计算或部分数据导出 GO-ID、MAYBE-ID 或
NO-GO-ID；当前唯一正式结论是 `BLOCKED`。

执行已停止在 Supervisor Gate。未运行 M2B、S5、三维、整心房、真实几何、
流体/CFD/FSI、重新标定、参数扫描、GPU 或新外部求解器。
