---
diagnosis_id: DIAG-PAPER2-FIGURE2-S1-HOTSPOT-MASK-V01
status: diagnosed_read_only_pending_repair_authorization
diagnosed_at: 2026-09-04
diagnoser_role: project_controller
source_execution_record: project_control/paper2_myocardial_dcm_physical_removal_execution_record_v01.md
source_execution_record_sha256: ff7da8c60fbc2f0868276371ca1ac63ac14c03a6dbc39fa7e7420c514f412d22
observed_test_result: 34_passed__1_failed
observed_failure: S1_hotspot_mask_changed
repair_authorized: false
tests_rerun: false
solver_or_docker_run: false
git_write_performed: false
next_gate: narrow_fixture_repair_decision
---

# Paper 2 Figure 2：`S1 hotspot mask changed` 只读诊断 v01

## 1. 结论

当前唯一失败最符合**测试夹具构造不完整**，而不是 FEM 求解失败、S1 物理规则冲突或本次
心肌 DCM 物理清理回归。

测试夹具 `tests/paper2_figure2/test_evidence_v01.py::_arrays()` 先按 schema 把所有数组初始化为
零；其中布尔 `s1_hotspot_mask` 因而是全 `False`。夹具随后填写端点、共同空间/相位轴和步数，
但在返回前没有从 S1 traction 重算 hotspot field 与 mask。

正式验证器 `src/paper2_figure2/evidence.py::validate_npz_arrays()` 冻结的规则为：

```text
hotspot = s1_hotspot_traction_e_to_m_x
threshold = row_min(hotspot) + 0.05 * row_range(hotspot)
expected_mask = hotspot <= threshold
```

夹具中的 traction 与 hotspot field 都为零，因此每一行 `min=0`、`range=0`、`threshold=0`，
正式规则必然得到全 `True` 的 `(4,128)` mask；夹具实际保留全 `False`，所以 512 个布尔位置
全部相反，并确定性触发 `S1 hotspot mask changed`。

## 2. 直接证据

| 文件 | 当前 SHA-256 | 只读事实 |
|---|---|---|
| `tests/paper2_figure2/test_evidence_v01.py` | `5c1760db59cb1cac527b264f5ab09a32227e1fa069f71d4e46f289c2fc8657d5` | 第 28--47 行的 `_arrays()` 将 bool schema 初始化为零后未派生 S1 mask |
| `src/paper2_figure2/evidence.py` | `df4c5a68394e7edba21789772d5560319ec324a0e877bf4da675ad76785cbf56` | 第 299--308 行先核对物理 traction，再按 `min+0.05*ptp` 生成 expected mask |
| `src/paper2_figure2/observables.py` | `29216f930b3be9cd5af65e912e9a637e2042960ab83fcc5d6f2115f395a5ea85` | 第 853--863 行的生产压缩路径使用与验证器相同的阈值和 `<=` 规则 |

生产提取与证据验证的公式、方向和包含等号规则彼此一致。当前静态证据没有显示应修改
`observables.py` 或 `evidence.py`。

## 3. 与物理清理的因果边界

1. 失败文件属于当前 `paper2_figure2`，不导入已经删除的 `paper2_m2`、`hybrid` 或
   `route_h` 命名空间；
2. 失败由零值测试夹具自身即可推出，不依赖 FEniCSx、网格、材料参数、Docker 或已删除结果；
3. 因而该失败应单列为既有 Figure 2 证据夹具问题，不应把 `34 passed, 1 failed` 误写为
   心肌 DCM 清理回归；
4. 反过来，在修复并实际运行前，也不能把本诊断表述为“测试已通过”或“生产 S1 已验证”。

## 4. 最小候选修复（未授权）

未来若人类批准，只修改：

```text
tests/paper2_figure2/test_evidence_v01.py
```

在 `_arrays()` 返回前，以夹具自身的 `s1_traction_on_ecm_p0` 按生产公式派生
`s1_hotspot_traction_e_to_m_x`、threshold 和 `s1_hotspot_mask`。不得把 mask 硬编码为全
`True`，因为夹具未来一旦改成非零场，硬编码会再次脱离正式规则；不得放宽验证器、改 `<=`、
改变 `0.05`、跳过 mask 检查或修改科学合同。

该一文件修订会改变已接受 15 文件候选的 SHA，因此必须：

1. 形成新的窄修订授权；
2. 先运行该失败用例，再运行不依赖 basix 的完整 Figure 2 静态/证据集；
3. 重新冻结 15 文件候选并做独立实现静态复核；
4. 在此之前不得使用旧 v07.2 接受记录授权 PRECHECK 或 staging。

## 5. 本轮证据边界

本诊断只读取现有源码、测试与执行记录；未修改任何实现或测试，未运行 Python、pytest、
FEniCSx、solver、Docker 或 GPU，未创建结果或实现锁，未暂存、提交或推送。
