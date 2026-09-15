---
execution_id: EXEC-PRL-T0-FIGURE1-THEORY-V01
plan_id: PLAN-PRL-T0-FIGURE1-THEORY-V01
executor: Codex current task
started_at: 2026-08-11
completed_at: 2026-08-11
status: completed_with_deviation
deviation_records:
  - initial Matplotlib mathtext used unbraced mathbf syntax; render failed before producing an output and was corrected
inspection_status: pending_human_figure_gate
---

# T0 / Figure 1 v01 执行记录

## Approved plan reference

`project_control/t0_figure1_theory_contract_v01.md`

用户在审阅“下一步”定义后以“继续”批准启动 T0 / Figure 1 v01。本轮没有把该批准扩展到 T1、心肌细胞层、完整三层求解或 X1-K 修复。

## Commands or tools used

- 只读核对既有 M1 外载记录、项目时间尺度规则和 X1-K 冻结边界；
- 使用 `apply_patch` 新增理论、绘图和本记录；
- 执行 `python scripts/build_t0_figure1_theory_v01.py` 生成 PNG/SVG；
- 用固定随机种子执行界面离散功率、接触张量迹和一维端口代数检查；
- 使用 `python -m py_compile` 检查绘图脚本；
- 对 PNG 进行原始分辨率目视检查。

## Files changed

- `project_control/t0_figure1_theory_contract_v01.md`
- `docs/theory/t0_dcm_fem_dcm_energy_interface_v01.md`
- `scripts/build_t0_figure1_theory_v01.py`
- `figures/theory/t0_figure1_unified_framework_v01.png`
- `figures/theory/t0_figure1_unified_framework_v01.svg`
- `project_control/t0_figure1_execution_log_v01.md`

未修改现有求解器、测试、冻结结果、SimuCell3D fork、M1 记录或 X1-K 证据。

## Tests and checks run

### 1. 界面功率抵消

随机非匹配插值矩阵、求积权重、界面阻力和两侧速度下，检查

\[
\mathbf f_m^T\mathbf v_m+\mathbf f_J^T\mathbf v_J
=-\mathbf r_\Gamma^T\mathbf W_\Gamma
(\mathbf B_m\mathbf v_m-\mathbf B_J\mathbf v_J).
\]

绝对误差：`8.882e-16`。

### 2. 接触方向张量

检查 `tr(M_A)=phi_A`，绝对误差：`5.551e-17`。

### 3. 一维 ECM 端口

以 `E=5, A=2, H=4, eta=3` 检查 `K=EA/H=2.5`、`C=eta*A/H=1.5` 与集中端口反力完全一致，绝对误差：`0.000e+00`。

### 4. 绘图脚本和图形

- `py_compile`：通过；
- PNG：`393586` bytes；
- SVG：`175063` bytes；
- 目视检查：四个 panel 完整，无裁切、重叠或空白；公式、非数据警示和递进关系可读。

以上是执行者自检，不是独立科学检查。

## Deviations

首次渲染因 Matplotlib mathtext 的 `\\mathbf` 未加花括号而在写出图片前失败。修正为 `\\mathbf{g}`、`\\mathcal{D}` 和 `\\dot{\\Psi}` 后重新生成。该偏差没有产生或覆盖任何冻结科学结果，也没有改变理论内容。

## Blockers

- X1-K 仍未通过，组织级长轨迹和下游 ECM/血流长耦合仍未授权；
- Figure 1 尚未获得人类终审，因此不能作为已接受理论或论文机制证据；
- ECM 的 Kelvin–Voigt、标准线性固体或孔弹竞争模型尚未在 T1/T4 中裁决。

## Outputs produced

Figure 1 v01 形成四个审阅 panel：

1. 三层 DCM–FEM–DCM 对象；
2. 非匹配界面功率一致映射；
3. 三层总能量—功率账本；
4. 自由细胞到完整三层的必要退化关系。

下一生命周期状态：`user_review`。等待人类对 Figure 1 作出保留、修改、替换或停止决定。

