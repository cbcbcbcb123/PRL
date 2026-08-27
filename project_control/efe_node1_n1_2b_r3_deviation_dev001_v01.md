---
deviation_id: DEV-EFE-NODE1-N1-2B-R3-001-JSON-BOOL-SERIALIZATION
status: recorded_and_repaired
recorded_at: 2026-08-20
related_plan: project_control/efe_node1_n1_2b_r3_transactional_cycle_plan_v01.md
affected_run: results/hybrid/efe_node1_n1_2b_r3_transactional_cycle_v01_20260820
---

# R3 DEV-001：父记录 JSON 布尔序列化失败

## Observation

首次 r3 正式运行的 cycle 3 step 1 worker 和父进程物理复核均已通过，父进程
随后 create-only 创建了该运行目录中的 `accepted_step_001.npz`。在写
`transaction_summary.json` 时，三个相位比较值和两个 worker 一致性比较值
仍为 NumPy `bool_`，标准 JSON encoder 因此抛出类型错误，父 driver 退出码
为 1。

## Scientific impact

- 不是求解器、固定点或物理门失败；
- 接受检查点只存在于这次已中止的 v01 运行目录；
- v01 没有根级 summary、完整 transaction ledger 或周期证据，不能用于
  r3 科学结论；
- 原 cycle 2 输入未被修改。

## Repair and restart rule

将所有 `np.isclose` 结果显式转换为 Python `bool`，重新运行聚焦测试和 Ruff。
不覆盖、不拼接、不继续 v01；保留其容器和全部文件作为偏差证据，并使用新的
v02 结果目录从原 cycle 2 末态完整重启 cycle 3–4。该修复不改变模型、算法、
门限、输入或批准科学范围。
