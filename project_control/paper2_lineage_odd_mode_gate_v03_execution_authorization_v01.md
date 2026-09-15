---
authorization_id: PAPER2-LINEAGE-ODD-MODE-GATE-v03-AUTH-v01
status: consumed_completed_not_resolved
authorized_at: 2026-09-09
attempts_consumed: 1
---

# Paper 2 分裂奇模态机械门 v03 执行授权

## 用户授权

用户在收到 v02 的运行环境失败闭环与 v03 最小修复提案后，于 2026-09-09 明确回复“批准执行”。本记录据此授权一次 v03 P1 CPU 正式尝试。

## 冻结身份

- base commit：`b45650a9e370be138a70acf305b6c3a21e6a7ed2`；
- scientific core：`scripts/run_paper2_lineage_odd_mode_gate_v02.py`；
- scientific core SHA256：`54f07dfdb1b51286c129ec41404e31945492532e1346fc5728893b06b17f752a`；
- v03 runner：`scripts/run_paper2_lineage_odd_mode_gate_v03.py`；
- v03 runner SHA256：`d6e52b17e00d9e0ddafbaee86689917f8f2bb4755fdd3d1cbc02ba8d1cf24ed7`；
- host wrapper：`scripts/run_paper2_lineage_odd_mode_gate_v03_host.ps1`；
- host wrapper SHA256：`35a45ad3f51a652d68c162a327bc351e1b4a43cd08635c17b1b5fbfd82b366ba`；
- result：`results/paper2_lineage_odd_mode_gate/v03_20260909/summary.json`，create-only；
- container：`prl-paper2-lineage-odd-mode-gate-v03-20260909`，create-only；
- image：`dolfinx/dolfinx:v0.11.0`，ID `sha256:2ae4bfbc0d9077268880faf04c72750528bee986c94ab223a2c159969bd56fa8`。

## 唯一运行时变化与预算

- 仅新增 `/root/.cache:rw,exec,nosuid,nodev,size=536870912` 的内存 tmpfs；
- 1 CPU、8 GiB、0 GPU、禁网、只读根、只读项目，唯一结果目录可写；
- 20 次分解、24 RHS；累计线性代数≤30 s；任一调用≤30 s；runner≤60 s；
- external watchdog：`host-60s-v01`。

## 消耗与停止规则

静态/行为测试、源哈希、镜像、Docker、资源与 create-only 预检通过后启动正式容器。容器一经启动，无论完成、失败或超时均令 `attempts_consumed=1`。不得自动重试、生成 v04、改阈值、换读出、使用 GPU 或进入 P2/P3。

## 授权消耗结果

- v03 容器于 2026-09-09 启动并以退出码 0 完成，本授权已经消耗；
- 结果：`results/paper2_lineage_odd_mode_gate/v03_20260909/summary.json`；
- 结果 SHA256：`d8882a7350996a9be6c364272ca51f9eb383201599bcfed73a8129bff3fd5b2d`；
- 执行状态 `PASS`：20 次分解、24 RHS，累计线性代数 14.470801716 s，总墙钟 24.389381747 s；
- 科学分类 `NOT_RESOLVED`：6/8 个纵深带的 `g` 未通过 5% 两网格经验门；
- P2/P3 继续阻塞；不允许第二次 v03、v04、S4、改阈值或换读出。
