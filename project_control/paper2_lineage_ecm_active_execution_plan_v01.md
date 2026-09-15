---
plan_id: PAPER2-LINEAGE-ECM-ACTIVE-v01
source_guidance: EXP-20260909-001-paper2-lineage-ecm
status: active
authorized_at: 2026-09-09
base_commit: b45650a9e370be138a70acf305b6c3a21e6a7ed2
---

# Paper 2 谱系—ECM 活动执行计划 v01

## 唯一当前目标

先完成 P0 合同修订，再用唯一一次 P1 CPU 正式尝试判断：在冻结的二维机械可达切向子空间和八带纵深核类中，分裂后的左右身份读出是否稳定分辨母平均隐藏模态。若 P1 不支持 H0，P2/P3 自动停止。

## 阶段、预算与状态

| 阶段 | 状态 | 预算 | 本阶段交付/停止条件 |
|---|---|---|---|
| P0 | `passed` | 实耗 8 个纯逻辑/静态合同测试、1.90 s；0 FEM | v02 runner、互斥裁决、完整 `R[w]` 证书、宿主 watchdog、部分失败留痕及正负合成测试均已实现并通过 |
| P1 | execution `passed` / scientific `unknown` (`NOT_RESOLVED`) | v03 唯一尝试已消耗；20/20 分解、24/24 RHS；14.471 s 线性代数；24.389 s runner；0 GPU | 镜像、残差、FD、符号、秩区间和混合核证书通过，但 6/8 个带未通过 5% 两网格门；不进入 P2，不追加 S4/v04 |
| P2 | `blocked` | ≤12 个 CPU 协议、≤180 s、0 新 FEM | 仅在 P1 为稳健 GO 时解除；若条件 GO 或 SMALL_GAIN，按专家分支先处理深度/可测性，不进入完整事件主张 |
| P3 | `blocked` | ≤8 个 CPU 协议、≤300 s、0 GPU | 仅在 P2 通过且规格、二维边界及公平连续强对照冻结后解除 |
| P4 | `not_run` | design-only | 不运行新求解或闭环 |
| P5 | `not_run` | 未授权 | 生长、重复分裂、死亡和周转暂缓 |

## P0 冻结修订

1. v01 保持不变；修订版固定为 `scripts/run_paper2_lineage_odd_mode_gate_v02.py`，结果固定为 `results/paper2_lineage_odd_mode_gate/v02_20260909/summary.json`，均为 create-only。
2. 分类优先级固定为：资源/镜像/实现失败 → 残差或 FD 未解析 → 对称性失败 → 两网格未解析 → `RESOLVED_SMALL_GAIN` → `ROBUST_NUMERICAL_NO_GO` → 带内同号且完整 `R[w]` 证书通过的稳健 GO → 全带秩可分辨但纵深符号改变的条件 GO → `NOT_RESOLVED`。每次只返回一个状态。
3. `RESOLVED_SMALL_GAIN` 要求所有带完整秩区间离零、但所有 `g` 区间均落在 ±1e−8 内；它不释放反馈。`ROBUST_NUMERICAL_NO_GO` 要求所有 `g` 区间均落在该参考尺度内且完整秩未被解析。
4. 对任意带内常数概率权重使用 `R[w]=Σw_bR_b`。稳健 GO 额外要求保守充分界 `A_min |g|_min > |a|_max |B|_max`；不通过只记未解析，不是 NO-GO。
5. P1 由宿主独立 watchdog 监督总墙钟 60 s；Python signal 仅为第二层保护。runner 逐项记录单次调用耗时并执行 30 s 门。
6. 每个离散完成后立即保留在内存 summary；异常记录已完成离散、账本、错误类别。非有限值写成带字段位置的显式 marker，绝不替换为零。

## P0 合成反例

- 正例：`A∈[1,1.1]`、同号 `g∈[0.9,1.1]`、`|a|,|B|≤1e−12`，保守全核证书为正。
- 负例：两个带分别为 `[[1,2],[0,1]]` 与 `[[1,0],[2,1]]`；各自行列式为 1，而等权混合矩阵行列式为 0，证明“逐带 det 离零”不能推出任意混合核 det 离零。

## P1 正式尝试合同

- 冻结 A1、H=0.3、De=0.2、T128、activation_peak=0.1；S2/S3×`/`、`\` 镜像；八个 `z/h` 物理带；`m={1e-4,5e-5}`。
- 容器 `dolfinx/dolfinx:v0.11.0`，镜像 ID `sha256:2ae4bfbc0d9077268880faf04c72750528bee986c94ab223a2c159969bd56fa8`；1 CPU、8 GiB、禁网、只读根和只读项目挂载，只有精确结果目录可写；不挂载 Docker socket，不请求 GPU。
- 正式尝试只允许 v02 一次；路径冲突、哈希漂移、资源预检失败或 watchdog 超时均记 `failed/blocked + not_run` 科学状态，不自动重试。

## 证据边界

P1 最多认证 H0 的受限数值观察结论；真实分裂因果 H1、ECM 选择性/存储 H2、生物真实性和目标期刊成熟度在没有各自证据前均保持 `unknown/not_run`。

## P1 v02 正式尝试结果（2026-09-09）

- 唯一授权尝试已经启动并消耗；容器退出码为 1，结果为 `FAILED_CLOSED`。
- 1 CPU、8 GiB、禁网、只读根、无 GPU、镜像 ID、runner SHA256 和受控源哈希门均通过。
- S2/S3 镜像网格预检通过；DOLFINx 导入成功。首个 S2 离散进入 JIT 前，FFCx 尝试创建 `/root/.cache`，触发 `OSError: [Errno 30] Read-only file system`。
- 求解账本为 0 次分解、0 个 RHS、0 s 线性代数；因此 H0 未评价，不能解释为机械奇模态不存在。
- P2/P3 继续阻塞。任何 v03 运行时修复与新正式尝试都需要新的用户明确授权。

## P1 v03 授权（2026-09-09）

用户已明确批准 v03 最小运行时修复与一次新的 P1 正式尝试。该授权只允许增加 `/root/.cache:rw,exec,nosuid,nodev,size=536870912` 的内存 tmpfs、建立新 create-only runner/wrapper/result/container 并运行一次；不得改变科学计算核心、参数、阈值、网格、读出、资源或阶段门。

## P1 v03 最终结果（2026-09-09）

- 缓存修复、资源门和完整执行均通过；结果为 `COMPLETED` / execution `PASS`。
- 八带 `g` 同为负，八带完整行列式区间均离零，任意带内常数概率核的保守证书通过。
- `g` 的 S2→S3 变化有 6/8 带超过 5%，最大 7.3426%；互斥科学分类为 `NOT_RESOLVED`。
- 这是数值分辨门未通过，不是 `ROBUST_NUMERICAL_NO_GO`，也不支持稳健 GO 或 P2。P2/P3 继续阻塞。
