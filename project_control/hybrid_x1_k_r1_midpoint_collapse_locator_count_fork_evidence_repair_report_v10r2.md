# X1-K v10r2 定位器、计数与 controlled-fork 证据修补报告

本 successor 是 append-only 的 packaging/evidence repair，不是新的科学响应，也不追溯声称 v10 当时已交付 configuration。v01-v10r1 冻结路径、v10 的 28 项 manifest 与 Gitlink 均通过只读完整性检查。

## 修补结果

- 32 个 canonical configuration leaf 全部从 `source_commit:path` 的冻结 Git blob 按结构化 line range 或 record/key locator 解析通过；篡改 locator 且保持 JSON echo 自洽的 RED 会 fail closed。
- canonical configuration count 为 32；六个 v09/v10 生命周期提交的 frozen blob 唯一集为 102。过程消息 37/105 是未版本化、已取代且不可重建的临时误计，未进入冻结 summary、manifest 或 gate。
- combined log 解析到 controlled fork `e2ed64a26bb5d7c2d878772564fb5ffcca343c3a`，HEAD/upstream/Gitlink 一致、tracked clean；同一日志中的 pytest 为 91/91、exit 0。
- candidate 1/2/4 保持 `adjudicated_legal`；candidate 3 保持 `not_adjudicated_due_to_production_sink_exception`，`merge_succeeded=false`，异常距离 `0.047434164902525666 > 1e-12`。

## 验证证据角色

- expected TDD RED：`tdd_red_locator_seam_missing`、`tdd_red_locator_json_echo`、`tdd_red_count_reconciliation`、`tdd_red_combined_log_parser`。这些失败只证明测试先于实现，不能作为最终通过。
- superseded/intermediate errors：`tdd_green_locator_resolution` 是错误测试节点调用（exit 4）；`tdd_green_locator_resolution_valid` 揭示 production path canonical 归一化差异（exit 1）。二者均不计作通过，后续有效 GREEN 另有独立日志。
- required final pass：`combined_python_final`、`focused_python_final`、`ruff_final`；其 exit code 均为 0。详细角色及实际 pytest 计数见 `verification_summary.json`，角色不得互换。

## 科学状态保护

v10 scientific status 仍失败；classification 仍未裁决；X1-K=false；R1=false；C1/F1 未执行；downstream=false。未运行 C++、microprobe 或 formal R1 response，未生成新物理数据。

本报告只声明 execution complete / inspection eligible，不作自验收。
