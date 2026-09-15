---
contract_id: CONTRACT-PRL-ROUTE-H-STAGE2-GATE-A-PHYSICAL-ACCEPTANCE-V03
status: approved
approved_by: user
approved_at: 2026-08-05
approval_basis: "用户明确批准 M1 v03，并要求单个心肌细胞科学主线阶段性走通后以图汇报"
preserves:
  - FREEZE-PRL-ROUTE-H-STAGE2-GATE-A-FAILURE-V01
  - CONTRACT-PRL-ROUTE-H-STAGE2-GATE-A-OBSERVABILITY-V02
  - CONSTRAINT-PRL-EXTERNAL-SCIENTIFIC-REVIEW-V01
scope: "不改力学与门槛，仅修订单细胞 Gate A 的物理平衡候选接受时机，并复跑完整时间步套件"
registered_v03_response_runs_before_contract: 0
---

# Route H Stage 2 Gate A M1 v03 物理门槛候选接受契约

## 1. 科学问题与修订依据

M1 v02 已把 Gate A v01 的第一个失败定位为优化器接受语义与物理验收语义的失配：
`A1_ACTIVE, dt=0.02` 的第 79 步存在 projected overdamped residual 小于
`1e-8` 的有限、正体积、无翻面候选，但该候选只出现在 L-BFGS-B 目标函数评估中，
没有成为 callback 所见的 accepted iterate；之后优化器在机器精度附近异常退出。

本版把离散物理平衡条件恢复为单步求解的直接停止条件。增量势仍用于产生下降路径，
但 Wolfe/line-search 的内部接受标签不再覆盖已经满足冻结物理方程容差的候选。

## 2. 冻结不变项

以下内容不得在 v03 中修改：

- reference geometry、base discretization、global six-constraint gauge 与 binary64
  null space；
- 被动能、主动 preferred-length 能、主动节点力装配、双面积加权阻尼和 backward-Euler
  增量势；
- `DRAG=1`、`ACTIVE_STIFFNESS=10`、`ACTIVE_PEAK=0.1` 及 activation protocol；
- L-BFGS-B 的 `maxiter=200`、`maxls=40`、`maxcor=20`、`ftol=0`、
  `gtol=1e-10`；
- projected residual `<=1e-8`、gauge increment residual `<=1e-12`；
- Gate A 指标、阈值、`t=3.0` plateau 定义和 time-refinement 公式；
- 正式时间步与时长：A0 `dt=0.01`，A1 `dt=0.02,0.01,0.005`，均为
  `duration=5.0`；
- 每个时间步只允许一次 optimizer 调用，不允许 retry、自适应时间步或第二优化器。

冻结的 `src/route_h/stage2_gate_a.py` 和
`results/route_h/stage2_gate_a_v01/` 不得修改；v03 只新增版本化入口、测试与结果。

## 3. 预注册接受算法

对于当前已接受状态 `x_n` 和给定 `alpha(t_{n+1})`：

1. 在冻结 null space 中令优化坐标 `q=0`，计算初始增量势 `J_0=J(0)` 和初始
   physical projected residual。若初始状态已满足 residual gate，则原样接受；
2. 否则只调用一次冻结配置的 L-BFGS-B；
3. 在每一次目标函数/解析梯度评估后，按确定性评估顺序检查候选，而不只在 callback
   accepted iterate 检查；
4. 第一个同时满足以下条件的候选立即结束该次 optimizer，并作为该步结果：
   - 坐标、目标函数、梯度和 residual 全部有限；
   - physical projected residual `<=1e-8`；
   - 增量势严格下降 `J_trial < J_0`，不引入额外松弛量；
   - gauge increment residual `<=1e-12`；
   - signed volume `>0`、翻面数 `=0`、退化面数 `=0`，全部几何诊断有限；
5. 对被接受坐标从力块重新计算 residual、gauge 和几何；任何复算失败都判为
   `invalid_numerics`，不得沿用目标函数评估时的缓存数值；
6. 若没有目标评估候选触发上述条件，则检查 optimizer 最终返回点，使用完全相同的
   residual、势下降、gauge 和几何门槛；仍不满足时 fail-fast；
7. 每步保存接受来源、评估次数、callback 次数、初始/接受势、residual、gauge 和
   几何诊断。自定义物理门槛停止不得伪记为“optimizer reported success”。

该规则接受的是满足离散力平衡容差且沿冻结增量势下降的状态，不是放宽 residual，
也不是把任意 line-search trial 当作有效响应。

## 4. 实施产物

- `src/route_h/stage2_gate_a_v03.py`：版本化单步、轨迹和完整套件入口；
- `tests/stage2/test_gate_a_v03.py`：先复现 v01/v02 失效节点的 RED 测试，再验证
  v03 物理门槛接受与全套 Gate A 行为；
- `scripts/run_route_h_stage2_gate_a_v03.py`：正式套件和可复算数据包入口；
- `results/route_h/stage2_gate_a_v03/`：四条轨迹、逐步审计、acceptance、环境与
  SHA-256 manifest；
- `results/route_h/stage2_gate_a_v03/Figures/`：仅从上述保留输出生成的科研审阅图，
  至少包括单细胞状态序列和 residual/time-refinement 诊断；
- v03 执行记录与交付前只读自检。

## 5. 测试顺序

1. **RED**：针对真实 `A1_ACTIVE, dt=0.02, t=1.58` 路径先写公共行为测试，证明
   v03 入口尚不存在或尚不能接受该节点；
2. **GREEN**：最小实现本契约第 3 节算法，要求轨迹到达 `t=1.58`，该步复算
   residual/gauge/geometry 全部过门；
3. **局部回归**：原 activation、Gate A v01 制造解与 v02 observability 测试不回归；
4. **正式套件**：只在实现冻结后运行 A0 一档和 A1 三档完整 5 s 轨迹；
5. **完整性**：Gate A v01 failure manifest 必须逐文件哈希一致；所有新 JSON
   禁止 NaN/Infinity；轨迹数组维度、时间节点和审计行必须一一对应；
6. **图形验收**：Notebook 可重执行，PNG/SVG 同源，状态图不得把优化器候选与
   已接受细胞状态混淆，并完成程序校验和单独目视检查。

## 6. 验收判据

M1 v03 只有在以下条件全部成立时才可报告 Gate A 通过：

- 四条正式轨迹均完整到达 `t=5.0`，无 retry、无阈值修改、无非有限值；
- `evaluate_gate_a_acceptance` 的冻结全部 checks 为真；
- 每个非初始节点均有明确接受来源，所有复算 residual/gauge/geometry 过门；
- A1 `dt=0.01` 与 `dt=0.005` 的冻结 time-refinement 指标最大相对差 `<=2%`；
- 原 Gate A v01 失败包及其 29 个文件哈希不变；
- 测试、静态检查、结果 manifest、Figure 自动检查和目视检查均通过。

若任一条件失败，必须保留首个失败状态和部分轨迹，结论仍为 M1 v03 未通过；不得在
看到正式响应后调阈值或更换方法。

## 7. 风险与声明边界

- 物理 residual 达标只证明当前离散方程在给定容差内平衡，不证明生理真实性；
- 当前仍是无量纲、自由边界、单个心肌细胞，没有真实前负荷/后负荷、Ca²⁺—横桥、
  ECM、接触或组织约束；
- 完整 Gate A 若通过，只支持“该单细胞离散响应在冻结数值门槛内可计算并通过时间步
  自洽性检查”，不支持真实力值、EFE 机制或器官尺度预测；
- v03 若改变 v01 的轨迹末位数值，必须通过 residual、势下降和 time refinement
  解释，不得以与 v01 逐点相同作为必要条件。

## 8. Out of scope

- 修改力学加载、材料参数、激活定律、几何、网格或 Gate 阈值；
- Gate B–E、ECM/血流/多细胞耦合、重网格、参数标定；
- 生理量纲映射、实验拟合、机制因果或论文结论；
- Git commit、push、PR 或远端发布。
