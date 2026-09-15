---
decision_id: DEC-PAPER2-FIGURE2-FEM-ONLY-NUMERICAL-CREDIBILITY-PRECHECK-AND-STAGING-V01
status: draft_for_independent_supervisor_review
decider_role: project_controller_under_human_authority
drafted_at: 2026-09-04
accepted_implementation_review: project_control/paper2_figure2_fem_only_numerical_credibility_implementation_candidate_supervisor_review_v07_2.md
accepted_implementation_review_sha256: 1681d42ec0b4e316f0fbca6bcd737afd58aae19c0442660a51d0012f0dd269ef
implementation_disposition: IMPLEMENTATION_ACCEPTED_FOR_PRECHECK_DECISION
current_authorization: decision_and_exact_staging_draft_only
precheck_authorized: false
python_or_pytest_authorized: false
solver_or_docker_authorized: false
formal_result_directory_authorized: false
implementation_lock_authorized: false
git_write_authorized: false
next_gate: independent_supervisor_review_of_this_decision
---

# Paper 2 Figure 2 FEM-only 数值可信度：PRECHECK 决定与精确 staging v01

## 1. 当前决定

Supervisor v07.2 已前瞻校正 v07/v07.1 元数据冲突，并在静态源码层接受同一 15 文件实现
候选，可进入 PRECHECK 授权决策门；这不等于
任何测试、运行时、FEniCSx、Docker、资源门或数值门已经通过。

本文件只起草后续顺序、命令向量、临时路径、硬时间上限、预期返回码、原始输出位置、停止
条件和精确 staging allowlist。当前仍不授权：

- 运行 Python、pytest、FEniCSx、solver、Docker 或 GPU；
- 创建 `results/paper2_figure2` 或正式 r01；
- 创建 implementation lock；
- 执行 `git add`、commit、push 或改写已有提交；
- 更新 Figure 2 或形成任何科学 PASS/论文结论。

## 2. 权威锚点与执行前顺序

当前只读观察到的 Git 基线为：

- branch: `codex/simucell3d-hybrid-feasibility`
- HEAD: `8f240cf38cb4db38f02b776d320562058439770f`
- upstream: `origin/codex/simucell3d-hybrid-feasibility`
- ahead/behind: `0/0`

权威文件为：

| 文件 | SHA-256 | Git 状态 |
|---|---|---|
| `project_control/paper2_figure2_fem_only_numerical_credibility_contract_v03.md` | `796de6a6cfa6167e30cae592128379206709ace720d4fcbe3ae80366fb504249` | 已在基线提交中 |
| `project_control/paper2_figure2_fem_only_numerical_credibility_v03_supervisor_acceptance_and_execution_contract_decision_v01.md` | `e854bcdddb0037d796b31ef1b4d54c5c20a5509a913bbe3fdb0b2c094014e4b5` | 已在基线提交中 |
| `project_control/paper2_figure2_fem_only_numerical_credibility_execution_contract_v03.md` | `484090034d049d5c48ad6e92ea809fc569ae01cdce26c9c693baebb6143ad38a` | 待精确 staging |
| `project_control/paper2_figure2_fem_only_numerical_credibility_execution_contract_v03_supervisor_review_v02.md` | `36949b75b4d3fb93c05219bc0ada3e7e58c31a04f8bc2691f032ae88c26af57e` | 待精确 staging |
| `project_control/paper2_figure2_fem_only_numerical_credibility_implementation_candidate_supervisor_review_v07.md` | `632bea4fe3e534d5b59084606bc98b59569955d2cbbb2931d85ef7d6f2bda8ed` | 待精确 staging；历史静态接受记录 |
| `project_control/paper2_figure2_fem_only_numerical_credibility_implementation_candidate_supervisor_review_v07_1.md` | `9042af11879f0bc1dec6d20d29856680f1f2e728749ef1ff701b3ce7e5165671` | 待精确 staging；历史静态接受记录，含已撤销的 v07 不存在元数据 |
| `project_control/paper2_figure2_fem_only_numerical_credibility_implementation_candidate_supervisor_review_v07_2.md` | `1681d42ec0b4e316f0fbca6bcd737afd58aae19c0442660a51d0012f0dd269ef` | 待精确 staging；当前唯一前瞻授权来源 |

后续必须依次经过以下门，任何一步都不能由本草案自动放行下一步：

1. 独立 Supervisor 只读审阅并接受本决定；
2. 人类明确授权精确 staging、commit 和同步；
3. 只把第 7 节 allowlist 纳入一个实现包提交，重新验证 HEAD/upstream 与 28 项 staged set；
4. 以该提交的实际 commit SHA 另行 create-only 生成 implementation lock；该锁不进入实现包提交；
5. 独立复核 implementation lock 后，人类再明确授权 A、B、C 三阶段 PRECHECK；
6. A、B、C 全部通过后，只进入 PRECHECK 证据审阅门，不自动执行 G0 或正式 r01。

在 implementation lock 完成并获复核前，A、B、C 均不得执行。

## 3. 唯一项目内临时根与共同约束

三阶段共用且只允许使用：

```text
E:\Temp-Projects\PRL\tmp\paper2_figure2_precheck_v01_20260904
```

共同规则：

1. 首次执行前该精确目录必须不存在；若已存在，立即
   `OUTPUT_PATH_EXISTS_FAIL/71`，不得清空、删除、覆盖、续接或改名重试；
2. 只允许以 create-only 方式创建该根及 `st0_windows`、`docker_readonly`、
   `linux_container` 三个子目录；每个原始输出文件也必须 create-only；
3. `results/paper2_figure2`、正式 r01 和 implementation lock 在 A、B、C 中均为只读检查对象，
   不得创建或修改；
4. 不执行任何删除 API 或删除命令，不使用 pytest cache，不生成 `.pyc`，不做自动清理；临时根和
   stopped PRECHECK 容器保留给审阅；
5. 禁止通配式写入、重试、覆盖日志、重用 basetemp、`docker rm`、`--rm`、prune、pull、build、
   push、socket 挂载和 GPU 参数；
6. 每阶段由宿主外层 monotonic watchdog 执行硬上限。超时只终止该阶段拥有的精确进程树；若为
   C 阶段容器，则仅在完整 cidfile ID、name 和 image 三重核验后停止该容器，永不按名称猜测；
7. 每阶段保存命令向量、合并的原始 stdout/stderr、native exit code、monotonic 起止值和超时
   状态。任何记录失败都使该阶段失败；
8. 阶段顺序固定为 `A -> B -> C`。A 或 B 失败时，不创建下一阶段目录；C 失败时不进入 G0。

## 4. A：Windows 宿主 ST0

### 4.1 范围

A 只验证 Windows 特有且不触及正式结果目录的安全边界：无 `setitimer`、Job Object、stdin
release gate、assignment failure、3/3/4 s worker recovery、5 s bounded readback、真实慢
readback 回收、真实 worker 边界和 `python -I -B` 隔离导入。不得运行完整 PRECHECK 或任何
FEM 端点。

### 4.2 冻结命令向量

工作目录固定为 `E:\Temp-Projects\PRL`，环境固定加入：

```text
PYTHONDONTWRITEBYTECODE=1
PYTHONPATH=E:\Temp-Projects\PRL\src
```

pytest argv 固定为：

```text
python -B -m pytest -q -p no:cacheprovider
  --basetemp=E:\Temp-Projects\PRL\tmp\paper2_figure2_precheck_v01_20260904\st0_windows\pytest_tmp
  --junitxml=E:\Temp-Projects\PRL\tmp\paper2_figure2_precheck_v01_20260904\st0_windows\pytest_junit.xml
  tests/paper2_figure2/test_runtime_smoke_v01.py::test_host_finalization_is_windows_safe_without_setitimer
  tests/paper2_figure2/test_runtime_smoke_v01.py::test_assignment_failure_never_releases_worker_to_touch_the_run_root
  tests/paper2_figure2/test_runtime_smoke_v01.py::test_host_final_worker_normal_wait_preserves_the_full_parent_tail
  tests/paper2_figure2/test_runtime_smoke_v01.py::test_bounded_readback_timeout_revokes_access_and_preserves_package_bytes
  tests/paper2_figure2/test_runtime_smoke_v01.py::test_readback_worker_imports_frozen_source_without_pytest_path_injection
  tests/paper2_figure2/test_runtime_smoke_v01.py::test_real_slow_readback_is_reaped_inside_five_seconds_without_package_writes
  tests/paper2_figure2/test_runtime_smoke_v01.py::test_host_final_worker_timeout_uses_3_3_4_recovery_and_returns_nonzero
  tests/paper2_figure2/test_runtime_smoke_v01.py::test_real_worker_boundary_is_terminated_within_the_frozen_parent_tail
  tests/paper2_figure2/test_runtime_smoke_v01.py::test_unreaped_worker_revokes_job_write_access_before_parent_returns
```

### 4.3 时间、输出与裁决

- 全阶段 hard cap：`90.0 s`，不延长、不重试；
- 原始合并输出：`st0_windows/pytest_stdout_stderr.txt`；
- JUnit：`st0_windows/pytest_junit.xml`；
- 原始返回码：`st0_windows/native_exit_code.txt`；
- 调用记录：`st0_windows/invocation.json`；
- 预期：native exit code `0`，上述 9 个 node 全部 PASS，`failed=0`、`error=0`、`skipped=0`，
  且正式结果目录和实现锁字节不变；
- 任何非零、skip、超时、残留 worker、marker 被错误创建、包字节改变、隔离导入未解析到本项目
  `src/paper2_figure2/evidence.py`，均为 A FAIL，立即停止；
- 超时映射 `RESOURCE_LIMIT_FAIL/73`；源码/导入漂移映射
  `SOURCE_OR_PROTOCOL_DRIFT_FAIL/10`；不得进入 B。

pytest 的 `--basetemp` 精确路径在启动前必须不存在；该 precondition 保证 pytest 不会删除或
覆盖既有数据。执行后保留整个目录，不运行清理。

## 5. B：固定镜像与 Docker 只读 preflight

### 5.1 冻结只读查询

B 不启动、不停止、不删除容器，不拉取镜像。工作目录仍为项目根。按顺序执行：

```text
docker version --format {{json .Server.Version}}
docker image inspect dolfinx/dolfinx:v0.11.0 --format {{.Id}}
docker ps -a --filter name=^/paper2-figure2-nc-v03-r01$ --format {{.ID}}
docker ps -a --filter name=^/paper2-figure2-precheck-v01-20260904$ --format {{.ID}}
```

随后以 PowerShell `Test-Path -LiteralPath` 只读检查下列精确路径：

```text
E:\Temp-Projects\PRL\results\paper2_figure2
E:\Temp-Projects\PRL\results\paper2_figure2\fem_only_numerical_credibility_v03_20260904_r01
E:\Temp-Projects\PRL\project_control\paper2_figure2_fem_only_numerical_credibility_implementation_lock_v01.json
E:\Temp-Projects\PRL\tmp\paper2_figure2_precheck_v01_20260904\linux_container
```

其中 implementation lock 在进入 A 前应已存在且已独立复核，因此 B 对它的预期是存在、字节
SHA 与获接受记录一致；两个正式结果路径与尚未创建的 `linux_container` 路径预期不存在。

### 5.2 时间、输出与裁决

- 全阶段 hard cap：`60.0 s`；每个 Docker CLI 调用单独 hard cap `15.0 s`；
- 原始输出依次保存为 `docker_readonly/01_docker_version.txt`、
  `02_image_inspect.txt`、`03_formal_name_query.txt`、`04_precheck_name_query.txt`、
  `05_path_preflight.txt`；
- 四项 Docker native exit code 分别保存为 create-only 的
  `docker_readonly/01_exit_code.txt` 至 `04_exit_code.txt`；路径检查结果单独写入
  `05_path_preflight.txt`，不采用 append 或覆盖；
- 预期镜像 ID 必须 byte-exact 等于
  `sha256:2ae4bfbc0d9077268880faf04c72750528bee986c94ab223a2c159969bd56fa8`；
- 两次容器查询输出必须为空；Docker Server 版本必须可读；不允许自动 pull；
- 任何调用非零、超时、镜像缺失/漂移、同名容器存在、正式结果路径存在、lock 缺失/漂移或
  `linux_container` 被预占，都 fail-closed；身份冲突映射
  `CONTAINER_ID_MISMATCH_FAIL/72`，资源/服务/超时映射 `RESOURCE_LIMIT_FAIL/73`，路径预占映射
  `OUTPUT_PATH_EXISTS_FAIL/71`；不得进入 C。

## 6. C：固定 Linux 容器 PRECHECK

### 6.1 唯一容器与资源边界

只有 A、B 都 PASS，才 create-only 创建 `linux_container` 子目录并启动唯一 PRECHECK 容器：

```text
docker run
  --name paper2-figure2-precheck-v01-20260904
  --cidfile E:\Temp-Projects\PRL\tmp\paper2_figure2_precheck_v01_20260904\linux_container\container.cid
  --network none
  --cpus 1
  --memory 8g
  --memory-swap 8g
  --pids-limit 256
  --read-only
  --cap-drop ALL
  --security-opt no-new-privileges
  --mount type=bind,src=E:\Temp-Projects\PRL,dst=/workspace,readonly
  --mount type=bind,src=E:\Temp-Projects\PRL\tmp\paper2_figure2_precheck_v01_20260904\linux_container,dst=/precheck_tmp
  --tmpfs /root/.cache:rw,noexec,nosuid,nodev,size=2147483648
  --workdir /workspace
  --env TMPDIR=/root/.cache
  --env XDG_CACHE_HOME=/root/.cache
  --env PYTHONPATH=/workspace/src
  --env PYTHONDONTWRITEBYTECODE=1
  --env OMP_NUM_THREADS=1
  --env OPENBLAS_NUM_THREADS=1
  --env MKL_NUM_THREADS=1
  --env NUMEXPR_NUM_THREADS=1
  dolfinx/dolfinx:v0.11.0
  python3 -B -m pytest -q -p no:cacheprovider
    --basetemp=/precheck_tmp/pytest_tmp
    --junitxml=/precheck_tmp/pytest_junit.xml
    tests/paper2_figure2/test_spec_v01.py
    tests/paper2_figure2/test_source_lock_v01.py
    tests/paper2_figure2/test_projection_v01.py
    tests/paper2_figure2/test_adjudication_v01.py
    tests/paper2_figure2/test_evidence_v01.py
    tests/paper2_hybrid/test_static_architecture.py
    tests/paper2_hybrid/test_projection.py
    tests/paper2_figure2/test_manufactured_v01.py
    tests/paper2_figure2/test_runtime_smoke_v01.py
    tests/paper2_hybrid/test_fenicsx_runtime.py
```

唯一可持久写挂载是 PRECHECK 临时子目录；项目仓库为 read-only，Docker socket 不挂载，GPU
不可见，不使用 `--rm`。容器正常或失败退出后均保留为 stopped，等待审阅。

### 6.2 240 s 分配与身份安全

- C 总 hard cap：`240.0 s`；正常 pytest/JIT wait 最多 `210.0 s`，固定保留 `30.0 s` 给精确
  ID 核验、必要停止、wait/reap 和末次 inspect；
- `container.cid` 必须恰为 64 位小写十六进制完整 ID；任何 stop 前必须以
  `docker inspect <full-id>` 验证 `Id`、name 和 image；
- timeout 时只允许对已三重验证的 `<full-id>` 执行
  `docker stop --time 10 <full-id>`、`docker wait <full-id>` 和
  `docker inspect <full-id>`；不得按名称 stop，不得 kill/remove/prune；
- cidfile 缺失、错误或身份不可验证时，不执行 stop；阶段以 code 72/73 失败并人工处置；
- 正常退出也以完整 ID 做末次只读 inspect，验证 stopped、exit code 0、image ID、单 CPU、8 GiB、
  memory-swap 8 GiB、pids 256、network none、read-only rootfs、cap-drop ALL 和
  no-new-privileges。

### 6.3 输出与裁决

- Docker run 合并原始输出：`linux_container/pytest_stdout_stderr.txt`；
- JUnit：`linux_container/pytest_junit.xml`；
- cidfile：`linux_container/container.cid`；
- 原始 Docker run 返回码：`linux_container/native_exit_code.txt`；
- 末次 inspect 原始 JSON：`linux_container/docker_inspect_after.json`；
- 调用与 deadline 记录：`linux_container/invocation.json`；
- 预期：Docker run native exit code `0`，JUnit `failed=0`、`error=0`；仅
  `sys.platform != win32` 明确标记的 Windows host-specific 用例允许 skip，其他 skip 均失败；
- 任一非零、超时、收集错误、导入漂移、lock 失败、FEniCSx runtime 失败、资源/身份漂移、
  项目仓库写入或正式结果路径变化，均为 C FAIL；不运行 G0、不创建正式 r01；
- C PASS 只形成 `PRECHECK_PASS_FOR_SUPERVISOR_REVIEW`，不构成数值可信度 PASS 或科学结论。

## 7. 精确 implementation-package staging allowlist

### 7.1 已接受的 15 个实现候选

| # | path | SHA-256 |
|---:|---|---|
| 1 | `src/paper2_figure2/__init__.py` | `b960435535758a5b602d80cf5ea125f4d22f367dfd61cdc3897ec5354b760412` |
| 2 | `src/paper2_figure2/spec.py` | `471ef6561beedf8d70dc3d6aafa8068494091c36c2dd1473fd43bc55a02f8d93` |
| 3 | `src/paper2_figure2/manufactured.py` | `dd8dd6cb408c6fe97f9b4c93bb25b0b0092f76b0eea2ac3f9879e7f7c6fb6a01` |
| 4 | `src/paper2_figure2/projection.py` | `e9f4f46cbb86d864f4a04db12e585507b142a2768f95318fc1ab183de765e2ef` |
| 5 | `src/paper2_figure2/observables.py` | `29216f930b3be9cd5af65e912e9a637e2042960ab83fcc5d6f2115f395a5ea85` |
| 6 | `src/paper2_figure2/evidence.py` | `df4c5a68394e7edba21789772d5560319ec324a0e877bf4da675ad76785cbf56` |
| 7 | `src/paper2_figure2/adjudication.py` | `9de9a95fa3babb8731d375b95718b0d7ca0a85b94c950da6d251d6bf9ae14cb7` |
| 8 | `scripts/run_paper2_figure2_fem_only_numerical_credibility_v01.py` | `93f1f9694e785288172e66ba59df7fbc8cdffa27575a237fc8999a0d04851d31` |
| 9 | `tests/paper2_figure2/test_spec_v01.py` | `37d2e25870f6cf9db9f901e355f90fbe053d6965809fa772d972a9a8c0ea9fd1` |
| 10 | `tests/paper2_figure2/test_source_lock_v01.py` | `4ff9e17b6f2348410f59ed68a3922140c00c319ec14e53f412fa0a6f95353511` |
| 11 | `tests/paper2_figure2/test_projection_v01.py` | `7fe50027b8b1574ff69572de3856511ad7c37afd68a6cd27ad61c160e9cd375d` |
| 12 | `tests/paper2_figure2/test_adjudication_v01.py` | `9a9badd4b5fbc97d51a01f25a09dd37ceffbfc182426bfeb4c246e8742d77cb6` |
| 13 | `tests/paper2_figure2/test_evidence_v01.py` | `5c1760db59cb1cac527b264f5ab09a32227e1fa069f71d4e46f289c2fc8657d5` |
| 14 | `tests/paper2_figure2/test_manufactured_v01.py` | `5945cbf3b9a2686d298115e5a24602c50a4f0e6a09f6f0e751e4a087ad985311` |
| 15 | `tests/paper2_figure2/test_runtime_smoke_v01.py` | `b693e419ff93624b7f1014b6e15cb17aead303db0b6ef922cd11ad5162707311` |

### 7.2 必须随实现包新增的合同与审阅链

| # | path | SHA-256 |
|---:|---|---|
| 16 | `project_control/paper2_figure2_fem_only_numerical_credibility_execution_contract_v03.md` | `484090034d049d5c48ad6e92ea809fc569ae01cdce26c9c693baebb6143ad38a` |
| 17 | `project_control/paper2_figure2_fem_only_numerical_credibility_execution_contract_v03_supervisor_review_v01.md` | `65638d9049d32e02e314fe3c49cb6b8c8ef7e6c1a68548217df2686a7f95f200` |
| 18 | `project_control/paper2_figure2_fem_only_numerical_credibility_execution_contract_v03_supervisor_review_v02.md` | `36949b75b4d3fb93c05219bc0ada3e7e58c31a04f8bc2691f032ae88c26af57e` |
| 19 | `project_control/paper2_figure2_fem_only_numerical_credibility_implementation_candidate_supervisor_review_v01.md` | `315356ad17cbafa8be59e6c4c6fe9bef4b30e195f21c00755bac5ae1f4cc3082` |
| 20 | `project_control/paper2_figure2_fem_only_numerical_credibility_implementation_candidate_supervisor_review_v02.md` | `4f5f3c02e0b0d8e654f360a467c29f903a10be793fc4da058b8d6383782e676e` |
| 21 | `project_control/paper2_figure2_fem_only_numerical_credibility_implementation_candidate_supervisor_review_v03.md` | `2ab96eda0a5e86c99cd96dc865a1234f83667565487000277662eeb463d9d325` |
| 22 | `project_control/paper2_figure2_fem_only_numerical_credibility_implementation_candidate_supervisor_review_v04.md` | `1638e6e6140e1a2131abd828aba0a5789199603dba21dc44c21a894eca5520a1` |
| 23 | `project_control/paper2_figure2_fem_only_numerical_credibility_implementation_candidate_supervisor_review_v05.md` | `cc8fe76af3b38860ed91de67f38c392771c91951d2a1f1abcd5f91cb96e4bd05` |
| 24 | `project_control/paper2_figure2_fem_only_numerical_credibility_implementation_candidate_supervisor_review_v06.md` | `d3c7b18efa0c7604083ff0d0926d3bdea93deffa8bd861d6da256d9a5252bac8` |
| 25 | `project_control/paper2_figure2_fem_only_numerical_credibility_implementation_candidate_supervisor_review_v07.md` | `632bea4fe3e534d5b59084606bc98b59569955d2cbbb2931d85ef7d6f2bda8ed` |
| 26 | `project_control/paper2_figure2_fem_only_numerical_credibility_implementation_candidate_supervisor_review_v07_1.md` | `9042af11879f0bc1dec6d20d29856680f1f2e728749ef1ff701b3ce7e5165671` |
| 27 | `project_control/paper2_figure2_fem_only_numerical_credibility_implementation_candidate_supervisor_review_v07_2.md` | `1681d42ec0b4e316f0fbca6bcd737afd58aae19c0442660a51d0012f0dd269ef` |
| 28 | `project_control/paper2_figure2_fem_only_numerical_credibility_precheck_decision_and_exact_staging_v01.md` | 本文件生成后在包外冻结实际 SHA；不得在文件内自引用 |

v06 内保留一条历史性的旧 v05 SHA 引用，v07.1 内保留一条已撤销的“v07 不存在”断言；旧
review 均不得改写。v07.2 绑定 v05、v06、v07、v07.1 的实际 SHA，并构成当前唯一前瞻授权
来源。设计合同 v03 与其接受决定已存在于基线 HEAD，SHA 见第 2 节，无需产生 staged diff，
但提交前仍须逐字节复核。

### 7.3 明确排除

当前 index 必须保持空，直到另获 Git 写授权。未来 staging 后，index 的 path set 必须与上表
28 项完全相等；禁止 `git add .`、`git add -A`、目录级 add 或通配 add。

以下 7 个既有 tracked 修改必须保持 unstaged、字节不变：

1. `project_control/prl_figure2_spatial_tolerance_validation_contract_v02.md`
2. `scripts/diagnose_efe_node1_sparse_preconditioner_v01.py`
3. `scripts/run_efe_node1_n1_2_periodic_case_v01.py`
4. `scripts/run_efe_node1_n1_2b_r1a_fixed_point_pilot_v01.py`
5. `scripts/run_efe_node1_n1_2b_r3_transactional_cycle_v01.py`
6. `src/hybrid/efe_fast_trilayer.py`
7. `src/hybrid/efe_fast_trilayer_solver.py`

所有不在 28 项 allowlist 中的 untracked 文件和目录均明确排除，包括但不限于
`02_图表/`、`artifacts/`、`docs/theory/`、`figures/`、`planning/`、其他
`project_control/` 文件、`results/`、其他 `scripts/`、`src/hybrid/`、`tests/hybrid/` 和
`tmp/`。未来 A/B/C 产生的全部 PRECHECK 临时证据也不得进入实现包提交。

staging 后必须只读验证：

- `git diff --cached --name-only` 恰为 28 项，无第 7.3 节排除项；
- 28 项的 staged blob SHA 对应冻结文件字节；
- 7 个既有 tracked 修改仍只在 unstaged 区；
- scoped package 之外的 untracked 数量和内容不影响 allowlist，但不得被 staged；
- base HEAD/upstream 在 staging 前仍为第 2 节记录的 `0/0`；若漂移，停止并另行复核；
- commit、push 和 implementation lock 均需后续明确授权，不由本文件自动执行。

## 8. PRECHECK 后停止点与证据边界

若未来 A、B、C 全部获授权且实际 PASS，项目必须停在
`PRECHECK_PASS_FOR_SUPERVISOR_REVIEW`：

1. 只汇报三阶段原始返回码、JUnit、Docker identity/resource evidence 和临时根 hash 清单；
2. 不创建 `results/paper2_figure2`，不执行正式 runner、G0、40 个端点或 Figure 2 更新；
3. 不把 PRECHECK 解释为网格、时间步、容差、物理机制或论文主张的证据；
4. 只有新的独立 Supervisor 审阅和人类明确授权，才能决定是否进入正式 HOST_CREATE/G0。

本草案生成后立即停止，冻结其 bytes/lines/SHA，并交独立 Supervisor 只读审阅。
