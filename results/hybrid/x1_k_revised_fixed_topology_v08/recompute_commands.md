# X1-K v08 复算命令

从仓库根目录执行：

```powershell
$env:PYTHONPATH='src'
python -m pytest -q tests/hybrid/test_x1k_v08_adjudication.py
python scripts/adjudicate_x1k_v08.py --workspace . --output-dir results/hybrid/x1_k_revised_fixed_topology_v08
python -m ruff check src/hybrid/fixed_topology_adjudication.py tests/hybrid/test_x1k_v08_adjudication.py scripts/adjudicate_x1k_v08.py
```

机器包核验：

```powershell
python -m json.tool results/hybrid/x1_k_revised_fixed_topology_v08/summary.json
python -m json.tool results/hybrid/x1_k_revised_fixed_topology_v08/provenance_manifest.json
$decisionRows = Import-Csv -LiteralPath 'results/hybrid/x1_k_revised_fixed_topology_v08/decision_matrix.csv'
$decisionRows | Group-Object role | Select-Object Name,Count
$decisionRows | Where-Object { $_.role -eq 'revised_acceptance' -and $_.passed -ne 'true' }
```

完整回归：

```powershell
docker run --rm --entrypoint sh -v "${PWD}:/workspace" -w /workspace prl-simucell3d-x0:38af451 -lc "cmake --build cpp/build-linux-x1h -j2 && ctest --test-dir cpp/build-linux-x1h --output-on-failure"
docker run --rm --entrypoint sh -v "${PWD}:/workspace" -w /workspace/external/simucell3d prl-simucell3d-x0:38af451 -lc "cmake --build build-x1k-v04 -j2 && ctest --test-dir build-x1k-v04 --output-on-failure"
docker run --rm --entrypoint sh -v "${PWD}:/workspace" -w /workspace prl-simucell3d-x0:38af451 -lc "cmake --build cpp/build-linux-x1h-strict --target prl_core -j2"
$env:PYTHONPATH='src'; python -m pytest -q
python -m ruff check src/hybrid/fixed_topology_adjudication.py tests/hybrid/test_x1k_v08_adjudication.py scripts/adjudicate_x1k_v08.py
```

Parent CTest 必须继续保留 v02 D1、v04 Family B、v06 Family C 三个历史科学失败；不得改成 xfail 或删除。
