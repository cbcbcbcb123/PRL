---
document_id: PRL-VENTRICLE-SIMUCELL3D-TRILAYER-SHAPE-FORMATION-EXECUTION-RECORD-V01
status: completed
completed_at: 2026-09-12
stage: Z1-TF2-B
outcome: failed_numerical
decision: FAIL_Z1_TF2B_NUMERICAL
contract: project_control/ventricle_simucell3d_trilayer_shape_formation_contract_v01.md
result: results/ventricle_z1/z1tf2b_simucell3d_shape_formation_v01_20260912/summary.json
next_stage: Z1-TF2B_REPAIR_NOT_RUN_NOT_AUTHORIZED
---

# Z1-TF2-B｜SimuCell3D 致密三层形态形成与维持筛查执行记录 v01

## 结论

唯一一次正式 `2 × 7 = 14` 轨迹矩阵已经完成调度并冻结。最终互斥裁决为 **`failed_numerical`**：只有 FORMATION/MAINTENANCE 的两个 `NO_LUMEN` 轨迹到达 `λ=1,s=1`；其余 12 个保留腔压的轨迹均触发冻结的心内膜体积停止门。共同数值门不成立，因此形成、维持、镜像和机制消融形态门均为 `not_run`，不得把局部外观或 MAINTENANCE 初始形态记为科学 PASS。

这不是 SimuCell3D M0 换核资格的回退。M0 只证明了内核构建、一步载荷/接触与输出账本可以工作；本轮证明当前 TF2-B 参数和粗网格接触离散不足以支持长期三层筛查。

## 实际模型与实现边界

- 每个试验臂包含 16 个心肌细胞、1 个闭合且可变形 ECM 表面和 16 个心内膜细胞，共 33 个闭合对象；
- FORMATION 从角色特异的体积等效近球面起步；MAINTENANCE 从 M0 长轴/扁平几何施加确定性 2% 表面扰动后起步；
- 心肌与心内膜只使用标量 `A^3/V^2` 面积储备、皮质张力、弯曲和体积项，`reference_edge_shape_terms=0`，没有方向性参考边或参考面；
- 核心 `contact_face_face_via_coupling` 负责当前网格面—面排斥与法向/曲率更新；PRL 适配层调用同一 SimuCell3D 节点—三角面最近点定义，在实际距离 `<=0.35` 的接触区动态装配 `0.04` 黏附力并逐作用施加等大反力。它不保存跨空隙永久弹簧，也未修改 `external/simucell3d/`；
- 心肌方向载荷经刚体模态投影，逐细胞净力和净矩为零；心内膜腔面施加有向 `0.50` 牵引；组织两端夹持有限顶点区；
- 每条完整轨迹执行 240 步并保存 9 个状态；发生 `>10%` 体积误差时立即停止向更高载荷推进。

## 正式矩阵结果

| 试验臂 | 完整轨迹 | 数值中止 | 中止位置与原因 |
|---|---:|---:|---|
| FORMATION | `NO_LUMEN` 1 条 | 6 条 | 全部在全局步 90；心内膜体积误差 `10.037%–10.070%` |
| MAINTENANCE | `NO_LUMEN` 1 条 | 6 条 | 全部在全局步 84–85；心内膜体积误差 `10.090%–10.151%` |

所有 `FULL`、`FULL_MIRROR`、`NO_DIRECTIONAL_SUPPORT`、`NO_CELL_ECM_ADHESION`、`NO_SAME_LAYER_ADHESION` 和 `SOFT_ECM` 均保留腔压并以同一失败模式中止。这个跨镜像、跨起始几何和跨其余消融的稳定模式，把首要失败归因限定为当前腔压幅值与体积/面积支撑组合不相容，而不是某个单独黏附或方向载荷开关。

## 共同数值门与部分形态观察

- 两个完整 `NO_LUMEN` 轨迹的网格均保持 33 个闭合对象、0 开边、0 非流形边、0 翻面、持久 ID 稳定；固定点最大位移分别为 `0` 和 `1.135e-21`；最小三角角分别为 `19.291°` 和 `19.366°`；直接心肌—心内膜接触为 0；
- FORMATION/`NO_LUMEN` 末态细胞最大体积误差为 `1.400%`，MAINTENANCE/`NO_LUMEN` 为 `2.018%`，均通过 5% 末态体积门；
- 接触、黏附、主动净力/净矩、压力积分与工作—耗散的独立相对残差均保持在冻结容差内；
- 但两个完整轨迹的末态/历史峰值自由力比分别为 `0.1651` 和 `0.4957`，均未达到 `<=0.05`；
- FORMATION 的中央联合接触占有率未达到 `0.80`。当前 80 面近球粗网格在冻结中心距下的节点—面最小距离约 `0.484`，高于 `0.35` 截断；几何表面看似拥挤或穿入，不等于当前接触离散成功捕获同层界面；
- 完整 FORMATION/`NO_LUMEN` 末态中央中位 `E_m=1.0197706`、`F_e=1.0052986`，远低于 `1.20/1.50` 形态门；
- 完整 MAINTENANCE/`NO_LUMEN` 末态中央中位 `E_m=1.4290913`、`F_e=2.2507887`。这些值描述从预制长/扁形态出发的部分保持，但因共同收敛门失败且关键消融末态不存在，不得裁决为维持 PASS。

## 复核、图片与来源链

- Release 适配层构建成功；聚焦 verifier/合同测试 `9/9 passed`；受控 SimuCell3D Release CTest `134/134 passed`；
- 正式矩阵仅执行 `1/1` 次，CPU 最多 4 线程、0 GPU，墙钟 `94.399 s`；正式前后 SimuCell3D 源树哈希均为 `e25abc3f40af6a27a14f7ff39b1e13d52bd62fc7cc87a1b86bee06d5c12d672d`；
- artifact-only 验证器不导入或执行 SimuCell3D，独立重算闭合性、边二重性、翻面、体积、面积、最小角、面积加权形状张量、方向、接触、夹持位移和各力账本；
- 七组 PNG/SVG 均通过文件检查并已人工视觉检查。缺失的 `λ=0.75/1` 与保持段状态在时间点图中明确留空，未插值；
- `render_manifest.json` 保存图片哈希及其节点、面、力、接触和独立指标来源哈希；图中面积归一节点力始终标为 traction proxy，不称为 Cauchy stress。

## 下一步边界

下一阶段不是直接增加周期力，也不是放宽体积、接触或收敛门。最小修订合同应先分成两个正交资格片：

1. **P–V 支撑标度资格片**：在单层/单细胞和受限三层小体系内确定 `0.50` 腔面牵引与当前 `bulk/area` 支撑为何在 84–90 步造成 >10% 体积损失；候选修订必须重新冻结并用压力积分、体积响应和能量账本验证；
2. **粗网格接触捕获资格片**：在不扩大 `0.35` 截断、不允许跨隙永久弹簧的前提下，比较网格加密、接触一致的初始布置或经验证的面—面距离捕获，使近球 FORMATION 的同层实际接触被识别。

这两个修订片均为 **NOT_RUN / 未授权**。不得复用或覆盖本正式结果目录，不自动进入新的 TF2-B 正式矩阵、周期收缩、Z2、CFD 或 FSI。

## 权限与工作区边界

本轮未使用 GPU、Docker、网络、软件安装、后台 worker、外部发布、提交或推送，也未删除任何文件。构建目录和三个烟雾目录继续保留；清理前必须另列绝对路径并取得用户确认。项目工作树原有的 SimuCell3D 受控兼容修订继续存在，但正式矩阵前后源树哈希一致，本轮没有追加核心修改。

## 入口

- 离线结果页：`results/ventricle_z1/z1tf2b_simucell3d_shape_formation_v01_20260912/index.html`
- 机器摘要：`results/ventricle_z1/z1tf2b_simucell3d_shape_formation_v01_20260912/summary.json`
- 独立复核：`results/ventricle_z1/z1tf2b_simucell3d_shape_formation_v01_20260912/verification/independent_verification.json`
- 视觉 QA：`results/ventricle_z1/z1tf2b_simucell3d_shape_formation_v01_20260912/visual_qa.json`
- 来源与命令：`results/ventricle_z1/z1tf2b_simucell3d_shape_formation_v01_20260912/provenance.json`、`commands.md`
