# PRL — 斑马鱼心室 FEM

目标是用FEM解释斑马鱼心室跳动及发育，逐步研究组织结构、生长、ECM和心内膜反馈。DCM不再运行、恢复或扩展；历史证据保留。精细逐细胞分割不是组织FEM的前置条件。

从[START_HERE](START_HERE.md)、[驾驶舱](memory/project_cockpit/index.html)、[专家材料索引](plan/INDEX.md)和[权威状态](project_control/CURRENT_STATUS.md)开始，遵循[工作约定](AGENTS.md)。

## 当前进展

F6-S1-Q已完成细网格14164单元的零载/0.02两态，粗网格3541单元不重跑。
加密后局部体积峰值6.71167%→11.15248%，仍超1%门；超限参考体积分数0.48565%→0.14100%。
两档腔面积响应只差0.01387个百分点，但局部门未通过，不能接受为已验证响应。
一次40.770秒容器保存2态、接受1态，无自动重试或主动收缩。
见[本地结构、应力、粗细局部J及两帧动图](../PRL-results/ventricle_fem/f6s1q_fine_diagnostic_v01_20260917/index.html)和
[本次执行记录](project_control/ventricle_fem_fenicsx_fine_diagnostic_execution_v01.md)。大图与原始数据不随GitHub同步。

最近通过的力学阶段保持如下：

F6-S0的FEniCSx运行时、被动与主动圆环资格均通过。两档896/3584个P2/P1三角形，26个唯一平衡态。
细网格四对照：零载0%、仅压力+9.8974%、仅主动−4.3150%、压力＋主动+4.5566%；均通过原1%局部体积门。
首次调用在十个被动态保存后发生读取错误，修复后仅补16个未运行主动态，原失败保留，0重复平衡求解。
见[结构、结果与动图](results/ventricle_fem/f6s0_active_completion_v01_20260917/index.html)和[完成记录](project_control/ventricle_fem_fenicsx_active_completion_execution_v01.md)。

上述力学结果仍是理想圆环、平面应变、未标定同质材料，不能代表斑马鱼实验拟合。
历史失败原记录保留。下一步待确认：边界拐角与局部体积约束离散的最小分离对照；
不盲目再加密、不改材料与1%J门，不继续加压或主动收缩。

## 软件入口

```powershell
$env:PYTHONPATH = "$PWD\src"
$env:PYTHONDONTWRITEBYTECODE = "1"
python -B -X utf8 -m prl storage status --workspace .
python -B -X utf8 -m prl verify fem-fenicsx-ring --workspace . --result results/ventricle_fem/f6s0_active_completion_v01_20260917
python -B -X utf8 -m prl verify fem-fenicsx-contour --workspace .
python -B -X utf8 -m prl verify fem-fenicsx-contour --repair-thin-mesh --workspace .
python -B -X utf8 -m prl verify fem-fenicsx-contour --retained-passive --workspace .
python -B -X utf8 -m prl verify fem-fenicsx-contour --fine-diagnostic --workspace .
python -B -X utf8 -m prl validate cockpit --workspace .
```

圆环verify完整G1/G2应返回passed；不带修复参数的轮廓verify重读原F6-S1并返回failed。
--repair-thin-mesh返回的是保存网格/预算核验passed，同时明确storage blocked、mechanics not_run，
不能误读为力学资格通过。--retained-passive和--fine-diagnostic重读对应保存态，应为failed，不自动重跑。
冻结图包不静默重绘。后续大型结果使用已批准的`E:\Temp-Projects\PRL-results`，不进入Git；旧结果保持原位。
当前FEniCSx轮廓输出接口及主机/Docker读写已验收；旧阶段ID仍拒绝重跑，新增科学阶段须按合同授权。

## 目录与安全

- `src/prl/fem/`：运动学、材料、单元、图像轮廓几何及压力接口。
- `src/prl/runs/`、`verification/`、`rendering/`：有界运行、独立复核和真实状态图。
- `project_control/`：合同与裁决；`plan/`只放外部专家材料。
- `results/ventricle_fem/`：既有FEM证据，不迁移；新结果在`E:\Temp-Projects\PRL-results\ventricle_fem/`。
- `project_control/result_storage_policy.json`：唯一结果根配置；`result_index/`保留小型路径与哈希索引。
- `memory/project_cockpit/`只是状态投影。
- 原SimuCell3D及C++应用仅历史保留，不参与当前FEM。

只使用本地固定FEniCSx镜像，单CPU、0 GPU。代码仓2.4 GiB预警、3 GiB硬限；外置新结果无固定阶段体积上限，准入要求磁盘余量足够容纳预计输出、至少64 MiB保全空间及10 GiB安全余量。运行时限、首失败停止、不自动重跑保持；旧合同不追溯修改。见[存储决定与边界](project_control/external_result_store_decision_v01.md)。公开大型数据按既有授权存E:\Data，不整包展开到项目。不自动删除或安装。阶段交付验收后直接本地提交`main`，不另开分支；远端推送按明确授权执行。
