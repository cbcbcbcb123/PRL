# PRL｜三维细胞分辨心室 Codex 阶段执行包 v03

**日期：2026-09-10。19 份阶段 MD（含控制入口与子门）+ 6 份公共说明 + JSON/CSV 模板；全部计算状态 NOT_RUN。** 本包不包含已生成的模拟动画或求解结果；它规定 Codex 在每个阶段必须交付哪些真实可视化与数值证据。

## 1. 怎样开始

将整个目录放进实际 PRL 工作区的合适位置，例如 `project_control/ventricle_stage_contracts_v03/`。这是建议位置，不代表当前目录已存在，也不是要求重新组织整个工程。保留原始 MD 与模板，结果由 Codex 写入阶段独立运行目录。

第一次只交给 Codex 下面这段话（目录位置按实际放置路径，或在已打开工作区按文件名定位）：

```text
请读取这套阶段执行包的 00_README_START_HERE.md、01_GLOBAL_EXECUTION_CONTRACT.md、
02_VISUALIZATION_AND_DATA_CONTRACT.md、03_VALIDATION_METRICS.md，
然后只执行 stages/Z0_ENTRY_DATA_AND_KERNEL_AUDIT.md。

先确认当前 PRL 工作区和唯一 muse_dcm 的真实位置，保护已有用户修改和失败包。
按 Z0 合同完成内核/资料审计、静态几何检查、可旋转离线模型入口和 Z1 执行合同。
请实际完成授权工作，不要只给新计划；不得启动主动收缩、CFD、泵血或 Z1。

必须给我可实际打开的 HTML 路径、静态图/几何检查证据、数据缺项表和运行/检查记录。
数据或依赖缺失就按合同记录阻断，不能编造结果、单位、配准或 PASS。
结束时提交 Z0 验收报告和 Z1 合同，然后停止。
```

后续将阶段文件替换成用户明确选择的那一份，仍一次一个阶段。每份执行 MD 都含前置证据、边界/禁止项、具体实验、执行顺序、主要读出、可视化表、验收和停止规则。共同公式/单位/文件语义由公共合同统一，避免多份 MD 演化成相互冲突的模型。

## 2. 阶段索引

| 阶段 | 独立文件 | 类型 | 计算状态 |
|---|---|---|---|
| Z0 | [资料、内核审计与可旋转模型入口](stages/Z0_ENTRY_DATA_AND_KERNEL_AUDIT.md) | 单阶段执行 | NOT_RUN |
| Z1 | [被动单细胞与双细胞力学](stages/Z1_PASSIVE_SINGLE_AND_DOUBLE_CELL.md) | 单阶段执行 | NOT_RUN |
| Z2 | [主动单细胞：自由缩短、固定端与有限负载](stages/Z2_ACTIVE_SINGLE_CELL.md) | 单阶段执行 | NOT_RUN |
| Z3 | [ECM 黏弹网络：内变量、剪切与离散标定](stages/Z3_ECM_VISCOELASTIC_NETWORK.md) | 单阶段执行 | NOT_RUN |
| Z4 | [有限双层组织：层间传递、局部扰动与边缘效应](stages/Z4_FINITE_BILAYER_TISSUE.md) | 单阶段执行 | NOT_RUN |
| Z4b | [无 CFD 共同腔面与被动受压](stages/Z4b_WATERTIGHT_CAVITY_AND_PRESSURE.md) | 单阶段执行 | NOT_RUN |
| Z5 | [独立 CFD：固定规则边界与解析/制造解](stages/Z5_FIXED_GRID_CFD.md) | 单阶段执行 | NOT_RUN |
| Z6 | [移动边界 CFD 总控制入口](stages/Z6_MOVING_BOUNDARY_CONTROLLER.md) | 控制入口 | NOT_RUN |
| Z6a | [切割几何与壁面扫掠：先不求流体](stages/Z6a_CUT_GEOMETRY_AND_SWEEP.md) | 单阶段执行 | NOT_RUN |
| Z6b | [固定曲壁 CFD：切割算子、牵引与壁面剪切](stages/Z6b_FIXED_CURVED_WALL_CFD.md) | 单阶段执行 | NOT_RUN |
| Z6c | [移动边界 CFD：规定运动、单元生灭与活塞排液](stages/Z6c_MOVING_WALL_CFD.md) | 单阶段执行 | NOT_RUN |
| Z7 | [被动双向流固耦合：牵引、虚功与时间状态](stages/Z7_PASSIVE_TWO_WAY_FSI.md) | 单阶段执行 | NOT_RUN |
| Z8 | [主动理想心室泵血：短管、椭球、负载与强对照](stages/Z8_ACTIVE_IDEAL_VENTRICLE_PUMP.md) | 单阶段执行 | NOT_RUN |
| Z9 | [斑马鱼数据比较总控制入口](stages/Z9_DATA_VALIDATION_CONTROLLER.md) | 控制入口 | NOT_RUN |
| Z9a | [实测壁运动驱动的条件性 CFD 比较](stages/Z9a_PRESCRIBED_WALL_DATA_COMPARISON.md) | 单阶段执行 | NOT_RUN |
| Z9b | [主动预测：参数可辨识性与保留数据检验](stages/Z9b_ACTIVE_PREDICTION_AND_IDENTIFIABILITY.md) | 单阶段执行 | NOT_RUN |
| Z10 | [心肌单次受控分裂与材料状态继承](stages/Z10_SINGLE_MYOCARDIAL_DIVISION.md) | 单阶段执行 | NOT_RUN |
| Z10b | [可选扩展：直接涉及腔面拓扑的心内膜分裂](stages/Z10b_ENDOCARDIAL_TOPOLOGY_EVENT_OPTIONAL.md) | 可选扩展 | NOT_RUN |
| Z11 | [ECM 分泌、降解与沉积参考态](stages/Z11_ECM_SECRETION_DEGRADATION_AND_MEMORY.md) | 单阶段执行 | NOT_RUN |

## 3. 默认顺序与子门

```text
Z0 → Z1 → Z2 → Z3 → Z4 → Z4b → Z5
   → Z6 [审计/控制入口] → Z6a → Z6b → Z6c → 汇总 Z6
   → Z7 → Z8
   → Z9 [数据分级/控制入口] → Z9a → Z9b → 汇总 Z9
   → Z10 → Z11

Z10b：涉及腔面拓扑的可选扩展，须 Z10 之后单独授权；不是 Z11 前置。
```

这只是默认执行次序，不把不相关模块假设为物理依赖。Z5 独立 CFD 不需要调用 DCM；Z3 可独立做网络材料试验。Z9 数据缺失只阻断对应实验主张，合成 Z10/Z11 满足真实数值依赖后可以另行授权，但不能自动跳过阶段。

Z6 与 Z9 的主文件是**控制入口**，不授权一次跑完所有子门。Z4b、Z6a/b/c、Z9a/b、Z10b 拆开，是为了每次有明确的可检查结果和停止点。

## 4. 六份公共说明

| 文件 | 用途 |
|---|---|
| [本文件](00_README_START_HERE.md) | 起步指令、阶段索引和执行顺序 |
| [总执行合同](01_GLOBAL_EXECUTION_CONTRACT.md) | 权限、唯一内核、预算、状态/回退和变更 |
| [可视化与数据合同](02_VISUALIZATION_AND_DATA_CONTRACT.md) | 真网格、离线 HTML、交互/同步、字段、原始数据和失败展示 |
| [指标与验收](03_VALIDATION_METRICS.md) | 单位、能量/质量/虚功、收敛、事件和材料账本 |
| [来源与变更](04_REFERENCES_AND_PROVENANCE.md) | 资料核查边界、各论文用途、v02→v03 扩展 |
| [报告与变更模板](05_REPORT_AND_CHANGE_TEMPLATES.md) | Codex 阶段报告、机器摘要、失败包、变更请求 |

原 v02 保存在 [sources/v02_original.md](sources/v02_original.md)，不覆盖原文。模板目录中的 null/空表是待填字段，不是模拟结果；具体 CLI 由实际项目审计后生成，不预设一个不存在的命令。

## 5. 每阶段最低可视化承诺

每个实际阶段都有离线模型/网格入口、至少一张定量验收图、原始数据和日志；适用时有真实网格动画、选细胞/连接/单元、剖切、透明、字段色标、同物理时间曲线游标。无动力学阶段只显示真实静态检查/几何扫描，不制造压力/流量曲线。

失败也有页面：最后有效状态、首次异常对象和残差。未启用字段不填零。节点力不写应力，ECM 连接不冒充完整三维应力场，规定壁运动不冒充主动耦合，实验插值不冒充测量。

合同包内的 `index.html` 只是**文档导航**，可离线查看各份 MD 的预览，不是模拟驾驶舱。真正阶段结果的 HTML 必须由 Codex 从实际运行产物生成。

## 6. 执行保护与通过范围

默认 CPU、有上限预检、预算冻结、独立验证和一次一阶段。新增工程测试幅度/阈值是合成默认值，不是生理参数，正式前登记；已有批准定义不能被静默覆盖。

没有真实计算不生成 PASS。即便物理子项通过，交付查看器缺失也要单列；有合成证据但缺实验数据，不声称生物验证。完整阶段矩阵都在 [stage_manifest.json](stage_manifest.json) 中，初始状态一致为 NOT_RUN。
