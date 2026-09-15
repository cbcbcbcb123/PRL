---
execution_id: EXEC-PRL-T1-FIGURE2-CONTACT-TOPOLOGY-V01
plan_id: PLAN-PRL-T1-FIGURE2-CONTACT-TOPOLOGY-V01
executor: Codex current task
started_at: 2026-08-11
completed_at: 2026-08-11
status: completed_with_deviation
deviation_records:
  - initial Matplotlib fraction syntax was unsupported and failed before output; corrected to explicit braced fractions
  - first rendered comparison layout was crowded; panel A was redesigned as a side-by-side matched comparison
inspection_status: pending_human_figure_gate
---

# T1 / Figure 2 v01 执行记录

## Approved plan reference

`project_control/t1_figure2_contact_topology_contract_v01.md`

Figure 1 被用户暂定保留后，用户批准继续。执行范围仅为解析接触拓扑模型和 Figure 2 审阅图；没有启动显式 DCM–FEM、重网格或长轨迹计算。

## Files changed

- `project_control/t0_figure1_provisional_decision_v01.md`
- `project_control/t1_figure2_contact_topology_contract_v01.md`
- `docs/theory/t1_contact_topology_reduced_model_v01.md`
- `scripts/build_t1_figure2_contact_topology_v01.py`
- `figures/theory/t1_figure2_contact_topology_v01.png`
- `figures/theory/t1_figure2_contact_topology_v01.svg`
- `project_control/t1_figure2_execution_log_v01.md`

## Scientific result

在总界面刚度匹配时，单侧接触保留伸长—弯曲交叉项，对称包埋因反射对称性消去该项。闭式解为

\[
\frac{\varepsilon}{\varepsilon_a}
=\frac{\beta+\Lambda}
{(1+\Lambda)(\beta+\Lambda)-\Lambda^2m^2},
\]

\[
\frac{\widehat\kappa}{\varepsilon_a}
=-\frac{\Lambda m}
{(1+\Lambda)(\beta+\Lambda)-\Lambda^2m^2}.
\]

这产生一个对 Figure 1 的修订候选：面积分数 \(\phi_A\) 和无符号二阶方向矩 \(\mathbf M_A\) 无法单独区分相反两侧接触，需要增加刚度加权的有符号极性 \(\mathbf p_K\)。该修改尚未写回 Figure 1 v01。

## Tests and checks run

- 1000 组随机正参数中，闭式解与直接 2×2 线性求解最大绝对误差：`3.747e-16`；
- 1000 组随机正参数中，Hessian 最小特征值下界：`2.277e-03 > 0`；
- `m=0` 曲率：`0.000e+00`；
- `m -> -m` 时缩短不变误差：`0.000e+00`；
- `m -> -m` 时曲率反号误差：`0.000e+00`；
- 单侧与对称两侧的第一法向矩差：`1.000e+00`；
- 两者第二法向矩差：`0.000e+00`，直接证明二阶矩可能丢失接触极性；
- `py_compile`：通过；
- PNG/SVG 最终目视检查：四个 panel 完整、无裁切，图中明确标注解析约化模型而非 DCM–FEM 模拟。

以上仍是执行者自检，不是独立科学检查。

## Deviations

首次图片渲染因 Matplotlib 不支持未加花括号的 `frac` 写法而失败，未生成输出。修复后第一次成图的 panel A 上下比较过密，随后改为左右并列且保持总刚度匹配。热图在 SVG 中改为嵌入式栅格，公式、曲线和文字仍为矢量，从而将 SVG 体积由约 9.9 MB 降至约 0.30 MB。

## Blockers and boundaries

- Figure 2 尚未获得人类终审；
- 解析梁模型不能替代三维 DCM–FEM 成对算例；
- X1-K 仍未通过，因此不执行可重网格长轨迹或下游长耦合；
- 黏性、相位和 ECM 三维应力不在本解析图中。

## Next lifecycle state

`user_review`。等待人类对以下三点作出决定：

1. 是否保留“接触极性导致伸长—弯曲耦合”的 Figure 2 主张；
2. 是否同意把 \(\mathbf p_K\) 加入未来 Figure 1 v02；
3. 是否批准起草固定拓扑、短时、单细胞—显式 ECM 的配对 benchmark 合同。

