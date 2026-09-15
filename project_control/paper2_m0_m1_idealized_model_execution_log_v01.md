---
execution_id: EXEC-PAPER2-M0-M1-IDEALIZED-MODEL-V01
plan_id: PLAN-PAPER2-M0-M1-IDEALIZED-MODEL-V01
executor: Codex current task
started_at: 2026-09-03
completed_at: 2026-09-03
status: completed_with_deviation
deviation_records:
  - DEV-PAPER2-M1-RESULT-VERSION-LINEAGE-V01
  - DEV-PAPER2-M1-REGRESSION-IMPORT-PATH-V01
next_gate: human_active_myocardial_fem_identity_conversion_gate
---

# Paper 2 M0–M1 理想体模型执行日志 v01

## Approved plan reference

- `project_control/paper2_m0_m1_idealized_model_execution_plan_v01.md`；
- 人类终审批准范围：M0 只读兼容性审计＋M1 CPU 理想化条带；完成后停止；
- 未授权范围保持不变：GPU、双向 FSI、移动域 CFD、真实几何、参数扫描、共同极限正式计算、A1 追加周期、Git 提交/推送/发布。

## Outcome

M0 已完成；M1 新架构的无量纲 quasi-2D 最小模型和验证包已完成，状态为
`passed_m1_human_gate_candidate`。这表示端口身份、分离载荷、作用—反作用、SLS
耗散、即时/周期功率账本和确定性检查通过；不表示生理标定、正式网格/时间收敛、
二维/三维实体实现或论文主张通过。

当前停止在 `human_active_myocardial_fem_identity_conversion_gate`。

## Commands or tools used

1. 只读检查 Git 分支、commit、dirty worktree、A1 summary 和关键合同；
2. 用 Poppler 将 16 页规划 PDF 渲染到项目内审阅目录，并逐张查看四个联系页；未修改源 PDF；
3. 用新 Python/NumPy 模块装配小规模线性系统并在 CPU 上运行；
4. 用 pytest 执行新 M1 测试和旧功率/空间预检回归；
5. 用 Matplotlib 生成内部诊断图；
6. 用 SHA256 冻结 create-only 结果清单。

未启动 GPU、Docker、FEniCSx worker、FEBio 或新的外部求解器。

## Files changed

### Project control

- `project_control/paper2_m0_m1_idealized_model_execution_plan_v01.md`；
- `project_control/paper2_m0_compatibility_audit_v01.md`；
- `project_control/paper2_m0_m1_idealized_model_execution_log_v01.md`；
- `project_control/CURRENT_STATUS.md`（只新增 Paper 2 M1 门信息并保留旧 A1 状态）。

### New implementation and tests

- `src/paper2_m1/__init__.py`；
- `src/paper2_m1/idealized_strip.py`；
- `tests/paper2_m1/test_idealized_strip.py`；
- `scripts/run_paper2_m1_idealized_strip_v01.py`。

未修改 `src/hybrid`、`src/route_h` 或旧测试/结果。

### Versioned outputs

- `artifacts/paper2_m0_m1/pdf_review_v2_20260903/`：规划 PDF 只读渲染证据；
- `results/paper2_m1/idealized_strip_v01_20260903/`：首次完整运行，保留；
- `results/paper2_m1/idealized_strip_v02_20260903/`：补充即时功率和逐周期账本，保留；
- `results/paper2_m1/idealized_strip_v03_20260903/`：补充心内膜/ECM 缩短传递量，作为本门最终候选。

没有覆盖、删除或移动 v01/v02。v03 manifest SHA256：
`6c07262b1fe598849896303ac535394f75b6094a5abb61810fc3e8b0ac2fac14`；
validation summary SHA256：
`639c370cbfaf3c586c6a7f71e9fd7e1b8114200eaf81f474a897844b3bfa9c5e`；
诊断图 SHA256：
`cb8d977124c92e2a0c281bb44c9de666997acbb04d9322eeb334fae42a3c2057`。

## Equations and port choices

### Model identity

- 心内膜：节点/连接 DCM 链，输出逐连接力和逐节点界面牵引；
- ECM：P1 条带 FEM，平衡支路加 Maxwell 支路，内部应变 `Z`；
- 心肌：P1 主动本征应变 FEM；
- 界面：同位置节点、同一集中求积权重的两组弹性连接；
- 运动学：沿条带的一维空间离散，每个节点保留切向/法向两分量。

### Active form

沿用旧 preferred-length/metric 的能量端口，连续化为

`Psi_myo = 1/2 ∫ E_m (epsilon_x+a)^2 dx`，

`P_active = (partial Psi_myo / partial a) adot`。

选择主动本征应变而非主动应力，是为了身份转换首步不同时改变冻结的主动控制器功率语义。

### Boundary and ledger

- `n_lum=+e_y`；
- `t_lum=-p n_lum+tau e_x`；
- `P_lum=f_lum·v_endo`；
- `P_ext=f_ext·v_myo`；
- 固定基座弹簧记储能，不记外功；
- 隐式中点逐步核对
  `Delta E + D_ECM + D_endo + D_myo = W_lum + W_ext + W_active + R_num`。

## Tests or checks run

### New M1 tests

命令等价于 `pytest tests/paper2_m1/test_idealized_strip.py -q`：

- `7 passed in 3.40 s`；
- 包括能量矩阵恒等式、零驱动、压力/剪切分离、主动传递、外支撑端口、作用—反作用、界面功率、被动松弛、非负耗散、即时功率字段、逐周期账本、确定性重放和敏感性初筛。

### Existing regression checks

旧 `test_loads_ledger_guards.py` 和 `test_prl_figure2_spatial_st0.py`：

- 首次调用因当前 Python 未自动加入 `src` 而在收集期报 `ModuleNotFoundError: route_h`；
- 以显式 `sys.path.insert(0, project/src)` 重跑相同测试：`16 passed in 74.52 s`；
- 环境初始化出现 CuPy 的 `CUDA path could not be detected` 警告，但没有调用 CuPy 或 GPU。

## M1 numerical results

主动峰值 `a=0.10` 的 v03 基线：

- 心肌峰值轴向缩短：`0.0837865307719656`；
- ECM 峰值轴向缩短：`0.0235159705838291`；
- 心内膜 DCM 峰值轴向缩短：`0.0107530051262929`；
- 最大 `|Z_ECM|`：`0.0263706661268524`；
- 最大心内膜–ECM 牵引：`0.0446973965198147`；
- 最大 ECM–心肌牵引：`0.243358421183472`；
- 激活到心肌缩短的基频增益：`0.831392506339496`；
- 激活到 ECM 缩短的基频增益：`0.208826962534952`；
- 激活到心内膜缩短的基频增益：`0.095688430580233`；
- 激活到心肌缩短的相位差：`-0.0292275049911783 rad`。

压力-only 的直接切向串扰为 `0`；剪切-only 的直接法向串扰为 `0`。它们是当前正交线性运动学的制造解检查，不是生理上“压力和剪切永不耦合”的主张。

## Ledger closure

主动基线：

- 最大单步绝对账本残差：`5.49936141004854e-19`；
- 最大单周期积分账本残差：`8.47879980201555e-19`；
- 四周期总积分残差：`7.60777137916685e-19`；
- 最大界面功率残差：`3.25260651745651e-19`；
- 最小单步耗散：`9.1640219794205e-16`。

被动扰动松弛的储能下降 `0.0004784470376541329`，全部记录耗散非负。

## Sensitivity screen

这只是两点初筛，不是正式收敛证明：

- T64→T128：心肌峰值缩短差 `0.0001164565`，心内膜–ECM 牵引差 `0.0004959227`，最大 `Z` 差 `0.0004097709`；
- N9→N17：对应差分别为 `0.0040470885`、`0.0215467208`、`0.0048763180`。

未执行 Richardson 外推、二维/三维空间细化、容差分离或多网格共同极限，因此不得写“已收敛”。

## Deviations

### DEV-PAPER2-M1-RESULT-VERSION-LINEAGE-V01

首次 v01 输出后，内部自检发现任务还要求显式即时功率和单周期积分账本，因此不覆盖 v01，而是产生 v02；随后为避免对称平均位移掩盖主动传递，又新增心内膜/ECM 轴向缩短，产生 v03。三个目录都保留，v03 是当前人类门候选。模型方程、参数和已批准范围未改变。

### DEV-PAPER2-M1-REGRESSION-IMPORT-PATH-V01

旧回归测试第一次在收集期因 `src` 不在解释器路径而失败；该失败不是模型或测试断言失败。使用显式只读导入路径重跑后 16 项全部通过，未修改旧测试或环境变量。

### PDF rendering note

规划 PDF 的文本层存在字体编码乱码，且 Poppler 报告 Symbol/ArialUnicode 显示字体警告。按只读 PDF 流程将 16 页渲染为 PNG 并逐页核对；可读内容足以确认模型身份、端口和功率账本。源 PDF 未改动。

## Blockers

无 M1 硬门失败。当前唯一停止条件是人类终审：是否接受该低维身份/端口验证，并批准下一阶段真实二维/三维主动心肌 FEM 身份转换合同。

## Outputs produced

最终候选入口：

- `results/paper2_m1/idealized_strip_v03_20260903/validation_summary.json`；
- `results/paper2_m1/idealized_strip_v03_20260903/manifest.json`；
- `results/paper2_m1/idealized_strip_v03_20260903/m1_diagnostic_summary.png`；
- 每个工况的 `.npz` 全数组和独立 summary JSON。

## Evidence boundary and next gate

M1 只证明“新身份的最小离散系统在当前无量纲条带上可运行且功率闭合”。它不证明：

- cardiac jelly 参数真实；
- DCM 必然优于 all-FEM；
- 真实心室压力/剪切耦合；
- 细胞膜、体积、弯曲或重排已进入新模型；
- 二维/三维主动心肌 FEM、非匹配界面和空间收敛已完成；
- EFE 机制或疾病预测成立。

建议人类门接受后，下一合同仅规划真实二维/三维主动心肌 FEM 的身份转换与制造解，不自动进入参数扫描或流体求解。
