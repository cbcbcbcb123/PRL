---
contract_id: CONTRACT-PRL-HYBRID-X1-K-V10R1-EVIDENCE-PACKAGING-SEMANTIC-REPAIR
status: frozen_before_v10r1_packaging_response
frozen_at: 2026-08-03
approved_parent_commit: ddd663d461da7b25aefd5cf3fbecff488800053e
v10_contract_commit: e54bc5933387070c697f5c88218f37f25faea4c3
v10_result_commit: 2919a5df50d9fa287fe823ee5a1bb9169c438f65
cell_engine_gitlink: e2ed64a26bb5d7c2d878772564fb5ffcca343c3a
scientific_status: failed_v10_midpoint_collapse_diagnosis_eligible_candidate_material_rebind
classification_status: not_adjudicated_due_to_first_failure
x1_k_passed: false
r1_passed: false
c1_f1: not_executed
downstream_authorized: false
---

# X1-K v10r1 证据包装与语义修补冻结合同

## 1. 授权目标与非目标

本合同只授权创建 append-only 的 v10r1 证据包装与语义修补包，用来：

1. 补齐 v10 合同要求但冻结 v10 结果包未交付的 `configuration.json`；
2. 把候选 3 在 production material-transfer sink 抛出异常后的 topology 状态，从旧 exporter 的错误二值映射修补为“未裁决”；
3. 以新的 manifest、criteria、summary、复算命令和中文报告说明来源、边界与冻结科学状态。

本任务不是新的 microprobe、formal R1 response 或物理数据生成任务；不修改 C++ 科学路径，不修改 controlled fork，不修复 fork，不重跑或改判 v09/v10，不进入 C1/F1，也不授权下游工作。

## 2. Append-only 写入边界

允许新增：

- `project_control/hybrid_x1_k_r1_midpoint_collapse_evidence_packaging_semantic_repair_contract_v10r1.md`；
- `project_control/hybrid_x1_k_r1_midpoint_collapse_evidence_packaging_semantic_repair_report_v10r1.md`；
- `results/hybrid/x1_k_r1_midpoint_collapse_diagnosis_v10r1/` 下的新证据包装文件；
- 独立的 v10r1 Python exporter/parser 与对应行为测试。

禁止改动：

- `results/hybrid/x1_k_r1_midpoint_collapse_diagnosis_v10/` 的任何字节；
- v10/v09 的合同、报告、结果、日志、阈值与裁决；
- Route H、`external/simucell3d/`、submodule pointer、`figures/`；
- `scripts/build_efe_nature_figure_plan_docx.py` 与 `scripts/insert_efe_figure_mockups_docx.py`；
- 任何 C++ 科学路径。

## 3. 冻结输入与配置重建规则

唯一允许的科学输入是已冻结的 v10 合同、v10 runner/source defaults 与原始响应：

- `e54bc5933387070c697f5c88218f37f25faea4c3:project_control/hybrid_x1_k_r1_midpoint_collapse_diagnostic_contract_v10.md`；
- `2919a5df50d9fa287fe823ee5a1bb9169c438f65:cpp/tests/r1_midpoint_collapse_diagnostic_test.cpp`；
- `2919a5df50d9fa287fe823ee5a1bb9169c438f65:results/hybrid/x1_k_r1_midpoint_collapse_diagnosis_v10/raw/formal_response.log`；
- `2919a5df50d9fa287fe823ee5a1bb9169c438f65:results/hybrid/x1_k_r1_midpoint_collapse_diagnosis_v10/raw/formal_response.exitcode`；
- 冻结 v10 的两个 manifest、candidate matrix、criteria、summary 与 failure report 仅作为包装完整性和旧语义对照。

`configuration.json` 必须显式声明它是在 v10 冻结后为 v10r1 包装修补而重建，不能声称 v10 当时已交付配置。每个配置字段必须保存：字段路径、值、来源 commit、来源 path、精确 line range 或 record/key locator，以及来源中的值。字段与 provenance 必须一一闭合；值冲突或来源缺失时 fail closed。

至少重建并溯源：冻结容差、初始 cell/revision/mesh、被动参数、两个 material point、active-contraction unit、production sink 最大重绑定距离、public refiner 参数、真实 split/eligibility/merge/event/snapshot 路径、禁用的动力学/耦合项、候选枚举顺序、输出精度和 formal-response 退出语义。

## 4. Topology 三态语义

新矩阵的规范字段为 `topology_status`：

- candidate 1、2、4：`adjudicated_legal`；
- candidate 3：`not_adjudicated_due_to_production_sink_exception`；
- 仅当完整 post-merge topology 检查实际完成且失败时，未来新合同才可使用 `adjudicated_illegal`；本包没有该状态的候选。

候选 3 必须继续保存 `can_be_merged=true`、`merge_succeeded=false`、原异常文本与精确数值 `0.047434164902525666 > 1e-12`。其 `topology_legal` 若出现在 JSON 中只能为 `null`，CSV 中只能留空；不能改成 `true`，也不能把旧 exporter 的 `false` 当作通用拓扑非法裁决。候选 3 的 `geometric_inverse=false` 仍按冻结 raw 保存，但不等价于 topology 已裁决。

`semantic_erratum.json` 或 Markdown 必须解释：冻结 raw 和 v10 文件保持字节不变；旧 runner/exporter 在异常分支未执行 post-merge topology audit，却把默认布尔值序列化为 `false`；v10r1 只修补包装语义，不产生新的科学裁决。

## 5. 交付物与允许状态

新目录至少包含：

- `configuration.json`；
- `candidate_matrix_v10r1.csv` 与 `candidate_matrix_v10r1.json`；
- `semantic_erratum.json`；
- `criteria.csv`；
- `summary.json`；
- `provenance_manifest.json`；
- `reproduction_commands.md`；
- TDD RED/GREEN 和最终 focused/full Python、Ruff 的真实日志与 exitcode；
- 远端同步证明（第三阶段新增）。

另交付新的中文 v10r1 修补报告。`summary.json` 的包装状态只能使用
`packaging_repair_complete_scientific_failure_preserved`；并必须继续声明：v10 scientific status 失败、classification 未裁决、`x1_k_passed=false`、`r1_passed=false`、`c1_f1=not_executed`、`downstream_authorized=false`、未运行新 microprobe/formal response、未生成新物理数据。

## 6. TDD 与完整性门禁

先通过公开 Python seam 建立会因“缺失配置产物”和“候选 3 被二值化为 false”而失败的 RED，再实现最小独立 v10r1 exporter/parser。不得为了测试修改 v10 parser/exporter 或 C++ 路径。

最终必须机器验证：

1. `ddd663d461da7b25aefd5cf3fbecff488800053e` 中全部 v10 目录、v10/v09 冻结 artifact 的 Git blob 身份与当前内容一致；
2. v10 raw manifest 的 10 项与 verification manifest 的 18 项仍存在，SHA-256 与字节数逐项匹配；
3. `configuration.json` 每个配置字段 provenance 闭合；
4. candidate 3 的 `topology_status` 只能是 `not_adjudicated_due_to_production_sink_exception`，`merge_succeeded` 仍为 false；
5. `0.047434164902525666 > 1e-12` 原样保留；
6. focused tests、完整 Python tests 与 Ruff 全部通过；
7. 无需也不得重跑 C++ 科学响应，只读取并核验冻结日志。

## 7. 三阶段提交与停止点

1. 本合同单独提交并正常推送；推送成功前不得生成 v10r1 响应。
2. 合同推送后，生成代码、测试、结果包和中文报告，完成门禁后作为结果提交并正常推送。
3. 确认远端仍等于结果提交后，只新增远端同步证明，形成第三个提交并正常推送。

每次远端动作前都必须用 `ls-remote` 检查目标分支。若远端不等于本阶段预期父提交，立即停止，不做强制推送、历史重写或未经审查的整合。完成后状态只能报告为 `execution complete / inspection eligible`；Executor 不作验收，不起草 v11，不修 fork，不进入 C1/F1。
