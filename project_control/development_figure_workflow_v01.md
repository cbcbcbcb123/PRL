---
rule_id: RULE-PRL-DEVELOPMENT-FIGURE-WORKFLOW-V01
status: human_approved_active
accepted_at: 2026-08-09
approved_by: human_final_reviewer
scope: development-stage diagnostic and progress figures
supplements:
  - project_control/publication_and_timescale_strategy_v01.md
preserves:
  - all existing figure packages and frozen evidence
  - formal paper-figure evidence requirements
---

# 开发期轻量绘图规则 v01

## 1. 生效范围

本规则适用于当前 M1 及后续模型开发阶段的进展图、诊断图、细胞状态图和阶段审阅图。

1. 现有 M1 v02--v04 图包作为历史证据保留，不返工、不降级，也不因本规则重新验收；
2. 开发阶段优先走通科学主线，绘图服务于解释模型状态、发现错误和支持人类阶段决策；
3. 本规则不适用于已经由人类终审明确指定为“正式论文图”或“最终统一制图”的图件。

## 2. 开发期最低要求

开发期图件只需满足以下底线：

1. 使用真实保存的模型数据，不补画、伪造或选择性隐藏失败结果；
2. 能清楚说明细胞状态、力学量、时间演化、失败位置或比较结论；
3. 显式区分已接受、已拒绝、失败、未运行和未标定状态；
4. 保留数据来源和最小复算入口，例如脚本、Notebook 或明确的运行命令；
5. 完成基本视觉检查，避免裁切、遮挡、错误标签和不可辨认的坐标；
6. 默认输出可读 PNG 即可；只有确有分析价值时才额外输出 SVG、动画或高分辨率版本。

## 3. 当前暂不要求

在项目整体完成或人类终审另行批准前，开发期图件：

1. 不调用 `cb-plot-unified-style` 技能；
2. 不强制统一画布尺寸、字体、线宽、配色模板和 panel 比例；
3. 不强制 600 dpi、SVG、完整 manifest 或正式论文图版本包；
4. 不因纯版式或美观问题阻塞模型开发和科学门禁；
5. 可根据每次诊断问题自行选择最清楚、最快速的排版。

## 4. 正式统一制图触发条件

满足下列任一条件时，再进入严格统一制图：

1. 项目整体科学主线已经走通，人类终审批准开始最终制图；
2. 人类终审明确指定某张图为正式论文图；
3. 某项结论需要按论文级证据链进行冻结和对外展示。

触发后应新建正式图版本，不得把开发期诊断图静默改名为论文图；届时再使用
`cb-plot-unified-style` 及相应可复现论文图流程。

## 5. 科学边界

绘图要求放宽只代表视觉规范和交付包装暂时简化，不代表数值、力学或证据标准降低。
守恒、稳定性、收敛性、失败原因和 claim 边界仍按既有门禁执行。
