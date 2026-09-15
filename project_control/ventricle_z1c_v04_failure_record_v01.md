---
document_id: PRL-VENTRICLE-Z1C-V04-FAILURE-RECORD-V01
status: preserved_failure
recorded_at: 2026-09-11
scientific_status: NOT_EVALUATED
---

# Z1-C v04 对数轴次刻度失败记录

v04 的接触响应定量图已经通过统一样式导出，但对数尺度验收概览没有可见 y 次刻度，触发样式失败。数值矩阵已完成但 summary 未生成，因此不作科学裁决。

失败包及 `runner_v04_failed.py` 保留。v05 只在验收概览图中显式设置 `show_minor_ticks=False`，并以 `StyleOverride` 记录对数门限图只显示主十倍刻度的理由；其他图形、数据、方程、参数、阈值和内核不变。

