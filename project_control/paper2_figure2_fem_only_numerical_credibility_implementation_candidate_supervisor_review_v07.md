# Paper 2 Figure 2 FEM-only 数值可信度实现候选：Supervisor 第七轮静态复核 v07

- review_date: 2026-09-04
- reviewer_role: Supervisor
- review_mode: independent_read_only_static_review
- reviewed_surface: v07.1 冻结的 15 个实现候选文件
- design_contract_v03_sha256: `796de6a6cfa6167e30cae592128379206709ace720d4fcbe3ae80366fb504249`
- execution_contract_v03_sha256: `484090034d049d5c48ad6e92ea809fc569ae01cdce26c9c693baebb6143ad38a`
- execution_contract_v03_supervisor_review_v02_sha256: `36949b75b4d3fb93c05219bc0ada3e7e58c31a04f8bc2691f032ae88c26af57e`
- source_review_v06_sha256: `d3c7b18efa0c7604083ff0d0926d3bdea93deffa8bd861d6da256d9a5252bac8`
- execution_performed: false
- python_or_pytest_performed: false
- solver_or_docker_performed: false
- result_directory_created: false
- implementation_lock_created: false
- git_write_performed: false
- disposition: `IMPLEMENTATION_ACCEPTED_FOR_PRECHECK_DECISION`
- execution_authorized: false
- precheck_authorized: false
- scientific_claim_authorized: false
- next_gate: `versioned_precheck_decision_and_exact_implementation_package_commit`

## 1. 二元结论

`IMPLEMENTATION_ACCEPTED_FOR_PRECHECK_DECISION`

v07.1 已在静态源码层关闭 v06 的 B1--B5，并补上独立 readback 子进程从 `scripts/` 启动时
可能无法导入冻结 `src` 包的确定性问题。当前没有遗留的实现接受 blocker。

该结论只表示实现候选可以进入“版本化 PRECHECK 决策与精确实现包提交”阶段。它不表示
pytest、Windows Job Object、Docker、FEniCSx、40 个端点、数值门、资源门或 Figure 2 已经
通过，也不授权对外报告科学结论。

## 2. 接受的冻结候选

| # | 文件 | bytes | lines | SHA-256 |
|---:|---|---:|---:|---|
| 1 | `src/paper2_figure2/__init__.py` | 521 | 28 | `b960435535758a5b602d80cf5ea125f4d22f367dfd61cdc3897ec5354b760412` |
| 2 | `src/paper2_figure2/spec.py` | 21448 | 595 | `471ef6561beedf8d70dc3d6aafa8068494091c36c2dd1473fd43bc55a02f8d93` |
| 3 | `src/paper2_figure2/manufactured.py` | 37440 | 939 | `dd8dd6cb408c6fe97f9b4c93bb25b0b0092f76b0eea2ac3f9879e7f7c6fb6a01` |
| 4 | `src/paper2_figure2/projection.py` | 12699 | 306 | `e9f4f46cbb86d864f4a04db12e585507b142a2768f95318fc1ab183de765e2ef` |
| 5 | `src/paper2_figure2/observables.py` | 34408 | 871 | `29216f930b3be9cd5af65e912e9a637e2042960ab83fcc5d6f2115f395a5ea85` |
| 6 | `src/paper2_figure2/evidence.py` | 21266 | 555 | `df4c5a68394e7edba21789772d5560319ec324a0e877bf4da675ad76785cbf56` |
| 7 | `src/paper2_figure2/adjudication.py` | 29425 | 854 | `9de9a95fa3babb8731d375b95718b0d7ca0a85b94c950da6d251d6bf9ae14cb7` |
| 8 | `scripts/run_paper2_figure2_fem_only_numerical_credibility_v01.py` | 217615 | 5144 | `93f1f9694e785288172e66ba59df7fbc8cdffa27575a237fc8999a0d04851d31` |
| 9 | `tests/paper2_figure2/test_spec_v01.py` | 3779 | 102 | `37d2e25870f6cf9db9f901e355f90fbe053d6965809fa772d972a9a8c0ea9fd1` |
| 10 | `tests/paper2_figure2/test_source_lock_v01.py` | 3038 | 91 | `4ff9e17b6f2348410f59ed68a3922140c00c319ec14e53f412fa0a6f95353511` |
| 11 | `tests/paper2_figure2/test_projection_v01.py` | 3780 | 101 | `7fe50027b8b1574ff69572de3856511ad7c37afd68a6cd27ad61c160e9cd375d` |
| 12 | `tests/paper2_figure2/test_adjudication_v01.py` | 6257 | 171 | `9a9badd4b5fbc97d51a01f25a09dd37ceffbfc182426bfeb4c246e8742d77cb6` |
| 13 | `tests/paper2_figure2/test_evidence_v01.py` | 9644 | 233 | `5c1760db59cb1cac527b264f5ab09a32227e1fa069f71d4e46f289c2fc8657d5` |
| 14 | `tests/paper2_figure2/test_manufactured_v01.py` | 6625 | 164 | `5945cbf3b9a2686d298115e5a24602c50a4f0e6a09f6f0e751e4a087ad985311` |
| 15 | `tests/paper2_figure2/test_runtime_smoke_v01.py` | 91128 | 2518 | `b693e419ff93624b7f1014b6e15cb17aead303db0b6ef922cd11ad5162707311` |

全部 15 个文件行尾空白命中为 0。相对 v06，只有 runner 与 runtime smoke test 改变；其余
13 项保持冻结哈希。

## 3. v06 B1--B5 关闭情况

| 项 | v07.1 静态证据 | 裁决 |
|---|---|---|
| B1 bounded readback | 父进程不再直接做包核对；`_run_bounded_package_readback()` 启动同文件 `--host-readback-worker`，总预算 5.0 s，预留 1.0 s 同步终止/回收；worker 使用 `-B` 且调用栈只读 | **CLOSED_STATICALLY** |
| B2 Docker deadline | inspect、stop、wait、JSON/exit-code parse、identity/resource validation 均接收并在前后复核同一 `MonotonicDeadline`；正常 post-exit inspect 也使用 earlier deadline | **CLOSED_STATICALLY** |
| B3 ownership window | host-final 与 readback worker 都由 stdin release gate 阻止访问运行目录；父进程仅在 Job assignment 和 deadline 复核成功后释放；assignment failure 路径关闭 gate 并同步 wait/kill/reap | **CLOSED_STATICALLY** |
| B4 plan sample | `plan_observed_monotonic` 已移动到 ledger preflight 与 gate-summary 恢复读取之后，并由同一样本生成 elapsed 与两个 deadline remaining/exhausted | **CLOSED_STATICALLY** |
| B5 test executability | 未定义变量已移除；缺 ready fixture 改为 `include_ready=False`；PRECHECK 覆盖源码的删除 API 扫描为 0 命中 | **CLOSED_STATICALLY** |

另有一个冻结后发现并已关闭的问题：`_host_readback_worker()` 在读包前显式执行
`_add_source_path(project_root)`；隔离回归源码以 `python -I -B` 验证导入目标解析到本项目
`src/paper2_figure2/evidence.py`，不依赖 pytest 已注入路径或偶然安装包。

## 4. 保持不变的已接受边界

1. canonical JSON 只要求 `dag` 数组顺序严格相等；`gates` 是 exact key-set，并按冻结 DAG
   主动索引；生产 canonical write/read round-trip 有对应测试源码。
2. readback 在路径访问前要求 ledger key set 精确等于实际目录减唯一自排除
   `hash_ledger.json`，并覆盖 completion、inventory、summary 与全部工件。
3. FINAL 300 s 与 total 3600 s 分别记录 applicability、absolute deadline、plan-point
   remaining 与 exhausted；shared 必须是较早不可变 deadline。
4. root success 仍是 PREPARED payload + 完整 inventory/ledger/prospective completion 复核 +
   最后独占 fsync `root_completion.json`；completion 后 worker 只有静态 no-write return/exit。
5. 活跃科学架构仍唯一为：心内膜离散链、心肌主动平面应变 FEM、ECM 黏弹平面应变 FEM。
   未见心肌 DCM、representation/comparator、流体、三维、第二求解器、GPU 或参数扫描回流。

## 5. 与实现接受分开的 PRECHECK/ST0

以下均尚未执行，必须在下一份版本化决定中单独授权并保留原始返回码：

1. 在 Windows 宿主运行不触及正式结果目录的静态/轻量测试子集，尤其是 Job Object、release
   gate、assignment failure、真实慢 readback 回收及隔离源码导入；
2. 检查固定 Docker image 的实际 ID、Docker 服务状态、容器名与正式 r01 结果路径不存在；
3. 在固定 Linux 容器内运行合同列出的 PRECHECK 测试集，确认语法、导入、单元与 FEniCSx
   runtime；
4. 只有宿主 ST0 与容器 PRECHECK 均通过，才另行决定是否执行 G0 与 40 个正式端点；
5. 任何 GPU worker 仍需用户明确确认，本项目当前 CPU-only 路线不应请求 GPU。

这些是尚待实际验证的 preflight，不是继续阻断静态接受的源码问题。

## 6. 精确下一步边界

1. 先创建一份版本化 PRECHECK 决定，冻结宿主测试命令、容器 PRECHECK 命令、最长时间、唯一
   项目内临时路径、预期返回码、停止条件与零删除操作；
2. 仅将接受的 15 个候选、其权威合同/接受记录、必要 review 和 PRECHECK 决定纳入精确 staging
   清单；继续排除七个既有 tracked 修改与全部无关 untracked 证据；
3. 提交并同步实现包后，以该提交作为 implementation lock 的 `accepted_implementation_commit`；
   implementation lock 是本地 create-only 锁，不纳入 scoped Git cleanliness，但必须自身被 hash；
4. 在 PRECHECK 决定和实现锁均完成前，不运行 Python/pytest、FEniCSx、solver 或 Docker，不创建
   `results/paper2_figure2`；
5. 本 review 不授权正式 r01、G0、端点计算、Figure 2 更新、论文结论或投稿表述。

## 7. 本轮停止点

本轮只进行了 PowerShell/文本级只读核验，并新建本 review。未修改 15 个候选、设计/执行
合同、旧 review、八个核心文件或 `CURRENT_STATUS.md`；未运行 Python、pytest、FEniCSx、
solver、Docker 或 GPU；未创建结果目录、实现锁或数值证据；未执行 Git 写操作。
