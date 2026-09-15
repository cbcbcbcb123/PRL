---
plan_id: PLAN-PAPER2-V08-MYOCARDIAL-FEM-ONLY-ARCHITECTURE-MIGRATION-V01
status: approved_by_human
approved_at: 2026-09-04
authorization: project_control/paper2_myocardial_dcm_retirement_and_fem_only_architecture_decision_v01.md
baseline_git_head: 34908b299475ee81d9cb2fccca0b191e22fa965a
legacy_fem_reference: results/paper2_m2/identity_2d_v03_t64_v01_20260903/
result_path: results/paper2_v08/fem_only_architecture_parity_v01_20260904/
executor_thread_id: 019fc73d-393d-71a3-98cb-d3c0cd0c8eda
execution_authorized: fem_only_active_namespace_migration_and_t64_parity_only
---

# Paper 2 v08 心肌 FEM-only 活跃架构迁移合同 v01

## 1. Goal

建立不含心肌 DCM 的新活跃生产架构：心内膜为离散细胞链，心肌为主动 FEM，ECM 为
黏弹 FEM。新实现必须独立于旧 `paper2_m2` 双表示运行时，并以旧 FEM 臂作为一次性、
只读迁移 oracle 证明行为没有因代码提取而漂移。

本阶段是架构迁移与数值等价门，不提出新生物学结论，不运行新参数扫描。

## 2. Inputs

- 人类架构决定：
  `project_control/paper2_myocardial_dcm_retirement_and_fem_only_architecture_decision_v01.md`；
- 旧 FEM 臂只读参考：
  `results/paper2_m2/identity_2d_v03_t64_v01_20260903/`；
- 已验证 CPU 环境：本地镜像 `dolfinx/dolfinx:v0.11.0`，镜像 ID
  `sha256:2ae4bfbc0d9077268880faf04c72750528bee986c94ab223a2c159969bd56fa8`；
- 旧双表示实现只用于人工提取 FEM 公式与读取历史输出；不得在新生产运行时导入。

## 3. Outputs

优先新增：

- `src/paper2_hybrid/`：唯一活跃模型包；
- `tests/paper2_hybrid/`：角色锁、API 锁、迁移等价与结构测试；
- `scripts/run_paper2_v08_fem_only_parity_v01.py`：一次性 create-only parity runner；
- `project_control/prl_independent_theory_mainline_plan_v03.md`：无心肌 DCM 的新论文主线；
- `project_control/paper2_v08_myocardial_fem_only_architecture_migration_execution_record_v01.md`；
- create-only 结果：
  `results/paper2_v08/fem_only_architecture_parity_v01_20260904/`。

不得修改、移动或删除 `src/paper2_m2/`、`tests/paper2_m2/`、既有 M2A runner 或
`results/paper2_m2/`；这些路径是历史退役证据。

## 4. Active model contract

新包固定以下角色，不提供运行时开关：

```text
endocardium = discrete_cell_chain
myocardium   = active_plane_strain_FEM
ECM          = viscoelastic_plane_strain_FEM
fluid        = absent_in_v08
```

新生产 API：

- 不得定义或接收 `Representation` / `representation`；
- 不得包含 `_dcm_network_full`、`passive_dcm_scale`、`active_dcm_scale` 或心肌 DCM
  calibration；
- `ModelSystem` 必须显式记录三个固定组织角色，但不能用字符串选择心肌实现；
- 工况名从 identity 语义中解耦，生产工况为
  `P0, P1, A1, A2, LN, LS, C0, CQ, S1`；
- 端点键只含 `case, spatial_level, time_level, tolerance`，不得包含心肌表示轴；
- 输出不得计算 `GO-ID/MAYBE-ID/NO-GO-ID` 或 DCM–FEM identity 指标。

新生产包不得在 import graph 中依赖 `paper2_m2`。一次性 parity runner 可以读取旧 JSON/
NPZ，但不得 import 或调用旧双表示 Python 模块。

## 5. Implementation steps

### Phase A — 公式提取与命名空间隔离

1. 从已冻结 FEM 分支提取主动心肌 FEM、黏弹 ECM、离散心内膜、界面 penalty、周期边界、
   载荷和离散功率账本公式；
2. 在 `src/paper2_hybrid/` 建立干净实现，移除全部心肌 DCM 分支、参数和校准；
3. 建立固定角色 manifest 与不含 representation 的公共 API；
4. 以静态测试证明新包没有导入 `paper2_m2`，也不存在被隐藏的心肌 DCM 选择路径。

### Phase B — FEM→FEM 迁移等价门

只对旧参考包中六个冻结动态留出工况执行新架构 `S4/T64/D0`：

`A2, LN, LS, C0, CQ, S1`。

旧参考只读取相应 `ID-*__FEM__S4__T64__D0` 档案；新输出在内存中比较后只写 JSON
摘要，不生成新 NPZ。至少比较：

- 首周期受限缩短与自由缩短；
- 心内膜切向/法向平均位移；
- 两条界面原生牵引与 64 段共同投影；
- 周期能量、主动功、腔面功、阻尼/SLS 耗散和离散闭合；
- ECM 峰值应变、内变量和应力场的摘要哈希/范数；
- 结构门、有限值和周期窗口。

所有数组和标量使用冻结算子：绝对误差 `<=1e-12` 或 normalized-L2
`<=1e-10`。该门只检验新 FEM-only 代码是否重现旧 FEM 臂，不是模型 identity 门；
不得因失败放宽阈值。

### Phase C — 主线 v03

新主线必须明确：

1. Figure 1：主动心肌 FEM—黏弹 ECM—离散心内膜的三层理论；
2. Figure 2：FEM-only 数值可信度、空间/时间/容差与功率闭合；
3. Figure 3：`De × H` 机械传递状态图；
4. Figure 4：cell/meso-resolved active FEM 与 homogenized active FEM 的粗粒化适用域，
   不允许心肌 DCM 比较臂；
5. Figure 5：主动心肌 H-FEM＋心内膜 DCM＋ECM 的整心房预测；流体后续分层加入。

v03 必须将 v01–v07 M2A 标为退役历史路线，不把其 NO-GO 或差异诊断作为新模型验证。

## 6. Tests and checks

至少覆盖：

- 固定模型角色和公共 API 签名；
- 拒绝任何 `myocardium=DCM`、`representation=DCM` 或同义输入；
- 新包 AST/import graph 不依赖 `paper2_m2`；
- 新包不存在心肌 DCM 网络、缩放、校准和 identity 分类符号；
- 矩阵对称性、刚体模态处理、界面作用反作用、制造解与单位/符号约定；
- 六个 T64 FEM→FEM parity 工况的全部冻结观测量；
- create-only、严格有限 JSON、完整 hash ledger、路径和资源 fail-closed；
- 主线 v03 不含活跃心肌 DCM/comparator/identity 路线。

宿主只运行不需要 FEniCSx 的静态/纯 NumPy 测试；需要装配和端点的测试在指定 CPU
容器中运行。容器必须 `--network none`、单进程，不挂载 Docker socket，不启动 GPU。

## 7. Acceptance criteria

正式标签：

- `FEM_ONLY_ARCHITECTURE_PASS_V08`：角色/API/import/静态门全部通过，六个 parity 工况
  全部满足误差门，结构与功率门通过，旧证据未改变；
- `BLOCKED`：路径、依赖、源锁、容器、资源或完整输出前置条件失败；
- `FEM_ONLY_PARITY_FAIL_V08`：新实现能完整运行，但任一冻结 parity 指标越界。

只允许以上三个标签。parity 失败不得恢复心肌 DCM，也不得改用 identity 阈值解释。

## 8. Resource and provenance limits

- CPU-only，单进程；正式总时间 `<=1200 s`，峰值内存 `<=8 GiB`；
- 允许使用本地已存在的固定镜像；不得联网拉取或更新镜像；
- 不使用 GPU，不运行三维、整心房、流体或新参数扫描；
- 正式结果目录已存在则 fail-closed；
- 运行前后记录新实现、合同、旧参考 ledger 与动态档案哈希；
- 输出仅 JSON 和必要小型文本日志，不生成新 NPZ。

## 9. Risks

- 机械复制 FEM 分支可能遗漏共享符号、界面权重或功率账本项；以六工况全观测 parity
  和结构门防护；
- 为追求代码干净而改变求解顺序可能引入浮点漂移；超过冻结门即失败，不事后放宽；
- 历史路径仍含字符串 `DCM`，静态退役门必须区分“历史证据”与“活跃生产源码”；
- 当前阶段只证明实现迁移等价，不证明生理真实性或 Nature Physics 级规律。

## 10. Out of scope and stop condition

不授权：删除历史文件、修改旧 v01–v07、重新校准、参数扫描、M2B、三维、整心房、
流体/CFD/FSI、实验拟合、GPU worker或论文成稿。

执行完成后写执行记录、更新 CURRENT_STATUS，并停止在 Supervisor Gate。不得从 v08
自动进入 Figure 3/4 扫描或器官级模型。
