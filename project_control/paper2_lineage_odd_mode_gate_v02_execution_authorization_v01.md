---
authorization_id: PAPER2-LINEAGE-ODD-MODE-GATE-v02-AUTH-v01
status: consumed_failed_closed
authorized_at: 2026-09-09
attempts_consumed: 1
---

# Paper 2 分裂奇模态机械门 v02 执行授权

用户在 2026-09-09 明确要求执行已经归档的专家方案。本授权据此允许在运行时预检通过后进行一次 P1 CPU 正式尝试。

- base commit: `b45650a9e370be138a70acf305b6c3a21e6a7ed2`;
- runner：`scripts/run_paper2_lineage_odd_mode_gate_v02.py`；
- runner SHA256：`54f07dfdb1b51286c129ec41404e31945492532e1346fc5728893b06b17f752a`；
- host wrapper SHA256：`4a4483ad7cc35d940726c269175e36e903cb2654d026085e3ff92e8bc9d30dae`；
- result：`results/paper2_lineage_odd_mode_gate/v02_20260909/summary.json`，create-only；
- resources：1 CPU、8 GiB、0 GPU、禁网、只读根与只读项目挂载，唯一结果目录可写；
- limits：20 次分解、24 RHS、累计线性代数≤30 s、任一调用≤30 s、runner≤60 s；
- external watchdog attestation：`host-60s-v01`；
- 最终状态：Docker Desktop 恢复后已启动唯一正式尝试；该尝试在首个 S2 离散前因只读 `/root/.cache` 失败，`attempts_consumed=1`，科学状态 `not_evaluable`。

恢复后仍须逐项核对基线、关键源哈希、镜像 ID、资源门和结果路径；任一失败则停止，不消耗或伪装成科学结果。正式尝试一旦启动，无论成功、失败或超时均计一次，不自动重试。

## 授权消耗记录

- 启动日期：2026-09-09；
- 容器：`prl-paper2-lineage-odd-mode-gate-v02-20260909`，退出码 1，保留为证据；
- 结果：`results/paper2_lineage_odd_mode_gate/v02_20260909/summary.json`；
- 结果 SHA256：`b2202f295d3521741523c00902e965d3622a2fad41ef2180c0618c3348cc4cf3`；
- 执行：`FAILED_CLOSED`；科学解释：`NOT_EVALUABLE_DUE_TO_EXECUTION_FAILURE`；
- 账本：0/20 分解、0/24 RHS、0 s 线性代数，总墙钟 3.937876581 s；
- 失败：`OSError: [Errno 30] Read-only file system: '/root/.cache'`；
- 本授权已终止，不允许据此重试、生成 v03、进入 P2/P3 或改变科学阈值。
