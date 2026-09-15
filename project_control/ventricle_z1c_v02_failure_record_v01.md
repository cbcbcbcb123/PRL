---
document_id: PRL-VENTRICLE-Z1C-V02-FAILURE-RECORD-V01
status: preserved_failure
recorded_at: 2026-09-11
scientific_status: NOT_EVALUATED
---

# Z1-C v02 绘图实现失败记录

v02 修正了 v01 汇总键名并再次完成全部数值矩阵，但在导出第一张定量图时被 CB 统一风格验证器拒绝：固定 `10×5 in` 主坐标框的外部画布边距不足，纵轴标题和刻度未达到距画布边缘 12 pt 的要求。

该失败不构成数值 PASS 或 FAIL。`results/ventricle_z1/z1c_v02_20260911`、原始表、已生成空间图、`failure.json` 和 `runner_v02_failed.py` 均保留。v03 只扩大总画布边距，不缩小主坐标框，不改变方程、参数、阈值、数据或 MeshCell3D 内核，并从头重跑完整矩阵。

