---
execution_id: EXE-PAPER2-M2A-V05-1-T256-RESOURCE-RETRY-V01
plan_id: PLAN-PAPER2-M2-ACTIVE-MYO-FEM-IDENTITY-V05-1-RESOURCE-RETRY
executor: Codex Executor
started_at: 2026-09-04
completed_at: 2026-09-04
status: completed_at_supervisor_gate
formal_stage_label: T256_TIME_CONVERGENCE_PASS_V05
resource_revision: v05.1
deviation_records: []
---

# Paper 2 M2A v05.1 T256 资源修复重试执行记录 v01

## 1. Approved plan reference

本执行依据：

- v05 科学合同：
  `project_control/paper2_m2_active_myocardial_fem_identity_conversion_contract_v05.md`；
- v05.1 资源修复与重试决定：
  `project_control/paper2_m2a_v05_t256_runtime_budget_repair_and_retry_decision_v01.md`；
- v05 首次失败记录：
  `project_control/paper2_m2a_v05_t256_execution_record_v01.md`；
- 持续授权：`project_control/paper2_autonomous_execution_and_chart_reporting_decision_v01.md`；
- 冻结 T64 源：`results/paper2_m2/identity_2d_v03_t64_v01_20260903/`；
- 冻结 T128 源：`results/paper2_m2/identity_2d_v04_t128_v02_20260903/`。

本次只允许把单端点运行时间门从 `30.0 s` 改为 `60.0 s`，在新 create-only
目录从第 1 个端点完整重跑 54 个 T256/D0 端点。阶段总时间、内存、科学实现、
74/54/2 个 T256 数值门及 74 个三层时间门均保持 v05 不变；完成后必须停止在
Supervisor Gate。

## 2. Commands or tools used

- 宿主执行 v05.1 协议、路径、资源门和 v03-v05.1 回归；
- 固定 `dolfinx/dolfinx:v0.11.0` CPU 容器执行完整回归；
- 固定容器从第 1 个端点正式运行：CPU 单进程、BLAS/OMP 单线程、16 GiB、禁网、
  无 GPU；
- 使用严格 JSON 解析、NPZ 数组有限值检查、SHA-256、字节数及原始记录复算执行
  独立结果包审计；
- 核对正式容器退出码、当前 Git HEAD、远端分支对齐和冻结输入哈希。

## 3. Files changed

新增：

- `src/paper2_m2/protocol_v05_1.py`；
- `scripts/run_paper2_m2_identity_2d_t256_v05_1.py`；
- `tests/paper2_m2/test_protocol_v05_1.py`；
- `tests/paper2_m2/test_t256_v05_1_resource_gate.py`；
- create-only 成功包
  `results/paper2_m2/identity_2d_v05_t256_v02_20260904/`；
- 本执行记录。

按决定更新 `project_control/CURRENT_STATUS.md`。未修改 v01-v05 冻结实现、v05 首次
失败包、T64/T128 成功包或工作树中 7 项既有无关 tracked 修改。未执行 Git
add/commit/push。

## 4. Tests or checks run

- v05.1 定向宿主测试：`6 passed in 0.84 s`；
- 最终宿主复核首次因未设置项目 `src` 导入路径而在收集阶段停止；补齐该路径后同一组
  测试为 `6 passed in 0.67 s`，属于命令环境配置而非实现失败；
- 宿主 v03-v05.1 协议、路径和资源门回归：`16 passed in 5.03 s`；
- 固定 DOLFINx CPU 容器完整回归：`32 passed in 127.66 s`；
- Python 语法编译通过；
- 正式容器 `prl-v05-1-t256-formal-20260904-01` 退出码为 `0`；
- 成功包 16 个 JSON 均可解析且数值有限；12 个动态留出 NPZ 共 360 个数组均为
  有限值；
- hash ledger 27/27 条目 SHA-256 与字节数复算一致，除 ledger 自身外无漏列文件；
- 54/54 个端点键均为 `T256/D0`，54/54 结构门通过；
- 74/74 个空间门、54/54 个周期门和 2/2 个热点门通过；
- 74 个 T64/T128/T256 记录唯一且全部通过；直接从三层原始值复算 `r_01`、`r_12`
  与冻结公式完全一致；
- 12/12 个 T128→T256 动态时间节点嵌套记录通过，最大绝对误差为 `0`；
- v05 首次失败包、v05 实现和全部冻结源的运行前后 SHA-256 保持一致；
- 当前 HEAD 与远端同名分支均为
  `13d22257a7fcefebca037cd0537e8752f52e123a`。

## 5. Deviations

无科学、实现或范围偏差。唯一变化严格为预注册资源修订：单端点预算
`30.0→60.0 s`。没有改阈值、改模型、重新标定、换求解器、使用 GPU 或跳过端点。

## 6. Blockers

无执行阻塞。原 v05 失败端点 `ID-A1__FEM__S4__T256__D0` 本次耗时
`30.62505569300265 s < 60.0 s`，同时满足全部科学门。该端点也是本次 54 个端点中的
最大耗时端点。

后续仍受 Supervisor Gate 限制：本次通过不授权正式 identity gate、M2B、S5 或任何
扩展计算。

## 7. Outputs produced

成功包：`results/paper2_m2/identity_2d_v05_t256_v02_20260904/`。

正式结果：

- 状态：`COMPLETE_AT_SUPERVISOR_GATE`；
- 决定：`T256_TIME_CONVERGENCE_PASS_V05`；
- 端点：`54/54`；
- T256 汇总门：空间 `74/74`、周期 `54/54`、热点 `2/2`；
- 三层时间门：`74/74`，标签 `THREE_LEVEL_TIME_GATE_PASS`；
- 最大 `r_12`：`0.0004150504093643955 < 0.01`，对应
  `ID-LS / DCM / S4 / total_dissipation`；
- 最大变化比：`0.2647139335152549`，对应
  `ID-C0 / DCM / S4 / peak_limited_shortening`；
- 最大直接相对残差：`2.9681468104030423e-08 < 1e-07`；
- 最大 normwise backward error：`6.799405880186699e-16 < 1e-12`；
- 最大归一化功率账本残差：`2.515595272983527e-09 < 1e-08`；
- 最大离散闭合相对误差：`2.520540448406629e-14 < 1e-10`；
- 最大端点相减旁路差：`6.729936408638804e-12`；
- 总耗时：`735.4341055739933 s < 5400 s`；
- 峰值内存：`1.1175003051757812 GiB < 16 GiB`；
- GPU：未使用。

关键 SHA-256：

- `pass_summary.json`：
  `d0d306433a8ca4ea61ad289ef7a94d7905a8383a42931c877dddd407a36ce97b`；
- `stage_T256_gate.json`：
  `38ce90532f4f2fdadfb32e73e1c6ab67b2a02578b26c9869f79c54b069ac1ff4`；
- `T64_T128_T256_time_gate.json`：
  `da862eb027374d87a9c5f63ac14bda947f4c3539f60acc5d9c2a34505ef17399`；
- `T128_T256_time_node_nesting_audit.json`：
  `d3bd62d8c090a9ce499c9bf3ee2dbe59a7a0548a1ff7c980c4d689f64247dda3`；
- `run_manifest.json`：
  `fc65096b2c51fcaaba0c8d47405a3549a191be4d73a8cabf554019437884f123`；
- `hash_ledger.json`：
  `214779763db6258e6e652c61cebc8ea821fe8f195e23940ebcf21e0efae5973f`。

v05.1 实现与测试 SHA-256：

- `protocol_v05_1.py`：
  `8997087cb5ab235e26449978e34780bc399bda867e81f86645a4386f73ef2860`；
- v05.1 T256 runner：
  `2053a35f60dca97ecc0e3d4078133f5eea5cbeed71e8bcb039edf25b1d0b7f5f`；
- `test_protocol_v05_1.py`：
  `f4724e550901822904a43f08c0bbeab40a65b2249133bd5e46ee18e2efe5dd40`；
- `test_t256_v05_1_resource_gate.py`：
  `09473a9cdf936abeef91484483b4e21fd1a72174dc31d7e3270e50a8c1e1f95e`。

## 8. Evidence boundary and stop state

本包只证明：在冻结的理想化二维体系、冻结的 D0 直接求解器、S2/S3/S4 空间层级和
预注册标量观测量上，T256 数值阶段及 T64/T128/T256 三层时间门通过。这里没有拟合
收敛阶，也没有计算 DCM-FEM identity，因此不能把结果表述为两种表示已经等价，更不能
外推为三维、生理标定或疾病机制证据。

执行已停止在 Supervisor Gate。未运行 identity gate、M2B、S5、三维、整心房、真实
几何、流体/CFD/FSI、GPU、新求解器或参数扫描。正式与测试 Docker 容器均保留为停止态，
未执行删除。
