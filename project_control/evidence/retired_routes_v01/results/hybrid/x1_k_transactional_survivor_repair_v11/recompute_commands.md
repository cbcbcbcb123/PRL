# X1-K v11 复算命令

在项目根目录 `E:\Temp-Projects\PRL` 使用 PowerShell 依次执行：

```powershell
python scripts/export_x1k_v11_evidence.py red
python scripts/export_x1k_v11_evidence.py cpp
python scripts/export_x1k_v11_evidence.py fork
python scripts/export_x1k_v11_evidence.py python
python scripts/export_x1k_v11_evidence.py strict
python scripts/export_x1k_v11_evidence.py ruff
python scripts/export_x1k_v11_evidence.py seal
```

运行条件：Docker image `prl-simucell3d-x0:38af451` 可用，Python 环境包含 Pytest 与 Ruff。`python` 阶段约需 9–10 分钟；当前 v11 工作树中唯一允许的 Python 失败是 v10 的 clean-fork 历史来源守卫，日志必须精确为 `1 failed, 120 passed` 且错误为 `controlled fork is dirty`。封存器会把任何额外失败判为 `failed_v11_verification`。

复算会更新本 v11 目录中的日志和摘要，但不会修改 v08r1、v09 或 v10 旧结果目录。
