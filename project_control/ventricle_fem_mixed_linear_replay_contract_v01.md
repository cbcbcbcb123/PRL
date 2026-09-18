---
document_id: PRL-FEM-MIXED-LINEAR-REPLAY-V01
status: adopted
authorized_at: 2026-09-18
authorization: user agreed to continue the proposed same-initial-state diagnostic replay
result_root: E:/Temp-Projects/PRL-results/ventricle_fem/f6s1s2_linear_report_replay_v01_20260918
---

# F6-S1-S2：同一初值的诊断报告重放

用户最新“同意，继续”批准上轮提出的同矩阵诊断重放。沿用F6-S1-S的冻结物理设置，
仅增加可靠的逐项持久化与非有限值编码。F6-S1-R、F6-S1-S原包保持原样。

- 一个单CPU、8 GiB、0 GPU、禁网容器，300秒上限；固定现有镜像，不安装/更新/拉取/重启。
- 同一896单元圆环、同一P2/DG2空间、mu=1、kappa=1000、压力0.02、主动0、原规范点与PETSc配置。
- 只组装一次初始切线；与F6-S1-S保存CSR、右端、DOF映射逐项核对，相同才因子化。
- 只做一次原MUMPS线性求解尝试及一次同矩阵SuperLU交叉尝试；条件估计可复用已有LU，不能重新分解。
- 不调用非线性solve，不更新状态；单独保存前后向量验证。
- 矩阵、SuperLU结果、MUMPS结果、前后状态分别即时保存；NaN/Inf明确编码，不吞掉错误。
- 记录实际KSP/PC类型、原因、MUMPS INFOG/RINFOG及可读取的控制项，保存两个线性解供独立残量复核。
- 失败保全且不自动重复；独立后处理不进行全局分解。交付实际圆环结构及诊断结果图。
- 本轮不测试块缩放、静态消元或替代压力空间，也不推进轮廓、主动、三维、FSI或生长。

判定：诊断报告完整且状态/矩阵身份通过可记为诊断交付passed；MUMPS失败本身是待解释的观察结果。
原DG2受压平衡仍failed，原1%局部体积门保持。根因须依据具体错误码，不能仅由块尺度比推断。

结果使用已批准PRL-results目录，代码/导航本地main提交，不推送、不删除任何路径。
