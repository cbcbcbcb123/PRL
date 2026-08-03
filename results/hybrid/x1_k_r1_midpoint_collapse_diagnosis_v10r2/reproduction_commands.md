# X1-K v10r2 packaging-evidence repair reproduction

```powershell
$env:PYTHONPATH = "src"
python -m pytest tests/test_r1_midpoint_packaging_repair_v10r2.py -q
python scripts/run_x1k_v10r2_combined_verification.py --repo-root . --controlled-parent-root "E:\Temp-Projects\PRL" -- -q
python scripts/export_x1k_r1_v10r2.py
python -m ruff check src/hybrid/r1_midpoint_packaging_repair_v10r2.py scripts/run_x1k_v10r2_combined_verification.py scripts/export_x1k_r1_v10r2.py tests/test_r1_midpoint_packaging_repair_v10r2.py
```

这些命令只验证冻结日志、Git blob、包装代码与 Python 测试；不得运行 C++、microprobe 或 formal response。
