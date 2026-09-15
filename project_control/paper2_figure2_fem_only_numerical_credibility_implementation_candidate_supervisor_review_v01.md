---
review_id: REVIEW-PAPER2-FIGURE2-FEM-ONLY-IMPLEMENTATION-CANDIDATE-V01-01
status: IMPLEMENTATION_REVISION_REQUIRED
reviewed_at: 2026-09-04
reviewer: independent_supervisor
baseline_commit: 8f240cf38cb4db38f02b776d320562058439770f
baseline_upstream_ahead_behind: 0/0
reviewed_scope: exact_15_uncommitted_candidate_files
test_execution_authorized: none
solver_execution_authorized: none
docker_execution_authorized: none
formal_r01_authorized: none
gpu_authorized: none
next_gate: executor_candidate_v02_then_independent_supervisor_static_review
---

# Paper 2 Figure 2 FEM-only 实现候选 Supervisor 静态审阅 v01

## 1. 二元裁决

裁决为 **IMPLEMENTATION_REVISION_REQUIRED**。

候选实现保持了已接受的科学架构：离散心内膜链、主动心肌平面应变 FEM、黏弹 ECM
平面应变 FEM；未引入流体、三维、整心房、心肌 DCM 或 `paper2_m2` 生产依赖。15 个
授权文件全部存在，八个 `src/paper2_hybrid` 核心文件未被本候选修改，且尚未创建
`results/paper2_figure2/`。

但静态源码与测试设计审阅发现八组会造成假通过、错误拒绝、资源越界或失败事务不能按
合同归类的阻塞。因此当前不授权 Python、pytest、solver、Docker、结果目录、实现锁、
Git 暂存、提交或推送。

## 2. 已通过项

| 检查项 | 结果 |
|---|---|
| 文件边界 | 7 个验证模块、1 个 runner、7 个测试，精确 15 个候选文件 |
| 活跃物理身份 | 无心肌 DCM/identity 路线导入；心内膜链＋心肌 FEM＋ECM FEM 保持不变 |
| 核心只读 | 候选未改动八个 `src/paper2_hybrid` 锁定文件 |
| 端点与 DAG | 36 个 formal、4 个 S1；G0–G7、digest、S1、FINAL 顺序已编码 |
| 周期提取 | 生产量使用第二周期，G7 保留两周期对照 |
| 公共映射 | 128 空间段、256 中心化相位段和 step-overlap 三条路径已实现 |
| 证据写入 | 严格 JSON、create-only、NPZ schema 与 formal commitments 已建立 |
| 执行边界 | 未运行测试/求解/Docker，未生成正式数值证据 |

## 3. 必须关闭的实现阻塞

### B1. 能量收敛量被压成单个范数，可能掩盖波形误差

`_qoi_catalog()` 把每个 `energy.*` 第二周期节点波形立即变成一个时间 L2 标量。合同和
`MACHINE_REGISTRY` 冻结的是 `native_cycle_waveform`，N4/N5/G4a 必须比较能量波形本身，
不能只比较两个波形各自的范数；两个不同波形可有相同范数并被当前实现判为零误差。

修订必须保留每个能量分量的完整第二周期半开节点波形，并给嵌套 T64/T128/T256 明确、
确定且不丢高次成分的比较路径；N5 同步比较同一 T128 节点波形，G4a 的四角输入必须指向
同一冻结的 native-waveform reduction。测试至少加入“同范数不同波形不得通过”的反例。

### B2. machine gate membership 未落实，ledger 被错误加入收敛门

`MACHINE_REGISTRY` 只保存单位/reduction/floor，未保存合同表中的适用门与参考；runner
随后对 `_qoi_catalog()` 的所有共享 key 批量执行 N4、N5 和 G4a。结果是
`ledger.equilibrium_defect` 与 `ledger.residual` 被错误加入 G2/G3/G4a，而合同明确规定
它们只进入 G6。该实现既可能错误拒绝，也无法证明没有漏掉应进入某门的量。

修订必须把每个 machine key 的适用门和参考方向编码为机器可检查的注册表或等价的显式
集合；N4、N5、G4a、G5、G4b、G6、G7 与 S1 都只能从该注册表选量。测试须逐门断言 key
集合，尤其断言 ledger 只在 G6/S1-G6，牵引场只在 G5/G4b/S1 对应门。

### B3. phase 路径不完整且低幅前提量纲错误

当前只有 G2 的 S3/T128→T256 shortening phase；开发集 G4a 与 S1-G4a 没有 phase
硬门。LN/LS 又把牵引输入幅值与 shortening strain floor 直接比较，量纲不一致。
`phase_comparison()` 在低幅时返回伪数值 `0.0`，也不符合“未定义而非强置零”。

修订必须分别传入输入幅值及其自身 floor、输出幅值及 parent-amplitude floor；对 A2、LN、
LS、C0、CQ 和 S1 使用合同冻结的参考，并以 wrapped `atan2` 完成 G2、G4a、S1-G4a
记录。低幅时必须显式保存 `PHASE_UNDEFINED_LOW_AMPLITUDE` 和未定义值语义，且该项状态为
`NOT_APPLICABLE`，不得伪装成数值零。测试需覆盖跨 `-pi/pi`、LN/LS 量纲前提、低幅及
G4a/S1 gate membership。

### B4. mixed difference 在低于 floor 时仍使用相对门

`mixed_difference()` 无条件构造 `numerator/denominator` 和相对阈值；G4a、G4b、S1 全部
直接使用 `normalized`。合同要求参考低于 floor 时不计算相对交互比，只允许绝对混合差
`<= F_Q`（场使用对应维度化绝对 floor）。当前公式会变成另一个、更小且未授权的门。

修订必须返回明确 applicability、绝对/相对两种互斥裁决值和阈值；所有调用点，包括
S1 `chi_D`，统一消费有效值而不是固定读取 `normalized`。测试须同时覆盖相对适用、参考
低于 floor 的绝对 PASS/FAIL，以及四角符号顺序。

### B5. G0 的谱与制造探针存在资源越界和非诊断性计算

S4 `matrix_inertia_audit()` 计算 `basis @ basis.T` 后再转 CSR。按冻结 S4 规模，状态维数约
41729，该临时稠密矩阵约 13.9 GB，尚未计 CSR 和其他数组，必然越过 8 GiB 硬门。
必须改为稀疏矩阵加 rank-2 `LinearOperator` 或等价 matvec，禁止物化 `n x n` 外积，并以
测试/静态断言锁住这一点。

此外 `_sls_manufactured()` 的 DC 误差是 `epsilon-epsilon`，谐波 residual 又由同一解析式
回代自身；`_chain_affine_error()` 只对手写线性数组做差分，未触及实际链算子。它们即使
生产实现损坏也会通过。修订必须让 SLS DC/CN 谐波和链 affine probe 比较实际离散
算子/更新结果与冻结解析值，同时保持 v02 的常数、seed、N 和阈值不变。

### B6. 冻结的单项资源 cap 与容器取证没有落实

`RESOURCE_CAP_SECONDS` 只在 spec/tests 中求和，runner 未导入或执行。当前只有 3600 秒
总 watchdog；PRECHECK 超时还会落入通用异常。合同要求每个 endpoint、G0 和后处理组各自
使用 monotonic 硬 cap，未用时间不得转移。

修订还必须补齐：

1. PRECHECK、G0、S2/S3/S4-T128/S4-T256、公共后处理和 FINAL 的冻结 cap；
2. 超 cap 一律 `RESOURCE_LIMIT_FAIL`，并保留已到达事务证据；
3. timeout 后 `docker wait` 与 `docker inspect`，确认停止且不删除容器；
4. 校验 `MemorySwap`、`PidsLimit`、`ReadonlyRootfs`、`CapDrop`、`SecurityOpt`、running、
   name/id、exit/OOM，不只校验 CPU/memory/network；
5. 同时记录 Linux `ru_maxrss` 与 cgroup peak，并实现合同冻结的 cgroup v2→v1 fallback；
6. TMPDIR 使用合同冻结的 `/root/.cache/tmp`，不得静默改名。

### B7. 失败代码、接口缺失与实现锁生命周期没有 fail closed

`NONFINITE_OUTPUT_FAIL`、`RETIRED_ROUTE_REINTRODUCED_FAIL`、
`MISSING_VALIDATION_INTERFACE_FAIL` 与 `POST_HOC_GATE_CHANGE_FAIL` 当前均不可达；非有限值、
缺字段或 pre/post drift 多数落为 code 10 或 99。`_solver_metrics()` 甚至在 backward-error
字段缺失时回退到 `0.0`，会把缺接口伪装成完美结果。

修订必须显式审计 `_loads_for_endpoint`、`discrete_ledger` 的导入路径、签名和必需字段；
缺失即 code 12，禁止数值默认值。所有正式量做统一有限性审计并映射 code 74；退休路线
回归映射 code 11；holdout 后协议/门/阈值漂移映射 code 75。

实现锁还将在验收 commit 之后生成，因而是精确的本地未跟踪机器锁。当前 scoped Git
status 把该文件本身列入检查，会令合法锁产生 `??` 并阻止正式启动。修订必须在继续独立
哈希/校验该锁的同时，只从 Git cleanliness 中排除这一个预留机器锁；不得依赖修改
`.gitignore`、`.git/info/exclude` 或全局忽略规则，也不得放宽其他 15 文件和合同的清洁门。

### B8. 最小测试没有覆盖上述合同风险与失败事务

当前测试主要覆盖常量、正向算例和 token 存在性，未能阻止 B1–B7。修订必须在原七个
测试文件内增加至少以下回归：

- energy waveform 保真、逐门 machine-key 集合、phase G4a/S1 与低幅未定义；
- mixed below-floor 绝对门，及 `chi_D` 的适用/不适用路径；
- S4 rank-2 complement 不物化稠密方阵，N1 探针能被故障注入击穿；
- 每类单项 cap、PRECHECK timeout、cgroup v1 fallback 和完整 inspect 拒绝条件；
- NaN/Inf→74、缺接口→12、退休依赖→11、post-hoc drift→75；
- 所有冻结病例的 load 周期平移/方向，以及 first-cycle sidecar、second-cycle energy/step
  shape 与闭合；
- malformed/missing container outcome 和 timeout 后的根事务仍可形成非覆盖式 FAIL 封账。

静态 source-token 断言不能替代行为测试；测试本轮仍只允许编写，不允许执行。

## 4. 候选文件指纹

| 文件 | bytes | lines | SHA-256 |
|---|---:|---:|---|
| `src/paper2_figure2/__init__.py` | 521 | 28 | `b960435535758a5b602d80cf5ea125f4d22f367dfd61cdc3897ec5354b760412` |
| `src/paper2_figure2/spec.py` | 15516 | 428 | `085385158babb248c0cad8bddd2feda7b4b047ad3392af6be4fb009c150fffae` |
| `src/paper2_figure2/manufactured.py` | 26809 | 653 | `ddc10294395b0f3f38d4648031f9d399c6cbc7a61d452758f2822e3de61db917` |
| `src/paper2_figure2/projection.py` | 10466 | 259 | `8d4f60f6a28bfa394130a024139942bffbed8c88fb4f91c2534a15e8f17d8b7f` |
| `src/paper2_figure2/observables.py` | 26372 | 645 | `c8cd456b66c4244bea9c4b3075876e77385ced3c57aa71ecf8b36e78f9872f73` |
| `src/paper2_figure2/adjudication.py` | 24298 | 705 | `ff96b618320dada06a92f13de4d9ea05b314593c61a05736ef72d4f8ead19e13` |
| `src/paper2_figure2/evidence.py` | 17708 | 468 | `bd9bdcaeff627a9f32097d9e68b7204f2c0cbe6c2e5d6f950a22a6176e3ddf02` |
| `scripts/run_paper2_figure2_fem_only_numerical_credibility_v01.py` | 97589 | 1979 | `673364b238a7ebbcaf2b74158b0afe96c289a86051dfccc2dfaa53f667355089` |
| `tests/paper2_figure2/test_spec_v01.py` | 1575 | 50 | `13da855e5436f7a68b1fcc56ef7f81c3db1e87d4d0960213f1c984e4b4beaa29` |
| `tests/paper2_figure2/test_source_lock_v01.py` | 2234 | 67 | `7fff47b45f17f086189991766d8d59f22f6b27116aa20fab2c30806511a33b6d` |
| `tests/paper2_figure2/test_projection_v01.py` | 2199 | 61 | `0bfc5ceaa0814192553e5959c8b985f834fc801709368fbe150e3d5720abc4ce` |
| `tests/paper2_figure2/test_manufactured_v01.py` | 1386 | 30 | `c91a5be9b54c109d45df7acb93edbb35a5284dd95a6e6d5ddb042517b417e21f` |
| `tests/paper2_figure2/test_adjudication_v01.py` | 3082 | 78 | `f5870b2abb24119e2af3ad71e5577132b4875694f9894e23b335bf79abc8ff73` |
| `tests/paper2_figure2/test_evidence_v01.py` | 4230 | 94 | `14be2b15c2ab709e8f9cdaffffb5e07fa062c5f219abcf4619aae414a0599eb0` |
| `tests/paper2_figure2/test_runtime_smoke_v01.py` | 2623 | 57 | `2ac1ca500fe2db7d041e4e49df9751d242485b0f4cb063b129f7097599f86bdd` |

## 5. 修订边界与下一门

Executor 只允许修改上述同一组 15 个候选文件以关闭 B1–B8，不得增加第 16 个实现/测试
文件，不得修改 v03 设计合同、v01/v02 执行合同、八个核心文件、CURRENT_STATUS 或既有
结果。若发现必须修改核心方程、病例、阈值、DAG、NPZ schema 或合同语义，立即停止并
返回 Supervisor Gate。

修订完成后报告逐文件 bytes/lines/SHA-256、B1–B8 对照和未执行声明，并停在
`executor_candidate_v02_then_independent_supervisor_static_review`。只有后续版本化 Supervisor
接受决定才可授权最小测试；正式 r01 仍不在该授权内。
