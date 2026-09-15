---
document_id: PRL-Z1-PARENT-PASSIVE-REPAIR-EXECUTION-RECORD-V01
status: current
completed_at: 2026-09-12T14:49:00+08:00
stage: Z1-PARENT-REPAIR
repair_status: PASS_REPAIR
parent_z1_status: UNRESOLVED_FORMAL_MATRIX
result: results/ventricle_z1/parent_repair_v06_20260912
---

# Z1 父级被动力学修复执行记录 v01

## 裁决

本次限定修复为 **PASS_REPAIR**。它闭合了父 Z1 预检中已经定位的三类实现问题：弯曲力与弯曲能的工作共轭、完整保守能量导出、刚体协变及合力/合矩平衡。父级 Z1 仍为 **UNRESOLVED_FORMAL_MATRIX**，因为完整组合模型的 AXIAL / TRANSVERSE / RELAX、时间细化及体积罚参数细化矩阵尚未按父合同重跑；不得据此进入 Z2。

## 实现范围

- `E:/MeshCell3D/code/muse_dcm` 的 Python 参考路径采用离散铰链弯曲能的解析负梯度，并修正微米尺度有效铰链被长度阈值误排除的问题。
- 压力势能改为 `K V0 (r log r - r + 1)`；全局面积能、膜参考态能和弯曲能均进入正式能量导出。
- 保留既有 `surface_tension_energy = 0.5 gamma A` 绘图缓存，同时新增工作共轭的 `surface_potential_energy = gamma A`，两者不再混入同一账本。
- Numba 路径通过独立 parity。未重建 C++ 扩展，也未运行 CUDA 弯曲 parity；含保守弯曲的 C++/CUDA 请求在运行时失败关闭到 Python 参考路径。

## 冻结结果

- 最差“最佳步长”方向导数相对误差：`4.187784028222584e-09`，冻结门 `1e-6`。
- 最大独立能量重建相对误差：`4.1237918758241266e-13`，冻结门 `1e-2`。
- 最大刚体协变/合力/合矩相对误差：`2.114501288862503e-14`，冻结门 `1e-10`。
- 球形 1:1:1、长轴心肌 3:1:1、扁平心内膜 4:4:1；80/320/1280 面三档网格。
- 长轴与扁平细胞各保存 `lambda=0, 0.5, 1` 三个规定路径点，共 6 个 NPZ。它们是准静态本构探针，不是物理时间步。
- 网格图已显示曲率、参考边应变、节点力和细胞压力；未构造当前壳模型未定义的三维 Cauchy 应力张量。

## 验证

- 完整单元测试：159 passed，5 skipped；跳过项仅为已退役的持久校准缓存。
- Numba 后端 parity：`success=true`。
- 独立结果包复核：`passed`；6 个快照的拓扑、数组维度和有限值均复核通过。
- 两张定量图样式验证通过；五张最终 PNG 人工检查通过。
- v05 数值通过但人工发现方向标注遮挡和压力色条裁切，已保留失败记录；v06 修复排版后重新冻结并完整重跑。

## 证据入口

- `results/ventricle_z1/parent_repair_v06_20260912/index.html`
- `results/ventricle_z1/parent_repair_v06_20260912/summary.json`
- `results/ventricle_z1/parent_repair_v06_20260912/verification/independent_verification.json`
- `results/ventricle_z1/parent_repair_v06_20260912/visual_qa.json`
- `results/ventricle_z1/parent_repair_v06_20260912/verification/command_results.json`

## 下一门

下一步只能先为父 Z1 完整组合模型冻结 AXIAL / TRANSVERSE / RELAX 与网格、时间、体积罚参数细化矩阵，再单独取得执行授权。多细胞黏附固定、两端约束和细胞内周期主动拉伸属于后续阶段，本次未运行。
