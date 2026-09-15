---
contract_id: CONTRACT-PAPER2-FIGURE2-FEM-ONLY-PRECHECK-STAGING-V02
status: p5_r03_precheck_pass_for_human_review
planner: project_controller
drafted_at: 2026-09-04
supersedes: project_control/paper2_figure2_fem_only_numerical_credibility_precheck_decision_and_exact_staging_v01.md
architecture_authority: project_control/paper2_myocardial_dcm_retirement_and_fem_only_architecture_decision_v01.md
physical_removal_record: project_control/paper2_myocardial_dcm_physical_removal_execution_record_v01.md
failure_diagnosis: project_control/paper2_figure2_s1_hotspot_mask_failure_readonly_diagnosis_v01.md
active_architecture: endocardium_discrete_chain__myocardium_active_plane_strain_fem__ecm_viscoelastic_plane_strain_fem
cleanup_staging_authorized: false
fixture_repair_authorized: true
host_cpu_checks_authorized: p1_p2_p3_only
dependency_reclassification_authorized: true
source_lock_assertion_repair_authorized: true
route_b_lazy_import_authorized: true
route_b_runtime_test_sha256: 5b85d716562be52a11c49f7954e66d1980067f2df2907f876beab6ebe3717995
p4_readonly_authorized: true
p4_outcome: pass_for_human_review
p4_evidence_sha256: a11c3b047f91752a2266e0a8f8f59fb75230904e010581652e31173853ed25b2
p5_authorized: true
p5_authorization_date: 2026-09-04
p5_authorization_text: 继续安排项目执行
p5_outcome: fail_closed_at_collection__dolfinx_import_unavailable
p5_evidence_sha256: ba06e775716151089d51ffbe64fee26ae54c6cd795fe86495d686e4b40eb4888
p5_container_id: 0b0a6c44909d2ea8dc988d92f7d7d502a61de54a19c24399c6a3e102465e7340
p5_r02_authorized: true
p5_r02_authorization_date: 2026-09-04
p5_r02_authorization_basis: readonly_diagnosis_h2_pythonpath_override
p5_r02_only_command_delta: PYTHONPATH=/workspace/src:/usr/local/dolfinx-real/lib/python3.12/dist-packages:/usr/local/lib:
p5_r02_container_name: paper2-figure2-nc-v03-r02
p5_r02_evidence_root: E:\Temp-Projects\PRL\tmp\paper2_figure2_fem_only_precheck_v02_r02_20260904\p5
p5_r02_outcome: fail_closed__17_failed_165_passed_2_windows_skipped
p5_r02_evidence_sha256: 9bfe96ae4c461c06cf0c54184ffae2265c8f4ce2d7463a3860087f214badb82a
p5_r02_container_id: 0ae55f99b83b89ea2ddd655870a1bf8b4e92b5e9ed1525fc3fe1bcd730c2f168
p5_r03_authorized: true
p5_r03_authorization_date: 2026-09-04
p5_r03_test_repairs_authorized: manufactured_self_match_plus_two_local_cidfile_fixtures_only
p5_r03_manufactured_test_sha256: 80f72467b4f89c4c04e6af7fe764b8d46c4ba539c7f48b3d7cc0b7d11cf6ed71
p5_r03_runtime_test_sha256: 4d836e3c2310bda3bb3ba0db08c5d8e22bbeda378358cad74dd789d8f0b14555
p5_r03_pythonpath: /workspace/src:/usr/local/dolfinx-real/lib/python3.12/dist-packages:/usr/local/lib:
p5_r03_xdg_cache_home: /tmp
p5_r03_tmpfs: /tmp:rw,nosuid,nodev,exec,size=1073741824
p5_r03_container_name: paper2-figure2-nc-v03-r03
p5_r03_evidence_root: E:\Temp-Projects\PRL\tmp\paper2_figure2_fem_only_precheck_v02_r03_20260904\p5
p5_r03_outcome: pass__182_passed_2_expected_windows_skipped
p5_r03_evidence_sha256: 493e3923564a05ed1c430cdbd2fea02ca3bce1d64ca766517cb2a5f9519ef3b5
p5_r03_container_id: 3561fcb66d0c2e389e7735aac13bb43e2aa77daed258e7da95520dc23a37cc77
precheck_authorized: false
docker_readonly_inspection_authorized: true
solver_or_docker_execution_authorized: p5_r03_consumed__formal_execution_not_authorized
git_commit_or_push_authorized: false
authorization_date: 2026-09-04
authorization_text: 好的，继续安排项目执行
host_check_outcome: p3_collect_9__p3_9_pass__p1_17_pass__p2_40_pass
p4_evidence_root: E:\Temp-Projects\PRL\tmp\paper2_figure2_p4_readonly_preflight_v01_20260904
p5_evidence_root: E:\Temp-Projects\PRL\tmp\paper2_figure2_fem_only_precheck_v02_20260904\p5
next_gate: human_acceptance_of_p5_r03_precheck
---

# Paper 2 Figure 2：FEM-only PRECHECK 与精确暂存合同 v02

## 0. 人类窄授权更新

2026-09-04，人类终审以“好的，继续安排项目执行”批准：仅在
`tests/paper2_figure2/test_evidence_v01.py` 中修复 S1 hotspot 测试夹具，使 hotspot、阈值和
mask 从夹具 traction 按现行正式公式派生；随后依次运行原失败定点测试、Figure 2
非 FEniCSx 静态/证据测试、P1 与 P3 主机 CPU-only 测试。任一步失败即 fail-closed 停止。

该授权不包含完整 P1–P5 PRECHECK、Docker、FEniCSx 求解器、GPU、正式结果写入、C0/C1
暂存、提交或推送；也不允许修改生产公式、阈值、比较符、科学合同或第二个源码/测试文件。

执行结果：原失败定点测试通过；随后 P2 在收集 `test_manufactured_v01.py` 时因主机缺少
`basix` 中止。依 fail-closed 规则，P1 与 P3 未运行。下一门为独立评审 P2 的依赖边界，
不得据此宣称 PRECHECK 通过。

追加依赖裁决确认：`test_manufactured_v01.py` 经直接依赖核对属于 FEniCSx runtime 测试，
因此从宿主 P2 重新归类到 P5；这不删除、不跳过也不弱化该测试。人类“继续安排项目执行”
及其日常事项自主推进授权允许从一个新的项目内临时根重新串行运行 P1、修订后的 P2 与 P3。
P4、P5、Docker、FEniCSx solver、GPU、正式结果和 Git 动作仍未授权。

重新分类后的宿主重跑结果：P1 为 `17 passed in 3.67s`；P2 为
`39 passed, 1 failed in 4.00s`。唯一失败是 source-lock 静态测试仍要求 runner 中出现旧的
精确单行文本 `_sha256(implementation_lock_path)`，而当前 runner 使用同一 `_sha256` 函数的
多行 deadline-aware 调用。P3 依 fail-closed 未运行。下一门为独立评审该静态契约与实现语义，
本合同不自行裁决或修复。

追加只读诊断确认：runner 仍将 `implementation_lock_path` 传入 `_sha256`，且新增 deadline 与
label 参数；`implementation_lock_sha256` 返回字段保持不变。失败只来自测试把函数调用锁定为
旧的单行排版。现批准仅修改 `tests/paper2_figure2/test_source_lock_v01.py` 中该断言，以跨空白/
换行验证 `_sha256(` 后的首个参数确为 `implementation_lock_path`。不得修改 runner、哈希行为、
lock 路径、deadline、科学合同或其他测试。随后从新临时根按定点节点、P1、P2、P3 串行重跑。

第二次宿主重跑结果：source-lock 定点节点 `1 passed in 0.69s`，P1 为
`17 passed in 3.38s`，P2 为 `40 passed in 3.56s`。P3 在收集期因
`test_runtime_smoke_v01.py` 顶层导入 `paper2_hybrid.model` 而再次触发主机缺少 `basix`；
`1 error in 1.13s`，冻结的 9 个节点未被收集。执行在此 fail-closed，未修改第二个测试文件。

随后经只读依赖闭包审计与人类授权，采用路线 B：保持 15 文件集合与 9 个 P3 node IDs 不变，
仅把 `test_runtime_smoke_v01.py` 的四组 FEM 模块级导入移入实际使用它们的 8 个 FEM 测试。
该文件 SHA-256 从 `b693e419ff93624b7f1014b6e15cb17aead303db0b6ef922cd11ad5162707311`
变为 `5b85d716562be52a11c49f7954e66d1980067f2df2907f876beab6ebe3717995`；runner 与 spec 未改。
最新宿主证据为：P3 collect-only `9 tests collected`、P3 `9 passed`、P1 `17 passed`、P2
`40 passed`。历史失败保留在以上时间线，但不再代表当前状态。

现只授权 P4 只读 Docker preflight：读取 Docker Server、固定镜像及精确 image ID、预留容器名
占用和正式结果路径状态；每个调用最多 15 秒、总计最多 60 秒。不得 pull、build、run、create、
start、stop、kill、remove、prune 或修改配置。P5 仍未授权。

P4 实际结果：Docker Server 可达；`dolfinx/dolfinx:v0.11.0` 解析为合同冻结的精确 image ID；
预留容器名未占用；正式 `results/paper2_figure2` 仍不存在。四项 exit code 均为 `0`，单项均小于
15 秒，总 wall time `4.2235894 s`。P4 当前为 `PASS_FOR_HUMAN_REVIEW`，不自动授权 P5。

随后人类以“继续安排项目执行”明确批准仅执行 P5 Linux CPU PRECHECK。授权严格限于下文冻结
命令及 11 个测试文件；执行前必须再次确认 P5 证据根不存在、预留容器名空闲。任何预存、身份
漂移、失败、超时、越界 skip、仓库写入或正式结果路径变化均立即 fail-closed。P5 PASS 也只形成
`PRECHECK_FOR_REVIEW`，不授权正式 G0、40 endpoints、implementation lock 或 Git 动作。

P5 实际在 create-only 前置门通过后执行一次，容器原生 exit `2`，壁钟 `5.899583 s`，未触发
宿主超时。pytest 在收集 `test_fenicsx_runtime.py` 与 `test_manufactured_v01.py` 时均报
`ModuleNotFoundError: No module named 'dolfinx'`；JUnit 为 `2 errors, 0 failures, 0 skipped`。
因此 P5 裁决为 `FAIL_CLOSED_AT_COLLECTION`，没有形成完整 PRECHECK 通过证据。容器以完整 ID
`0b0a6c44909d2ea8dc988d92f7d7d502a61de54a19c24399c6a3e102465e7340` 保持 exited 供审阅；
未观察到排除 `tmp/**` 后的仓库状态或正式结果路径漂移。当前不授权重试或任何修复。

随后严格只读诊断确认：镜像 Config.Env 原含
`PYTHONPATH=/usr/local/dolfinx-real/lib/python3.12/dist-packages:/usr/local/lib:`，但 r01 容器实际
Config.Env 被显式参数替换为 `PYTHONPATH=/workspace/src`；镜像 Entrypoint 为 `null`，其激活不依赖
Entrypoint。人类据此批准一次最小 r02 重试。唯一命令差异是把 `PYTHONPATH` 冻结为
`/workspace/src:/usr/local/dolfinx-real/lib/python3.12/dist-packages:/usr/local/lib:`；其他 image ID、
11 个测试文件、资源、安全、超时和 fail-closed 条件全部不变。r02 必须使用全新根
`E:\Temp-Projects\PRL\tmp\paper2_figure2_fem_only_precheck_v02_r02_20260904\p5` 与全新容器名
`paper2-figure2-nc-v03-r02`，不得触碰 r01。若 r02 失败，不授权自动第三次重试。

r02 实际执行 exit `1`，宿主壁钟 `40.673486 s`，未超时；JUnit 为 `184 tests`、
`17 failures`、`0 errors`、`2 skipped`，即 `165 passed`。`PYTHONPATH` 修订已使 DOLFINx 成功
导入并进入 FFCx JIT，但 14 个 FEM 节点因 read-only rootfs 下 `/root/.cache/fenics` 不可写而
失败；另有 1 个测试源码自引用静态断言失败和 2 个测试局部 `container.cid` 夹具缺失失败。
两个 skip 均为源码明确的 Windows-only Job boundary 节点。r02 因非零返回而 fail-closed；不授权
第三次重试或任何修复。

随后只读诊断闭合了三个阻断类别，并由人类批准“两个测试夹具修复 + 一次 P5 r03”。代码写入
严格限于两个测试文件：`test_manufactured_v01.py` 只把自匹配的连续 parametrize 字面量拆为
运行时拼接；`test_runtime_smoke_v01.py` 只在两个 pre-holdout 测试各自 `tmp_path` create-only
写入基线 `container.cid`。生产源码、runner、spec、判据、skip 与其他测试未改。

修复后宿主串行门均通过：两个 cidfile 定向节点 `2 passed in 1.21s`；P1 `17 passed in 3.62s`；
P2 `40 passed in 3.27s`；P3 `9 passed in 6.13s`。r03 仅在 r02 的修订 `PYTHONPATH` 基础上新增
`XDG_CACHE_HOME=/tmp`，并把既有 `/tmp` tmpfs 的 `noexec` 改为 `exec`；其他冻结参数保持不变。
r03 必须使用全新证据根和容器名，先复核不存在/空闲及 r01/r02 完整性；失败即停止且不得自动
再次重试。

r03 实际执行 exit `0`，宿主壁钟 `56.970658 s`，未超时，stderr 为空；JUnit 为
`184 tests`、`0 failures`、`0 errors`、`2 skipped`，即 `182 passed`。两个 skip 均为源码明确的
Windows-only Job boundary 节点，没有其他 skip。容器以完整 ID
`3561fcb66d0c2e389e7735aac13bb43e2aa77daed258e7da95520dc23a37cc77` 保持 exited；r01/r02
终态及证据未变，源码/控制面和正式结果路径无运行漂移。r03 只形成
`P5_R03_PRECHECK_PASS_FOR_HUMAN_REVIEW`，不授权正式执行。

## 1. 目标与当前结论

本合同在心肌 DCM 已从当前工作树物理清理后，重新定义 Figure 2 的 PRECHECK 与提交边界。
唯一活跃架构为：

```text
心内膜离散细胞链
  -> 主动心肌平面应变 FEM
  -> 黏弹 ECM 平面应变 FEM
```

流体、三维、心肌离散比较臂、表示转换、缩放校准和旧结果再生成均不属于本合同。

当前裁决为：S1 与 source-lock 夹具修复均已通过；路线 B 已解除 P3 的模块级 FEM 连带导入；
P1--P3 主机证据及 P4 只读 preflight 均通过。P5 已获窄授权并执行一次，但在收集阶段因冻结
命令的 `python3` 环境无法导入 `dolfinx` 而 fail-closed。因此完整 P1--P5 PRECHECK 未通过；
P5 重试、入口或镜像修复、solver 正式执行、正式结果和 staging 均未授权。

## 2. 当前工作树基线

只读观察：

- branch: `codex/simucell3d-hybrid-feasibility`
- HEAD: `8f240cf38cb4db38f02b776d320562058439770f`
- upstream: `origin/codex/simucell3d-hybrid-feasibility`
- ahead/behind: `0/0`
- index entries: `0`
- tracked diff: `405 deleted + 5 modified`

其中只有下列 4 个修改属于物理清理：

1. `external/simucell3d/include/prl_cell_engine/remesh_contract.hpp`
2. `project_control/CURRENT_STATUS.md`
3. `pyproject.toml`
4. `tests/paper2_hybrid/test_static_architecture.py`

`project_control/prl_figure2_spatial_tolerance_validation_contract_v02.md` 是既有、无关的 tracked
修改，必须始终排除在本合同两个提交候选之外。

物理清理后现存生产与测试表面为：

| 表面 | 文件数 | 角色 |
|---|---:|---|
| `src/paper2_hybrid/` | 8 | 当前 FEM-only 三层生产实现 |
| `src/paper2_figure2/` | 7 | Figure 2 数值可信度、证据与裁决 |
| `src/paper2_m1/` | 2 | 理想化主动 FEM/端口基线 |
| `tests/paper2_hybrid/` | 3 | 架构、投影、FEniCSx runtime |
| `tests/paper2_figure2/` | 7 | Figure 2 协议、证据、数值门与 runtime smoke |
| `tests/paper2_m1/` | 1 | M1 主动 FEM/端口测试 |
| `scripts/` | 4 | 两个生产入口与两个通用证据/文档工具 |

已退役执行命名空间、旧结果树及心肌专用 C++ 栈在当前工作树中均不存在。后续活跃源码、
测试、PRECHECK 和提交不得恢复、导入或生成这些路线。源码中的数值 comparator、容器
identity、离散功率 identity，以及用于证明退役 API 不可调用的负向断言，不构成心肌模型比较臂。

## 3. 单一失败与修复记录

权威诊断为
`project_control/paper2_figure2_s1_hotspot_mask_failure_readonly_diagnosis_v01.md`。其边界是：

1. `_arrays()` 将 bool schema 初始化为全 `False`；
2. 零 S1 hotspot field 按正式 `min + 0.05 * range` 与 `<=` 规则应得到全 `True` mask；
3. 生产提取 `observables.py` 与验证器 `evidence.py` 使用相同公式；
4. 因此最小候选修复只应让测试夹具从其 traction 按正式公式派生 hotspot 与 mask；
5. 不修改生产公式、阈值、方向、比较符、科学合同或求解器。

已执行的修复只触及：

```text
tests/paper2_figure2/test_evidence_v01.py
```

修复前 SHA-256 为
`5c1760db59cb1cac527b264f5ab09a32227e1fa069f71d4e46f289c2fc8657d5`，修复后为
`082eb2a5d989656268404fcf27dd5cb043654eade2817950a78e7c3afedd5778`。既有 15 文件冻结和
v07.2 静态接受不再能授权 staging；必须运行获准测试、重新冻结 15 文件并取得新的独立实现复核。

## 4. 两个提交候选必须严格分离

### 4.1 C0：心肌 DCM 物理清理提交候选

C0 的 tracked source set 由下列 manifest 唯一定义：

```text
project_control/paper2_myocardial_dcm_physical_removal_tracked_manifest_v01.txt
```

manifest 当前为 409 项：`405 D + 4 M`；SHA-256 为
`bc33efc089a3e08e7f5ca4a4c5ac088521a01f85061e419b97140de0499aea15`。C0 最终 staging path set
必须恰为 411 项：

1. manifest 中的 409 个精确路径及状态；
2. `project_control/paper2_myocardial_dcm_physical_removal_execution_record_v01.md`，SHA-256
   `ff7da8c60fbc2f0868276371ca1ac63ac14c03a6dbc39fa7e7420c514f412d22`；
3. manifest 文件自身。

C0 不得包含 Figure 2 的 15 个候选、Figure 2 合同/review、本合同、S1 诊断、PRECHECK 临时
证据、无关 tracked 修改或任何 allowlist 外 untracked。不得使用目录级、通配或全仓 add。

C0 当前只是**独立提交候选**，不授权 staging、commit 或 push。staging 前需重新核对 base
HEAD、409 行 manifest 与当前 diff 完全相等；任一增删、重命名或状态变化都使候选失效。

### 4.2 C1：Figure 2 FEM-only 实现包候选

C1 必须建立在已接受的 C0 提交之上，并等待 S1 夹具修复、测试和新实现复核完成。其生产/测试
代码边界固定为以下 15 个路径，不得加入其他源码：

1. `src/paper2_figure2/__init__.py`
2. `src/paper2_figure2/spec.py`
3. `src/paper2_figure2/manufactured.py`
4. `src/paper2_figure2/projection.py`
5. `src/paper2_figure2/observables.py`
6. `src/paper2_figure2/evidence.py`
7. `src/paper2_figure2/adjudication.py`
8. `scripts/run_paper2_figure2_fem_only_numerical_credibility_v01.py`
9. `tests/paper2_figure2/test_spec_v01.py`
10. `tests/paper2_figure2/test_source_lock_v01.py`
11. `tests/paper2_figure2/test_projection_v01.py`
12. `tests/paper2_figure2/test_adjudication_v01.py`
13. `tests/paper2_figure2/test_evidence_v01.py`
14. `tests/paper2_figure2/test_manufactured_v01.py`
15. `tests/paper2_figure2/test_runtime_smoke_v01.py`

C1 的治理文件边界预留为：

- Figure 2 execution contract v03 及两轮 execution review；
- implementation review v01--v07、v07.1、v07.2，均只作历史审查链；
- 已作废的 PRECHECK/staging v01 与本 v02，明确以前者为 superseded；
- S1 hotspot mask 只读诊断；
- 未来的人类窄修订决定与新的实现复核记录。

由于第 13 项和未来复核记录尚未冻结，C1 当前**没有可执行的最终 staging allowlist**。不得把
上述边界解释为现在可以 staging。只有修复获准并完成后，才能另立附录冻结每个路径、bytes、
lines、SHA-256 和 staged blob；implementation lock 必须在 C1 提交形成后 create-only 生成，
不得进入 C1 提交本身。

## 5. 新 FEM-only PRECHECK 阶梯

PRECHECK 仅在 C0、C1、implementation lock 和独立复核全部完成并获得新的明确运行授权后
执行。唯一临时根预留为：

```text
E:\Temp-Projects\PRL\tmp\paper2_figure2_fem_only_precheck_v02_20260904
```

该目录在执行前必须不存在；存在即 `OUTPUT_PATH_EXISTS_FAIL/71`，不得删除、覆盖、续接或
自动换名。pytest cache 禁用，bytecode 禁用；所有 stdout/stderr、JUnit、exit code、monotonic
起止值和 Docker inspect 原文只写入该临时根，绝不写入正式 `results/paper2_figure2`。

本次获准的 P1--P3 宿主重跑不构成完整 PRECHECK，使用新的唯一临时根：

```text
E:\Temp-Projects\PRL\tmp\paper2_figure2_reclassified_host_checks_v01_20260904
```

不得复用、覆盖或清理先前失败运行的临时根。

### P1：宿主 portable architecture gate

固定文件：

```text
tests/paper2_m1/test_idealized_strip.py
tests/paper2_hybrid/test_static_architecture.py
tests/paper2_hybrid/test_projection.py
```

最新宿主重跑为 `17 passed in 3.31s`；正式 PRECHECK 时仍需在 C0/C1 新基线与 lock 下重跑。宿主 hard
cap `120 s`，预期 exit `0`、17 passed、0 failed/error/skipped。该门不导入 basix，不执行
FEniCSx runtime。

### P2：宿主 Figure 2 static/evidence gate

固定文件：

```text
tests/paper2_figure2/test_spec_v01.py
tests/paper2_figure2/test_source_lock_v01.py
tests/paper2_figure2/test_projection_v01.py
tests/paper2_figure2/test_adjudication_v01.py
tests/paper2_figure2/test_evidence_v01.py
```

`test_manufactured_v01.py` 因收集期依赖 `basix.ufl` 与 `dolfinx`，只属于 P5。修订后的 P2
hard cap `120 s`；预期 exit `0`、0 failed/error/skipped。任何失败立即停止，不进入 P3。

本次修订后 P2 实际为 `39 passed, 1 failed in 4.00s`；失败节点是
`test_source_lock_v01.py::test_local_machine_lock_is_hashed_but_excluded_only_from_git_cleanliness`。
这是历史失败；跨空白断言修复后，最新 P2 为 `40 passed in 3.69s`，当前主机 P2 已通过。

### P3：Windows host worker-safety gate

只运行 `tests/paper2_figure2/test_runtime_smoke_v01.py` 中冻结的 9 个 Windows node：无
`setitimer`、ownership release、assignment failure、正常 parent tail、bounded readback、隔离
导入、真实慢 readback、3/3/4 recovery 和 unreaped access revocation。hard cap `90 s`；预期
exit `0`、9 passed、0 failed/error/skipped。不得运行 FEM endpoint。

本次实际在收集阶段因该文件顶层导入 `paper2_hybrid.model` 而缺少 `basix`，结果为
`1 error in 1.13s`，没有执行 9 个节点。当时 P3 保持红门，并进入拆分或延迟导入的独立评审。

以上为历史失败。路线 B 完成后，最新证据为 collect-only `9 tests collected in 0.35s`，随后
P3 `9 passed in 6.08s`；模块级 FEM 重依赖计数为 `0`。当前主机 P3 已通过。

### P4：Docker read-only gate

只允许读取 Docker Server、固定镜像
`dolfinx/dolfinx:v0.11.0`、镜像 ID
`sha256:2ae4bfbc0d9077268880faf04c72750528bee986c94ab223a2c159969bd56fa8`、PRECHECK 容器名占用
和正式结果路径状态。不得 pull、build、run、stop、kill、remove 或 prune。总 hard cap `60 s`，
每个 CLI 调用 `15 s`；任一服务、镜像、身份或路径漂移即停止，不进入 P5。

本轮 P4 已获只读授权，唯一证据根为：

```text
E:\Temp-Projects\PRL\tmp\paper2_figure2_p4_readonly_preflight_v01_20260904
```

该根执行前必须不存在；不复用、覆盖或清理前四个临时根。P4 通过也只允许起草 P5 命令，
不授权运行容器。

P4 已通过。原始命令、stdout/stderr、exit code 与 wall time 位于：

```text
tmp/paper2_figure2_p4_readonly_preflight_v01_20260904/p4_readonly_preflight_evidence_v01.md
```

文件 SHA-256 为
`a11c3b047f91752a2266e0a8f8f59fb75230904e010581652e31173853ed25b2`。

### P5：固定 Linux CPU 容器 PRECHECK

P5 使用单 CPU、8 GiB、无网络、read-only rootfs、cap-drop ALL、no-new-privileges、无 GPU、
无 Docker socket 的固定容器。项目仓库只读挂载，唯一持久可写挂载是 PRECHECK 临时根。测试
文件严格为：

```text
tests/paper2_m1/test_idealized_strip.py
tests/paper2_hybrid/test_static_architecture.py
tests/paper2_hybrid/test_projection.py
tests/paper2_hybrid/test_fenicsx_runtime.py
tests/paper2_figure2/test_spec_v01.py
tests/paper2_figure2/test_source_lock_v01.py
tests/paper2_figure2/test_projection_v01.py
tests/paper2_figure2/test_adjudication_v01.py
tests/paper2_figure2/test_evidence_v01.py
tests/paper2_figure2/test_manufactured_v01.py
tests/paper2_figure2/test_runtime_smoke_v01.py
```

其中 `test_manufactured_v01.py` 是 FEniCSx runtime 证据，只能在 P5 的固定 Linux CPU 环境
执行；它没有被删除、跳过或从完整 PRECHECK 中移除。

容器总 hard cap `240 s`：正常测试最多 `210 s`，保留 `30 s` 给完整 cidfile ID 核验、必要的按
ID stop/wait 和末次 inspect。禁止 `--rm`；容器保留 stopped 供审阅。预期 Docker run exit
`0`、JUnit 0 failed/error；只允许源码中明确标记的 Windows-only 用例在 Linux skip。

P5 PASS 只形成 `FEM_ONLY_PRECHECK_PASS_FOR_SUPERVISOR_REVIEW`，不自动创建正式 r01、不执行
G0 或 40 个端点，也不形成 Figure 2 或论文科学结论。

以下 P5 CPU-only 启动命令曾获人类窄授权，create-only 前置门通过后已精确执行一次，状态为
`EXECUTED_ONCE__FAIL_CLOSED_AT_COLLECTION__NO_RETRY_AUTHORIZED`。现有项目根只读挂载：

```powershell
docker run `
  --pull=never `
  --name paper2-figure2-nc-v03-r01 `
  --cpus=1 `
  --memory=8g `
  --network=none `
  --read-only `
  --cap-drop=ALL `
  --security-opt=no-new-privileges `
  --mount "type=bind,source=E:\Temp-Projects\PRL,target=/workspace,readonly" `
  --mount "type=bind,source=E:\Temp-Projects\PRL\tmp\paper2_figure2_fem_only_precheck_v02_20260904\p5,target=/evidence" `
  --tmpfs "/tmp:rw,nosuid,nodev,noexec,size=1073741824" `
  --workdir /workspace `
  --env PYTHONDONTWRITEBYTECODE=1 `
  --env PYTHONPATH=/workspace/src `
  --env CUDA_VISIBLE_DEVICES=-1 `
  --env NVIDIA_VISIBLE_DEVICES=void `
  --cidfile "E:\Temp-Projects\PRL\tmp\paper2_figure2_fem_only_precheck_v02_20260904\p5\container.cid" `
  sha256:2ae4bfbc0d9077268880faf04c72750528bee986c94ab223a2c159969bd56fa8 `
  timeout --signal=TERM --kill-after=30s 210s `
  python3 -B -m pytest -q -p no:cacheprovider `
  --basetemp=/evidence/pytest_tmp `
  --junitxml=/evidence/junit.xml `
  tests/paper2_m1/test_idealized_strip.py `
  tests/paper2_hybrid/test_static_architecture.py `
  tests/paper2_hybrid/test_projection.py `
  tests/paper2_hybrid/test_fenicsx_runtime.py `
  tests/paper2_figure2/test_spec_v01.py `
  tests/paper2_figure2/test_source_lock_v01.py `
  tests/paper2_figure2/test_projection_v01.py `
  tests/paper2_figure2/test_adjudication_v01.py `
  tests/paper2_figure2/test_evidence_v01.py `
  tests/paper2_figure2/test_manufactured_v01.py `
  tests/paper2_figure2/test_runtime_smoke_v01.py
```

命令不含 `--rm`，没有 Docker socket 或 GPU 设备挂载。实际容器在 `5.899583 s` 内以 exit `2`
结束并保留供 inspect；未触发 timeout。完整容器 ID、资源限制、JUnit、stdout/stderr 与前后路径/
状态核验已封存于：
`tmp/paper2_figure2_fem_only_precheck_v02_20260904/p5/p5_linux_cpu_precheck_evidence_v01.md`。
其 SHA-256 为 `ba06e775716151089d51ffbe64fee26ae54c6cd795fe86495d686e4b40eb4888`。

## 6. 失败、输出与停止条件

1. P1--P5 严格串行，任何非零、timeout、skip 越界、残留进程、仓库写入、正式结果路径变化、
   lock/hash 漂移或退役命名空间出现，立即停止；
2. 每门在唯一临时根的独立子目录中 create-only 保存 `invocation.json`、合并 stdout/stderr、
   `native_exit_code.txt`、JUnit（如适用）和 deadline 状态；不覆盖、不删除、不重试；
3. 宿主缺 `basix` 是当前已知环境事实，因此宿主不得假装完成 FEM runtime；
   `test_manufactured_v01.py` 与 FEM runtime 检查只在 P5 固定 Linux 容器执行；
4. P4 与 P5 r03 已通过，r01/r02 历史失败保留；r03 授权已消费，不授权其他 Docker/FEniCSx
   solver 执行、正式结果或 GPU；
5. 完整 P1--P5 PRECHECK、C0/C1 staging、lock 与正式结果仍保持
   `NOT_AUTHORIZED/NOT_REACHED`。

## 7. 接受标准

本合同只有同时满足以下条件才可交人类决定：

- 409 项物理清理 manifest 与当前 tracked diff 完全一致；
- C0=411 项与 C1 的代码/治理边界互不相交；
- 单一 S1 失败的原因、最小未来修复和证据限制明确；
- PRECHECK 只引用 `paper2_m1`、`paper2_hybrid`、`paper2_figure2` 及现行测试；
- P1--P5 均有固定输入、资源上限、预期返回码和 fail-closed 停止点；
- 所有旧结果、旧运行入口、无关 tracked 修改和 allowlist 外 untracked 均明确排除；
- 当前 P1--P5 PRECHECK 已形成 `PASS_FOR_HUMAN_REVIEW`；没有正式 G0/40 endpoints、staging、
  commit、push 或科学结论授权。

## 8. Out of scope 与当前停止点

P4 只读检查已通过，P5 冻结容器已执行一次并在测试收集阶段 fail-closed；未运行任何数值测试
主体、G0/40 endpoints 或 GPU，不创建正式结果或 implementation lock，不暂存、提交或推送。
三维、流体、参数扫描、组织级扩展、Figure 3--5 和投稿结论均不在本合同内。

当前停止点为独立只读评审 P5 的 Python/FEniCSx 入口不一致。不得把本次 collection failure
解释为模型失败，也不得自行修改镜像、命令或测试后重试。任何最小修复与第二次 P5 都需新的
明确人类授权。

只读评审完成后，人类批准的单次 r02 最小重试已执行并以 exit `1` fail-closed。当前停止点为
三个失败类别的独立只读评审：FEniCSx JIT cache 写入策略、一个自引用静态断言、两个局部
cidfile 测试夹具。不得自行修改或第三次重试。该边界仍不包含正式 G0/40 endpoints、正式
results、implementation lock、GPU、staging、commit、push 或任何清理。

r02 完整证据位于
`tmp/paper2_figure2_fem_only_precheck_v02_r02_20260904/p5/p5_linux_cpu_precheck_r02_evidence_v01.md`，
SHA-256 为 `9bfe96ae4c461c06cf0c54184ffae2265c8f4ce2d7463a3860087f214badb82a`。r02 完整容器 ID 为
`0ae55f99b83b89ea2ddd655870a1bf8b4e92b5e9ed1525fc3fe1bcd730c2f168`，保持 exited 供审阅；
r01 同样保持原终态和原证据哈希。

三个失败类别只读诊断完成后，人类已批准上述两处测试夹具修复与一次 r03。当前停止点更新为
r03 create-only 前置门：新根
`E:\Temp-Projects\PRL\tmp\paper2_figure2_fem_only_precheck_v02_r03_20260904\p5` 必须不存在，
新容器名 `paper2-figure2-nc-v03-r03` 必须空闲，冻结 image ID 必须匹配，r01/r02 容器及证据必须
未变。全部通过后才执行一次 r03。该授权不包含再次重试、正式 G0/40 endpoints、正式 results、
implementation lock、GPU、staging、commit、push 或任何清理。

r03 create-only 前置门与一次执行均已完成。结果为 `182 passed + 2` 个明确 Windows-only skip，
exit `0`；完整证据位于
`tmp/paper2_figure2_fem_only_precheck_v02_r03_20260904/p5/p5_linux_cpu_precheck_r03_evidence_v01.md`，
SHA-256 `493e3923564a05ed1c430cdbd2fea02ca3bce1d64ca766517cb2a5f9519ef3b5`。当前停止点更新为
人类 P5 r03 接受门。不得从 PRECHECK PASS 自动进入正式 G0、40 endpoints、implementation lock、
正式 results、Figure 2 结论、GPU、staging、commit、push 或清理。
