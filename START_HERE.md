---
document_id: PRL-START-HERE
status: current
updated_at: 2026-09-15
organization_status: cleanup_closure_v01_active_old_git_replaced_first_commit_pending
---

# PRL 项目导航

目标是建立不依赖参考形状膜能的细胞分辨心室组织。当前双细胞接触已通过更长范围的数值检查，但尚未得到合格组织平衡形态。

## 当前仓库清理

科研阶段暂时停止，正在执行全面清理与防膨胀方案。Batch 1完整分类盘点已`passed`。Batch 2最终`passed`：30/30精确路径、4,338文件、287,147,295 bytes已删除；工作区从基线7.569 GiB降至7.310 GiB。首次环境阻断与后续单独授权的完成记录均保留。

- [清理总合同](project_control/repository_cleanup_master_contract_v01.md)
- [完整分类与哈希](project_control/repository_cleanup_batch01_inventory_v01.md)
- [Batch 2精确删除提案](project_control/repository_cleanup_batch02_deletion_proposal_v01.md)
- [Batch 2阻断执行记录](project_control/repository_cleanup_batch02_execution_v01.md)
- [Batch 2完成执行记录](project_control/repository_cleanup_batch02_execution_v02.md)

Batch 3A也已`passed`：[执行记录](project_control/repository_cleanup_batch03a_execution_v01.md)显示53.139 MiB精选证据通过169/169哈希验收，19个旧Hybrid、Route H、Paper2和NCS/FEM结果目录永久删除，净释放1.476 GiB。旧链接按[退役路径映射](project_control/repository_cleanup_retired_path_map_v01.md)解释。

Batch 3B现已`passed`：[执行记录](project_control/repository_cleanup_batch03b_execution_v01.md)显示42个被取代Z1包与3个本轮缓存共45路径、1,275文件、490,593,270 bytes已删除；13个当前/关键Z1包以及114+14项哈希保持完整，13项无缓存回归通过。删除后工作区约5.377 GiB。

Batch 4候选3[退出前安全切片](project_control/repository_cleanup_batch04_candidate03_exit_safe_slice_execution_v01.md)和[永久删除](project_control/repository_cleanup_batch04_candidate03_deletion_execution_v01.md)均已`passed`：16个退役源码及包装、369,160 bytes在精选证据区保持完整；8个递归目录和30个单文件共38路径、61文件、1,541,224 bytes已永久删除，32/32保护身份、默认pytest与显式quick 19/19通过。存储准入仍`blocked`，项目超过3 GiB。

[一次性清理收口与科学重启审批包](project_control/repository_cleanup_closure_and_science_restart_proposal_v01.md)已获精确授权。旧`.git`首次部分失败后依规停止；补充授权下9,994个剩余文件的ReadOnly位已清除，旧Git已完全删除。本地`codex/clean-baseline`已创建且无远端，首提交正在保全48项迁移前来源和当前唯一内核。其余30目标未处理，[CPU接触性能与扩展双胞合同](project_control/ventricle_contact_performance_and_extended_equilibrium_contract_v01.md)仍为`not_run`，GPU未启动。

## 当前模型与载荷

END端对端、SIDE侧邻各两个闭合三维心肌细胞，每胞194节点/384面；全部自由。皮质/体积/面积约束、恒定方向骨架、独立黏附与正间隙排斥；无参考形状膜能、永久跨隙链接或周期收缩。没有ECM、心内膜、腔压或夹持。

相同初态模板、材料和方向使细胞过于整齐。本轮保持该确定性对照，尚未添加随机几何或主动噪声。4×4整片只做了静态计时，没有推进组织形态。

![实际双胞初态](results/ventricle_z1/z1_myo_long_doublet_v01_20260914/figures/structure.png)

## 已完成与核心结果

| 项目 | 状态 | 直接结果 |
|---|---|---|
| 长程双胞数值资格 | passed | 4轨迹至算法坐标5；事件网格无穿透见证 |
| 网格与步长对照 | passed | 体积误差<=.334%，最小角>=22.516°，步长末态位移差<=.054% |
| 实际安全步长裁切 | passed | END/SIDE各7次裁切，接受状态保持正间隙 |
| 2/4/16胞静态性能测量 | passed | 16胞一次13.735秒，接触部分12.150秒 |
| 静态平衡 | failed | 末态残力约.104，高于.001门；有限时域未收敛 |
| 生物学验证/父Z1 | blocked | 尚无合格组织及实验参数标定 |

![真实逐胞形变](results/ventricle_z1/z1_myo_long_doublet_v01_20260914/figures/cell_length.png)

END每胞长轴约+6.36%，SIDE约+12.21%；这是恒定预应力下的形态重排，不是周期收缩。算法坐标不是生理时间。

## 当前主要难点与唯一下步

接触计算开销大，尚未得到静态平衡；固定拓扑的更长期质量、形态异质性与参数标定仍待验证。不能把本次未发现穿透或折叠当作普遍数学保证。

唯一下一步是用户确认已经冻结的收口审批语句。确认后按固定顺序完成C++/Python迁移、旧Git与31路径清理、独立验收；只有这些步骤和接触数值等价/性能门全部通过，才运行END/SIDE扩展双胞并输出实际结构、曲率、压力、接触牵引、残力曲线与五状态动图。不运行16胞动力学，不自动重跑。

不规则形态候选路线：统计大小/截面/端部错位与相容界面 → 区域力学差异 → 相关主动涨落。先保留规则对照，不能简单给节点加白噪声冒充生物形态。

## 图像与证据

- [完整结构、场量及五状态动图](results/ventricle_z1/z1_myo_long_doublet_v01_20260914/index.html)：实际算法坐标0/1.25/2.5/3.75/5。
- [执行报告](project_control/ventricle_myocardial_long_doublet_execution_v01.md)、[总裁决](results/ventricle_z1/z1_myo_long_doublet_v01_20260914/verdict.json)、[文献与采纳建议](docs/myocardial_shape_variability_literature_v01.md)。
- [当前权威状态](project_control/CURRENT_STATUS.md)、[驾驶舱](memory/project_cockpit/index.html)、[外部方案](plan/INDEX.md)。

当前SimuCell3D失败、原始数据和专家原件继续保留；旧Hybrid、Route H、Paper2和NCS/FEM不再完整，仅保留Batch 3A精选证据。被删除的旧路径不可恢复，不能再声称全部旧计算可复算。导航仅是状态投影，遵守[AGENTS.md](AGENTS.md)。
