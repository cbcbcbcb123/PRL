---
document_id: PRL-F6-S2-D2A-MESH-QUALITY-EXECUTION-V01
status: passed
date: 2026-09-18
scientific_pressure_gate: failed
causal_identification: unknown
new_FEM_solves: 0
unstructured_mesh: not_run
contract: project_control/ventricle_fem_3d_mesh_quality_contract_v01.md
---

# 网格形状已改善，但不能单独解释基底局部体积误差

本次只对已有M0/M1参考网格和p/mu=0.01、Ta=0完整u/p做离线重算。
诊断交付passed不等于三维加载资格passed；两原压力态均failed，未新增平衡解。

## 定量结果

| 指标 | M0 | M1 |
|---|---:|---:|
| 四面体 | 1344 | 3960 |
| 最小内部二面角 | 4.410972° | 6.637914° |
| q=3r/R最小值（正四面体为1） | 0.151387 | 0.222035 |
| q中位数 | 0.284540 | 0.327222 |
| 正则参考映射最大条件数 | 19.542528 | 12.981101 |
| 形状筛查标记单元 | 545 | 600 |
| 原1%体积门超限单元 | 96 | 120 |
| 同时形状标记与体积超限 | 96 | 48 |
| 远离基底的形状标记单元 | 289 | 384 |
| 远离基底的体积超限单元 | 0 | 0 |
| 原max abs(J-1) | 1.522743% | 1.449560% |

形状筛查预先取q<0.2或最小内部二面角<10°，只用于定位，不是通用合格门。
正则参考映射条件数不是组装刚度矩阵或混合系统条件数；参考几何Jacobian也不是变形J。
完整逐单元数据、各层/基底分区分布、12个最严重体积单元和描述性相关系数均保留。

## 能确定什么

1. M1形状度量总体改善，仍存在小二面角；仅凭单元正体积不能完成网格质量审查。
2. M1仍各只有1个心内膜/ECM径向区间；不是各方向、各薄层都充分细化。
3. 全部120个M1体积超限单元邻接固定基底，但只有48个同时触发形状筛查。
   另72个超限单元未触发筛查；384个远区形状标记单元却没有一个超体积门。
   因而“形状差”这一筛查条件既不能充分解释，也不能完整识别当前误差热点。
4. 全体q与体积误差的描述性Spearman为M0=-0.4850、M1=-0.6175；
   在薄层且基底相邻的分层子集中符号反而为正（约+0.52至+0.61）。
   这提示位置/层别与网格质量混杂，不能把合并相关性当因果，更不能把FE单元当生物重复。
5. 尚未分离网格拓扑、局部分辨率、基底约束和P1连续压力表示的贡献。
   本次不认定基底“错误”，不认定换非结构化即可解决，不改变原门限。

## 实现、验证与图件

新增独立tetra_quality度量和create-only离线入口，原生产力学/几何/协议/原力学验证器哈希不变。
正四面体解析值、24种重编号、刚体变换和尺度不变性、退化及筛查不替代物理门测试通过。
定向回归121项、21项子测试passed；逐单元重算与保留数组完全一致。
图件包含实际结构/形状质量、同单元J误差和全部单元散点；共同色标、参考坐标对齐、无平滑。
只有原粗细两压力态，不补造时间点；是离线诊断，不是心动、生长或FSI模拟。
使用cb-diagnose组织可证伪诊断；cb-paper-figure-workflow和cb-plot-unified-style组织
真实数据、独立代码快照、Notebook、600dpi PNG/SVG、样式与目检验收。

主机find_spec未发现Gmsh/TetGen；唯一既有镜像依赖探针发现gmsh模块。
探针只读根、1CPU、禁网、0GPU，ExitCode=0；未导入本机库、生成网格或求解。
Gmsh实际可导入并生成所需三域共形网格仍not_run，不以模块存在宣称准备完全就绪。
没有启动/修复Docker、安装、拉取、删除、自动重跑或推送。

结果：[外置证据与图](../../PRL-results/ventricle_fem/f6s2d2a_mesh_quality_v01_20260918/index.html)。
逐单元：cell_metrics.npz；报告：quality_report.json；验收：delivery_audit.json。
复算：`python -B -X utf8 -m prl verify fem-mesh-quality`，预期诊断passed、科学压力门仍failed。
包哈希/大小及保护项后验记录在result_index和交付验收，不改原失败包。
tmp/f6s2d2a_checks仅本次测试/Jupyter/绘图缓存，保留未删除。

## 下一步

先冻结同一M1多面体边界及层界的内部非结构化剖分资格，保持所有力学量与约束。
见[候选合同](ventricle_fem_3d_unstructured_comparison_contract_v01.md)。
不同时改变曲面、壁厚分辨率、压力空间或基底，不将“更不规则”当质量验收。
