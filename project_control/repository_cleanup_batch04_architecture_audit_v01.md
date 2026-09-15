---
document_id: PRL-REPOSITORY-CLEANUP-BATCH04-ARCHITECTURE-AUDIT-V01
status: passed
recorded_at: 2026-09-15
implementation_status: candidate03_deletion_passed_candidate02_application_migration_not_run
scientific_execution: not_run
deletion_executed: true
---

# Batch 4 当前代码架构审计与重构候选 v01

## 结论

当前主要问题不是源码磁盘占用，而是活动入口、历史证据脚本和版本化实验脚本没有形成稳定边界。审计范围内 210 个代码/构建文件共 3,868,810 bytes；即使全部缩减，对当前 5.377 GiB 总量影响也很小。Batch 4 的主要收益应是降低耦合、恢复可测试入口并为 Batch 5 精简 Git 基线明确“什么是真正的当前代码”，不能以压缩代码行数替代架构修复。

本文件原始审计只做静态审计、测试收集诊断和方案记录。用户随后确认候选1、候选2、候选4第一切片及候选3来源矩阵、源码复制、退出前安全切片和精确删除。最新[删除记录](repository_cleanup_batch04_candidate03_deletion_execution_v01.md)显示16个必要源码及包装已保全，默认包发现、默认pytest和根README已切换到当前`prl`主线；38路径、61文件已永久删除，默认与显式quick均19/19通过。候选2应用迁移仍未实施。没有运行科研求解器、GPU、Docker、安装或外部服务。

## 当前代码地图

| 范围 | 文件/规模 | 关键事实 |
|---|---:|---|
| `scripts/*.py` | 145 个，2,989,937 bytes | 136 个文件名带版本号；54 个脚本存在本地脚本导入，共 82 条本地导入边 |
| `tests/**/*.py` | 30 个，188,712 bytes | 默认收集得到 266 个测试，但退役 Paper2/FEniCSx 测试因缺少 `basix` 产生 2 个 collection error |
| `src/` | 34 个文件，689,564 bytes | Python 包仍以 NCS/Paper2 为主；当前 SimuCell3D 应用是独立 C++ 目录，不在 Python 包发现中 |
| 当前长程入口闭包 | 15 个脚本，100,135 bytes，1,263 行 | 8 个当前入口经 28 条内部边扩展到 15 个脚本；运行、验证、绘图和打包仍从旧阶段脚本取常量、路径和工具函数 |
| 保留 Z1 包来源引用 | 54 个规范化路径 | 29 脚本、13 个 `src` 文件、7 个 SimuCell3D 文件、4 个测试和 1 个结果内快照键；来源引用不等于都应继续参加日常构建 |
| C++ 应用目标 | 14 个 | M0 目录 8 个、bioform 目录 5 个、TF2B 目录 1 个；没有根级当前应用构建入口 |
| C++ 实现包含 | 8 个应用源 | 通过重命名 `main` 后 `#include` 旧 `.cpp` 取得内部 helper；编译边界和程序入口混在同一翻译单元 |
| 退役结果硬编码 | 32 个代码文件、75 处 | 仍引用已经永久退役的结果路径；其中当前保留的接触修复绘图器仍读取已删除 dev01 指标 |
| Git 可见性 | scripts 22/123、tests 4/26、src 10/24（tracked/untracked） | 当前大量有效代码未被 Git 跟踪；不能用“Git 未跟踪”作为删除依据，Batch 5 必须使用显式保留清单 |

当前关系可概括为：

```text
缺失的稳定入口：python -m prl
        |
        +-- 8 个当前 run/verify/render/package 根脚本
        |       +-- 15 脚本传递闭包 / 28 条内部边
        |       +-- 固定结果目录、b/z1m0a 可执行文件
        |       +-- C:/Users/chenb/.codex/skills 的机器路径
        |
        +-- 现有 pyproject.toml
                +-- 只发现退役 paper2_m1/paper2_hybrid/paper2_figure2

M0/Bioform/TF2B 共 14 个 C++ 程序
        +-- 8 个应用源通过 include 旧 .cpp 复用匿名命名空间实现
                +-- 唯一 external/simucell3d 核心
```

## 主要摩擦与删除测试

1. **Python 活动入口是脚本网络，不是模块接口。** `run_myo_long_doublet_v01.py` 直接从接触屏障阶段导入可执行文件路径、旧结果路径、哈希和 CSV 读取；验证器又从运行器和几何脚本导入同一批实现细节。删除任一中间脚本会把路径、预算、I/O 和几何知识扩散到多个调用者，因此这些复杂度应先收进稳定模块。
2. **科学运行与独立验证的边界不清。** 可以共享只负责格式的 JSON/CSV/schema I/O，但不能让运行器和验证器共享同一力学判定实现。新包必须保持“求解器写账本、验证器从冻结状态独立重算”的边界。
3. **C++ 所谓复用实际上绕过编译接口。** `ventricle_simucell3d_m0.cpp` 同时包含 27 类 helper/数据结构与 `main`；5 个 M0 应用直接包含它。另有 3 个应用直接包含 `ventricle_bioform_myo_v03.cpp`。若直接删除这些大文件，复杂度不会消失而是所有目标无法编译；应先抽出正常头文件/实现库。
4. **退役路线代码通过删除测试。** Paper2/NCS 应用层没有当前 SimuCell3D 调用者；删除后复杂度不会转移到当前主线。其风险在历史证据来源与 Git 记录，而不在当前运行，因此应先把精选来源快照迁入证据区，再形成精确删除清单。
5. **当前默认入口反向指向历史。** `pyproject.toml` 只发现三个 Paper2 包；根 README 仍把 Hybrid/X1 和已退役命令写成可复算入口；默认 pytest 也收集退役套件。这会让新执行者错误地把历史路线当作当前产品。
6. **机器依赖未封装。** 当前长程打包与绘图闭包仍引用本机 Codex skill 绝对路径。该依赖可以用于当时交付，但不能成为精简 Git 基线的运行前提。

## 重构候选

### 候选 1：建立稳定 Python 应用/证据模块（建议先做）

- **Files**：新增 `src/prl/` 包，更新 `pyproject.toml`，新增 `tests/prl/`；第一安全切片不修改或删除任何冻结旧脚本。
- **Current friction**：当前 8 个入口扩展到 15 个脚本；调用者需要知道阶段目录、旧结果路径、可执行文件、预算、哈希和输出顺序。
- **Proposed deepening**：用 `python -m prl` 暴露稳定命令；把工作区解析、存储预算、JSON/CSV schema、结果定位和命令状态收进深模块。运行器与独立验证器只共享格式层，不共享力学裁决。
- **Benefit**：新主线不再从版本化历史脚本导入；为 3 GiB 总量门禁和单阶段 256 MiB 预算提供唯一入口；测试可以直接验证公共接口。
- **Risk**：若直接改写旧脚本，会使保留结果的来源哈希失配。必须采用 create-only 新包，以冻结结果做行为对照，再单独退役旧入口。
- **First safe slice**：`passed`。已实现 `python -m prl storage status` 和 `python -m prl verify long-doublet`，读取现有数据、不启动求解器；3组公共接口测试和包发现通过。详见[执行记录](repository_cleanup_batch04_candidate01_execution_v01.md)。`run`/`render`仍未迁移。

### 候选 2：抽取 C++ 应用支持库

- **Files**：`src/ventricle_simucell3d_m0/`、`src/ventricle_bioform_myo/` 的应用 helper 与 CMake；`external/simucell3d/` 保持唯一内核，不复制。
- **Current friction**：8 个应用源直接包含带 `main` 的旧 `.cpp`，匿名命名空间类型、参数和输出细节成为隐式接口。
- **Proposed deepening**：建立一个正常的 `prl_ventricle_support` 静态库和小头文件接口，承载几何、细胞类型、载荷组装、接触调用、状态输出与安全指标；每个 executable 仅保留参数解析和场景选择。
- **Benefit**：减少重复编译与隐藏耦合，允许单元测试 helper，并使日常构建只选择当前目标。
- **Risk**：这些文件被保留结果哈希绑定；提取前须保全原源码快照，且必须用现有几何 self-test、作用反作用、能量梯度、正间隙和小规模输出逐字节/数值对照。
- **First safe slice**：`passed`。新增独立`prl_ventricle_support`静态库，覆盖向量、三角表面网格文本I/O和版本化结果schema；以保留双胞网格/六表及合同测试验收。现有应用尚未切换，不移动接触势、材料参数或积分器。详见[执行记录](repository_cleanup_batch04_candidate02_execution_v01.md)。

### 候选 3：退役 Paper2/NCS 代码进入精选证据

- **Files**：候选范围当前为 4 个 `src` 目录、4 个测试目录、2 个根测试和 26 个脚本，共 36 个路径、59 个文件、1,532,153 bytes；这还不是删除授权清单。
- **Current friction**：这些包控制当前 `pyproject.toml` 和默认 pytest，但不属于 SimuCell3D 前向主线；32 个代码文件仍含退役结果路径。
- **Proposed deepening**：把仍被 Batch 3A 精选证据引用的最小来源与依赖复制到 `project_control/evidence/retired_routes_v01/source/` 并验收哈希；随后另行冻结逐路径删除清单。
- **Benefit**：日常包、测试和入口不再受退役路线依赖；默认收集不再要求 FEniCSx/basix。
- **Risk**：删除后旧路线不能从活动源码重跑；Git 跟踪与未跟踪文件混合，必须逐文件登记。当前统计不授权删除。
- **Safe slices and deletion**：`passed`。来源矩阵、14个必要源码及两个宿主包装均已保全；合计16个证据源码、369,160 bytes。退出前依赖复核确认候选外148个Python文件无导入依赖，默认入口现只暴露当前`prl`。38路径、61文件、1,541,224 bytes已按[精确提案](repository_cleanup_batch04_candidate03_deletion_proposal_v01.md)和[执行记录](repository_cleanup_batch04_candidate03_deletion_execution_v01.md)永久删除。

### 候选 4：统一构建、测试与导航

- **Files**：根 `README.md`、`pyproject.toml`、当前 CMake 入口、测试标记与项目导航。
- **Current friction**：根 README 与当前状态冲突；默认包发现和默认 pytest 均以历史路线为中心；当前 C++ 有 14 个分散目标。
- **Proposed deepening**：默认只暴露当前 `prl` 包、当前应用和快速回归；历史证据测试进入显式 `evidence` 入口，不参加日常门禁。构建目标分为 `current`、`qualification`、`upstream`，不删除上游必要测试。
- **Benefit**：新基线检出后能从一个入口安装、构建、测试、验证；首页与真实运行边界一致。
- **Risk**：若过早缩减测试集合会掩盖耦合。应在候选 1/2 的行为对照稳定后切换默认入口。
- **First safe slice**：`passed`。新增 `python -m prl test quick`、5文件显式manifest和严格import/路径/保护身份检查；初始17项quick及旧位置7项资格对照通过。后续经用户确认的[退出前安全切片](repository_cleanup_batch04_candidate03_exit_safe_slice_execution_v01.md)已把根README、`pyproject.toml`和默认pytest切换到当前主线；默认与显式quick现为19/19通过。

## 建议顺序与停止点

建议按 **候选 1 → 候选 2 → 候选 4 → 候选 3** 执行。理由是先建立新边界并做行为对照，再切换默认入口，最后才让旧代码真正离开活动树。每个切片单独验收，不一次性重写全部代码。

下一步建议只实施候选 1 的 first safe slice，预计新增 8–10 个小文件并修改 `pyproject.toml`，不删除任何文件、不运行求解器。完成后应满足：

1. `python -m prl storage status` 从工作区根给出总量、预警/硬上限和可用预算；
2. `python -m prl verify long-doublet` 独立读取保留状态，输出与冻结 verdict 一致的关键数值/状态；
3. 新模块不导入 `scripts/run_*` 或外部 Codex skill；
4. 运行器与验证器没有共享力学判定；
5. 新测试不产生 `.pytest_cache` 或 `__pycache__`；
6. 旧脚本、旧结果和来源哈希保持原样。

候选1、候选2第一切片、候选4默认入口及候选3退出/删除均已`passed`；候选2应用迁移仍为`not_run`。存储状态入口继续报告当前仓库超过3 GiB硬上限并拒绝科研新任务；这不等于空间清理完成。下一步应冻结8个当前C++应用的迁移安全切片，保持物理实现与验证门不变；本次候选3删除授权已经消费，不覆盖该迁移或任何新删除。
