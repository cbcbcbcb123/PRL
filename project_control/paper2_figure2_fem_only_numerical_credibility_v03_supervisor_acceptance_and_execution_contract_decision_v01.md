---
decision_id: DEC-PAPER2-FIGURE2-FEM-ONLY-NUMERICAL-CREDIBILITY-V03-ACCEPT-EXECUTION-CONTRACT-V01
status: approved_under_human_standing_authority
decider: independent_supervisor
decided_at: 2026-09-04
standing_authority: project_control/paper2_autonomous_execution_and_chart_reporting_decision_v01.md
accepted_contract: project_control/paper2_figure2_fem_only_numerical_credibility_contract_v03.md
accepted_contract_sha256: 796de6a6cfa6167e30cae592128379206709ace720d4fcbe3ae80366fb504249
prior_contract: project_control/paper2_figure2_fem_only_numerical_credibility_contract_v02.md
prior_review: project_control/paper2_figure2_fem_only_numerical_credibility_contract_v02_supervisor_review_v01.md
accepted_label: FIGURE2_FEM_ONLY_NUMERICAL_CREDIBILITY_CONTRACT_ACCEPTED_V03
next_contract: project_control/paper2_figure2_fem_only_numerical_credibility_execution_contract_v01.md
execution_authorized: figure2_execution_contract_drafting_only
---

# Paper 2 Figure 2 FEM-only 数值可信度合同 v03 Supervisor 验收与执行合同决定 v01

## 1. 决定

Supervisor 接受
`project_control/paper2_figure2_fem_only_numerical_credibility_contract_v03.md`，正式标签为
`FIGURE2_FEM_ONLY_NUMERICAL_CREDIBILITY_CONTRACT_ACCEPTED_V03`。

该合同冻结 Figure 2 的前瞻数值可信度规则，不证明任何门已经通过。v01、v02、两轮
审阅和 v03 共同构成不可覆盖的决策链。活跃架构继续只有离散心内膜细胞链、主动心肌
FEM 和黏弹 ECM FEM；心肌 DCM 不得进入实现、比较器、病例轴或论文主张。

## 2. 独立验收结果

| 检查项 | 独立结果 | 状态 |
|---|---:|---|
| 基线与 upstream | `ade5f96d...`，0/0 | PASS |
| v02、v02 审阅、Figure 1 | 三个 SHA-256 与 v03 锚点一致 | PASS |
| 八个核心源码 | SHA-256 逐项一致 | PASS |
| 开发/留出分区 | `A2/LN/LS/C0/CQ` 开发，`S1` digest 后独立解盲 | PASS |
| 门禁 DAG | `G4a -> G5 -> G4b -> G4` 无环，总裁决不能提前 | PASS |
| 混合差 | 四角以 S4/T256 和同一 floor 归一 | PASS |
| 公共空间域 | 128 个 P0 段，原生分片线性场解析积分 | PASS |
| 公共相位域 | 256 个周期中心化 P0 段，DC/一阶谐波取解析段平均 | PASS |
| 峰值热点 | `I128` 以 `T/2` 为中心并标 `peak_phase_bin_average` | PASS |
| 功/耗散映射 | 与单频场分路，按原生区间交叠守恒分配 | PASS |
| N1–N11 | 全部为硬门，无未决候选 | PASS |
| 结果与资源 | 强制最小 NPZ、128 MiB、create-only、单 CPU/无网络/GPU | PASS |
| 文本完整性 | 788 行，34468 bytes，24/24 组展示公式，无尾随空格 | PASS |

## 3. 冻结的执行逻辑

1. 开发阶段按 `G0 -> G1 -> G2 -> G3 -> G4a -> G5 -> G4b -> G4 -> G6 -> G7`
   依次执行；任一硬门失败立即停止；
2. 只有开发门全部通过并生成 `pre_holdout_digest.json` 后，才可解盲 S1；
3. G4a 只处理标量、周期积分量和无需跨空间网格对应的波形；G5 生成并审计公共域；
   G4b 才处理公共牵引场混合差；G4 只做真值表汇总；
4. 共同定义域唯一为 128 空间段 × 256 周期中心化相位段；相位段值为解析段平均，
   禁止端点、中心点或节点抽样；
5. S1 热点使用以 `T/2` 为中心的第 128 相位段平均，不冒充精确点值；
6. 逐步功与耗散不做谐波重建，必须走原生时间单元到公共段的区间交叠守恒映射；
7. `common_observables.npz` 是强制最小证据包，压缩后不得超过 128 MiB；
8. 最终候选标签只能在所有开发门、留出门、源锁、资源和数组合同通过后生成。

## 4. 证据边界

本验收只接受验证设计。当前尚无 Figure 2 v03 的求解、收敛、功率、留出或资源结果，
因此不能写 `FIGURE2_FEM_ONLY_NUMERICAL_CREDIBILITY_PASS_V03`。它也不证明生理真实性、
EFE 机制、三维/整心房、流体、实验验证或 Nature Physics 级普适规律。

## 5. 下一步授权

下一步只授权起草版本化
`project_control/paper2_figure2_fem_only_numerical_credibility_execution_contract_v01.md`。
该执行合同必须把 v03 逐项映射成：

1. 拟新增的验证模块、runner 和测试的精确文件清单；
2. G0–G7、digest 与 S1 的入口、输入、输出、停止码和依赖关系；
3. N1–N11 的机器可判定 schema、比较方向、floor 和 FAIL 标签；
4. 唯一 create-only `run_id`、结果目录、数组键/shape/dtype 和 hash ledger；
5. 单 CPU、8 GiB、3600 s、无网络/GPU/socket 的容器命令与运行前后锁；
6. 最小测试顺序，以及开发集通过后才生成 digest、随后才解盲 S1 的事务边界；
7. 核心模型源码只读；任何模型方程、参数、病例、阈值或生产观测量改变都必须另立
   模型/协议变更合同，并使本执行合同失效。

执行合同完成后必须再次停在 Supervisor Gate。本决定不授权写代码、运行测试、启动
solver/Docker、创建结果目录、执行参数扫描或制作 Figure 2。

## 6. 当前禁止范围

仍不授权 Figure 3、三维、整心房、流体/CFD/FSI、实验拟合、GPU、外部数据写入、
公开发布或投稿。不得删除、覆盖、移动或恢复旧 DCM/FEM identity 材料；其存在只作为
退役历史证据，不构成活跃项目的一部分。
