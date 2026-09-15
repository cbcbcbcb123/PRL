# Paper 2 Figure 2 FEM-only 数值可信度实现候选：Supervisor 第三轮静态复核 v03

- review_date: 2026-09-04
- reviewer_role: Supervisor
- review_mode: independent_read_only_static_review
- reviewed_surface: 第三版冻结的 15 个实现候选文件
- runner_sha256: `78d0a640ab01321d4c3c1e24ed12d927b94099fbee17fc112477254eefb1616e`
- runtime_smoke_sha256: `b62ae4f5f2a3481cea0022d13ee625dfd5bc1e87614d6a702c1b184a1c307a31`
- execution_performed: false
- python_or_pytest_performed: false
- solver_or_docker_performed: false
- result_directory_created: false
- disposition: `IMPLEMENTATION_REVISION_REQUIRED`
- execution_authorized: false
- scientific_claim_authorized: false

## 1. 二元结论

`IMPLEMENTATION_REVISION_REQUIRED`

第三版已实质关闭第二轮 B1--B7 的主体：P0 与第二周期接口已经统一；链和 SLS 探针已触及
冻结离散算子；N2 判据、force 高次谐波、G6 machine-key 展开和 S1 逐门短路已经进入真实
行为路径；array/N2 typed failure、容器 outcome 一致性、Popen 后清理和 FINAL 跨边界预算也
均有明显加强。

但最新字节仍有下列可由源码直接证明的执行阻断。尤其是 Windows 宿主 FINAL cap 会确定性
失败，S1 的原生--公共步积分守恒没有形成硬门；因此本轮不能生成实现锁，不能授权
PRECHECK、pytest、solver、Docker、结果目录或 Git 提交。

## 2. 已确认未回退的科学与范围边界

1. 活跃实现仍为心内膜离散链 + 心肌主动平面应变 FEM + ECM 黏弹平面应变 FEM；候选未
   重新引入心肌 DCM、流体、三维、identity 或参数扫描。
2. 候选文件集合仍精确为获批 15 文件；`results/paper2_figure2` 不存在。
3. 八个核心文件和 design v03、execution v01/v02 仍由 `spec.py` 的既有 SHA 锁约束。
4. 本轮只进行了 PowerShell/文本级只读检查；没有运行 Python、pytest、FEniCSx、solver
   或 Docker，也没有生成任何数值证据。

## 3. 仍阻断实现接受的问题

### B1. Windows 宿主 FINAL 计时器确定性不可用，300 s 跨边界预算仍未形成单调闭环

runner 的 `_monotonic_cap()`（约第 74--111 行）只接受 `signal.setitimer/SIGALRM`；而正式
宿主被固定为 Windows 路径 `E:\\Temp-Projects\\PRL`。`_finalize_host()`（约第
2940--2996 行）在 Windows 宿主再次调用 `_run_capped()`，会在进入
`_finalize_host_transaction()` 前直接抛出 code 73，因而任何正式尝试都无法写
`resource_audit`、summary、inventory、ledger 和 root completion。

新加入的 epoch 桥接避免了直接相减两个 monotonic origin，但 `time.time()` 不是单调时钟；
回拨但尚未变成负 elapsed 时仍可放宽实际总耗时。并且 `remaining <= 0` 与 host cap 超时均
从封账函数外抛出，不能形成合同要求的失败事务。

最小修订要求：提供 Windows 可执行、不会留下后台写线程的宿主 monotonic deadline；FINAL
各段的本地硬 cap 必须连同 wait/inspect 明确组成不超过 300 s 的确定性上界，不能靠跨 VM
wall clock 作为正确性基础。预算耗尽必须返回冻结的 `RESOURCE_LIMIT_FAIL/73`，并按可达
范围完成唯一失败封账；补无 `setitimer`、clock rollback、handoff 超时和 host-final 超时的
行为测试。

### B2. FINAL 的 owner 和 PASS 时点仍早于宿主最终门

容器在 runner 约第 2822--2835 行已经：

- `machine.accept("FINAL")`；
- 写 `FINAL=PASS` event；
- 把正式 `PASS_LABEL` 写入 `container_outcome.json`；
- 写 `08_final/stage_complete.json`。

这些动作均发生在宿主 postlock、Docker/resource 校验、宿主 NPZ 重读、summary、inventory、
ledger 和 root completion 之前。若上述任一宿主门失败，目录会同时存在“FINAL PASS / 08_final
complete”和根级 FAIL，违反 v02 的宿主唯一 FINAL owner 与互斥 PASS/late-FAIL 语义。

最小修订要求：容器结果只能标为 provisional/container-NPZ-complete，不得携带正式候选标签
或 FINAL PASS；`08_final` 的最终状态、FINAL gate/event 和候选标签只能由宿主在全部宿主门
通过后产生。注入 postlock、resource、host NPZ 与 ledger 自检失败，证明不会遗留正式 PASS
标志。

### B3. 失败路径没有保存完整 gate/postlock 证据

`_finalize_host_transaction()` 只在 `failure is None` 时执行 postlock；因此任何 G0--S1、容器
或 watchdog FAIL 都不记录合同要求的运行后源/Git 锁。另一方面，容器异常出口调用
`_write_container_outcome()` 时不携带 `machine.summary()`；宿主在 early/late FAIL 时通常写出
空的 `gate_summary.gates`，而不是已通过门、首失败门和后续 `NOT_REACHED` 的完整 DAG。

最小修订要求：所有已创建 r01 根的路径都应 best-effort 执行并记录只读 postlock，不覆盖更早
的因果 stop code；容器失败必须保存当时 GateMachine 的完整摘要，或由宿主从受哈希保护的
事件/门工件确定性重建。测试至少覆盖 G0、G5、S1-G4a、NPZ late FAIL 和 watchdog FAIL。

### B4. 第二周期源接口仍未按精确 shape 和冻结 stop code fail closed

`observables.py` 约第 424--429 行对两个 traction 源直接 `reshape`，未先验证合同冻结的原始
shape `(2*n_interface_nodes, 2N+1)`；两个 mean-endocardial 源也只在 `vstack` 后检查，错误的
二维输入可能被接受；`free_shortening_two_cycles` 完全未检查。时间/节点/source shape 以及
production ledger shape 使用普通 `ValueError`，runner 最终多落到 code 99，而 v02 明确要求
源时间/shape drift 为 code 10、缺接口为 12、ledger 失败为 50、FINAL array contract 为 70。

此外 `_validate_container_outcome()` 的 `int(outcome["stop_code"])` 会接受 `73.5`、`"73"`
等非整数 JSON 类型；在标签和进程退出码恰好为 73 时可错误通过。

最小修订要求：逐个原始字段先检查精确 ndim/shape/finite，再作 reshape/stack；使用明确 typed
failure 完成上述 stop-code 映射；outcome 的 stop code 必须是 JSON integer 且排除 bool，不能
做有损 `int()` 强转。补转置 traction、二维 mean、缺/错 free-shortening、time-grid、ledger
shape、float/string/bool stop code 的故障注入测试。

### B5. S1-G5 缺少原生--公共步积分守恒硬门

development G5 在 runner 约第 1953 行对八个 `step_overlap_conservation` channel 逐项建门；
S1-G5（截至约第 2589 行）只检查谐波、force conservation、终局牵引场和热点，没有对 S1
四端点的主动功、腔面功、支撑功、物质能增量、drag/SLS 耗散、平衡缺陷功和 ledger residual
执行原生--公共周期和 `<=1e-10` 门。最终 NPZ 因而可携带错误的 S1 common step arrays 而仍
通过全部 S1 子门。

最小修订要求：在 `accept_s1_gate("S1-G5")` 前，按 development 同一算法对四个 S1 端点、
八个 channel 独立建 record；测试必须篡改一个 S1 common channel 并证明 S1-G5 fail closed。

### B6. PRECHECK 违反冻结的 S2-only manufactured smoke，重复执行完整 S3/S4 G0

`test_manufactured_v01.py` 第 25--26 行参数化 S2/S3/S4，并对每层调用
`run_g0_for_system()`；这会在 240 s PRECHECK 内先执行三层完整谱/零 RHS/N1/N2，随后正式 G0
再次执行同一工作。execution v01 第 771 行明确冻结该测试只做 S2 最小单元 smoke，完整
S2/S3/S4 N1/N2 由 G0 执行。当前测试扩大了计算量并可能在进入 G0 前耗尽 PRECHECK cap。

最小修订要求：运行型 manufactured smoke 限于 S2；S3/S4 只做不触发求解的静态常数/路由
断言，完整三层行为仍由 G0 留证。

### B7. pre-holdout digest 未绑定实际容器身份和全部权威开发工件

runner 约第 2200--2239 行的 digest 绑定 expected image/provenance、case matrix、八个根级
audit 和 formal arrays，但没有绑定宿主已写的 `container_start.json` 及其中实际 container
ID；设计 v03 明确要求 digest 锁定容器 ID。若实际启动身份记录在 S1 前变化，当前两次 digest
复核不会发现。若 `03_g2/04_g3` gate audit 等阶段工件被视为权威开发输出，它们也未包含在
`development_artifact_sha256` 中。

最小修订要求：digest 必须读取、验证并哈希实际 `container_start.json`，绑定 name、ID、
expected image ID；给出唯一权威 development-artifact exact set 并全部纳入 digest，或明确把
重复 sidecar 降为非权威且由被绑定的权威工件可完全重建。补 S1 前篡改 container ID/任一权威
开发工件的故障注入测试。

### B8. N2 complement Ritz residual 的归一化不是合同冻结的 Frobenius 范数

`manufactured.py` 约第 658 行对 rank-two complement 调用 `_eigenpairs(...,
operator_norm=3.0*lambda_max)`；v02 冻结的是每个 Ritz 对以实际
`norm(Ahat)_F*norm(v)` 归一化。`3*lambda_max` 只是另一个界，不是 complement operator 的
Frobenius 范数，可能改变 `1e-8` 门的裁决。

最小修订要求：在不物化 `basis @ basis.T` 稠密方阵的前提下，用 sparse Frobenius、
`trace(U.T@A@U)` 和 rank-two 项解析计算实际 complement Frobenius norm；补与小型显式矩阵
结果逐值一致的单元测试。

### B9. Popen 后清理仍可能先停止未验证身份的同名容器

`_stop_wait_inspect()` 先按名称执行 `docker stop`，随后才 inspect/核对 `expected_id`；而
`_await_container_id()` 失败时调用者会以 `expected_id=None` 进入该函数。名称复用或并发竞争
时，这不满足“只停止本次精确容器”，并可能影响不属于本事务的同名容器。

最小修订要求：Popen 后必须先取得与本次启动原子绑定的 container ID；任何 stop 前先只读
核对该 ID/name/image，身份未知或不一致时禁止按名称停止并以 code 72/73 封账。补 foreign-ID
和 unavailable-ID 两个行为测试。

## 4. 与上述静态阻断分开的运行前检查

以下仍只是后续 ST0/PRECHECK；本轮未执行，也不得写成 PASS：

1. S2/S3/S4 eigsh、Ritz residual、S4 LinearOperator 峰值内存与实际收敛；
2. 各 endpoint、PRECHECK、G0、post/S1、container FINAL 和 Windows host FINAL 的真实耗时；
3. 冻结 Docker inspect/none-network/cgroup/`ru_maxrss`/单 worker 证据；
4. 最终 NPZ 实际压缩大小、216 commitments、宿主重读和完整 root transaction；
5. pytest 在固定镜像内的真实通过情况。

## 5. 下一步授权边界

只授权 Executor 在同一 15 文件候选范围内修订 B1--B9 并更新相应测试；不得运行 Python、
pytest、solver 或 Docker，不得创建 `results/paper2_figure2`，不得修改八个锁定核心文件、
design v03、execution v01/v02、既有 Supervisor review 或用户原有 7 个 tracked 脏文件；不得
生成实现锁，不得执行 Git add/commit/push。修订后返回 Supervisor 做第四轮独立静态复核。
