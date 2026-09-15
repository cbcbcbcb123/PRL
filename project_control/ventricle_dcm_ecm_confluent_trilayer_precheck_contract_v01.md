---
document_id: PRL-VENTRICLE-DCM-ECM-CONFLUENT-TRILAYER-PRECHECK-CONTRACT-V01
status: frozen
prepared_at: 2026-09-12
stage: Z1-TF2-A
decision: project_control/ventricle_cell_geometry_strategy_decision_v05.md
execution_status: authorized
authorization: project_control/ventricle_dcm_ecm_confluent_trilayer_precheck_authorization_v01.md
---

# Z1-TF2-A｜DCM-ECM 原语与连续三层几何预检合同 v01

## 目的和停止点

在不修改细胞参考形状、不进入主动周期的前提下，确认唯一 `muse_dcm` 是否能把 ECM 作为独立闭合 DCM 薄层实体，并通过实际表面接触与两层细胞传递法向和切向作用。该子门只建立可执行原语与合成几何，不以漂亮形态替代材料或组织验证。

本合同已由用户于 2026-09-12 明确授权执行，授权记录见 `project_control/ventricle_dcm_ecm_confluent_trilayer_precheck_authorization_v01.md`。执行仍不得修改 `E:\MeshCell3D`、使用 GPU、跨入主动周期或覆盖既有结果包。

## A. 固定对象与类型

| 对象 | DCM 数量 | 初始几何 | 关闭项 | 主要力学 |
|---|---:|---|---|---|
| 心肌 | `4×4` 闭合细胞 | 受限铺砌、纤维方向沿 x | 生长、分裂、参考形状膜能 | 体积、总面积、皮质、弯曲、黏附/排斥、方向性胞内承载 |
| ECM | `1` 个连续闭合薄层实体 | 有顶面、底面和边缘的薄板 | 生长、分裂、细胞周期 | surface-only 基线；必要时独立裁决 ECM 材料参考/黏弹分支 |
| 心内膜 | `4×4` 闭合细胞 | 受限铺砌、腔面/基底面可识别 | 生长、分裂、参考形状膜能 | 体积、总面积、皮质、弯曲、黏附/排斥 |

初始几何必须报告每对邻居的最小间隙、接触截断、接触面积分数和邻居数。中心距大于直径且表面间隙超过接触截断的球阵列不得进入组织预检。

## B. 接触矩阵

| 源—目标 | 主相互作用 | 说明 |
|---|---|---|
| 心肌—心肌 | adhesion + repulsion | 固定首轮邻接身份，但力来自实际接触面 |
| 心内膜—心内膜 | adhesion + repulsion | 形成连续腔面所需的侧向接触 |
| 心肌—ECM | adhesion + repulsion | 允许有限切向滑移；记录面积、间隙、牵引和功 |
| 心内膜—ECM | adhesion + repulsion | 同上 |
| 心肌—心内膜 | ignore | ECM 必须隔开两层 |
| 任一对象—自身非邻面 | self-contact audit | 若内核不支持，预检必须证明本矩阵不会触发自穿透 |

节点强耦合只作为单独 `TIED_LIMIT` 对照，不与主相互作用混用。

## C. 必需原语检查

1. `ECM-CLOSED`：闭合、有向、无重复/非流形边；顶、底、边缘面标签完整。
2. `ECM-RIGID`：整体平移和非坐标轴旋转不改变内部能；内力合力/合矩满足既有代数门。
3. `ECM-NORMAL`：小幅法向压缩/拉伸，输出反力、体积、面积、弯曲和网格质量。
4. `ECM-SHEAR`：顶底相对切向位移；测可分辨切向刚度。若 surface-only 分支在细化后趋于零，记录 `not_solid_support`，不得调参伪造通过。
5. `CELL-ECM-CONTACT`：一个细胞接近—黏附—压缩—分离；检查作用反作用、功共轭、穿透和网格依赖。
6. `TRILAYER-GEOMETRY`：构造 `4×4 + 1 + 4×4` 致密三层初始状态，只做几何/接触账本，不施加腔压。
7. `PRESSURE-PATH`：仅在前六项通过后，以小幅延拓检查腔面压力是否通过心内膜—ECM—心肌传递；该坐标不是物理时间。

## D. 分支裁决

- `surface-only_supported`：surface-only ECM 在法向、剪切、弯曲和细化门均有稳定非零响应，可进入下一静态三层筛查。
- `requires_ecm_material_reference`：几何与接触通过，但 surface-only ECM 缺少目标所需剪切支撑；下一步须冻结 ECM 专属材料参考度量或黏弹内变量合同。
- `blocked_dependency`：当前内核无法构造连续闭合 ECM、声明接触矩阵或保持拓扑/网格有效；停止并提交最小内核变更提案。
- `failed`：已有能力的客观性、接触功、网格或守恒检查失败；保留失败包，不进入三层形态筛查。

## E. 预登记门

- 心肌和心内膜 `reference_shape_modulus == 0`、捕获参考边数为 0；
- ECM 生长、分裂和细胞周期均关闭；
- ECM 与每个细胞有可追踪且不同的类型/对象身份；
- 三个 DCM 对象族均闭合、0 非流形边、0 翻面，最小角门沿用 `>=15 deg`；
- 作用—反作用与刚体合力/合矩使用现有 Z1 代数门；接触工作共轭使用 Z1-C 已冻结的适用门，不因结果放宽；
- 三层初始同层邻居位于接触截断内，且中心四细胞的接触面积分数和邻居数为非零；
- 压力载荷总力与受压面积积分一致，层间交换功各记一次；
- surface-only 与 ECM 材料参考分支不得在同一正式包中结果后混选。

## F. 最小输出和图片

- `model_structure`：真实初始网格，分别标出三类 DCM、ECM 顶/底/边缘、腔压与夹持区；
- `contact_topology`：细胞—细胞和细胞—ECM 接触面积、间隙及类型矩阵；
- `ecm_fields`：ECM 曲率、节点力、法/切向牵引、面积/体积变化和网格质量；
- `cell_fields`：细胞曲率、压力、接触牵引和体积；
- `continuation_snapshots`：`0, 0.25, 0.5, 0.75, 1.0`，明确标为算法延拓坐标；
- `report.md`、`summary.json`、原始网格/账本、独立验证和离线 `index.html`。

未实际运行不得生成“结果图”；本合同附带的策略图只标为模型示意。

## G. 资源与权限

- 若后续获得执行授权：CPU 最多 4 线程，预检累计墙钟最多 600 s，GPU 0，网络 0，不安装软件；
- 结果使用新的 create-only 目录，不覆盖 `tissue_formation_pilot_v04_20260912`；
- 优先通过 PRL runner 调用唯一内核的现有公开入口。发现必须改 `E:\MeshCell3D` 时停止，不继承旧 Z1-B 修改授权；
- 不进入物理时间、主动周期、完整 Z3/Z4、CFD、FSI、分裂或 ECM 周转。
