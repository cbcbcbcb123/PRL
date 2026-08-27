---
report_id: REPORT-PRL-HYBRID-X1-K-V10R1-EVIDENCE-PACKAGING-SEMANTIC-REPAIR
status: packaging_repair_complete_scientific_failure_preserved
contract_commit: 785796d409b9f43ef9657b7d6b44a10d36d5eef1
approved_baseline_commit: ddd663d461da7b25aefd5cf3fbecff488800053e
v10_contract_commit: e54bc5933387070c697f5c88218f37f25faea4c3
v10_result_commit: 2919a5df50d9fa287fe823ee5a1bb9169c438f65
cell_engine_gitlink: e2ed64a26bb5d7c2d878772564fb5ffcca343c3a
v10_scientific_status: failed_v10_midpoint_collapse_diagnosis_eligible_candidate_material_rebind
classification_status: not_adjudicated_due_to_first_failure
x1_k_passed: false
r1_passed: false
c1_f1: not_executed
downstream_authorized: false
---

# X1-K v10r1 证据包装与语义修补执行报告

## 1. 执行结论

本次只完成 append-only 的 v10r1 证据包装与语义修补，包装状态为
`packaging_repair_complete_scientific_failure_preserved`。该状态不表示新的科学响应通过，也不改变冻结 v10 的失败结论。

v10 scientific status 继续为
`failed_v10_midpoint_collapse_diagnosis_eligible_candidate_material_rebind`；机制 classification 继续为
`not_adjudicated_due_to_first_failure`；`x1_k_passed=false`、`r1_passed=false`、`c1_f1=not_executed`、`downstream_authorized=false`。本任务没有运行新的 microprobe、formal R1 response 或 C++ 科学响应，没有生成新物理数据，没有修改 controlled fork，也没有进入 C1/F1。

## 2. 配置产物修补

冻结 v10 合同要求交付配置，但 `results/hybrid/x1_k_r1_midpoint_collapse_diagnosis_v10/` 中没有配置文件。v10r1 新增的 `configuration.json` 明确标记为
`reconstructed_after_v10_freeze_for_v10r1_packaging_repair`，同时记录
`historical_v10_delivery_claim=false`，因此不声称该文件在 v10 当时已经交付。

配置从三类冻结来源重建：v10 合同、v10 C++ runner/source defaults、v10 原始 response/exitcode；另用 v10r1 合同记录“本次未运行新科学响应”的执行边界。共形成 32 个配置字段，覆盖容差、cell/revision/mesh、被动参数、两个 material point、active-contraction unit、production sink、public refiner、执行路径、禁用的动力学/耦合项、候选顺序、输出精度与 formal-response 退出语义。每个字段都保存值、source commit、source path、line range 或 record/key locator 及 source value；32/32 字段闭合，5 个唯一 `commit:path` Git 对象存在并通过核验。

## 3. 候选 3 topology 语义修补

冻结 runner 的 `CandidateResult.topology_legal` 默认初始化为 false。候选 3 的真实 production merge 在 material-transfer sink 抛出异常后，于 post-merge topology audit 之前返回；旧异常分支仍把默认布尔值输出为 `topology_legal=false`。因此该值只能视为旧序列化痕迹，不能视为通用拓扑非法裁决。

v10r1 的规范 `topology_status` 为：

| candidate | merge_succeeded | topology_status | topology_legal |
|---:|---:|---|---:|
| 1 | true | `adjudicated_legal` | true |
| 2 | true | `adjudicated_legal` | true |
| 3 | false | `not_adjudicated_due_to_production_sink_exception` | null / CSV 空值 |
| 4 | true | `adjudicated_legal` | true |

候选 3 继续原样保存 `can_be_merged=true`、`merge_succeeded=false`、异常文本及
`0.047434164902525666 > 1e-12`。`legacy_topology_legal_serialized=false` 仅作为 provenance 明示保留；没有把候选 3 改成 legal，也没有把 `merge_succeeded=false` 改写。详细说明位于 `semantic_erratum.json`。冻结 raw log、v10 candidate matrix 和全部 v10 文件保持字节不变。

## 4. 冻结完整性门禁

`frozen_integrity.json` 以批准父提交 `ddd663d461da7b25aefd5cf3fbecff488800053e` 为基线，覆盖 v09/v10 六个合同、结果和同步生命周期提交所涉及的 102 个冻结 Git blob：当前 blob mismatch 为 0，相关工作树改动为 0。

冻结 v10 `provenance_manifest.json` 的 10 条 raw evidence 与
`verification_artifact_manifest.json` 的 18 条 verification evidence 仍全部存在；28/28 条均按原 SHA-256 与字节数复算匹配。候选 3 的冻结 observation 仍为 `merge_succeeded=false`、旧序列化 false、重绑定距离 `0.047434164902525666`、阈值 `1e-12`。

新 `provenance_manifest.json` 记录冻结输入提交、32/32 配置 provenance 闭合、核心新产物哈希和 verification manifest。它不复制冻结输入，不包含自引用哈希；第三阶段的 `remote_sync.json` 在结果提交推送后另行新增。

## 5. TDD 与软件验证

按行为切片保存了真实 RED/GREEN：

- 缺失配置产物：有效 RED exit 1；配置重建 GREEN 1/1；
- topology 二值误映射：RED 明确显示 candidate 3 被错误解释为 `adjudicated_illegal`；修补后 GREEN 2/2；
- 核心包装产物：缺文件 RED；实现后 GREEN 3/3；
- 冻结完整性 seam：RED；实现后 GREEN 4/4；
- provenance manifest：缺文件 RED；实现后 GREEN 5/5。

最终 required verification 为：

- exporter 真实复算：exit 0；
- focused Python：5/5，exit 0；
- 完整 Python：88/88，exit 0；
- Ruff：exit 0。

隔离 worktree 的 `external/simucell3d/` 未初始化。直接完整测试曾因此让旧 v10 provenance 测试把空目录误识别为父仓库，形成 87 passed / 1 layout failure；该日志原样保留并标记为 superseded。最终完整测试没有初始化或写入该目录，而是只读使用现有父工作区中 HEAD/upstream 均为 `e2ed64a26bb5d7c2d878772564fb5ffcca343c3a` 的 controlled fork；其余测试仍针对当前 worktree 代码。命令行参数试运行、bundled Python 缺 pytest 以及中间 GREEN 语法/回归失败也均保留并在 `verification_summary.json` 中与 required pass 分开标记。

## 6. Executor 停止点

本报告只记录执行结果，不作独立验收。结果提交与远端同步证明完成后，状态只能进入
`execution complete / inspection eligible`，等待 Inspector 只读检查。未起草 v11，未修 fork，未进入 C1/F1。
