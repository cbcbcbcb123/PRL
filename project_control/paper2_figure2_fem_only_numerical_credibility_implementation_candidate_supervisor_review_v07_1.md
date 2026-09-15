# Paper 2 Figure 2 FEM-only 数值可信度实现候选：Supervisor 第七轮静态复核 v07.1

- review_date: 2026-09-04
- reviewer_role: Supervisor
- review_mode: independent_read_only_static_review
- reviewed_surface: v07.1 冻结的 15 个实现候选文件
- execution_contract_v03_sha256: `484090034d049d5c48ad6e92ea809fc569ae01cdce26c9c693baebb6143ad38a`
- execution_contract_v03_supervisor_review_v02_sha256: `36949b75b4d3fb93c05219bc0ada3e7e58c31a04f8bc2691f032ae88c26af57e`
- source_review_v05_actual_sha256: `cc8fe76af3b38860ed91de67f38c392771c91951d2a1f1abcd5f91cb96e4bd05`
- source_review_v06_actual_sha256: `d3c7b18efa0c7604083ff0d0926d3bdea93deffa8bd861d6da256d9a5252bac8`
- source_review_v06_declared_v05_sha256: `86116f593b6d649121ce1281f337c17f20f3e2395b8e375c7265daf30384757d`
- provenance_correction: `v06_declared_v05_sha256_is_incorrect__v07_1_binds_actual_v05_and_v06_bytes_without_modifying_history`
- execution_performed: false
- python_or_pytest_performed: false
- solver_or_docker_performed: false
- result_directory_created: false
- implementation_lock_created: false
- git_write_performed: false
- disposition: `ACCEPT_IMPLEMENTATION_CANDIDATE_FOR_PRECHECK_DECISION`
- execution_authorized: false
- precheck_authorized: false
- scientific_claim_authorized: false
- next_gate: `human_decision_on_implementation_lock_and_narrow_precheck_authorization`

## 1. 二元结论

`ACCEPT_IMPLEMENTATION_CANDIDATE_FOR_PRECHECK_DECISION`

v07.1 的 15 文件原始字节身份与本轮给定冻结完全一致。v06 的 B1--B5 均已静态关闭；新发现的
readback 子进程独立导入阻断也已关闭。没有观察到新的、足以阻断候选进入下一人类授权门的
实现问题。

本结论只表示当前候选可以提交给人类决定是否创建实现锁并运行窄范围 PRECHECK。它不等于
PRECHECK 已通过，不授权 Python、pytest、FEniCSx、solver、Docker、GPU 或任何数值运行，
不创建结果目录、实现锁或数值证据，也不构成 Figure 2 科学 PASS。

## 2. 权威链核验与 v06 元数据纠正

本轮直接按原始字节重新计算并确认：execution contract v03、其 Supervisor review v02、
implementation review v05 和 v06 的实际 SHA 分别为：

1. `484090034d049d5c48ad6e92ea809fc569ae01cdce26c9c693baebb6143ad38a`；
2. `36949b75b4d3fb93c05219bc0ada3e7e58c31a04f8bc2691f032ae88c26af57e`；
3. `cc8fe76af3b38860ed91de67f38c392771c91951d2a1f1abcd5f91cb96e4bd05`；
4. `d3c7b18efa0c7604083ff0d0926d3bdea93deffa8bd861d6da256d9a5252bac8`。

v06 元数据把 v05 写成
`86116f593b6d649121ce1281f337c17f20f3e2395b8e375c7265daf30384757d`，与 v05 当前实际原始字节
SHA 不一致。本记录以前瞻方式明确纠正该引用：本轮判断绑定上列 v05 与 v06 的实际 SHA；不改写
v05、v06 或其他历史文件。由于本轮给定了实际权威链、四个文件均已重新核验，且 v06 的 B1--B5
正文可由其实际字节直接读取，此元数据错误作为已披露的治理瑕疵保留，不构成本版实现候选的
接受阻断。

## 3. v07.1 冻结输入

| # | 文件 | bytes | lines | SHA-256 |
|---:|---|---:|---:|---|
| 1 | `src/paper2_figure2/__init__.py` | 521 | 28 | `b960435535758a5b602d80cf5ea125f4d22f367dfd61cdc3897ec5354b760412` |
| 2 | `src/paper2_figure2/spec.py` | 21448 | 595 | `471ef6561beedf8d70dc3d6aafa8068494091c36c2dd1473fd43bc55a02f8d93` |
| 3 | `src/paper2_figure2/manufactured.py` | 37440 | 939 | `dd8dd6cb408c6fe97f9b4c93bb25b0b0092f76b0eea2ac3f9879e7f7c6fb6a01` |
| 4 | `src/paper2_figure2/projection.py` | 12699 | 306 | `e9f4f46cbb86d864f4a04db12e585507b142a2768f95318fc1ab183de765e2ef` |
| 5 | `src/paper2_figure2/observables.py` | 34408 | 871 | `29216f930b3be9cd5af65e912e9a637e2042960ab83fcc5d6f2115f395a5ea85` |
| 6 | `src/paper2_figure2/evidence.py` | 21266 | 555 | `df4c5a68394e7edba21789772d5560319ec324a0e877bf4da675ad76785cbf56` |
| 7 | `src/paper2_figure2/adjudication.py` | 29425 | 854 | `9de9a95fa3babb8731d375b95718b0d7ca0a85b94c950da6d251d6bf9ae14cb7` |
| 8 | `scripts/run_paper2_figure2_fem_only_numerical_credibility_v01.py` | 217615 | 5144 | `93f1f9694e785288172e66ba59df7fbc8cdffa27575a237fc8999a0d04851d31` |
| 9 | `tests/paper2_figure2/test_spec_v01.py` | 3779 | 102 | `37d2e25870f6cf9db9f901e355f90fbe053d6965809fa772d972a9a8c0ea9fd1` |
| 10 | `tests/paper2_figure2/test_source_lock_v01.py` | 3038 | 91 | `4ff9e17b6f2348410f59ed68a3922140c00c319ec14e53f412fa0a6f95353511` |
| 11 | `tests/paper2_figure2/test_projection_v01.py` | 3780 | 101 | `7fe50027b8b1574ff69572de3856511ad7c37afd68a6cd27ad61c160e9cd375d` |
| 12 | `tests/paper2_figure2/test_adjudication_v01.py` | 6257 | 171 | `9a9badd4b5fbc97d51a01f25a09dd37ceffbfc182426bfeb4c246e8742d77cb6` |
| 13 | `tests/paper2_figure2/test_evidence_v01.py` | 9644 | 233 | `5c1760db59cb1cac527b264f5ab09a32227e1fa069f71d4e46f289c2fc8657d5` |
| 14 | `tests/paper2_figure2/test_manufactured_v01.py` | 6625 | 164 | `5945cbf3b9a2686d298115e5a24602c50a4f0e6a09f6f0e751e4a087ad985311` |
| 15 | `tests/paper2_figure2/test_runtime_smoke_v01.py` | 91128 | 2518 | `b693e419ff93624b7f1014b6e15cb17aead303db0b6ef922cd11ad5162707311` |

## 4. v06 B1--B5 逐项裁决

| 项 | v07.1 静态证据 | 裁决 |
|---|---|---|
| B1：5.0 s 包外 readback hard cap | readback 已移入同一 runner 的 `--host-readback-worker`；以 `-B` 启动、受 Job Object 与所有权门约束；绝对截止取 `min(shared_deadline, readback_start + 5.0 s)`，正常等待预留 1.0 s 同步回收，超时后撤销整个 Job 的访问并同步 wait。父进程成功与 timeout-recovery 两条路径均调用该受限边界。fake timeout 测试与 Windows 真实慢进程测试分别覆盖预算、回收和包字节不变。 | **CLOSED_STATICALLY** |
| B2：Docker 调用未贯穿同一 deadline | `_docker_evidence()` 把同一 `MonotonicDeadline` 传入真实命令层，并在 JSON parse/record 构造后复核；`_stop_wait_inspect()` 对 pre-inspect、identity、stop、wait、exit-code parse、post-inspect 与 resource validation 均使用或复核同一 deadline；正常退出与异常清理的生产调用点都传入较早的 active deadline。fake clock 覆盖命令虽返回但解析/验证越界时仍为 `RESOURCE_LIMIT_FAIL/73`。 | **CLOSED_STATICALLY** |
| B3：先启动后纳管窗口 | 子进程 stdin 所有权门在入口阻塞；父进程创建后先完成 Job assignment 与 deadline 复核，再写入唯一 release token。assignment/launch 失败时关闭 gate、同步等待，必要时按精确 PID 终止并复核已退出，最后关闭 Job。两个 worker 模式都在解析后、访问项目/结果路径前等待 release；故障注入覆盖 assignment failure、marker 不产生、进程退出和 ownership 关闭。 | **CLOSED_STATICALLY** |
| B4：plan monotonic 采样过早 | 唯一 `plan_observed_monotonic` 样本已位于 host ledger preflight 与 gate-summary 恢复之后，并同时驱动 elapsed、ready-to-plan 和双 deadline audit。测试用 fake clock 在 ledger preflight 推进 7.0 s，并对两个 observed 字段及 audit sample 做一致断言。 | **CLOSED_STATICALLY** |
| B5：runtime test 的确定性错误与禁止动作 | 错置断言已从 deadline 测试移除；handoff fixture 通过 `include_ready=False` 从源头不创建 ready。对纳入 PRECHECK 的七个候选测试文件按用户列举的删除调用模式逐文件扫描，均为 0 命中。 | **CLOSED_STATICALLY** |

以上裁决均是源码与测试文本的静态判断；测试尚未运行，不能把 `CLOSED_STATICALLY` 解释为
PRECHECK 通过或运行时 hard cap 已实证。

## 5. readback 独立导入阻断复核

新增问题已静态关闭：

1. runner 模块顶层只导入标准库；`paper2_figure2` 的 readback 依赖在
   `_readback_committed_package()` 函数体内延迟导入；
2. `_host_readback_worker()` 先解析并核对路径/deadline，随后调用
   `_add_source_path(project_root)`，下一行才进入 `_readback_committed_package()`，因此本地包导入
   发生在 `src` 路径加入之后；
3. `main()` 在进入 readback worker 前仍先等待父进程 ownership release，不因本次修复重开 B3；
4. 新测试同时检查 worker 源码中的调用顺序，并用 `python -I -B -c` 的隔离子进程显式加载
   runner、加入冻结 `src`、导入 `paper2_figure2.evidence`，再核对模块实际来自冻结项目路径；
5. runner 中 `_readback_committed_package()` 仅出现一次定义和一次生产调用，唯一调用者是
   `_host_readback_worker()`；测试文件中的直接调用仅用于 fixture/readback 负例，不形成生产路径。

裁决：**CLOSED_STATICALLY**。隔离加载测试仍须等待下一人类门授权后实际运行。

## 6. 静态卫生与不存在性核验

- 纳入 PRECHECK 的七个测试文件：用户列举的删除调用模式总命中数为 0；
- runner 与 runtime smoke 测试：行尾空白行数分别为 0、0；
- `results/paper2_figure2`：不存在；
- `project_control/paper2_figure2_fem_only_numerical_credibility_implementation_lock_v01.json`：不存在；
- 作废的 v07 review：不存在，且本轮未创建；
- 本轮未运行候选代码、Python、pytest、FEniCSx、solver、Docker 或 GPU，未执行 Git 写操作。

## 7. 非阻断 PRECHECK 项

以下不是本轮拒绝理由，而是下一门必须保留的运行前/运行时核验：

1. 创建实现锁时必须绑定本记录第 3 节全部 15 个实际 SHA，并保持合同、阈值、端点、资源上限
   与结果 schema 不变；
2. 获得单独授权后，PRECHECK 必须实际运行完整候选测试集合，尤其包括隔离导入、Docker
   fake-clock、assignment failure、5.0 s readback 和 3/3/4 s worker recovery；
3. Windows 专属真实进程/Job Object 测试必须在获批的 Windows 宿主门内执行；其他平台的 skip
   不能替代该证据；
4. 静态复核不能证明调度抖动下的 5.0 s/299.75 s 上界，也不能证明 FEniCSx、solver、资源门或
   数值门通过；这些只能由后续获批运行给出。

## 8. 精确下一步授权与停止点

下一步只能由人类明确决定是否授权以下窄动作：

1. 依据本记录冻结的 15 个 SHA 创建唯一实现锁；
2. 在实现锁生效后运行合同规定的 PRECHECK，并将 Windows 专属宿主测试单列为 ST0 证据；
3. PRECHECK 完成后停止并返回结果，未经新的书面门禁不得进入 FEniCSx/solver/Docker/GPU
   数值执行、不得创建正式 `results/paper2_figure2` 运行包、不得更新 Figure 2 或作科学结论。

本轮停止于 v07.1 静态 review 写入。除本文件外未修改任何既有文件；未创建实现锁、结果目录
或数值证据；未运行 PRECHECK 或任何候选代码；未执行 Git add、commit、push。
