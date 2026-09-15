# Paper 2 Figure 2 FEM-only 数值可信度执行合同 v03：Supervisor 独立复核 v02

- review_date: 2026-09-04
- reviewer_role: Supervisor
- review_mode: independent_read_only_contract_review
- reviewed_contract: `project_control/paper2_figure2_fem_only_numerical_credibility_execution_contract_v03.md`
- reviewed_contract_bytes: 26070
- reviewed_contract_lines: 440
- reviewed_contract_sha256: `484090034d049d5c48ad6e92ea809fc569ae01cdce26c9c693baebb6143ad38a`
- source_review: `project_control/paper2_figure2_fem_only_numerical_credibility_execution_contract_v03_supervisor_review_v01.md`
- source_review_sha256: `65638d9049d32e02e314fe3c49cb6b8c8ef7e6c1a68548217df2686a7f95f200`
- execution_performed: false
- python_or_pytest_performed: false
- solver_or_docker_performed: false
- result_directory_created: false
- implementation_lock_created: false
- disposition: `ACCEPTED_FOR_IMPLEMENTATION_REVISION`
- implementation_revision_authorized: `narrow_original_15_candidate_files_only`
- execution_authorized: false
- scientific_claim_authorized: false
- next_gate: `candidate_revision_then_independent_supervisor_static_review_v05`

## 1. 二元结论

`ACCEPTED_FOR_IMPLEMENTATION_REVISION`

C1/C2 窄修订已满足前审 v01 的七项再审接受条件。合同现在以不可移动的宿主绝对 deadline
统一父子进程预算，正常等待不再吞掉恢复和包外复核余量；同时把
`root_completion.json + inventory/ledger` 的包内 commit 与父进程事后观察到的
exit/wait/join/readback 结果明确分层，消除了 completion 前后事实的循环依赖。

前审第 2 节已接受的 cidfile/完整 ID、payload+ready、exact provisional schema、first-failure
和 PREPARED/root transaction 方向均原样保留。科学架构、40 个动态端点、N1--N11、阈值、
S1、300/3600 s、NPZ schema 与资源上限未漂移。本轮没有真实合同 blocker。

本结论只接受合同并放行窄范围实现修订；它不是实现验收、PRECHECK 授权、运行证据或
Figure 2 科学 PASS。

## 2. v01 七项再审条件

| 条件 | v03 当前冻结条款 | 结论 |
|---|---|---|
| 1. 正常等待保留恢复预算 | `normal_wait_timeout = min(284.5, max(0, remaining-15.0))`；父尾部固定 15.0 s，其中恢复 10.0 s、包外只读 5.0 s | SATISFIED |
| 2. 绝对截止不可移动 | `final_absolute_deadline=ready_observed+299.5`、`total_absolute_deadline=host_create+3600.0`，父子只使用两者较早值；启动延迟或局部计时不得重置 | SATISFIED |
| 3. completion/exit 无循环 | completion 与已预完成复核的 inventory/ledger 只形成包内 commit；实际 exit/wait/join/readback 只决定包外宿主返回 | SATISFIED |
| 4. completion 后零写入 | worker 仅允许 no-write return/exit；父进程只读核验且不写回；包内资源证据不预写实际退出结果 | SATISFIED |
| 5. completion 后异常语义 | 卡住或回收失败为 `COMMITTED_BUT_HOST_FAILED`；readback 失败为 `PACKAGE_COMMIT_INVALID_ON_READBACK`；两者均非零且不得对外报告 PASS | SATISFIED |
| 6. 已接受方向与科学边界 | cidfile、完整 ID、ready、exact schema、首失败与两阶段事务均保留；科学/数值/资源不变量无变化 | SATISFIED |
| 7. 未执行证据边界 | frontmatter 与停止条款仍声明无实现、无执行、无数值证据，且先停在独立合同复核门 | SATISFIED |

## 3. C1 复核：不可移动 deadline 与可回收 worker

1. 父进程在观察 ready 后冻结
   `shared_absolute_deadline = min(ready_observed+299.5, host_create+3600.0)`；worker 接收该
   绝对时刻，而不是用自身启动时刻重建一份可延长预算。
2. worker 启动前若 `remaining <= 15.0 s`，直接以
   `RESOURCE_LIMIT_FAIL/73` 停止，不把不可证明的尾部工作挤进截止线。
3. 正常 wait 上限为 284.5 s，并同时受 `remaining-15.0` 约束；因此第一次 wait 不会再消费
   全部 remaining。
4. 超时恢复固定为 terminate wait 3.0 s、kill wait 3.0 s、最终 reap/join/status 4.0 s，
   合计 10.0 s；每项仍受不可移动 shared deadline 约束。
5. 正常退出后的 completion/readback 核验最多 5.0 s；只有 exit 0、未使用 terminate/kill、
   核验通过且仍在较早 deadline 内，宿主才可返回 0。
6. 第 8.1 节要求在真实 worker 边界验证启动延迟、各恢复分项、包外复核和无活动 writer，
   没有用整体 transaction mock 代替关键预算证据。

因此 C1 已从“有共享 deadline 但无回收余量”修订为数值明确、可实现且可故障注入的闭环。

## 4. C2 复核：包内 commit 与宿主成功分层

1. PREPARED payload、inventory、ledger 和 prospective completion 均在 completion 前完成
   写入及只读预完成复核；`root_completion.json` 仍为包内最后一次写入。
2. completion 只陈述 fsync 当时可知事实与冻结的 `worker_exit_policy`，不伪造实际
   exit/terminate/kill/wait/join 结果。
3. completion 后 worker 只允许沿当前调用栈返回并退出；禁止新增文件、子进程、后台线程、
   solver、Docker 或 Git 调用。
4. 父进程的实际 wait/join 与最多 5.0 s readback 是包外运行结果，不反向写入已 commit 的
   工件包，也不成为包内字节的循环前提。
5. 包内 commit 有效但 worker 卡住时，宿主必须经冻结恢复序列非零返回并使用
   `COMMITTED_BUT_HOST_FAILED`；包外 readback 发现 hash、strict JSON 或 completion 后字节
   漂移时使用 `PACKAGE_COMMIT_INVALID_ON_READBACK`。两者均禁止发布、引用或向用户报告
   Figure 2 PASS。
6. 第 8.4 节已冻结 completion 后正常退出、卡住和 readback 漂移的三类故障注入，并要求
   不向包内写回。

因此 C2 采用了前审建议的“包内 commit + 包外宿主返回”方案，并保持
`no_files_after_completion=true`。

## 5. 前审已接受条款与边界漂移核对

| 核对面 | 当前冻结结果 |
|---|---|
| 容器身份 | `--cidfile` 位于全新 r01；只接受 64 位完整小写十六进制 ID；stop 前重核 ID/name/image；未知或不匹配身份禁止名称级停止 |
| Handoff | payload 完整 fsync/close 后才发布零字节 ready；宿主只观察 ready；半写 payload 不被当作终态 |
| Provisional success | exact key/DAG/gate/check schema；全部前序门必须 PASS；resource 字段使用精确 JSON 类型且排除有损强转 |
| First failure | `observe_failure()` 只首次赋值；watchdog 73 在 cleanup 前冻结；后续异常只进 secondary |
| Root transaction | completion 前仅 PREPARED；inventory/ledger/prospective completion 预复核后才独占写 completion；completion 后零写入 |
| 科学范围 | 心内膜离散链、心肌主动平面应变 FEM、ECM 黏弹平面应变 FEM；未引入心肌 DCM、流体、三维、第二求解器、GPU、参数扫描或 identity comparator |
| 数值范围 | 40 endpoints、S2/S3/S4、T64/T128/T256、D0、G0--G7、digest、S1 子门、N1--N11、阈值/floor/方向/stop code 均沿用 |
| 数组与资源 | 128×256 公共域、216 formal commitments、NPZ key/shape/dtype、128 MiB、单 CPU、8 GiB、无网络/GPU/socket 均沿用 |
| 时间总额 | FINAL 300 s 与根事务 3600 s 总额均未增加；C1 只在原有总额内切分父进程尾部预算 |

## 6. 与合同接受分开的实现与运行检查

下列内容仍须由后续实现候选及其静态复核证明，不能倒推为本轮合同 blocker，也尚未获得
执行授权：

1. Windows 实现确实不使用 `setitimer`、wall clock 或不可终止后台线程，并按绝对 deadline
   将剩余 timeout 传到每个实际阻塞调用；
2. worker terminate/kill/reap、completion 后 no-write tail 与父进程 readback 的故障注入测试
   已真实进入行为路径；
3. cidfile、ID/name/image、payload+ready、exact outcome/resource schema 与完整 gate DAG 的
   实现逐项符合合同；
4. PREPARED、inventory、ledger、prospective completion 和最终 completion 的字节事务通过
   独立静态复核；
5. PRECHECK、pytest、FEniCSx、solver、Docker、资源/耗时及数值门禁的运行结果以后另行授权。

## 7. 精确下一步授权边界

本复核仅授权 Executor 在原冻结的 15 个实现候选文件内进行一次窄范围静态修订：

1. 按本合同 v03 实现 cidfile/完整 ID、payload+ready、不可移动 absolute deadline、
   284.5 s 正常 wait、15.0 s parent tail、3.0/3.0/4.0 s worker recovery、5.0 s 包外只读核验、
   first-failure、exact provisional schema 和 PREPARED/root completion 两层语义；
2. 在原 15 文件内同步相应故障注入测试与 source-lock 绑定，将本合同当前 SHA256
   `484090034d049d5c48ad6e92ea809fc569ae01cdce26c9c693baebb6143ad38a` 纳入实现候选的冻结依据；
3. 不得修改八个核心 `paper2_hybrid` 文件、设计合同 v03、执行合同 v01/v02/v03、既有 review、
   `CURRENT_STATUS.md`、用户既有 tracked 修改或任何其他文件；
4. 本授权不包含运行 Python、pytest、FEniCSx、solver、Docker 或 GPU，不包含创建
   `results/paper2_figure2`、实现锁、数值证据，也不包含 Git add、commit 或 push；
5. 修订完成后须冻结全部 15 文件的新 SHA，并返回独立 Supervisor 做实现候选第五轮静态复核。
   只有后续静态复核另行接受，才可讨论实现锁与 PRECHECK 授权。

## 8. 本轮停止点

本轮仅执行 PowerShell/文本级只读核验并新建本 review；未运行 Python、pytest、FEniCSx、
solver、Docker 或 GPU，未创建 `results/paper2_figure2`、实现锁或数值证据，未修改合同、
15 个实现候选、八个核心文件、旧 review 或其他既有文件，未执行 Git add、commit 或 push。
