# Paper 2 Figure 2 FEM-only 数值可信度实现候选：Supervisor 第五轮静态复核 v05

- review_date: 2026-09-04
- reviewer_role: Supervisor
- review_mode: independent_read_only_static_review
- reviewed_surface: 第五版冻结的 15 个实现候选文件
- execution_contract_v03_sha256: `484090034d049d5c48ad6e92ea809fc569ae01cdce26c9c693baebb6143ad38a`
- execution_contract_v03_supervisor_review_v02_sha256: `36949b75b4d3fb93c05219bc0ada3e7e58c31a04f8bc2691f032ae88c26af57e`
- source_review_v04_sha256: `1638e6e6140e1a2131abd828aba0a5789199603dba21dc44c21a894eca5520a1`
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
- next_gate: `narrow_candidate_revision_then_independent_supervisor_static_review_v06`

## 1. 二元结论

`IMPLEMENTATION_REVISION_REQUIRED`

第五版已经实质关闭 v04 的 R2、R4、R5，并在执行合同 v03 授权下关闭 R6：容器只发布
provisional outcome；宿主用 PREPARED 工件、预完成 inventory/ledger/prospective completion
和最后写入的 `root_completion.json` 形成包内 commit；completion 后 worker 沿静态 no-write
调用栈退出；cidfile、完整 ID/name/image 核验及按完整 ID 停止也均已落地。科学架构、40 个
端点、N1--N11、阈值、S1、NPZ 与资源范围没有观察到静态漂移。

但当前候选仍有两个真实接受阻断。第一，容器把 `gate_summary.gates` 以 canonical sorted-key
JSON 写盘，而宿主要求该 JSON object 的读取顺序等于非字典序的 `GATE_DAG`；因此真实成功
outcome 在宿主一定被判为 `RESOURCE_LIMIT_FAIL/73`。第二，Windows 宿主的 deadline 仍有
未硬封顶部分：包外 5.0 s readback 在父进程内直接执行不可中断的整文件读取和目录枚举，
Docker inspect/stop/wait 路径也没有把 deadline 对象贯穿到调用后复核；现有测试没有在真实
worker/readback 边界证明这些上限与无活动 writer。

因此本轮不能生成实现锁，不能运行 PRECHECK、pytest、FEniCSx、solver、Docker 或 GPU，
不能创建 `results/paper2_figure2`、数值证据或执行 Git 写操作。

## 2. 权威与冻结输入核验

三份权威文件的当前字节 SHA-256 均与委托值完全一致。第五版 15 个候选文件也逐项按原始
字节、物理行数和 SHA-256 核对一致，且未发现行尾空白漂移：

| # | 文件 | bytes | lines | SHA-256 |
|---:|---|---:|---:|---|
| 1 | `src/paper2_figure2/__init__.py` | 521 | 28 | `b960435535758a5b602d80cf5ea125f4d22f367dfd61cdc3897ec5354b760412` |
| 2 | `src/paper2_figure2/spec.py` | 21448 | 595 | `471ef6561beedf8d70dc3d6aafa8068494091c36c2dd1473fd43bc55a02f8d93` |
| 3 | `src/paper2_figure2/manufactured.py` | 37440 | 939 | `dd8dd6cb408c6fe97f9b4c93bb25b0b0092f76b0eea2ac3f9879e7f7c6fb6a01` |
| 4 | `src/paper2_figure2/projection.py` | 12699 | 306 | `e9f4f46cbb86d864f4a04db12e585507b142a2768f95318fc1ab183de765e2ef` |
| 5 | `src/paper2_figure2/observables.py` | 34408 | 871 | `29216f930b3be9cd5af65e912e9a637e2042960ab83fcc5d6f2115f395a5ea85` |
| 6 | `src/paper2_figure2/adjudication.py` | 29425 | 854 | `9de9a95fa3babb8731d375b95718b0d7ca0a85b94c950da6d251d6bf9ae14cb7` |
| 7 | `src/paper2_figure2/evidence.py` | 21266 | 555 | `df4c5a68394e7edba21789772d5560319ec324a0e877bf4da675ad76785cbf56` |
| 8 | `scripts/run_paper2_figure2_fem_only_numerical_credibility_v01.py` | 199960 | 4692 | `114b3f7eb16c651b875faa8c335ae1fe9f938390b472a3ce2e9698f9b6074397` |
| 9 | `tests/paper2_figure2/test_spec_v01.py` | 3779 | 102 | `37d2e25870f6cf9db9f901e355f90fbe053d6965809fa772d972a9a8c0ea9fd1` |
| 10 | `tests/paper2_figure2/test_source_lock_v01.py` | 3038 | 91 | `4ff9e17b6f2348410f59ed68a3922140c00c319ec14e53f412fa0a6f95353511` |
| 11 | `tests/paper2_figure2/test_projection_v01.py` | 3780 | 101 | `7fe50027b8b1574ff69572de3856511ad7c37afd68a6cd27ad61c160e9cd375d` |
| 12 | `tests/paper2_figure2/test_manufactured_v01.py` | 6625 | 164 | `5945cbf3b9a2686d298115e5a24602c50a4f0e6a09f6f0e751e4a087ad985311` |
| 13 | `tests/paper2_figure2/test_adjudication_v01.py` | 6257 | 171 | `9a9badd4b5fbc97d51a01f25a09dd37ceffbfc182426bfeb4c246e8742d77cb6` |
| 14 | `tests/paper2_figure2/test_evidence_v01.py` | 9644 | 233 | `5c1760db59cb1cac527b264f5ab09a32227e1fa069f71d4e46f289c2fc8657d5` |
| 15 | `tests/paper2_figure2/test_runtime_smoke_v01.py` | 69233 | 1883 | `1a0118356a8d18ee1bc4e55ab98a7daafadb2ca3e5d28264c3343dce8c57d225` |

`spec.py` 已把 execution contract v03 当前 SHA
`484090034d049d5c48ad6e92ea809fc569ae01cdce26c9c693baebb6143ad38a`
纳入 source lock；`IMPLEMENTATION_PATHS` 仍恰为上述 15 项。当前正式实现锁与
`results/paper2_figure2` 均不存在，符合本轮只读门禁。

## 3. v04 R1--R5 与 execution contract v03 R6 逐项复核

| 项 | 第五版静态结果 | 状态 |
|---|---|---|
| R1 Windows/FINAL deadline | 绝对 monotonic deadline、284.5 s 正常 wait、15.0 s parent tail、3/3/4 s recovery 和可终止 worker 已实现；但父进程 5.0 s readback 仍非 hard cap，Docker recovery 也未逐调用做 deadline 后复核，真实边界测试不完整 | **PARTIAL / BLOCKER** |
| R2 PREPARED/root transaction | 容器不再写正式 PASS；宿主在 completion 前仅写 PREPARED；inventory、ledger、prospective completion 复核后才最后写 completion，之后函数只有内存返回 | **CLOSED_STATICALLY** |
| R3 exact outcome/DAG/resource | outcome、check、resource 的 exact key/type 与全部前序 PASS 校验已加入；但 gate object 的错误顺序要求与 canonical JSON 写盘互相冲突 | **PARTIAL / BLOCKER** |
| R4 first failure | `_host_launch()` 与 host-final prepare 均只在 first failure 为空时赋值；watchdog 在 cleanup 前冻结，后续 stop/inspect/outcome 问题进入 secondary | **CLOSED_STATICALLY** |
| R5 handoff race | payload 以 `xb` 完整写入、flush/fsync/close 后，再以 `xb` 发布零字节 ready；宿主只观察 ready，并校验 payload、schema 和 budget copy hash | **CLOSED_STATICALLY** |
| R6 cidfile/按 ID stop 合同授权 | v03 已授权 `--cidfile`；实现要求恰 64 bytes 小写十六进制 ID，核对 ID/name/image，未知或 foreign identity 时拒绝任何 stop，停止与 wait/inspect 均使用完整 ID | **CLOSED_STATICALLY** |

以上 `CLOSED_STATICALLY` 只说明源码结构与冻结合同相符，不代表相关测试已运行，也不代表
数值门、资源门或科学结论通过。

## 4. 真正阻断实现接受的问题

### B1. canonical JSON 与 gate object 顺序校验冲突，使真实成功路径必然失败

这是确定性行为错误，不是风格问题：

1. runner 第 207--214 行的 `_canonical_bytes()` 对所有嵌套 JSON object 使用
   `sort_keys=True`，第 217--223 行的 `_exclusive_json()` 使用这些字节落盘；
2. 容器第 3601--3608 行把 `machine.summary()` 放入 `container_outcome.json` 并经上述
   canonical writer 写出；
3. `GateMachine.summary()` 在 `adjudication.py` 第 805--829 行虽按 `GATE_DAG` 插入 gate，
   但落盘时嵌套 `gates` key 会被重新排成字典序；冻结 DAG 从 `PRECHECK` 开始、以 `FINAL`
   结束，并非字典序；
4. 宿主第 3681--3697 行 strict-load 该文件后调用 validator；validator 第 1291--1292 行却
   要求 `list(gates) == list(GATE_DAG)`，把 JSON object 的读取顺序误当成合同语义；
5. execution contract v03 第 5 节冻结的是 `dag` 数组“值和顺序完全相等”以及 gate **key
   集合**完全相等，并未授权 object key 顺序成为证据。

因此，按生产路径生成的每个合法 provisional success 都会在宿主被固定为
`RESOURCE_LIMIT_FAIL/73`，无法形成 PREPARED plan。测试没有发现该问题，因为
`_valid_provisional_outcome()` 在内存中按 DAG 插入 key 后直接调用 validator；宿主 fixture
又用未排序的 `json.dumps(outcome)` 写盘，二者都绕过生产 canonical writer。

最小修订：保留 `dag == list(GATE_DAG)` 的严格顺序校验，把 `gates` 改为 exact key-set 校验；
新增一项使用生产 `_exclusive_json()` 写出、`strict_json_load()` 重读、再走宿主 outcome
validator 的真实 round-trip 测试，并保留 missing/extra gate 的 fail-closed 测试。

### B2. R1 的确定性 deadline 与真实 worker 边界证明仍未闭合

当前绝对时刻和预算常数本身正确，但还有三处合同要求未被实现或证明：

1. `_readback_committed_package()` 第 4194--4217 行在父进程中直接执行多个
   `strict_json_load()`；`strict_json_load()` 又在 `evidence.py` 第 71--72 行一次性
   `read_bytes()`。runner 第 4235--4239 行还直接执行完整 `rglob()`/排序。deadline 只在这些
   阻塞操作的外围或逐文件 hash 块之间检查。若整文件读取、JSON 解析、目录枚举或 metadata
   I/O 阻塞，检查只能在超时后拒绝成功，不能把父进程实际耗时硬限制在 5.0 s，也不能证明
   ready 至宿主返回不超过 299.75 s。
2. `_docker_evidence()` 第 724--752 行只接收数值 timeout，调用 `_command()` 时没有传入
   deadline；`_stop_wait_inspect()` 第 883--939 行把当时 remaining 换成数值后，pre-inspect、
   直接 `subprocess.run()` stop、wait 和 post-inspect 均没有完整的调用后 deadline 复核。
   这不满足 v03 第 184--187 行“每一项调用前后检查同一 deadline”的冻结要求。
3. 测试第 963--1007 行用 fake worker 验证了 3/3/4 数值；第 1010--1037 行的真实 sleeper
   只覆盖 terminate 足以结束的分支；第 1097--1130 行则把整个 readback 替换成立即抛错的
   mock。它们没有真实覆盖 worker 启动延迟、terminate 无效后进入 kill、final reap/join、
   一个会超过 5.0 s 的实际 readback、以及这些路径结束时无活动 writer。event/stage 与
   inventory/ledger/prospective/completion 的故障注入本身有效，但均直接调用函数，不能替代
   上述进程边界证据。

这里的风险不是“超时后误报 PASS”——末尾检查通常会拒绝成功——而是宣称的 5.0 s、
299.75 s/300 s 硬上界和可回收边界并未由实现保证，故仍是 R1 接受阻断。

最小修订：让 Docker inspect/stop/wait 的实际调用接收同一 deadline，并在每次调用与解析的
前后复核；把包外 readback 放入可同步终止和回收的只读边界，使父进程能在 5.0 s 内得到
成功或非零结论且绝不写回包内；补真实进程测试覆盖启动延迟、terminate、kill、final reap、
readback 超时和无活动 writer。不得用不可终止后台线程，也不得移动 shared absolute deadline。

## 5. 已关闭项的静态证据边界

1. **源码锁**：v03 当前 SHA 已进入 host/container prelock，核心文件、15 个候选文件、
   implementation lock、HEAD/upstream 与 scoped status 均有锁定路径；Git 子命令已接收 worker
   deadline。
2. **身份安全**：cidfile 的长度、字符集、ID/name/image 一致性及 unknown/foreign-ID 拒停均
   有源码和定向测试；未发现退回名称级 stop 的路径。
3. **handoff**：`final_handoff_payload.json` 关闭后才创建零字节
   `final_handoff.ready`，宿主以 ready 为唯一终态观察点；ready 后缺失、partial 或 hash 不符
   均 fail-closed。
4. **exact schema**：除 B1 的 object-order 错误外，outcome、stop code、check、resource、DAG
   数组、全部前序门及 count/check 一致性均采用精确类型或精确 key-set 校验。
5. **首失败**：watchdog 的 `RESOURCE_LIMIT_FAIL/73` 在 cleanup 之前冻结，后续异常不覆盖首因。
6. **事务**：成功路径的 summary、FINAL adjudication/event/stage 均为 PREPARED；
   inventory/ledger/prospective completion 预检完成后，`root_completion.json` 最后写入；其后
   `finalize_root_transaction()` 没有文件读写、子进程或 checkpoint。父进程根据实际 worker
   exit/readback 区分 host success、`COMMITTED_BUT_HOST_FAILED` 与
   `PACKAGE_COMMIT_INVALID_ON_READBACK`，且不写回已提交包。
7. **科学/数值静态范围**：活跃对象仍为心内膜离散链、心肌主动平面应变 FEM 与 ECM 黏弹
   平面应变 FEM；未见心肌 DCM、流体、三维、第二求解器、GPU、参数扫描或 identity
   comparator 回流。36 formal + 4 S1 holdout、S2/S3/S4、T64/T128/T256、D0、G0--G7、
   digest、S1 子门、N1--N11、阈值、128×256 公共域、24-key NPZ、216 commitments、128 MiB、
   单 CPU/8 GiB/无网络-GPU-socket 均保持冻结。

## 6. 与实现阻断分开的 ST0/PRECHECK

下列事项必须等静态实现接受后另行授权并实际运行；它们不是本轮两个 blocker 的替代品：

1. S2/S3/S4 eigsh、Ritz residual、S4 LinearOperator 内存与真实收敛；
2. PRECHECK、G0、40 个端点、post/S1、container FINAL 与 Windows host FINAL 的实际耗时；
3. Docker image/inspect、none-network、cgroup、`ru_maxrss`、单 worker 与资源上限；
4. 216 commitments、NPZ 大小、完整 inventory/ledger/completion 及包外 readback；
5. 固定镜像内 pytest 的真实通过情况和所有数值 gate 的可复算证据。

## 7. 精确下一步授权边界

本结论只放行一次**窄范围实现修订**，不放行任何执行：

1. 仅在原冻结 15 文件内关闭 B1、B2；最小预计修改面为
   `scripts/run_paper2_figure2_fem_only_numerical_credibility_v01.py` 与
   `tests/paper2_figure2/test_runtime_smoke_v01.py`。若无需实现 B2，不得顺带改动科学模块、数值
   模块、阈值、端点、资源或结果 schema；
2. 保持 execution contract v03 及其当前 SHA 不变；本轮没有授权起草 v04，也没有授权修改
   设计合同、既有 review、八个 `paper2_hybrid` 核心文件、`CURRENT_STATUS.md` 或其他文件；
3. 修订后重新冻结全部 15 文件的 bytes/lines/SHA，并返回独立 Supervisor 做第六轮只读静态
   复核；
4. 只有 v06 另行给出 `IMPLEMENTATION_ACCEPTED_FOR_PRECHECK_DECISION` 后，才可进一步讨论
   实现锁创建与 ST0/PRECHECK 授权；
5. 在此之前继续禁止 Python、pytest、FEniCSx、solver、Docker、GPU、
   `results/paper2_figure2`、实现锁、数值证据以及 Git add/commit/push。

## 8. 本轮停止点

本轮只进行了 PowerShell/文本级只读核验，并新建本 review。未修改 15 个候选、三份权威、
八个核心文件、旧 review 或其他既有文件；未运行 Python、pytest、FEniCSx、solver、Docker
或 GPU；未创建结果目录、实现锁或数值证据；未执行任何 Git 写操作。
