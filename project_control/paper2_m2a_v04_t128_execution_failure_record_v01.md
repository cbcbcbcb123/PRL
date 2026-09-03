---
execution_id: EXE-PAPER2-M2A-V04-T128-V01
plan_id: PLAN-PAPER2-M2-ACTIVE-MYO-FEM-IDENTITY-V04
executor: Codex Executor
started_at: 2026-09-03
completed_at: 2026-09-03
status: blocked
deviation_records:
  - runner_path_normalization_error_before_first_endpoint
---

# Paper 2 M2A v04 T128 执行失败记录 v01

## Approved plan reference

- 合同：`project_control/paper2_m2_active_myocardial_fem_identity_conversion_contract_v04.md`；
- 授权：`project_control/paper2_m2a_v03_t64_supervisor_acceptance_and_t128_decision_v01.md`；
- 冻结源：`results/paper2_m2/identity_2d_v03_t64_v01_20260903/`。

本执行只获准新增 v04 模块、runner、测试、指定 create-only 结果包、执行记录并更新
`CURRENT_STATUS.md`。v01–v03 文件与结果保持只读。

## Commands or tools used

- 宿主执行协议与源锁测试；
- 固定 `dolfinx/dolfinx:v0.11.0` CPU 容器执行真实 S4/T128 定向测试；
- 固定容器、CPU 单进程、BLAS/OMP 单线程、禁网、无 GPU 启动正式 T128 runner；
- 使用 SHA-256、严格 JSON 解析和 create-only 文件写入封存失败包。

## Files changed

新增：

- `src/paper2_m2/protocol_v04.py`；
- `src/paper2_m2/identity_2d_v04.py`；
- `scripts/run_paper2_m2_identity_2d_t128_v04.py`；
- `tests/paper2_m2/test_protocol_v04.py`；
- `tests/paper2_m2/test_identity_2d_v04.py`；
- `results/paper2_m2/identity_2d_v04_t128_v01_20260903/`；
- 本执行记录。

允许范围内更新 `project_control/CURRENT_STATUS.md`。未修改 v01–v03 源码、runner、测试、
合同或结果。

## Tests or checks run

- 初始 red seam：v04 模块尚不存在时，协议测试按预期 collection fail；
- 宿主 v04 协议/源锁测试：`2 passed in 1.70 s`；
- 固定 DOLFINx CPU 环境 v04 定向测试：`4 passed in 42.33 s`；
- 真实 `ID-LN/DCM/S4/T128/D0` 测试通过功率账本、离散闭合、相对残差、后向误差和有限值门；
- Python 语法编译与 `git diff --check` 通过；
- 失败包 5 个 JSON 均可解析，4/4 hash-ledger 条目逐项复算一致。

测试期间曾发现合法工况名 `ID-C0` 会使全局字符串搜索产生假阳性；测试已在正式运行前
改为检查协议字段中不存在 `tolerance_labels` 且唯一 `solver_levels=[D0]`。这不改变模型或
执行合同。

## Deviations

正式 runner 在创建结果目录、写入源 T64 锁、校准锁和测试记录后，于任何 T128 端点开始
之前失败。失败发生在只读 provenance manifest 的路径规范化：命令行传入的
`source_t64_dir` 与 `source_calibration` 为相对路径，而 `_project_path()` 对它们直接调用
`path.relative_to(PROJECT_ROOT)`；前者未先解析为绝对项目路径，因此抛出 `ValueError`。

正式失败分类：`RUNNER_PATH_NORMALIZATION_ERROR`。

这是工程实现偏差，不是源数据、求解器或科学门失败。没有自行修复、换目录或重跑；指定
create-only 结果路径已由失败包占用，必须由 Supervisor 决定修复合同和新结果路径。

## Blockers

- T128 完成端点：`0/54`；
- 无 T128 endpoint summary、动态 NPZ、空间门或 T64→T128 配对结果；
- runner 需在新授权下把 provenance 路径统一解析到项目绝对路径，或让路径记录器同时接受
  项目相对路径；
- create-only 语义禁止覆盖现有失败包，因此重试需要新的结果包版本/路径。

## Outputs produced

create-only 失败包：
`results/paper2_m2/identity_2d_v04_t128_v01_20260903/`，包含：

- `source_T64_lock.json`：通过，54 个 `T64/D0` 键与三个冻结哈希一致；
- `source_calibration_lock.json`：通过；
- `preflight_tests.json`：通过；
- `failure.json`：`FAIL_CLOSED_AT_SUPERVISOR_GATE`；
- `hash_ledger.json`：4/4 条目复算一致。

关键 SHA-256：

- `failure.json`：
  `373b2c6be19e7d9fc957fab23e8790b16989d78862d10905c0c166814407c138`；
- `hash_ledger.json`：
  `a6c8bba5da6d68422c5c2b502cc3bb56c83d6aadd3e16300bf8b56be48dc9c1d`；
- `protocol_v04.py`：
  `9e23b50c0fb54f60a6247b09f8b5b4d46abc8507976ff2a4e5f738252cd0bbdc`；
- `identity_2d_v04.py`：
  `f314634fab7060cf436d9fb57b3f65b31365c1c7d439bce865ab12ef9414fc4d`；
- T128 runner：
  `28886614b611c884ea7175b6ce496c29518dd878aff65063878e91167e0a97ba`；
- `test_protocol_v04.py`：
  `08290aafceae0fdb7f08172f798717fc29bbf84fc117689f4e574d3599dc8677`；
- `test_identity_2d_v04.py`：
  `7162b6723992d4c03e1c331b55da51759026ef6ac064877ed119ec6e1e9e37ff`。

## Evidence boundary and stop state

本包只证明 T64 源锁、校准锁和 v04 定向实现测试通过，并记录一次端点前工程失败。它不含
任何 T128 科学结果，不能输出 `T128_STAGE_PASS_V04`、时间配对结论、时间收敛或
DCM–FEM identity 结论。

执行已 fail-closed 停在 Supervisor Gate。没有运行 T256、identity gate、M2B、三维、
整心房、真实几何、流体、CFD/FSI、GPU、新求解器或参数扫描；没有 Git commit/push。
