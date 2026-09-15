---
execution_id: EXEC-PRL-ROUTE-H-STAGE2-GATE-A-OBSERVABILITY-V02
plan_id: CONTRACT-PRL-ROUTE-H-STAGE2-GATE-A-OBSERVABILITY-V02
executor: Codex current task
started_at: 2026-08-04T14:25:00+08:00
completed_at: 2026-08-04T14:51:41+08:00
status: completed
deviation_records: []
---

# Route H Stage 2 Gate A M1 v02 可观测性诊断执行记录

## Approved plan reference

用户已批准 M1 v02 可观测性诊断及科研审阅图。执行边界见
`project_control/route_h_stage2_gate_a_v02_observability_contract.md`。冻结 Gate A v01、力学方程、
参数、时间步、L-BFGS-B 选项和验收阈值均未修改。

## Commands or tools used

- 用当前公共轨迹入口在内存中重现 `A1_ACTIVE, dt=0.02`；
- 采用 RED–GREEN 回归，先证明可观测模块不存在，再实现结构化失败返回；
- 执行 `scripts/run_route_h_stage2_gate_a_v02_observability.py` 物化新证据包；
- 使用论文图版本包 Notebook 生成 PNG/SVG；
- 使用 CB 统一风格校验器和单独目视检查验收残差图；
- 使用 pytest、Ruff、JSON/Notebook 校验和 SHA-256 复核完成收尾。

## Files changed

新增：

- `src/route_h/stage2_gate_a_v02_observability.py`；
- `tests/stage2/test_gate_a_v02_observability.py`；
- `scripts/run_route_h_stage2_gate_a_v02_observability.py`；
- `project_control/route_h_stage2_gate_a_v02_observability_contract.md`；
- `results/route_h/stage2_gate_a_v02_observability/` 下的数值证据和两个 Figure 版本包；
- 本执行记录及只读自检记录。

用户原有未跟踪的 `figures/`、`scripts/build_efe_nature_figure_plan_docx.py` 和
`scripts/insert_efe_figure_mockups_docx.py` 未修改。

## Tests or checks run

- 原 Gate A 制造解与新真实失败路径回归：`6 passed`；
- 新增/相关 Python 和两个绘图 helper：Ruff 全部通过；
- Gate A v01 freeze manifest：`29/29` 文件 SHA-256 匹配；
- 状态图 Figure 版本包：Notebook 执行、自动校验、目视验收通过；
- 残差图 Figure 版本包：Notebook 执行、自动校验、CB 统一风格 manifest、目视验收通过；
- PNG 为 600 dpi，SVG 保留可编辑文字。

## Diagnostic outcome

- 首个无效节点：step `79`，`t=1.58`，`alpha=0.06243449435824275`；
- 最后有效节点：step `78`，`t=1.56`；轴向缩短 `5.4288836%`，两个横向尺度变化
  `+2.7999972%`、`+2.0306619%`，体积误差 `-0.0097906%`；
- rejected candidate residual：`1.488435357e-8 > 1e-8`；gauge residual
  `4.634496559e-20`；
- rejected candidate 几何仍有限、正体积、`0` 翻面、`0` 退化面，最小面面积比
  `0.836616`，最小方向余弦 `0.997087`；
- 失败步共有 `147` 次目标/梯度评估和 `66` 个 callback accepted iterates；accepted
  iterates 的最小 residual 为 `1.238135340e-8`，未通过门槛；
- evaluation `74` 和 `115` 的 trial residual 分别为 `8.840121477e-9` 和
  `7.948783821e-9`，已低于门槛，但均未成为 accepted iterate；
- trial 与返回候选的增量势差仅约 `1e-17` 量级，之后目标函数/残差在机器精度附近振荡并以
  `ABNORMAL` 退出。

上述证据把失效定位到目标函数平台区的 L-BFGS-B line-search acceptance 与只在 callback
检查物理门槛之间的失配；没有发现细胞几何崩坏。该结论是数值诊断，不等于 Gate A 通过。

## Deviations

无范围偏离。执行中发现严格 JSON 不接受 `numpy.bool_`，已将输出边界显式转换为 Python
`bool` 并补入回归；首次残差图自动/目视检查分别发现对数次刻度和文字遮挡，均只调整绘图
布局与标签，未改变任何数据。

## Blockers

M1 v02 本身无技术 blocker。Gate A 仍维持 `failed_invalid_numerics`。进入数值方法修订前，
需要人工终审接受本诊断，并另行批准 M1 v03。

## Outputs produced

- 状态图：`Figures/FigM1_cell_state_observability/.../04_*.png` 与 `05_*.svg`；
- 残差图：`Figures/FigM1_solver_residual_observability/.../04_*.png` 与 `05_*.svg`；
- 数值摘要：`summary.json`、`failure_snapshot.json`；
- 可复算数据：`accepted_time_series.csv`、`accepted_vertices.npy`、
  `rejected_candidate_vertices.npy`、`failure_optimizer_trace.csv`、`reference_faces.npy`；
- 完整性清单：`manifest.json`。
