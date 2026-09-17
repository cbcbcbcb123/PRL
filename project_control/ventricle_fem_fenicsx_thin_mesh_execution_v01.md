---
document_id: PRL-FEM-FENICSX-THIN-MESH-EXECUTION-V01
status: blocked
contract: project_control/ventricle_fem_fenicsx_thin_mesh_contract_v01.md
result: results/ventricle_fem/f6s1m_thin_mesh_v01_20260917
geometry_gate: passed
storage_admission: blocked
passive_mechanics: not_run
active_mechanics: not_run
equilibrium_solves: 0
---

# F6-S1-M：网格已修复，完整输出预算阻断求解

用户确认继续有界薄层网格修复。一次正式容器13.698秒、最多三个预声明候选，
0平衡求解，0自动重跑。原调用以异常/failed退出，原failure.json不改写；
经独立重读，物理前的实际阻断是存储准入，不是网格仍失败或材料失稳。

## 已验证的进展

原最薄层间距0.01041762，统一目标边长0.09为其8.64倍。将边界尺寸改为
min(0.09,c×到相邻层界的最短距离)，保持同一128段源多边形、层界、剖分算法、
材料、载荷、20度及1%局部J门不变。结果支持此前的尺寸适配假设。

| 网格 | 三角形 | 最小角 | 几何门 | 十态输出预算预测 |
|---|---:|---:|---|---:|
| 原F6-S1 | 1828 | 12.8687° | failed | 本次不重复计算 |
| c=1.2 | 3541 | 23.0435° | passed | 307.35 MiB |
| c=0.9 | 5085 | 26.2953° | passed | 420.44 MiB |
| c=0.7 | 6949 | 20.7516° | passed | 556.96 MiB |

三候选坏角单元均为0；所有正面积、共享层界、连通性、构造层面积等门均通过。
源mask IoU保持99.5882%，原始轮廓采样Hausdorff保持1.66974微米。
加密并不单调提高最小角，故不再盲目加密。最小合格候选应优先复用。

## 为什么没有压力/形变/应力结果

三候选全部超过本轮256 MiB阶段准入上限。预测按粗/细两档（1+4倍单元）、
每档5个压力状态、12积分点、32标量×8 bytes、另加48 MiB图件与控制余量计算。
最小候选为322,280,448 bytes，超出原限53,844,992 bytes（51.35 MiB）。
这只是保守的未压缩输出预测，不是实际文件体积、RAM不足或磁盘已经写满。
按合同完成三个纯几何候选后停止，没有创建Ring求解器或运行SNES。

全部候选通过几何，但没有一个通过预算并获准送入求解器。
raw/M0_input_mesh.npz是调用停止时最后一个候选，不是推荐的最小网格。
后续应明确读取raw/candidate_0_mesh.npz，不得误用最后候选。

## 证据与交付

260个父包文件SHA-256保持，原F6-S1、F5失败及F6-S0通过包均未改变。
固定本地镜像、1 CPU、8 GiB、禁网、只读根、无GPU等容器约束全部核验通过。
独立验证器重新读取三份原始网格、重算几何和预算；开发回归47项及21子测试通过。
图由保全网格和预算生成，不调用Gmsh或力学求解器；遵循绘图技能保存逐字节数据副本、
可编辑Notebook、样式/代码快照、600dpi PNG与SVG，执行、样式及目检分别验收。

[图件及Notebook](../results/ventricle_fem/f6s1m_thin_mesh_v01_20260917/index.html) ·
[独立核验](../results/ventricle_fem/f6s1m_thin_mesh_v01_20260917/verification.json) ·
[交付与空间审计](../results/ventricle_fem/f6s1m_thin_mesh_v01_20260917/delivery_audit.json)。

## 唯一下一步（待确认，不自动执行）

复用已合格的candidate_0，不重做三候选。建议仅将下一被动资格阶段预算从默认
256 MiB特批到384 MiB（停止保全另留64 MiB；项目3 GiB硬上限不变），
执行原两档网格×5个压力的十态矩阵。源几何、材料、压力、时间上限和原力学门不变。
保留完整状态和失败证据，首个力学失败即停；仍不加入主动收缩。
如果不批准阶段预算调整，则先做无科学求解的数据布局预算审计，不自动开跑。

临时保留目录为E:\Temp-Projects\PRL\results\ventricle_fem\f6s1m_thin_mesh_v01_20260917\figure_runtime，
仅属于本次图件执行缓存；任何清理仍须精确清单确认。没有删除、安装、GPU、项目外新建或推送。
阶段按既有决定本地提交main。
