---
document_id: PRL-FEM-F1SEG-SURFACE-CELL-SEGMENTATION-CANDIDATE-EXECUTION-V01
status: completed_blocked_human_validation
executed_at: 2026-09-17
contract: project_control/ventricle_fem_surface_cell_segmentation_candidate_contract_v01.md
result: results/ventricle_fem/f1seg_surface_cell_candidate_v01_20260917
gpu_runs: 0
scientific_solver_runs: 0
---

# F1-Seg-A｜曲面心肌细胞候选分割执行记录 v01

## 裁决

- G0 曲面提取完整性：`passed`。
- G1 候选实例工程门：`passed`。
- G2 独立人工留出门：`not_run`。
- 总体 F1-Seg：`blocked_human_validation`。

G1 的通过只说明同一冻结算法能在三条鱼的九个真实曲面局部图中产生有限、可复算、显式标记排除原因的候选分区；它不说明这些分区已经是正确细胞。未经人工留出复核，不得把候选边界、面积、长宽比或邻接映射进 FEM/DCM 并称为真实细胞形态场。

## 输入与执行

直接读取 `E:\Data\PRL\public\zenodo\15509350\Data.zip`，未整包解压、未执行上游 MATLAB 代码。Fish 4 是唯一开发样本；在其三个确定性质量排序 ROI 上比较了预登记的12组参数。冻结配置为 `cfg03`：0.35 µm ridge 尺度、0.75膜响应分位阈值、3.0 µm种子最小间距，配置 SHA-256 为 `27d32acda82769a52b7880937b51d8ea90a165e7e9a48ee85b6c56e6d22d30db`。随后以同一配置对 Fish 3 和 Fish 5 各执行一次留出提取，没有根据留出结果回调参数。

每个 ROI 由作者表面采样点、法向和 `Mask_Full` 的内外占据率建立局部正交基，对距表面0、1、2、3 µm层的 `Orientation_Ch` 反相信号作浅层最大投影。作者提供的 surface point 和 director 只用于局部坐标及方向一致性读数，不被重新命名为细胞中心或细胞标签。

首次 Fish 4 开发调用在产生冻结配置或结果前人工中止：实现错误在每个采样点重复复制约100 MiB mask。将二值 mask 固定为 `uint8` 只读采样后，完成一次开发运行和一次 Fish 3/5 留出运行。该中止没有消费留出集，也没有产生可解释的科学结果。

## 定量结果

| 样本 | 角色 | ROI | 全部分区 | 保留候选 | 面积中位数 (µm²) | 长宽比中位数 |
|---|---|---:|---:|---:|---:|---:|
| Fish 3 | 冻结留出 | 3 | 101 | 32 | 50.4043 | 1.5319 |
| Fish 4 | 开发 | 3 | 97 | 39 | 54.3310 | 1.7032 |
| Fish 5 | 冻结留出 | 3 | 90 | 28 | 45.1257 | 1.5450 |

三鱼面积中位数最大/最小为1.204，长宽比中位数最大/最小为1.112，均低于冻结的2倍门。全部保留候选面积在20--600 µm²、长短轴为正、长宽比不超过8；三鱼局部基正交误差均低于 `1e-6`。加入独立一致性核验后结果包为8,416,760 bytes，低于64 MiB阶段上限。

独立验证器不导入分割实现，从NPZ和CSV重算配置哈希、每个标签的像素面积、标签—账本完备性、三鱼计数和中位数比，并重新读取三张图；全部检查 `passed`。该结论只证明证据包自洽，不改变G2=`not_run`或总体=`blocked_human_validation`。见[独立核验](../results/ventricle_fem/f1seg_surface_cell_candidate_v01_20260917/independent_verification.json)。

## 图像复核与限制

[曲面切平面结构图](../results/ventricle_fem/f1seg_surface_cell_candidate_v01_20260917/surface_tangent_structure.png)和[九ROI候选审计图](../results/ventricle_fem/f1seg_surface_cell_candidate_v01_20260917/candidate_segmentation_audit.png)均可读；[三鱼结果图](../results/ventricle_fem/f1seg_surface_cell_candidate_v01_20260917/candidate_summary.png)明确区分绿色保留候选和红色排除候选。

视觉复核同时显示，部分 ROI 具有清楚的闭合高亮信号，但另一些 ROI 含条带、模糊区和曲面浅层投影混叠；分水岭可以在这些区域产生数学闭合分区，却不能证明其对应单个心肌细胞。这个现象不推翻 G1 工程可复算性，但正是 G2 不能省略的原因。

## 唯一下一步

冻结 Fish 3/5 的少量 ROI，建立独立人工实例边界；预注册计数误差、边界重合、漏分割、并分割及闭合率后只计算一次 G2。若 G2 未通过，应首先检查成像通道身份、局部曲面投影深度和人工可辨识性，而不是继续用自动分区参数追求整齐图形。G2 通过前不启动真实形态 FEM、DCM、增长或 ECM 反馈。

本阶段单线程 CPU，0 GPU、0科学求解器、0安装、0删除、0自动留出重跑。
