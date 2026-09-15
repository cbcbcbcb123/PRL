# Paper 2 Figure 2 FEM-only 数值可信度执行合同 v03：Supervisor 独立复核 v01

- review_date: 2026-09-04
- reviewer_role: Supervisor
- review_mode: independent_read_only_contract_review
- reviewed_contract: `project_control/paper2_figure2_fem_only_numerical_credibility_execution_contract_v03.md`
- reviewed_contract_sha256: `0544862b250dfa9e488c426bd48d8db745263f45dc4a234c05158d39de131220`
- source_review: `project_control/paper2_figure2_fem_only_numerical_credibility_implementation_candidate_supervisor_review_v04.md`
- source_review_sha256: `1638e6e6140e1a2131abd828aba0a5789199603dba21dc44c21a894eca5520a1`
- execution_performed: false
- python_or_pytest_performed: false
- solver_or_docker_performed: false
- result_directory_created: false
- implementation_lock_created: false
- disposition: `CONTRACT_REVISION_REQUIRED`
- implementation_revision_authorized: false
- execution_authorized: false
- scientific_claim_authorized: false
- next_gate: `revise_execution_contract_v03_C1_C2_then_independent_supervisor_review_v02`

## 1. 二元结论

`CONTRACT_REVISION_REQUIRED`

v03 的修订方向正确，而且严格维持既定科学架构：心内膜为离散细胞链，心肌为主动平面
应变 FEM，ECM 为黏弹平面应变 FEM；没有引入心肌 DCM、流体、三维、第二求解器、GPU、
参数扫描或 identity comparator。40 个动态端点、N1--N11、阈值、S1、公共域、NPZ schema、
128 MiB、300/3600 s 和单 CPU/8 GiB/无网络资源边界均未漂移。

合同已经在文字层面实质关闭第四轮实现复核 R2--R6 的主要方向，并为 R1 建立了共享
deadline 与可终止 worker 的正确骨架。但第 4.2、4.3 与第 7.2 节之间仍有两个内部不可同时
满足的条件：worker 的正常等待会耗尽全部共享预算，未给 terminate/kill/join 留出时间；同时
又要求 completion 写完后不再写文件，却把只有父进程在 completion 之后才能知道的 worker
退出/join 结果纳入最终资源证据和正式 PASS 条件。

因此当前合同不能授权修改 15 个实现候选文件，也不能运行 PRECHECK、pytest、FEniCSx、
solver、Docker 或 GPU，不能创建正式结果或提交 Git。允许的下一步仅是在同一未接受的 v03
草案中做 C1--C2 的窄范围文字修订，冻结新 hash 后进入 Supervisor v02 复核。

## 2. 已接受的合同方向

以下项目在本轮合同层面无新增阻断，但“合同方向接受”不等于实现通过或数值证据成立：

| 项目 | 复核结果 | 状态 |
|---|---|---|
| 科学架构与端点 | 未改变设计合同 v03；明确排除心肌 DCM 与流体 | ACCEPTED_CONTRACT_LEVEL |
| 容器身份 | `--cidfile`、64 字符完整 ID、ID/name/image 三项核对、未知身份禁止停止 | ACCEPTED_CONTRACT_LEVEL |
| 停止对象 | 仅按已验证完整 ID 停止，不回退为名称级 stop/kill/remove | ACCEPTED_CONTRACT_LEVEL |
| handoff | payload 写闭合后再原子创建零字节 ready；宿主只观察 ready | ACCEPTED_CONTRACT_LEVEL |
| provisional success | exact schema、完整 DAG、全部前序 PASS 与资源类型硬校验 | ACCEPTED_CONTRACT_LEVEL |
| 首失败 | cleanup/inspect/outcome 后续错误只能进入 secondary，不能覆盖首失败 | ACCEPTED_CONTRACT_LEVEL |
| 根事务 | 正式成功推迟到 inventory/ledger 与 prospective completion 复核之后 | ACCEPTED_CONTRACT_LEVEL |
| 故障注入 | 覆盖超时、身份、handoff、类型、首失败和各事务阶段 | ACCEPTED_DIRECTION |

这些条款应原样保留；本轮不重新裁量科学、数值、资源或证据范围。

## 3. 合同阻断

### C1. worker 正常等待耗尽全部 deadline，清理序列没有冻结预算

第 4.2 节第 187 行规定父进程先执行
`wait(timeout=shared_deadline.remaining)`，只有该等待超时后才 terminate、短等待、必要时 kill，
最后 wait/join。若第一次 wait 已消费全部剩余预算，后续任何 terminate/kill/join 等待都会发生
在 299.75/300 s FINAL deadline 或更早的 3600 s 总门之外。于是合同同时要求“共享 deadline
硬封顶”和“超时后同步回收 worker”，但没有给出能让二者共同成立的时间分配。

这也使第 8.1 节要求的“worker timeout 后 terminate/kill/wait 完成且不遗留 writer”目前没有
可判定、可测试的上界。仅把每个 timeout 写成 `min(局部上限, remaining)` 不够，因为 remaining
可能已经为零。

最小修订要求：

1. 在启动 worker 前冻结一个明确的 worker recovery reserve，并给出 terminate 等待、kill 等待
   和最终 join/状态核对的逐项上限；各项总和不得超过该 reserve；
2. 正常 worker wait 的 timeout 必须最多为“较早共享 deadline 的剩余时间减去 recovery
   reserve”，不得使用全部 remaining；
3. 父进程始终持有原始、不可向后移动的 FINAL 与 total deadline；子 worker 的启动延迟或
   内部计时不得延长这两个截止时刻；
4. 每个 terminate/kill/wait/join 调用仍取其局部上限与当时 remaining 的较小值；当安全回收
   无法在冻结上界内得到证明时，必须返回非零并明确为运行不完整，绝不形成正式 PASS；
5. 故障注入必须在真实 worker 边界证明“正常等待 + 恢复 + 同步回收”不越过冻结上界，且
   没有活跃后台 writer。

合同不必增加 300 s 总额，只需在现有总额内明确切分正常工作与回收预算。

### C2. completion 之后才能知道的 worker 退出事实，无法写入 completion 之前冻结的证据

第 4.3 节第 207 行要求最终资源证据记录 worker 正常退出、terminate、kill 和 join 结果；
第 7.2 节第 277 行又规定 `root_completion.json` 必须最后写入，且此后不得再写任何文件；
第 282 行进一步把“父 worker 已同步退出”设为 PREPARED 文件成为正式 PASS 的必要条件。

这三项不能同时实现。worker 负责写 completion 时，父进程只有在 completion 写完、worker
随后真正退出并被 wait/join 后，才知道实际退出和 join 结果。此时按合同已禁止写文件，因而
无法把该事实真实地加入 resource、inventory、ledger 或 completion。反过来，若预先声称
worker 会正常退出，则该字段不是观测事实；worker 也可能在写出 PASS completion 后、实际
退出前卡住，使目录表面具有正式 PASS 字节，却不满足第 282 行的正式条件。

最小修订要求：合同必须选择并冻结一种无循环的唯一语义。建议采用最小改动方案：

1. `root_completion.json + 已验证 inventory/ledger` 是工件包内部唯一正式 commit；
2. worker 在 completion 成功 fsync 后进入静态限定的 no-write tail，除退出外不得再调用任何
   文件写入、子进程或后台线程入口；
3. completion 之前的 resource 证据只记录可真实观测的状态与预先冻结的
   `worker_exit_policy`，不得伪造实际 exit/terminate/kill/join 结果；
4. 父进程的 wait/join 与只读复核是包外运行结果，不写回已经完成的包，也不作为目录字节
   已正式 commit 的循环前提；若父进程不能在 C1 的回收预算内确认退出，命令必须返回非零，
   此次运行不得由编排层对外报告成功；
5. 合同需明确区分“工件包内部 commit 有效性”与“本次宿主命令成功返回”，并为 completion
   后卡住、父进程回收失败和只读复核失败分别冻结唯一解释。

若不采用上述方案，也可改为由 worker 在 completion 前退出、父进程确认退出后再由父进程
完成 inventory/ledger/completion 的唯一最终提交；但必须重新给父进程的最终写入冻结预算，
且仍需保持 completion 最后、无后台 writer、失败互斥与不越过较早 deadline。两种方案只能
选一个，不能继续把 completion 前后事实循环依赖。

## 4. 再审接受条件

Supervisor v02 只检查以下条件：

1. C1 的 recovery reserve 与各阶段上界数值明确，正常等待不会吃掉回收预算；
2. 父子进程共享的最终绝对截止语义不可因 worker 启动而延长；
3. C2 选择了一种无循环的 completion/worker-exit 语义；
4. completion 之后仍保持零写入，证据字段只陈述当时可真实观测的事实；
5. completion 后 worker 卡住时，工件内部状态、宿主返回状态和用户可见结论互不矛盾；
6. 本文件第 2 节列出的已接受方向与全部科学/数值边界原样保留；
7. 修订仍只是一份未执行合同，不冒充实现、测试、运行或数值证据。

满足以上七项后，Supervisor 才可给出
`ACCEPTED_FOR_IMPLEMENTATION_REVISION`，并另行授权对冻结的 15 个实现候选文件进行窄范围
修订。在此之前，任何代码修改或执行都属于越门。

## 5. 本轮停止点

本轮在合同复核记录冻结后停止。未执行 Python、pytest、FEniCSx、solver、Docker 或 GPU；
未创建 `results/paper2_figure2` 或实现锁；未修改 15 个实现候选文件、八个核心
`paper2_hybrid` 文件、已接受设计合同、v01/v02、既有 review、`CURRENT_STATUS.md` 或用户
既有 tracked 修改；未进行 Git add、commit 或 push。
