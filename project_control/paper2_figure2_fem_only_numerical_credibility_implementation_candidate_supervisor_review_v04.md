# Paper 2 Figure 2 FEM-only 数值可信度实现候选：Supervisor 第四轮静态复核 v04

- review_date: 2026-09-04
- reviewer_role: Supervisor
- review_mode: independent_read_only_static_review
- reviewed_surface: 第四版冻结的 15 个实现候选文件
- runner_sha256: `2748c80e22c23b1fc43aa1dcdc140d7ebaf14dfef293e0dc0552349de009154c`
- observables_sha256: `29216f930b3be9cd5af65e912e9a637e2042960ab83fcc5d6f2115f395a5ea85`
- manufactured_sha256: `dd8dd6cb408c6fe97f9b4c93bb25b0b0092f76b0eea2ac3f9879e7f7c6fb6a01`
- evidence_sha256: `238a90ab10ab1bebc4ab329810f153ffd0553cb764748867f352a2fe12cc654a`
- runtime_smoke_sha256: `e698af5b1e84f9810eca546b7e569bd2059a0030d1e7e03e293bc9f3b6cdc64f`
- manufactured_test_sha256: `5945cbf3b9a2686d298115e5a24602c50a4f0e6a09f6f0e751e4a087ad985311`
- source_review: `project_control/paper2_figure2_fem_only_numerical_credibility_implementation_candidate_supervisor_review_v03.md`
- source_review_sha256: `2ab96eda0a5e86c99cd96dc865a1234f83667565487000277662eeb463d9d325`
- execution_performed: false
- python_or_pytest_performed: false
- solver_or_docker_performed: false
- result_directory_created: false
- implementation_lock_created: false
- disposition: `IMPLEMENTATION_REVISION_REQUIRED`
- execution_authorized: false
- scientific_claim_authorized: false
- next_gate: `execution_contract_v03_narrow_amendment_then_candidate_revision_then_supervisor_review_v05`

## 1. 二元结论

`IMPLEMENTATION_REVISION_REQUIRED`

第四版已经实质关闭第三轮 B4--B8，并把 B9 的容器停止方向改为“原子取得 ID、只读核对
ID/name/image、随后按 ID 停止”。这些是有效进展；活跃架构仍严格保持为心内膜离散链、
心肌主动平面应变 FEM、ECM 黏弹平面应变 FEM，没有重新引入心肌 DCM、流体或比较器。

但宿主 FINAL 仍不是一个不超过 300 s、失败封闭且互斥发布 PASS 的完整事务。当前还可由
源码直接构造：超过时限后继续写、根账本失败前已留下正式 FINAL PASS、前序门未全 PASS 却
由宿主补成 FINAL PASS，以及 watchdog 首失败被清理失败覆盖。另有一个治理性阻断：
`--cidfile` 和按 ID 停止是关闭 B9 所需的最小安全增强，但它们改变了 v01/v02 冻结的唯一
Docker 参数与 timeout 命令，必须先由窄范围 execution contract v03 正式授权，不能靠实现者
自行改写合同。

因此本轮不能生成实现锁，不能运行 PRECHECK、pytest、FEniCSx、solver 或 Docker，也不能
创建正式结果或提交 Git。

## 2. 第三轮阻断的关闭情况

| v03 项 | 第四轮静态结果 | 状态 |
|---|---|---|
| B1 Windows/FINAL deadline | 已移除宿主对 `setitimer` 和 wall clock 的直接依赖，并加入 handoff 预算；但实际宿主工作未被 deadline 封顶 | PARTIAL |
| B2 FINAL owner/PASS | 容器现只写 provisional outcome；但宿主仍在真实 inventory/ledger/completion 前写正式 PASS | PARTIAL |
| B3 failure/postlock/gate DAG | 已 best-effort postlock，并可从 machine/events 恢复 DAG；但成功 payload 不验证全部前序门，host 首失败仍可被覆盖 | PARTIAL |
| B4 source/ledger/outcome 类型 | traction、mean、free-shortening、time 和 ledger shape 已逐字段 typed fail；stop code 严格排除 float/string/bool | CLOSED_STATICALLY |
| B5 S1 4×8 step conservation | 四个 S1 端点各八个 channel 在 `S1-G5` 接受前形成硬门，并有篡改测试 | CLOSED_STATICALLY |
| B6 PRECHECK S2-only | manufactured 完整运行 smoke 已缩为 S2；S3/S4 完整 G0 仍由 runner 拥有 | CLOSED_STATICALLY |
| B7 pre-holdout digest | 已绑定 `container_start.json` 的实际 ID/name/image 与十个明确权威开发工件 | CLOSED_STATICALLY |
| B8 complement Frobenius | 已用 sparse Frobenius、cross trace 与 rank-two Gram 解析计算，并有小矩阵显式对照 | CLOSED_STATICALLY |
| B9 stop identity | stop 前 ID/name/image 核对和 unknown/foreign-ID 拒停已实现；但新增命令尚未被合同授权 | SAFETY_FIXED_CONTRACT_PENDING |

以上 `CLOSED_STATICALLY` 不是测试 PASS，也不是数值证据。

## 3. 仍阻断实现接受的问题

### R1. Windows host deadline 仍是检查点提示，不是覆盖实际 FINAL 工作的确定性 cap

`MonotonicDeadline` 本身使用宿主本地 `time.monotonic()`，方向正确；问题在于它没有传入并
封顶实际耗时操作：

1. `_prepare_host_finalization()` 只在调用 `_prelock()` 前检查一次 deadline；而 `_prelock()`
   内的多个 Git 命令仍各自使用 `_command()` 的默认 240 s timeout。多个命令可累计超过
   FINAL 的 300 s，且函数返回前没有 deadline 复核；
2. `_host_ledger_preflight()`、NPZ/文件哈希和 `finalize_root_transaction()` 没有 deadline 参数；
3. `_seal_host_finalization()` 只在入口检查一次，随后可继续写 resource、summary、FINAL
   event、stage 状态、inventory、ledger、completion 并复算全目录；
4. `elapsed_seconds` 在 ledger preflight 和全部 seal/root transaction 之前计算，因而资源记录
   会系统性漏掉终局时间；3600 s 总门也没有在根事务完成后复核；
5. 现有 Windows 测试把 `_finalize_host_transaction()` 整体替换为 mock，超时测试只在小型
   临时目录中验证“入口已过期仍能写出失败”，没有证明真实 postlock/hash/seal 被硬封顶。

最小修订要求：让 postlock 的每个外部命令、NPZ/哈希预检、seal 和 root transaction 共用
同一宿主 monotonic deadline，并为每个可阻塞调用传入剩余 timeout；在每个调用前后复核，
最终 elapsed 必须覆盖 completion 与只读复算。若必须用独立 host-final worker 实现 Windows
硬停止，worker 必须同步、可终止且不得留下后台写线程；超时后只能形成唯一 FAIL 或明确的
`INCOMPLETE_TRANSACTION`，不能继续声称完整 PASS。补真实调用层的预算耗尽测试，不能只 mock
掉整个 transaction。

### R2. 正式 FINAL/PASS 仍早于真实 inventory、ledger、completion 与最终自检

runner 约第 3550--3627 行先写：

- `pass_summary.json` 及正式 `PASS_LABEL`；
- `08_final/final_adjudication.json` 的 `PASS`；
- `manifest_events.jsonl` 的 `FINAL=PASS`；
- `08_final/stage_complete.json`；

随后才调用 `finalize_root_transaction()` 写 inventory、ledger、completion 并复算。若 FINAL
event 追加、stage completion、inventory/ledger/completion 写入或最终复算任一点失败，目录已
留下正式 PASS 标志。`formal_only_with_root_completion=true` 不能消除同目录中已经写出的
`FINAL=PASS` 和 `stage_complete`。

当前 late-fault 测试注入的是 `_host_ledger_preflight()`，不是实际
`finalize_root_transaction()` 的 inventory 写、ledger 写、completion 写或 post-write
self-check，因此没有覆盖第三轮 B2 的关键反例。

最小修订要求：把终局设计成单一两阶段事务。任何在 root transaction 真正完成前写出的
summary/adjudication/event/stage 状态都必须是非正式 `PREPARED/PROVISIONAL`；正式 PASS 的唯一
语义必须依赖最后 completion 及 ledger/inventory 的独立复算，且不能与合同的
`no_files_after_completion=true` 冲突。故障注入至少覆盖 FINAL event、stage completion、
inventory、ledger、completion 和最终复算；每一种故障都必须证明不存在一个可独立解释为
完整正式 PASS 的根。

### R3. 宿主没有验证“全部前序门 PASS”及 resource payload 的严格类型

`_validate_container_outcome()` 对 provisional success 只检查：stop code 为 0、FINAL 是
`NOT_REACHED`、`first_failure=None`、`next_gate=FINAL`。它没有要求：

- `dag` 与冻结 `GATE_DAG` 完全相等；
- gate key 集合完全相等；
- PRECHECK 至 S1-G7 每一门都为 PASS；
- applicable/not-applicable 计数和 checks schema 自洽。

若 outcome 只含 FINAL，`_recover_gate_summary()` 会把缺失前序门恢复为 `NOT_REACHED`；只要没有
另一个 host failure，`_seal_host_finalization()` 仍会手工把 FINAL 改为 PASS 并写 PASS summary。
这直接违反“所有适用门 PASS 才可 FINAL”。

同一成功路径对 `container_resource` 也使用 truthiness 和 `int()` 强转，例如字符串形式的
`cpu_affinity_count` 或非整数 `memory_peak_bytes` 可能通过；这不满足冻结的严格 JSON/schema
边界。

最小修订要求：宿主对 provisional success 做 exact-schema 验证，逐门要求全部前序 gate PASS，
校验完整 DAG、check schema/count 和互斥状态；resource 的整数、布尔、数组字段使用精确 JSON
类型并排除 bool/float/string 强转。补“缺一门、前序 NOT_REACHED、前序 FAIL、DAG 乱序、
resource 错类型”故障测试。

### R4. watchdog 首失败仍可被 stop/inspect/outcome 的后续失败覆盖

`_host_launch()` 约第 3734 行捕获 `wait_failure` 后，先执行 `_stop_wait_inspect()`，直到该调用和
`host_timeout.json` 写入均成功才把 `failure` 设为 watchdog code 73。若 stop、wait、inspect 或
timeout 文件写入失败，外层 `except RunFailure` 会直接用后续错误替换原始 watchdog 失败。
即使已经设置 `failure`，同一外层 try 的后续异常仍在约第 3794 行无条件覆盖它。

最小修订要求：捕获 watchdog 时立即冻结 first failure，所有 cleanup/outcome/inspect 问题只进
secondary failures；整个 host launch 使用一个“仅在 first failure 为空时赋值”的观察器。
补 `watchdog + stop fail`、`watchdog + inspect fail`、`watchdog + outcome malformed` 三组测试，
证明根 summary 的首失败始终为 `RESOURCE_LIMIT_FAIL/73`。

### R5. `final_handoff.json` 的生产者/消费者存在可见半写文件竞争

容器用 `_exclusive_json()` 直接以 `xb` 创建 `final_handoff.json`，随后写入、flush、fsync；宿主
轮询只要 `is_file()` 为真就立即读取验证。文件名在内容写完前已经可见，宿主可能读到空或
部分 JSON，并把一次正确运行误判为资源失败。现有 handoff 测试都在进入 wait 前预先写完
marker，没有覆盖并发发布窗口。

最小修订要求：采用符合 create-only/禁止覆盖约束的发布协议，例如先完整 fsync handoff
payload，再独占创建单独的 ready sentinel，宿主只观察 sentinel 后读取 payload；或者提供
等价、可证明不会把部分写当最终字节的协议。该协议及新增工件必须写入下一版执行合同，并补
“payload 已创建但未完成、ready 未出现”和“ready 后 payload 不一致”测试。

### R6. `--cidfile` 与按 ID stop 是正确的最小安全增强，但当前违反冻结执行合同

候选 `_docker_arguments()` 新增 `--cidfile <r01>/container.cid`，`_stop_wait_inspect()` 改为按
已验证 container ID 执行 stop。这是关闭 B9、避免误停同名外部容器所需且应保留的安全方向；
不建议回退到未验证名称 stop。

但 execution v01 第 700--728 行和 execution v02 第 737--769 行都把 Docker 参数声明为“唯一
参数向量”，其中没有 `--cidfile`；v02 第 775--780 行还冻结为按精确名称执行 stop。实现不能
自行改变已接受合同，因此当前会同时出现“更安全”与“protocol drift”两个事实。

最小治理修订要求：先只起草窄范围
`paper2_figure2_fem_only_numerical_credibility_execution_contract_v03.md`，明确：cidfile 路径、
Docker 在计算启动前绑定 ID 的语义、`container_start.json` 与 digest/inventory 的关系、未知 ID
拒停、核对 ID/name/image 后按 ID stop，以及 R5 的 handoff ready 协议。v03 不得改变科学
方程、40 个端点、N1--N11、阈值、资源总额、S1 或结果 schema；经独立接受后，再把 v03 哈希
加入 source lock 并修订候选。

## 4. 与实现阻断分开的运行前检查

以下仍是以后才允许执行的 ST0/PRECHECK，不是本轮阻断的替代品，也没有被运行：

1. S2/S3/S4 eigsh、Ritz residual、S4 LinearOperator 内存与实际收敛；
2. PRECHECK、端点、G0、post/S1、container FINAL 与 Windows host FINAL 的真实耗时；
3. Docker image/inspect、none-network、cgroup、`ru_maxrss` 与单 worker 证据；
4. 216 commitments、NPZ 压缩大小和完整 root transaction 的真实重读；
5. 固定镜像内 pytest 的真实通过情况。

## 5. 下一步边界

1. 先只允许起草 R6 所述 execution contract v03 窄修订，不执行任何代码；
2. v03 经独立 Supervisor 接受后，才允许在原 15 文件内关闭 R1--R5 并同步 source lock；
3. 修订后冻结全部字节，返回 Supervisor 做第五轮只读静态复核；
4. 在新的静态接受与 PRECHECK 授权决定出现前，禁止 Python、pytest、solver、Docker、GPU、
   `results/paper2_figure2`、实现锁和 Git add/commit/push；
5. 保护用户已有 7 个 tracked 修改和全部既有未跟踪证据，不得删除、覆盖或移动。
