---
contract_id: CONTRACT-PRL-ROUTE-H-STAGE2-GATE-A-CURVATURE-MEMORY-V04
status: approved
approved_by: user
approved_at: 2026-08-09
approval_basis: "用户在审阅心肌细胞体积证据与 M1 v04 建议后明确要求继续任务"
preserves:
  - FREEZE-PRL-ROUTE-H-STAGE2-GATE-A-V03-FAILURE-V01
  - CONTRACT-PRL-ROUTE-H-STAGE2-GATE-A-PHYSICAL-ACCEPTANCE-V03
  - CONSTRAINT-PRL-EXTERNAL-SCIENTIFIC-REVIEW-V01
registered_v04_response_runs_before_contract: 0
nonregistered_step86_solver_preflight_before_contract: 6
---

# Route H Stage 2 Gate A M1 v04 曲率记忆修订合同

## 1. 目标与依据

M1 v03 在 `A1_ACTIVE, dt=0.02, t=1.72` 失败。冻结诊断表明候选细胞保持正体积、无翻面、无退化，但原 L-BFGS-B 路径的最小 projected residual 为
`1.310584667e-8`，未达到冻结的 `1e-8` 门槛。

合同登记前仅在该冻结失效步进行了不落盘、非 response 的单变量求解器预检：

- 冻结配置可重复得到 returned residual `1.980868094e-8`；
- 单独把 `gtol` 从 `1e-10` 改为 `1e-12` 无改善；
- 单独把 `maxls` 从 `40` 改为 `80` 无改善；
- 单独把 `maxiter` 从 `200` 改为 `400` 无改善；
- 仅把 L-BFGS-B 曲率历史 `maxcor` 从 `20` 改为 `40`，第 88 次目标函数评估达到
  projected residual `9.455399901e-9`，并保持严格增量势下降。

因此 v04 只检验“增加曲率记忆能否在不改变物理模型和验收门槛的条件下走通固定时期单细胞心搏主线”。

## 2. 冻结项

以下项目全部保持 v03 不变：

- reference geometry、网格、global six-constraint gauge 和 binary64 null space；
- 面积、弯曲、体积、主动 preferred-length 与双面积加权阻尼的方程和参数；
- `DRAG=1`、`ACTIVE_STIFFNESS=10`、`ACTIVE_PEAK=0.1`；
- `maxiter=200`、`maxls=40`、`ftol=0`、`gtol=1e-10`；
- projected residual `<=1e-8`、gauge residual `<=1e-12`、几何门槛和 Gate A 指标；
- A0 `dt=0.01` 与 A1 `dt=0.02,0.01,0.005`，每条 `duration=5.0`；
- 每步只允许一次 optimizer 调用，不允许 retry、自适应时间步或第二求解器；
- v01、v02、v03 的源码、结果和失败冻结包只读保留。

## 3. 唯一数值修改

SciPy L-BFGS-B 的 `maxcor` 从 `20` 改为 `40`。它只增加单次 optimizer 内保存的曲率对数量，不改变目标函数、解析梯度、坐标、时间离散或候选验收语义。

## 4. TDD 与执行顺序

1. RED：通过公共入口要求 v04 的 `A1_ACTIVE, dt=0.02` 到达 `t=1.72`，并验证 step 86 的 residual、gauge、势下降和几何门槛；
2. GREEN：新增版本化 v04 入口，只修改 `maxcor=40`；
3. 回归：运行 activation、v02 observability、v03 和 v04 的 Stage 2 测试；
4. 正式套件：按 A0、A1 coarse/base/fine 顺序 fail-fast，每条只运行一次并保存逐步审计；
5. 若任一轨迹失败，冻结首个新失效状态，不继续调参，不运行后续轨迹；
6. 只有四条轨迹完整到达 `t=5.0` 后，才计算 time refinement 和 Gate A acceptance。

## 5. 产物

- `src/route_h/stage2_gate_a_v04.py`；
- `tests/stage2/test_gate_a_v04.py`；
- `scripts/run_route_h_stage2_gate_a_v04.py`；
- `results/route_h/stage2_gate_a_v04/` 下的版本化轨迹、审计、失败状态与 manifest；
- 若 Gate A 通过，再从正式结果生成细胞状态图和收敛诊断图；若失败，仅生成失败定位图；
- v04 execution log 与只读自检记录。

## 6. 验收标准

- step 86 公共行为测试通过，且该步 residual `<=1e-8`；
- 四条正式轨迹均完整到达 `t=5.0`，所有接受步通过 residual、gauge、势下降和几何门槛；
- A1 `dt=0.01` 对 `dt=0.005` 的冻结 time-refinement 指标最大相对差 `<=2%`；
- 体积误差继续按冻结门槛 `<=0.5%` 验收；
- v03 冻结失败 manifest 逐文件哈希保持一致；
- 测试、静态检查、结果完整性检查和图形数据一致性检查通过。

## 7. 证据边界与 out of scope

v04 通过只证明当前无量纲、自由边界、单细胞离散响应在冻结门槛内可计算并通过时间步自洽性检查，不证明真实力值、前负荷/后负荷、Ca²⁺—横桥机制、ECM/血流耦合或发育机制。

本合同不修改几何、主动加载分布、材料参数、体积可压缩性、激活定律、Gate 阈值或论文 claim；不执行 Gate B–E、参数标定、Git commit/push/PR 或远端发布。
