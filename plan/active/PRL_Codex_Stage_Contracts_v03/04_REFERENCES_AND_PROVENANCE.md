# 资料来源、核查范围与 v03 变更说明

## 1. 母文档与证据边界

本包由用户已提供的 v02 拆解并补成执行合同。原文按字节保留在 [sources/v02_original.md](sources/v02_original.md)。v03 没有访问用户 Windows PRL、M1 完整运行包或 `muse_dcm` 源码；所有计算阶段仍 NOT_RUN。来源网页可访问不等于 Z0 已完成，合同检查不等于求解器验证。

2026-09-10 对下列公开 HTML 页面/摘要与仓库说明做了有限复核；不是穷尽性文献检索，没有把所有论文算法逐行复现。Codex 正式引用/实现时应保存具体版本、可访问原文、许可和使用范围。

## 2. 一手来源登记

| ID | 标识与入口 | 本包用途 | 不能推断 |
|---|---|---|---|
| R1 | Glasgow, Multiview-SPIM-μPIV for mapping 3C-3D blood flow within beating zebrafish heart. DOI 10.5525/gla.researchdata.2322。`https://researchdata.gla.ac.uk/2322/` | 官方文件清单/来源；记录小影像/代码及大数据申请限制 | 年龄、完整细胞膜和全周期壁运动均已齐备 |
| R2 | 作者仓库 JJ473/BOE_multiview_SPIM_PIV。`https://github.com/JJ473/BOE_multiview_SPIM_PIV` | 处理速度快照、位置/速度/不确定度数组及分析说明 | 数组已由本包下载验证、与全部壁相位已配准 |
| R3 | Hong BD 等，Modeling left ventricular dynamics with characteristic deformation modes，2019。DOI 10.1007/s10237-019-01168-8。`https://link.springer.com/article/10.1007/s10237-019-01168-8` | 理想构型、低维变形和整体/局部比较线索 | 人体左室参数可直接用于斑马鱼 |
| R4 | Van Liedekerke P 等，A quantitative high-resolution computational mechanics cell model for growing and regenerating tissues，2020，online 2019。DOI 10.1007/s10237-019-01204-7。`https://link.springer.com/article/10.1007/s10237-019-01204-7` | 三维细胞网络、被动/接触/组织标定与分裂思路；核对阻尼语义 | 心肌主动周期收缩和本项目 FSI 已通过 |
| R5 | Quirós Rodríguez A 等，A Conservative Cartesian Cut Cell Method for the Solution of the Incompressible Navier-Stokes Equations on Staggered Meshes。arXiv:2211.10698。`https://arxiv.org/abs/2211.10698` | 守恒交错切割算子、离散结构参考 | 本项目三维移动几何与状态转移已经完成 |
| R6 | Battista NA 等，Fluid Dynamics in Heart Development: Effects of Hematocrit and Trabeculation。arXiv:1610.07510。`https://arxiv.org/abs/1610.07510` | 既有心脏流体工作及模型边界参考 | 与本路线三维主动细胞双向耦合完全等价 |
| R7 | Serino DA 等，AMP model problem analysis，arXiv:1812.03192；完整算法 arXiv:1812.05208。`https://arxiv.org/abs/1812.03192`；`https://arxiv.org/abs/1812.05208` | 附加质量/阻尼稳定性和独立 FSI 基准线索 | 弹性连续体算法可未经推导直接保证过阻尼 DCM 稳定 |
| R8 | 用户给定 Zenodo 记录 15627197。`https://zenodo.org/records/15627197` | 备用资料入口 | 本次访问未成功，文件内容/数量/体量不重新确认为事实 |
| R9 | Libat L 等，A space-time extension of a conservative two-fluid cut-cell method for moving diffusion problems。arXiv:2512.23358v2。`https://arxiv.org/abs/2512.23358v2` | 规定运动下时空控制体与单元生灭的补充线索 | 方程为扩散，不是完整不可压缩 Navier–Stokes 或本项目 FSI |

R1 官方当前记录列出两个约 5 MB 相位影像和约 6 MB 代码，约 37 GB 大数据需申请；Z0 仍须实际读取小文件并核对单位、年龄和相位。R2 的 README 说明快照含三组位置、速度及不确定度数组；这只是可读性入口，不是本包已取得配对生物证据。

v02 对 R9 标题的描述保留在原文件；本表采用本次页面显示的正式标题，不据此改变任何计算状态。

## 3. 本包新增测试与公式的来源性质

Poiseuille、振荡通道、制造解、活塞和 SLS 等式在对应阶段给定方程及适用边界，是用于独立验证的解析/直接推导合同，不是实验曲线。Codex 需先用独立解析/符号程序检验，再作为求解器参考。制造源项不得由待验离散算子自身生成。

Z11 有限矩沉积记忆方程由同连接共同参数的线性逐批 SLS 方程直接求和，适用范围已写清；不是声称发现或实现了任意非线性 ECM 重塑理论。与逐批独立参考一致性、正性及能量验收仍 NOT_RUN。

文档生产时对部分代数关系所做的编辑性检查只属于文档 QA，不是 PRL 或 `muse_dcm` 实验。原始/模拟快照、CPU 测量、求解残差与生物误差必须由未来实际运行产生。

## 4. v02 → v03 的主要扩展

保持路线与 Z0–Z11 编号，将 Z4b、Z6a/b/c、Z9a/b、Z10b 拆为单独文件；Z6/Z9 是控制入口，避免一份长指令自动跨关。

每阶段新增：可执行任务顺序、必需算例/对照、边界/载荷、参考解或独立检查、主要读出、可视化清单、原始数据、异常处理和明确停止点。保留现有质量10^-3、能量1%、整体/局部2%/5% 等主阈值，新增合成单元测试阈值和资源保护值必须首次正式前冻结。

统一可视化明确 `file://` 离线双击、小型展示副本与原始数据分离、真实时间/版本同步、字段缺失与零值分离。恢复/检查点保存完整内变量，不只网格。

本包选择当前构型零应力沉积作为 Z11 的默认合成材料机制，并保留旧参考态增量为对照；这属于执行细化，不是生物事实。已有批准机制不同时必须按变更合同处理，不能在程序里静默替换。

## 5. 内部资料

用户原文的 M1 路径、Hong/肝脏 PDF 路径和 Casebook 摘要均为待本地核验线索。本包未重新判 PASS/FAIL，也未处理用户本地 PDF 字节。复制公共论文、数据或第三方代码须保留许可，不把它们改名为项目原创。
