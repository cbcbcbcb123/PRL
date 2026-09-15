---
document_id: PRL-VENTRICLE-SIMUCELL3D-TRILAYER-SHAPE-FORMATION-AUTHORIZATION-V01
status: consumed_completed
authorized_at: 2026-09-12T22:23:59+08:00
consumed_at: 2026-09-12T22:55:43+08:00
stage: Z1-TF2-B
contract: project_control/ventricle_simucell3d_trilayer_shape_formation_contract_v01.md
contract_sha256: 9a56df030279595036f43a6a169adb7710e2a4ba2fcbafdc64459dbe3db72c2b
formal_attempt_limit: 1
---

# Z1-TF2-B 一次性执行授权 v01

> 2026-09-12T22:55:43+08:00：正式 14 工况矩阵开始，唯一一次正式执行授权已消费；后续不得在同一路径重跑或覆盖。

> 2026-09-12：矩阵完成调度，2 条完整、12 条触发冻结数值停止门；最终裁决见 `ventricle_simucell3d_trilayer_shape_formation_execution_record_v01.md`。

## 用户授权

用户于 2026-09-12 明确回复：

> `确认冻结并执行 Z1-TF2-B`

该回复批准并冻结 [Z1-TF2-B 合同](ventricle_simucell3d_trilayer_shape_formation_contract_v01.md) 中的模型、FORMATION/MAINTENANCE 双试验臂、七工况矩阵、形态与数值门、结果路径、图片要求和资源上限。

## 授权范围

- 在 `src/ventricle_simucell3d_tf2b/`、`scripts/` 与 `tests/` 新增本阶段所需的适配层、runner、独立验证器、渲染器和聚焦测试；
- 在正式矩阵前执行构建、测试和有上限烟雾检查，累计不超过 `300 s`；
- 以 CPU 最多 4 线程执行一次 create-only 正式矩阵，累计不超过 `1800 s`；
- 写入唯一正式结果目录 `results/ventricle_z1/z1tf2b_simucell3d_shape_formation_v01_20260912/`；
- 从冻结 artifact 生成合同要求的 PNG/SVG、报告、离线 HTML 和独立复核。

## 禁止范围

- 不修改 `external/simucell3d/` 核心；若适配层不能满足合同，停止并记为 `blocked_dependency`；
- 不使用 GPU、Docker、网络、软件安装、后台 worker、外部发布、提交或推送；
- 不改动冻结阈值、物理定义、工况矩阵或旧结果包；
- 不自动进入周期主动力学、物理时间标定、Z2、CFD 或 FSI；
- 不删除任何旧文件、失败包、构建目录或临时目录。

## 冻结基线

| 对象 | SHA-256 / 标识 |
|---|---|
| PRL HEAD | `b45650a9e370be138a70acf305b6c3a21e6a7ed2` |
| 冻结合同 | `9a56df030279595036f43a6a169adb7710e2a4ba2fcbafdc64459dbe3db72c2b` |
| M0 适配层源文件 | `b53c9e463320ecd1f910d59b420cea56cb9ad4d7ce54d0f559fa9423b0cb18d2` |
| M0 CMake | `99f24d2bccccb2914b6585a844027b5013ac394f627ed3cede95226fd9d3046e` |
| M0 provenance | `84c35f76e04e6c635fc0f24de8621add8933c65d0b33d10106c8199c17f3ad5d` |

新增 TF2-B 源码、测试、验证器和渲染器的精确哈希必须在正式矩阵启动前写入结果预登记；正式启动后本授权即消费，无论结果为通过、未知、失败或阻断均不得自动发起第二次正式矩阵。
