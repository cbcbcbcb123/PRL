---
proposal_id: PAPER2-LINEAGE-ODD-MODE-GATE-v03-RUNTIME-REPAIR-v01
status: approved_for_implementation
created_at: 2026-09-09
approved_at: 2026-09-09
execution_authorized: true
---

# Paper 2 分裂奇模态机械门 v03 最小运行时修复提案

## 提议范围

仅修复 v02 已确认的 FEniCSx/FFCx JIT 缓存写入边界：在保持容器根文件系统只读的同时，为 `/root/.cache` 增加 512 MiB 内存 `tmpfs`，显式选项为 `rw,exec,nosuid,nodev,size=536870912`。

## 必须保持不变

- 科学模型、A1、H、De、T128、激活幅值、S2/S3、双镜像网格、八个纵深带和两档 FD；
- 分类优先级、全部数值阈值、完整 `R[w]` 证书和 H0 证据边界；
- 20 次分解、24 RHS、累计线性代数≤30 s、单次≤30 s、runner≤60 s；
- 1 CPU、8 GiB、禁网、0 GPU、只读根和只读项目挂载；
- 不安装或升级软件，不改变 `HOME`，不创建盘符或目录映射。

## 若获授权才可实施

1. 创建新的 v03 runner 与 host wrapper；优先以最小适配层复用 v02，不复制或改写科学计算核心；
2. 在任何 FEM 工作前验证 `/root/.cache` 恰有一个 `tmpfs` 挂载，且包含 `rw,nosuid,nodev`、不含 `noexec`；
3. 使用新的 create-only 结果目录与容器名，不覆盖 v02 失败证据；
4. 冻结新 runner、wrapper、合同和适用源的 SHA256；
5. 形成一份新的“一次正式 P1 尝试”授权；无论成功、失败或超时均消耗该次授权，不自动生成 v04；
6. 任一预检失败即停止，科学状态保持 `not_run/not_evaluable`。

## 未授权事项

本提案不授权创建 v03 文件、运行容器、重新求解、修改阈值、使用 GPU、安装依赖、清理 v02 证据、进入 P2/P3 或对外发布。下一步需要用户明确批准“实施该最小运行时修复并进行一次新的 P1 正式尝试”。

## 用户裁决

用户于 2026-09-09 明确回复“批准执行”。据此，本提案获准转化为 v03 执行合同、最小适配 runner、宿主 watchdog 和一次性正式 P1 授权。未授权事项继续有效，其中 P2/P3 只按 v03 的科学裁决和既有阶段门处理。
