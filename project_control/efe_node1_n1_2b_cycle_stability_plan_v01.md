---
plan_id: PLAN-EFE-NODE1-N1-2B-CYCLE-STABILITY-V01
status: approved
planner: codex_current_task
approved_by: human_final_reviewer
approved_at: 2026-08-20
executor: codex_current_task
inspector: human_final_reviewer
related_memory_entries: []
---

# EFE Node 1 N1-2b 周期稳态验证计划 v01

## Goal

在已接受的 D0/E0/F150、T16 完全耦合路径上消除零历史首周期瞬态，并用
预登记、可复算的周期差判据检验模型是否达到黏弹性极限周期。

## Inputs

- 已接受的 N1-2a `cycle_01` 完整几何历史；
- D0 心肌/内膜、E0 ECM、F150 足迹；
- `T=1`、峰值激活 `0.20`、16 steps/cycle；
- `mu_ve=0.5`、`eta_ve=0.5`；
- `fenicsx_ufl_ad_serial_v02_lazy_tangent` ECM 后端；
- 已登记的耦合门 `r_Z <=1e-4` 与状态硬门。

## Outputs

1. 冻结 N1-2a 几何下的解析周期 `Z` 暖启动及其平衡检查点；
2. 从暖启动出发的 2–4 个完全耦合 T16 周期；
3. 每周期状态、时序、检查点、周期摘要和总摘要；
4. 跨周期四条登记波形叠加图、收敛门诊断图和牵引—缩短滞回图；
5. 执行报告与人类终审请求。

## Implementation Steps

1. 为暖启动工具补齐项目自举、显式 FEniCSx seam、后端诊断、严格 KKT
   捕获门和稀疏精化残差保护传递；
2. 用 N1-2a 的 17 相位 ECM 几何解析求解冻结几何 SLS 周期固定点，并在
   `a=0` 下重新平衡三层几何；
3. 从该检查点连续推进完全耦合 T16 周期，最少 2 个、最多 4 个；
4. 每个周期都执行既有 KKT、体积、`J`、gap、面面积、SLS、耗散和 `Z`
   硬门；
5. 从第二周期起，把相邻周期插值到共同 4097 相位，计算四条登记波形的
   对称归一化 L2 差，并计算周期末 `Z` 相对差；
6. 首次通过全部周期门时停止；若第 4 周期仍未通过则保留失败并停止；
7. 生成可复算阶段图并提交人类终审。

## Impacted Files Or Modules

- `scripts/prepare_efe_node1_n1_2_periodic_warm_start_v01.py`；
- `scripts/run_efe_node1_n1_2_periodic_case_v01.py`（仅在发现受批准范围内的
  必要缺陷时修改）；
- N1-2b 阶段绘图脚本；
- 相关 hybrid tests；
- `project_control` 中的决定、执行与终审记录。

## Test Plan

- 暖启动脚本默认 reference 后端兼容，FEniCSx 路径显式可审计；
- 解析冻结几何周期残差 `<=1e-12`，暖启动平衡 KKT `<=1e-5`；
- 相关 pytest 与 Ruff 通过；
- JSON/CSV/NPZ 全部可读取，周期数量与每周期 17 个相位一致；
- PNG/SVG 非空并人工视觉核查。

## Risks

- 冻结几何解析周期态不是完全耦合周期态，只能降低瞬态，不能作为证据；
- 暖启动几何重平衡可能触发稀疏精化；
- 完全耦合几何会改变 SLS 周期映射，4 周期内可能仍未达到门限；
- T16 只能建立该离散下的周期稳定性，不能替代后续时间收敛。

## Acceptance Criteria

暖启动辅助门：

- 冻结几何 `Z` 周期相对残差 `<=1e-12`；
- `a=0` 平衡 KKT `<=1e-5`、`min J >=0.5`、`min gap >=-1e-12`。

周期稳定候选门：

- 至少完成两个连续、完全耦合 T16 周期，且每个接受相位通过既有硬门；
- 相邻两周期的 `axial_shortening`、
  `maximum_discrete_interface_traction`、`total_stored_energy`、
  `ecm_internal_z_norm` 四条波形，对称归一化 L2 差分别 `<=1e-3`；
- 相邻周期末 `ecm_internal_z` 相对差 `<=1e-3`；
- 只要任一登记量未通过，即不得声称周期稳定。

## Out Of Scope

- 超过 4 个验证周期；
- T32/T64 时间收敛；
- D1/E1、F200、ECM 参数扫描；
- N1-3、Node 2、实验拟合、EFE 疾病效应与论文终稿图。

## Required Memory Updates

只有在人类终审接受 N1-2b 后，才把“D0/E0/F150、T16 已达到周期稳态”写入
稳定项目状态；暖启动本身及当前任务自检均不构成独立接受。
