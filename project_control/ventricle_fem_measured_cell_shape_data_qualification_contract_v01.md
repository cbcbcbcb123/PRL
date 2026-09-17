---
document_id: PRL-FEM-F1R-MEASURED-CELL-SHAPE-DATA-QUALIFICATION-CONTRACT-V01
status: adopted
authorized_at: 2026-09-16
authorization: user allowed the public data download and established E:\Data as the classified large-data root
gpu: forbidden
scientific_solver_runs: 0
automatic_retries: 0
---

# F1-R｜真实心肌细胞形态数据资格合同 v01

## 本轮问题与边界

本轮只判断公开数据能否形成带来源、物理尺度和可分割证据的斑马鱼心室心肌细胞形态场。它是 F1-S 合成方向场之后的数据门，不运行 FEM、DCM、分割模型训练、参数拟合、组织生长、ECM 反馈或 GPU 任务。

第一目标固定为 `72 hpf` 斑马鱼心室外层致密心肌；`120 hpf` 作为后续发育阶段外推或留出比较，不与 72 hpf 混合拟合。若数据包不能区分心脏、阶段或通道，则相应子项为 `blocked_data`，不得从论文图名猜测。

## 首选来源

- 记录：Zenodo `10.5281/zenodo.15509350`，版本日期 `2025-05-27`，记录更新 `2025-08-15`。
- 标题：*Capturing Nematic Order on Tissue Surfaces of Arbitrary Geometry*。
- 许可：Zenodo API 标记 `CC BY 4.0`；文章许可与数据许可分别记录。
- 上游代码：`https://github.com/Julia-Eckert/3D_SurfProps`，只做静态审计。
- 外置根：`E:\Data\PRL\public\zenodo\15509350`。

冻结的上游文件为：

| 文件 | 字节数 | 上游 MD5 |
|---|---:|---|
| `Analysis_codes.zip` | 40,886 | `5e08495b92b9968508d443194fea1991` |
| `GitHub_repository.zip` | 317,730,085 | `ec0eda17034657bb49c5b8f078970a64` |
| `Data.zip` | 8,013,661,132 | `fc94a41c8654b817cdbe5cd131f4a90c` |

采用可续传下载；只有本地字节数和 MD5 与上游同时一致才记为 `acquired_verified`。中断但可续传的文件记为 `partial`，不得解包或分析。

## 资格检查

1. 只读列出归档成员并检查绝对路径、父目录跳转、符号链接或其他异常成员；不直接执行归档中的脚本。
2. 建立逐文件来源表，区分 raw、preprocessed、mask、surface、director、curvature、F-actin 和 figure-only 产物。
3. 核对每个心脏的阶段、个体 ID、转基因标记、通道、体素间距、轴顺序、单位、处理历史及是否有独立细胞边界。
4. 论文和作者代码报告的示例体素间距 `0.2071606 × 0.2071606 × 1 µm` 只作为待核对输入；须由数据内元数据、README 或明确的上游说明确认后才能用于模型。
5. 检查数据实际覆盖的心脏数。论文的统计样本量不能替代数据包逐样本清单。
6. 若只有组织膜强度和方向场而无逐细胞实例分割，允许进入“可重新分割”资格，但不得声称已取得真实逐细胞网格。
7. 不把本数据与 Glasgow 跳动/血流数据默认为同鱼、同相位或已配准；运动学验证另立合同。

## 通过门与输出

数据资格记为 `passed` 仅当至少一个 72 hpf 心室样本同时具备：可追溯个体文件、明确膜通道、物理尺度、足够的外层致密心肌边界信号以及可安全读取的格式。若只能取得论文汇总方向或曲率，状态为 `partial`；若阶段、尺度或边界信号缺失，状态为 `blocked_data`。

本轮交付：

- 上游与本地双哈希清单；
- 归档成员清单及安全检查；
- 样本/阶段/通道/尺度资格表；
- 至少一张来自真实数据的结构预览图；
- `72 hpf measured / uniform-mean / shuffled` 后续映射所需字段清单；
- 数据缺项、许可和可发表主张边界。

资格通过也不等于分割、FEM 映射或生物验证通过。本轮结束后先提交数据资格结果和下一阶段精确合同，不自动启动科学求解。

