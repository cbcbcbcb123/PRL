---
record_id: PRL-FIG2-SPATIAL-TOLERANCE-ST1-E1-WARM-START-FAILURE-HUMAN-GATE-V01
status: blocked_at_human_gate
recorded_at: 2026-09-01
authorized_scope: st1_a1_a2_b1_b2_only
runtime_restored: true
failed_stage: e1_spatial_warm_start_scientific_gate
failed_output: results/hybrid/prl_figure2_spatial_tolerance_st1_warm_e1_v03_20260901
scientific_cycles_started: false
next_gate: human_warm_start_repair_decision
---

# PRL Figure 2 ST1：E1 空间暖启动失败与人类门

## 结论

Docker/FEniCSx 运行环境已经恢复，既有 CPU 镜像
`dolfinx/dolfinx:v0.11.0` 可正常导入 `basix 0.11.0`、
`dolfinx 0.11.0.post0` 和 `petsc4py 3.25.1`，项目目录挂载正常。

但全新的 E1 空间暖启动 v03 在相位 0 机械平衡硬门失败：归一化 KKT 残差为
`1.9647424237527947e-05`，高于 C0 冻结门 `1e-05`。因此未进入 A1，
A1、B1、A2、B2 的正式事务周期数仍全部为 0。该失败按合同 fail closed，等待
人类决定；不得把运行环境恢复误写为 ST1 已开始或暖启动已通过。

## 运行环境恢复证据

- Docker client/server：`29.1.3/29.1.3`；
- context：`desktop-linux`；backend：Linux `x86_64`；
- CPU/内存识别：80 CPU、`67221458944` bytes；
- 镜像：`dolfinx/dolfinx:v0.11.0`，digest
  `sha256:2ae4bfbc0d9077268880faf04c72750528bee986c94ab223a2c159969bd56fa8`；
- smoke 容器：`prl-st1-runtime-smoke-v02-20260901`；
- 未启用 GPU、未切换后端、未拉取新镜像、未清理历史容器。

## 暖启动尝试

### v02：启动配置失败

输出：
`results/hybrid/prl_figure2_spatial_tolerance_st1_warm_e1_v02_20260901`。

容器启动时显式设置 `PYTHONPATH=/workspace/src`，遮蔽了镜像原有 FEniCSx Python
路径，触发 `ModuleNotFoundError: No module named 'dolfinx'`。该目录保留，不作为
科学失败，也不计为目标事务周期。

### v03：科学硬门失败

输出：
`results/hybrid/prl_figure2_spatial_tolerance_st1_warm_e1_v03_20260901`。

去掉 `PYTHONPATH` 覆盖后，FEniCSx 后端完成计算并写出可审计摘要。结果如下：

- 映射覆盖率：`1.0`；
- 最大参考定位残差：`2.7194799110210365e-16`；
- 目标网格 SLS 周期残差：`5.307722380875671e-16`；
- 归一化 KKT 残差：`1.9647424237527947e-05`，**失败**；
- 体积约束残差：`1.1102230246251565e-16`；
- 最小 ECM Jacobian：`0.9993676972724249`；
- 最小间隙：`0.039094384146616715`；
- 心肌/心内膜最小面面积比：`0.999944948805329` / `0.9994641830636086`。

映射、周期性、体积和几何质量均通过；当前唯一失败项是相位 0 机械平衡 KKT 门。
失败 checkpoint 仅用于诊断，不得作为 A1 起点。

## 证据边界

1. Docker 已修复，不再是当前阻塞；
2. E1 映射和 SLS 周期重建已通过各自门，但这不等于完整暖启动通过；
3. 暖启动不是 ST1 端点证据；
4. 不得自动放宽 KKT 门、增加未登记回退、追加事务周期或直接进入 E2；
5. Figure 2 v02 继续保持时间离散阶段 FINAL，ST1 尚无新论文级结果。

## 待人类决定

建议下一步仅授权一个受控的相位 0 暖启动修复诊断，区分“冻结的 80 次 L-BFGS
预算不足”与“跨网格映射状态本身不能满足平衡门”。诊断应继续使用同一 FEniCSx
CPU 后端和 C0 门，不放宽 `1e-05`，不运行 T64 周期；形成修订入口并重新测试后，
再以全新输出目录恢复 E1 暖启动。

在该决定前，A1、B1、A2、B2 保持已授权但暂停；A3–B4、T128、T256、GPU、新
求解器和参数扫描仍未授权。
