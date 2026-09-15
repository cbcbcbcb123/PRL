---
decision_id: DEC-PAPER2-M1-ACCEPT-M2-CONTRACT-V01
status: approved
decider: human_final_reviewer
decided_at: 2026-09-03
accepted_execution: project_control/paper2_m0_m1_idealized_model_execution_log_v01.md
authorized_next_action: draft_m2_identity_conversion_contract_only
execution_authorized: false
---

# Paper 2 M1 接受与 M2 合同起草授权决定 v01

## Decision

人类终审接受 M1 为**低维模型身份、端口和离散功率账本验证**，并批准起草下一阶段
“二维/三维主动心肌 FEM 身份转换合同”。本决定不授权执行该合同。

## Accepted evidence

- M1 使用一维 P1 条带和二维切向/法向运动学；
- 模型身份为心内膜 DCM—SLS ECM FEM—主动本征应变心肌 FEM；
- 压力、剪切、主动和外支撑端口已经分账；
- 作用—反作用、界面功率、逐步/周期总账本和非负耗散门通过；
- 新模型测试独立复核为 `7 passed`，关键旧回归独立复核为 `16 passed`；
- 最终候选 manifest、validation summary 和诊断图哈希与执行记录一致；
- 未使用 GPU，未修改共享核心，未改判旧 A1 失败。

## Explicit non-inferences

本次接受不表示：

1. M1 是真实二维或三维实体；
2. 心肌主动参数具有生理定量意义；
3. 压力与剪切在真实心室中正交解耦；
4. DCM 已证明优于连续心内膜；
5. 已获得正式空间/时间收敛、De–H–Pi_f–Delta_phi 状态律或 EFE 机制。

## Authorized next action

只允许起草 `project_control/paper2_m2_active_myocardial_fem_identity_conversion_contract_v01.md`，
把二维直接等价比较、三维有限变形验证、制造解、功率端口、误差门和停止规则写清楚。
合同必须返回人类审阅；未经新批准，不得运行二维/三维求解器。

## Out of scope

本决定不授权 A1 追加周期、二维/三维计算、GPU、CFD、单向/双向 FSI、真实心室、
参数扫描、实验拟合、Git 提交/推送或发布。
