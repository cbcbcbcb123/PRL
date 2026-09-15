---
contract_id: PAPER2-LINEAGE-ODD-MODE-GATE-v03
status: accepted_for_one_formal_attempt
accepted_at: 2026-09-09
base_commit: b45650a9e370be138a70acf305b6c3a21e6a7ed2
source_guidance: EXP-20260909-001-paper2-lineage-ecm
---

# Paper 2 分裂奇模态机械门 v03 执行合同

## 目的与唯一操作修复

v03 只修复 v02 已冻结的运行时失败：保持容器根文件系统只读，为 FEniCSx/FFCx 的 `/root/.cache` 增加 512 MiB `tmpfs`，挂载选项固定为 `rw,exec,nosuid,nodev,size=536870912`。`noexec` 不允许，因为 JIT 共享库需要可执行映射。

v03 runner 必须以小适配层直接复用、不得改写 `scripts/run_paper2_lineage_odd_mode_gate_v02.py` 的科学计算核心。适配层只允许：冻结新的版本/输出身份和源哈希；验证缓存挂载；把缓存门记录进既有资源门；调用 v02 的 `run()`。

## Create-only 身份

- runner：`scripts/run_paper2_lineage_odd_mode_gate_v03.py`；
- host wrapper：`scripts/run_paper2_lineage_odd_mode_gate_v03_host.ps1`；
- tests：`tests/test_paper2_lineage_odd_mode_gate_v03.py`；
- result：`results/paper2_lineage_odd_mode_gate/v03_20260909/summary.json`；
- container：`prl-paper2-lineage-odd-mode-gate-v03-20260909`。

上述路径和容器名在冻结前必须不存在；v02 runner、结果与退出容器保持原样。

## 不变的科学与资源合同

- A1、H=0.3、De=0.2、T128、activation_peak=0.1；
- S2/S3 × `/`、`\` 严格镜像网格；八个 `z/h` 带；`m={1e-4,5e-5}`；
- v02 的互斥裁决、全部阈值、完整 `R[w]` 证书、异常留痕与科学边界；
- 20 次分解、24 RHS；累计线性代数≤30 s；任一调用≤30 s；总 runner≤60 s；
- `dolfinx/dolfinx:v0.11.0` 及冻结 image ID；1 CPU、8 GiB、禁网、0 GPU、只读根、只读项目、仅结果目录可写；
- 不使用 S4，不改扰动、ROI 或读出，不加入真实分裂、反馈、流体、三维、非线性或参数扫描。

## 一次性执行与停止条件

1. 先运行不调用 FEM 的行为/静态测试并核对基线、关键源哈希、image ID、Docker、create-only 路径和容器名；
2. 测试与预检通过后只启动一次 v03 正式尝试；启动后无论成功、失败或超时均消耗授权；
3. 宿主独立 watchdog 为 60 s；超时可停止容器，但不得自动重试或生成 v04；
4. 失败时保留 summary、容器、账本和错误，不作科学阴性解释；
5. 完成后按 v02 冻结裁决解释 H0。只有既有 P1 阶段门明确支持继续时，才可另行处理 P2；本合同本身不执行 P2/P3。

## 授权来源

用户于 2026-09-09 在收到 v02 失败闭环和 v03 最小修复提案后明确回复“批准执行”。精确 runner/wrapper 哈希与尝试消耗状态登记在独立执行授权记录中。
