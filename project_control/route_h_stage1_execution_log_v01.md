---
execution_id: EXEC-PRL-ROUTE-H-STAGE1-V01
plan_id: PLAN-PRL-ROUTE-H-DCM-ECM-STAGE0-STAGE2-V01
authorization_id: DEC-PRL-ROUTE-H-STAGE1-AUTHORIZATION-V01
executor: Codex current task; governed single-worker execution
started_at: 2026-07-30T19:52:50+08:00
completed_at: 2026-07-30T20:50:00+08:00
status: completed_pending_freeze_and_readonly_inspection
working_branch: codex/stage1-passive-kernel
checkpoint_commit: b73745a923f5003b3b342dc70969c2f4a10ab1ab
---

# Route H Stage 1 被动内核执行记录 v01

## 1. 授权与边界

用户明确批准 Phase 1 / Stage 1。执行范围为 reference bundle、被动 DCM、有限变形
黏弹 ECM、contact/adhesion、loads/support、source-map、gauge、ledger 和模块测试。

始终保持：

- active preferred-length mechanism 未启用；
- full-patch trajectory 未运行；
- Stage 2 未授权；
- `j_myo=0`，无 turnover、标定、参数扫描或论文 claim；
- v01–v04 冻结件未修改；
- 无删除、force push 或 Git 历史重写。

## 2. 预物化阻断及 v05 勘误

v04 materialization 的 998 个 same-layer neighbor master ray 检查发现 10 个重复失败。
根因是 8 个数学上三轴等权的 corner direction 受到 binary64 1 ULP 舍入影响，
使镜像 face 63/159 获得不同 face identity。

在不覆盖 v04 的前提下新增并冻结 Stage 0 v05：

- `8*eps_binary64` 内视为绝对分量并列；
- 固定 `z → x → y` 优先级；
- 只改变 8 个 corner material label；
- 坐标、拓扑、方程、参数、contact/load/source-map 均不变。

v05 检查后 998/998 ray 合法，阻断关闭。该修复是确定性离散身份勘误，不是科学路线替换。

## 3. Reference bundle

生成 22 个 canonical binary64/int64 数组和 canonical metadata：

- 15 个 cell：每个 162 vertices / 320 oriented faces；
- ECM：351 vertices / 1152 positive tetrahedra / 544 exterior faces；
- 1828 material tether records；
- 504 myocardial zero-flux source-map records；
- boundary owner、traction-free owner 和 gauge weight arrays。

bundle SHA-256 seal：
`4A73D370162D8EBFB7B120C42881F7470D68E82D10ABD159CB65C2B73ADECC59`。

Windows CRLF 会在 Git 入库时规范为 LF。为避免重新检出后 v05 hash 失效，生成器改为
显式 UTF-8/LF 字节输出，随后从头重建 v05 freeze hash 链并确认 staged blob 与
working bytes 8/8 一致。

## 4. 被动内核

核心实现位于 `src/route_h/`：

- `geometry.py`：deterministic cell/ECM、identity、tether/source-map、bundle seal；
- `dcm_cell.py`：area、oriented hinge bending、volume 及解析 nodal force；
- `ecm_finite_strain.py`：compressible isochoric equilibrium/viscoelastic stress、`Z` relaxation；
- `contact_adhesion.py`：global closest owner、winding sign、steric、material tether、CCD；
- `coupling.py`：AABB search、ordered pair、zero `j_myo` assembly；
- `loads.py`：current-area pressure/WSS 与 fixed Kelvin–Voigt support；
- `gauge.py`：全局六约束零功率 gauge；
- `ledger.py`：stored/dissipation/external power 与 integrated residual；
- `solver.py`：唯一 passive reference/local manufactured 入口和授权 guard。

## 5. 测试修复记录

1. CCD manufactured endpoint tangency 首轮测试把恒零 coplanarity polynomial 传入
   求根器；修订为恒零无 oriented-side sign crossing。
2. Reference static intersection 初筛把 basal vertex–ECM plane 的
   `~10^-18` 浮点侧号当作 transverse crossing；按几何尺度归一 tolerance，并按合同
   排除 vertex-only zero-measure tangency。复核后 16 个 target self-intersection 与
   46 个 eligible entity-pair proper crossing 均为 0。
3. Windows line-ending hash 漂移按第 3 节修复。

以上修订没有改变 contact potential、tether identity、参数或接受阈值。

## 6. 最终证据

- `pytest`：31 passed，0 failed/error/skipped；
- Ruff：all checks passed；
- Stage 1 registry terminal status：37 passed，3 scope-correct not-run；
- minimum cell triangle quality：0.3460311354（阈值 0.30）；
- minimum anchor length：0.9821932172（阈值 0.80）；
- minimum ECM `J`：1.0；
- eligible steric pairs / owners：46 / 16584；
- proper intersection：0；
- reference steric energy：0；
- maximum tether opening/slip/force：
  `4.44e-16 / 2.19e-17 / 2.73e-17`；
- assembled net force/moment：
  `7.58e-31 / 2.91e-30`；
- active enabled：false；
- full-patch trajectory run：false。

机器可读证据：

- `tests/route_h/stage1_pytest_junit_v01.xml`；
- `tests/route_h/stage1_metrics_v01.json`；
- `tests/route_h/stage1_verification_results_v01.csv`。

下一步是 Stage 1 冻结和冻结后只读检查。Stage 2 仍不授权。

