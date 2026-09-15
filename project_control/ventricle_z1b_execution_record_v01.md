---
document_id: PRL-VENTRICLE-Z1B-EXECUTION-RECORD-V01
status: current
substage_status: PASS_REFERENCE_STATE
parent_stage_status: BLOCKED_DEPENDENCY
physics_status: passed_reference_state_only
visualization_status: passed
claims_status: synthetic_numerical_benchmark_only
executed_at: 2026-09-11
authorization: project_control/ventricle_z1b_execution_authorization_v01.md
contract: project_control/ventricle_z1b_reference_state_contract_v01.md
result_package: results/ventricle_z1/z1b_v04_20260911
next_stage_authorized: false
---

# Z1-B 长轴与扁平细胞参考态执行记录 v01

## 裁决

本轮按用户授权修改唯一 E:\MeshCell3D\code\muse_dcm 内核，加入显式捕获的通用表面参考度量；PRL 未复制第二套内核。最终 create-only v04 包的参考态、方向导数、刚体客观性、方向响应、卸载恢复、网格细化、失败关闭和预算门全部通过，独立验证器亦为 PASS。因此 Z1-B 的**参考态子门**记为 PASS_REFERENCE_STATE。

该结果证明 3:1:1 长轴探针和 4:4:1 扁平探针可以是内核的无载参考态，并能在小幅加载后恢复；它不证明真实心肌/心内膜材料参数，不等于纤维材料各向异性已标定。旧弯曲/面积账本和 Z1-C 接触仍未解决或未运行，所以父 Z1 继续为 BLOCKED_DEPENDENCY，Z2 及以后阶段保持 NOT_RUN。

## 内核改动

- CellTypeParameters 新增默认关闭的 reference_shape_modulus，单位 N/m；
- Cell 新增显式 capture_reference_geometry / clear_reference_geometry、参考边长—面积权重和 reference_shape_energy；
- 内部力路径新增与参考能量工作共轭的解析边力；
- 缺失参考态、退化边或拓扑变化失败关闭；
- 加速 hot path 在参考模量非零时回退到 Python 参考路径；完整 native step 在迭代零前拒绝，避免漏算；
- XML 参数解析和细胞类型克隆已同步；
- 新增 7 项聚焦测试；muse_dcm 全单元套件 141 passed、5 个既有预期 skip，旧内力 parity 通过。

参考态捕获不会在加载任意网格时自动执行，因此观察到的形状不会被静默宣布为无应力态。重网格或分裂后的参考态转移尚未实现；这些拓扑操作不得与本项同时启用。

## 冻结输入

- 等体积半径 R0=4.5e-6 m；
- 三档 icosphere：80/320/1280 面；
- 心肌合成比例 3:1:1，长轴 x；
- 心内膜合成比例 4:4:1，厚度法向 z；
- 合成参考模量 5e-4 N/m；
- 体积、表面张力、全局面积、弯曲、接触、主动、ECM 和流体关闭；
- CPU 最多 4 线程，0 GPU、0 网络、0 安装。

## 通过结果

- 最差最佳方向导数相对误差 1.010424e-9，门限 1e-6；
- 最大刚体/合力合矩残差 4.799699e-13，门限 1e-10；
- 最大 medium→fine 归一化方向刚度变化 5.682041e-3，门限 5%；
- 卸载最终最大 RMS 边应变 2.848161e-7，门限 1e-6；
- 卸载最终最大主轴长度误差 2.206040e-5，门限 1e-4；
- fine 5% 结构方向刚度比：心肌长轴/横向 2.202276，心内膜面内/厚度 1.427856。

上述方向刚度差来自非球形参考几何的结构响应；参考材料模量本身仍为各向同性。

## 版本历史

- v01 保留为 FAIL_NUMERICAL：最速下降卸载器在 2000 次内收敛不足，其余门通过；
- v02 保持相同物理与阈值，改用带线搜索的 L-BFGS 后数值通过；
- v03 只修复卸载图横轴标签重叠，数值未改；
- v04 在内核补充加速后端失败关闭策略后重新运行并作为最终包。

## 证据入口

- 离线入口：results/ventricle_z1/z1b_v04_20260911/index.html；
- 模型结构：figures/z1b_model_structure.png；
- 方向响应：figures/z1b_directional_response.png；
- 卸载恢复：figures/z1b_unload_recovery.png；
- 机器摘要：summary.json；
- 独立复核：verification/independent_verification.json；
- 本构审计：constitutive_audit.md；
- 命令和测试：commands.md、test_report.json。

## 下一门

Z1-C 受控双细胞接触、多细胞拥挤桥接、Z2 和任何 GPU 工作均未授权。本轮在 Z1-B 参考态结果交付后停止。
