---
record_id: RECORD-PAPER2-FIGURE2-S1-FIXTURE-HOST-CHECKS-V01
status: p5_r03_precheck_pass_for_human_review
executed_at: 2026-09-04
authorization: 好的，继续安排项目执行
contract: project_control/paper2_figure2_fem_only_precheck_and_exact_staging_contract_v02.md
reclassification_authorized_at: 2026-09-04
p5_authorization: 继续安排项目执行
p5_r02_authorization: readonly_h2_diagnosis_accepted__single_retry_only
p5_r03_authorization: two_test_fixture_repairs_plus_single_cpu_precheck
next_gate: human_acceptance_of_p5_r03_precheck
---

# Paper 2 Figure 2：S1 夹具修复与主机检查执行记录 v01

## 1. 唯一代码改动

本次在 `tests/paper2_figure2/test_evidence_v01.py::_arrays()` 内仅增加四行派生逻辑：

1. 从 `s1_traction_on_ecm_p0` 计算 `hotspot`；
2. 按现行 `min + 0.05 * ptp` 公式计算逐端点阈值；
3. 回填 `s1_hotspot_traction_e_to_m_x`；
4. 按现行 `<=` 比较符回填 `s1_hotspot_mask`。

未修改生产公式、阈值、比较符、科学合同或第二个源码/测试文件。

- 修复前 SHA-256：`5c1760db59cb1cac527b264f5ab09a32227e1fa069f71d4e46f289c2fc8657d5`
- 修复后 SHA-256：`082eb2a5d989656268404fcf27dd5cb043654eade2817950a78e7c3afedd5778`
- 修复后大小：`9902 bytes`；`237 lines`

## 2. 实际测试与结果

所有已执行命令均设置 `PYTHONDONTWRITEBYTECODE=1`、`PYTHONPATH=E:\Temp-Projects\PRL\src`，
使用 `python -B`、`-p no:cacheprovider` 和项目内独立 `--basetemp`。

### 2.1 原失败定点测试

```powershell
python -B -m pytest -q -p no:cacheprovider --basetemp='E:\Temp-Projects\PRL\tmp\paper2_figure2_fixture_repair_host_checks_v01_20260904\targeted_pytest_tmp' 'tests/paper2_figure2/test_evidence_v01.py::test_216_formal_commitments_bind_the_final_npz'
```

结果：退出码 `0`，`1 passed in 2.47s`。出现 CuPy 未检测到 CUDA 路径的导入警告；未启动
GPU，警告不影响该测试通过。

### 2.2 Figure 2 非 FEniCSx 静态/证据集

```powershell
python -B -m pytest -q -p no:cacheprovider --basetemp='E:\Temp-Projects\PRL\tmp\paper2_figure2_fixture_repair_host_checks_v01_20260904\figure2_static_pytest_tmp' 'tests/paper2_figure2/test_spec_v01.py' 'tests/paper2_figure2/test_source_lock_v01.py' 'tests/paper2_figure2/test_projection_v01.py' 'tests/paper2_figure2/test_adjudication_v01.py' 'tests/paper2_figure2/test_evidence_v01.py' 'tests/paper2_figure2/test_manufactured_v01.py'
```

结果：退出码 `1`；测试收集在 `test_manufactured_v01.py` 中止。该模块通过
`paper2_hybrid.model` 顶层导入 `basix.ufl`，当前主机报
`ModuleNotFoundError: No module named 'basix'`；`1 error in 1.59s`。因此 P2 没有形成通过证据。

### 2.3 后续检查

按 fail-closed 顺序，P1 与 P3 均未运行；没有以拆分命令绕过 P2 失败。

## 3. 偏差与边界

合同把 P2 称为“非 FEniCSx 静态/证据集”，但其中的 manufactured 测试存在收集期
`basix` 依赖；这是本次唯一执行偏差。原 S1 失败点已独立通过，当前证据不支持把 P2
收集失败归因于 S1 修复，也不支持宣称完整主机检查或 PRECHECK 已通过。

本次未运行 Docker、FEniCSx 求解器或 GPU；未写入正式 Figure 2 结果，未生成 implementation
lock，未执行 C0/C1 暂存、提交或推送。检查时 Git index 条目为 `0`。

项目内测试临时目录为：
`E:\Temp-Projects\PRL\tmp\paper2_figure2_fixture_repair_host_checks_v01_20260904`。当前只确认
定点测试 scratch 子目录存在，尚未清理。

## 4. 依赖事实裁决与追加授权

直接依赖核对确认：`test_manufactured_v01.py` 顶层通过 `paper2_hybrid.model` 导入
`basix.ufl` 与 `dolfinx`。因此将它从宿主 P2 重新归类到 P5 是依赖事实修正，不是删除、跳过或
弱化测试，也不修改代码、测试或科学判据。

根据人类“继续安排项目执行”及既有日常事项自主推进授权，追加批准从新的项目内唯一临时根
重新串行运行 P1、修订后的 P2、P3；仍不授权 Docker、P5、FEniCSx solver、GPU、正式结果、
implementation lock、staging、commit 或 push。任何一门失败立即停止，不改代码绕过。

## 5. 宿主重跑结果

新临时根冻结为：
`E:\Temp-Projects\PRL\tmp\paper2_figure2_reclassified_host_checks_v01_20260904`。旧临时根不得
复用、覆盖或清理。

### 5.1 P1 portable architecture gate

```powershell
python -B -m pytest -q -p no:cacheprovider --basetemp='E:\Temp-Projects\PRL\tmp\paper2_figure2_reclassified_host_checks_v01_20260904\p1_pytest_tmp' 'tests/paper2_m1/test_idealized_strip.py' 'tests/paper2_hybrid/test_static_architecture.py' 'tests/paper2_hybrid/test_projection.py'
```

结果：退出码 `0`，`17 passed in 3.67s`；命令壁钟 `13.295s`。仅有 CuPy 未检测到 CUDA
路径的导入警告，未启动 GPU。

### 5.2 P2 reclassified Figure 2 static/evidence gate

```powershell
python -B -m pytest -q -p no:cacheprovider --basetemp='E:\Temp-Projects\PRL\tmp\paper2_figure2_reclassified_host_checks_v01_20260904\p2_pytest_tmp' 'tests/paper2_figure2/test_spec_v01.py' 'tests/paper2_figure2/test_source_lock_v01.py' 'tests/paper2_figure2/test_projection_v01.py' 'tests/paper2_figure2/test_adjudication_v01.py' 'tests/paper2_figure2/test_evidence_v01.py'
```

结果：退出码 `1`，`39 passed, 1 failed in 4.00s`；命令壁钟 `12.981s`。失败节点：

```text
tests/paper2_figure2/test_source_lock_v01.py::test_local_machine_lock_is_hashed_but_excluded_only_from_git_cleanliness
```

测试要求 `_prelock()` 源码片段包含精确文本 `_sha256(implementation_lock_path)`；当前 runner
在同一位置使用多行 `_sha256(implementation_lock_path, deadline=..., label=...)` 调用，因此
字符串断言失败。当前只将其记录为“静态文本契约与 deadline-aware 实现的漂移候选”，不在执行
角色内判定哪一侧应修改。

### 5.3 P3 与停止边界

P3 的 9 个 Windows worker-safety 节点未运行。P2 非零后立即 fail-closed，没有修改任何代码
或测试绕过失败，也没有运行 Docker、P5、FEniCSx solver 或 GPU。

## 6. SHA、偏差与下一门

- `tests/paper2_figure2/test_evidence_v01.py`：
  `082eb2a5d989656268404fcf27dd5cb043654eade2817950a78e7c3afedd5778`，本轮未变；
- `tests/paper2_figure2/test_source_lock_v01.py`：
  `4ff9e17b6f2348410f59ed68a3922140c00c319ec14e53f412fa0a6f95353511`，本轮未变；
- `scripts/run_paper2_figure2_fem_only_numerical_credibility_v01.py`：
  `93f1f9694e785288172e66ba59df7fbc8cdffa27575a237fc8999a0d04851d31`，本轮未变。

本轮唯一计划内偏差是 P2 新暴露一个 source-lock 精确文本断言失败。正式
`results/paper2_figure2` 与 implementation lock 仍不存在，Git index 条目为 `0`。下一步必须
独立只读评审该断言与实现语义；评审前不授权修复或续跑 P3。

## 7. Source-lock 诊断、授权与修复前 SHA

追加只读核对确认：runner 的 `_prelock()` 仍以 `implementation_lock_path` 为 `_sha256` 的首个
参数，并增加 `deadline=deadline` 和 label；返回字段仍为 `implementation_lock_sha256`。失败仅因
测试要求旧的单行精确文本，并不构成哈希安全语义丢失证据。

- `tests/paper2_figure2/test_source_lock_v01.py` 修复前 SHA-256：
  `4ff9e17b6f2348410f59ed68a3922140c00c319ec14e53f412fa0a6f95353511`；`3038 bytes`，`91 lines`；
- 修复后 SHA-256：
  `b9db75f2ec37c791a18414dd13106765143d84cf0570045256cf48f4855ecb29`；`3100 bytes`，`94 lines`；
- runner 修复前 SHA-256：
  `93f1f9694e785288172e66ba59df7fbc8cdffa27575a237fc8999a0d04851d31`；修复后 SHA 相同。

现批准只把该精确字符串断言改为跨空白/换行验证，不修改 runner 或其他代码/测试。第三个唯一
临时根冻结为：
`E:\Temp-Projects\PRL\tmp\paper2_figure2_source_lock_assertion_host_checks_v01_20260904`。执行顺序为
失败节点、P1、P2、P3；任一步非零立即停止。

## 8. Source-lock 修复后串行验证

全部命令设置 `PYTHONDONTWRITEBYTECODE=1`、`PYTHONPATH=E:\Temp-Projects\PRL\src`，并使用
`python -B`、`-p no:cacheprovider` 与各自独立 `--basetemp`。

### 8.1 原失败节点

```powershell
python -B -m pytest -q -p no:cacheprovider --basetemp='E:\Temp-Projects\PRL\tmp\paper2_figure2_source_lock_assertion_host_checks_v01_20260904\targeted_pytest_tmp' 'tests/paper2_figure2/test_source_lock_v01.py::test_local_machine_lock_is_hashed_but_excluded_only_from_git_cleanliness'
```

结果：退出码 `0`，`1 passed in 0.69s`；命令壁钟 `10.351s`。

### 8.2 P1

```powershell
python -B -m pytest -q -p no:cacheprovider --basetemp='E:\Temp-Projects\PRL\tmp\paper2_figure2_source_lock_assertion_host_checks_v01_20260904\p1_pytest_tmp' 'tests/paper2_m1/test_idealized_strip.py' 'tests/paper2_hybrid/test_static_architecture.py' 'tests/paper2_hybrid/test_projection.py'
```

结果：退出码 `0`，`17 passed in 3.38s`；命令壁钟 `12.348s`。

### 8.3 P2

```powershell
python -B -m pytest -q -p no:cacheprovider --basetemp='E:\Temp-Projects\PRL\tmp\paper2_figure2_source_lock_assertion_host_checks_v01_20260904\p2_pytest_tmp' 'tests/paper2_figure2/test_spec_v01.py' 'tests/paper2_figure2/test_source_lock_v01.py' 'tests/paper2_figure2/test_projection_v01.py' 'tests/paper2_figure2/test_adjudication_v01.py' 'tests/paper2_figure2/test_evidence_v01.py'
```

结果：退出码 `0`，`40 passed in 3.56s`；命令壁钟 `12.599s`。

### 8.4 P3

```powershell
python -B -m pytest -q -p no:cacheprovider --basetemp='E:\Temp-Projects\PRL\tmp\paper2_figure2_source_lock_assertion_host_checks_v01_20260904\p3_pytest_tmp' 'tests/paper2_figure2/test_runtime_smoke_v01.py::test_host_finalization_is_windows_safe_without_setitimer' 'tests/paper2_figure2/test_runtime_smoke_v01.py::test_assignment_failure_never_releases_worker_to_touch_the_run_root' 'tests/paper2_figure2/test_runtime_smoke_v01.py::test_host_final_worker_normal_wait_preserves_the_full_parent_tail' 'tests/paper2_figure2/test_runtime_smoke_v01.py::test_bounded_readback_timeout_revokes_access_and_preserves_package_bytes' 'tests/paper2_figure2/test_runtime_smoke_v01.py::test_readback_worker_imports_frozen_source_without_pytest_path_injection' 'tests/paper2_figure2/test_runtime_smoke_v01.py::test_real_slow_readback_is_reaped_inside_five_seconds_without_package_writes' 'tests/paper2_figure2/test_runtime_smoke_v01.py::test_host_final_worker_timeout_uses_3_3_4_recovery_and_returns_nonzero' 'tests/paper2_figure2/test_runtime_smoke_v01.py::test_real_worker_boundary_is_terminated_within_the_frozen_parent_tail' 'tests/paper2_figure2/test_runtime_smoke_v01.py::test_unreaped_worker_revokes_job_write_access_before_parent_returns'
```

结果：退出码 `1`，收集阶段
`ModuleNotFoundError: No module named 'basix'`，`1 error in 1.13s`；命令壁钟 `10.577s`，
9 个节点均未收集。直接原因是该文件顶层导入 `paper2_hybrid.model`，而后者导入 `basix.ufl`。

依 fail-closed 规则在此停止。未修改 `test_runtime_smoke_v01.py` 或任何其他代码/测试；未运行
Docker、P5、FEniCSx solver 或 GPU。`test_runtime_smoke_v01.py` SHA-256 为
`b693e419ff93624b7f1014b6e15cb17aead303db0b6ef922cd11ad5162707311`，本轮未变。

## 9. 当前证据边界

Source-lock 修复已由定点节点与完整 P2 验证，P1 也通过；但 P3 没有形成任何节点通过证据。
正式 `results/paper2_figure2` 与 implementation lock 仍不存在，Git index 条目为 `0`。下一步
必须独立评审 P3 的依赖边界，未获授权前不得改第二个测试文件或继续后续门。

## 10. 路线 B 执行前计划与原 SHA

人类继续执行授权批准路线 B。本轮唯一代码/测试写入路径为
`tests/paper2_figure2/test_runtime_smoke_v01.py`；原 SHA-256 为
`b693e419ff93624b7f1014b6e15cb17aead303db0b6ef922cd11ad5162707311`，`91128 bytes`，
`2518 lines`。

精确修改计划：

1. 移除模块级 `paper2_hybrid.model`、`paper2_hybrid.numerics`、
   `paper2_figure2.manufactured` 与 `paper2_figure2.observables` 导入；
2. 在实际使用这些符号的 8 个 FEM 测试中分别局部导入：
   `test_frozen_load_helper_signature_and_periodic_nodes`、
   `test_second_cycle_extraction_and_first_cycle_sidecar_parity`、
   `test_raw_endpoint_shape_and_time_faults_fail_with_frozen_typed_codes`、
   `test_production_ledger_shape_fault_maps_to_power_ledger_code`、
   `test_true_zero_rhs_compresses_into_formal_p0_without_numeric_defaults`、
   `test_force_higher_harmonic_is_measured_from_the_native_resultant`、
   `test_failure_classification_and_post_hoc_drift_are_reachable`、
   `test_missing_solver_assurance_field_never_defaults_to_zero`；
3. 不使用 `try/except ImportError`、`pytest.importorskip` 或新增 skip；不删断言、不改节点名，
   不新增测试文件，不修改 runner、生产代码、spec 或科学合同；
4. 完整 FEniCSx 环境下仍导入并使用同一原符号，仅把导入时机推迟到对应测试执行时。

第四个唯一临时根冻结为：
`E:\Temp-Projects\PRL\tmp\paper2_figure2_runtime_lazy_import_host_checks_v01_20260904`。执行顺序为
P3 九节点 collect-only、定向 P3、P1、P2；任何一步非零立即停止。CPU-only，禁 pytest cache
与 Python bytecode，不复用或清理既有临时根。

实施后 SHA-256 为
`5b85d716562be52a11c49f7954e66d1980067f2df2907f876beab6ebe3717995`，`92111 bytes`，
`2540 lines`。局部导入位于上述 8 个测试的当前起始行 `42`、`86`、`118`、`173`、`206`、
`237`、`682`、`720`；模块级四组 FEM 导入已移除。runner 与 spec SHA 分别保持
`93f1f9694e785288172e66ba59df7fbc8cdffa27575a237fc8999a0d04851d31`、
`471ef6561beedf8d70dc3d6aafa8068494091c36c2dd1473fd43bc55a02f8d93`。

## 11. 路线 B 实际执行结果

本轮只修改 `tests/paper2_figure2/test_runtime_smoke_v01.py`。模块级四组 FEM 导入已移入实际
使用它们的 8 个 FEM 测试，当前局部导入起始行分别为 `43`、`87`、`119`、`176`、`207`、
`238`、`683`、`721`。P3 九个节点、节点名称和断言未改；未增加 skip、`importorskip` 或
`try/except ImportError`。

- 原 SHA-256：`b693e419ff93624b7f1014b6e15cb17aead303db0b6ef922cd11ad5162707311`；
- 新 SHA-256：`5b85d716562be52a11c49f7954e66d1980067f2df2907f876beab6ebe3717995`；
- 新文件大小：`92111 bytes`；`2540 lines`；
- runner 与 spec SHA 保持不变。

全部命令设置 `PYTHONDONTWRITEBYTECODE=1`、`PYTHONPATH=E:\Temp-Projects\PRL\src`，使用
`python -B`、`-p no:cacheprovider` 和第四临时根。P3 节点列表与第 8.4 节冻结的 9 个 node IDs
完全相同。

1. P3 collect-only：退出码 `0`，`9 tests collected in 0.35s`；命令壁钟 `9.447s`；
2. 定向 P3：退出码 `0`，`9 passed in 6.08s`；命令壁钟 `15.231s`；
3. P1：退出码 `0`，`17 passed in 3.31s`；命令壁钟 `12.291s`；
4. P2：退出码 `0`，`40 passed in 3.69s`；命令壁钟 `13.094s`。

执行测试合计 `66 passed`；collect-only 另确认 9 个 P3 节点均可在主机环境收集。各命令均出现
CuPy 未检测到 CUDA 路径的导入警告，但没有启动 GPU，未影响返回码。没有出现计划外测试失败
或执行顺序偏差。

第四临时根为：
`E:\Temp-Projects\PRL\tmp\paper2_figure2_runtime_lazy_import_host_checks_v01_20260904`；当前保留
`p2_pytest_tmp` 与 `p3_pytest_tmp` scratch，未清理。既有三个临时根也未复用、覆盖或清理。

未运行 Docker、P5、FEniCSx solver 或 GPU；正式 `results/paper2_figure2` 与 implementation lock
仍不存在，Git index 条目为 `0`，未 staging、commit 或 push。完整 FEniCSx 环境下的全文件
运行仍未获授权，因此本轮证明的是主机 P3 隔离、P1/P2 无回归，以及局部导入保持原符号绑定；
不把它扩张为 P5 或完整 PRECHECK 通过。路线 B 执行轮次依当时写边界未修改 v02，故合同状态
仍是前次 P3 收集失败快照；该历史状态已由第 12 节获准的合同对齐所更新。

## 12. 合同对齐、P4 只读 preflight 与 P5 草案

v02 合同已对齐路线 B、最新测试 SHA 和 P1--P3 当前通过证据；此前 P2/P3 失败仍作为历史时间线
保留，不再作为当前状态。P4 使用新的唯一证据根：
`E:\Temp-Projects\PRL\tmp\paper2_figure2_p4_readonly_preflight_v01_20260904`。

P4 只执行四项只读检查：

1. Docker Server：exit `0`，wall `1.1254119 s`，Linux/amd64 Engine `29.1.3`；
2. 固定镜像：exit `0`，wall `1.1710536 s`，image ID byte-exact 匹配
   `sha256:2ae4bfbc0d9077268880faf04c72750528bee986c94ab223a2c159969bd56fa8`；
3. 预留容器名：exit `0`，wall `1.1005812 s`，stdout empty，即未占用；
4. 正式结果路径：exit `0`，wall `0.8265427 s`，仍为 `ABSENT`。

四项 wall time 合计 `4.2235894 s`；每项低于 15 秒且总计低于 60 秒。原始输出记录 SHA-256 为
`a11c3b047f91752a2266e0a8f8f59fb75230904e010581652e31173853ed25b2`。P4 裁决为
`PASS_FOR_HUMAN_REVIEW`。

P5 的精确 CPU-only 启动草案已写入 v02 合同，状态为 `DRAFT_ONLY_NOT_AUTHORIZED`。本轮没有
执行 Docker run、P5、FEniCSx solver 或 GPU；没有创建正式结果、implementation lock、staging、
commit 或 push。五个既有临时根均未复用、覆盖或清理。下一步停在人类 P5 执行授权门。

## 13. P5 Linux CPU PRECHECK 实际执行与 fail-closed 裁决

人类随后以“继续安排项目执行”窄授权 P5。执行前再次确认：冻结 image ID 完全一致；预留容器名
未占用；新的 P5 总根及子目录均不存在；正式 `results/paper2_figure2` 不存在。随后 create-only
建立：
`E:\Temp-Projects\PRL\tmp\paper2_figure2_fem_only_precheck_v02_20260904\p5`，并精确运行合同中
冻结的 11 文件、单 CPU、8 GiB、无网络、read-only rootfs、cap-drop ALL、
no-new-privileges、无 GPU、无 Docker socket、`--pull=never`、无 `--rm` 命令。

实际结果：Docker 原生 exit `2`，壁钟 `5.899583 s`，宿主 timeout 未触发。pytest 在收集
`tests/paper2_hybrid/test_fenicsx_runtime.py` 与
`tests/paper2_figure2/test_manufactured_v01.py` 时均因
`ModuleNotFoundError: No module named 'dolfinx'` 中止。JUnit 为 `tests=2`、`errors=2`、
`failures=0`、`skipped=0`；精确 Linux skip 列表为空，其他测试没有形成执行证据。

容器完整 ID 为
`0b0a6c44909d2ea8dc988d92f7d7d502a61de54a19c24399c6a3e102465e7340`，当前保持 `exited`、
exit code `2`，未被删除或重启。末次 inspect 确认 image ID 为
`sha256:2ae4bfbc0d9077268880faf04c72750528bee986c94ab223a2c159969bd56fa8`，平台
`linux/amd64`，`NanoCpus=1000000000`，内存 `8589934592` bytes，网络 `none`，read-only rootfs，
cap drop `ALL`，security opt `no-new-privileges`，auto remove `False`，GPU device requests 为
`null`；项目挂载 `RW=False`，仅 `/evidence` 挂载 `RW=True`。

执行前后 HEAD 均为 `8f240cf38cb4db38f02b776d320562058439770f`；排除 `tmp/**` 后的
source/control 状态条目数均为 `14335`，摘要 SHA-256 均为
`482fcbe546f87d57c793ee7e0428528bfa5204718b5636fe410087c14b53be7c`；正式结果根前后均不存在。
因此未观察到源码/控制面或正式结果路径漂移。

完整 P5 证据：
`tmp/paper2_figure2_fem_only_precheck_v02_20260904/p5/p5_linux_cpu_precheck_evidence_v01.md`，
SHA-256 `ba06e775716151089d51ffbe64fee26ae54c6cd795fe86495d686e4b40eb4888`；JUnit SHA-256
`98a9f82cac7deea78339420f2eaff880137c07e7b1407e569e25553ee2143fe4`。

P5 裁决为 `FAIL_CLOSED_AT_COLLECTION`，不是 `PRECHECK_FOR_REVIEW`。本轮未重试、未修改镜像/
入口/代码/测试，未运行 G0/40 endpoints、正式 solver、GPU，未创建 implementation lock 或正式
结果，未 staging、commit 或 push。当前只允许独立只读评审冻结镜像与 `python3`/FEniCSx 入口
不一致；任何修复或第二次 P5 均需新的人类授权。

## 14. P5 r02 单次重试授权与冻结差异

后续严格只读诊断只读取 r01 的 container/image inspect、logs、stdout/JUnit 与合同。镜像原
Config.Env 的 `PYTHONPATH` 为
`/usr/local/dolfinx-real/lib/python3.12/dist-packages:/usr/local/lib:`，r01 容器实际值为
`/workspace/src`；显式 `--env` 覆盖镜像模块搜索路径是当前最可能根因。镜像 Entrypoint 为
`null`、默认 Cmd 为 `/bin/bash`，不支持“显式命令绕过 Entrypoint 激活”假设。

人类批准一次最小 r02 重试。唯一命令差异冻结为：

```text
PYTHONPATH=/workspace/src:/usr/local/dolfinx-real/lib/python3.12/dist-packages:/usr/local/lib:
```

其余 image ID、11 个测试文件、CPU/内存、无网络、read-only rootfs、cap-drop ALL、
no-new-privileges、无 GPU、无 Docker socket、210/240 秒上限、无 `--rm` 与 fail-closed 条件均与
r01 一致。r02 新证据根为
`E:\Temp-Projects\PRL\tmp\paper2_figure2_fem_only_precheck_v02_r02_20260904\p5`，新容器名为
`paper2-figure2-nc-v03-r02`。执行前两者必须不存在/空闲，并复核 r01 容器和证据仍在；不得删除、
覆盖、启动或修改 r01。r02 任一失败即停止，不授权第三次重试，也不授权正式 G0/40 endpoints、
results、implementation lock、GPU、staging、commit、push 或清理。

## 15. P5 r02 实际执行与第二次 fail-closed

r02 create-only 前置门全部通过后按冻结差异执行一次。Docker 原生 exit `1`；宿主壁钟
`40.673486 s`，pytest 为 `38.52 s`，未触发 host timeout，stderr 为空。JUnit 统计为
`tests=184`、`failures=17`、`errors=0`、`skipped=2`，即 `165 passed`。

`PYTHONPATH` 修订已确认有效：DOLFINx 成功导入，14 个失败节点均进一步到达
`dolfinx.fem.form -> ffcx_jit`，随后因 read-only rootfs 下 `/root/.cache/fenics` 不可写而失败。
剩余三个失败独立于 cache：

1. `test_full_three_level_g0_is_owned_by_the_runner_not_precheck` 读取自身完整源码，同时在断言自身
   写入被禁止的 marker 字面量，构成自引用恒假断言；
2. `test_pre_holdout_environment_binds_container_and_every_authority_artifact`；
3. `test_pre_holdout_environment_rejects_a_changed_actual_container_id`。

后两个节点在各自 `tmp_path` 内没有建立正式逻辑所要求的局部 `container.cid`，均产生
`RunFailure: container cidfile is unreadable before S1`。两个 skip 分别为 Windows readback Job
boundary 与 Windows Job Object ownership 的 host-specific 节点，未观察到其他 skip。

r02 完整容器 ID 为
`0ae55f99b83b89ea2ddd655870a1bf8b4e92b5e9ed1525fc3fe1bcd730c2f168`，状态 `exited`、exit `1`、
auto remove `False`。末次 inspect 确认同一 image ID、1 CPU、8 GiB、网络 `none`、read-only
rootfs、cap drop `ALL`、no-new-privileges、GPU device requests `null`、项目挂载 `RW=False`、
仅 r02 `/evidence` 挂载 `RW=True`。r01 容器和三份 r01 证据哈希未变化。

执行后、治理记录更新前，HEAD、index、排除 `tmp/**` 的 source/control 状态条目数与摘要、合同/
执行记录哈希以及正式结果根状态均与执行前一致。完整 r02 证据位于：
`tmp/paper2_figure2_fem_only_precheck_v02_r02_20260904/p5/p5_linux_cpu_precheck_r02_evidence_v01.md`，
SHA-256 `9bfe96ae4c461c06cf0c54184ffae2265c8f4ce2d7463a3860087f214badb82a`；JUnit SHA-256 为
`10c9cf9e97fe485c26ce356d76f8854ef492d682aea8acab4c8d507db5cf722a`。

r02 裁决为 `FAIL_CLOSED_AFTER_TEST_EXECUTION`，不是 `PRECHECK_FOR_REVIEW`。依授权不进行第三次
重试，不修改 cache 环境、容器策略、测试或生产代码；不运行 G0/40 endpoints、正式 solver、
GPU，不创建 implementation lock 或正式 results，不 staging/commit/push，不清理任何临时目录或
容器。下一步仅为三个失败类别的独立只读评审及新的人类修订授权门。

## 16. 两个测试夹具修复与 r03 前宿主门

人类批准只修改两个测试文件，不触及生产模型、runner、spec、判据、skip 或其他测试。

### 16.1 精确修改与 SHA

`tests/paper2_figure2/test_manufactured_v01.py`：

- 修复前 SHA-256：`5945cbf3b9a2686d298115e5a24602c50a4f0e6a09f6f0e751e4a087ad985311`；
- 修复后 SHA-256：`80f72467b4f89c4c04e6af7fe764b8d46c4ba539c7f48b3d7cc0b7d11cf6ed71`；
- 修复后 `6690 bytes`、`165 lines`；
- 唯一修改是把连续 `@pytest.mark.parametrize("spatial_level"` 字面量拆为运行时拼接；
- 修复后连续 marker 计数 `0`，`run_g0_for_system(system)` 调用计数仍为 `1`。

`tests/paper2_figure2/test_runtime_smoke_v01.py`：

- 修复前 SHA-256：`5b85d716562be52a11c49f7954e66d1980067f2df2907f876beab6ebe3717995`；
- 修复后 SHA-256：`4d836e3c2310bda3bb3ba0db08c5d8e22bbeda378358cad74dd789d8f0b14555`；
- 修复后 `92266 bytes`、`2542 lines`；
- 仅在两个 pre-holdout 测试的 `tmp_path` 各新增一个 create-only `container.cid`：首个为 a/a
  合法基线，第二个为 b/b 合法基线；后者仍由既有 c/b 变化触发 code `61`。

runner 与 spec SHA-256 分别保持
`93f1f9694e785288172e66ba59df7fbc8cdffa27575a237fc8999a0d04851d31`、
`471ef6561beedf8d70dc3d6aafa8068494091c36c2dd1473fd43bc55a02f8d93`。

### 16.2 宿主串行回归

唯一宿主临时根为
`E:\Temp-Projects\PRL\tmp\paper2_figure2_r03_fixture_host_checks_v01_20260904`，执行前不存在并以
create-only 建立，当前保留且未清理。所有命令均设置 `PYTHONDONTWRITEBYTECODE=1`、项目 `src`
为 `PYTHONPATH`，使用 `python -B`、`-p no:cacheprovider` 与独立 `--basetemp`。

1. 两个 cidfile 定向节点：exit `0`，`2 passed in 1.21s`，wall `10.084700 s`；
2. P1：exit `0`，`17 passed in 3.62s`，wall `12.511797 s`；
3. P2：exit `0`，`40 passed in 3.27s`，wall `12.033569 s`；
4. P3：exit `0`，`9 passed in 6.13s`，wall `14.833120 s`。

四门合计 `68 passed`。CuPy 在每门提示未检测到 CUDA 路径，但未启动 GPU，返回码均为 `0`。

### 16.3 r03 冻结入口与当前停止点

r03 保留 r02 的完整 `PYTHONPATH`，新增 `XDG_CACHE_HOME=/tmp`，并将 `/tmp` tmpfs 从 `noexec`
改为 `exec`，使 DOLFINx 默认 JIT cache `/tmp/fenics` 可编译并加载扩展模块且不写仓库。除此之外
image ID、11 个测试文件、1 CPU、8 GiB、无网络、read-only rootfs、cap-drop ALL、
no-new-privileges、无 GPU/socket、210/240 秒上限与禁止 `--rm` 均不变。

新证据根冻结为
`E:\Temp-Projects\PRL\tmp\paper2_figure2_fem_only_precheck_v02_r03_20260904\p5`，新容器名为
`paper2-figure2-nc-v03-r03`。执行前必须复核新根不存在、新名空闲、image ID 匹配及 r01/r02 容器/
证据未变；只有全部通过才可执行一次。任何失败、unexpected skip、timeout 或漂移立即停止，不再
自动重试。仍不授权正式 G0/40 endpoints、results、implementation lock、GPU、staging、commit、
push 或清理。

## 17. P5 r03 实际执行与 PRECHECK 裁决

r03 create-only 前置门全部通过：新根不存在、新容器名空闲、image ID 匹配，正式结果根不存在，
HEAD/index/source-control 摘要与冻结值一致，r01/r02 容器状态及六份既有证据 SHA-256 均未变。
随后只 create-only 建立 r03 P5 根并运行一次冻结命令。

实际结果：Docker exit `0`，宿主 wall `56.970658 s`，pytest `54.48 s`，host timeout `False`，
stderr 为空。JUnit 为 `tests=184`、`failures=0`、`errors=0`、`skipped=2`，即 `182 passed`。
精确 skip 为：

1. `test_real_slow_readback_is_reaped_inside_five_seconds_without_package_writes`：
   `Windows readback Job boundary is host-specific`；
2. `test_real_worker_boundary_is_terminated_within_the_frozen_parent_tail`：
   `Windows Job Object ownership is host-specific`。

没有其他 skip。JUnit SHA-256 为
`1005a63d60f5d92cb942f8527080dda2d96d82867232832cc79f85ab601690ba`，cidfile SHA-256 为
`7be05aa87d790cab82080d64fb1ca8b516145914046175eb5cb407cec4c81e64`。

r03 完整容器 ID 为
`3561fcb66d0c2e389e7735aac13bb43e2aa77daed258e7da95520dc23a37cc77`，状态 `exited`、exit `0`、
auto remove `False`。末次 inspect 确认冻结 image ID、1 CPU、8 GiB、网络 `none`、read-only rootfs、
cap drop `ALL`、no-new-privileges、GPU device requests `null`、项目挂载 `RW=False`，仅 r03
`/evidence` 挂载 `RW=True`；`XDG_CACHE_HOME=/tmp`，`/tmp` 为受限 `exec` tmpfs。

执行后、治理记录更新前，合同、执行记录、两个测试、runner、spec SHA-256 与执行前一致；HEAD、
index、排除 `tmp/**` 的 source/control 状态摘要、正式结果根及 r01/r02 容器/证据均无漂移。

完整 r03 证据位于
`tmp/paper2_figure2_fem_only_precheck_v02_r03_20260904/p5/p5_linux_cpu_precheck_r03_evidence_v01.md`，
SHA-256 `493e3923564a05ed1c430cdbd2fea02ca3bce1d64ca766517cb2a5f9519ef3b5`。

本轮裁决为 `P5_R03_PRECHECK_PASS_FOR_HUMAN_REVIEW`。它不自动授权正式 G0/40 endpoints、
implementation lock、正式 results、Figure 2 或论文科学结论。本轮未执行上述正式工作，未启动
GPU，未 staging/commit/push，未清理任何临时目录或容器。当前停止在人类 P5 r03 接受门。
