# Paper 2 Figure 2 FEM-only 数值可信度实现候选：Supervisor 第六轮静态复核 v06

- review_date: 2026-09-04
- reviewer_role: Supervisor
- review_mode: independent_read_only_static_review
- reviewed_surface: 第六版冻结的 15 个实现候选文件
- execution_contract_v03_sha256: `484090034d049d5c48ad6e92ea809fc569ae01cdce26c9c693baebb6143ad38a`
- execution_contract_v03_supervisor_review_v02_sha256: `36949b75b4d3fb93c05219bc0ada3e7e58c31a04f8bc2691f032ae88c26af57e`
- source_review_v05_sha256: `86116f593b6d649121ce1281f337c17f20f3e2395b8e375c7265daf30384757d`
- execution_performed: false
- python_or_pytest_performed: false
- solver_or_docker_performed: false
- result_directory_created: false
- implementation_lock_created: false
- git_write_performed: false
- disposition: `IMPLEMENTATION_REVISION_REQUIRED`
- execution_authorized: false
- precheck_authorized: false
- scientific_claim_authorized: false
- next_gate: `narrow_candidate_revision_then_independent_supervisor_static_review_v07`

## 1. 二元结论

`IMPLEMENTATION_REVISION_REQUIRED`

v06 已静态关闭 canonical gate object 顺序冲突和 ledger path-set 漏检，并加入 300 s/3600 s
双 deadline 字段与 Windows kill-on-close Job Object。这些是有效进展；心内膜离散链、心肌主动
平面应变 FEM、ECM 黏弹平面应变 FEM 的科学架构也没有漂移，心肌 DCM 未回流。

但 v05 的 hard-cap 主阻断并未关闭：包外 readback 仍在父进程内直接运行，不是可终止的只读
边界；Docker inspect/stop/wait 仍未把同一 deadline 对象贯穿至每次调用和解析之后。新增 Job
Object 还存在“先启动、后纳管”的窗口，纳管失败时也不能证明未归属子进程已经同步回收。
此外，deadline 的 `plan` 采样发生在 ledger preflight 之前；runtime test 新增了一处确定性
`NameError`，并保留一处项目规则明确禁止执行的 `Path.unlink()`。

因此本轮不能生成实现锁，不能运行 PRECHECK、pytest、FEniCSx、solver、Docker 或 GPU，
不能创建 `results/paper2_figure2`、数值证据或执行 Git 写操作。

## 2. 第六版冻结输入

三份权威文件保持已接受 SHA。第六版 15 个候选文件当前原始字节冻结如下：

| # | 文件 | bytes | lines | SHA-256 |
|---:|---|---:|---:|---|
| 1 | `src/paper2_figure2/__init__.py` | 521 | 28 | `b960435535758a5b602d80cf5ea125f4d22f367dfd61cdc3897ec5354b760412` |
| 2 | `src/paper2_figure2/spec.py` | 21448 | 595 | `471ef6561beedf8d70dc3d6aafa8068494091c36c2dd1473fd43bc55a02f8d93` |
| 3 | `src/paper2_figure2/manufactured.py` | 37440 | 939 | `dd8dd6cb408c6fe97f9b4c93bb25b0b0092f76b0eea2ac3f9879e7f7c6fb6a01` |
| 4 | `src/paper2_figure2/projection.py` | 12699 | 306 | `e9f4f46cbb86d864f4a04db12e585507b142a2768f95318fc1ab183de765e2ef` |
| 5 | `src/paper2_figure2/observables.py` | 34408 | 871 | `29216f930b3be9cd5af65e912e9a637e2042960ab83fcc5d6f2115f395a5ea85` |
| 6 | `src/paper2_figure2/evidence.py` | 21266 | 555 | `df4c5a68394e7edba21789772d5560319ec324a0e877bf4da675ad76785cbf56` |
| 7 | `src/paper2_figure2/adjudication.py` | 29425 | 854 | `9de9a95fa3babb8731d375b95718b0d7ca0a85b94c950da6d251d6bf9ae14cb7` |
| 8 | `scripts/run_paper2_figure2_fem_only_numerical_credibility_v01.py` | 210080 | 4954 | `8e99de157681742108f256b4e9f966d7261ef16dd825fad0656883085812ff3a` |
| 9 | `tests/paper2_figure2/test_spec_v01.py` | 3779 | 102 | `37d2e25870f6cf9db9f901e355f90fbe053d6965809fa772d972a9a8c0ea9fd1` |
| 10 | `tests/paper2_figure2/test_source_lock_v01.py` | 3038 | 91 | `4ff9e17b6f2348410f59ed68a3922140c00c319ec14e53f412fa0a6f95353511` |
| 11 | `tests/paper2_figure2/test_projection_v01.py` | 3780 | 101 | `7fe50027b8b1574ff69572de3856511ad7c37afd68a6cd27ad61c160e9cd375d` |
| 12 | `tests/paper2_figure2/test_adjudication_v01.py` | 6257 | 171 | `9a9badd4b5fbc97d51a01f25a09dd37ceffbfc182426bfeb4c246e8742d77cb6` |
| 13 | `tests/paper2_figure2/test_evidence_v01.py` | 9644 | 233 | `5c1760db59cb1cac527b264f5ab09a32227e1fa069f71d4e46f289c2fc8657d5` |
| 14 | `tests/paper2_figure2/test_manufactured_v01.py` | 6625 | 164 | `5945cbf3b9a2686d298115e5a24602c50a4f0e6a09f6f0e751e4a087ad985311` |
| 15 | `tests/paper2_figure2/test_runtime_smoke_v01.py` | 81400 | 2237 | `a1aae5705f5ae8a1f3b54921122d5c1cbe0200075f4ddf593239ee2d319a185c` |

正式实现锁与 `results/paper2_figure2` 均仍不存在。未执行任何候选代码。

## 3. 已关闭项

| 项 | v06 静态结果 | 状态 |
|---|---|---|
| canonical gate round-trip | `dag` 保持严格数组顺序；`gates` 改为 exact key-set；新增 canonical write/read 测试 | **CLOSED_STATICALLY** |
| ledger path coverage | readback 先比较 `set(ledger_items) == actual_paths - {hash_ledger}`，再访问路径；summary/inventory/completion 均强制存在 | **CLOSED_STATICALLY** |
| 双 deadline 字段 | FINAL 300 s 与 total 3600 s 的 applicability、absolute、remaining、exhausted 和 shared source 已加入 | **PARTIAL**：plan 采样点仍过早 |
| Windows writer ownership | Job Object 启用 `KILL_ON_JOB_CLOSE`，正常及恢复路径都会关闭 ownership | **PARTIAL**：启动/纳管失败窗口未闭合 |
| 科学范围 | 未见心肌 DCM、流体、三维、第二求解器、GPU、参数扫描或 identity comparator 回流 | **CLOSED_STATICALLY** |

以上关闭均仅是源码静态判断，不代表测试、资源门、数值门或科学结论已经通过。

## 4. 仍阻断接受的问题

### B1. 5.0 s 包外 readback 仍不是 hard cap

`_readback_committed_package()` 第 4429--4515 行仍由父进程直接调用多个
`strict_json_load()`、`rglob()`、`stat()` 和逐文件 hash；调用点在第 4606--4609 与
4625--4626 行。`MonotonicDeadline` 只能在阻塞 I/O 返回后检查，不能中断单次整文件读取、JSON
解析、目录枚举或 metadata I/O。新增 Job Object 只拥有已经退出前的 host-final worker，
并不拥有这段父进程 readback。

runtime test 也没有构造一个真实阻塞超过 5.0 s 的 readback 边界；现有 readback drift 测试仍把
整个函数替换成立即抛错的 mock。因此 v03 第 4.2、4.3 与第 8.1 节冻结的 5.0 s/299.75 s
上界仍未被实现或证明。

最小修订：把包外 readback 放进同文件、只读、可同步终止并可回收的进程边界；该边界不得写
包内或包外文件。父进程必须在 5.0 s 内得到成功或非零结论，并在返回前证明该 readback 进程
已退出或其访问能力已被可靠撤销。补真实阻塞 readback 的超时与无残留进程测试。

### B2. Docker 调用仍未贯穿同一 deadline

`_docker_evidence()` 第 724--752 行仍只接收数值 `timeout`，调用 `_command()` 时不传
`deadline`，JSON 解析和 record 构造后也没有 deadline 复核。`_stop_wait_inspect()` 第
883--939 行仍把 remaining 转成一次性的数值 timeout；直接 `subprocess.run()` stop、Docker
wait 和 pre/post inspect 的实际返回与解析之后均没有完整的同一 deadline 检查。正常退出后的
post-exit inspect 第 4764--4779 行也采用同样模式。

这没有满足 v03 第 184--187、225--228 行“每一项调用前后检查同一 deadline”的要求。

最小修订：让 inspect/stop/wait 的真实调用接收同一个 `MonotonicDeadline`；在每次外部调用前、
调用返回后、JSON/exit-code 解析后和 identity/resource validation 后复核。新增 fake clock 在调用
过程中越过 deadline 的测试，证明即便命令自行返回 0 也必须 `RESOURCE_LIMIT_FAIL/73`。

### B3. Job Object 仍有先执行、后纳管窗口

`_start_owned_host_final_worker()` 第 4363--4385 行先 `Popen()`，后
`ownership.assign(process)`。生产 worker 因而可以在 Job Object 纳管完成前开始访问结果目录。
若 assignment 失败，异常路径调用 exact-PID `kill()`，但其 wait 的 `TimeoutExpired` 或
`RunFailure` 被吞掉，最后关闭的是尚未拥有该进程的空 Job Object；这不能在所有返回路径证明
子进程已经停止写入。

最小修订：增加父进程 ownership release gate。实际 worker 在接到 release 前不得执行任何
文件访问；父进程只在 Job assignment 成功且 deadline 复核通过后释放。assignment/launch
失败时关闭 gate，并同步终止/回收；不得依赖空 Job Object。补 assignment failure 故障注入，
验证 marker 未创建、进程不存活且父进程非零。

### B4. `plan_observed_monotonic` 采样早于 plan

`_prepare_host_finalization()` 第 3850 行先采样 `plan_observed_monotonic`，第 3858--3867 行随后
才执行 host ledger preflight。按 v03 第 7.1 节，全部文件 hash 的只读验证结束后才形成 root
plan；当前 `observed_elapsed_to_plan_seconds` 与 `ready_to_plan_observed_seconds` 会少计 ledger
preflight，字段名和证据语义不符。

最小修订：把唯一 plan 样本移动到最后一项只读验证完成之后、开始构造内存 plan 之前；双
deadline 的 remaining/exhausted 必须使用这同一个样本。补测试证明 ledger preflight 推进的
monotonic 时间被计入两个 observed-to-plan 字段。

### B5. runtime test 当前必然失败且包含禁止执行的删除动作

1. `test_host_deadline_audit_rejects_shared_deadline_that_is_not_the_earlier_one()` 第 1495--1496
   行引用本函数中不存在的 `deadline` 与 `now`，必然触发 `NameError`；
2. `test_handoff_payload_without_ready_is_not_observed_as_terminal()` 第 865 行调用
   `Path.unlink()`。项目级 `AGENTS.md` 明确规定任何出现 `Path.unlink` 的脚本都视为破坏性
   操作并须先停止确认，因此当前测试套件不得执行。

最小修订：删除两条串入错误测试的陈旧断言；让 handoff fixture 支持
`include_ready=False`，从一开始就不创建 ready，而不是先创建再删除。扫描此次 PRECHECK 会
覆盖的全部测试，保证不存在其他删除 API。

## 5. 精确下一步授权边界

本 review 只放行一次窄范围实现修订，不放行执行：

1. 最小修改面仍限于
   `scripts/run_paper2_figure2_fem_only_numerical_credibility_v01.py` 与
   `tests/paper2_figure2/test_runtime_smoke_v01.py`；只有确有必要时才可在同一 15 文件集合内修改
   其他文件；
2. 只关闭 B1--B5，不改设计合同、execution contract v03、科学模型、端点、阈值、资源上限、
   结果 schema、八个 `paper2_hybrid` 核心文件、`CURRENT_STATUS.md` 或旧 review；
3. 修订后冻结全部 15 文件的 bytes/lines/SHA，返回 Supervisor 做第七轮独立静态复核；
4. 在 v07 明确给出 `IMPLEMENTATION_ACCEPTED_FOR_PRECHECK_DECISION` 前，继续禁止 Python、
   pytest、FEniCSx、solver、Docker、GPU、结果目录、实现锁、数值证据与 Git add/commit/push；
5. Windows 专属真实进程测试须在后续 PRECHECK 决策中单列为宿主 ST0，不得只依赖 Linux
   容器中的 skip 结果。

## 6. 本轮停止点

本轮只进行了 PowerShell/文本级只读核验，并新建本 review。未修改 15 个候选、三份权威、
八个核心文件、旧 review 或其他既有文件；未运行 Python、pytest、FEniCSx、solver、Docker
或 GPU；未创建结果目录、实现锁或数值证据；未执行任何 Git 写操作。
