# Z1-MYO-STRIP-DEFORMABILITY-HI-A 最终定向收敛修复合同 v03

- 日期：2026-09-13
- 基础包：`results/ventricle_z1/z1_myo_strip_high_amp_deformability_repair_v02_20260913`
- 新建包：`results/ventricle_z1/z1_myo_strip_high_amp_deformability_repair_v03_20260913`
- 执行：CPU 单线程、create-only，仅 `CENTER_EPS200`

## v02 剩余失败

v02 已使 `CENTER_EPS150` 通过原 `1e-3` 保存残差门；组合 61 门仅剩：

- `CENTER_EPS200_SAVED_RESIDUAL = 0.0010063821249926316 > 0.001`。

该值只比门限高约 0.638%。`phi=0.875` 保持的最后 1000 步中，最大自由节点力从 `0.0011538454` 降到 `0.0010065190`，比值 `0.872317`；体积、网格质量、夹持、功耗、恢复和其余全部门已通过。

## 唯一修复

1. 仅重算 `CENTER_EPS200`；
2. 每相位保持由 6000 增至 7000 步；
3. `dt=0.02`、预平衡 1000、每段加载 50、8 个相位、20% 主动参考缩短、全部材料、连接、边界和冻结门保持不变；
4. v01 与 v02 的失败结果继续保留；
5. `CENTER_EPS150` 引用 v02，`SYNC_EPS150/200` 引用 v01，两个 10% 基线继续引用原冻结轨迹，均逐文件核验哈希；
6. 这是本问题的第三次且最后一次正式/修复轮次；若仍失败，停止追加松弛并报告 `failed`。

只有组合 61/61 门通过才可给出 `passed_synthetic_isometric_high_amplitude_response`。无论通过与否，等长幅度扫描都不能单独标定细胞被动柔软度。
