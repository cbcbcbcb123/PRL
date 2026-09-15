---
document_id: PRL-VENTRICLE-Z1C-CONTROLLED-CONTACT-CONTRACT-V01
status: frozen
frozen_at: 2026-09-11
stage: Z1-C
parent_stage_status_before_run: BLOCKED_DEPENDENCY
---

# Z1-C 受控双细胞接触合同 v01

## 目标与裁决范围

在 Z1-B 已通过的显式非球形参考态上，验证唯一 `E:\MeshCell3D\code\muse_dcm` 的 spring-contact 路径能否完成可逆的规定运动接近—黏附—压入—分离，并保持作用反作用、合力合矩、能量—力共轭、ID 交换不变性和网格趋势。

本合同裁决的是**双细胞接触本构切片**，通过状态记为 `PASS_CONTACT_CONSTITUTIVE`。规定运动参数不是物理时间，不能据此声称动态松弛、组织稳定、生理接触强度或 Z1 整体通过。旧 C6 动态子步失败、弯曲梯度和全局能量导出仍单独保留。

## 唯一内核与写入边界

- `E:\MeshCell3D\code\muse_dcm` 是唯一 DCM 内核；本轮默认只读调用现有接触和 Z1-B 参考态路径；
- PRL 只保存本合同、授权、验证脚本、预登记、原始快照、结果、独立复核和图片；
- 若预检表明必须修改 MeshCell3D 接触内核，停止并记为 `BLOCKED_DEPENDENCY`，不得在 PRL 复制第二套内核；
- CPU 最多 4 线程、墙钟 600 s、0 GPU、0 安装、0 网络、0 提交或发布。

## 冻结对象与接触路径

三档闭合 icosphere 为 80、320、1280 面，等体积半径 `R0=4.5e-6 m`。使用：

1. 球—球 x 向对照；
2. `3:1:1` 心肌探针端对端；
3. `3:1:1` 心肌探针侧对侧；
4. `4:4:1` 心内膜探针边对边；
5. `4:4:1` 心内膜探针对面。

参考形状模量固定为 `5e-4 N/m`，体积模量固定为 `6000 Pa`；表面张力、全局面积弹性、弯曲、主动、ECM 和流体关闭。接触使用 exact node-face 距离、`c=4.5e-7 m`、`alpha=2.5e8 Pa/m`、`beta=1.0e9 Pa/m`，黏附和排斥缩放均为 1。

规定运动以载荷参数 `lambda` 表示，不是物理时间：名义表面间隙从 `1.25c` 线性变化至 `-0.20c`，轴向压缩从 0 线性变化至 `5e-4`，再沿同一路径卸载。该小压缩用于让实际体积压力和参考膜面力可见，同时保持最大体积变化不超过 `1e-3`。

## 冻结门

1. **LAW**：独立分段公式与 `spring_contact_traction` 在冻结采样点的相对/尺度误差 `<=1e-14`；
2. **FAR**：`1.25c` 状态 active contact 为 0，接触力绝对值 `<=1e-24 N`；
3. **ACTIVE**：每种方向在加载路径中均出现黏附和排斥接触；
4. **BALANCE**：每个活动状态的归一化净接触力、净接触力矩和逐对平衡残差均 `<=1e-10`；
5. **ID-SWAP**：交换两个细胞 ID 后，峰值反力、能量、活动接触数和场统计的相对/尺度差 `<=1e-10`；
6. **REVERSIBILITY**：同一 `lambda` 的加载与卸载几何、反力、接触能和场统计相对/尺度差 `<=1e-12`；
7. **WORK-CONJUGACY**：避开分段拐点，对总独立势能作中心差分，与实际总节点力对规定运动的投影比较；每例最佳相对误差 `<=1e-5`；
8. **VOLUME/PRESSURE**：最大相对体积变化 `<=1e-3`，内核压力与 `K ln(V0/V)` 相对/尺度差 `<=1e-12`；
9. **REFINE**：峰值反力以参考面积和接触尺度归一，medium→fine 相对变化 `<=5%`；
10. **FIELDS**：核心离散节点曲率、参考度量膜面力合量、压力和接触牵引全部来自同一保存状态，数值有限、单位和定义明确；无膜厚时禁止把 N/m 膜面力合量称为 Pa 三维应力；
11. **VISUAL**：输出真实网格结构、网格力学场、力—间隙曲线和验收图；定量图沿用已确认 `10×5 in` 主轴框并通过 CB 风格验证；
12. **BUDGET**：在冻结 CPU/墙钟范围内完成。

任一必需门失败则 Z1-C 为 `FAIL_NUMERICAL`；缺失依赖为 `BLOCKED_DEPENDENCY`。即使全部通过，父 Z1 仍须处理弯曲/全局能量账本和动态接触稳定性，不能自动进入多细胞桥接或 Z2。

## 冻结输出

- `contact_path.csv`、`gradient_check.csv`、`mesh_refinement.csv`、`id_swap.csv`、`field_statistics.csv`；
- `mechanical_fields.npz` 和代表状态网格快照；
- `figures/z1c_model_structure.*`；
- `figures/z1c_mesh_mechanical_fields.*`；
- `figures/z1c_contact_response.*`；
- `figures/z1c_validation_overview.*`；
- `summary.json`、`report.md`、`index.html`、命令日志及独立验证结果。

