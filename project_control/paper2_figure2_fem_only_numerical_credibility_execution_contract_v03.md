---
contract_id: CONTRACT-PAPER2-FIGURE2-FEM-ONLY-NUMERICAL-CREDIBILITY-EXECUTION-V03
status: draft_for_independent_supervisor_review
created_at: 2026-09-04
created_by: executor
governance_mode: governed_computational_paper
baseline_commit: c52b2de7536a055699b2e23011fa221a6f2f1019
baseline_upstream_ahead_behind: 0/0
accepted_design_contract: project_control/paper2_figure2_fem_only_numerical_credibility_contract_v03.md
accepted_design_contract_sha256: 796de6a6cfa6167e30cae592128379206709ace720d4fcbe3ae80366fb504249
incorporates_execution_contract_v01: project_control/paper2_figure2_fem_only_numerical_credibility_execution_contract_v01.md
incorporates_execution_contract_v01_sha256: 2cbbae0f09bb966e9292a306f4c7a698952f9bf962139c772b1cfb02e4b7c070
incorporates_execution_contract_v02: project_control/paper2_figure2_fem_only_numerical_credibility_execution_contract_v02.md
incorporates_execution_contract_v02_sha256: 11ebd843cf23c404c920a0274b409a907e01cd1755a2a5812de1eb8bdc66e253
source_review: project_control/paper2_figure2_fem_only_numerical_credibility_implementation_candidate_supervisor_review_v04.md
source_review_sha256: 1638e6e6140e1a2131abd828aba0a5789199603dba21dc44c21a894eca5520a1
revision_review: project_control/paper2_figure2_fem_only_numerical_credibility_execution_contract_v03_supervisor_review_v01.md
revision_review_sha256: 65638d9049d32e02e314fe3c49cb6b8c8ef7e6c1a68548217df2686a7f95f200
active_architecture: endocardium_discrete_chain__myocardium_active_fem__ecm_viscoelastic_fem
evidence_level: prospective_narrow_host_orchestration_amendment_not_implementation_or_numerical_evidence
implementation_authorized: none
execution_authorized: none
next_gate: independent_supervisor_contract_review
---

# Paper 2 Figure 2 FEM-only 数值可信度执行合同 v03

## 0. 目的、优先级与本轮边界

本文件只修订 Figure 2 数值可信度运行的宿主编排层，关闭第四轮独立静态复核 v04 的
R1--R6。它不是新的科学合同，不改变模型、端点、判据或结果数组，也不接受当前实现候选。

规范优先级固定为：已接受设计合同 v03 最高；本执行合同 v03 对宿主编排的窄修订次之；
执行合同 v02 的其余条款再次之；执行合同 v01 的其余未冲突条款最后。只有本文件明确列出
的冲突条款被替换，不得把未重复内容解释为撤销。

本轮只允许新增本草案并交独立 Supervisor 复核。当前仍禁止：

- 修改 15 个实现候选文件、八个核心 `paper2_hybrid` 文件、设计合同、v01/v02、旧 review、
  `CURRENT_STATUS.md` 或用户既有 tracked 修改；
- 运行 Python、pytest、FEniCSx、solver、Docker 或 GPU；
- 创建 `results/paper2_figure2`、实现锁或任何数值证据；
- Git add、commit、push，或更新 Figure 2。

## 1. 明确保持不变的科学与资源合同

以下内容全部沿用设计合同 v03 与执行合同 v01/v02，不在本文件中重新裁量：

1. 活跃架构仍为心内膜离散链、心肌主动平面应变 FEM、ECM 黏弹平面应变 FEM；不引入
   心肌 DCM、流体、三维、第二求解器、GPU、参数扫描或 identity comparator；
2. 40 个唯一动态端点、S2/S3/S4、T64/T128/T256、D0、开发/S1 顺序与复用不变；
3. G0--G7、digest、S1 子门、N1--N11、全部阈值、floor、方向和 stop code 不变；
4. 公共域仍为 128 个空间段、256 个相位箱；`common_observables.npz` 的 key、shape、dtype、
   216 项 formal commitments 与 128 MiB 上限不变；
5. 单 CPU、8 GiB、无网络/GPU/socket、容器不自动删除、总计 3600 s 不变；
6. `NPZ + postlock + inventory + ledger + completion` 的 FINAL 总额仍为 300 s；本文件只
   冻结其内部安全分配，不增加总预算。

任何实现借本合同改变以上任一项，均为 `SOURCE_OR_PROTOCOL_DRIFT_FAIL/10`。

## 2. Docker 启动与原子容器身份

### 2.1 唯一允许的参数变化

执行合同 v01 第 13.2 节与 v02 第 12.1 节的 Docker 参数向量只作一个变化：在 `--name` 后
加入宿主侧 cidfile；其余参数、顺序语义、镜像、挂载、环境与入口保持不变。

```text
docker run
  --name paper2-figure2-nc-v03-r01
  --cidfile E:\Temp-Projects\PRL\results\paper2_figure2\fem_only_numerical_credibility_v03_20260904_r01\container.cid
  --network none
  --cpus 1
  --memory 8g
  --memory-swap 8g
  --pids-limit 256
  --read-only
  --cap-drop ALL
  --security-opt no-new-privileges
  --tmpfs /root/.cache:rw,exec,nosuid,size=2g
  --mount type=bind,source=E:\Temp-Projects\PRL,target=/workspace,readonly
  --mount type=bind,source=E:\Temp-Projects\PRL\results\paper2_figure2\fem_only_numerical_credibility_v03_20260904_r01,target=/output
  --workdir /workspace
  --env TMPDIR=/root/.cache/tmp
  --env OMP_NUM_THREADS=1
  --env OPENBLAS_NUM_THREADS=1
  --env MKL_NUM_THREADS=1
  --env NUMEXPR_NUM_THREADS=1
  --env PYTHONDONTWRITEBYTECODE=1
  dolfinx/dolfinx:v0.11.0
  python3 scripts/run_paper2_figure2_fem_only_numerical_credibility_v01.py
    --inside-container --project-root /workspace --output-root /output --run-id r01
    --implementation-lock /workspace/project_control/paper2_figure2_fem_only_numerical_credibility_implementation_lock_v01.json
```

`container.cid` 必须在全新 r01 根内且启动前不存在。Docker 对 cidfile 的创建失败即启动失败，
不得回退为按名称猜测身份、列举同名对象或另启容器。

### 2.2 启动绑定顺序

宿主在 `Popen` 后按以下顺序绑定本事务容器：

1. 等待 `container.cid`，但不得因为名称存在而取得控制权；
2. cidfile 必须恰为 64 位小写十六进制完整 ID；float、短 ID、多行、空白外内容或非 ASCII
   均拒绝；
3. 只读执行 `docker inspect <full-id>`；
4. inspect 的 `Id` 必须等于 cidfile，`Name` 必须等于冻结名称，`Image` 必须等于冻结 image
   ID；三者任一不符即 `CONTAINER_ID_MISMATCH_FAIL/72`；
5. 只有核验通过后，宿主才独占写/fsync `container_start.json`，其 exact schema 为
   `name/id/image_id`；
6. `container_start.json` 的字节 SHA、三个值和 `container.cid` 字节 SHA 必须进入
   pre-holdout digest，并在 S1 前后复核；二者及其角色必须进入最终 inventory/ledger。

未知 ID、cidfile 未就绪或 inspect 不可读时，宿主不得对同名容器执行任何 stop/kill/remove。
身份未知是 code 72 或资源不可读 code 73，但安全失败不得变成名称级破坏操作。

### 2.3 停止只按已验证完整 ID

执行合同 v02 第 12.2 节的“按精确名称停止”由本节替换。任何 stop 前必须重新
`docker inspect <full-id>` 并再次核对 ID/name/image。核对通过后，唯一停止序列为：

```text
docker stop --time 30 <full-id>
docker wait <full-id>
docker inspect <full-id>
```

停止、等待与末次 inspect 都使用完整 ID，不使用名称。容器仍保留为 stopped；删除、`--rm`、
prune 或自动重试继续禁止。

## 3. FINAL handoff 的 create-only 发布协议

### 3.1 两文件协议

容器进入 FINAL 后，按程序顺序创建：

1. `final_handoff_payload.json`：以 `xb` 独占创建，写完整 canonical JSON，flush、fsync、close；
2. `final_handoff.ready`：仅在 payload 已关闭后，以 `xb` 独占创建零字节文件，flush、fsync、
   close。

宿主只轮询零字节 `final_handoff.ready`，不得以 payload 的 `is_file()` 作为就绪条件。ready
可见而 payload 缺失、不可 strict JSON 读取、schema 不完整或与 `08_final/final_budget.json`
最终字节 SHA 不同，均为 fail-closed。payload 已可见但 ready 尚未出现只是 `NOT_READY`，宿主
继续受 3600 s watchdog 约束，不得提前读取并误判半写文件。

两文件、`08_final/final_budget.json` 及其 SHA/role 全部进入 inventory/ledger；不得覆盖、重命名
或删除不完整 payload。

### 3.2 handoff payload exact schema

payload 固定包含：

- `schema = paper2_figure2_final_handoff_v03`；
- `container_cap_seconds = 120.0`；
- `host_handoff_deadline_seconds = 299.5`；
- `handoff_poll_seconds = 0.25`；
- `host_stop_reserve_seconds = 130.0`；
- `host_seal_reserve_seconds = 30.0`；
- `host_recovery_reserve_seconds = 160.0`；
- `worst_case_from_ready_seconds = 299.75`；
- `budget_composition = container_FINAL_runs_inside_host_handoff_deadline`；
- `clock_domains = container_and_host_monotonic_are_not_compared`；
- `scope = container NPZ through host root_completion`。

容器 monotonic 值可作为诊断字段，但不得与宿主 monotonic 或 wall clock 相减。不得使用
`time.time()`、文件 mtime 或跨 VM wall clock 扩张 300 s 正确性边界。

## 4. Windows 宿主 monotonic deadline 与同步 worker

### 4.1 单一边界

宿主首次观察到 ready 时，以同一宿主 `time.monotonic()` 建立两个不可向后移动的绝对时刻：

- `final_absolute_deadline = ready_observed_monotonic + 299.5 s`；
- `total_absolute_deadline = host_create_monotonic + 3600.0 s`；
- `shared_absolute_deadline = min(final_absolute_deadline, total_absolute_deadline)`。

父进程和 worker 的唯一剩余量都是
`remaining = shared_absolute_deadline - host_monotonic_now`。worker 启动延迟、内部重启计时、
容器状态或任何局部异常都不得重置、重算或延长这三个绝对时刻。轮询间隔最多 0.25 s，因此
从 ready 发布到宿主命令结束的确定性上界仍最多 299.75 s，不超过 300 s。容器 120 s FINAL
cap 与宿主 deadline 重叠，不得相加为新预算，也不得把未用时间借给其他阶段。

若容器在 deadline 剩余 160 s 时仍未返回，立即进入恢复序列。恢复序列的本地上界为：
pre-stop inspect 10 s、stop 45 s、wait 60 s、post-stop inspect 10 s，共 125 s；130 s 为停止
预算，另保留 30 s 失败封账。任何单项 timeout 取“该项上限、共享 deadline 剩余时间”两者
较小值，并在调用前后检查同一 deadline。

### 4.2 host-final worker

Windows 宿主不得依赖 `signal.setitimer/SIGALRM`，也不得用不可终止的后台线程模拟 hard cap。
宿主 runner 可在同一文件中增加一个内部 `--host-final-worker` 模式；它不是第二 runner，也
不得改变科学调用。父进程以参数数组同步启动该 worker，传入 r01、绑定容器 ID、首失败记录
与上述不可变绝对 deadline。

启动 worker 前冻结以下父进程尾部预算，单位均为宿主 monotonic 秒：

- `worker_recovery_reserve_seconds = 10.0`；
- `normal_worker_wait_cap_seconds = 284.5`；
- `terminate_grace_wait_seconds = 3.0`；
- `kill_grace_wait_seconds = 3.0`；
- `final_reap_join_status_seconds = 4.0`；
- `post_exit_readonly_verify_seconds = 5.0`；
- `parent_tail_reserve_seconds = 15.0`。

其中三项恢复上限恰好合计 10.0 s，正常退出后的只读复核另占最多 5.0 s。若 worker 启动前
`remaining <= 15.0 s`，父进程不得启动 worker，直接冻结 `RESOURCE_LIMIT_FAIL/73`。正常等待
上限固定为：

```text
normal_wait_timeout = min(284.5, max(0, remaining_at_wait_start - 15.0))
```

不得把全部 remaining 交给第一次 wait。正常 wait 返回后，不调用 terminate/kill；父进程仅在
最多 5.0 s 内完成第 4.3 节的包外只读复核与返回状态判定。正常 wait 超时则立即进入唯一恢复
序列：terminate 后 wait 最多 3.0 s，仍存活则 kill 后 wait 最多 3.0 s，最后 wait/join、exit-code
与无活动 writer 核对最多 4.0 s。每一步实际 timeout 仍取其局部上限与当时 `remaining` 的较小
值；任何一步不能在不可变 `shared_absolute_deadline` 前证明同步回收，父进程必须非零返回，
标记本次运行不完整，且绝不形成宿主成功。

worker timeout 的首失败固定为 `RESOURCE_LIMIT_FAIL/73`；若根事务已经开始但没有有效
completion，目录按第 7.3 节定义为 `INCOMPLETE_TRANSACTION`，绝不解释为 PASS。父进程不得
重启 worker，也不得把恢复余量转回正常计算。

worker 内每个 Git/inspect 外部命令也必须使用共享 deadline 的剩余 timeout；不能因为父进程
有 timeout，就让子命令保留各自 240 s 默认值。NPZ 重读、逐文件 hash、postlock、root plan、
写入和 completion 前的只读复核均在同一 worker hard timeout 内。每项前后检查 deadline；任何检查失败只记
code 73，不能继续发布完整 PASS。

### 4.3 3600 s 总门与时间证据

3600 s watchdog 仍从 HOST_CREATE 前的宿主 monotonic 起点计时。FINAL deadline 与总门始终取
上述较早的不可变绝对时刻。completion 前写入工件包的最终资源证据只记录当时已经真实观测
到的字段：

- HOST_CREATE 至 host-final plan 的 observed monotonic elapsed；
- ready 至 plan 的 observed monotonic elapsed；
- 覆盖 completion fsync 的 certified monotonic upper bound；
- 300 s 与 3600 s 两个 deadline 的剩余/耗尽状态；
- 冻结的 `worker_exit_policy`、10.0 s recovery reserve、3.0/3.0/4.0 s 分项上限、5.0 s 包外
  只读复核上限与 15.0 s parent tail reserve。

权威合规量是覆盖 completion 的 certified upper bound；较早采样的 observed elapsed 只作诊断，
不得冒充完整运行耗时。completion 前不得预写或推测 worker 的实际 exit、terminate、kill、
wait/join 结果；这些只有父进程在事后知道，属于包外运行结果，不写回工件包。

worker 成功 fsync completion 后立即进入静态 no-write tail：只允许从当前调用栈返回并退出；
不得再写文件、启动子进程、创建后台线程、调用 solver/Docker/Git 或改变工件目录。父进程实际
wait/join 后只做最多 5.0 s 的只读核对，包括 completion strict JSON、inventory/ledger hash、
completion 后无新增/修改文件与 worker exit code；不创建日志或计时文件。只有 worker exit 0、
未进入 terminate/kill、只读核对通过且仍早于 `shared_absolute_deadline`，宿主命令才返回 0。

## 5. provisional success 的宿主 exact validation

容器成功 outcome 只能为 `PROVISIONAL_CONTAINER_COMPLETE`，不得含正式候选标签、FINAL PASS
或 `08_final/stage_complete.json`。宿主进入 PASS plan 前必须验证：

1. outcome exact key 集合、`stop_code` 为 JSON integer 0 且排除 bool/float/string，容器 exit
   code 也为 0；
2. `dag` 与冻结 `GATE_DAG` 的值和顺序完全相等，gate key 集合完全相等；
3. PRECHECK 至 S1-G7 每一前序门均为 `PASS`，FINAL 恰为 `NOT_REACHED`，
   `first_failure=null`、`next_gate=FINAL`；
4. 每门 `applicable/not_applicable/checks` 类型、计数与 check record exact schema 自洽；任何
   前序 FAIL/NOT_REACHED、缺门、多门、乱序或计数冲突均 fail-closed；
5. `container_resource` 使用 exact JSON 类型：整数必须 `type is int` 且排除 bool/float/string，
   Boolean 必须 `type is bool`，数组必须是 JSON list 且元素类型精确；禁止 truthiness 或
   `int()` 强转；
6. CPU affinity 非空且 count 等于列表长度；memory peak 为非负整数且不超过 8 GiB；cgroup
   与 `ru_maxrss` 不得同时为 null；network interfaces 只能为空或 `['lo']`；socket/GPU 必须
   为 false；Docker inspect 的全部冻结资源字段仍按 v02 校验。

宿主不得用 `_recover_gate_summary()` 把成功 outcome 缺失的前序门补成 PASS。恢复函数只用于
失败审计，永不把 `NOT_REACHED` 提升为成功。

## 6. first-failure preservation

宿主 runner 使用唯一 `observe_failure()` 规则：仅当 `first_failure is None` 时赋值；之后任何
cleanup、inspect、outcome、postlock、NPZ、hash、seal 或 worker 问题只追加到
`secondary_failures`，不得覆盖首因。

watchdog 异常一经捕获，必须在调用 stop/wait/inspect 或写 `host_timeout.json` 前立即冻结
`RESOURCE_LIMIT_FAIL/73`。即使随后发生 stop fail、inspect fail、outcome malformed 或审计
文件写失败，根 summary 的首失败仍为 watchdog 73；后续异常只进入 secondary evidence。

对已经创建的 r01，所有路径仍 best-effort 执行只读 postlock。postlock 失败不得覆盖更早首因；
若此前无失败，才成为 `SOURCE_OR_PROTOCOL_DRIFT_FAIL/10`。完整 gate summary 必须保留已通过门、
首失败门和全部后续 `NOT_REACHED`。

## 7. 两阶段 root transaction 与正式 PASS 唯一语义

### 7.1 Phase A：只读验证与内存 plan

host-final worker 首先完成 Docker/resource、postlock、NPZ、digest、exact gate/resource schema
和全部文件 hash 的只读验证。随后在内存构造唯一 root plan，包括所有将写 bytes、
manifest append bytes、inventory、ledger 和 prospective completion bytes。任何 plan/self-check
失败发生在正式 PASS 字节写入前。

### 7.2 Phase B：PREPARED 写入与 completion commit

PASS path 在 completion 前只允许下列非正式状态：

- `pass_summary.json`: `status=PREPARED`，标签字段名为 `prepared_candidate_label`；不得出现
  可独立解释的 `candidate_label`；
- `gate_summary.json`: FINAL 为 `PREPARED`；
- `08_final/final_adjudication.json`: `status=PREPARED`；
- `manifest_events.jsonl`: FINAL event 为 `PREPARED`；
- `08_final/stage_prepared.json`；不得提前写 `stage_complete.json`。

以上每个 payload 必须声明 `formal_only_with_valid_root_completion=true`。Phase B 固定顺序为：

1. 写/fsync 所有 PREPARED payload，关闭并 fsync FINAL PREPARED event；
2. 写/fsync inventory；
3. 写/fsync ledger；
4. 在 completion 尚不存在时，对全目录、inventory、ledger 及 prospective completion 的
   path/bytes/SHA 做完整只读复核；
5. 再次检查共享 deadline 与 3600 s 总门；
6. 最后以预先冻结 bytes 独占写/fsync `root_completion.json`，此后不再写任何文件。

`root_completion.json` 的 `status=PASS` 与通过预完成复核的 ledger/inventory 共同构成工件包
内部唯一正式 commit，并把上述 PREPARED 状态解释性提升为包内 FINAL PASS、stage complete
和 `FIGURE2_FEM_ONLY_NUMERICAL_CREDIBILITY_PASS_V03`。缺 completion、completion 非 strict
JSON、hash 不符或 ledger/inventory 不覆盖时，PREPARED 文件永远不是包内正式 PASS。

包内 commit 与宿主命令成功是两个有序但不循环依赖的层次：

1. worker 先在不可变 deadline 内完成包内 commit；completion 只陈述 fsync 当时可知事实和
   冻结的 `worker_exit_policy`，不声称实际 exit/wait/join 已发生；
2. completion fsync 后，worker 执行第 4.3 节的静态 no-write tail 并退出；
3. 父进程 wait/join 后在 5.0 s 包外上限内只读核对，且不向包内写回；
4. 只有 worker 正常 exit 0、未使用 terminate/kill、只读核对通过且未越过较早绝对 deadline，
   宿主命令才可对外报告成功。

因此，worker 在 completion 后卡住时，工件包字节可能仍满足内部 commit，但本次宿主命令必须
经 10.0 s 恢复序列非零返回，对外状态唯一为 `COMMITTED_BUT_HOST_FAILED`，不得发布、引用或
向用户报告 Figure 2 PASS。父进程只读复核发现 hash/新增文件/strict JSON 错误时，对外状态为
`PACKAGE_COMMIT_INVALID_ON_READBACK`；同样非零返回且不得报告成功。包外状态只存在于进程
返回/标准错误与调用方内存，不写回 completion 后已冻结的工件包。

该语义替换 v02 第 11.3 节中“先写 FINAL PASS/stage complete、后写 ledger/completion、再
self-check”的冲突部分，但保留 create-only、completion 最后、ledger 不自哈希和
`no_files_after_completion=true`。

### 7.3 FAIL 与 INCOMPLETE

已知首失败且尚未开始 Phase B 时，按 v02 early/late FAIL path 写唯一 failure transaction。
若 Phase B 的 event、prepared stage、inventory、ledger、prospective completion 复核或
completion 写入失败：

- 不得创建第二 summary，不得覆盖或删除既有字节；
- 没有有效 `root_completion.status=PASS` 的根统一为 `INCOMPLETE_TRANSACTION`；
- 任何 PREPARED 标记都不得解释为 PASS；
- worker 必须退出非零，父进程必须同步终止/回收；
- 重试只能另立合同/run id，不得续接 r01。

有效 completion 写出后，worker 只允许 no-write return/exit，父进程只允许包外只读复核；任何
新增或修改文件都会使包内 commit 在 readback 时失效。completion 后 worker 卡住或回收失败不
反向改写已经关闭的包内字节，但强制本次宿主命令非零返回并禁止对外报告成功。

## 8. 最小故障注入与验收测试

下一版实现候选必须在原 15 文件范围内加入下列测试，但本合同阶段不运行：

### 8.1 Deadline 与 worker

- Windows 无 `setitimer/SIGALRM`；wall clock 回拨不改变 deadline；
- worker 启动延迟与内部计时不能移动
  `min(ready_observed+299.5, host_create+3600.0)` 的较早绝对 deadline；
- postlock 的每个 Git 命令、host NPZ、逐文件 hash、root plan/commit 在真实调用层耗尽预算；
  禁止把整个 transaction mock 掉；
- 正常 wait 固定为 `min(284.5, remaining-15.0)`；真实 worker 边界分别验证 terminate wait 3.0 s、kill
  wait 3.0 s、final reap/join/status 4.0 s 与只读核对 5.0 s，任何路径不遗留 writer；
- elapsed/certified upper bound 覆盖 completion，且 299.75/3600 s 不被放宽。

### 8.2 Handoff 与容器身份

- payload 已创建或仍在写、ready 未出现时，宿主不读取、不误判；
- ready 出现后 payload 缺失、strict JSON/schema 错或 stage budget SHA 不同即失败；
- cidfile unavailable、malformed、foreign ID/name/image 时，任何 stop 命令调用数为零；
- 核验通过后 stop/wait/inspect 的参数均为同一完整 ID，不出现名称 stop。

### 8.3 Success exact schema

- 缺一个前序门、前序 `NOT_REACHED`、前序 `FAIL`、DAG 乱序、gate key 多/少、check count/schema
  错误均不得进入 PASS plan；
- resource 的 int 字段分别注入 bool/float/string，Boolean/list 元素注入错类型，全部失败；
- 合法完整 provisional payload 才可形成 PREPARED plan。

### 8.4 首失败与两阶段事务

- `watchdog + stop fail`、`watchdog + inspect fail`、`watchdog + outcome malformed` 三组都保留
  首失败 `RESOURCE_LIMIT_FAIL/73`，后者只进入 secondary；
- 分别在 FINAL event、stage prepared、inventory、ledger、prospective completion self-check、
  completion write 注入失败；每种情况下均无有效正式 PASS 根；
- 仅当 PREPARED 全部落盘、预完成复核通过且 completion 最后写入时，根才可解释为 PASS；
- completion 后 worker 正常退出且包外只读复核通过时宿主才返回 0；
- completion 后 worker 卡住时保留包内 commit 字节，但恢复后返回
  `COMMITTED_BUT_HOST_FAILED`，不得对外报告 PASS；
- completion 后目录多一个字节或任一 hash 变化，包外只读复核返回
  `PACKAGE_COMMIT_INVALID_ON_READBACK`，不得写回工件包。

所有这些测试仍只是实现验收证据；不产生 Figure 2 数值 PASS。

## 9. 与 v01/v02 的窄差异清单

本 v03 只作以下八项差异：

1. Docker 参数向量新增唯一 `--cidfile <r01>/container.cid`；
2. stop/wait/inspect 从按名称改为“先核对 ID/name/image，再按完整 ID”；
3. `container_start.json` 与 cidfile 身份/哈希进入 digest、inventory 和 ledger；
4. FINAL handoff 从观察正在写的单文件改为 payload 完成后发布零字节 ready；
5. Windows host FINAL 使用父进程可终止、可 wait 的同步 worker 覆盖 postlock、NPZ、hash、
   seal 和 root transaction；较早绝对 deadline 不可移动，正常 wait 保留 15.0 s parent tail，
   其中 worker recovery 为 3.0/3.0/4.0 s、包外只读核对最多 5.0 s，不用 signal 或 wall clock；
6. first failure 在任何 cleanup 前冻结，后续错误只进 secondary；
7. provisional success 增加完整 DAG、全部前序 PASS 和 resource exact JSON 类型校验；
8. completion 前的成功语义从 PASS 改为 PREPARED；最后有效 root completion 与
   ledger/inventory 预完成复核只形成包内 commit，completion 后静态 no-write 退出和父进程
   包外 wait/join/readback 再独立决定宿主命令能否对外报告成功。

除这八项外，v01/v02 的科学、数值、端点、门禁、资源和证据条款全部保持。特别是 300 s/
3600 s 总额、40 endpoints、N1--N11、S1、NPZ schema 与 128 MiB 上限未改变。

## 10. 合同验收门与停止边界

独立 Supervisor 只有在确认以下全部成立时才可接受本草案：

1. v03 只处理 v04 R1--R6 的宿主编排，不扩张科学范围；
2. cidfile/按 ID stop 的安全增强被正式授权且无名称级误停路径；
3. payload + zero-byte ready 消除半写可见竞争；
4. Windows 同步 worker 使用不可移动的较早绝对 deadline，正常 wait 上限 284.5 s 并保留
   15.0 s parent tail，3.0/3.0/4.0 s 恢复与 5.0 s 只读复核均有可测试上限且不留后台 writer；
5. exact provisional schema 不允许缺失前序门被提升为 PASS；
6. watchdog 首失败不能被 cleanup 或 malformed outcome 覆盖；
7. PREPARED/root completion 只形成无循环的包内 commit；completion 后 worker 为静态
   no-write tail，父进程的实际 wait/join/readback 仅决定包外宿主返回，不伪造到包内证据；
8. completion 后卡住或 readback 失败的包内状态、宿主返回与用户可见结论互不矛盾；
9. 本文件仍是未执行的合同草案，不冒充实现、测试或数值证据。

本文件冻结后立即停在独立 Supervisor 合同复核门。未获得新的书面接受与实现修订授权前，
不得修改候选、运行 PRECHECK/pytest/solver/Docker、创建结果/实现锁或执行 Git 操作。
