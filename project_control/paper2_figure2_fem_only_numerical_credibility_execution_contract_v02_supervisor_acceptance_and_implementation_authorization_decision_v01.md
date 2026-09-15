---
decision_id: DECISION-PAPER2-FIGURE2-FEM-ONLY-EXECUTION-CONTRACT-V02-ACCEPTANCE-AND-IMPLEMENTATION-V01
status: ACCEPTED_IMPLEMENTATION_ONLY_AUTHORIZED
decided_at: 2026-09-04
decided_by: independent_supervisor
baseline_commit: c52b2de7536a055699b2e23011fa221a6f2f1019
baseline_upstream_ahead_behind: 0/0
accepted_design_contract: project_control/paper2_figure2_fem_only_numerical_credibility_contract_v03.md
accepted_design_contract_sha256: 796de6a6cfa6167e30cae592128379206709ace720d4fcbe3ae80366fb504249
accepted_execution_contract: project_control/paper2_figure2_fem_only_numerical_credibility_execution_contract_v02.md
accepted_execution_contract_sha256: 11ebd843cf23c404c920a0274b409a907e01cd1755a2a5812de1eb8bdc66e253
incorporated_execution_contract: project_control/paper2_figure2_fem_only_numerical_credibility_execution_contract_v01.md
incorporated_execution_contract_sha256: 2cbbae0f09bb966e9292a306f4c7a698952f9bf962139c772b1cfb02e4b7c070
source_review: project_control/paper2_figure2_fem_only_numerical_credibility_execution_contract_v01_supervisor_review_v01.md
source_review_sha256: 0a02656853625b52ff10b99379d7c5421e90b528fcf0a804ec33820e49edfb4d
implementation_authorized: exact_15_new_files_only
test_execution_authorized: none_this_stage
solver_execution_authorized: none
docker_execution_authorized: none
formal_r01_authorized: none
gpu_authorized: none
next_gate: implementation_candidate_independent_supervisor_review
---

# Paper 2 Figure 2 执行合同 v02 Supervisor 接受与实现授权决定 v01

## 1. 二元裁决

裁决为 **ACCEPTED**。

SHA-256 为
`11ebd843cf23c404c920a0274b409a907e01cd1755a2a5812de1eb8bdc66e253` 的执行合同 v02
规范性纳入 SHA-256 为
`2cbbae0f09bb966e9292a306f4c7a698952f9bf962139c772b1cfb02e4b7c070` 的 v01 未冲突条款，
并已关闭 v01 审阅提出的 B1–B5。两份文件按 v02 冻结的优先级共同构成唯一执行合同。

本裁决只接受未来实现与判定规则，不代表 15 个实现文件已经存在，不代表测试、Docker、
solver 或正式 r01 已运行，也不构成 Figure 2 数值通过、生理验证、EFE 机制、流体、三维/
整心房或 Nature Physics 级普适规律证据。

## 2. 独立验收结果

| 项目 | 结果 |
|---|---|
| 活跃架构 | PASS：离散心内膜链＋主动心肌 FEM＋黏弹 ECM FEM；无心肌 DCM 路线 |
| 周期与账本 | PASS：生产量只取第二周期；N 步账本由第二周期节点重算 |
| G0 零控制 | PASS：S2/S3/S4 使用 N=64 的真实 DC/谐波零 RHS；S2 复用为 formal index 0 |
| 制造与谱 | PASS：探针、seed、归一、差分步长、缩放谱、Ritz 与失败语义唯一 |
| QoI 与 floor | PASS：machine key、来源、单位、reduction、参考方向和跨层零噪声聚合唯一 |
| 牵引与功率 | PASS：只保存 ECM 侧物理力；对侧、热点和界面功率符号唯一 |
| 留出与数组 | PASS：S1 位于开发 digest 后；216 个 formal commitments 绑定最终 NPZ |
| 事务 | PASS：create-only；PASS/late FAIL/early FAIL；inventory、ledger、completion 无环 |
| 资源 | PASS：39 个动态调用＋1 个 G0 P0 复用；单 CPU、8 GiB、3600 s；无网络/GPU/socket |
| 静态完整性 | PASS：890 行、51280 bytes、无尾随空格、公式定界符配对 |

## 3. 本阶段唯一实现授权

只允许新增以下 15 个文件：

1. `src/paper2_figure2/__init__.py`
2. `src/paper2_figure2/spec.py`
3. `src/paper2_figure2/manufactured.py`
4. `src/paper2_figure2/projection.py`
5. `src/paper2_figure2/observables.py`
6. `src/paper2_figure2/adjudication.py`
7. `src/paper2_figure2/evidence.py`
8. `scripts/run_paper2_figure2_fem_only_numerical_credibility_v01.py`
9. `tests/paper2_figure2/test_spec_v01.py`
10. `tests/paper2_figure2/test_source_lock_v01.py`
11. `tests/paper2_figure2/test_projection_v01.py`
12. `tests/paper2_figure2/test_manufactured_v01.py`
13. `tests/paper2_figure2/test_adjudication_v01.py`
14. `tests/paper2_figure2/test_evidence_v01.py`
15. `tests/paper2_figure2/test_runtime_smoke_v01.py`

实现必须逐条翻译已接受合同，不得另造第二协议、第二 runner、第二 writer 或新的生产
观测量。八个 `src/paper2_hybrid` 核心文件保持字节只读；若实现需要第 16 个文件、修改
核心方程/参数/病例/阈值/DAG/schema，立即停止并返回 Supervisor Gate。

## 4. 本阶段明确不授权

- 不运行任何测试、solver、Docker、正式 r01 或结果生成；
- 不创建 `results/paper2_figure2/` 或任何结果目录；
- 不建立实现锁或宣称实现已验收；
- 不修改 Figure 1、Figure 2 v03、执行合同、CURRENT_STATUS 以外的治理历史；
- 不修改、移动、覆盖或删除既有证据；
- 不恢复心肌 DCM、identity、`paper2_m2` 生产依赖、流体、三维、整心房或参数扫描；
- 不启动 GPU，不使用网络，不执行 Git 暂存、提交或推送。

## 5. 下一门

实现者完成 15 个候选文件后必须报告逐文件字节数/SHA-256、导入关系和合同条款映射，
停在 `implementation_candidate_independent_supervisor_review`。Supervisor 先做静态源码与
测试设计复核；只有另立版本化决定后，才可运行测试或容器 smoke。正式 r01 始终需要更后
一层独立实现锁、资源预检和明确执行决定。
