---
document_id: PRL-REPOSITORY-CLEANUP-MASTER-CONTRACT-V01
status: batch04_candidate03_deletion_passed_candidate02_application_migration_not_run
recorded_at: 2026-09-14
scientific_execution: paused
deletion_authority: batch04_candidate03_consumed_none_for_next_batch
---

# PRL 全面清理与防膨胀总合同 v01

## 已冻结决定

- 唯一活动科研主线为受控 SimuCell3D 心肌→心内膜→ECM 三层模型；旧 Hybrid、Route H、Paper2/FEM 不再要求保持可运行。
- 历史采用精选证据后永久清理；不建立全仓复制或另一份完整历史压缩包。
- 最终建立本地精简 Git 新基线；不推送、不强推、不修改远端历史。
- 清理后目标不超过 2 GiB；整个项目硬上限 3 GiB、预警线 2.4 GiB；单科研阶段默认 256 MiB，停止保全至少预留 64 MiB。
- 达到预算时停止新运行并生成清理候选，不自动删除科学证据。

## 六批门禁

1. 完整盘点、分类和哈希；
2. 可重建缓存、构建与明确临时烟测；
3. 旧路线及结果的精选证据；
4. 当前代码依赖解耦和统一入口；
5. 本地精简 Git 新基线；
6. 导航、行为、数据、停止和空间总验收。

每批先交付准确绝对路径、字节数、依赖、风险与预期影响；取得该批明确确认后才执行。确认只覆盖当次列出的路径；新增路径必须另行确认。所有目标先解析到工作区内并检查目录链接、Git 跟踪状态和唯一成果。不得使用宽泛路径或通配符执行清理。

当前 Batch 1、Batch 2 与 Batch 3 均完成。用户在首次删除环境阻断后另行授权，仅对 Batch 2 同一30路径使用`System.IO.Directory.Delete`；最终30/30成功删除。Batch 3A 与 3B 也分别按各自精确授权完成。清理期间不启动新的科研阶段、GPU、外部归档、虚拟盘或服务。

## 证据保留原则

始终保留用户原始数据、外部专家原件、唯一稿件/图件、许可证和来源；保留当前主线必要成功证据与接触穿透、网格退化、体积失控等关键失败证据。哈希不替代原始数据。旧合同和原裁决不改写；后续用独立映射记录保留、裁减和失效链接。

当前活动构建 `E:\Temp-Projects\PRL\b\z1m0a` 保留到代码解耦、重建和行为对照完成。`external/simucell3d` 的源码、BSD-3许可证及受控修改来源不进入第2批删除。

## 当前状态

- Batch 1：`passed`，见 [完整分类表](repository_cleanup_batch01_inventory_v01.md)。
- Batch 2：`passed`，30/30路径、4,338文件、287,147,295 bytes已删除；首次阻断保留在[v01](repository_cleanup_batch02_execution_v01.md)，最终完成见[v02](repository_cleanup_batch02_execution_v02.md)。
- Batch 3A：`passed`。169个精选文件、55,720,718 bytes已迁入项目内证据区并逐项验收；19个旧Hybrid、Route H、Paper2、NCS/FEM结果目录、14,089文件、1,640,809,991 bytes已永久删除，净释放1,585,089,273 bytes。见[执行记录](repository_cleanup_batch03a_execution_v01.md)和[退役映射](repository_cleanup_retired_path_map_v01.md)。
- Batch 3B：`passed`。按[精确提案](repository_cleanup_batch03b_z1_proposal_v01.md)删除42个被取代Z1结果目录和3个本轮缓存目录，共45路径、1,275文件、490,593,270 bytes；13个保留Z1包、当前结果/来源哈希及13项无缓存回归通过。见[执行记录](repository_cleanup_batch03b_execution_v01.md)和[退役映射](repository_cleanup_retired_path_map_v01.md)。本批授权已经消费。
- Batch 4：候选3[退出前安全切片](repository_cleanup_batch04_candidate03_exit_safe_slice_execution_v01.md)及[永久删除](repository_cleanup_batch04_candidate03_deletion_execution_v01.md)均已`passed`。16个退役路线源码及包装、369,160 bytes在精选证据区保持32/32身份一致；冻结的8目录＋30文件共38路径、61文件、1,541,224 bytes已永久删除，范围外Git变化为0。默认setuptools仅发现`prl`/`prl.verification`，默认pytest和显式quick均19/19通过。本批授权已经消费。候选2应用迁移仍为`not_run`；存储门仍`blocked`，未改变力学方程。
- Batch 5–6：`not_run`。
