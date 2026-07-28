---
execution_id: EXEC-PRL-ROUTE-H-STAGE0-V01
plan_id: PLAN-PRL-ROUTE-H-DCM-ECM-STAGE0-STAGE2-V01
executor: Codex current task, single-worker governed science-minimum execution
started_at: 2026-07-28T16:04:19+08:00
completed_at: 2026-07-28T16:12:53+08:00
status: blocked
deviation_records:
  - DEV-PATH-001
  - DEV-HISTORICAL-ISOLATION-001
  - DEV-ACTIVE-SIGN-001
  - DEV-ACTIVE-MOMENT-001
---

# Route H Stage 0 执行记录 v01

## Approved plan reference

- 计划：`project_control/route_h_stage0_stage2_governed_plan_v01.md`
- 用户授权：2026-07-28 对话“好的，开始！”
- 本次授权解释：只执行 Stage 0；不实现 Stage 1 求解器，不运行 Stage 2，不生成科学结果。

## Commands or tools used

- 只读检索计划和本地 SimuCell3D 参考文献；
- 创建新的最简 Stage 0 目录；
- 写入 JSON、CSV 和 Markdown 合同；
- 用 PowerShell 解析 JSON/CSV、复算输入哈希和检查交叉引用；
- 用两个数值 manufactured examples 检查主动功率符号与锚点净力矩。

未访问网络，未运行 solver、notebook、数值轨迹或绘图。

## Files changed

- `src/route_h/route_h_contract_v01.json`
- `src/route_h/route_h_model_specialization_v01.json`
- `data/route_h/route_h_cases_v01.json`
- `docs/route_h/route_h_coordinate_and_sign_convention_v01.md`
- `docs/route_h/route_h_port_and_power_ledger_v01.csv`
- `tests/route_h/route_h_verification_registry_v01.csv`
- `project_control/route_h_stage0_scientific_decision_v01.md`
- `project_control/route_h_stage0_execution_log_v01.md`

## Tests or checks run

### 结构检查

- JSON 解析：通过；
- CSV 解析：通过；
- 15 个 case ID：无重复；
- Gate A–E 对 required/sensitivity case 的引用：全部存在；
- verification registry 对 case 的引用：全部存在；
- 直接输入 SHA-256：3/3 匹配；
- ledger：23 行；
- verification registry：38 行；
- `results/`、`figures/`、`notebooks/`：保持为空；
- Stage 1、Stage 2 和 case execution：均保持未授权。

### 科学 manufactured checks

1. 取 \(k_f=10\)、\(L_f=1\)、\(L_f^\star=0.9\)、
   \(\dot L_f^\star=-0.1\)：
   - \(\partial\Psi/\partial L_f^\star=-1\)；
   - 建议的右端输入功率为 \(+0.1\)；
   - 计划原带负号表达式为 \(-0.1\)。

2. 取锚点差向量 \(d=(1,0.2,0)\)：
   - 固定轴 \(f=(1,0,0)\) 的力对产生 \(M_z=0.2\)；
   - 沿 \(d/\|d\|\) 的中心力对净力矩为
     \(2.78\times10^{-17}\)，即浮点容差内为零。

3. 心肌参考椭球：
   - 轴长 \(1.0\times0.6\times0.6\) 的体积为
     \(0.18849556\)；
   - 登记目标体积为 \(0.188496\)，一致。

4. cohesive cubic 权重在 \(g=0\) 与 \(g=g_c\) 的值和一阶导数连续：通过。

一次早期 scratch manufactured 命令因 PowerShell 数组运算解析错误而废弃；随后改用显式标量
运算重新执行并通过。该错误未修改任何项目文件，也未作为科学证据使用。

## Deviations

### DEV-PATH-001

用户已清理旧目录并批准最简骨架。原计划的 `03_分析与代码/...` 写域映射为：

- `src/route_h/`
- `data/route_h/`
- `docs/route_h/`
- `tests/route_h/`
- `project_control/`

没有扩大项目根目录，也没有改变 Stage 0 科学范围。

### DEV-HISTORICAL-ISOLATION-001

用户清理后，v01 计划列出的 migration、v03、v06 和 Stage 4 历史检查文件不在新项目中；
旧 D: 源目录当前不可读。本次没有重建、猜测或继承这些证据，而是把 Route H 冻结为
clean-room dependency：所有历史 pass flag、参数、几何有效性和求解结果均不得满足 Route H
门禁。

### DEV-ACTIVE-SIGN-001

计划中的主动功率前导负号与右端输入功率约定冲突。建议改用

\[
P_{\rm active\ control}
=\frac{\partial\Psi_{\rm act}}{\partial L_f^\star}\dot L_f^\star.
\]

等待用户决定。

### DEV-ACTIVE-MOMENT-001

固定投影方向不能一般性满足零净内部力矩。建议采用

\[
L_f=\|c^+-c^-\|,
\qquad
f_{\rm current}=(c^+-c^-)/L_f.
\]

等待用户决定。

## Blockers

Stage 0 当前不能标记为 frozen，原因是：

1. 主动输入功率符号尚未由用户决定；
2. 主动轴线/零净力矩修订尚未由用户决定；
3. 当前检查是同一执行者的 self-check，不是独立科学 inspection。

## Outputs produced

Stage 0 的合同、模型特化、case registry、坐标/符号说明、功率账本和验证注册表均已生成，
但状态保持 `draft_blocked_pending_user_scientific_decision` 或
`preregistered_not_authorized_to_run`。

下一步只需要用户接受或否决
`project_control/route_h_stage0_scientific_decision_v01.md`
中的两个科学修订。未得到决定前不会进入 Stage 1。

