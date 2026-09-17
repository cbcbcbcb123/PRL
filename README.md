# PRL — 斑马鱼心室 FEM

目标是用FEM解释斑马鱼心室跳动及发育，逐步研究组织结构、生长、ECM和心内膜反馈。DCM不再运行、恢复或扩展；历史证据保留。精细逐细胞分割不是组织FEM的前置条件。

从[START_HERE](START_HERE.md)、[驾驶舱](memory/project_cockpit/index.html)、[专家材料索引](plan/INDEX.md)和[权威状态](project_control/CURRENT_STATUS.md)开始，遵循[工作约定](AGENTS.md)。

## 当前进展

F6-S1已接回真实外轮廓，但在网格门停止：1828单元中45个低于20度，最差12.8687度，
全部位于薄构造心内膜/ECM层；图像重合与层界连通通过。0个新平衡态，位移/应力/压力响应not_run。
见[当前结构及质量诊断图](results/ventricle_fem/f6s1_contour_passive_v01_20260917/index.html)和
[本次执行记录](project_control/ventricle_fem_fenicsx_contour_passive_execution_v01.md)。

最近通过的力学阶段保持如下：

F6-S0的FEniCSx运行时、被动与主动圆环资格均通过。两档896/3584个P2/P1三角形，26个唯一平衡态。
细网格四对照：零载0%、仅压力+9.8974%、仅主动−4.3150%、压力＋主动+4.5566%；均通过原1%局部体积门。
首次调用在十个被动态保存后发生读取错误，修复后仅补16个未运行主动态，原失败保留，0重复平衡求解。
见[结构、结果与动图](results/ventricle_fem/f6s0_active_completion_v01_20260917/index.html)和[完成记录](project_control/ventricle_fem_fenicsx_active_completion_execution_v01.md)。

模型仍是无量纲理想圆环、平面应变、未标定同质材料，不能代表斑马鱼实验拟合。
F5图像外轮廓局部体积失败保留。下一步F6-S1-M先修薄层局部网格，保持原物理及20度/1%J门；
新的有界尝试待确认。几何通过后才运行被动压力，之后再考虑主动收缩。

## 软件入口

```powershell
$env:PYTHONPATH = "$PWD\src"
$env:PYTHONDONTWRITEBYTECODE = "1"
python -B -X utf8 -m prl storage status --workspace .
python -B -X utf8 -m prl verify fem-fenicsx-ring --workspace . --result results/ventricle_fem/f6s0_active_completion_v01_20260917
python -B -X utf8 -m prl verify fem-fenicsx-contour --workspace .
python -B -X utf8 -m prl validate cockpit --workspace .
```

圆环verify只读引用父被动态和续算主动态，完整G1/G2应返回passed。当前轮廓verify应返回failed，
不能把其非零退出当作需要自动重跑。结果不得覆盖重跑；冻结图包不静默重绘。历史失败保留。

## 目录与安全

- `src/prl/fem/`：运动学、材料、单元、图像轮廓几何及压力接口。
- `src/prl/runs/`、`verification/`、`rendering/`：有界运行、独立复核和真实状态图。
- `project_control/`：合同与裁决；`plan/`只放外部专家材料。
- `results/ventricle_fem/`：FEM证据；`memory/project_cockpit/`只是状态投影。
- 原SimuCell3D及C++应用仅历史保留，不参与当前FEM。

只使用本地固定FEniCSx镜像，单CPU、0 GPU。项目2.4 GiB预警、3 GiB硬限；F6-S0为128 MiB阶段上限加64 MiB保全余量。公开大型数据按既有授权存E:\Data，不整包展开到项目。不自动删除或安装。阶段交付验收后直接本地提交`main`，不另开分支；远端推送按明确授权执行。
