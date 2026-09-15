---
document_id: PRL-VENTRICLE-Z1C-V01-FAILURE-RECORD-V01
status: preserved_failure
recorded_at: 2026-09-11
scientific_status: NOT_EVALUATED
---

# Z1-C v01 汇总实现失败记录

v01 已完成接触矩阵和原始 CSV 写入，但在汇总阶段读取不存在的 `medium_fine_peak_reaction_change` 字段而触发 `KeyError`；实际冻结表列名为 `medium_fine_relative_change`。因此 v01 为 `FAIL_IMPLEMENTATION`，不能据此裁决 Z1-C 科学状态。

失败包 `results/ventricle_z1/z1c_v01_20260911`、其中的原始表、`failure.json` 和 `runner_v01_failed.py` 全部保留。v02 只修正两个汇总键名并从头重跑全部矩阵，不读取或复用 v01 数值结果，不改变方程、参数、阈值、图形字段或 MeshCell3D 内核。

