---
document_id: PRL-FEM-MIXED-LINEAR-DIAGNOSIS-V01
status: adopted
authorized_at: 2026-09-18
authorization: user agreed to continue the proposed mixed-linear-system diagnosis
result_root: E:/Temp-Projects/PRL-results/ventricle_fem/f6s1s_linear_system_diagnosis_v01_20260918
---

# F6-S1-S：DG2首个受压初值的混合线性系统诊断

## 目标

解释F6-S1-R在理想圆环p/mu=0.02、Newton更新0次时的`SNES_DIVERGED_LINEAR_SOLVE`。
本轮是工程诊断，不修复模型、不产生新的平衡态，也不改变F6-S1-R failed裁决。

## 冻结范围

- 只使用F6-S1-R已保存的M0圆环网格、p=0接受态和p=0.02失败态初值；要求三者状态链一致。
- 保持P2位移/DG2压力、mu=1、kappa=1000、六阶积分、平面应变、随动压力、固定点及PETSc选项不变。
- 一次无网络、单CPU、8GiB、0GPU容器；只组装一次p/mu=0.02初值残量与切线矩阵。
- 不调用`SNES.solve`或`NonlinearProblem.solve`，Newton更新数必须为0，状态向量前后逐字节不变。
- 对该同一矩阵只允许一次原配置`KSP preonly + LU/MUMPS`因子化/线性步尝试，记录KSP/PC原因及MUMPS `INFOG/RINFOG`。
- 使用同一已组装CSR矩阵做一次SciPy SuperLU交叉因子化；它只用于判断代数矩阵是否可解，不更新FEM状态、不成为生产求解器。
- 检查矩阵维数、非有限值、零行/列、结构秩、对称误差、u-u/u-p/p-u/p-p块范数、逐单元压力块谱及局部耦合秩。
- 保存CSR、右端、自由度映射、版本、原始诊断日志和一张矩阵结构/结果图；不进入真实轮廓、不改变材料或1%门、不测试替代参数。
- 失败即保全，不自动重跑；诊断完成也不授权修复或新的平衡求解。

## 判定边界

- `diagnostic_delivery=passed`仅表示证据足以缩小故障范围；不是DG2科学资格通过。
- 若MUMPS和SuperLU均失败或矩阵含非有限值/零行，具体修复仍需另立切片。
- 若MUMPS报告数值奇异而SuperLU以小残量求解，只支持“当前MUMPS主元/尺度路径触发失败”，不自动证明任意后端都稳定。
- 压力块因有限kappa非奇异，不等于P2/DG2在严格不可压极限inf-sup稳定，也不能推广到三维。
- 当前二维局部J失败、真实三维、FSI、生长、ECM反馈及生物学验证状态均保持原记录。

## 安全与交付

使用已批准外置结果库及磁盘余量门禁；代码仓3GiB硬限保持。新包create-only。
保护F6-S1-R完整包、既有FEM证据和工作区无关改动；不删除、移动、安装、拉取、重启Docker或推送远端。
完成后独立核验哈希、图件和导航，仅明确暂存本轮文件并提交本地main。
