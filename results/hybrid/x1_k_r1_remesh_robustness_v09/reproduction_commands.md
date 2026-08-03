# X1-K v09 R1 复算命令

以下命令均从仓库根目录执行。正式 R1 响应按冻结语义返回 `1`；回归测试断言该精确失败并返回 `0`。

```powershell
docker run --rm --entrypoint sh -v "${PWD}:/workspace" -w /workspace `
  prl-simucell3d-x0:38af451 -lc `
  "cmake -S cpp -B cpp/build-linux-x1k-v09 -DBUILD_TESTING=ON -DPRL_BUILD_CELL_ENGINE_INTEGRATION_TESTS=ON -DCMAKE_BUILD_TYPE=Release && cmake --build cpp/build-linux-x1k-v09 --target prl_x1k_r1_remesh_robustness_integration_test -j2"

docker run --rm --entrypoint sh -v "${PWD}:/workspace" -w /workspace `
  prl-simucell3d-x0:38af451 -lc `
  "cpp/build-linux-x1k-v09/prl_x1k_r1_remesh_robustness_integration_test --formal-response"

docker run --rm --entrypoint sh -v "${PWD}:/workspace" -w /workspace `
  prl-simucell3d-x0:38af451 -lc `
  "ctest --test-dir cpp/build-linux-x1k-v09 -V -R '^prl_x1k_v09_r1_real_remesh_robustness$'"

$env:PYTHONPATH = "src"
python scripts/export_x1k_r1_v09.py `
  --evidence-dir results/hybrid/x1_k_r1_remesh_robustness_v09/verification `
  --output-dir results/hybrid/x1_k_r1_remesh_robustness_v09
```

完整验证的原始命令输出与退出码位于 `verification/`；`verification_summary.json` 从这些文件解析计数和失败集合，不使用硬编码测试数。
