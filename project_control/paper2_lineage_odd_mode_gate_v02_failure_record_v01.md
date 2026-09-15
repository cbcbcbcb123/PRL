---
record_id: PAPER2-LINEAGE-ODD-MODE-GATE-v02-FAILURE-v01
status: failed_closed
scientific_status: not_evaluable
recorded_at: 2026-09-09
attempts_consumed: 1
---

# Paper 2 分裂奇模态机械门 v02 失败记录

## 裁决

唯一一次 P1 v02 正式尝试已经消耗，执行结果为 `FAILED_CLOSED`。失败发生在首个 FEM 分解或 RHS 之前，科学状态为 `NOT_EVALUABLE_DUE_TO_EXECUTION_FAILURE`，不是 H0 的阴性结果，也不释放 P2/P3。

## 冻结证据

- 结果文件：`results/paper2_lineage_odd_mode_gate/v02_20260909/summary.json`；
- 结果 SHA256：`b2202f295d3521741523c00902e965d3622a2fad41ef2180c0618c3348cc4cf3`；
- 容器：`prl-paper2-lineage-odd-mode-gate-v02-20260909`，退出码 1，未自动清理；
- 镜像：`dolfinx/dolfinx:v0.11.0`，ID `sha256:2ae4bfbc0d9077268880faf04c72750528bee986c94ab223a2c159969bd56fa8`；
- runner SHA256：`54f07dfdb1b51286c129ec41404e31945492532e1346fc5728893b06b17f752a`，与批准值一致；
- host wrapper SHA256：`4a4483ad7cc35d940726c269175e36e903cb2654d026085e3ff92e8bc9d30dae`；
- 基线 HEAD：`b45650a9e370be138a70acf305b6c3a21e6a7ed2`，受控源哈希门通过；
- 资源门：1 CPU、8 GiB、网络仅 `lo`、只读根、无 GPU，全部通过；
- S2/S3 的 `/`、`\` 严格镜像网格预检均通过；
- DOLFINx `0.11.0.post0` 导入成功。

## 首个失败与预算账本

- 错误类型：`OSError`；
- 错误信息：`[Errno 30] Read-only file system: '/root/.cache'`；
- 失败位置：首个 S2 离散开始时的 FEniCSx/FFCx JIT 缓存初始化之前或期间；
- 分解：0/20；
- RHS：0/24；
- 线性代数累计：0/30 s；
- runner 总墙钟：3.937876581/60 s；
- 峰值 RSS：0.16357421875 GiB。

## 根因边界

Docker 的只读根文件系统按合同工作，但 v02 未为 FEniCSx/FFCx 的 JIT 缓存提供独立可写且可执行的 `/root/.cache`。项目既往静态模式筛查和反馈核门曾出现同类启动失败；已验证的最小运行时模式是仅将该路径挂为 `tmpfs`，选项为 `rw,exec,nosuid,nodev,size=536870912`，同时保持根文件系统只读。`noexec` 不可用，因为 JIT 生成的共享库需要可执行映射。

这是一项运行环境诊断，不证明 v03 一定成功，也不授权套用既往修复。科学矩阵、源、阈值、网格、观测量和预算均未被本次失败评价。

## 停止条件

1. v02 结果路径与退出容器保留，不覆盖、不重用；
2. 不自动重试，不自动生成 v03 runner，不启动 P2/P3；
3. 新尝试必须使用新的 create-only runner、wrapper、结果目录、容器名、哈希冻结和一次性执行授权；
4. 若用户不授权新尝试，P1 保持 `failed / scientific not_evaluable`。
