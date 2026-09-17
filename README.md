# PRL — 斑马鱼心室 FEM

目标是用FEM解释斑马鱼心室跳动及发育，逐步研究组织结构、生长、ECM和心内膜反馈。DCM不再运行、恢复或扩展；历史证据保留。精细逐细胞分割不是组织FEM的前置条件。

从[START_HERE](START_HERE.md)、[驾驶舱](memory/project_cockpit/index.html)、[专家材料索引](plan/INDEX.md)和[权威状态](project_control/CURRENT_STATUS.md)开始，遵循[工作约定](AGENTS.md)。

## 当前进展

F6-S1-P已执行：800 MiB阶段预算生效，复用3541单元合格网格；粗/细几何均通过。
零载passed；p/mu=0.02求解收敛但局部体积偏差6.71167%超过1%门，按合同停止。
保存2态、接受1态；其余8态及细网格力学未运行。计算腔面积+20.10718%仅为失败态诊断。
见[结构、形变应力、局部J及两帧动图](results/ventricle_fem/f6s1p_retained_passive_v01_20260917/index.html)和
[本次执行记录](project_control/ventricle_fem_fenicsx_retained_passive_execution_v01.md)。

最近通过的力学阶段保持如下：

F6-S0的FEniCSx运行时、被动与主动圆环资格均通过。两档896/3584个P2/P1三角形，26个唯一平衡态。
细网格四对照：零载0%、仅压力+9.8974%、仅主动−4.3150%、压力＋主动+4.5566%；均通过原1%局部体积门。
首次调用在十个被动态保存后发生读取错误，修复后仅补16个未运行主动态，原失败保留，0重复平衡求解。
见[结构、结果与动图](results/ventricle_fem/f6s0_active_completion_v01_20260917/index.html)和[完成记录](project_control/ventricle_fem_fenicsx_active_completion_execution_v01.md)。

上述力学结果仍是理想圆环、平面应变、未标定同质材料，不能代表斑马鱼实验拟合。
F5局部体积、F6-S1网格及F6-S1-M预算阻断原记录保留。下一步待确认：只计算尚未运行的
细网格0及0.02两态，检验局部离散精度，不改材料与1%J门，不重跑粗网格。

## 软件入口

```powershell
$env:PYTHONPATH = "$PWD\src"
$env:PYTHONDONTWRITEBYTECODE = "1"
python -B -X utf8 -m prl storage status --workspace .
python -B -X utf8 -m prl verify fem-fenicsx-ring --workspace . --result results/ventricle_fem/f6s0_active_completion_v01_20260917
python -B -X utf8 -m prl verify fem-fenicsx-contour --workspace .
python -B -X utf8 -m prl verify fem-fenicsx-contour --repair-thin-mesh --workspace .
python -B -X utf8 -m prl verify fem-fenicsx-contour --retained-passive --workspace .
python -B -X utf8 -m prl validate cockpit --workspace .
```

圆环verify完整G1/G2应返回passed；不带修复参数的轮廓verify重读原F6-S1并返回failed。
--repair-thin-mesh返回的是保存网格/预算核验passed，同时明确storage blocked、mechanics not_run，
不能误读为力学资格通过。--retained-passive重读本次保存态，应为failed，不自动重跑。
冻结图包不静默重绘。大型原始结果留在Git外。外置结果库的精确路径尚待确认，未迁移旧结果。

## 目录与安全

- `src/prl/fem/`：运动学、材料、单元、图像轮廓几何及压力接口。
- `src/prl/runs/`、`verification/`、`rendering/`：有界运行、独立复核和真实状态图。
- `project_control/`：合同与裁决；`plan/`只放外部专家材料。
- `results/ventricle_fem/`：FEM证据；`memory/project_cockpit/`只是状态投影。
- 原SimuCell3D及C++应用仅历史保留，不参与当前FEM。

只使用本地固定FEniCSx镜像，单CPU、0 GPU。项目2.4 GiB预警、3 GiB硬限；新阶段默认800 MiB加64 MiB保全余量，旧合同保持历史限额。公开大型数据按既有授权存E:\Data，不整包展开到项目。不自动删除或安装。阶段交付验收后直接本地提交`main`，不另开分支；远端推送按明确授权执行。
