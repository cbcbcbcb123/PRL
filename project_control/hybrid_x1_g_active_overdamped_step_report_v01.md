---
report_id: REPORT-PRL-HYBRID-X1-G-V01
status: passed_frozen
completed_at: 2026-08-02
parent_branch: codex/simucell3d-hybrid-feasibility
cell_engine_branch: codex/cell-engine-integration-seam
cell_engine_commit: 7a709a8353e83c43847a4853414068033217b906
result_id: PRL-HYBRID-X1-G-ACTIVE-OVERDAMPED-STEP-V01
---

# Hybrid X1-G 主动过阻尼原子单步报告 v01

## 结论

X1-G 已完成。父项目新增 `advance_active_cell_overdamped_one_step`，在真实 cell-engine `cell` 上完成“当前 surface snapshot → 主动力求值 → 与既有力缓冲区相加 → 一次 `dx=dt·F/ζ` → 原子位置提交与力缓冲区清零”。fork 新增生物学无关的 `advance_surface_overdamped` primitive，并保持长期项目的 C++ 高性能内核 / Python 科研层分工。

## TDD 证据

1. **RED**：真实 cell 集成 tracer 首先因 `prl/cell_engine/active_overdamped_step.hpp` 不存在而编译失败；
2. **GREEN**：最小父入口与 fork primitive 接通后，真实八节点 cell 产生逐节点精确位移，主动能量下降；
3. **failure atomicity**：非正阻尼和陈旧材料在父入口被拒绝，位置与原有力缓冲区均保持不变；一个“节点力有限、但主动输入功率溢出”的反例先产生 RED，随后由父入口的预提交审计有限性检查修复；fork 另覆盖未知 persistent vertex；
4. **post-remesh composition**：真实 edge swap 与材料迁移后，在 revision 1 完成同一单步；
5. **refactor**：fork 按稳定节点索引顺序计算 pending writes 与审计和，避免哈希容器遍历顺序影响末位浮点结果；父入口移除提交后的主动求值，使成功提交后不再存在额外可抛异常步骤。

## 冻结接口与失败边界

- 已有 `node.force_` 是预装配的 passive/contact contribution，主动力是额外增量；
- fork 先验证完整输入、当前状态、总力、位移和全部 resulting positions，再提交位置并清零 used-node force buffers；
- cell 必须非静态，`dt` 与 `ζ` 必须有限且为正，`dt/ζ` 必须有限；
- material/mesh revision 必须一致，persistent vertex IDs 必须唯一、存在且有限；
- 步前主动能量、输入功率、控制能估计与守恒残差必须在提交前保持有限；
- 调用期间 target cell 必须由一个 worker 独占；
- primitive 不刷新派生几何缓存，stock solver 也未自动 hook。

## 定量结果

| 检查 | 结果 |
|---|---:|
| real-cell used vertices | `8` |
| contraction units | `1` |
| activation / activation rate | `0.1 / 0` |
| time step / damping | `1e-3 / 1` |
| active energy before | `0.04315625` |
| active energy after | `0.04279879638351551` |
| active-force L2 norm | `0.5984955095905065` |
| displacement L2 norm | `0.0005984955095905065` |
| force work | `0.000358196875` |
| viscous dissipation | `0.000358196875` |
| work–dissipation residual | `≤1e-12` |
| net displacement residual | `≤1e-12` |
| failure atomicity | passed |
| real post-remesh step at revision 1 | passed |
| parent C++ CTest | `26/26 passed` |
| fork standalone CTest | `130/130 passed` |
| owned parent core strict warnings | `13/13 passed` |
| fork X1-G translation unit strict compile | passed with two inherited warning classes downgraded |
| parent Python | `63 passed` |
| tracked Python Ruff | passed |
| diff / JSON checks | passed |

显式 Euler 的独立能量账本给出 `ΔΨ + D = 7.43258515510908e-7`，这是该有限步长的二阶截断项，不作为零残差门槛；本阶段冻结的是力功与黏性耗散的代数恒等式以及实际主动能量下降。

## Git 与 CI 边界

fork 的功能提交为 `d2c54f8`，公共接口边界注释提交为 `7a709a8353e83c43847a4853414068033217b906`；二者均已推送到 `origin/codex/cell-engine-integration-seam`。fork workflow 只监听 `main` push 和指向 `main` 的 pull request，因此 branch push 不产生 GitHub Actions run；本报告以 Docker 内完整 `130/130` 回归为当前可复现证据。

## Claim guard

X1-G 证明一次主动过阻尼更新能够在真实 cell-engine cell 上按 revision 与 persistent identity 原子执行，并提供力功—黏性耗散账本、能量下降、失败原子性和重网格后组合证据。它不证明真实被动力已由该 driver 自动装配，不证明派生几何缓存已刷新，不证明 stock solver 已接管该路径，也不证明连续轨迹稳定、步长收敛、ECM/血流耦合或任何生理效应。
