---
document_id: PRL-Z1-TF-EXECUTION-V01
status: current
recorded_at: 2026-09-12
scientific_status: unknown
package_status: passed
parent_z1_status: unresolved
---

# Z1-TF 三层环境成形静态筛查执行记录

## 执行结论

已按用户决定执行 4×4 心肌细胞—可变形 ECM—4×4 心内膜细胞的静态成形筛查。所有细胞的 `reference_shape_modulus` 严格为 `0`，没有捕获参考边度量。形态仅由被动壳力学、固定邻接黏附、当前网格接触筛查、细胞—ECM 分布连接、ECM 变形、心肌长轴细胞骨架支杆、腔面压力和组织片两端夹持共同产生。

正式交付包为 `results/ventricle_z1/tissue_formation_pilot_v04_20260912`。其独立证据验证为 `passed`（19/19），人工视觉 QA 为 `passed`，但冻结的目标形态门没有全部通过，因此科学筛查状态为 `unknown`；父级 Z1 保持 `unresolved`，Z2 及后续阶段未运行。

## 工况与边界

- 细胞：16 个初始球形心肌 DCM 和 16 个初始球形心内膜 DCM，每胞 80 个三角面；
- ECM：25 节点可变形弹簧—弯曲网络，位于两层细胞的共同基底界面；
- 夹持：x 两端的细胞有限端帽节点与 ECM 两侧边固定；
- 腔面载荷：心内膜顶侧显式法向压力 `20 Pa`，从 0 延拓到全载；
- 心肌极性：每个心肌细胞 6 条 x 向细胞骨架支杆，目标长度为初始长度的 `1.22`；
- 对照：`FULL`、`NO_LUMEN`、`NO_ECM_ATTACH`、`NO_CYTOSKELETON`；
- 输出点：`f=0, 0.25, 0.50, 0.75, 1.00`，为算法延拓坐标，不是物理时间；
- 运行：CPU 4 线程，四工况共 1028.4648224 s；GPU 0、网络 0、软件安装 0、内核修改 0。

## 冻结门结果

| 门 | 结果 | 数值 |
|---|---|---|
| 四工况完成 | passed | 4/4，各 100 次接受更新 |
| 参考态膜能未使用 | passed | 最大模量 0；参考边数 0 |
| 网格有效 | passed | 0 翻面；全条件最小角 32.539847°，门 15° |
| 体积控制 | passed | 最大相对误差 0.00179216，门 0.05 |
| 残余力比 | passed | 最差 0.0288341，门 0.05 |
| 心内膜目标扁平化 | failed | FULL 中央细胞中位数 1.182021，门 1.50 |
| 心肌目标长轴化 | failed | FULL 中央细胞中位数 0.983671，门 1.10 |

对照数值为：无腔压心内膜扁平度 `1.174429`，无 ECM 连接为 `1.188177`；无骨架心肌长轴比为 `0.982904`。虽然原冻结的严格大小比较布尔门返回 true，但 FULL 相对无骨架仅增加约 `0.000767`，且 FULL 反而低于无 ECM 连接。这只表示极弱或非单调差异，不能称为稳健机制分离。

## 解释

本次新路线解决了“预设扁平/长轴参考形状导致零载网格崩坏”的数值问题：当前多细胞环境模型保持闭面、体积和残余力门，ECM 在 FULL 中发生约 `0.319 µm` 的可变形响应。但冻结载荷与连接强度只让心内膜扁平度增加约 18%，没有达到目标；心肌也没有形成长轴，反而略低于初始比值。

因此当前答案是：**这种不依赖参考态膜能的三层机制在数值上可运行，但现有构型与参数还不能产生我们想要的两类细胞形态。** 这不支持恢复参考态膜能，也不支持直接进入主动周期；下一步应先定位为什么 ECM 连接和轴向骨架作用过弱或方向不对。

## 版本与失败保留

- v01：计算完成后定量图画布安全边距失败，保留；
- v02：CSV 字符串/整数筛选错误导致定量图为空，保留；
- v03：数值/绘图数据验证通过，但人工视觉 QA 发现图例和标签重叠，保留；
- v04：复用 v01 的 20 个计算快照并逐文件 SHA-256 核对，只修复呈现层；独立验证和人工视觉 QA 通过。

## 权威证据

- `project_control/ventricle_cell_geometry_strategy_decision_v04.md`
- `project_control/ventricle_trilayer_shape_formation_pilot_contract_v01.md`
- `results/ventricle_z1/tissue_formation_pilot_v04_20260912/summary.json`
- `results/ventricle_z1/tissue_formation_pilot_v04_20260912/verification/independent_verification.json`
- `results/ventricle_z1/tissue_formation_pilot_v04_20260912/visual_qa.json`
- `results/ventricle_z1/tissue_formation_pilot_v04_20260912/index.html`

## formal parent-Z1 参考态结果和本轮环境成形结果都保留为不同模型路线的证据。v04 的 `unknown` 不取代早期 Z1-A/Z1-B/Z1-C 的局部本构通过，也不把它们外推为组织验证。
