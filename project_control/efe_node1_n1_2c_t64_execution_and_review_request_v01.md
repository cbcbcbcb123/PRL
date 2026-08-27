---
inspection_id: INSPECTION-EFE-NODE1-N1-2C-T64-V01
status: awaiting_human_gate_t64
inspector: codex_current_task
submitted_to: human_final_reviewer
submitted_at: 2026-08-26
related_plan: project_control/efe_node1_n1_2c_time_refinement_contract_v01.md
authorization: project_control/efe_node1_n1_2c_t32_acceptance_and_p3_p4_authorization_decision_v01.md
executed_scope: p3_p4_only
stopped_at: human_gate_t64
---

# EFE Node 1 N1-2c：T64 执行结果与 Human Gate 审阅请求 v01

## 结论先行

P3 的 T32→T64 暖启动审计通过，P4 的两个 T64 正式事务周期完成；共 128 个
顺序 CPU worker 事务全部通过且 PID 唯一。T64 cycle 2 相对 cycle 1 的五项周期门
均通过，最大周期差为周期末完整 ECM `Z` 的 `2.11085e-5`，低于预登记门
`1e-3` 约 47 倍。因此，可把当前结果提交为 **T64 周期稳态候选**。

本次没有执行 P5。T16/T32/T64 三档正式时间裁决、观察阶/Richardson 分析、正式
时间收敛 Figure 2 和任何 T128 计算都没有发生；不能据本报告宣称“时间收敛已
证明”。

## 授权与实际边界

已执行且仅执行：

1. P3：接受的 T32 cycle 2 → 65 相位 T64 可审计重采样及冻结几何 SLS 周期
   固定点；
2. P4：T64 cycle 1 与 cycle 2，各 64 个新求解事务；
3. T64 内部周期门、安全门、敏感相位和阶段科研审阅图；
4. 实现测试、完整 hybrid 回归、结果摘要与容器退出核验。

未执行：P5 三档比较、观察阶、Richardson、正式 Figure 2、T128、空间细化、
参数扫描、N1-2d、N1-3、Node 2、GPU worker 或新外部求解器。

## P3：T64 暖启动审计

结果目录：
`results/hybrid/efe_node1_n1_2c_t64_warm_start_v01_20260826/`

| 项目 | 结果 | 判定 |
|---|---:|---|
| 目标步数/相位点 | `64 / 65` | 符合 |
| T32 公共相位 | bitwise exact | 通过 |
| 冻结几何周期残差 | `5.23096e-16` | 通过 |
| 候选内部 `Z` 相对差 | `0` | 通过 |
| phase 0 归一化 KKT | `1.29436e-6` | `<1e-5` |
| 体积残差 | `2.22045e-16` | `<1e-8` |
| 最小 ECM `J` | `0.999021` | `>0.5` |
| 最小 gap | `0.0391219` | `>-1e-12` |
| create-only checkpoint | `e6872de9...e6ef` | 通过 |
| 耗时 | `45.29 s` | 记录 |

该步骤只产生 T64 暖启动，不构成 T64 动态周期证据。正式证据来自后续 128 个
新求解事务。

## P4：T64 两周期事务结果

结果目录：
`results/hybrid/efe_node1_n1_2c_t64_transactional_cycle_v01_20260826/`

### 事务完整性

| 项目 | 结果 |
|---|---:|
| 正式事务 | `128 / 128` 通过 |
| 每周期 CSV 行数 | `65, 65` |
| worker PID | `128` 个且全部唯一 |
| T64 时间步 | `1/64 = 0.015625 T` |
| 总耗时 | `6112.95 s`（约 `1.70 h`） |
| cycle 1 / cycle 2 求解耗时 | `3050.80 / 2988.62 s` |
| 容器镜像 | `dolfinx/dolfinx:v0.11.0`，CPU |
| 暖启动/周期容器退出码 | `0 / 0` |

### T64 cycle 2 相对 cycle 1 的预登记周期门

| 指标 | 归一化差 | 门 | 判定 |
|---|---:|---:|---|
| 轴向缩短波形 | `5.27989e-8` | `1e-3` | 通过 |
| 最大界面牵引波形 | `4.84719e-6` | `1e-3` | 通过 |
| 总储能波形 | `1.35905e-8` | `1e-3` | 通过 |
| ECM `||Z||` 波形 | `1.82346e-5` | `1e-3` | 通过 |
| 周期末完整 ECM `Z` | `2.11085e-5` | `1e-3` | 通过 |

### cycle 2 的物理与安全读数

| 指标 | 结果 | 门/含义 |
|---|---:|---|
| 峰值轴向缩短 | `0.116882`（`11.6882%`） | 物理读数 |
| 峰值最大界面牵引 | `0.0977303` | 物理读数 |
| 周期 ECM 耗散 | `2.47358e-6` | 正且有限 |
| 最大归一化 KKT | `1.35155e-7` | `<1e-5` |
| 最大 raw coupling residual | `9.13285e-5` | `<1e-4` |
| 最小 ECM `J` | `0.987734` | `>0.5` |
| 最小 gap | `0.0155184` | `>-1e-12` |

## 敏感相位审计

1. 预登记的 T16 敏感相位 `0.25, 0.6875, 0.8125, 0.875` 在 T64 两周期均通过；
   T16 的 phase `0.25` fallback 未复发。
2. T64 新出现的 step 15 是可重复的局部耦合敏感相位：cycle 1/2 raw coupling
   residual 分别为 `9.12867e-5` 与 `9.13285e-5`，均低于 `1e-4`，但只保留约
   `8.7%` 裕量。它应在 P5 和后续空间/材料研究中作为注册诊断相位，而不能被
   当作失败或生物学热点。
3. cycle 1 step 12 的 KKT `6.11484e-6` 在 cycle 2 降至约 `4.03e-9`；这是孤立的
   求解路径敏感性，不是重复物理现象。
4. cycle 1 step 10 与 step 59 的额外 coupling 迭代未在 cycle 2 重复；均通过原
   oracle，没有修改门限或追加周期。

## 跨级预览：只用于决定是否批准 P5

T64 cycle 1 与接受的 T32 cycle 2 比较得到：

| 指标 | T32→T64 预览差 |
|---|---:|
| 轴向缩短波形 | `0.1591%` |
| 最大界面牵引波形 | `0.3102%` |
| 总储能波形 | `0.3954%` |
| ECM `||Z||` 波形 | `0.1981%` |
| 周期末完整 ECM `Z` | `3.00868e-5` |

这些值提示 T32→T64 差异较小，但它们只是运行入口产生的观察性预览。尚未执行
预登记 P5 的统一三档相位重建、积分量、峰值相位、耗散、局部场、误差单调性、
观察阶和不可辨识裁决，因此不升级为正式时间收敛证据。

## 阶段科研审阅图 v01

Figure 包：
`02_图表/Figures/Fig2_n1_2_t64_cycle_stability_interim/`
`Fig2_n1_2_t64_cycle_stability_interim_v01_20260826/`

图中：A–C 比较两个 T64 周期的细胞缩短、界面载荷和 ECM 黏弹记忆；D 汇总五项
周期门；E 显示 KKT/coupling 裕量并标出 step 15；F 为 T64 cycle 2 峰值收缩的
真实三维状态。图题明确标注“P5 not performed”。Notebook 已执行，自动校验和
人工视觉 QA 均通过。当前状态是 **validated working, pending user confirmation**，
尚未标记 FINAL。

图文件 SHA-256：

- PNG：`82b20d979c13bd0978eccd50be36a754ee3c65c041a0194de11e527f874ef29a`
- SVG：`03c331d3b5dda563b6f77438ea62517008b93f17029326fb2068e8c16e24f476`

## 软件与证据核验

- 针对时间细化实现的测试：`34 passed`；
- 完整 hybrid 回归：`103 passed in 172.66 s`；
- Ruff：时间细化模块、T64 暖启动/周期入口、绘图辅助代码全部通过；
- 进度输出已从冻结父入口的装饰性 `/16` 修正为 T64 的 `/64`，不改变数值计算；
- 暖启动 summary SHA-256：
  `44383cbfd8d9f17abea720c6c6d09ba0aa3ab937aa7f5f19c0a7258157c84cb3`；
- T64 周期 summary SHA-256：
  `e8ccae923d99585d6b54c51a508c48b3a9497cfc80aab0424a92237cd0dd5bc5`。

## 审阅意见

执行者建议：

1. 接受 T64 cycle 2 为 N1-2c 的 T64 周期稳态候选；
2. 接受“重采样只用于暖启动，正式证据来自新求解事务”的证据边界；
3. 接受并冻结阶段诊断图 v01；
4. 若继续，单独批准 P5：对 T16/T32/T64 做正式三档时间裁决、观察阶或不可辨识
   判定，并制作正式时间收敛 Figure 2；到 N1-2c Final Human Gate 停止。

## Requested Human Decision

建议回复：

> 接受 N1-2c T64 周期稳态候选与阶段诊断图 v01；接受重采样只用于暖启动的证据
> 边界；批准 P5 三档时间裁决、观察阶或不可辨识判定与正式时间收敛 Figure 2；
> 到 N1-2c Final Human Gate 停止。P5 不授权 T128、空间细化、参数扫描、N1-2d、
> N1-3、Node 2、GPU worker或新外部求解器。

在获得该决定前，执行状态保持 `human_gate_t64_pending_review`。
