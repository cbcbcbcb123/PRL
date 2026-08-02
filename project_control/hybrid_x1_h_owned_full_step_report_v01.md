---
report_id: REPORT-PRL-HYBRID-X1-H-V01
status: passed_frozen
completed_at: 2026-08-02
parent_branch: codex/simucell3d-hybrid-feasibility
cell_engine_branch: codex/cell-engine-integration-seam
cell_engine_commit: b8828da18bfda62f28cece95027ba65edd431a0f
result_id: PRL-HYBRID-X1-H-OWNED-FULL-STEP-V01
governed_by: CONSTRAINT-PRL-EXTERNAL-SCIENTIFIC-REVIEW-V01
---

# Hybrid X1-H owned 完整单步报告 v01

## 结论

X1-H 已完成并冻结。PRL owned driver 现按固定顺序执行当前几何刷新、真实 face-face 接触装配、真实 `cell::apply_internal_forces(dt)` 被动力装配、主动心肌力装配、一次过阻尼位置提交，以及步后 face/node/cell 几何缓存刷新。Route H Gate A v01 失败包未修改。

## TDD 证据

1. **RED 1**：真实 cell 集成 tracer 首先因 owned-step 公共头不存在而编译失败；最小入口接通后，被动力、主动增量和步后几何缓存进入 GREEN；
2. **RED 2**：真实接触行为最初被 owned driver 明确拒绝；启用受限 contact context 后继续要求实际接触力非零，不使用 mock；
3. **RED 3**：普通非原点接触面产生零力，诊断定位到上游点—三角形最近点公式不具平移不变性；修正公式并新增非原点三角形单测后，真实接触进入 GREEN；
4. **RED 4**：步后 node normal/curvature tracer 因缓存未刷新而失败；将 node 几何刷新纳入同一成功提交后进入 GREEN；
5. **failure path**：制造“被动力已装配、主动输入功率随后溢出”的失败，异常原样传播，位置不提交、力缓存清零、几何缓存与未移动位置一致；
6. **geometry atomicity**：制造把 tetrahedron 顶点移到另一顶点的退化 pending geometry，验证位置与原有力均不被部分提交。

## 冻结单步合同

详见 `docs/hybrid_architecture_v11.md`。接触入口收窄为真实 `contact_face_face_via_coupling`，仅允许一个 mobile target 与静态接触体；epithelial–epithelial 位置耦合在 X1-H 被拒绝。调用期间遵守 one-cell/one-owner。

被动力包括当前 stock cell 路径中的 pressure、surface tension/membrane、bending 与 angle regularization 等已启用分量。具体非零分量由 cell/face 参数决定；X1-H 没有新增或标定生物学参数。

## 定量与回归结果

| 检查 | 结果 |
|---|---:|
| real-cell used vertices / faces | `8 / 12` |
| time step / uniform node damping | `1e-3 / 10` |
| passive-only path passive-force L2 | `1.50084` |
| passive+active total-force / displacement L2 | `1.8092 / 1.80920e-4` |
| real-contact target-force L2 | `40` |
| contact context net-force residual | `0` |
| contact context net-moment residual | `1.77636e-15` |
| contact+passive+active total-force / displacement L2 | `40.7549 / 4.07549e-3` |
| collapsed pending geometry atomic rejection | passed |
| post-assembly active-audit failure cleanup | passed |
| parent C++ CTest | `29/29 passed` |
| fork standalone CTest | `132/132 passed` |
| owned parent core strict warnings | `13/13 passed` |
| fork X1-H translation units strict compile | passed with inherited ignored-qualifiers and unused-parameter warnings downgraded |
| parent Python | `63 passed` |
| tracked Python Ruff | passed |

`W_F=D_zeta` 仍只是冻结离散式的代数恒等式。本阶段没有把它解释为稳定性或能量收敛证据。

## 已登记限制

- 当前阻尼是每节点统一 `zeta`，可能随网格加密改变动力学时间尺度；进入任何连续轨迹前必须完成 X1-I；
- 当前没有 `DeltaPsi_remesh`，split/swap/merge 的伪能量与循环漂移必须在 X1-J 单独记账；
- 当前没有时间/空间 refinement、体积误差、质心漂移、最小 Jacobian/三角质量、穿透或离散能量不等式门禁；这些属于 X1-K；
- stock `solver::run_iteration` 尚未自动调用 owned driver；
- upstream passive/contact 内核保留 `noexcept`/assert 边界，进程级 assertion 不能由此入口转为可捕获异常；
- pressure/WSS、ECM 相态、EFE 反馈与谱系来源等科学边界遵守外审约束文件。

## Git 与同步

受控 fork 功能提交 `69da1f9` 与步后 node 几何补充提交 `b8828da18bfda62f28cece95027ba65edd431a0f` 已推送到 `origin/codex/cell-engine-integration-seam`。父项目冻结提交与同步在本报告入库后完成。

## Claim guard

X1-H 只证明一个无量纲、单 cell、单步的真实力装配—位置提交—几何刷新软件路径及其受控失败行为。它不证明稳定收缩轨迹、阻尼空间一致性、重网格能量一致性、完整 cell–ECM/血流耦合、EFE 双稳态/机械记忆、发育机制、参数可识别性或生理预测；Route H Gate A v01 仍为 `failed_invalid_numerics`。
