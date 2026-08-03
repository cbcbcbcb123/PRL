# X1-K v10 reproduction commands

```powershell
docker run --rm --entrypoint sh -v "${PWD}:/workspace" -w /workspace `
  prl-simucell3d-x0:38af451 -lc `
  "cmake -S cpp -B cpp/build-linux-x1k-v10 -DBUILD_TESTING=ON -DPRL_BUILD_CELL_ENGINE_INTEGRATION_TESTS=ON -DCMAKE_BUILD_TYPE=Release && cmake --build cpp/build-linux-x1k-v10 --target prl_x1k_v10_midpoint_collapse_diagnostic_test -j2"

docker run --rm --entrypoint sh -v "${PWD}:/workspace" -w /workspace `
  prl-simucell3d-x0:38af451 -lc `
  "cpp/build-linux-x1k-v10/prl_x1k_v10_midpoint_collapse_diagnostic_test --formal-response"

docker run --rm --entrypoint sh -v "${PWD}:/workspace" -w /workspace `
  prl-simucell3d-x0:38af451 -lc `
  "ctest --test-dir cpp/build-linux-x1k-v10 -V -R '^prl_x1k_v10_midpoint_collapse_microprobe$'"

$env:PYTHONPATH = "src"
python scripts/export_x1k_r1_v10.py `
  --repo-root . `
  --raw-dir results/hybrid/x1_k_r1_midpoint_collapse_diagnosis_v10/raw `
  --output-dir results/hybrid/x1_k_r1_midpoint_collapse_diagnosis_v10 `
  --verification-dir results/hybrid/x1_k_r1_midpoint_collapse_diagnosis_v10/verification
```

`--formal-response` 预期退出 1；focused regression 预期退出 0，并断言冻结失败没有消失。
