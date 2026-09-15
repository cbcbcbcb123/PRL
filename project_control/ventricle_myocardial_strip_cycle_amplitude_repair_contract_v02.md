# Z1-MYO-STRIP-CYCLE-AMP-A 定向收敛修复合同 v02

- 日期：2026-09-13
- 状态：`authorized_targeted_repair_by_current_test_scope`
- 基础正式包：`results/ventricle_z1/z1_myo_strip_cycle_amp_v01_20260913`
- 新建修复包：`results/ventricle_z1/z1_myo_strip_cycle_amp_repair_v02_20260913`

## v01 冻结失败

六条轨迹均正常完成。独立复核仅发现两个失败门，且都属于 `CENTER_EPS100`：

- `CENTER_EPS100_SAVED_RESIDUAL = 0.0013431656543663616 > 0.001`；
- `CENTER_EPS100_RECOVERY = 0.11740362682002109 > 0.10`。

在 `phi=0.875` 的 2000 步定相位松弛中，自由节点最大力由 `0.2065` 量级持续下降，在最后 1000 步从 `0.00254` 降至 `0.00134`；在 `phi=1` 的保持中同样持续下降至 `0.00112`。体积、网格、夹持、功耗、链接、幅度单调性和 5 细胞大于 1 细胞等其余门全部通过。该模式符合“定相位松弛不足”的预登记修复条件，不是发散或物理门槛失败。

## 唯一允许的修复

1. 只重算 `CENTER_EPS100`；
2. 每相位定值松弛由 2000 增至 3000 步；
3. 保持可执行文件、输入网格、`dt=0.02`、预平衡 1000 步、每段加载 50 步、材料、主动幅度、黏附、夹持和全部门限不变；
4. v01 四条新轨迹及其失败 verdict 原样保留；2% 和 5% 的 CENTER/SYNC 以及 10% SYNC 只按哈希引用，不复制、不重算；
5. v02 重新生成全部六工况的组合静态图和三张 9 状态 GIF，使 `CENTER_EPS100` 面板明确来自修复轨迹。

## 组合裁决

只有 v02 修复轨迹通过原数值门，且用它替换 `CENTER_EPS100` 后，v01 冻结的全部逐工况门、幅度单调门和 SYNC 大于 CENTER 门仍全部通过，才可裁决为 `passed_synthetic_activation_count_amplitude_response`。不得放宽 `1e-3` 或 10% 恢复门；实验比较仍为 `qualitative_consistency_only`，生物学验证仍为 `blocked_data`。
