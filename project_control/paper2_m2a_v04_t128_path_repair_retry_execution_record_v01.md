---
execution_id: EXE-PAPER2-M2A-V04-T128-PATH-REPAIR-RETRY-V01
plan_id: PLAN-PAPER2-M2-ACTIVE-MYO-FEM-IDENTITY-V04
executor: Codex Executor
started_at: 2026-09-03
completed_at: 2026-09-03
status: completed_at_supervisor_gate
formal_stage_label: T128_STAGE_PASS_V04
scientific_or_scope_deviations: none
---

# Paper 2 M2A v04 T128 路径修复重试执行记录 v01

## 1. Approved plan reference

本执行依据：

- v04 合同：`project_control/paper2_m2_active_myocardial_fem_identity_conversion_contract_v04.md`；
- 修复与重试决定：
  `project_control/paper2_m2a_v04_t128_path_normalization_repair_and_retry_decision_v01.md`；
- 冻结 T64 源：`results/paper2_m2/identity_2d_v03_t64_v01_20260903/`；
- 首次失败包：`results/paper2_m2/identity_2d_v04_t128_v01_20260903/`。

修复范围仅限新增 v04.1 路径归一化入口和定向测试，再在新的 create-only v02 结果目录
完整重跑冻结的 54 个 T128/D0 端点。原 v04 runner、v04 模块、原测试、首次失败包及
v01-v03 证据均保持只读。

## 2. Minimal repair

新增 runner 在加载原 v04 runner、创建输出目录、写 manifest 或开始计算之前，将六个项目
路径参数统一解析为 `PROJECT_ROOT` 内的绝对规范路径。相对与绝对项目内输入映射到同一
目标；解析到项目外的输入立即 fail-closed。

新 runner 复用原 runner 的冻结科学实现，不改变方程、校准、端点矩阵、D0 直接求解器、
功率账本、闭合公式、空间/周期/热点阈值或生产观测量。`run_manifest.json` 同时记录了原
runner、新 runner、修复决定和 v04 合同的 SHA-256 以及路径审计。

## 3. Commands or tools used

- 宿主执行路径归一化、协议和源锁测试；
- 固定 `dolfinx/dolfinx:v0.11.0` CPU 容器执行原 v04 回归、真实 S4/T128/D0 端点测试和
  新路径测试；
- 固定容器执行完整 T128 矩阵：CPU 单进程、BLAS/OMP 单线程、16 GiB 上限、禁网、无 GPU；
- 使用严格 JSON 解析、NPZ 有限值扫描、SHA-256 和字节数逐项复算进行独立封存审计。

## 4. Files changed

新增：

- `scripts/run_paper2_m2_identity_2d_t128_v04_1.py`；
- `tests/paper2_m2/test_t128_v04_1_path_normalization.py`；
- `results/paper2_m2/identity_2d_v04_t128_v02_20260903/`；
- 本执行记录。

按决定更新 `project_control/CURRENT_STATUS.md`。未修改原 v04 runner、v04 模块、原测试、
首次失败包、v01-v03 结果或其他科学实现。未执行 Git commit/push。

## 5. Tests or checks run

- 初始 red seam：新 runner 尚不存在时，四项定向测试中旧故障复现通过，其余三项按预期
  因入口缺失而失败；
- 新入口宿主定向测试：`4 passed in 0.66 s`；
- 宿主 v04 协议与路径测试：`6 passed in 1.84 s`；
- 固定 DOLFINx CPU 环境原 v04 与路径回归：`8 passed in 43.18 s`；
- 测试覆盖旧相对路径故障、相对/绝对项目内路径等价、项目外路径拒绝以及归一化先于输出
  创建和原 runner 加载；
- Python 语法编译与 `git diff --check` 通过；
- 结果包 14 个 JSON 均可解析且数值有限；12 个 NPZ 共 360 个数组全部有限；
- hash ledger 的 25 个文件条目 SHA-256 与字节数逐项复算一致；
- manifest 中原 runner、新 runner、修复决定和 v04 合同四项哈希均与当前文件一致；
- v03/T64 关键源哈希及首次 v04 失败包 hash ledger 与执行前基线一致。

## 6. T128 result

正式阶段标签：`T128_STAGE_PASS_V04`。

- 54/54 个 T128/D0 端点完成并通过结构门；
- 74/74 个 T128 空间主量门通过；
- 54/54 个周期门通过；
- 2/2 个热点门通过；
- 74/74 个 T64→T128 配对记录完整，正式标签仅为
  `T64_T128_PAIR_AUDIT_ONLY`；方向判定保持 `PENDING_T256`；
- 最大 T64→T128 相对差为 `0.0016598581580133645`，出现在
  `ID-LS/DCM/S4/total_dissipation`；此数值没有独立时间收敛门，也不构成方向结论；
- 最大 D0 相对方程残差为 `2.9681468104030423e-08 < 1e-07`；
- 最大 normwise backward error 为 `1.2667253508759522e-15 < 1e-12`；
- 最大功率账本归一化 residual 为 `3.7028260806074476e-09 < 1e-08`；
- 最大离散闭合相对误差为 `2.315226770008592e-14 < 1e-10`；
- 最大端点相减缺口为 `7.260820343440186e-12`；
- 共同投影 sidecar 与原生生产门没有观测结论冲突；
- 运行 `548.6667 s < 5400 s`，峰值内存 `0.9385 GiB < 16 GiB`。

## 7. Outputs and hashes

create-only 成功包：
`results/paper2_m2/identity_2d_v04_t128_v02_20260903/`。

关键 SHA-256：

- `pass_summary.json`：
  `0b1ccce87abdbe65633a66fe52c1cb70c24de0c4c8a685d6e2cabf5d37e624ef`；
- `stage_T128_gate.json`：
  `e5d73917ad8f75052ab913101cd78e7d68faaad3dc4b9f7b21e61f8808b051e0`；
- `T64_T128_pair_audit.json`：
  `1158a7c7f9ba26497ee3001878277b40f215bb007b61dc14a9d596cea1493601`；
- `run_manifest.json`：
  `302931097e9117d48b8f5a49325c9286711a291562fcee9eea997034be5fd16c`；
- `hash_ledger.json`：
  `d819e9c7315b89450ea3e8b8417baf9197370de54fe52efd179dbfb2d981b67f`；
- 新 runner：
  `382b40f57eaa53b15ceeb06685974f3ccb174ba8f1ac9065254d84d4010fae60`；
- 路径测试：
  `f4dbd921491a1e797ea92820eaee0975bd29c3068713425645775b705b02262d`。

## 8. Deviations and blockers

没有科学或范围偏差。首次失败指定目录未复用或覆盖；本次使用决定中指定的新 v02 目录。
T128 阶段本身无数值阻塞，但后续 T256、三层时间方向、正式时间收敛和 identity gate 均未获
授权，仍是明确的人类/Supervisor 决策门。

## 9. Resource and cleanup record

正式计算为 CPU 单进程、BLAS/OMP 单线程、禁网、无 GPU。为遵守“删除需单独确认”，本次
产生的停止态 Docker 测试和执行容器未删除。未在项目目录外新建普通文件或文件夹。

## 10. Evidence boundary and stop state

`T128_STAGE_PASS_V04` 只证明冻结理想二维模型在 T128、既定 S2/S3/S4 空间梯度、D0 直接
求解质量、离散功率账本、周期与热点门下通过当前数值阶段。T64 与 T128 两个时间层不足以
证明时间收敛、收敛方向或 DCM-FEM identity，也不证明生理真实性、EFE 机制、三维/整心房
迁移性或流体耦合有效性。

执行已停止在 Supervisor Gate。没有运行 T256、identity gate、M2B、三维、整心房、真实
几何、CFD/FSI、GPU、新求解器或参数扫描。
