# PRL — 斑马鱼心室 FEM

目标是用FEM解释斑马鱼心室跳动及发育，逐步研究组织结构、生长、ECM和心内膜反馈。DCM不再运行、恢复或扩展；历史证据保留。精细逐细胞分割不是组织FEM的前置条件。

从[START_HERE](START_HERE.md)、[驾驶舱](memory/project_cockpit/index.html)、[专家材料索引](plan/INDEX.md)和[权威状态](project_control/CURRENT_STATUS.md)开始，遵循[工作约定](AGENTS.md)。

## 当前进展

F6-S1-M薄层网格修复通过：最小候选3541单元、最小角23.0435度，原45个坏角单元降至0，
图像外轮廓与共享层界保持。十态完整输出预测307.35 MiB超过本轮256 MiB准入上限，
故0个新平衡态，位移/应力/压力响应not_run；不是材料失稳或RAM不足。
见[结构、质量及预算图](results/ventricle_fem/f6s1m_thin_mesh_v01_20260917/index.html)和
[本次执行记录](project_control/ventricle_fem_fenicsx_thin_mesh_execution_v01.md)。

最近通过的力学阶段保持如下：

F6-S0的FEniCSx运行时、被动与主动圆环资格均通过。两档896/3584个P2/P1三角形，26个唯一平衡态。
细网格四对照：零载0%、仅压力+9.8974%、仅主动−4.3150%、压力＋主动+4.5566%；均通过原1%局部体积门。
首次调用在十个被动态保存后发生读取错误，修复后仅补16个未运行主动态，原失败保留，0重复平衡求解。
见[结构、结果与动图](results/ventricle_fem/f6s0_active_completion_v01_20260917/index.html)和[完成记录](project_control/ventricle_fem_fenicsx_active_completion_execution_v01.md)。

上述力学结果仍是理想圆环、平面应变、未标定同质材料，不能代表斑马鱼实验拟合。
F5局部体积及F6-S1网格失败保留。下一步待确认：复用candidate_0，下一被动阶段特批384 MiB、
另64 MiB停止空间，项目3 GiB硬限保持；执行原十态，不改物理与20度/1%J门，之后再考虑主动收缩。

## 软件入口

```powershell
$env:PYTHONPATH = "$PWD\src"
$env:PYTHONDONTWRITEBYTECODE = "1"
python -B -X utf8 -m prl storage status --workspace .
python -B -X utf8 -m prl verify fem-fenicsx-ring --workspace . --result results/ventricle_fem/f6s0_active_completion_v01_20260917
python -B -X utf8 -m prl verify fem-fenicsx-contour --workspace .
python -B -X utf8 -m prl verify fem-fenicsx-contour --repair-thin-mesh --workspace .
python -B -X utf8 -m prl validate cockpit --workspace .
```

圆环verify完整G1/G2应返回passed；不带修复参数的轮廓verify重读原F6-S1并返回failed。
--repair-thin-mesh返回的是保存网格/预算核验passed，同时明确storage blocked、mechanics not_run，
不能误读为力学资格通过。结果不得覆盖重跑；冻结图包不静默重绘。大型原始结果留在Git外。

## 目录与安全

- `src/prl/fem/`：运动学、材料、单元、图像轮廓几何及压力接口。
- `src/prl/runs/`、`verification/`、`rendering/`：有界运行、独立复核和真实状态图。
- `project_control/`：合同与裁决；`plan/`只放外部专家材料。
- `results/ventricle_fem/`：FEM证据；`memory/project_cockpit/`只是状态投影。
- 原SimuCell3D及C++应用仅历史保留，不参与当前FEM。

只使用本地固定FEniCSx镜像，单CPU、0 GPU。项目2.4 GiB预警、3 GiB硬限；F6-S1-M阶段256 MiB加64 MiB保全余量，尚未批准增加。公开大型数据按既有授权存E:\Data，不整包展开到项目。不自动删除或安装。阶段交付验收后直接本地提交`main`，不另开分支；远端推送按明确授权执行。
