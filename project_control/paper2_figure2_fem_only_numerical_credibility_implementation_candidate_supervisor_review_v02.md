# Paper 2 Figure 2 FEM-only 数值可信度实现候选：Supervisor 第二轮静态复核 v02

- review_date: 2026-09-04
- reviewer_role: Supervisor
- review_mode: independent_read_only_static_review
- reviewed_surface: 修订后的 15 个实现候选文件
- execution_performed: false
- python_or_pytest_performed: false
- solver_or_docker_performed: false
- result_directory_created: false
- disposition: `IMPLEMENTATION_REVISION_REQUIRED`
- execution_authorized: false
- scientific_claim_authorized: false

## 1. 二元结论

`IMPLEMENTATION_REVISION_REQUIRED`

修订版已经实质关闭了第一轮中的两个重要问题：能量量现在以原生第二周期波形进入跨网格比较，S4 补空间谱算子也不再显式物化 `basis @ basis.T` 稠密方阵；machine registry、相位适用性、below-floor 绝对门、单项 endpoint cap、Linux `ru_maxrss` 与 cgroup v2→v1 路径亦有明显改善。

但当前候选仍存在可由源码直接证明的必然失败路径，以及若干会让硬门失真或让失败事务不闭合的实现缺口。因此本轮不得生成实现锁、不得授权 PRECHECK、pytest、solver、Docker、结果目录或 Git 提交。

## 2. 本轮确认未回退的边界

1. 活跃候选仍为心内膜离散链 + 心肌主动平面应变 FEM + ECM 黏弹平面应变 FEM；15 个候选文件中未重新引入心肌 DCM、流体、三维、identity 或参数扫描路线。
2. 正式轴仍为 36 个 development 记录 + 4 个 S1 holdout；唯一 P0 正式记录仍为 S2/T64 G0 复用。
3. NPZ 仍冻结为 24 keys、128×256 公共场、128 MiB 上限和 216 条 formal slice commitment。
4. 单 CPU、8 GiB、3600 s、固定镜像与 create-only r01 边界仍保留。

## 3. 仍阻断执行授权的问题

### B1. 当前测试套件与 G0 数据接口存在两个确定性不兼容，候选无法进入正式门

1. `test_runtime_smoke_v01.py` 要求 `compressed.metrics["step_integrals_second_cycle"]`，但 `extract_compressed_endpoint()` 从未生成该 key；冻结 PRECHECK 会在五个动态病例测试中直接触发 `KeyError`，从而测试失败。
2. G0 真零端点的 solver assurance 输出 `dc_backward_error` / `harmonic_backward_error`，而统一 `_solver_metrics()` 只接受 `dc_normwise_backward_error` / `harmonic_normwise_backward_error`。runner 在 S2 P0 复用提取时必然把它映射为 `MISSING_VALIDATION_INTERFACE_FAIL`，因此即使先修复 PRECHECK，也不能完成 G0。

修订必须统一生产接口与测试合同，并增加一个真实的 `solve_true_zero_rhs → extract_compressed_endpoint` 行为测试，证明 P0 可被压缩、复用且不使用数值默认值。

### B2. N1/N2 冻结制造与实际 GateMachine 尚未一致

1. 链 affine probe 仍只把 macro x 应变代入总链能量；它没有使用合同冻结的两分量节点场
   `u_x=1e-4*1.25X`、`u_y=1e-4*(-0.5X+0.25)`，也没有比较离散链算子输出与解析输出的长度加权 L2。
2. SLS probe 仍从单一 macro x 应变生成 `epsilon`；没有使用合同冻结的三分量
   `1e-4*(1,-0.5,0.25)` DC/复谐波制造应变。
3. `matrix_inertia_audit()` 虽计算补空间最小特征值并在内部 `pass` 中使用，但 runner 从不把该判据提交给 GateMachine，且完全忽略 `N2["pass"]`。
4. runner 对平移基/回代残差使用 `1e-8`，而合同冻结阈值是 `1e-10`。

修订必须让制造 probe 使用冻结输入并触及实际离散算子；N2 的每个唯一判据都必须成为可审计的 GateMachine record，阈值不得放宽。

### B3. machine-key gate membership 仍有声明与执行不一致

1. `interface.*.force_on_ecm.*` 在 registry 中是 `single_frequency_eligible=True`，且属于 G5/S1-G5；当前 G5 只审计 shortening、endocardial displacement 和 traction 的 reconstruction/higher-harmonic，force 的谐波残差被计算后丢弃，未形成硬门。
2. G6/S1-G6 声明包含全部 energy、work、dissipation 与 ledger keys，但实际 CheckRecord 只覆盖 ledger、两种 dissipation、`energy.material` 和 `energy.interface`；其余能量分量及 active/lumen/support work 没有按合同形成独立 machine-key 记录。

修订必须让实际 records 与 `gate_quantities()` 精确对应；不能只在 JSON sidecar 中出现数值，也不能依赖总账本掩盖单分量缺失。

### B4. S1 的硬门不是实际的逐门短路

runner 先生成 S1-G4a、S1-G5、S1-G4b、S1-G6、S1-G7 的全部比较、热点和账本记录，最后才依次调用 `machine.accept()`。因此 S1-G4a 失败时，后续门的计算已发生，只是在输出中把它们隐藏为未到达；这不满足“首个硬门失败立即短路”和 early FAIL 只保存真实到达工件的事务语义。

修订必须按 DAG 逐门：生成当前门记录 → 写当前门证据 → `accept` → PASS 后才进入下一门。

### B5. stop-code 与失败事务仍有 fail-open/误分类路径

1. NPZ key/shape/dtype/size 等 array-contract 错误在 `machine.accept("FINAL")` 之前以普通 `ValueError` 抛出，最终被分类为 code 99；当前 FINAL record 本身固定为数值 1，故真实 `ARRAY_CONTRACT_FAIL` code 70 对这些错误不可达。
2. N2 对角、维数、ARPACK 或谱算法异常同样会落入 code 99，而不是合同冻结的 `MATRIX_INERTIA_FAIL` code 21。
3. 容器非零退出时，宿主没有验证 `container_outcome.stop_code == docker/process exit code`，也没有校验 label-code 映射；一个内容为 FAIL 但 `stop_code=0` 的 outcome 甚至可能让宿主返回 0。
4. `_write_container_outcome()` 对 PRECHECK/G0 等 early failure 总会新建 `08_final` 阶段，违反 early FAIL 不创建尚未到达后续阶段工件的规则。

修订应使用明确的 typed failure 边界，把 array/N2/retired/interface/nonfinite/post-hoc 各自映射到冻结 stop code；宿主必须拒绝 outcome/exit 不一致，并用不伪造后续 stage 的位置保存 early-failure outcome。

### B6. 资源与 watchdog 的最终闭环仍不完整

1. 300 s FINAL cap 只包住容器内 NPZ 组装与容器 outcome；合同列入该 cap 的宿主 postlock、宿主 NPZ 复核、resource/gate/summary、inventory、ledger 与 root completion 全部在 cap 外。
2. 容器启动后，只有总 watchdog 的 `TimeoutExpired` 分支会执行 stop → wait → inspect。若 `_await_container_id()`、`container_start.json` 写入或其他 wait 前步骤失败，宿主直接封账，已启动容器可能继续运行并在 root completion 后继续写入。
3. Docker 校验额外要求 `NetworkSettings.Networks == []`，但合同冻结的是 `HostConfig.NetworkMode=none` 与无外部网络；该额外假设既未由合同授权，也未用真实 `--network none` inspect fixture 验证，可能把合法 none-network 容器确定性误判为资源失败。

修订必须让 FINAL 300 s 覆盖容器与宿主的完整最终链；任何 Popen 成功后的异常都必须对精确容器执行非删除式 stop/wait/inspect；Docker fixture 应来自实际冻结启动形态并只实施合同规定的约束。

### B7. 测试没有锁住上述真实故障面

当前测试一方面包含 B1 的必然缺 key，另一方面仍把非冻结的链/SLS probe 当作正确行为。还缺少以下行为测试：N2 补空间判据确实进入 GateMachine、1e-10 平移阈值、force 高次谐波、G6 全 key 展开、array error→70、N2 error→21、outcome/exit 一致性、Popen 后任意异常的 stop/wait/inspect、S1 首失败短路，以及宿主 FINAL cap 覆盖最终封账。

这些应以故障注入证明 fail closed，不能只检查源码中是否出现某个 token。

## 4. 与批准阻断项分开的运行前检查

以下不是本轮新增的静态设计阻断；完成 B1–B7 并再次通过独立静态复核后，才允许在一次受控 PRECHECK/smoke 中验证：

1. S2/S3/S4 实际 eigsh 收敛、Ritz residual 和 S4 LinearOperator 峰值内存；
2. 每类 endpoint 的真实 wall time 是否低于 8/20/60/90 s；
3. PRECHECK 总时长、G0 总时长、后处理/S1 与完整 FINAL 时长；
4. 冻结 Docker 镜像的真实 inspect 结构、none-network 表示、cgroup peak、Linux `ru_maxrss` 和单 worker 证据；
5. 最终 NPZ 实际压缩大小与宿主只读复核。

这些运行检查尚未执行，不能被本静态复核写成 PASS。

## 5. 下一步授权边界

只授权 Executor 在同一 15 文件实现候选范围内修订 B1–B7，并更新对应测试；不得运行 Python/pytest/solver/Docker，不得创建结果目录，不得改 8 个锁定核心文件、v03/v02 合同或用户既有 7 个脏文件，不得生成实现锁或执行 Git add/commit/push。修订完成后返回 Supervisor 做第三轮独立静态复核。
