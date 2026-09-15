---
review_id: REVIEW-PAPER2-FIGURE2-FEM-ONLY-NUMERICAL-CREDIBILITY-V02-01
status: NUMERICAL_DESIGN_MINOR_REVISION_REQUIRED
reviewed_at: 2026-09-04
reviewer: independent_supervisor
reviewed_contract: project_control/paper2_figure2_fem_only_numerical_credibility_contract_v02.md
reviewed_contract_sha256: ebbf03fd06142021f658cbb834295cbed9e615890564e776c01234d8a1b3fe7c
baseline_commit: ade5f96d7b89a6ed6b629a37db795ed08853ba3f
baseline_upstream_ahead_behind: 0/0
execution_authorized: none
next_gate: executor_revision_then_independent_supervisor_review
---

# Paper 2 Figure 2 FEM-only 数值可信度合同 v02 Supervisor 独立审阅 v01

## 1. 结论

结论为 `NUMERICAL_DESIGN_MINOR_REVISION_REQUIRED`。v02 已实质关闭 v01 的三项主要
阻塞：开发集/独立留出分离、128×256 公共域，以及以 S4/T256 为统一参考的混合差；
N1–N11 也已写成冻结硬门。当前只剩两个相互关联、但会影响 fail-closed 可执行性的
正式阻塞，不能在执行合同中靠实现者自行解释。

本审阅不授权 solver、Docker、代码、测试、结果、制图、Git 提交或推送。

## 2. 已通过项

| 检查项 | 独立结果 | 状态 |
|---|---|---|
| 合同与源码锚点 | v01、v01 审阅、Figure 1 及八个核心源码 SHA-256 全部一致 | PASS |
| 开发/留出分区 | 开发集仅 `A2/LN/LS/C0/CQ`；`S1` 在 digest 后独立解盲 | PASS |
| 公共空间域 | 128 个 P0 段；原生分片线性场按交叠解析积分 | PASS |
| 公共时间域 | 256 个相位段；单频场和逐步功/耗散使用不同路径 | PASS_WITH_CLARIFICATION_REQUIRED |
| 联合混合差 | 四角差及边际误差均以 S4/T256 和同一 floor 归一 | PASS |
| 矩阵结构 | `Kmat` 两个共同平移零模；`Kmat+Ks` 与 `G` 严格 SPD | PASS |
| S1 热点与耗散份额 | 时刻、阈值、周期距离、`chi_D` 及低耗散边界均冻结 | PASS |
| 结果与资源 | 强制最小 NPZ、128 MiB、create-only、单 CPU/无网络/GPU | PASS |
| 文本完整性 | 736 行、无尾随空格、合同 SHA-256 与申报一致 | PASS |

## 3. 必须修订的两个阻塞

### B1. G4 的正式 PASS 依赖尚未完成的 G5，但主门禁顺序仍写 G4→G5

第 6 节冻结 `G3 -> G4 -> G5`；第 11 节又规定共同牵引场必须先经 G5 的 128×256
投影，且标量/波形部分与场部分都通过后才能写 `G4 PASS`。因此当前顺序无法按文字
逐门执行：G4 在 G5 前不能形成最终 PASS，G5 又被列为 G4 之后的门。

修订版必须显式拆分依赖并只保留一个无环顺序。建议冻结为：

```text
G0 -> G1 -> G2 -> G3
   -> G4a 标量/周期积分/无需跨空间网格对应的波形混合差
   -> G5 128×256 公共域投影、守恒与场收缩
   -> G4b 公共牵引场混合差
   -> G4 总裁决
   -> G6 -> G7 -> pre_holdout_digest -> S1
```

`gate_summary.json` 必须分别记录 `G4a`、`G4b` 和汇总 `G4`，任何子门失败时不得继续。
Figure 2 面板与 S1 适用门也须引用同一顺序，不能继续用含糊的 `G0→G7` 代替。

### B2. 单频场“重建到相位段”没有冻结段值的唯一数学定义

第 12.2 节未说明 256 个 P0 相位段保存的是段中心点值、左端点值还是段平均。该选择会
改变共同域 L2 范数、热点幅值与混合差，不能留给 runner 决定。

修订版必须规定：对 DC＋一阶谐波连续重建，在每个目标相位段上取**解析段平均**作为
P0 段值；不得用端点或中心点抽样。至少冻结：

\[
Q_j=\frac{1}{\Delta t_j}\int_{t_j}^{t_{j+1}}
\left[Q_0+\operatorname{Re}(\widehat Q_1 e^{i\omega t})\right]dt.
\]

相位段覆盖半开周期 `[0,T)`，周期端点不重复计权。公共域 L2、合力、热点和 G4b 均
使用这些 P0 段平均；逐步功/耗散仍按第 12.3 节的原生区间交叠守恒映射，二者不得混用。

## 4. 修订版验收门

下一版只有同时满足以下条件才可接受：

1. 明确无环的 `G4a -> G5 -> G4b -> G4` 顺序，并同步病例矩阵、S1、结果 schema、
   Figure 2 面板和最终 PASS 条件；
2. 256 个单频 P0 相位段冻结为解析段平均，明确积分区间、周期端点和禁止抽样；
3. v02 已通过的 S1 留出、128×256、fine-reference 混合差、N1–N11、资源和证据边界
   不得回退；
4. 新版本只改合同，不运行任何数值工作，不修改核心源码或旧合同。

## 5. 停止边界

Executor 只获准起草版本化 v03 并在完成后停止于 Supervisor Gate。v03 未被接受前，
不授权执行合同、代码、测试、solver、Docker、结果、制图、Figure 3、流体、整心房、
实验拟合、GPU、Git 暂存、提交或推送。
