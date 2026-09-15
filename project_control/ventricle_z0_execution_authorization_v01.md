# PRL 心室路线 Z0 执行授权记录 v01

- 决定时间：2026-09-11（Asia/Shanghai）
- 授权来源：用户在当前任务中明确要求“现在开始分阶段执行……先完成第一阶段内容”。
- 权威方案包：`plan/active/PRL_Codex_Stage_Contracts_v03/`
- 本次允许阶段：`Z0_ENTRY_DATA_AND_KERNEL_AUDIT`
- 本次禁止越界：不得执行 Z1 或后续阶段；不得启动 GPU；不得申请受限数据；不得下载大体积原始包；不得删除既有文件。
- 计算设备：CPU，最多 4 线程。
- 下载预算：累计不超过 256 MiB，仅获取合同要求的小文件。
- 输出根目录：`results/ventricle_z0/v01_20260911/`
- 状态边界：Z0 的 PASS 只覆盖资料审计、静态合成几何、可视化与 Z1 合同准备，不代表力学、CFD、泵血或实验验证通过。

执行前预注册见 `results/ventricle_z0/v01_20260911/preregistration.json`。本记录不授权自动执行下一阶段。
