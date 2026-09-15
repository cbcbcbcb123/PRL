---
execution_id: T1.1R-ECM-THICKNESS-CONVERGENCE-EXECUTION-V01
plan_id: T1.1R-ECM-THICKNESS-CONVERGENCE-CONTRACT-V01
executor: codex_primary_single_agent
started_at: 2026-08-12
completed_at: 2026-08-12
status: completed
scientific_gate: passed
inspection_status: pending_human_final_review
deviation_records: []
---

# T1.1R ECM 厚度收敛修复执行记录 v01

## 1. 批准计划

执行依据为 `project_control/t1_1r_ecm_thickness_convergence_contract_v01.md`。本轮只增加 basal ECM 的厚度方向划分，从既有 `Y2=(5,2,4)` 继续到 `Y3=(5,3,4)` 与 `Y4=(5,4,4)`；细胞、ECM 外形、材料、tether、远端边界、激活路径和固定拓扑约束均未改变。

## 2. 新完成状态

| 工况 | ECM 节点 | 四面体 | 峰值缩短 | 峰值曲率 | ECM 储能 | 最大 ECM 位移 | KKT | 最小 J |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Y2 | 90 | 240 | 15.62118% | -4.25351e-3 | 2.27977e-5 | 5.59801e-3 | 2.7449e-6 | 0.99286 |
| Y3 | 120 | 360 | 15.62256% | -4.23358e-3 | 2.73952e-5 | 6.46370e-3 | 3.4206e-6 | 0.99325 |
| Y4 | 150 | 480 | 15.62313% | -4.23103e-3 | 2.92491e-5 | 6.77800e-3 | 3.2674e-6 | 0.99353 |

Y3、Y4 的 `0, 0.10, 0.20` 三个激活状态全部完成，并通过原 T1 的体积、完整 KKT、非穿透、正 Jacobian、细胞面质量以及界面 pair force/moment 门。

## 3. 预注册收敛门

| 指标 | Y2→Y3 | Y3→Y4 | Y3→Y4 门槛 | 结果 |
|---|---:|---:|---:|---|
| 缩短绝对差 | 0.001374 pp | 0.000570 pp | <=0.10 pp | 通过 |
| 曲率相对差 | 0.4696% | 0.0602% | <=5% | 通过 |
| ECM 储能相对差 | 18.319% | 6.546% | <=10% | 通过 |
| 最大 ECM 位移相对差 | 14.354% | 4.747% | <=10% | 通过 |

储能与最大位移的最新一级差异均小于前一级差异，趋势门通过。T1.1R 总体 `scientific_gate=passed`。

## 4. 对 T1.1 失败的解释更新

T1.1 的单层到双层储能差 `68.95%` 继续保留为真实失败。新增结果显示：

- Y1→Y2 出现大变化，是因为增加第一个内部厚度层后开始解析非仿射场；
- Y2→Y3 储能差降至 `18.32%`；
- Y3→Y4 进一步降至 `6.55%`；
- 细胞缩短与曲率从 Y2 起已经基本稳定。

这支持“ECM 储能随厚度自由度增加正在趋于平台”的解释，而不是体积重复或本构积分错误。当前可以把 Y4 作为后续固定拓扑研究的最低推荐厚度离散，但不能把本结果称为严格渐近收敛或 GCI。

## 5. 文件与复现

- 合同：`project_control/t1_1r_ecm_thickness_convergence_contract_v01.md`；
- 运行：`scripts/run_t1_1r_ecm_thickness_convergence_v01.py`；
- 绘图：`scripts/build_t1_1r_ecm_thickness_convergence_figure_v01.py`；
- 数据：`results/hybrid/t1_1r_ecm_thickness_convergence_v01/`；
- 阶段图：`t1_1r_ecm_thickness_convergence_stage_review_v01.png/.svg`；
- 相关回归：`18 passed`；
- 源码格式检查：`git diff --check` 通过。

## 6. 证据边界与下一决策门

若人类终审接受，本轮可形成以下阶段结论：

> 在固定拓扑、准静态、未标定材料参数的三维 DCM–FEM 单细胞—ECM 模型中，细胞缩短和接触诱导曲率对测试的 ECM 厚度离散稳定；ECM 储能与最大位移在 Y3→Y4 上分别变化 6.55% 和 4.75%，达到预注册的工程网格不敏感门。

仍不得声称：严格 GCI、动态心搏耦合、黏弹 cardiac jelly、内膜层、remeshing 稳定性、实验标定或 EFE 机制已经完成。

建议人类终审通过后，将后续固定拓扑 ECM 默认更新为 `(5,4,4)`，下一科学包进入“黏弹 cardiac jelly 的单周期动态耦合”，但该新包需要单独批准，不能从本轮自动启动。
