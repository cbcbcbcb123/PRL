---
document_id: PRL-VENTRICLE-STAGE-CONTRACTS-V03-ADOPTION-V01
status: passed
recorded_at: 2026-09-11
decision_scope: route_adoption_framework_setup_and_confirmed_cleanup
stage_execution_status: not_run
cleanup_execution_status: passed
---

# 三维细胞分辨心室 v03 阶段合同采纳记录

## 当前决定

用户于 2026-09-11 指定最新计划并要求从简单、整洁的框架重新开始项目。项目据此把 [v03 阶段合同包](ventricle_stage_contracts_v03/00_README_START_HERE.md) 设为新的前向执行主线；默认入口为 Z0，并严格一次只执行一个阶段或子门。

该决定只取代 2026-09-10 NCS 路线的**后续执行优先级**。既有 NCS-M1 PASS、旧 P1 `NOT_RESOLVED`、历史失败包、原始数据、用户修改和版本化合同仍是有效历史证据，不因“重新开始”而被改写为未发生、无效或可任意删除。

## 输入包与完整性

- 用户消息中的分层路径未在本机出现；实际定位到的目录为 `C:\Users\chenb\Desktop\PRL_Codex_Stage_Contracts_v03`。
- 源包 `SHA256SUMS.txt` 的 SHA-256 为 `4751236e3d5709acee5287f3b05775c3e67b4fa55e502f95f1e71981e694922e`。
- `SHA256SUMS.txt` 登记的 34 个文件全部存在且哈希匹配；源目录共 35 个文件（含校验表本身）。
- 35 个文件已原样复制到 `E:\Temp-Projects\PRL\project_control\ventricle_stage_contracts_v03`，复制后逐文件 SHA-256 与源包一致。
- 桌面的源目录及同名 ZIP 未修改、未删除。

合同包是执行计划，不是结果。包内 `document_qa.json` 只证明文档完整性；全部 Z 阶段计算状态继续为 `NOT_RUN`。

## 新主线的最小框架

1. `START_HERE.md`、`project_control/CURRENT_STATUS.md` 和项目驾驶舱作为唯一导航入口。
2. `project_control/ventricle_stage_contracts_v03/` 保存冻结的 v03 公共合同、阶段合同、模板、来源副本和哈希。
3. 后续实际结果只进入阶段独立、create-only 的运行目录；不得把合同、临时缓存或历史结果改名冒充新阶段结果。
4. 第一科学阶段仅为 Z0：资料、唯一内核、依赖、静态几何、离线查看器和 Z1 合同审计。当前尚未执行 Z0，也未授权或运行 Z1、主动收缩、CFD、FSI、泵血、细胞事件或 ECM 记忆。

## 当前现场与边界

- PRL 根目录：`E:\Temp-Projects\PRL`；分支 `codex/simucell3d-hybrid-feasibility`；审计时 HEAD `b45650a9e370be138a70acf305b6c3a21e6a7ed2`。
- 整理前工作树已有 3 个已跟踪修改和 14,913 个未跟踪文件；本次不得把它们一概视为 Codex 临时产物。
- v03 所称唯一 `muse_dcm` 的当前候选位置是 `E:\MeshCell3D\code\muse_dcm`，MeshCell3D HEAD 为 `fa21321b80a371f107afd398f93d7f69508e20c6`。这里只确认路径存在；版本、导入入口和适用能力仍须由 Z0 核验，状态为 `available_unverified`。
- PRL 内的 `external/simucell3d/` 是已跟踪的历史内核/依赖及证据链组成部分。是否从新主线退役必须在 Z0 完成依赖映射后另立决定，不能因名称不同直接删除。
- 未启动 GPU、Docker、求解器或外部下载；未安装或升级软件；未提交、推送或发布。

## 删除门

用户已明确回复“确认删除清单 A 的 14 个路径”。[清理审计](ventricle_v03_workspace_cleanup_audit_v01.md) 中 14 个绝对路径已全部删除并完成删除后核验；清理授权至此消费完毕。`results/`、`project_control/`、`planning/`、`plan/`、`data/`、`02_图表/`、`artifacts/`、`figures/`、`tmp/`、`.git/` 和已跟踪源码未被本次清理删除。

## 下一最小切片

工作区清理已完成。下一最小切片是只执行 Z0；Z0 当前仍为 `NOT_RUN`，本轮确认不授权 Z0，也不自动进入 Z1。
