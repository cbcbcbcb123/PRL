# X1-K v07 复算命令

从仓库根目录执行：

```powershell
docker run --rm --entrypoint sh -v "${PWD}:/workspace" -w /workspace prl-simucell3d-x0:38af451 -lc "cmake --build cpp/build-linux-x1h --target prl_short_trajectory_integration_test -j2"
docker run --rm --entrypoint sh -v "${PWD}:/workspace" -w /workspace prl-simucell3d-x0:38af451 -lc "ctest --test-dir cpp/build-linux-x1h -V -R '^prl_x1k_v07_four_level_structural_identity_gate$'"
Copy-Item -LiteralPath 'cpp/build-linux-x1h/Testing/Temporary/LastTest.log' -Destination 'results/hybrid/x1_k_mean_radius_v07/structural_ctest_output.txt'
docker run --rm --entrypoint sh -v "${PWD}:/workspace" -w /workspace prl-simucell3d-x0:38af451 -lc "ctest --test-dir cpp/build-linux-x1h -V -R '^prl_x1k_v07_family_c_mean_radius_time_floor_gate$'"
Copy-Item -LiteralPath 'cpp/build-linux-x1h/Testing/Temporary/LastTest.log' -Destination 'results/hybrid/x1_k_mean_radius_v07/time_ctest_output.txt'
python scripts/export_x1k_v07_diagnosis.py --structural-log results/hybrid/x1_k_mean_radius_v07/structural_ctest_output.txt --time-log results/hybrid/x1_k_mean_radius_v07/time_ctest_output.txt --output-dir results/hybrid/x1_k_mean_radius_v07
```

完整验证：

```powershell
docker run --rm --entrypoint sh -v "${PWD}:/workspace" -w /workspace prl-simucell3d-x0:38af451 -lc "cmake --build cpp/build-linux-x1h -j2 && ctest --test-dir cpp/build-linux-x1h --output-on-failure"
docker run --rm --entrypoint sh -v "${PWD}:/workspace" -w /workspace/external/simucell3d prl-simucell3d-x0:38af451 -lc "cmake --build build-x1k-v04 -j2 && ctest --test-dir build-x1k-v04 --output-on-failure"
docker run --rm --entrypoint sh -v "${PWD}:/workspace" -w /workspace prl-simucell3d-x0:38af451 -lc "cmake -S cpp -B cpp/build-linux-x1h-strict -DPRL_WARNINGS_AS_ERRORS=ON && cmake --build cpp/build-linux-x1h-strict --target prl_core -j2"
$env:PYTHONPATH='src'; python -m pytest -q
python -m ruff check scripts/export_x1k_v07_diagnosis.py
```

完整 parent CTest 预期保留三个历史科学失败：v02 D1、v04 Family B、v06 Family C。它们不属于 v07 的意外回归。
