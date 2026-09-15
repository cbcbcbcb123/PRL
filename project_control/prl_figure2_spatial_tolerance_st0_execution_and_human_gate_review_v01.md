---
record_id: PRL-FIG2-SPATIAL-TOLERANCE-ST0-EXECUTION-AND-HUMAN-GATE-V01
status: pass_for_human_review
executed_at: 2026-09-01
execution_scope: st0_only
authorization: project_control/prl_figure2_spatial_tolerance_contract_v02_st0_execution_authorization_decision_v01.md
contract: project_control/prl_figure2_spatial_tolerance_validation_contract_v02.md
evidence_package: results/hybrid/prl_figure2_spatial_tolerance_st0_v03_20260901
diagnostic_figure: 02_图表/Figures/Fig2_spatial_tolerance_st0_diagnostics_v03_20260901/st0_diagnostics.png
next_gate: prl_figure2_spatial_tolerance_st0_human_gate
execution_authorized_after_record: false
---

# PRL Figure 2 空间与容差 ST0：执行记录与 Human Gate 审阅

## 1. 裁决

ST0 v03 的全部七项机器门通过，状态为 `PASS_FOR_HUMAN_REVIEW`。本记录只证明
空间/容差计算的前置基础设施和制造检查可以进入人类审阅；它不证明空间收敛、
容差独立或联合时间—空间稳健性。

本轮到此停止。没有执行 A1–B4 完整周期、细网格 T128、T256、GPU、新外部求解器
或 Figure 2 v03 冻结。

## 2. 已通过的 ST0 证据

1. **完整配置指纹**：C0/C1 均序列化 32 个参数；两者只有合同允许的 7 项不同，
   其余算法、FEniCSx 后端、历史模式、回退策略、接触、零压力/WSS 和 L-BFGS
   参数完全冻结。两条路径均使用 unrelaxed Picard，回退关闭。
2. **F200N 嵌套**：E2/F150 的 1872 个节点和 8640 个四面体全部映入 F200N；
   坐标、连接、参考体积和材料编号均 byte-exact。F200N 为 `(19,8,16)`、3060
   个节点、14592 个四面体。
3. **界面不变量**：D0 的心肌—ECM/ECM—心内膜 tether 数为 `52/60`，D1 为
   `182/242`；总权重和一阶矩均通过冻结检查。
4. **共同求积与映射**：8640 个 E2/F150 共同求积点对全部候选网格覆盖率为
   100%；仿射 P1 重构误差不超过 `6.76e-16`。两侧表面映射覆盖率为 100%，
   守恒牵引投影的合力和合矩误差处于 `1e-16` 量级。
5. **R0 只读复演**：相位 `0,0.25,0.5,0.75,1` 的输入/接受 digest、variables、
   三层 vertices、ECM 内变量 Z 和门限布尔值全部 bitwise exact；未重新求解周期。
6. **离散功率账本**：使用
   `W_active + W_pressure + W_WSS = Delta_U_recoverable + D_SLS_alg + R_num`。
   T32/T64/T128 的绝对逐步残差比分别为 `1.029e-3`、`2.583e-4`、
   `6.466e-5`；SLS 算法耗散逐步非负；T64→T128 正功与绝对功差均约
   `9.67e-5`。
7. **CPU/存储预检**：所有网格的零载参考装配和一次指数 SLS 更新通过；
   A4/B4 的该项预检约 9.31 s，未压缩 T64 状态历史估计约 81.84 MB。

相关测试：空间 ST0、三层模型、三层求解器与 T128 入口共 25 项，通过。

## 3. 证据边界与待人类确认事项

- 表面映射是沿冻结材料射线定义的，不是要求 D0/D1 曲面在欧氏空间重合；两侧
  最大几何投影距离分别为 `0.0312 L` 和 `0.0281 L`。映射方程残差为机器精度，
  但该几何距离应在 ST1 前由人类确认可接受。
- follower tolerance 在零压力/WSS 下标记为 `not_exercised_zero_load`，不能称为
  已验证的非零随形载荷精度。
- 资源时间只是 CPU 装配、参考评估与一次 SLS 更新的下限，不是完整平衡求解或
  周期墙钟时间预测。
- 诊断图中的 T32/T64/T128 只复用已冻结时间病例来检查功率离散，不是本轮新执行
  的细网格 T128，也不构成共同极限证据。

## 4. 版本说明

`prl_figure2_spatial_tolerance_st0_v01_20260901` 和 v02 均被保留为初步证据包。
最终审计发现 v01 只序列化合同阈值；v02 补入多数隐藏默认值后，又进一步识别到
捕获位移边界/牛顿次数及稀疏谱预检开关尚未进入同一指纹。v03 冻结全部 32 项并
重新生成，作为本 Human Gate 的唯一候选证据。旧包没有覆盖或删除；该版本替换是
执行前审计完整性修复，不是物理门失败。

## 5. Human Gate

可供人类终审的下一决定仅有：

1. 接受 ST0，并另行授权 ST1 的 A1、A2、B1、B2；或
2. 要求修订 ST0，继续禁止任何完整空间周期。

在明确决定前，执行权限为 `false`。
