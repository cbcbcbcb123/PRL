---
execution_id: EXE-PAPER2-MYOCARDIAL-DCM-PHYSICAL-REMOVAL-V01
status: completed_and_verified
authorized_by: human
authorized_at: 2026-09-04
authorization_text: 同意，执行
supersedes_non_deletion_boundary: project_control/paper2_myocardial_dcm_retirement_and_fem_only_architecture_decision_v01.md
pre_removal_head: 8f240cf38cb4db38f02b776d320562058439770f
active_architecture: endocardium_discrete_chain__myocardium_active_fem__ecm_viscoelastic_fem
---

# Paper 2 心肌 DCM 物理清理执行记录 v01

## 1. 已确认边界

人类明确确认物理清理旧心肌 DCM 可执行实现。清理后唯一活跃架构仍为：心内膜离散
细胞链、主动心肌 FEM、黏弹 ECM FEM。心内膜 DCM/离散细胞链不得被删除或改成 FEM。

历史合同、决定和执行记录继续保留，只承担审计作用，不恢复任何可执行旧路线。

## 2. 删除目标与删除前规模

以下目标均位于仓库 `E:\Temp-Projects\PRL` 内，删除前已解析并核对：

| 目标 | 文件数 | 字节数 | 处置理由 |
|---|---:|---:|---|
| `src/paper2_m2/` | 47 | 842755 | 旧 DCM/FEM identity 双表示生产包 |
| `src/hybrid/` | 60 | 1212586 | 旧主动 DCM—ECM/三层 EFE 可执行栈 |
| `src/route_h/` | 72 | 1072079 | 旧 DCM 单细胞、主动收缩与 Route H 可执行栈 |
| `tests/paper2_m2/` | 65 | 577153 | 旧双表示测试 |
| `tests/hybrid/` | 38 | 612673 | 旧混合 DCM 测试 |
| `tests/route_h/` | 21 | 181257 | 旧 Route H 测试与测试证据副本 |
| `tests/stage0_v06/` | 4 | 82644 | 旧 Route H 离散化测试 |
| `tests/stage1/` | 17 | 236712 | 旧 DCM–ECM 测试 |
| `tests/stage2/` | 22 | 202172 | 旧主动 DCM 测试 |
| `results/paper2_m2/` | 192 | 2381368069 | 已确认删除的旧 M2A 结果树 |
| `scripts/*.py` 旧路线集合 | 135 | 1999511 | 旧 DCM、Route H、EFE、M2A 与其再生成入口 |
| `cpp/` | 9905 | 265425294 | 旧 C++ 主动心肌表面细胞、材料转移、重网格与构建产物 |
| `tests/test_r1*.py` | 4 | 20656 | 依赖已退役 C++/Python 混合栈的根级测试 |

脚本清理使用保留清单：除以下四个文件外，删除 `scripts/` 中其余 Python 文件：

- `scripts/capture_command_evidence.py`
- `scripts/make_docx_qa_contact_sheets.py`
- `scripts/run_paper2_m1_idealized_strip_v01.py`
- `scripts/run_paper2_figure2_fem_only_numerical_credibility_v01.py`

删除集合中共有 405 个 Git 已跟踪文件；这些文件的提交版本可从删除前 HEAD 恢复。未跟踪
结果和未提交旧路线修改在清理后不可由当前工作树恢复，人类已在获知该风险后确认执行。

## 3. 明确保留

- `src/paper2_hybrid/`、`src/paper2_figure2/`、`src/paper2_m1/`；
- `tests/paper2_hybrid/`、`tests/paper2_figure2/`、`tests/paper2_m1/`；
- 心内膜离散细胞链及其生产接口；
- `project_control/` 内历史合同、决定、审阅与执行记录；
- `docs/`、`planning/`、`data/`、`results/hybrid/`、`results/route_h/` 等非执行历史材料；
- `external/simucell3d/` 通用 DCM 引擎；仅移除其中未被通用引擎使用的心肌专用材料状态类型；
- 当前工作树中不属于上述删除目标的修改与未跟踪材料。

## 4. 执行后验收门

1. 所有删除目标不存在，四个保留脚本仍存在；
2. `pyproject.toml` 只发现当前 Paper 2 生产包，不再自动打包旧命名空间；
3. 当前 FEM-only 包不导入 `paper2_m2`、`hybrid` 或 `route_h`；
4. 更新静态架构测试，使其验证旧命名空间物理缺席；
5. 运行 CPU-only 静态/轻量测试；不运行 GPU、Docker 或正式求解；
6. Git 状态中不出现删除边界之外的新增改动。

## 5. 执行结果与验证

本次清理已完成，并通过以下边界验证：

- 已物理删除上表列出的 11 个旧路线目录/结果目标，以及 4 个依赖旧 C++ 栈的根级测试；
- 主删除集合共移除 10,582 个文件，记录规模为 2,653,833,561 字节，另清理 20 个由旧路线留下的缓存目录；
- Git 工作树显示 405 个已跟踪文件被删除；删除前提交版本仍可由
  `8f240cf38cb4db38f02b776d320562058439770f` 恢复；
- `scripts/` 仅保留第 2 节所列 4 个 Python 入口；
- Python 包发现结果严格为 `paper2_m1`、`paper2_hybrid`、`paper2_figure2`；
- 活跃源码与测试的 AST 检查通过，活跃导入图未发现对 `paper2_m2`、`hybrid` 或
  `route_h` 的导入；生产源码未发现心肌 DCM 材料状态或执行符号；
- CPU-only 静态/轻量测试结果为 **17 passed**；
- Figure 2 静态/证据测试为 **34 passed, 1 failed**。唯一失败是既有
  `S1 hotspot mask changed` 数组合同不一致；该测试不导入本次删除的旧路线，因此记录为
  独立的 Figure 2 证据冻结问题，不将其误报为本次清理回归；
- 宿主环境未安装 `basix`/FEniCSx，因此未在宿主机执行完整 FEM 运行时测试；
- 未运行 Docker、GPU、正式求解或结果再生成，也未执行暂存、提交或推送；
- `external/simucell3d/lib/pybind11/.ruff_cache` 属于保留的通用外部依赖缓存，未作为
  心肌 DCM 资产删除。

清理完成后的 Git 汇总为：`410 files changed, 67 insertions(+), 170559 deletions(-)`；
工作树同时包含大量不属于本清理任务的未跟踪材料，因此不得使用宽泛暂存。后续提交必须采用
重新制定的精确文件清单，并把本次物理清理与 Figure 2 既有工作分开审查。
