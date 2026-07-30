# PRL — Route H passive DCM–ECM model

本仓库当前实现早期心室平面 patch 的 Stage 1 无量纲被动力学内核：

`lumen → endocardial closed-surface DCM → finite-strain viscoelastic ECM → myocardial closed-surface DCM → compliant surroundings`

模型使用独立 watertight 三角曲面细胞、独立四面体 ECM、动态 closed-surface
steric、冻结 material tether、心内膜 pressure/WSS 端口和固定参考
Kelvin–Voigt 支撑。ECM amount 与 natural thickness 冻结，`j_myo=0`。

当前权威科学输入是 Stage 0 v05；v05 只修复 binary64 对称角 face-identity
并列规则，不改变 v04 的拓扑、方程、参数或接触机制。Stage 1 只允许 reference
materialization 和被动模块/制造解验证：

- active preferred-length contraction：未启用；
- full-patch trajectory：未运行；
- Stage 2 Gate A–E：未授权；
- 生理标定和论文 claim：未进行。

最简目录：

- `src/route_h/`：被动核心模块和冻结合同；
- `data/route_h/stage1_reference_bundle_v01/`：canonical reference arrays 与 hash seal；
- `tests/stage1/`：可执行模块/制造解测试；
- `tests/route_h/`：冻结 registry 与机器可读证据；
- `docs/route_h/`：坐标、符号和功率账本；
- `project_control/`：授权、冻结、检查和阶段记录；
- `scripts/`：可复算 materialization/verification 工具。

复算：

```powershell
$env:PYTHONPATH = "$PWD\src"
pytest -q
python scripts\route_h_stage1_verification_evidence.py
```
