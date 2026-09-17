---
document_id: PRL-FEM-F1R-MEASURED-CELL-SHAPE-DATA-QUALIFICATION-EXECUTION-V01
status: passed
executed_at: 2026-09-16
contract: project_control/ventricle_fem_measured_cell_shape_data_qualification_contract_v01.md
result: results/ventricle_fem/f1r_data_qualification_v01_20260916
---

# F1-R 真实心肌细胞形态数据资格执行记录 v01

## 裁决

F1-R 数据资格为 `passed`，限定类别为 `real_static_morphology_resegmentable`。至少一个冻结的 72 hpf 心室样本同时具备可追溯个体、膜边界信号、物理尺度、可安全读取的 TIFF/MAT 文件和作者处理后的表面长轴信息。因此可以进入独立的逐细胞分割资格阶段。

这不等于已取得逐细胞实例标签或真实细胞网格。`Mask_Boundary.tif` 是组织区域 mask，数据包没有逐细胞 instance segmentation；本轮也没有运行分割模型、FEM、DCM、参数拟合或 GPU。

## 数据取得与完整性

- 按用户长期授权将公开大数据保存至 `E:\Data\PRL\public\zenodo\<record>`；PRL 仓内只保留约 1.7 MiB 的清单、摘要和预览。
- Zenodo `15509350` 的 `Analysis_codes.zip`、`GitHub_repository.zip` 和 `Data.zip` 分别为 40,886、317,730,085 和 8,013,661,132 bytes，本地 MD5 均与 Zenodo API 一致；同时登记本地 SHA-256。
- `Data.zip` 含 522 个成员，成员压缩量 8,013,512,414 bytes、展开逻辑量 15,698,172,813 bytes；0 路径穿越、0 绝对路径、0符号链接。未整包解压，也未执行上游代码。
- 数据包列出 5 个 72 hpf 和 5 个 120 hpf 个体。72 hpf Fish 1 的 `MasFull.tif` 和 Fish 2 的 `Analysis_Surface_Marker_X.mat.mat` 是上游文件名异常；Fish 3/4/5 的七个冻结必要文件名完整。
- 另行取得 Zenodo `5006918` 的 48 hpf 轻量动态序列，原包 38,099,253 bytes 且 MD5 一致；只作为以后周期图像处理预检的独立储备，没有参与本轮 72 hpf 裁决。

## 72 hpf 主样本

主样本固定为 `Data/Zebrafish/Fish_72hpf_4_Fig4-5/`。只读脚本直接从 ZIP 读取七个必要成员，不产生 15.7 GB 展开副本。

| 指标 | 结果 |
|---|---:|
| 栈形状 | 110 × 1024 × 1024，ZYX |
| 体素尺度 | 0.2071606 × 0.2071606 × 1 µm |
| 尺度交叉核对 | `SurfacePoints.mat` 与 `Marker_X.tif` ImageJ 元数据在 1e-6 µm 内一致 |
| 表面点 | 507 |
| 表面采样间距 | 10 µm |
| 粗粒化半径 | 17 µm |
| 局部 nematic order | 0.299143–0.995724 |
| 法向/方向单位长度 | 数值误差范围内通过 |

真实图像视觉 QA 为 `passed`：最大投影可见明显的非圆形、长轴化和相互铺砌的心肌轮廓；单切片、组织 mask、表面采样与 director 面板均可读，且标题明确标为真实数据资格而非模型结果。

## 元数据冲突与解释边界

论文方法把材料描述为 `Tg(myl7:BFP-CAAX); Tg(-0.2myl7:Lifeact-mNeongreen)`，膜信号用于细胞边界、LifeAct 用于 F-actin；TIFF 系列名却写 `BFP-CAAX H2B-mNG`。项目不推测哪一处是笔误，保留第二通道为 `Marker_X / biological identity unresolved`。该冲突不影响膜栈和尺度的资格，但在澄清前禁止把 `Marker_X` 解释为 F-actin。

论文报告样本在麻醉导致心脏停止后于十分钟内成像。因此本数据支持静态形态和长轴统计，不支持跳动周期、压力、材料参数或同鱼的运动学。不同阶段和其他公开数据只作为独立验证轴，不能拼接成同一实验轨迹。

## 工程与资源验收

- 资格脚本通过 `py_compile`，只使用安全的 ZIP/HDF5/TIFF 读取；未使用 pickle 或运行归档代码。
- 72 hpf 和 120 hpf 两张预览均已人工目检；72 hpf 摘要的两个尺度来源一致。
- 本轮结果包新增量低于 2 MiB；统一存储门后检为 9,007 个文件、1,653,493,076 逻辑字节，低于 3 GiB 硬上限。
- 单线程 CPU 数据读取；0 GPU、0 科学求解、0 自动科学重跑、0 删除、0安装、0提交、0推送。

## 入口与下一步

- [结果说明](../results/ventricle_fem/f1r_data_qualification_v01_20260916/README.md)
- [资格裁决](../results/ventricle_fem/f1r_data_qualification_v01_20260916/qualification.json)
- [72 hpf真实数据预览](../results/ventricle_fem/f1r_data_qualification_v01_20260916/primary_72hpf_fish4/real_data_structure_preview.png)
- [来源与双哈希](../results/ventricle_fem/f1r_data_qualification_v01_20260916/source_manifest.json)
- [公开数据分工图](public_zebrafish_experimental_data_map_v01.md)

唯一下一步是另立曲面逐细胞分割资格合同：先冻结少量人工标注留出集，再评价边界闭合、漏分割、并分割和跨个体稳定性，并输出质心、面积、长宽比、方向、局部有序度和邻接表。只有该门通过后，才定义 `measured / uniform-mean / shuffled` 的 FEM 映射；不会自动启动求解器。
