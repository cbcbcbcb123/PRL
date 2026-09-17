---
document_id: PRL-FEM-F1SEG-SURFACE-CELL-SEGMENTATION-CANDIDATE-CONTRACT-V01
status: adopted
authorized_at: 2026-09-17
authorization_source: user agreed to continue the proposed F1-Seg-A stage
gpu: forbidden
scientific_solver_runs: 0
automatic_retries: 0
result: results/ventricle_fem/f1seg_surface_cell_candidate_v01_20260917
---

# F1-Seg-A｜曲面心肌细胞候选分割合同 v01

## 问题与裁决边界

本阶段判断公开的72 hpf心肌膜栈能否在真实曲面局部切平面上形成可审阅、可复算的逐细胞**候选实例**。它不运行FEM、DCM、材料反演、组织生长、ECM反馈、模型训练或GPU任务。

作者提供的`SurfacePoints.mat`是10 µm间距的表面取向采样点，不是细胞中心或实例标签。`Mask_Boundary.tif`是组织区域mask。两者均不得转换名称后冒充真实细胞。

没有独立人工实例标签时，本阶段最多通过工程候选提取子门；完整F1-Seg资格保持`blocked_human_validation`。模型自身生成的边界、同一算法的二次计算或视觉印象不能替代人工留出真值。

## 冻结输入与样本分工

- 原包：`E:\Data\PRL\public\zenodo\15509350\Data.zip`，已在F1-R中通过大小和MD5。
- 方法开发：`Data/Zebrafish/Fish_72hpf_4_Fig4-5/`。
- 冻结留出：`Data/Zebrafish/Fish_72hpf_3/`和`Data/Zebrafish/Fish_72hpf_5/`。
- 读取：`Orientation_Ch.tif`、`Mask_Boundary.tif`、`Mask_Full.tif`、`SurfacePoints.mat`和`Analysis_Coarse_Grained_Nematic.mat`。
- Fish 1/2因文件命名异常不参与本轮；120 hpf不参与参数选择或验收。

## 方法冻结

1. 按`SurfacePoints.xyz`和`xyzNormal`建立正交局部切平面；根据`Mask_Full`沿法向两侧的占据率确定向组织内部的方向。
2. 在每个中心提取固定物理尺寸的局部切平面，并对距表面0--3 µm的四层膜信号作最大投影。坐标按`SurfacePoints.Pixel`转换，不把z层数当作等距像素。
3. 只在Fish 4上进行一次有界参数选择：局部对比、膜线增强、阈值、种子最小间距和面积过滤均记录到冻结配置；不得查看Fish 3/5结果后重新调参。
4. Fish 4选择三个空间分离、组织占据充分的开发ROI；Fish 3/5使用同一确定性质量排序和同一参数，各选择三个ROI。
5. 候选实例使用膜网络约束的距离变换/分水岭生成；接触ROI边缘、掩膜缺失或面积超出冻结范围的对象只标为排除候选，不静默删除。
6. 对每个保留候选输出质心、面积、周长、长/短轴、长宽比、无极性方向、最近作者director及其无极性夹角；这些量是候选读数，不是已验证生物统计。

## 有界参数和预算

- 切平面边长：40--56 µm；输出像素间距固定为原始xy间距`0.2071606 µm`。
- 浅层深度固定候选：`0, 1, 2, 3 µm`。
- 候选细胞面积过滤只可在`20--600 µm²`内冻结；长宽比上限只可在`6--10`内冻结。
- 开发阶段最多比较12组参数；冻结后对Fish 3/5只运行一次，不自动重调或重跑。
- 结果包上限64 MiB，停止保全16 MiB；整个项目仍受3 GiB硬上限约束。
- 单线程CPU、0 GPU、0安装、0删除；不执行上游MATLAB代码。

## 子门

### G0 曲面提取完整性

- 三条鱼均能直接从原包读取；物理尺度明确。
- 每个选定ROI的切平面坐标有限、法向正交误差小于`1e-6`。
- 有效组织覆盖率、内外法向选择和数据范围被逐ROI记录。

### G1 候选实例工程门

- 冻结参数在Fish 3/5不变，配置哈希一致。
- 三条鱼各至少3个可显示ROI；每条鱼累计至少15个不接触边界的候选实例。
- 所有保留候选面积有限且位于冻结范围，长/短轴为正，标签互斥。
- 输出原膜图、增强膜图、候选标签和叠加边界，不仅输出统计表。
- 跨鱼面积或长宽比中位数相差超过2倍时记为`failed_generalization`，不通过调参掩盖。

### G2 独立人工留出门

必须由独立人工标注或用户确认的冻结ROI计算细胞计数误差、边界重合、漏分割、并分割和闭合率。没有该材料时状态固定为`not_run`，总体F1-Seg固定为`blocked_human_validation`。

## 输出与停止规则

- 冻结配置、每ROI质量账本、候选实例CSV和可复算NPZ。
- 一张曲面切平面结构图；一张三鱼候选结果与分布图。
- 明确区分作者director、候选细胞长轴和人工真值。
- 若切平面不能稳定显示膜边界，或G1在冻结留出上失败，则停止，不安装新模型、不转向GPU、不启动FEM。
- 本阶段结束后先提交候选图和裁决；下一阶段需要新的合同或用户对人工标注的明确确认。
