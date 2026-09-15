---
document_id: PRL-VENTRICLE-Z1C-CONTACT-REPAIR-EXECUTION-RECORD-V02
status: current
executed_at: 2026-09-11
stage: Z1-C-REPAIR
substage_status: PASS_CONTACT_CONSTITUTIVE
parent_stage_status: BLOCKED_DEPENDENCY
---

# Z1-C 接触离散修复与原门重跑记录

## 1. 授权与实现边界

用户授权“同意，继续下一步，先修复”。依 [修复授权](ventricle_z1c_contact_repair_execution_authorization_v01.md) 与最终冻结的 [修复合同 v03](ventricle_z1c_contact_discretization_repair_contract_v03.md)，本轮修改唯一 `E:\MeshCell3D\code\muse_dcm`，PRL 不复制第二套内核。未使用 GPU、网络或安装；未提交、推送、发布，也未进入多细胞桥接或 Z2。

v01 参考顶点面积和 v02 面/PN 面求积均未消除各向异性端部的力学网格依赖，故保留为失败诊断谱系。v03 增加 `symmetric_reference_quadric_proxy`：球/椭球参考态使用固定 1280 面共同接触代理，代理节点以仿射完备权重映射到当前力学网格，参考顶点双对偶面积保持固定，力按同一映射回传。既有 `legacy_target_face_all` 默认路径保持不变。

该模式只覆盖严格正定拟合的球形/椭球参考态，不是任意非椭球、重塑后表面或组织级接触的一般解。

## 2. 聚焦工程验证

- 新接触代理测试共 8 项通过：缺失参考态失败关闭、独立能量—力工作共轭、ID 交换、逐对平衡/唯一接触，以及五种方向完整加载路径的黏附—排斥激活与峰值网格细化；
- 既有 spring 接触与参考态力学回归 26/26 通过；
- CPU 路径完成。CuPy 仅报告未检测到 CUDA path，本轮未调用 GPU；
- MeshCell3D Git HEAD 保持 `fa21321b80a371f107afd398f93d7f69508e20c6`，修复位于未提交工作树；没有把未运行的全套 CI、GPU 或发布认证写成通过。

## 3. Z1-C 原冻结门重跑

正式 create-only 结果为 [z1c_v08_20260911](../results/ventricle_z1/z1c_v08_20260911/index.html)。五种工况、三档力学网格和原阈值未改变；11 个加载/卸载路径点全部保存，`lambda` 仍是规定路径参数而非真实时间。

13 个门全部通过，Z1-C 裁决为 **PASS_CONTACT_CONSTITUTIVE**：

- 最差工作共轭误差 `1.7104664618725823e-08 <= 1e-5`；
- 最大 medium→fine 全路径峰值反力变化 `0.012829612934447308 <= 0.05`；
- 最大合力/合矩平衡误差 `9.29855773616632e-15 <= 1e-10`；
- 最大体积相对变化 `5.000000000001516e-4 <= 1e-3`；
- 压力公式误差 `0`，ID 交换误差 `0`，卸载可逆误差 `0`；
- 五个工况均实际激活黏附与排斥，远距接触力为 `0`；
- 正式运行耗时 `199.5141043 s <= 600 s`，CPU 最多 4 线程，GPU 0。

独立验证为 `PASS_VERIFICATION`，重算上述裁决并核对 runner、内核文件、配置和图像哈希。两张定量图样式清单通过；七张最终图人工验收为 `PASS_VISUAL_QA`。

## 4. 可追溯实现与结果

- runner：`scripts/run_ventricle_z1c_v07.py`，SHA-256 `75d8adf931d0d9dec9dad3466db895e529f965341226d80ce26511716a8496d9`；
- verifier：`scripts/verify_ventricle_z1c_v07.py`；
- 接触实现：`E:\MeshCell3D\code\muse_dcm\engine\mechanics\contact_spring.py`，SHA-256 `b2545b3e5c16569faab584a6e65b7677048d25372175494bc2eab0221c49bce0`；
- 网格参考态实现：`E:\MeshCell3D\code\muse_dcm\engine\core\mesh.py`，SHA-256 `b641596022651615cb0b19e2b37dcb4085363a4f017840097935adf5bd0a59d3`；
- 汇总：`results/ventricle_z1/z1c_v08_20260911/summary.json`；
- 独立复核：`results/ventricle_z1/z1c_v08_20260911/verification/independent_verification.json`；
- 视觉验收：`results/ventricle_z1/z1c_v08_20260911/visual_qa.json`。

首次通过包 v07 在运行后遇到共享工作树的无关配置漂移：新增 `legacy_division_check_interval_steps` 使当前精确配置哈希不再等于预注册值。移除该单行可逐字节恢复 v07 的冻结哈希，且七张 PNG 与 v08 全部同哈希；但没有放宽验证器。v07 当前复核保留 `FAIL_CONFIG_HASH_DRIFT`，v08 在新的冻结哈希下完整重跑并取得 `PASS_VERIFICATION`，因此 v08 是正式入口。

## 5. 科学裁决边界与下一步

本 PASS 只证明规定运动、合成参数和严格球/椭球参考态下的接触本构切片。它不证明动态子步收敛、生理标定、组织连续性、弯曲正确性、多细胞稳定性或 Z2。

父 Z1 因既有弯曲梯度、完整能量导出及组合内力账本仍为 **BLOCKED_DEPENDENCY**。下一步应先处理这些父阶段依赖并形成单独合同；多细胞桥接和 Z2 仍为 **NOT_RUN / 未授权**。
