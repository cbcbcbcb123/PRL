---
record_id: PAPER2-LINEAGE-ODD-MODE-GATE-v03-EXECUTION-v01
execution_status: passed
scientific_status: unknown
scientific_label: NOT_RESOLVED
recorded_at: 2026-09-09
attempts_consumed: 1
---

# Paper 2 分裂奇模态机械门 v03 执行与验收记录

## 最终裁决

v03 唯一正式尝试完整执行，执行层为 `passed`；冻结 P1 科学门为 `NOT_RESOLVED`，对应项目状态 `unknown`。信号方向、秩区间和混合纵深核证书在本次数值包中可分辨，但 6/8 个纵深带未通过 S2→S3 的 5% 经验收敛门，因此不能认证稳健 GO，也不是数值 NO-GO。

P2/P3 继续 `blocked`。不得追加 S4、改变扰动、阈值、ROI、读出或自动生成 v04 来挽救本门。

## 身份与资源验收

- 结果：`results/paper2_lineage_odd_mode_gate/v03_20260909/summary.json`；
- 结果 SHA256：`d8882a7350996a9be6c364272ca51f9eb383201599bcfed73a8129bff3fd5b2d`；
- 容器：`prl-paper2-lineage-odd-mode-gate-v03-20260909`，退出码 0，已退出并保留；
- 镜像 ID：`sha256:2ae4bfbc0d9077268880faf04c72750528bee986c94ab223a2c159969bd56fa8`；
- v03 runner SHA256：`d6e52b17e00d9e0ddafbaee86689917f8f2bb4755fdd3d1cbc02ba8d1cf24ed7`；
- host wrapper SHA256：`35a45ad3f51a652d68c162a327bc351e1b4a43cd08635c17b1b5fbfd82b366ba`；
- 源哈希门和 runner 授权哈希门均通过；
- 1 CPU、8 GiB、禁网、只读根、只读项目、0 GPU 全部通过；
- `/root/.cache` 被验证为 536870912 字节 `tmpfs`，具备 `rw,nosuid,nodev` 且允许执行；
- S2/S3 严格镜像网格预检与镜像 parity 门均通过。

## 执行账本

- 分解：20/20；
- RHS：24/24；
- 账本记录：44 条；
- 累计线性代数：14.470801716/30 s；
- 44 次线性代数调用均通过 30 s 单次门；
- runner 总墙钟：24.389381747/60 s；
- 峰值 RSS：0.429302215576172 GiB；
- 宿主独立 watchdog 未触发。

## 数值与科学门

- 线性残差门：`passed`；
- 两档有限差分门：`passed`；
- 镜像 parity：`passed`；
- 预期近零的 `B`、`a`：`passed`；
- 八带 `g`：S2、S3 均为负；
- 八带完整 `det(R)=A*g-a*B` 经验区间：全部离零；
- 任意带内常数概率纵深核的保守混合证书：`passed`，行列式下界裕量为 `0.0009770867749692765`；
- 两网格经验门：`failed`。各带 `g` 的 S2→S3 相对变化依次为 5.7874%、7.2469%、5.4140%、4.1905%、4.2171%、5.4793%、7.3426%、6.2029%；只有带 3、4 通过 5% 门。

因此唯一互斥分类为 `NOT_RESOLVED`，bounded claim 为“two-grid empirical convergence or expected-zero gate did not pass”。本结果只评价冻结二维切向机械子空间和八带核类；不是实际分裂模拟，不证明 DCM 必要性、ECM 反馈、生物真值或投稿成熟度。

## 停止与后续

1. v03 正式授权已消耗，结果和容器保留；
2. 不运行 P2/P3，不追加 S4 或新正式尝试；
3. 下一步应回到专家阶段门，裁决是停止该机械门主线，还是另行提出不依赖事后放宽门限的新问题；当前没有数值授权。
