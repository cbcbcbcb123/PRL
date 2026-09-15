# Z1-MYO-STRIP-L5-A 定向收敛修复合同 v02

- 日期：2026-09-13
- 状态：`authorized_targeted_repair`
- 基础正式包：`results/ventricle_z1/z1_myo_strip_l5_a_v01_20260913`
- 唯一失败门禁：`CENTER_NO_LINK_SAVED_RESIDUAL = 0.00107093370889369 > 0.001`

## 根因证据

在 `phi=0.375` 的 2000 步固定相位松弛中，最大自由节点力从 `2.3437e-2` 单调降至 `1.0721e-3`。体积、网格、夹持、功耗和机制门禁均通过。因此当前失败归类为阴性对照松弛不足，而非模型发散或界面力学错误。

## 唯一允许的修复

- 只重跑相互独立的 `CENTER_NO_LINK` 工况；
- 保持网格、材料、形态支持、主动缩短、阻尼、步长、预平衡和加载步数不变；
- 每个固定相位松弛由 2000 步增加到 3000 步；
- 不修改 `1e-3` 收敛门槛，不修改任何机制门禁；
- `PASSIVE`、`SYNC`、`CENTER` 继续引用 v01 冻结原始结果，不重算也不复制。

## 组合判定

v02 只能在下列条件同时成立时形成 `passed_synthetic_strip_mechanics`：

1. v01 除 `CENTER_NO_LINK_SAVED_RESIDUAL` 外所有门禁原样通过；
2. v02 修复工况的全部数值门禁通过；
3. 使用 v02 的无链接反力重新计算 `NO_LINK_ABLATION` 后仍通过；
4. 所有证据路径和 SHA-256 均登记。

实验比较仍为 `qualitative_consistency_only`，生物定量验证仍为 `blocked_data`。
