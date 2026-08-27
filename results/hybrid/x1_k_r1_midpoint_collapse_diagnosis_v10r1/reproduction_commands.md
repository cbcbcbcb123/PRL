# X1-K v10r1 packaging repair recomputation commands

本包只读取并核验冻结 v10 文件；无需也不得重跑 C++ 科学响应、microprobe 或 formal R1 response。

```powershell
$env:PYTHONPATH = "src"
python scripts/export_x1k_r1_v10r1.py --repo-root . --output-dir results/hybrid/x1_k_r1_midpoint_collapse_diagnosis_v10r1
python -m pytest tests/test_r1_midpoint_packaging_repair.py -q
$controlledParentRoot = "PATH_TO_EXISTING_PARENT_WORKTREE_WITH_POPULATED_CONTROLLED_FORK"
python scripts/run_x1k_v10r1_python_tests.py --controlled-parent-root $controlledParentRoot -- -q
ruff check .
```
