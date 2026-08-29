# X1-K v11 RED/GREEN 证据索引

## RED

RED 使用受控 fork 的 stage-entry commit `e2ed64a26bb5d7c2d878772564fb5ffcca343c3a` 中的原始 `remesh_contract.hpp` 重放，而不是人为制造无关语法错误。

- 原始 stage-entry 头文件：`red_baseline_include/prl_cell_engine/remesh_contract.hpp`
- 编译探针：`red_transaction_capability_probe.cpp`
- 原始编译日志：`verification/tdd_red_transaction_capability.log`
- exitcode：`1`
- 预期且实际的失败原因：`RemeshEventSink` 没有 `prepare_remesh` public capability。

## GREEN

GREEN 使用当前 v11 源码和真实 cell/material remesh 路径：

- 原始 focused 日志：`verification/cpp_v11_focused_ctest.log`
- exitcode：`0`
- 结果：5/5，通过 transaction prepare/commit/reject、candidate 3 原子拒绝、survivor cycle、R1r、C1、F1/F1R。
- `transaction_audit.json` 记录 cell、material、transfer audit、energy defect、ledger、workset 六类拒绝前后状态指纹，全部相等。

上述证据只说明 v11 的公共能力从缺失到可验证实现，不重写 v09/v10 历史失败。
