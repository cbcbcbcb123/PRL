# PRL — cardiac cell–ECM–flow hybrid model

本仓库现在包含两条严格隔离的证据线：

1. **Route H reference/oracle**：独立闭合表面 DCM 细胞 + 独立四面体有限变形黏弹 ECM。Stage 2 Gate A 已冻结为 `failed_invalid_numerics`，Gate B–E 仍 blocked。
2. **Hybrid X0–X1 implementation**：采用 PRL 自有 cell engine + 独立体积 ECM 的混合架构，不覆盖 Route H 历史结果。X0-A–E 已完成；X1-A–C 已冻结真实 remesher—材料迁移 C++ 闭环，X1-D 已冻结多细胞规模、并发确定性与性能基线，X1-E 已冻结单细胞主动能量/力/功率端口，X1-F 已冻结主动力进入真实 cell-engine force buffer 的装配 seam，X1-G 已冻结一次原子主动过阻尼更新，X1-H 已冻结 PRL owned driver 中真实接触力、真实被动力、主动力、位置提交与派生几何缓存刷新组成的完整单步。

目标架构：

`lumen → remeshable endocardial cells → tetrahedral ECM → remeshable myocardial cells → surroundings`

## 最小目录

- `src/route_h/`：原小规模参考力学内核；
- `src/hybrid/`：混合架构的持久材料点与耦合 seam；
- `cpp/`：PRL 自有 C++17 高性能内核的公共合同与测试；
- `external/simucell3d/`：固定提交的 PRL 受控 fork submodule；官方基线通过 fork 的 `upstream/main` 与 immutable tag 保留；
- `tests/stage1/`, `tests/stage2/`, `tests/hybrid/`：可执行验证；
- `docs/`：模型与架构说明；
- `project_control/`：计划、冻结边界和阶段记录；
- `results/`：小型、可审计的正式结果摘要；
- `scripts/`：可复算入口。

## 当前可复算入口

```powershell
git submodule update --init --recursive
$env:PYTHONPATH = "$PWD\src"
pytest -q tests/hybrid
pytest -q tests/stage1 tests/stage2
python scripts\run_hybrid_x0_probe.py
python scripts\run_hybrid_x0_cd_probe.py
```

X1-D Release 基准入口：

```powershell
cmake -S cpp -B cpp/build-release -DCMAKE_BUILD_TYPE=Release
cmake --build cpp/build-release --target prl_multicell_remesh_benchmark
python scripts/run_hybrid_x1_d_benchmark.py --executable cpp/build-release/prl_multicell_remesh_benchmark --build-type Release
```

长期架构决策见 `docs/adr/0001-owned-cpp-core-python-research-layer.md`，X0-C/D 冻结接口见 `docs/hybrid_architecture_v02.md`，X0-E 自有仓库拓扑见 `docs/hybrid_architecture_v03.md`，X1-A–H 的递进冻结见 `docs/hybrid_architecture_v04.md` 至 `docs/hybrid_architecture_v11.md`。外部科学评审后的硬约束见 `project_control/external_scientific_review_constraints_v01.md`。后续必须依次完成 X1-I 阻尼空间一致性、X1-J `DeltaPsi_remesh` 账本与循环漂移、X1-K 短轨迹数值门禁；X1-K 通过前不进入 ECM/血流长耦合、参数标定或论文机制 claim。当前 stock solver 尚未自动调用 owned 路径，也没有经时间/空间 refinement 验证的稳定收缩轨迹。
