---
document_id: PRL-VENTRICLE-BIOFORM-MYOCARDIUM-FREE-STATE-CONTRACT-V01
status: superseded_pre_execution
frozen_at: 2026-09-13
stage: Z1-BIOFORM-MYO-A
authorization: project_control/ventricle_bioform_myocardium_free_state_authorization_v01.md
superseded_by: project_control/ventricle_bioform_myocardium_free_state_contract_v02.md
---

# Z1-BIOFORM-MYO-A｜心肌细胞内禀骨架自由态资格合同 v01

> 2026-09-13：开发烟雾测试显示，完整 Cauchy 牵引在无面内剪切弹性的流体式 DCM 表面上产生切向网格漂移；固定节点/面数又与 SimuCell3D 的动态重网格机制冲突。本合同在正式运行前由 v02 取代，未消耗正式尝试。

## 1. 本阶段问题

在不使用逐边/逐面参考形状、邻居、ECM、腔压或端部夹持的条件下，一个从等体积近球形起步的心肌 DCM，能否由明确的细胞骨架各向异性形成稳定、可旋转、可扰动恢复的非球形稳态？

通过只表示一个合成、粗粒化的心肌细胞骨架机制通过数值与机制资格门；不表示真实斑马鱼参数已标定、成人杆状细胞已复现、组织中形态已形成或父 Z1 已通过。

## 2. 冻结模型

被动表面模型沿用受控 SimuCell3D：细胞体积压力、标量总面积稳态、各向同性皮质张力与弯曲。所有细胞表面参考边、参考面及目标最终几何关闭：

```text
reference_edge_shape_terms = 0
reference_face_metric_terms = 0
target_geometry_used = false
```

细胞骨架以常量、对称、无迹的稳态预应力张量表示。局部正交基为长轴 `p`、平面横轴 `q`、厚度轴 `r`：

```text
Sigma_cyt = s * [ 1.00 p⊗p - 0.15 q⊗q - 0.85 r⊗r ]
```

每个三角面 `f` 的积分力为：

```text
F_f = alpha(t) * A_f * Sigma_cyt * n_f
```

并以 `1/3` 均分给三个顶点。`alpha(t)` 只用于从 0 到 1 的数值加载延拓，不代表发育时间。该载荷是非保守、ATP 维持的净细胞骨架稳态代理；本阶段不加入周期肌节收缩。

初始体积、皮质张力、弯曲、面积模量、体积模量、阻尼与全部无量纲尺度由 `preregistration.json` 冻结。目标面积只允许是同网格等体积球的一个标量面积，不携带方向。

## 3. 有界预检与参数选择

预检仅在 320 面网格、基准数值步长上运行三个预登记幅值：

```text
s in {0.020, 0.040, 0.060}
```

按从小到大顺序选择第一个同时满足以下工程成形条件的幅值：长/横轴比 `E_pq >= 1.20`、横/厚轴比 `F_qr >= 1.15`、最大体积误差 `<= 0.02`、最小三角角 `>= 15 deg`、无非有限值。若均不满足，本阶段停止为 `failed_numerical_or_mechanism`，不得扩大扫描或修改正式阈值。

幅值选择是合成工程校准，不是实验拟合。选择结果写入独立 `pilot_selection.json`，正式矩阵开始后不再改变。

## 4. 冻结正式矩阵

使用预检选定的唯一 `s`，执行以下 create-only CPU 轨迹：

| ID | 网格面数 | 数值步长 | 初始状态 | 骨架张量 | 目的 |
|---|---:|---:|---|---|---|
| `FULL_M320_DT020` | 320 | 0.020 | 等体积球 | 基准 | 主成形 |
| `ABLATION_M320_DT020` | 320 | 0.020 | 2% 无方向扰动球 | 关闭 | 消融/圆化 |
| `PERTURBED_M320_DT020` | 320 | 0.020 | 2% 无方向扰动球 | 基准 | 稳态吸引性 |
| `ROTATED37_M320_DT020` | 320 | 0.020 | 整体旋转 37 deg 的球网格 | 张量同步旋转 | 客观性 |
| `FULL_M080_DT020` | 80 | 0.020 | 等体积球 | 基准 | 粗网格 |
| `FULL_M1280_DT020` | 1280 | 0.020 | 等体积球 | 基准 | 细网格 |
| `FULL_M320_DT040` | 320 | 0.040 | 等体积球 | 基准 | 粗步长 |
| `FULL_M320_DT010` | 320 | 0.010 | 等体积球 | 基准 | 细步长 |

所有轨迹具有相同加载时长与总数值松弛坐标；保存初始、加载 25/50/75/100% 和保持 25/50/75/100% 共 9 个状态。保存坐标明确标为算法加载/松弛进度，不称为生理时间。

## 5. 正式验收门

### 共同数值门

- 所有坐标、曲率、压力和力为有限值；闭合拓扑、面数和持久顶点 ID 不变。
- 任一状态最大体积相对误差 `<= 0.02`，最小三角角 `>= 15 deg`。
- 细胞骨架面牵引的相对净力与相对净力矩均 `<= 1e-10`。
- 过阻尼步的力功—耗散代数残差 `<= 1e-12`。
- 主轨迹末态/历史峰值自由节点总力比 `<= 0.05`。

### 机制门

- 主轨迹从球形形成 `E_pq >= 1.20` 且 `F_qr >= 1.15`。
- 消融末态 `E_pq <= 1.05`、`F_qr <= 1.05`，且主轨迹相对消融的两个比值增量分别 `>= 0.15`、`>= 0.10`。
- 2% 扰动轨迹末态的 `E_pq`、`F_qr` 与主轨迹相对差均 `<= 0.05`。
- 旋转轨迹的形状比与主轨迹相对差均 `<= 0.02`；逆旋转后面积加权节点 RMS 差除以等体积半径 `<= 0.02`；长轴与旋转后的 `p` 夹角 `<= 5 deg`。

### 离散门

- 320→1280 面的 `E_pq`、`F_qr` 相对变化各 `<= 0.05`；80 面只报告趋势，不作为中细门替代。
- `dt=0.020`→`0.010` 的 `E_pq`、`F_qr` 相对变化各 `<= 0.02`；`dt=0.040` 只报告趋势。

### 主张门

- 以上全过时状态为 `passed_synthetic_mechanism`。
- 缺少约 48 hpf 同期、同区域、三维注册的细胞长/横/厚轴数据时，`biological_validation_status=blocked_data`。
- 任一共同数值门失败时，机制门不得裁决为 PASS；保存最后有效状态和失败证据。

## 6. 输出

结果目录为新的 create-only 路径：

```text
results/ventricle_z1/z1_bioform_myo_a_v01_20260913/
```

至少包含 `preregistration.json`、`pilot_selection.json`、`run_ledger.json`、`summary.json`、`report.md`、原始节点/面/力/步账本、独立验证、命令与来源哈希、离线 `index.html`，以及：

1. `model_structure.png/.svg`：模型结构和力学机制示意，明确标注 schematic；
2. `morphology_timepoints.png/.svg`：真实网格的多状态形态；
3. `mechanical_fields.png/.svg`：曲率、压力、骨架牵引和总牵引；
4. `validation_gates.png/.svg`：消融、旋转、扰动、网格和数值步长验收。

正式执行只允许一次；完成或失败后停止，不自动进入心内膜、ECM 锚定或三层模型。
