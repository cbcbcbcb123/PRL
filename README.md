# PRL — cardiac cell–ECM–flow hybrid model

本仓库现在包含两条严格隔离的证据线：

1. **Route H reference/oracle**：独立闭合表面 DCM 细胞 + 独立四面体有限变形黏弹 ECM。Stage 2 Gate A 已冻结为 `failed_invalid_numerics`，Gate B–E 仍 blocked。
2. **Hybrid X0 feasibility**：验证 SimuCell3D cell engine + 独立体积 ECM 的混合架构，不覆盖 Route H 历史结果。X0-C/D 已冻结自有接口，X0-E 受控 fork 决策尚未执行。

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

长期架构决策见 `docs/adr/0001-owned-cpp-core-python-research-layer.md`，X0-C/D 冻结接口见 `docs/hybrid_architecture_v02.md`，X0-E 自有仓库拓扑见 `docs/hybrid_architecture_v03.md`。目前 X0-A–E 已完成；下一安全切片为 X1-A remesh event hook。
