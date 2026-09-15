# PRL 心室路线 Z1 v02 执行授权记录 v01

- 决定时间：2026-09-11 11:02（Asia/Shanghai）
- 授权来源：用户在确认“球形基准 + 长轴心肌 + 扁平心内膜”Z1 方案后明确回复“同意，开始”。
- 基础合同：`plan/active/PRL_Codex_Stage_Contracts_v03/stages/Z1_PASSIVE_SINGLE_AND_DOUBLE_CELL.md`
- 最新几何决定：`project_control/ventricle_cell_geometry_strategy_decision_v02.md`
- 本次允许阶段：Z1a–Z1d 被动单/双细胞验证及其必需实现、测试、图件、离线报告和独立复核。
- 本次停止点：提交 Z1 状态并停在 Z2 前；不得自动执行 Z2 或任何后续阶段。
- 计算设备：CPU，最多 4 线程；不启动 GPU。
- 运行预算：预检单例不超过 120 s，预检累计不超过 600 s；本轮 Z1 累计墙钟不超过 20 min，超限保存证据并停止。
- 工作区：所有新文件只写入 `E:\Temp-Projects\PRL`；只读使用 `E:\MeshCell3D\code\muse_dcm` 2.1.0，不在外部仓库写文件。
- 禁止项：不得删除既有文件，不安装/升级软件，不下载外部数据，不改变权限，不提交、推送或发布。
- 输出根目录：`results/ventricle_z1/v01_20260911/`（create-only）。

## 首要停止门

正式载荷前必须审计唯一内核的压力、表面张力、面积弹性、弯曲、阻尼和接触路径。若无法从实际实现导出或独立重建与节点力功共轭的能量分项，或合成长轴/扁平参考态缺少保持其形态所需的参考构型语义，则记录 `blocked` 证据并停止正式 Z1 动力学，不用替代模型制造通过。
