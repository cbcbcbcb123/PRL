# PRL — cardiac cell–ECM–flow hybrid model

本仓库现在包含两条严格隔离的证据线：

1. **Route H reference/oracle**：独立闭合表面 DCM 细胞 + 独立四面体有限变形黏弹 ECM。Stage 2 Gate A 已冻结为 `failed_invalid_numerics`，Gate B–E 仍 blocked。
2. **Hybrid X0–X1 implementation**：采用 PRL 自有 cell engine + 独立体积 ECM 的混合架构，不覆盖 Route H 历史结果。X0-A–E 已完成；X1-A–J 的逐级接口均在各自 coverage 内冻结。X1-K 的主动固定拓扑时间 refinement 通过，但表面张力 cube 的 area/registered-energy 空间 refinement 出现约负一阶行为，已按预冻结合同停止并记为 `failed_spatial_refinement_nonconvergent_area_energy`；R1/C1/F1 未继续执行。

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

长期架构决策见 `docs/adr/0001-owned-cpp-core-python-research-layer.md`，X0-C/D 冻结接口见 `docs/hybrid_architecture_v02.md`，X0-E 自有仓库拓扑见 `docs/hybrid_architecture_v03.md`，X1-A–J 的递进冻结见 `docs/hybrid_architecture_v04.md` 至 `docs/hybrid_architecture_v13.md`；X1-K 失败冻结见 `docs/hybrid_architecture_v14.md`。外部科学评审后的硬约束见 `project_control/external_scientific_review_constraints_v01.md`，X1-K 预冻结验收合同见 `project_control/hybrid_x1_k_acceptance_contract_v01.md`。当前不得继续 ECM/血流长耦合、参数标定或论文机制 claim，也不得把 T1 通过描述为完整短轨迹或稳定收缩轨迹已经验证。
