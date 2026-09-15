---
document_id: PRL-Z1-MYO-STRIP-DEFORMABILITY-HI-A-EXECUTION-V04
status: current
completed_at: 2026-09-13T23:10:09+08:00
numerical_status: passed_synthetic_isometric_high_amplitude_response
visual_status: passed_visual_qa_and_contract_compliance
biological_validation_status: blocked_data
parent_z1_status: blocked
---

# 五细胞心肌条带高幅度形变与可变形性执行记录 v04

## 1. 本轮回答的问题

用户要求重新查看逐细胞形变，并在同一模型中提高主动缩短，判断当前心肌细胞是否能表现为容易变形的物质。本轮严格区分：

1. **局部几何是否能明显改变**：由逐细胞三轴应变直接回答；
2. **被动材料是否过硬**：刚性等长夹持下不可单独辨识，必须另做外部负载边界对照。

## 2. 冻结模型与唯一改变量

- 5 个长轴心肌 DCM 沿 `p` 轴首尾串联；
- 4 个界面各 7 条固定材料黏附链接；
- 最左和最右外端帽各固定 7 个节点，横向表面自由；
- 每个主动细胞有 7 条胞内长轴收缩单元；
- `CENTER` 只激活第 3 个细胞，`SYNC` 同步激活 5 个细胞；
- 方向性骨架形态牵引、被动材料、链接、阻尼、网格和边界条件均不改；
- 只把主动参考缩短从既有 10% 扩展到 15% 和 20%；20% 是合成上限探针，不登记为生理幅度；
- `phi` 是算法激活坐标，不是生理时间。

目标末态、逐边参考形状、逐面参考度量、旧弯曲项和动态重网格继续关闭。本轮没有修改 SimuCell3D 核心。

## 3. 执行与修复链

| 版本 | 结果 | 冻结事实 |
|---|---|---|
| v01 | `failed` | 四条新轨迹完成；仅 `CENTER 15%` 与 `CENTER 20%` 的保存残差分别为 `0.0022842863`、`0.0017541406`，高于 `1e-3` 门，其余门通过。 |
| v02 | `failed` | 只把两个 CENTER 工况每相位保持由 3000 增至 6000 步；15% 通过，20% 为 `0.0010063821`，仍比门限高约 0.638%。 |
| v03 | `passed` | 只把 `CENTER 20%` 每相位保持由 6000 增至 7000 步；材料、载荷、边界和门限不变，组合 **61/61** 门通过。 |
| v04 | `passed_visual_qa` | 仅移动模型示意的行标签以消除遮挡；不修改数值、原始轨迹或裁决。 |
| v05 | `passed_visual_qa_and_contract_compliance` | 保留 v04 无遮挡示意，并补齐冻结合同要求的 10 倍位移显示图；明确标注仅用于观察，不参与数值验收。 |

v01 与 v02 失败包均保留，未回写为 PASS。

## 4. 逐细胞与整体形变结果

峰值激活时的主要结果如下。负 `p` 应变表示长轴缩短，正 `q/r` 应变表示横向或厚度扩张。

| 激活模式 | 主动参考缩短 | 峰值端反力增量 | 五细胞平均 `p` 应变 | 中央细胞 `p` 应变 | 中央细胞 `q/r` 应变 |
|---|---:|---:|---:|---:|---:|
| CENTER | 10% | 0.154504 | -0.2681% | -5.6766% | +2.0655% / +1.7563% |
| CENTER | 15% | 0.246131 | -0.3793% | -8.6929% | +3.3042% / +2.7897% |
| CENTER | 20% | 0.329012 | -0.4903% | **-11.6227%** | **+4.6736% / +3.9391%** |
| SYNC | 10% | 0.879828 | -1.3597% | -1.4141% | +0.3921% / +0.3308% |
| SYNC | 15% | 1.315220 | -2.0372% | -2.0941% | +0.5802% / +0.4839% |
| SYNC | 20% | 1.753258 | **-2.7159%** | -2.7883% | +0.7832% / +0.6561% |

`CENTER 20%` 中，中央主动细胞长轴缩短约 11.62%，而四个被动邻居沿长轴被拉长约 2.29%。因此五细胞平均值只有 -0.49%，此前“形态几乎不变”的观感主要来自整体平均、刚性端夹持和真实比例显示共同掩盖了局部变形，并不是中央细胞没有变形。

反力与局部/平均缩短均随 10%→15%→20% 单调增加；同一幅度下 SYNC 的端反力明显大于 CENTER。结果支持当前合成模型具有连续、可传递的局部变形响应。

## 5. 数值质量与图像验收

- 组合冻结门：**61/61 passed**；
- 最大相对体积误差：`0.7481%`；
- 最小三角角：`33.548°`；
- 最大保存自由节点力：`8.523e-4`；
- 固定节点最大位移：`0`；
- 界面链接作用反作用残差：`0`；
- 子步功耗相对残差：不超过 `8.29e-16`；
- v05 离线页面 13 个链接全部存在，自有 2 张 PNG 与 2 张 SVG 可解析，引用的 GIF 含 9 个真实求解状态并循环播放，证据哈希无漂移；
- v05 模型结构图和 10 倍位移显示图已经人工目视检查；标签不遮挡细胞或夹具，放大倍数与“仅用于显示”说明清晰可见。

## 6. 裁决与解释边界

本轮裁决为 **`passed_synthetic_isometric_high_amplitude_response`**。它证明：在当前合成材料、固定连接与刚性夹持下，单个主动细胞能够产生两位数百分比的局部长轴形变，且形变与张力随主动参考缩短连续增加。

它**不能**证明“被动材料柔软度已正确”，也不能把 20% 主动参考缩短等同于生理细胞缩短。等长端约束会把一部分主动缩短转化为端反力和邻细胞拉伸，因此几何变形大小由主动机制、被动材料、细胞连接和外部负载共同决定。牵引仍是模型节点力/面积代理，不是已标定的三维 Cauchy 应力。

生物学验证继续为 **`blocked_data`**，父 Z1 继续为 **`blocked`**。

## 7. 唯一建议的下一判别实验

在不改变细胞材料、主动幅度和连接的前提下，对同一 10%/20% 工况比较：

1. `ISOMETRIC`：当前两端刚性夹持；
2. `COMPLIANT`：端部连接已知刚度的弹性支撑；
3. `FREE/LOW-LOAD`：一端去除轴向约束或施加近零外载。

同时比较逐细胞长轴缩短、横向扩张、端反力、界面牵引和体积误差。只有这个边界条件矩阵才能区分“细胞本身太硬”与“当前外部约束太强”。该合同尚未起草，也未获得执行授权；心内膜自由态仍保留为其后的既定工作。

## 8. 权威证据

- 主合同：`project_control/ventricle_myocardial_strip_high_amplitude_deformability_contract_v01.md`
- v02 修复合同：`project_control/ventricle_myocardial_strip_high_amplitude_deformability_repair_contract_v02.md`
- v03 最终修复合同：`project_control/ventricle_myocardial_strip_high_amplitude_deformability_repair_contract_v03.md`
- 数值裁决：`results/ventricle_z1/z1_myo_strip_high_amp_deformability_repair_v03_20260913/verdict.json`
- 数值摘要：`results/ventricle_z1/z1_myo_strip_high_amp_deformability_repair_v03_20260913/summary.md`
- 逐细胞指标：`results/ventricle_z1/z1_myo_strip_high_amp_deformability_repair_v03_20260913/cellwise_peak_metrics.csv`
- 图文入口：`results/ventricle_z1/z1_myo_strip_high_amp_deformability_visual_v05_20260913/index.html`
- 视觉验收：`results/ventricle_z1/z1_myo_strip_high_amp_deformability_visual_v05_20260913/visual_compliance_manifest.json`
