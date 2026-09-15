---
document_id: PRL-VENTRICLE-SIMUCELL3D-KERNEL-MIGRATION-PRECHECK-CONTRACT-V01
status: frozen
prepared_at: 2026-09-12
stage: Z1-TF2-M0
decision: project_control/ventricle_simucell3d_kernel_transition_decision_v01.md
execution_status: authorized
authorization: project_control/ventricle_simucell3d_kernel_migration_precheck_authorization_v01.md
---

# Z1-TF2-M0｜SimuCell3D 换核资格门合同 v01

## 1. 目的与停止点

在不进入 Z1-TF2-B 的条件下，验证 PRL 受控 SimuCell3D 核心是否具备承接“心肌 DCM—可变形 ECM DCM—心内膜 DCM”路线的最小可执行能力。该门只回答内核、适配接口、守恒、约束和可观测性是否闭合；不回答长期组织成形、生理参数或主动周期是否成功。

## 2. 固定实现范围

- 直接链接 `external/simucell3d/`，不得复制核心源码；
- 使用新的最小 PRL 心室适配层，显式分离对象角色与运动学约束；
- ECM 必须可变形；夹持仅作用于预登记的边界顶点；
- 心肌/心内膜逐边参考态膜能为 0；
- 允许面积、体积、皮质张力、弯曲、接触、腔面压力和零合力/零合矩方向性胞内载荷；
- 固定拓扑、CPU 最多 4 线程、累计正式运行墙钟不超过 600 s；
- 输出坐标是算法延拓坐标，不是物理时间。

## 3. 冻结子门

| 子门 | 预登记判据 |
|---|---|
| `M0-SOURCE` | 记录 PRL HEAD、SimuCell3D 来源和修改哈希；MSVC Release 构建成功；当前受控 fork 测试全通过或逐项冻结非本轮原因 |
| `M0-ROLE-MOBILITY` | ECM 对象以 `deformable` 运动学推进且有非零有限位移；固定顶点位移 `<=1e-14`（模型长度单位） |
| `M0-LOAD` | 腔压合力与有向投影面积积分相对误差 `<=1e-12`；方向性胞内载荷的净力及以细胞质心计净矩相对残差均 `<=1e-10` |
| `M0-CONTACT` | 至少一个细胞—ECM 接触对产生非零有限界面力；作用—反作用相对残差 `<=1e-10`；不得用独立跨空隙弹簧冒充接触 |
| `M0-STEP` | 所有自由节点、力、曲率、压力和几何量有限；接受步中工作—耗散相对误差 `<=1e-10`；固定拓扑的节点/面数和持久 ID 不变 |
| `M0-TRILAYER` | 构造 `4×4 + 1 + 4×4` 的 33 个闭合对象；心肌与心内膜不得直接接触；同层及细胞—ECM 接触账本非空 |
| `M0-OUTPUT` | 保存真实网格和 `0,0.25,0.5,0.75,1.0` 五个延拓点；结构图及曲率、压力、节点力/界面牵引图来自保存状态并通过独立文件复核 |

所有相对残差的分母均使用相应绝对贡献和与机器安全下限的较大者。若量级为零，必须同时报告绝对残差，不能以除零或 NaN 判 PASS。

## 4. 输出合同

正式结果使用新建目录：

`results/ventricle_z1/z1tf2m0_simucell3d_migration_v01_20260912/`

至少包含：

- `summary.json`、`report.md`、`provenance.json`、`commands.md`；
- 五个延拓点的原始网格/节点场与接触账本；
- `model_structure.png`、`continuation_snapshots.png`；
- `curvature_fields.png`、`pressure_fields.png`、`force_traction_fields.png`；
- 独立验证报告和离线 `index.html`。

图片中的“应力”只允许标为表面牵引或面积归一节点力；当前薄壳/曲面内核没有被验证的三维 Cauchy 应力张量。

## 5. 互斥裁决

- `passed_migration_precheck`：全部冻结子门通过，只允许起草 Z1-TF2-B 的 SimuCell3D 合同；
- `blocked_dependency`：编译器/依赖或当前核心缺少不可在本门内安全建立的必要接口；
- `failed`：已有能力在守恒、约束、拓扑、数值或输出门失败；
- `not_run`：正式运行没有开始。

任何通过都不证明长期稳定、生理有效、细胞形态已自发形成、主动收缩有效或父 Z1 已解决。

## 6. 权限与资源

- 用户已授权一次本合同范围内的 create-only CPU 执行；
- 不使用 GPU、Docker、网络、后台服务，不安装或升级软件；
- 不删除、覆盖或改名既有文件和结果包；
- 允许在 `external/simucell3d/` 做本资格门所需的最小、可测试、来源可追踪修订；
- 遇到需要扩大为完整求解器重构、恢复已退役旧栈或进入 Z1-TF2-B 时停止并另行裁决。

