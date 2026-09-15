---
contract_id: PAPER2-LINEAGE-ODD-MODE-GATE-v02
status: accepted_for_one_formal_attempt
accepted_at: 2026-09-09
base_commit: b45650a9e370be138a70acf305b6c3a21e6a7ed2
source_guidance: EXP-20260909-001-paper2-lineage-ecm
---

# Paper 2 分裂奇模态机械门执行合同 v02

本合同冻结 `project_control/paper2_lineage_ecm_active_execution_plan_v01.md` 的 P0/P1 范围。v01 runner 与 v01 结果路径保持不变；唯一正式尝试使用：

- `scripts/run_paper2_lineage_odd_mode_gate_v02.py`；
- `scripts/run_paper2_lineage_odd_mode_gate_v02_host.ps1`（宿主独立 60 s watchdog）；
- `results/paper2_lineage_odd_mode_gate/v02_20260909/summary.json`。

二者 create-only；若路径冲突、基线或关键源哈希漂移则 fail-closed，不生成 v03。

冻结物理与离散：A1、H=0.3、De=0.2、T128、activation_peak=0.1；S2/S3×两种严格镜像网格；八个 `z/h` 带；`m={1e-4,5e-5}`；20 次分解、24 RHS。禁止 S4、参数扫描、真实 DCM 分裂、反馈、流体、三维、非线性和 GPU。

资源：`dolfinx/dolfinx:v0.11.0` 及既有固定 image ID；1 CPU、8 GiB、禁网、只读根、只读项目挂载、唯一结果目录可写；累计线性代数≤30 s，任一调用≤30 s，总 runner≤60 s。宿主独立 watchdog 强制总墙钟；Python signal 只是补充。

裁决互斥顺序和完整 `R[w]` 保守证书以活动计划 P0 冻结条款及 v02 聚焦行为测试为准。稳健 GO 必须同时通过每带门与 `A_min |g|_min > |a|_max |B|_max`；`RESOLVED_SMALL_GAIN` 不释放反馈；数值未解析不得解释为物理纵深歧义。

正式运行失败、超时、路径/资源预检失败或数值未解析后停止，不自动重试。P1 只涉及 H0；H1、H2、生物验证和投稿成熟度保持 `not_run/unknown`。
