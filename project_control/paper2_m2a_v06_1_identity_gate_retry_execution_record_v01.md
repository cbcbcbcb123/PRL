---
execution_id: EXE-PAPER2-M2A-V06-1-IDENTITY-GATE-RETRY-V01
plan_id: PLAN-PAPER2-M2-ACTIVE-MYO-FEM-IDENTITY-V06
authorization: DEC-PAPER2-M2A-V06-T64-TEST-EOF-HASH-V06-1-RETRY-V01
executor: Codex Executor
started_at: 2026-09-04
completed_at: 2026-09-04
status: completed
formal_decision: NO-GO-ID
source_lock_compatibility: ACCEPTED_TEST_EOF_FORMATTING_DELTA
deviation_records: []
---

# Paper 2 M2A v06.1 identity gate 重试执行记录 v01

## 1. Approved plan reference

本执行依据：

- v06 科学合同：
  `project_control/paper2_m2_active_myocardial_fem_identity_conversion_contract_v06.md`；
- v06.1 单例 EOF 兼容与重试决定：
  `project_control/paper2_m2a_v06_t64_test_eof_hash_diagnosis_and_v06_1_retry_decision_v01.md`；
- v06 `BLOCKED` 执行记录：
  `project_control/paper2_m2a_v06_identity_gate_execution_record_v01.md`；
- 执行 Git 基线与同名远端分支：
  `7ec88653a5fa880d4dd9f0168bacf9b2c2aeb073`。

授权只允许对 T64 的一个已确定测试文件 EOF 差异作字节级单例兼容，然后复用冻结 v06
算子，对既有 S4/T256/D0 结果作一次只读 identity 后处理。T64/T128/T256 结果包、v01-v06
实现、原测试文件和 v06 v01 失败包均保持只读。

## 2. Exact T64 EOF compatibility result

正式标签为 `ACCEPTED_TEST_EOF_FORMATTING_DELTA`，全部 18 项条件通过：

- 来源仅为 `T64`，路径精确为 `tests/paper2_m2/test_protocol_v03.py`；
- T64 manifest 期望 SHA-256：
  `4eb28d7c38f8606e590b1216b337fd5bbde3d0fe95afab43682d7d84e66bf25f`；
- 当前文件为 1681 字节，SHA-256：
  `502a5c9273c1c5b1c95f9457ffc411ed710c99f0f4e169cc89a23b92f61bf5b5`；
- 只在内存字节流末尾追加一个 `0x0A` 后为 1682 字节，SHA-256 精确变为旧 T64
  manifest 期望值；没有写回文件，也没有进行一般空白归一化；
- 当前测试文件 Git clean；
- T128 manifest SHA-256 为
  `302931097e9117d48b8f5a49325c9286711a291562fcee9eea997034be5fd16c`，其
  `read_only_sha256_before` 封存当前 `502a5c...`；
- T256 manifest SHA-256 为
  `fc65096b2c51fcaaba0c8d47405a3549a191be4d73a8cabf554019437884f123`，其
  `read_only_sha256_before` 同样封存当前 `502a5c...`；
- T64 原 v06 锁只有
  `implementation_hash:tests/paper2_m2/test_protocol_v03.py` 这一项失败；其余 T64 锁及
  T128/T256 全部源锁通过；
- v01 `combined_load_gain` 源文件期望与当前 SHA-256 均为
  `6d637e1b67a69c8a8c16a01267194f0f4a87502433bacd7522d0d9841e09a1a4`。

该规则不能用于其他标签、路径、哈希、第二个末尾 LF、CRLF/空格或任意内容变化。

## 3. Files changed and outputs produced

新增实现与测试：

- `src/paper2_m2/protocol_v06_1.py`；
- `scripts/run_paper2_m2_identity_gate_v06_1.py`；
- `tests/paper2_m2/test_v06_1_source_lock.py`。

新增 create-only 结果包：

- `results/paper2_m2/identity_gate_v06_v02_20260904/`。

结果包包含 11 个 JSON：v06 约定的 preflight、逐工况 identity、identity 汇总、数值变化
包络、校准审计、场诊断、run manifest、pass summary 和 hash ledger，并额外包含分类复核与
有限值审计。没有生成 NPZ。

未修改 v06 合同、v06 实现/测试、原测试文件、v06 v01 失败包、T64/T128/T256 源包或
工作树中既有 7 项无关 tracked 修改。未执行 Git add、commit 或 push。

## 4. Tests and checks

- v06.1 单例锁、冻结 v06 协议与 identity 定向测试：`35 passed in 9.12 s`；
- v02-v06 协议、共同投影、路径/资源门、v06 identity 和 v06.1 源锁轻量回归：
  `57 passed in 12.98 s`；
- Ruff：3 个新增文件全部通过；
- 更宽的 `tests/paper2_m2` 宿主收集尝试中，3 个求解器测试因宿主缺少 `basix` 而在收集
  阶段停止。该组依赖 FEniCSx 环境，不属于本次 CPU 只读后处理门；本授权禁止启动 Docker
  或求解器，因此未越权补跑。所有 v06/v06.1 定向及相关轻量回归均已通过；
- 正式包 11/11 JSON 可严格解析且全部数值有限；hash ledger 10/10 文件集合、字节数和
  SHA-256 一致；0 个 NPZ；
- run manifest 的 T64/T128/T256 `source_sha256_before` 与 `source_sha256_after` 逐项一致；
- 分类独立复算与冻结 v06 候选结果均为 `NO-GO-ID`，45 条正式记录计数为
  `35 pass / 4 maybe / 6 no_go`；阈值未修改、未加入探索指标、数值包络未从 identity
  差异中扣除。

## 5. Formal identity result

正式决策：`NO-GO-ID`。六个预注册留出工况中，只有 `ID-LS` 的全部适用门通过。

| 工况 | 裁决 | 关键越界量 |
|---|---|---|
| `ID-A2` | NO-GO | 心肌–ECM 牵引差 `80.4031%`；心内膜–ECM 牵引差 `80.3362%` |
| `ID-LN` | NO-GO | 峰值缩短差 `18.3367%`；缩短波形差 `18.0161%` |
| `ID-LS` | PASS | 全部 7 个适用门通过 |
| `ID-C0` | MAYBE | 峰值缩短差 `6.6594%`；缩短波形差 `10.3651%` |
| `ID-CQ` | MAYBE | 峰值缩短差 `7.5106%`；缩短波形差 `10.4343%` |
| `ID-S1` | NO-GO | 心肌–ECM 牵引差 `15.0255%`；心内膜–ECM 牵引差 `25.5128%` |

`ID-S1` 的共同网格热点中心差为 0，且没有热点分裂；两条界面牵引仍分别计门。`ID-C0`
和 `ID-CQ` 的冻结 v01 组合增益差分别为 `5.2098%` 与 `6.5975%`，均通过 10% 门。
储能绝对门、耗散、适用相位与结构控制均未触发 NO-GO。

## 6. Numerical-change envelope interpretation

关键 identity 差异显著大于对应数值变化包络，且包络只作解释、不参与扣除：

- `ID-A2` 两侧牵引差为 `80.4031% / 80.3362%`；对应合并数值包络约为
  `0.8967% / 0.0511%`；
- `ID-LN` 峰值/波形差为 `18.3367% / 18.0161%`；对应包络约为
  `0.0250% / 0.0104%`；
- `ID-S1` 两侧牵引差为 `15.0255% / 25.5128%`；对应包络约为
  `1.7279% / 0.4964%`。

`ID-LN` 与 `ID-LS` 的相位包络只包含真实 T128→T256 自定义位移信号分量；因没有冻结
S3 自定义位移动态档案，空间分量明确标为不完整。该缺口不改变正式相位 identity 门或
`NO-GO-ID` 分类。

## 7. Resources and hashes

- 正式只读后处理耗时：`15.83884029998444 s < 600 s`；
- 峰值内存：`0.057636260986328125 GiB < 8 GiB`；
- CPU 进程：1；GPU、网络、solver/endpoint 均未使用。

关键结果 SHA-256：

- `preflight.json`：
  `1a0e80aae8cc08ff9e852c405a213b66d949062c801c381459cde344e7fdb128`；
- `identity_gate_by_case.json`：
  `110472bbe1a2bcc9a1d46582eb5241fa174c280ed6a68fa630e338cd3e7d660c`；
- `identity_gate_summary.json`：
  `dbdfc5da20aaad53d8db5f2defc9cc4346580443d0ded9a92ac752c2a84cd01c`；
- `numerical_change_envelope.json`：
  `387d9bbcbb6c5f337ccd6b90442b388053b850e9cb1339230b8e6140175cd905`；
- `classification_audit.json`：
  `50b4c76b7d365d7135f150e58ef28e1d184821a1b99ca8af088751267eb9a588`；
- `pass_summary.json`：
  `1d8e201d6564ffb9347216c51618f7ffa250a9d0ccdfb51b3a8640b823afc0ed`；
- `run_manifest.json`：
  `8753d8259903d040a990760c156018c21252ed887f9f0e4a54db3558a8e48aab`；
- `hash_ledger.json`：
  `436d026a8479ef653c7f32cce654e46d6ff45a39c31a47b775c6366486cebce5`。

新增实现 SHA-256：

- `protocol_v06_1.py`：
  `e4972c51db8f85f946107078cc499f5d907eefe254683ebec09620d7519aa4b3`；
- v06.1 runner：
  `480a9be08cde0d210f2b91449caad2f709e06f5ffc93b1275a5d80c98bc499b3`；
- `test_v06_1_source_lock.py`：
  `53b9142a6b578e03196fcf9d3a0611e3350912087765bce2058a89c177f295da`。

## 8. Evidence boundary and stop state

`NO-GO-ID` 只说明：在冻结理想化二维 S4/T256/D0 基准、六个预注册留出和 v06 观测量
下，DCM 与主动心肌 FEM 不能按冻结阈值视作可互换表示。它不是“某一模型错误”，也不
否定两者在特定观测量或 `ID-LS` 工况下的一致性；更不外推到三维、整心房、生理标定、
EFE、实验或流体耦合。

执行已停止在 Supervisor Gate。未运行 M2B、S5、三维、整心房、真实几何、CFD/FSI、
重新标定、参数扫描、GPU worker、新外部求解器或任何端点。
