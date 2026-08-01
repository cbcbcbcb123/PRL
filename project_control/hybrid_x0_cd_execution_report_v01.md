---
report_id: REPORT-PRL-HYBRID-X0-CD-V01
status: completed_x0_c_x0_d
reported_at: 2026-08-01
branch: codex/simucell3d-hybrid-feasibility
decision_gate_next: X0-E
upstream_forked: false
---

# Hybrid X0-C/D 执行报告 v01

## 结论

X0-C 与 X0-D 已完成并通过冻结门槛。项目已按“自有 C++ 高性能内核 + Python 科研层”建立第一条端到端 seam，但尚未 fork 或修改上游 SimuCell3D。下一关口是 X0-E 受控 fork 决策。

## X0-C：心肌材料场与 remesh adapter 合同

新增：

- PRL-owned C++17 value types、`RemeshEvent` 和同步 `RemeshEventSink`；
- Python executable reference：区域身份、纤维方向和主动状态按 persistent material-point ID 迁移；
- split、swap、merge 三种显式语义；
- 纤维切平面投影、单位化、director 符号连续和退化 fail-fast；
- registry 与 myocardial field ID/region 一致性检查。

三种操作均得到：

| 指标 | split | swap | merge | 门槛 |
|---|---:|---:|---:|---:|
| region retention | 1.0 | 1.0 | 1.0 | 1.0 |
| active-state residual | 0 | 0 | 0 | 0 |
| fiber norm error | 0 | 0 | 0 | `<=1e-12` |
| fiber tangency error | 0 | 0 | 0 | `<=1e-12` |
| minimum fiber alignment | 1.0 | 1.0 | 1.0 | `>=1-1e-12` |
| material position error | `2.78e-17` | 0 | `1.24e-16` | `<=1e-12` |

独立 C++17 contract test 在 Linux/GCC 14.2、CMake 3.31.6 中构建并通过：`1/1 passed`。

Python 回归：`tests/hybrid` 为 `14 passed`；未修改的 Stage 0/1/2 回归为 `49 passed`。

## X0-D：单细胞—四面体 ECM 垂直切片

垂直切片包含：

- 一个经过闭合双流形检查的立方细胞表面；
- 一个可跨 cell surface remesh 重绑定的 basal material point；
- 一个独立单四面体有限变形黏弹 ECM patch；
- 一个 cell–ECM material tether；
- ECM Jacobian、作用—反作用、总能量方向导数、功率积分和穿透 fail-fast 检查。

| 指标 | observed | limit | status |
|---|---:|---:|---|
| remesh energy residual | 0 | `1e-12` | passed |
| remesh resultant-force residual | `4.03e-18` | `1e-12` | passed |
| pair force residual | `1.21e-19` | `1e-10` | passed |
| pair moment residual | `1.73e-18` | `1e-10` | passed |
| force directional-derivative residual | `2.03e-10` | `1e-6` | passed |
| normalized integrated-power residual | `1.95e-15` | `5e-3` | passed |
| minimum gap | `0.112` | `>0` | passed |
| minimum ECM Jacobian | `1.01` | `>0` | passed |

## 验证入口

```powershell
$env:PYTHONPATH = "$PWD\src"
pytest -q tests\hybrid
pytest -q tests\stage1 tests\stage2
python scripts\run_hybrid_x0_cd_probe.py
```

```bash
cmake -S cpp -B cpp/build -DBUILD_TESTING=ON
cmake --build cpp/build --parallel
ctest --test-dir cpp/build --output-on-failure
```

## 边界与未完成项

- 没有修改 `external/simucell3d`，其 submodule 仍固定在 `38af45154070b2b08dcdb25cbe629de499f382d9`；
- 当前 C++ 文件冻结 adapter 合同，尚未实现对上游 remesher 内部操作的 hook；
- Python vertical slice 是 reference/oracle，尚未宣告大规模 C++ coupled driver 完成；
- 尚未完成多细胞、主动收缩、流体、长期动态积分或生理标定；
- Route H Gate A failure freeze 与 Gate B–E blocked 状态保持不变。

## X0-E 输入

上游目前没有逐 split/swap/merge 的通用事件 hook，而冻结合同要求每个已接受拓扑操作同步产生 PRL-owned snapshot 事件。因此 X0-E 已具备“需要受控 fork”的直接架构证据；是否正式创建 fork、确定维护策略和生产迁移范围由 X0-E 决策记录处理。
