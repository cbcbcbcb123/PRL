---
document_id: PRL-FEM-MUMPS-WORKSPACE-V01
status: adopted
authorized_at: 2026-09-18
authorization: user agreed to the proposed single same-matrix workspace-margin check
result_root: E:/Temp-Projects/PRL-results/ventricle_fem/f6s1s3_mumps_workspace_v01_20260918
---

# F6-S1-S3：同矩阵MUMPS工作空间最小修复验证

用户“同意，继续”批准上轮建议。本轮只将MUMPS `mat_mumps_icntl_14`由原实际20改为100，
即相对于估计工作空间的额外余量由20%变100%，不表示容器内存扩大5倍。

- 直接读取F6-S1-S2保存的CSR、右端和初值，不重组装，不改变矩阵或任何材料、几何、边界、载荷、压力空间和1%门。
- 新建顺序AIJ矩阵与独立KSP，保持原`M0_`前缀、preonly/LU/MUMPS；核对保存的其他可读MUMPS控制项。
- 一次MUMPS线性尝试；0次新的SuperLU因子化，直接与S2保存的SuperLU向量比较。
- 验收要求：KSP正收敛原因、PC=0、INFOG(1)=0、解有限、独立相对残量≤1e-8、两解相对2范数差≤1e-6。
  后一阈值是本轮预声明线性对照门，不是生物学容差，不取代原1%体积门。
- 保存输入、PETSc读取及求解后CSR、前后初值数组、实际控制项、完整报告和解；后处理只做稀疏乘法与范数。
- 一个已有固定镜像容器，单CPU、8 GiB、300秒、0 GPU、禁网；不安装/拉取/重启、不自动重跑，失败保全。
- 0次非线性求解、0次FEM状态更新；不构造新的平衡态，不推进轮廓/主动/三维/FSI/生长。
- 工作空间试验成功仅授权提出恢复圆环被动资格的下一切片；本合同不执行该非线性阶段。

沿用外部结果库准入、至少64 MiB停止空间及10 GiB磁盘余量。保留所有父证据和S2来源链。
输出实际模型结构图与本次真实诊断结果，0新形变状态不能画成形变时间序列。
本地main提交，结果不进Git、不推送、不删除任何路径。
