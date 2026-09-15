# PRL — 三维细胞分辨心室模型

本仓库当前只维护受控 SimuCell3D 心肌→心内膜→ECM 三层主线。旧 Hybrid、Route H、Paper2/FEM 和 NCS 路线仅作为精选历史证据保留，不再是默认软件入口。

开始工作前依次阅读：

1. [START_HERE.md](START_HERE.md)；
2. [项目驾驶舱](memory/project_cockpit/index.html)；
3. [当前权威状态](project_control/CURRENT_STATUS.md)；
4. [外部专家计划索引](plan/INDEX.md)；
5. [项目执行规则](AGENTS.md)。

## 当前模型状态

当前模型为END端对端与SIDE侧邻双心肌细胞的三维闭合曲面DCM：每胞194节点、384面，使用皮质/体积/面积约束、恒定方向骨架、独立黏附与正间隙排斥；没有参考形状膜能、ECM、心内膜、腔压、夹持或周期收缩。

长程双胞数值资格为`passed`，但有限时域末态残力约0.104，静态平衡为`failed`；父Z1和生物学验证仍为`blocked`。这些状态不能由工程测试通过替代。

## 当前软件入口

稳定Python入口位于`src/prl/`，提供有界存储检查、独立核验、工程回归、驾驶舱维护，以及当前冻结科学合同的运行/验证/绘图入口：

```powershell
$env:PYTHONPATH = "$PWD\src"
python -B -X utf8 -m prl storage status --workspace .
python -B -X utf8 -m prl verify long-doublet --workspace .
python -B -X utf8 -m prl test quick --workspace .
python -B -X utf8 -m prl render cockpit --workspace .
python -B -X utf8 -m prl validate cockpit --workspace .
```

当前唯一科学任务使用分阶段、create-only命令；运行器会先检查清理裁决和存储准入，Q未通过时拒绝平衡阶段：

```powershell
python -B -X utf8 -m prl run contact-performance-equilibrium --phase q --workspace .
python -B -X utf8 -m prl verify contact-performance-equilibrium --phase q --workspace .
python -B -X utf8 -m prl run contact-performance-equilibrium --phase equilibrium --workspace .
python -B -X utf8 -m prl verify contact-performance-equilibrium --phase equilibrium --workspace .
python -B -X utf8 -m prl render contact-performance-equilibrium --workspace .
```

默认pytest仅收集当前`tests/prl/`：

```powershell
$env:PYTHONDONTWRITEBYTECODE = "1"
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD = "1"
$env:PYTHONPATH = "$PWD\src"
python -B -X utf8 -m pytest -q
```

只有上述`run`子命令会启动科研求解器；本合同强制单线程CPU且不自动重跑，所有其他命令均不启动求解器或GPU。

## 代码与证据边界

- `src/prl/`：当前稳定Python应用与验证入口；
- `src/prl_ventricle_support/`：不含物理方程迁移的C++应用支撑库；
- `external/simucell3d/`：唯一受控细胞表面、接触和重网格内核；
- `tests/prl/`：默认当前工程测试；
- `plan/`：外部专家原件、来源和哈希；
- `project_control/`：采纳决定、合同、执行与失败记录；
- `project_control/evidence/retired_routes_v01/`：旧路线精选证据与保全源码；
- `results/`：正式计算结果和摘要；
- `memory/project_cockpit/`：状态投影，不替代权威证据；
- `tmp/`：非权威临时产物，不得存放唯一成果。

旧路线的详细过程仍由`project_control/`和精选证据解释。不要从历史脚本、文件名中的`latest/final/pass`或已退役命令推断当前状态。

## 存储与执行边界

项目存储预警线为2.4 GiB、硬上限为3 GiB；当前仍超过硬上限，因此新科研任务保持`blocked`。[一次性收口审批包](project_control/repository_cleanup_closure_and_science_restart_proposal_v01.md)已冻结31个精确目标，但尚未取得删除与CPU运行确认。程序不自动删除证据；只有收口、独立验收和接触性能门全部通过，才会进入冻结的扩展双胞科学切片。
