# Z1-MYO-STRIP-L5-A 五细胞心肌条带执行记录 v02

- 完成时间：2026-09-13 21:14 CST
- 内核：项目内受控 SimuCell3D
- 计算：CPU 单线程；GPU 0
- 组合裁决：**`passed_synthetic_strip_mechanics`**
- 实验比较：**`qualitative_consistency_only`**
- 生物学定量验证：**`blocked_data`**
- 父 Z1：继续 **`blocked`**

## 实际模型

五个由 `Z1-BIOFORM-MYO-R v03` 生成的长轴心肌细胞沿 `p` 轴首尾串联。相邻细胞的四个界面各有 7 条固定材料黏附链接；每个细胞有 7 条等大反向的胞内长轴收缩单元。最左和最右细胞的外侧 7 个端帽节点固定，其余表面自由。

细胞长轴形态由 v03 的方向性骨架法向形态牵引维持；胞内收缩单元的目标长度按 `a(phi)=sin^2(pi phi)` 最多缩短 5%。这不是目标形状膜能：参考边、参考面度量和目标末态项均为 0。弯曲项继续因旧实现未通过刚体不变性而隔离为 0。求解器相位 `phi` 是算法激活坐标，不是生理时间。

正式矩阵包含 `PASSIVE`、`SYNC`、`CENTER` 和 `CENTER_NO_LINK`。前三项与 v01 同时运行；`CENTER_NO_LINK` 在 v01 唯一未通过保存状态残差门。该残差在定相位松弛中单调下降，因此 v02 按预先冻结的修复合同只将该独立阴性对照的每相位松弛从 2000 增至 3000 步，未改变模型、载荷或门槛。v01 失败 verdict 原样保留，v02 通过路径由组合 verdict 明确引用，不覆盖历史失败。

## 核心结果

| 量 | 结果 | 解释 |
|---|---:|---|
| `SYNC` 端部反力 | `0.00276077 -> 0.44149444` | 峰值出现在 `phi=0.5` 的峰值激活处 |
| `SYNC` 平均长轴跨度 | `9.192856 -> 9.129906` | 峰值激活时缩短 `0.6848%` |
| `SYNC` 平均横轴跨度 | `6.662215 -> 6.676541` | 增加 `0.2150%` |
| `SYNC` 平均厚度跨度 | `5.373200 -> 5.382984` | 增加 `0.1821%` |
| `CENTER` 主动端部反力增量 | `0.07132033` | 中心细胞的力可跨四个界面到达夹持端 |
| `CENTER_NO_LINK` 最大端部反力变化 | `0.00072964` | 仅为有链接中心传力增量的约 `1.02%` |
| `PASSIVE` 最大端部反力漂移 | `0.00268438` | 低于同步主动增量的 10% 门 |

因此，本阶段在合成条件下支持：固定细胞间链接能够传递胞内收缩力；同步激活在等长夹持下主要表现为端部反力升高和小幅三轴形变，而不是条带整体明显缩短；去除链接后中心细胞到端部的传力基本消失。

## 数值与验证

- 组合冻结门：`43/43 passed`；
- 五个细胞在九个保存状态均保持 `162` 节点、`320` 面；
- 最大保存相对体积误差：`0.7257%`；
- 最小保存三角形角：`46.1684 deg`；
- 最大保存自由节点力：`7.5414e-4`；
- v02 修复阴性对照最大保存自由节点力：`5.7740e-4`；
- 固定端帽最大位移：`0`；
- 功耗相对残差、固定链接作用—反作用残差和所有有限性门均通过；
- v01 四工况墙钟合计 `499.15 s`；v02 定向修复 `180.26 s`；
- 五组 PNG/SVG 已人工检查，未见裁切、错误标签或概念图冒充求解器结果。

## 与实验现象的关系

该结果与微图案心肌组织中“长轴排列、等长边界下产生收缩反力、细胞—细胞连接参与跨细胞力传递”的方向一致；也与斑马鱼心室外弯心肌细胞呈扁平且拉长、形态受内外力平衡调节的观察相容。这里只能称**定性相容**：模型单位没有映射到微牛顿，算法相位没有映射到心率，且没有登记同一实验体系的细胞边界、端部刚度和力时序数据。

相关原始研究：

- [Cooperative coupling of cell-matrix and cell-cell adhesions in cardiac muscle](https://pmc.ncbi.nlm.nih.gov/articles/PMC3382528/)
- [A microfabricated platform to measure and manipulate the mechanics of engineered cardiac microtissues](https://pmc.ncbi.nlm.nih.gov/articles/PMC3338105/)
- [Functional modulation of cardiac form through regionally confined cell shape changes](https://pubmed.ncbi.nlm.nih.gov/17311471/)

## 证据入口

- 决定：[ventricle_myocardial_strip_decision_v01.md](ventricle_myocardial_strip_decision_v01.md)
- 初始合同：[ventricle_myocardial_strip_contract_v01.md](ventricle_myocardial_strip_contract_v01.md)
- pilot 冻结：[ventricle_myocardial_strip_pilot_freeze_v01.md](ventricle_myocardial_strip_pilot_freeze_v01.md)
- 定向修复合同：[ventricle_myocardial_strip_repair_contract_v02.md](ventricle_myocardial_strip_repair_contract_v02.md)
- v01 单门禁失败包：[../results/ventricle_z1/z1_myo_strip_l5_a_v01_20260913/verdict.json](../results/ventricle_z1/z1_myo_strip_l5_a_v01_20260913/verdict.json)
- v02 组合 verdict：[../results/ventricle_z1/z1_myo_strip_l5_a_repair_v02_20260913/verdict.json](../results/ventricle_z1/z1_myo_strip_l5_a_repair_v02_20260913/verdict.json)
- v02 摘要：[../results/ventricle_z1/z1_myo_strip_l5_a_repair_v02_20260913/summary.md](../results/ventricle_z1/z1_myo_strip_l5_a_repair_v02_20260913/summary.md)
- 视觉验收：[../results/ventricle_z1/z1_myo_strip_l5_a_repair_v02_20260913/visual_qa.json](../results/ventricle_z1/z1_myo_strip_l5_a_repair_v02_20260913/visual_qa.json)

## 下一步

按用户当前路线，下一阶段回到**心内膜单细胞自由态**：先冻结不使用目标形状能的扁平化骨架机制、消融与离散门，再另行执行。当前心肌条带的固定链接和刚性端夹持仍是最小试验边界，尚不能替代可变形 ECM、组织拥挤、腔压或真实微柱边界。
