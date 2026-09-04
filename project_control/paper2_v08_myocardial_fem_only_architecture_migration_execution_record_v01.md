---
execution_id: EXE-PAPER2-V08-MYOCARDIAL-FEM-ONLY-ARCHITECTURE-MIGRATION-V01
plan_id: PLAN-PAPER2-V08-MYOCARDIAL-FEM-ONLY-ARCHITECTURE-MIGRATION-V01
authorization: DEC-PAPER2-MYOCARDIAL-DCM-RETIRE-FEM-ONLY-ARCHITECTURE-V01
executor: Codex Executor
started_at: 2026-09-04
completed_at: 2026-09-04
status: completed_at_supervisor_gate
formal_label: FEM_ONLY_ARCHITECTURE_PASS_V08
deviation_records: []
---

# Paper 2 v08 心肌 FEM-only 架构迁移执行记录 v01

## 1. Approved plan reference

本执行依据：

- 人类架构决定：
  `project_control/paper2_myocardial_dcm_retirement_and_fem_only_architecture_decision_v01.md`；
- v08 迁移合同：
  `project_control/paper2_v08_myocardial_fem_only_architecture_migration_contract_v01.md`；
- 实际执行基线与同名远端：
  `b6f1c16a1fcc04856d4ac10cd4745160ff666644`，执行前 ahead/behind=`0/0`；
- 合同与架构决定记录的历史退役锚点：
  `34908b299475ee81d9cb2fccca0b191e22fa965a`；
- 一次性只读 FEM 参考：
  `results/paper2_m2/identity_2d_v03_t64_v01_20260903/`。

实际执行基线晚于合同 frontmatter 的历史锚点；前者用于锁定本轮代码与远端状态，后者
用于解释 v01–v07 退役证据的历史位置。没有改写合同，也没有把旧路线作为活跃比较臂。

## 2. Files changed and outputs produced

新增唯一活跃包：

- `src/paper2_hybrid/__init__.py`；
- `src/paper2_hybrid/roles.py`；
- `src/paper2_hybrid/config.py`；
- `src/paper2_hybrid/protocol.py`；
- `src/paper2_hybrid/model.py`；
- `src/paper2_hybrid/numerics.py`；
- `src/paper2_hybrid/projection.py`；
- `src/paper2_hybrid/validation.py`。

新增测试、一次性迁移 runner 与主线：

- `tests/paper2_hybrid/test_static_architecture.py`；
- `tests/paper2_hybrid/test_projection.py`；
- `tests/paper2_hybrid/test_fenicsx_runtime.py`；
- `scripts/run_paper2_v08_fem_only_parity_v01.py`；
- `project_control/prl_independent_theory_mainline_plan_v03.md`。

新增 create-only 正式结果：

- `results/paper2_v08/fem_only_architecture_parity_v01_20260904/`。

结果包包含 9 个 JSON，hash ledger 列出其余 8 个文件；没有生成新 NPZ。未修改、移动、
删除或覆盖 `src/paper2_m2/`、`tests/paper2_m2/`、既有 M2A runner 或
`results/paper2_m2/`。未执行 Git add、commit 或 push，工作树既有无关修改保持原样。

## 3. Architecture result

新生产角色固定为：

| 组织层 | 固定实现 |
|---|---|
| 心内膜 | `discrete_cell_chain` |
| 心肌 | `active_plane_strain_fem` |
| ECM | `viscoelastic_plane_strain_fem` |
| 流体 | `absent_in_v08` |

生产工况固定为 `P0/P1/A1/A2/LN/LS/C0/CQ/S1`，端点键为
`case__spatial_level__time_level__tolerance_level`，例如 `A2__S4__T64__D0`。

对 `src/paper2_hybrid/` 的逐文件 AST/import 与词法审计通过：没有旧包 import、心肌离散
网络、被动/主动缩放、心肌校准、表示选择轴或 GO/MAYBE/NO-GO 分类符号。公共构建入口
只有 `spatial_label/active_profile/config` 三个关键字参数；固定角色校验拒绝其他心肌实现。

## 4. Tests and preflight

- 宿主静态架构与纯 NumPy 投影测试：`9 passed in 0.75 s`；
- 指定 `dolfinx/dolfinx:v0.11.0` CPU 镜像，镜像 ID
  `sha256:2ae4bfbc0d9077268880faf04c72750528bee986c94ab223a2c159969bd56fa8`；
- 容器内 FEniCSx 装配、矩阵、作用反作用与端点测试：`1 passed in 4.27 s`；
- Ruff：全部新增 Python 文件通过；
- 正式运行参数为 `--network none`、`--cpus 1`、`--memory 8g`，没有挂载 Docker
  socket，没有启用 GPU。

正式运行前有三次环境入口预检未进入端点：第一次覆盖镜像原 `PYTHONPATH` 导致找不到
`dolfinx`；第二次只读根文件系统未提供 JIT cache；第三次 JIT cache 的 tmpfs 未启用
可执行映射。最终保留镜像原运行库路径，并给 `/root/.cache` 使用 `rw,exec` 临时内存盘后，
同一测试通过。上述过程没有修改模型、合同、阈值或正式结果目录。

## 5. Six-case FEM-to-FEM migration parity

对新架构与旧参考的 `S4/T64/D0` 六工况逐项比较，全部通过：

| 新工况 | 旧只读参考 | 新端点耗时（s） | 结果 |
|---|---|---:|---|
| `A2` | `ID-A2__FEM__S4__T64__D0` | `26.0474030090` | PASS |
| `LN` | `ID-LN__FEM__S4__T64__D0` | `25.9432427870` | PASS |
| `LS` | `ID-LS__FEM__S4__T64__D0` | `26.0272950160` | PASS |
| `C0` | `ID-C0__FEM__S4__T64__D0` | `25.7400706980` | PASS |
| `CQ` | `ID-CQ__FEM__S4__T64__D0` | `25.8903824560` | PASS |
| `S1` | `ID-S1__FEM__S4__T64__D0` | `25.9145147730` | PASS |

每个工况比较 38 个冻结标量、28 个完整数组、两条原生界面牵引、两条 64 段共同投影
及其空间—时间范数。六工况所有标量最大绝对误差、所有数组最大逐值误差与 normalized-L2、
共同投影误差均为 `0`。ECM 质心、峰值应变、内变量和应力的 24/24 组数组字节哈希完全
相等。

因此本次不是“阈值内近似通过”，而是在同一固定容器、求解顺序和浮点路径下逐值重现
旧 FEM 臂。旧档案只作为一次性迁移 oracle；新结果 schema 没有表示轴或 identity 指标。

## 6. Structural and power checks

- 主材料＋支撑矩阵对称性误差：`5.77902946605705e-21 < 1e-12`；
- 速率矩阵对称性误差：`1.3492047304964419e-18 < 1e-12`；
- UFL/手工装配制造解误差：`1.03217118583013e-15 < 1e-6`；
- 界面作用反作用制造检查误差：`0`；
- 固定支撑具有 513 个非零项、257 个正对角项，刚体模态处理门通过；
- 主动功共轭中心差分误差：`3.9384830658998466e-08 < 1e-7`；
- 共同投影常场与合力误差为 `0`，离散界面功误差为
  `1.3877787807814457e-17 < 1e-12`；
- 六工况求解器、周期、离散功率账本、非负耗散和有限值结构门全部通过。

## 7. Provenance, resources and hashes

旧参考的 23 项原 hash ledger 全部复算通过；包含 ledger 自身的 24 项快照前后一致。
退役源码、测试与 runner 共 50 个文件的前后哈希一致；新实现、测试与 runner 共 12 个
文件的正式运行前后哈希一致。

正式阶段资源：

- 耗时：`189.14686104100838 s < 1200 s`；
- 峰值内存：`0.7554397583007812 GiB < 8 GiB`；
- 单 CPU 进程；网络、GPU、Docker socket 均未使用。

关键结果 SHA-256：

- `architecture_manifest.json`：
  `a3f09ba772de06798434ecbddf6a29bf5662e18ccac2e3609e9a373cf986097f`；
- `parity_by_case.json`：
  `ee1d92723aaa4cf1028c8e16dddb2f6ed6ec2afb9e84a65e48747214c61ba5d5`；
- `ecm_field_summary_audit.json`：
  `d29dc2c3963e11a6c202818503eb30afca336b0b6d46ea8f954752eaca1f0b65`；
- `structural_checks.json`：
  `8154069b53f4da3a1609cd859574e25b8b05348ae0e21b61abc1b0a719cab91d`；
- `provenance.json`：
  `891460cf72ade864527d26bf05128e56909eac93fbb5df2756c52bc6d2dbeb46`；
- `pass_summary.json`：
  `558858ab56ca76ce7e9fe49952bf808c2add649c9cfea4409c5f97e19d57ac78`；
- `hash_ledger.json`：
  `047fdfea3fe806c992828317cc5d60c414aba38be49f96e5848709a1b8757643`。

## 8. Mainline and evidence boundary

`project_control/prl_independent_theory_mainline_plan_v03.md` 已把 Figure 4 改为
cell/meso-resolved active FEM 与 homogenized active FEM 的粗粒化适用域，不再设置
心肌 DCM 比较臂。Figure 5 固定为主动心肌 H-FEM＋黏弹 ECM＋离散心内膜；流体后续
另立合同。

Nature Physics 是问题设计和机制深度的战略目标，但当前迁移证据远未达到该期刊标准。
只有后续获得简洁无量纲规律、跨几何稳健性和独立留出预测，才保留该目标；否则在后续
证据门依据实际贡献降档至 PRX Life，或在形式适合时评估 Physical Review Letters。

正式标签为 `FEM_ONLY_ARCHITECTURE_PASS_V08`。它只证明新的生产实现逐值重现冻结旧 FEM
臂并完成架构隔离，不是新的力学机制、生理真实性、实验验证或论文级结论。

执行已停止在 Supervisor Gate。未运行参数扫描、三维、整心房、流体、CFD/FSI、GPU、
实验拟合或后续 Figure 2–5 计算，也未恢复任何已退役路线。
