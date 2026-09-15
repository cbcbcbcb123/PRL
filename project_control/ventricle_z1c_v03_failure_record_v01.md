---
document_id: PRL-VENTRICLE-Z1C-V03-FAILURE-RECORD-V01
status: preserved_failure
recorded_at: 2026-09-11
scientific_status: NOT_EVALUATED
---

# Z1-C v03 绘图边界失败记录

v03 扩大了定量图外画布，但统一样式验证仍发现纵轴标题距左边界为负 12.1 pt、一个刻度仅 2.7 pt，未达到冻结的 12 pt 清晰距离。主 `10×5 in` 坐标框保持不变，数值矩阵已完成但未作科学裁决。

失败包及 `runner_v03_failed.py` 保留。v04 只进一步增加显式左右/下/上边距并从头重跑；方程、几何、参数、阈值、原始字段和 MeshCell3D 内核均不变。

