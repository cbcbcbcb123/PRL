---
decision_request_id: DECISION-REQUEST-EFE-NODE1-N1-2-BACKEND-P1-REVIEW-V01
status: approved
requested_at: 2026-08-19
related_plan: project_control/efe_node1_n1_2_backend_productionization_p1_plan_v01.md
related_execution: project_control/efe_node1_n1_2_backend_productionization_p1_execution_v01.md
formal_n1_2_evidence: not_started
decision_record: project_control/efe_node1_n1_2_backend_productionization_p1_acceptance_decision_v01.md
---

# EFE Node 1 N1-2 backend productionization P1 终审请求 v01

## 推荐决定

建议人类终审：

1. 接受 P1 执行检查通过；
2. 接受 `fenicsx_ufl_ad_serial_v02_lazy_tangent` 为候选 ECM 生产后端；
3. 保留 Python ECM 作为 D0/E0 oracle，保留 SciPy 稀疏 Newton 作为当前完整
   耦合求解器；
4. 接受 PETSc SNES “ECM 子问题可用，但当前串行小网格不更快，暂不替换
   全系统 Newton”的结论；
5. 追认机器零能量/力使用绝对误差门，非零量使用相对误差门；
6. 批准下一步仅执行 `N1-2a`：FEniCSx 显式后端下的 D0/E0 完全耦合
   16-step 黏弹性单周期 pilot；pilot 经复核后，再决定 32-step 与 D1/E1。

## 本次不请求

- 不请求直接完成或接受正式 N1-2 收敛结论；
- 不请求立即执行 D1/E1；
- 不请求废弃参考后端或强制迁移 PETSc SNES；
- 不请求 N1-3、Node 2、实验拟合、论文定稿或发布；
- 不请求删除失败结果、容器或镜像。

## 待人类终审

人类终审已于 2026-08-19 明确指示“接受 P1，批准 N1-2a 16-step
pilot”。决定记录见
`project_control/efe_node1_n1_2_backend_productionization_p1_acceptance_decision_v01.md`。
