# PRL — cardiac cell–ECM–flow hybrid model

本仓库现在包含两条严格隔离的证据线：

1. **Route H reference/oracle**：独立闭合表面 DCM 细胞 + 独立四面体有限变形黏弹 ECM。Stage 2 Gate A 已冻结为 `failed_invalid_numerics`，Gate B–E 仍 blocked。
2. **Hybrid X0 feasibility**：验证 SimuCell3D cell engine + 独立体积 ECM 的混合架构，不覆盖 Route H 历史结果。

目标架构：

`lumen → remeshable endocardial cells → tetrahedral ECM → remeshable myocardial cells → surroundings`

## 最小目录

- `src/route_h/`：原小规模参考力学内核；
- `src/hybrid/`：混合架构的持久材料点与耦合 seam；
- `external/simucell3d/`：固定提交的官方 SimuCell3D submodule；
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
```

混合阶段计划见 `project_control/hybrid_architecture_feasibility_plan_v01.md`。目前 X0-A 与 X0-B 已完成；X0-C 与 X0-D 尚未宣告通过。
