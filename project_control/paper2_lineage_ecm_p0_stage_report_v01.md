---
report_id: PAPER2-LINEAGE-ECM-P0-REPORT-v01
status: passed
reported_at: 2026-09-09
next_stage: P1_blocked_runtime_not_run
---

# Paper 2 谱系—ECM P0 阶段报告 v01

## 结论

P0 `passed`。专家指出的裁决重叠、任意混合纵深核、单次/总时限边界和失败证据缺口均有对应修订与聚焦行为测试。生产物理源、v01 runner、用户已有修改和历史结果均未改动。

P1 当前为 `blocked`，科学执行为 `not_run`：Docker Desktop 状态无法取得，`com.docker.service` 为 `Stopped/Manual`，当前权限无法启动。未创建 `results/paper2_lineage_odd_mode_gate/v02_20260909`，未调用 FEM，正式尝试次数仍为 0。

## P0 交付

- 冻结 runner：`scripts/run_paper2_lineage_odd_mode_gate_v02.py`，SHA256 `54f07dfdb1b51286c129ec41404e31945492532e1346fc5728893b06b17f752a`；
- 宿主监督器：`scripts/run_paper2_lineage_odd_mode_gate_v02_host.ps1`，SHA256 `4a4483ad7cc35d940726c269175e36e903cb2654d026085e3ff92e8bc9d30dae`；
- 行为/静态合同测试：`tests/test_paper2_lineage_odd_mode_gate_v02.py`；8/8 `PASS`，约 1.90 s；
- 互斥状态新增 `RESOLVED_SMALL_GAIN`，并收紧条件 GO 只允许“全带秩已解析、仅纵深符号改变”；
- 稳健 GO 新增完整 `R[w]=Σw_bR_b` 保守证书；负例证明逐带 det 非零不保证混合 det 非零；
- 每个线性代数调用记录 30 s 门，runner 要求宿主 60 s watchdog 见证；
- 离散结果在每项完成后即挂入 summary；非有限值保留字段路径和显式 marker，不置零；
- 专家原件及附件按原哈希复制到 `plan/active/EXP-20260909-001-paper2-lineage-ecm/`，源 HTML SHA256 与原包一致。

## P1 预检证据

1. `HEAD=b45650a9e370be138a70acf305b6c3a21e6a7ed2`，与冻结基线一致；
2. v02 结果目录不存在，create-only 条件仍满足；
3. `docker desktop status` 先报告 `stopped`，后报告无法取得状态；
4. 命令行启动/重启请求均未使后端就绪；
5. `Start-Service com.docker.service` 因当前权限无法打开服务而失败；
6. 因容器运行时预检未通过，没有运行 `docker run`，没有消耗唯一正式 P1 尝试。

## 证据层级

- P0 实现与聚焦测试：`passed`；
- P1 FEM 数值门：`not_run`；
- H0 机械可见性：`unknown`；
- H1 真实分裂因果：`not_run`；
- H2 ECM 选择性放大/存储：`not_run`；
- 生物真实性与投稿成熟度：`unknown`。

## 恢复条件

用户在有权限的桌面会话中使 Docker Desktop 正常运行后，重新执行只读镜像/资源预检即可；若基线、关键源哈希、runner 哈希和 create-only 路径仍匹配，可使用已保留的一次 P1 授权。不得在运行时未就绪时改用新依赖、放宽资源边界或创建 v03。
