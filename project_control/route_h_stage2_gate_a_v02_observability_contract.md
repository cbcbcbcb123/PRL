---
contract_id: CONTRACT-PRL-ROUTE-H-STAGE2-GATE-A-OBSERVABILITY-V02
status: approved
approved_by: user
approved_at: 2026-08-04
approval_basis: "用户明确批准执行 M1 v02 可观测性诊断，并要求以科研审阅图阶段汇报"
preserves:
  - FREEZE-PRL-ROUTE-H-STAGE2-GATE-A-FAILURE-V01
  - DEC-PRL-ROUTE-H-STAGE2-NUMERICAL-METHOD-V02
scope: "单个心肌细胞 A1_ACTIVE 自由收缩失败路径的只增量可观测诊断"
---

# Route H Stage 2 Gate A M1 v02 可观测性诊断合同

## Goal

在不改变 Gate A v01 方程、离散、参数、时间步、优化器选项和验收阈值的前提下，复现并定位
`A1_ACTIVE, dt=0.02` 的首个无效时间步。将最后一个已接受状态、失败候选、优化过程和几何有效性
分别持久化，以支持下一版数值方法修订和面向人工终审的状态图。

## Inputs

- 冻结失败包：`results/route_h/stage2_gate_a_v01/`；
- 冻结求解实现：`src/route_h/stage2_gate_a.py`；
- 冻结主动与被动力学：`src/route_h/activation.py`、`src/route_h/dcm_cell.py`；
- 冻结参考离散：`data/route_h/stage0_v06_discretization_family/base/`；
- 外部科学评审约束：`project_control/external_scientific_review_constraints_v01.md`。

## Outputs

新增而不覆盖 v01：

- `src/route_h/stage2_gate_a_v02_observability.py`：结构化诊断入口；
- `tests/stage2/test_gate_a_v02_observability.py`：真实失败路径回归；
- `scripts/run_route_h_stage2_gate_a_v02_observability.py`：可复算结果入口；
- `results/route_h/stage2_gate_a_v02_observability/`：部分轨迹、顶点、失败快照、优化轨迹和哈希清单；
- 同一结果目录中的 `Figures/`：由保留模型输出生成的 Notebook、PNG、SVG 和 methods 版本包；
- 对应执行记录和只读检查记录。

## Implementation Steps

1. 用当前公共力学入口重现首个失败，不写入 v01；
2. 先新增行为测试，要求失败返回结构化结果而不是丢失部分轨迹；
3. 在新 v02 模块中复用冻结力学计算，记录每个已接受节点；
4. 在失败步记录全部目标函数评估与回调节点，并明确区分 accepted 与 rejected；
5. 记录纤维长度、轴向缩短、横向尺度、体积、质心、力平衡、残差和网格有效性；
6. 通过独立脚本写入新结果目录并生成 SHA-256 manifest；
7. 仅从该持久化结果生成科研审阅图，并完成程序校验与目视检查。

## Impacted Files Or Modules

允许新增上述 v02 文件和结果。禁止修改下列冻结内容：

- `src/route_h/stage2_gate_a.py`；
- `results/route_h/stage2_gate_a_v01/`；
- v01 failure manifest、freeze record 和既有阈值；
- 主动 preferred-length 定律、被动能量和参考几何。

## Test Plan

- RED：真实运行到首个失败，要求结构化返回 `failed_invalid_numerics`、失败节点和部分轨迹；
- GREEN：确认已接受节点与失败候选分离，所有保存数组有限且维度一致；
- 回归：`tests/stage2/test_gate_a_activation.py` 保持通过；
- 完整性：复算 v01 manifest 中全部文件哈希，必须与冻结记录一致；
- 几何：报告失败前最后状态及失败候选的有向体积、退化面、翻转面和最小面积比；
- 图形：Notebook 可重新执行，PNG/SVG 同源，状态图不把 rejected candidate 表述为有效响应。

## Risks

- 诊断代码若复制求解逻辑可能与冻结实现漂移；处置：关键量逐步与原入口比对；
- 失败候选可能来自优化器的最后返回点而非 accepted iterate；处置：在字段名和图注中明确标记；
- 部分轨迹可能看似生理合理；处置：只称“失败前数值诊断轨迹”，不做生理或 Gate A 通过结论；
- 绘图可能掩盖门槛越界；处置：残差阈值和失败节点必须显式显示。

## Acceptance Criteria

1. 原冻结入口仍稳定复现 `A1_ACTIVE, dt=0.02` 首个失败；
2. v02 返回并保存从初始节点到最后一个 accepted node 的完整有限状态；
3. failure record 至少包含 step、time、alpha、residual、gauge residual、optimizer status/message；
4. rejected candidate 与 accepted trajectory 不混写；
5. 不改变 `1e-8` projected residual 和 `1e-12` gauge residual 门槛；
6. v01 冻结文件哈希不变；
7. 阶段图由保存数据与 Notebook 生成，并通过 PNG/SVG、方法说明和目视检查；
8. 结论只定位数值失效及下一步可证伪修法，不重新判定 Gate A。

## Out Of Scope

- 修改或放宽求解器、阈值、时间步、材料参数或激活定律；
- 将失败候选接纳为有效状态；
- Gate A time refinement、Gate B–E、ECM/血流耦合；
- Ca²⁺、横桥、真实前负荷/后负荷和生理参数标定；
- 论文机制结论、正式投稿图、Git 提交或远端发布。

## Required Memory Updates

本阶段不更新 stable memory。只有 v02 结果经人工终审接受后，才可另行登记诊断结论。
