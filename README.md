# PRL — cardiac cell–ECM–flow hybrid model

## 当前论文主线（2026-08-27）

当前优先级是独立的 **PRL 理论论文**：研究主动心肌—有限厚度黏弹夹层—被动心内膜边界之间的周期机械传递、相位滞后、耗散和离散—连续适用边界。**EFE Nature** 调整为独立的实验疾病论文；它可向 PRL 提供有限校准与独立验证，但只有在 PRL 理论版本发表/冻结后，才把该框架用于 EFE 的前瞻盲验证、谱系、Gate X 与人源机制研究。现行决定见 `project_control/prl_independent_theory_mainline_decision_v01.md`，执行计划见 `project_control/prl_independent_theory_mainline_plan_v01.md`。历史 EFE Node 记录和冻结证据全部保留。

本仓库现在包含两条严格隔离的证据线：

1. **Route H reference/oracle**：独立闭合表面 DCM 细胞 + 独立四面体有限变形黏弹 ECM。Stage 2 Gate A 已冻结为 `failed_invalid_numerics`，Gate B–E 仍 blocked。
2. **Hybrid X0–X1 implementation**：采用 PRL 自有 cell engine + 独立体积 ECM 的混合架构，不覆盖 Route H 历史结果。X0-A–E 已完成；X1-A–J 的逐级接口均在各自 coverage 内冻结。X1-K v01/v02/v03 的历史失败均保留。v04 已在受控 fork 将 excluded legacy surface-tension cache 精度由 float 提升为 double，修复后 Family A 原门禁全部通过；固定 SPD Family B 的方向、legacy cache、global normal/tangential L2 与 force balance 通过，但 source levels 2–4 的 `h_max/h_min` 超过冻结上限 `2.0`，因此 v04 正确冻结为 `failed_family_B_parameterized_diagnosis`。X1-K 仍未通过，smooth S1 与 R1/C1/F1 均未执行。

M1 单细胞阶段探针已进一步走通 20% 位移控制平衡：端部严格缩短 20%，内部节点求约束平衡，体积用等式约束精确保持，原六区域面积惩罚改为单一全局软面积弹性，网格质量由独立参考角正则项维护。面积刚度 `0/0.1/1.0` 三组均通过几何与 KKT 门槛；该结果是被动力学试验，不覆盖上述冻结 gate，也尚不是主动收缩心肌细胞。记录见 `project_control/m1_displacement_equilibrium20_global_area_v01.md`。

进一步的50%应力测试也在三组参数下数值到达终点，体积与KKT约束仍通过，但约32–36%开始出现网格面积局部化和反力曲线拐折，50%最小面面积比仅为 `0.058–0.060`，接近 `0.05` 失效门槛。因此该结果登记为“数值完成、网格质量警告”，不能作为50%形态或反力已网格无关的证据。记录见 `project_control/m1_displacement_equilibrium50_global_area_v01.md`。

M1现已从外部位移控制推进到内部主动材料驱动。新的分布式轴向主动度量作用于全部表面网格边，替代单根端到端虚拟弹簧；在无外载、精确体积约束下，20%局部主动应变产生15.6764%整细胞缩短和7.2240%/9.8571%横向膨胀，峰值最小面面积比0.877，舒张后恢复参考形态。该周期仍是无时间、无耗散的准静态基线，下一步为黏性时间推进与负载响应。记录见 `project_control/m1_distributed_active_cycle20_v01.md`。

过阻尼动态v01也已走通：20步/周期、阻尼1.0的未标定基线产生15.0093%最大缩短，缩短峰值比激活峰值滞后0.05个周期，周期末保留1.6615%动态残余，体积与几何门槛均通过。但一阶时间离散耗散占总算法损失43.30%，因此只接受“存在黏性相位滞后”的定性结论，能量与相位的定量门仍未通过。下一步必须进行时间步收敛或改进时间积分。记录见 `project_control/m1_distributed_active_dynamic_v01.md`。

20/40/80步每周期的时间收敛现已完成。二次插值最大缩短依次为15.0172%/15.1689%/15.2485%，相位延迟为5.8484%/5.9777%/6.0284%周期；数值耗散占总算法损失由43.30%降至27.42%和15.81%，但80步仍未达到10%暂定门槛。数值耗散/物理耗散的估计收敛阶为1.016和1.009，确认当前积分器严格是一阶。停止继续到160步，下一步改用二阶或能量一致时间积分。记录见 `project_control/m1_dynamic_time_convergence_v01.md`。

二阶 Crank–Nicolson 动态积分现已通过 M1 时间精度门。20/40/80 步的插值峰值缩短为 15.3289%/15.3300%/15.3303%，相位延迟为 6.1073%/6.0766%/6.0709% 周期；采用同一梯形主动功账本后，逐步绝对能量缺陷占正主动输入仅为 0.2474%/0.0624%/0.0156%，两次加密的观测阶为 1.988 和 1.996。三组均保持约 `1e-13` 体积误差、健康网格和非负物理耗散。下一步在单细胞范围内验证多周期极限环，再进入参数化外部负载。记录见 `project_control/m1_dynamic_crank_nicolson_v01.md`。

多周期极限环现已通过M1门。20步×6周期探索和40步×5周期正式复核均在第4周期满足连续两次周期转移收敛；正式第4周期的峰值缩短为15.33023%，相位延迟为6.07499%周期，周期零相位缩短稳定为1.366262%。第4周期与第3周期的整周期波形差为`3.19e-9`，周期末全节点状态差为`5.96e-9`；净主动功与物理黏性耗散相对差仅0.00958%。因此周期末非零缩短是连续周期驱动下的稳定相位状态，不是累积塑性变形。下一步进入参数化外部弹性/黏性负载。记录见 `project_control/m1_dynamic_limit_cycle_v01.md`。

目标架构：

`lumen → remeshable endocardial cells → tetrahedral ECM → remeshable myocardial cells → surroundings`

## 科学时间尺度与论文目标

项目先研究固定发育时期的快速心搏力学，再在快速证据链通过后加入发育时间尺度的生长与重塑。
工程阶段和数值 gate 是证据门，不自动对应独立论文。当前主论文候选以固定时期的
心肌—cardiac-jelly—心内膜动力学为核心，并以 `Nature Physics` 为最高投稿目标；慢发育模型只有形成
独立的“快速力学 → 慢生长/重塑”反馈定律并经人类终审批准后，才建立第二篇论文候选。完整规则见
`project_control/publication_and_timescale_strategy_v01.md`。

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

长期架构决策见 `docs/adr/0001-owned-cpp-core-python-research-layer.md`，X0-C/D 冻结接口见 `docs/hybrid_architecture_v02.md`，X0-E 自有仓库拓扑见 `docs/hybrid_architecture_v03.md`，X1-A–J 的递进冻结见 `docs/hybrid_architecture_v04.md` 至 `docs/hybrid_architecture_v13.md`；X1-K v01–v04 冻结见 `docs/hybrid_architecture_v14.md` 至 `docs/hybrid_architecture_v17.md`。外部科学评审后的硬约束见 `project_control/external_scientific_review_constraints_v01.md`，v04 合同见 `project_control/hybrid_x1_k_legacy_cache_repair_contract_v04.md`。当前不得继续 ECM/血流长耦合、参数标定或论文机制 claim，也不得把 instrumentation repair 或 global L2 局部 gate 通过描述为 X1-K、pointwise convergence、完整短轨迹或稳定收缩轨迹已经验证。
