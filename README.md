# PRL — 斑马鱼心室 FEM

用FEM研究斑马鱼心脏发育、心动与血流相互作用。先使用理想化三维模型及公开资料，
后续以自有实验替换；不恢复DCM。路线为三维固体 → 规定式生长 → 双向FSI → 力学生长/ECM反馈。
当前尚未完成三维加载资格，不能宣称已模拟真实实验心跳。

## 最新进展（2026-09-19）

**v03正J候选步保护核验通过，但场精度和高κ平衡仍未通过。**

- 当前是三维P2位移/P1压力四面体的单位立方体制造解基准，不是心室收缩计算。
- 6次求解尝试、5个有效平衡终态、2例未运行；31条接受路径独立安全核验通过。
- κ=100最细网格位移H1误差43.65%仍超15%门；κ=1000粗网格接近退化，保护拒绝不安全候选后停止。
- 原三域半椭球心室局部体积最大偏差1.4496%仍超1%门。三维主动、生长、FSI未运行。
- 唯一下一步：先用保存态区分制造载荷积分与混合压力约束的误差放大，再决定新对照；不放宽原门。

[专家在线审阅：模型、结果表、图件与代码入口](docs/review/mixed_cube_benchmark_v03_20260919/README.md)

![当前基准结构、误差与安全诊断](docs/review/mixed_cube_benchmark_v03_20260919/diagnostic.png)

图为冻结计算的真实结果，Newton迭代不是生理时间。安全实现passed不等于整体数值或生物学资格passed。

## 导航与复核

- [项目目标、当前模型及唯一下一步](START_HERE.md)
- [当前权威状态与历史证据](project_control/CURRENT_STATUS.md)
- [本阶段执行裁决](project_control/ventricle_mixed_cube_benchmark_v03.md)
- [外部专家材料索引](plan/INDEX.md) / [工作约定](AGENTS.md)
- [阶段提交与普通远端同步规则](project_control/main_branch_stage_push_decision_v01.md)

源码在 `src/prl/fem/`，运行、独立验证和绘图分别在 `src/prl/runs/`、`src/prl/verification/`、
`src/prl/rendering/`，测试在 `tests/prl/`。合同与裁决在 `project_control/`；`plan/`仅放外部专家材料。

完整原始结果留在已批准的 `E:\Temp-Projects\PRL-results`，不随Git同步。
本仓保留代码、合同、小型审阅摘要和必要PNG预览；仅克隆仓库不足以独立复算全部保存态。
`memory/project_cockpit/status.json`是状态投影，HTML驾驶舱仅在拥有本地证据时渲染，不作为GitHub唯一入口。

具备本地结果的工作区可只读核对驾驶舱证据链接：

```powershell
$env:PYTHONPATH = "$PWD\src"
$env:PYTHONDONTWRITEBYTECODE = "1"
python -B -X utf8 -m prl validate cockpit --workspace .
```

## 执行边界

阶段交付检查后直接提交main并普通推送origin/main；不强推、不更新其他分支或标签，
不纳入无关旧改动。完整原始数据、大型结果、构建与缓存不上传。
计算仍遵守独立授权、固定FEniCSx镜像、单CPU、0 GPU、首失败停止与不自动重跑。

代码仓2.4 GiB预警、3 GiB硬限；外置结果按[存储决定](project_control/external_result_store_decision_v01.md)
使用磁盘余量保护。无自动删除、安装或旧路线恢复。
