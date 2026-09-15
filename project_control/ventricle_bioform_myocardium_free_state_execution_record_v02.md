---
document_id: PRL-VENTRICLE-BIOFORM-MYOCARDIUM-FREE-STATE-EXECUTION-RECORD-V02
status: completed
completed_at: 2026-09-13
stage: Z1-BIOFORM-MYO-A
outcome: failed_numerical
decision: FAIL_Z1_BIOFORM_MYO_A_NUMERICAL
contract: project_control/ventricle_bioform_myocardium_free_state_contract_v02.md
authorization: project_control/ventricle_bioform_myocardium_free_state_authorization_v02.md
result: results/ventricle_z1/z1_bioform_myo_a_v02_20260913/summary.json
next_stage: Z1_BIOFORM_MYO_REPAIR_NOT_RUN_NOT_AUTHORIZED
---

# Z1-BIOFORM-MYO-A｜心肌细胞内禀骨架自由态执行记录 v02

## 结论

本轮已按冻结合同完成有界预检，并调度唯一一次 8 工况正式矩阵。最终裁决为 **`failed_numerical`**：7 条正式轨迹完成，`FULL_M1280_DT020` 在保持段因退化三角面终止；另外，80 面轨迹的冻结相对净力矩门失败，`dt=0.040` 与 `dt=0.010` 轨迹的全过程最大体积误差超过 2%。共同数值门不成立，因此机制门和离散门均为 **`not_adjudicated`**，父 Z1 继续 `blocked`。

主分辨率轨迹确实从近球形形成了长轴、横轴和厚度轴分离，末态 `E_pq=1.265211`、`F_qr=1.151702`，但这只是诊断观察，不是合成机制 PASS，更不是实验心肌形态验证。

## 实际模型

- 单个自由闭合心肌 DCM；无邻居、无 ECM、无腔压、无端部夹持；
- 被动项为 SimuCell3D 体积压力、标量总面积弹性、各向同性皮质张力和弯曲；
- `reference_edge_shape_terms=0`、`reference_face_metric_terms=0`、`target_geometry_used=false`，没有目标末态或逐边/逐面参考形状能；
- 主动粗粒化细胞骨架为无迹张量 `Sigma=s[p⊗p-0.15q⊗q-0.85r⊗r]`，仅将 `n·Sigma·n` 作为界面法向形状牵引；
- 顶点法向投影后移除离散刚体净力和净力矩；过阻尼积分并启用 SimuCell3D 动态重网格；
- 每条完整轨迹保存 9 个真实状态。横轴 `lambda` 是算法加载/松弛坐标，不是生理时间。

## 有界预检与冻结参数

预检只按顺序尝试 `s={0.020,0.040,0.060}`、请求 320 面、`dt=0.020`。前两档未达到冻结形态阈值；最小通过档 `s=0.060` 被选择：

| s | E_pq | F_qr | 预检选择门 |
|---:|---:|---:|---|
| 0.020 | 0.734785 | 1.039297 | failed |
| 0.040 | 1.006155 | 1.062298 | failed |
| 0.060 | 1.265211 | 1.151702 | passed / selected |

正式参数保持为：目标体积 `167.875410364543`、皮质张力 `0.160`、弯曲模量 `0.010`、总面积模量 `0.050`、体积模量 `30`、阻尼 `1`、加载坐标 `10`、保持坐标 `400`。这些均是合成无量纲筛查参数，不是实验拟合。

## 正式矩阵

| 工况 | 执行 | E_pq | F_qr | 关键观察 |
|---|---|---:|---:|---|
| `FULL_M320_DT020` | completed | 1.265211 | 1.151702 | 主诊断轨迹；9 个保存状态闭合、球拓扑、有限 |
| `ABLATION_M320_DT020` | completed | 1.001372 | 0.998334 | 去骨架后保持近球形 |
| `PERTURBED_M320_DT020` | completed | 1.669234 | 1.013031 | 与主轨迹差异大，仅作不稳健警报 |
| `ROTATED37_M320_DT020` | completed | 1.265211 | 1.151702 | 形状比与主轨迹一致 |
| `FULL_M080_DT020` | completed | 1.229953 | 1.139783 | 形状趋势接近，但相对净力矩门失败 |
| `FULL_M1280_DT020` | failed | — | — | 保持段 `lambda=121.64` 后检测到退化面；只保存状态 0–5 |
| `FULL_M320_DT040` | completed | 0.889741 | 0.934819 | 最大体积误差 4.7002%，超门 |
| `FULL_M320_DT010` | completed | 0.862552 | 1.075921 | 最大体积误差 2.6252%，且末态主轴漂移 |

## 冻结门失败

独立复核确认来源哈希全部与预登记匹配。共有 4 个共同数值门失败：

1. `FULL_M080_DT020:cyt_moment_residual=2.135488e-2`，要求 `<=1e-10`；该峰值出现在极小载荷的第 1 步，提示相对残差分母定义也需要单独审查，但冻结门不能在本结果中事后改写；
2. `FULL_M1280_DT020` 未完成，错误为 `surface geometry contains a degenerate face`；
3. `FULL_M320_DT040:max_volume_error=0.0470022`，要求 `<=0.02`；
4. `FULL_M320_DT010:max_volume_error=0.0262518`，要求 `<=0.02`。

因为 1280 面末态不存在，320→1280 离散门不能计算。机制门也不作正式裁决。仅作诊断时还能看到：扰动轨迹相对主轨迹的 `E_pq/F_qr` 差约 `31.9%/12.0%`，远高于预登记的 `5%` 稳健性尺度；`dt=0.010` 与主轨迹的差约 `31.8%/6.6%`。这说明即使先修复显式数值失败，当前自由态机制仍需要检查分支敏感性和长期重网格漂移，不能直接进入心内膜阶段。

## 实现、测试与证据

- Release 可执行文件：`b/z1_bioform_myo/Release/prl_ventricle_bioform_myo.exe`；正式哈希 `4a739cce0d27d044ee11238d85020376feb7b433e6cb5324b9db8d18d921a622`；
- 原冻结求解器、合同、运行器、成功路径核验器和渲染器在正式运行后均保持预登记哈希；
- 聚焦行为测试 `6/6 passed`；受影响的 SimuCell3D 局部重网格回归 `5/5 passed`；这只证明实现接口与失败证据可复核，不把阶段改判为通过；
- CPU 单线程，GPU 0；预检与正式求解器累计约 `450.814 s`，运行账本墙钟 `455 s`；
- 正式失败后没有重跑或调参覆盖。由于冻结成功路径核验器只在 8/8 完成时读取指标，新增了只读、只能保守裁决的失败态独立核验器和渲染器；二者明确记录为正式运行后工具，不能授予机制 PASS；
- 四组 PNG/SVG 均生成并通过尺寸、哈希、离线链接和人工视觉检查：结构图明确为示意图，时间点图与力学场图来自真实主轨迹，裁决图明确显示失败条件与 `NOT ADJUDICATED`。

## 根因工作假设与唯一下一步

当前证据指向三个相互关联但必须分开验证的问题：

1. **动态重网格长期稳定性**：1280 面在保持段局部面退化；`dt=0.040` 末态面数从 320 降至 138，提示拓扑更新/边长控制可能与长程松弛耦合；
2. **时间步与刚体漂移**：`dt=0.010` 在最后四分之一保持段出现质心和主轴漂移，形态不向同一末态收敛；
3. **残差归一化与扰动分支**：80 面第 1 步的相对力矩峰值可能受近零分母支配，但扰动轨迹的大幅分叉是真实的稳健性警报，二者不能混为同一修复。

下一步应建立新的 **Z1-BIOFORM-MYO-R 数值资格修复合同**：先用短程、只读诊断定位首次坏面/首次刚体漂移和残差分母，再以新的 create-only 版本验证冻结的几何、守恒、体积、时间步与扰动恢复门。当前修复、重跑、心内膜、ECM 和三层模型均为 **NOT_RUN / 未授权**。

## 权限与保留边界

本轮未使用 GPU、网络、Docker、软件安装、外部发布、提交或推送，也未删除任何文件。构建目录和开发烟雾测试目录继续保留；如需清理，必须另列绝对路径并取得用户确认。

## 入口

- 结果页：`results/ventricle_z1/z1_bioform_myo_a_v02_20260913/index.html`
- 机器摘要：`results/ventricle_z1/z1_bioform_myo_a_v02_20260913/summary.json`
- 独立失败裁决：`results/ventricle_z1/z1_bioform_myo_a_v02_20260913/verification/independent_verification.json`
- 条件指标：`results/ventricle_z1/z1_bioform_myo_a_v02_20260913/verification/condition_metrics.csv`
- 视觉 QA：`results/ventricle_z1/z1_bioform_myo_a_v02_20260913/visual_qa.json`
- 原始失败：`results/ventricle_z1/z1_bioform_myo_a_v02_20260913/raw/FULL_M1280_DT020/stderr.txt`
