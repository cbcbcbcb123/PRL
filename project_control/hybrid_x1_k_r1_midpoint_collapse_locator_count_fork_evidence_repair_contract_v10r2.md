---
contract_id: CONTRACT-PRL-HYBRID-X1-K-V10R2-LOCATOR-COUNT-FORK-EVIDENCE-REPAIR
status: frozen_before_v10r2_packaging_response
frozen_at: 2026-08-03
approved_parent_commit: 27b7fbfda1d8533a99dd7c80e91fce15ddfcdd6c
v10r1_contract_commit: 785796d409b9f43ef9657b7d6b44a10d36d5eef1
v10r1_result_commit: 1348f6aff6a3f46437f836ad053618ed68cb9b5b
v10r1_sync_commit: 27b7fbfda1d8533a99dd7c80e91fce15ddfcdd6c
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

# X1-K v10r2 locator、计数与 controlled-fork 证据修订合同

## 1. 修订授权与 append-only 边界

本合同只修复 Inspector 对 v10r1 提出的三类证据包装缺陷：配置 locator 未从冻结 Git blob 真解析、过程计数缺少 machine-readable reconciliation、controlled-fork 完整测试日志不够自解释。v10r2 不产生新的科学响应或物理数据，不修改科学裁决。

只允许新增：

- 本 v10r2 合同与新的中文 v10r2 修订报告；
- `results/hybrid/x1_k_r1_midpoint_collapse_diagnosis_v10r2/`；
- 独立的 v10r2 Python verifier/exporter、combined verification wrapper 与对应行为测试。

禁止修改、覆盖、移除或改判 v01-v10r1 的合同、报告、结果、日志、代码与同步证明；禁止修改 Route H、任何 C++ 文件、`external/simucell3d/`、submodule pointer、`figures/` 和受保护脚本。v10r1 的 RED/GREEN、superseded 与 required-pass 日志全部保持字节不变。

## 2. 32 个 canonical configuration leaf

v10r2 配置使用以下唯一 canonical count 定义：从 `configuration` 根递归遍历 mapping；mapping 继续展开，数组整体作为一个 leaf，任何其他值为 leaf。leaf path 必须按字典序列举、无重复，独立重算结果必须为 32。

每个 leaf 必须包含至少一个结构化 source locator：source commit、path、locator kind、line range 或 record/key selector、parser id 及期望值。验证器必须通过 Git object 数据库读取 `source_commit:path` 的真实 blob 字节，再由对应 parser 从实际内容解析值；不得读取当前工作树副本冒充冻结来源，也不得仅检查 JSON 中 `source_value == value`。

以下六项必须修订为可真实解析且与冻结内容一致的 locator：

1. `configuration.execution.production_path`：从 v10 合同的 production pipeline 代码块解析；
2. `configuration.execution.disabled_dynamics_and_couplings`：从 v10 合同冻结初态句解析；
3. `configuration.execution.candidate_order`：从 v10 合同全候选枚举段解析；
4. `configuration.execution.new_microprobe_run`；
5. `configuration.execution.new_formal_response_run`；
6. `configuration.execution.new_physical_data_generated`：后三项从冻结 v10r1 合同的明确非目标句解析为 false。

其余 26 个 leaf 同样必须做真实 source resolution。line range 越界、blob 不存在、parser 不支持、record/key 不唯一、解析值与 canonical value 不同均 fail closed。TDD 必须先证明：只篡改 locator、同时保持 JSON `source_value` 与 canonical value 自洽时仍会 RED；然后实现到 GREEN。最终报告真实 source resolution 的通过数，目标为 32/32。

## 3. Count reconciliation

新增 `count_reconciliation.json` 与中文说明，机器列举两个 canonical set：

- configuration leaf：按第 2 节规则列举 32 个 path；
- frozen lifecycle blob：对 v09/v10 六个生命周期提交
  `f7701d59ce3e1c94737e3b0a276205ed70fae6f8`、
  `10bb2c2602b499b5a75ba2d57a35ba717e156616`、
  `855bd8b7467761ba7fcdaa49632bed2ee5681e85`、
  `e54bc5933387070c697f5c88218f37f25faea4c3`、
  `2919a5df50d9fa287fe823ee5a1bb9169c438f65`、
  `ddd663d461da7b25aefd5cf3fbecff488800053e`
  分别读取 changed paths，取路径唯一并集，再只保留批准基线中的 blob；按字典序列举，独立重算结果必须为 102。

两个 set 必须无重复，并保存每项来源。过程消息出现过的 37/105 若无法从版本化证据重建精确中间集合，必须标记为
`non_versioned_interim_miscount_superseded_non_reconstructable`，明确不得编造 37→32 或 105→102 的映射；同时记录这些数字从未进入 v10r1 冻结 summary、manifest 或 gate。

## 4. Combined controlled-fork verification

v10r2 必须生成一次不可歧义的 combined log。单一日志按顺序包含：

1. wrapper 的真实 invocation 与 pytest 参数；
2. 只读 controlled parent/fork root；
3. 实际 fork HEAD、upstream、tracked-clean 状态；
4. 当前仓库 Gitlink；
5. 随后的真实 pytest 输出；
6. pytest exit code 与 wrapper exit code。

wrapper 必须在 preflight 不闭合时 fail closed；不得初始化或写入隔离 worktree 的 `external/simucell3d/`。最终 summary/parser 必须从 combined log 和 sidecar exitcode 解析 fork 身份、Gitlink、clean 状态、pytest passed/total 与 exit code；禁止硬编码 fork 哈希或测试计数。原始 combined log、exitcode、parser 输出与 SHA-256 必须进入 v10r2 manifest。

## 5. 科学语义与冻结完整性

v10r2 candidate 矩阵继续使用 v10r1 三态语义：candidate 1、2、4 为 `adjudicated_legal`；candidate 3 只能为 `not_adjudicated_due_to_production_sink_exception`，其 `topology_legal=null`/CSV 空值、`merge_succeeded=false`、异常文本及 `0.047434164902525666 > 1e-12` 原样保留。不得产生 `adjudicated_illegal` 或把 candidate 3 改成 legal。

必须独立证明：

- 以 `27b7fbfda1d8533a99dd7c80e91fce15ddfcdd6c` 为基线识别并列举全部 v01-v10r1 冻结路径，当前 Git blob、Gitlink 与相关工作树内容无差异；
- v09/v10 六提交的 canonical lifecycle blob set 仍为 102；
- v10 原 10 条 raw 与 18 条 verification manifest 项仍为 28/28 且 SHA-256/字节数匹配；
- Gitlink 仍为 `e2ed64a26bb5d7c2d878772564fb5ffcca343c3a`；
- focused、完整 Python、Ruff 最终通过；不运行 C++、microprobe 或 formal response。

最终 summary 只能使用不易误读的 packaging-repair 状态，并继续声明 v10 scientific status 失败、classification 未裁决、X1-K=false、R1=false、C1/F1 未执行、downstream=false。所有预期 RED、superseded 环境/调用错误与 required pass 必须在 verification summary/manifest 中分角色列出，不得混淆。

## 6. 三阶段提交、远端门禁与停止点

1. 本合同单独提交并正常推送；推送成功前不得生成 v10r2 响应。
2. 合同推送后生成代码、测试、combined log、v10r2 结果包和中文报告，作为结果提交并正常推送。
3. 远端确认等于结果提交后，只新增 `remote_sync.json`，形成第三个提交并正常推送。

每次远端动作前必须确认目标分支 tip 等于本阶段预期父提交。若不一致立即停止，不强推、不重写历史、不整合未经审查的变更。完成后 Executor 只报告 `execution complete / inspection eligible`、完整提交哈希、测试与远端状态；不自验收、不起草 v11、不修 fork、不进入 C1/F1。
