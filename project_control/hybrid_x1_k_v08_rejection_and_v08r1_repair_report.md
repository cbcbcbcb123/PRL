---
report_id: REPORT-PRL-HYBRID-X1-K-V08R1-ADJUDICATOR-REPAIR
status: passed_revised_fixed_topology_d1_s1_acceptance_after_adjudicator_repair
contract: CONTRACT-PRL-HYBRID-X1-K-V08R1-ADJUDICATOR-REPAIR
contract_commit: a500893e86c2d5415a48a8458a8a0c2f7eb721ce
rejected_v08_status: failed_adjudicator_contract_incomplete
fork_commit: e2ed64a26bb5d7c2d878772564fb5ffcca343c3a
x1_k_passed: false
r1_c1_f1: not_executed
downstream_authorized: false
---

# X1-K v08 拒绝与 v08r1 adjudicator 修复报告

## 结论

接受导师对 v08 的拒绝：v08 冻结为 `failed_adjudicator_contract_incomplete`。旧 v08 的三个
提交和结果目录未被覆盖。此次返工没有发现新的原始科学数据失败；修复后的唯一允许状态为
`passed_revised_fixed_topology_d1_s1_acceptance_after_adjudicator_repair`。

该状态只表示 v05–v07 固定拓扑原始证据在修复后的 fail-closed 程序中通过 revised D1/S1
裁决。`x1_k_passed=false`，R1/C1/F1 未执行，下游未授权。

## 1. 阻断项修复

### 1.1 Source Git object

23/23 required CSV 现在逐一验证：来源 commit 存在、`commit:path` 是 blob、Git blob 原始
字节与当前 required file 相同、`source_blob_id=current_blob_id`。provenance manifest 对每项
保存 `source_blob_id`、`current_blob_id` 与 `source_blob_verified`。替换 commit 或 source
path 的测试分别以 `source_commit_missing`、`source_blob_mismatch` fail closed。

### 1.2 v05 语义闭合

每层分别重算：

```text
E_total = E_v5 + E_v6
fraction_i = E_i / E_total
e_normal = sqrt(E_total / (A_v5 + A_v6)) / abs(v_exact)
p_E = log(E_coarse/E_fine) / log(h_coarse/h_fine)
```

fraction 逐区核对；global normal L2 与 `family_c_levels.csv` 交叉核对；total、valence-5、
valence-6、closed-one-ring 四列三对相邻层 order 均按实际 `h` 复算。三个篡改测试都在临时
Git 仓同步更新修改文件的 hash 与 source commit，因此失败来自语义复算，不是 SHA 检查。

### 1.3 Limitation 逻辑

valence-5 四层 pointwise maximum 必须存在并原样报告，pointwise/uniform claim 永久为
false；但 limitation 不再进入 revised D1 acceptance 聚合。测试把 pointwise 序列改为改善
后，D1 仍由 global-L2 门禁决定，不会出现“改善反而失败”的逻辑倒置。冻结 raw data 本身
仍保留点态不收敛风险，不得升级为 uniform/pointwise convergence。

### 1.4 真实机器验证

v08 脚本中的硬编码验证计数不再用于 v08r1。新 parser 必须读取五个 `.log` 和五个
`.exitcode`，从原始文本解析 CTest/pytest 计数、严格的 parent 历史失败集合与完成标记，并
保存各日志 SHA-256。缺任一文件或不一致均 fail closed。

## 2. 修复后裁决

- 23/23 当前 CSV 的 SHA-256、rows、schema、finite 与 key closure：通过；
- 23/23 source/current Git blob：相同；
- v05 fraction/global-L2/error-order semantic reconstruction：通过；
- revised D1 Family C area-weighted global L2：通过；
- revised S1 structure/time 与 area/volume/energy/controls：通过；
- v06/v07 energy ledger：逐行复算通过，coverage 仍仅为 `surface_tension_only`；
- v08 rejection、Route H、v02、v04、v06 历史失败：保留。

## 3. TDD 与完整验证

v08r1 共保存八个 RED/GREEN 行为切片。focused v08/v08r1 测试为 12/12。完整机器证据由
日志 parser 得到：

- parent CTest：52/55，仅 v02 D1、v04 Family B、v06 trajectory 三项历史失败；
- controlled fork：134/134；
- strict `prl_core`：通过；
- Python：75/75；
- tracked + v08r1 Ruff：通过。

以上数字均来自版本化日志解析，不由 summary 常量生成。

## 4. 科学边界

此次修复只证明裁决软件满足 v08r1 合同。它没有生成新轨迹、没有修改 C++ 或 fork、没有
证明长期稳定、生理有效、完整 cell–ECM/FSI、EFE 机械记忆、参数可识别性或心脏发育机制。
R1/C1/F1 继续禁止，等待新的导师合同。
