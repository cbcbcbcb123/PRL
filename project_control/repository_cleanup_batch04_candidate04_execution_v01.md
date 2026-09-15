---
document_id: PRL-REPOSITORY-CLEANUP-BATCH04-CANDIDATE04-EXECUTION-V01
status: passed
recorded_at: 2026-09-15
implementation_status: first_safe_slice_passed
default_test_switch: not_run
legacy_test_migration: not_run
scientific_execution: not_run
deletion_executed: false
---

# Batch 4 候选4统一测试入口第一安全切片执行记录 v01

## 结论

用户确认的候选4第一安全切片已完成。新增显式命令 `python -m prl test quick` 和版本化测试清单，只运行当前 `tests/prl/` 下列出的5个文件；运行前先检查路径、reparse point、import边界、机器绝对路径和保护文件身份。quick suite最终17项通过。

本次 `passed` 仅表示当前Python应用/证据层获得了一个有界、无缓存、可机器读取的快速工程门。根`pyproject.toml`的默认pytest收集、根`README.md`、旧测试位置和C++默认构建目标均未切换；因此不能把本切片写成候选4完整迁移完成，更不能替代接触资格、完整回归或科学验证。

## 现场保护与变更

- [实施前基线](evidence/repository_cleanup_v01/batch04_candidate04_source_baseline.json)记录根README、`pyproject.toml`、3个旧位置资格测试及当前稳定实现/测试的字节和SHA-256；11个声明为保护不变的文件最终身份一致。
- 新增 `src/prl/quality.py`：加载精确manifest、拒绝越界/缺失/重复/非Python路径，拒绝测试路径离开`tests/prl`或经过reparse point。
- 对`src/prl/**/*.py`和quick清单中的测试做AST检查：只允许标准库及`prl`导入；拒绝Paper2/NCS/FEniCSx、`scripts`、`sys.path`、动态文件导入和Windows/UNC机器绝对路径。
- 修改 `src/prl/cli.py`，只新增 `test quick` 分支；原`storage status`和`verify long-doublet`入口保持。
- 新增 `tests/prl/quick_suite_v01.txt` 与 `tests/prl/test_quality.py`，并为CLI增加机器JSON接口测试。
- 未修改根`README.md`、`pyproject.toml`、3个旧位置资格测试、任何C++/SimuCell3D文件、力学方程、材料或冻结阈值。

## 运行边界

quick runner固定使用当前Python解释器、`-B`、`PYTHONDONTWRITEBYTECODE=1`、`PYTEST_DISABLE_PLUGIN_AUTOLOAD=1`、`-p no:cacheprovider`及120秒超时；`PYTHONPATH`仅设为工作区`src`。这样不会因机器上任意第三方pytest插件改变当前快速门，也不会产生`.pytest_cache`或`__pycache__`。

默认pytest未切换，仍会按现有`pyproject.toml`收集整个`tests/`；审计中记录的退役Paper2/FEniCSx `basix` collection error仍保留。3个当前接触资格测试也继续留在根`tests/`，单独运行，不借quick绿灯掩盖其历史脚本依赖。

## 验收

| 检查 | 状态 | 结果 |
|---|---|---|
| `python -m prl test quick` | `passed` | 5个显式文件，17项测试，0 stderr |
| 路径与manifest边界 | `passed` | 仅`tests/prl/*.py`；拒绝`..`、缺失、重复、reparse和越界 |
| import/机器路径边界 | `passed` | 扫描13个Python文件；无退役路线、`scripts`、`sys.path`、动态导入或机器绝对路径 |
| 保护文件身份 | `passed` | 11/11字节和SHA-256一致；根README与`pyproject.toml`未改 |
| 旧位置接触资格对照 | `passed` | 3个文件、7项测试；未加入quick清单 |
| 长程独立核验 | `passed` | 13/13来源、4/4矩阵；静态平衡`failed`与父Z1 `blocked`保持 |
| 存储准入 | `blocked` | 检查时5,774,819,244 bytes，超过3 GiB硬上限；科研新任务不可启动 |
| 删除/GPU/求解器 | `not_run` | 没有删除、GPU或科学计算 |

首轮新增边界测试为`failed`：检查器把自身用于识别UNC路径的字符串常量误判为机器路径。只将该常量改为运行时构造，检测语义不变；第二轮及最终quick suite均通过。旧源、旧测试和结果没有改变。该失败同时保留在[机器验收记录](evidence/repository_cleanup_v01/batch04_candidate04_acceptance.json)。

## 未完成与下一门

- 默认pytest、包发现、根README和C++默认构建尚未切换。
- 旧测试没有分层迁移，审计中的2个默认collection error仍未修复或隐藏。
- quick suite不运行旧位置资格测试、C++ CTest、求解器或科学门；这些必须按各自入口单独验收。
- 本切片不释放空间，也不授权删除。

按已采纳顺序，下一步应是候选3第一安全切片：生成退役Paper2/NCS源码的来源保留矩阵与哈希，不删除。只有该矩阵验收后才能另行提交精确删除清单；任何删除仍需新的逐路径确认。
