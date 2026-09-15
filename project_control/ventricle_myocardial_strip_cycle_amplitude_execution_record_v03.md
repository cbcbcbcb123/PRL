# Z1-MYO-STRIP-CYCLE-AMP-A 激活数量与收缩幅度执行记录 v03

- 完成日期：2026-09-13
- 数值裁决：**`passed_synthetic_activation_count_amplitude_response`**
- 冻结门：**85/85 passed**
- 可视化：**`passed_visual_qa`**（v03 排版修复投影）
- 实验比较：**`qualitative_consistency_only`**
- 生物学验证：**`blocked_data`**
- 父 Z1：继续 **`blocked`**
- 资源：CPU 单线程，GPU 0

## 实际问题与比较定义

本轮在同一个五细胞长轴条带中比较两种激活数量：`CENTER` 仅中心第 3 个细胞周期激活，其余四个保持被动；`SYNC` 五个细胞同步激活。两组均保留四个界面各 7 条固定材料链接、左右外端帽各 7 个固定节点和自由横向表面。因此它比较的是主动细胞数量，不把“单细胞”换成无邻居、无链接、无夹持的另一种模型。

每个模式使用 `epsilon=0.02,0.05,0.10` 三个主动参考长度缩短探针，激活为 `a(phi)=sin²(pi phi)`。材料、形态支撑、收缩单元刚度、黏附、阻尼、网格和边界均不随幅度重拟合。`phi` 是 9 个算法激活/松弛状态的坐标，不是生理时间。

5% 的 `CENTER` 与 `SYNC` 轨迹只在可执行文件、C++ 源、输入网格和求解设置哈希全部匹配后复用；2% 与 10% 首轮共新算四条轨迹。内核和输入未修改。

## 数值过程与失败保留

v01 六工况矩阵全部完成，但 `CENTER_EPS100` 有两门失败：最大保存自由节点力 `0.00134317 > 0.001`，周期末反力恢复误差占主动增量 `11.7404% > 10%`。该轨迹在固定相位保持中残差持续单调下降，其余体积、网格、夹持、功耗、链接和幅度响应门均通过。

v02 按预登记修复规则只把 `CENTER_EPS100` 的每相位保持从 2000 增至 3000 步，未改模型、载荷或门限。修复后最大保存自由节点力降为 `8.33649e-4`，反力恢复误差降为主动增量的 `5.2250%`；组合 85/85 门通过。v01 失败 verdict 和原始轨迹完整保留。

首次 v02 张力图出现双颜色条挤压，模型示意的行标签也压到夹具。v03 只重排这两张图，数值和原始数据没有变化；修复图、PNG/SVG 解析、三张 GIF 的 9 帧/循环信息和离线页 11 个链接已检查，缺失链接为 0。

## 核心结果

| 模式 | `epsilon` | 峰值端反力增量 | 峰值平均长轴应变 | 横向应变 | 厚度应变 |
|---|---:|---:|---:|---:|---:|
| CENTER | 2% | 0.026538 | -0.0669% | +0.0309% | +0.0245% |
| CENTER | 5% | 0.071320 | -0.1453% | +0.0499% | +0.0401% |
| CENTER | 10% | 0.154504 | -0.2681% | +0.0837% | +0.0587% |
| SYNC | 2% | 0.173658 | -0.2811% | +0.0969% | +0.0812% |
| SYNC | 5% | 0.438734 | -0.6848% | +0.2150% | +0.1821% |
| SYNC | 10% | 0.879828 | -1.3597% | +0.4221% | +0.3590% |

两个模式的端反力和长轴缩短都随收缩幅度单调增加；每个幅度下五细胞同步反力均大于中心单细胞激活。SYNC/CENTER 的峰值反力增量比约为 6.54、6.15、5.69，说明在当前固定链接与等长夹持的合成模型中，多细胞同步不是简单的单细胞形变复制，而是形成贯穿四个界面的共同传力链。

等长夹持抑制条带整体缩短，因此几何形变保持在小幅范围；同步 10% 主动参考缩短只产生约 1.36% 的平均细胞长轴缩短，但端反力明显增加。这个结果符合“等长工况主要把主动缩短转为张力”的模型预期。

## 场量解释

- 形变动画和峰值图使用真实三角网格、无形变放大；颜色为同一材料节点相对各轨迹 `snapshot 0` 的位移。
- `contraction_traction` 是胞内收缩节点力除以节点面积的幅值；`adhesion_traction` 是固定界面链接节点力除以节点面积的幅值。
- 两种场分开作图，每种场在 6 个工况和全部动画帧使用同一色标。
- 这些是模型牵引代理，不是三维 Cauchy 应力，也没有映射到 Pa、μN 或真实心动周期。

## 证据入口

- 主合同：[ventricle_myocardial_strip_cycle_amplitude_contract_v01.md](ventricle_myocardial_strip_cycle_amplitude_contract_v01.md)
- 修复合同：[ventricle_myocardial_strip_cycle_amplitude_repair_contract_v02.md](ventricle_myocardial_strip_cycle_amplitude_repair_contract_v02.md)
- v01 失败包：[verdict.json](../results/ventricle_z1/z1_myo_strip_cycle_amp_v01_20260913/verdict.json)
- v02 组合裁决：[verdict.json](../results/ventricle_z1/z1_myo_strip_cycle_amp_repair_v02_20260913/verdict.json)
- v02 定量表：[metrics.csv](../results/ventricle_z1/z1_myo_strip_cycle_amp_repair_v02_20260913/metrics.csv)
- v02 结果摘要：[summary.md](../results/ventricle_z1/z1_myo_strip_cycle_amp_repair_v02_20260913/summary.md)
- v03 可视化入口：[index.html](../results/ventricle_z1/z1_myo_strip_cycle_amp_visual_v03_20260913/index.html)
- v03 视觉验收：[visual_repair_manifest.json](../results/ventricle_z1/z1_myo_strip_cycle_amp_visual_v03_20260913/visual_repair_manifest.json)

## 结论边界与下一步

本阶段通过的是合成的“主动细胞数量 × 主动参考缩短幅度”响应，不是生理幅度、真实张力或实验吻合验证。固定材料链接不是已标定闰盘，刚性端帽不是可变形 ECM 或微柱，方向性骨架仍是粗粒化代理。

这轮授权已消费。下一步回到已经约定但尚未运行的**心内膜单细胞自由态合同**：先验证扁平化角色机制，再进入心肌—ECM—心内膜受限三层组织；不得由本轮 PASS 自动启动。
