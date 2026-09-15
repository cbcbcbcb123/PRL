# Route H Stage 0 v03 冻结记录

## 1. 冻结结论

- 冻结记录 ID：`FREEZE-PRL-ROUTE-H-STAGE0-V03`
- 冻结日期：2026-07-30（Asia/Shanghai）
- 冻结状态：`frozen_stage0_pending_independent_inspection`
- 合同：`CONTRACT-PRL-ROUTE-H-STAGE0-V03`
- 特化：`SPECIALIZATION-PRL-ROUTE-H-STAGE0-V03`
- 用例：`CASES-PRL-ROUTE-H-STAGE0-V03`
- 几何：`GEOMETRY-PRL-ROUTE-H-STAGE0-V03`
- v02 检查报告 7 项：已在 v03 规范层修订并通过静态复核。
- 参考网格实例：未生成，且未授权生成。
- Stage 1：未授权。
- Stage 2：未授权。

本轮依据用户在 v02 检查结论后的指示“继续下一步”，创建并冻结 v03；该指示不解释为 Stage 1 授权。

## 2. 冻结清单

| # | 路径 | 字节数 | SHA-256 |
|---:|---|---:|---|
| 1 | `data/route_h/route_h_reference_geometry_spec_v03.json` | 20112 | `0ECE1ED6DE89453126776C449144A62B7FEC94D0FA80CCA40C538963179FD1CF` |
| 2 | `src/route_h/route_h_contract_v03.json` | 16020 | `7DC166E0D14A66682CA6E0DE6B41D1A62569691AE24BA476FA89D3C7DC2E08B3` |
| 3 | `src/route_h/route_h_model_specialization_v03.json` | 5986 | `FEAB21897161D17C04C2E908BF4EABFDF05F2DBD5882A58DE1D34EAD5B06B6BB` |
| 4 | `data/route_h/route_h_cases_v03.json` | 13511 | `8FD5F63FA63DB37C7F2D5FBA0D1F0029F4F921D317E44DB85754F09FD20EDFD4` |
| 5 | `docs/route_h/route_h_coordinate_and_sign_convention_v03.md` | 6520 | `E0A477DFC247448F7BEA69D7683AB1DC42EB52360F8AC1BFD05B247F7F81A1FA` |
| 6 | `docs/route_h/route_h_port_and_power_ledger_v03.csv` | 6784 | `886BE9D084F49E7FAE28A935C00E6C02A9BBB091D0C4975381C805D505434BA8` |
| 7 | `tests/route_h/route_h_verification_registry_v03.csv` | 14734 | `D3475015A8AEB5F594165607A04155A9FBA0C1FB7C0758D40EC64A874548F520` |
| 8 | `project_control/route_h_stage0_v03_revision_execution_log.md` | 7443 | `311348B4D26653C983F9317D2221A3D72DC428A22D995FF1441018167D32FED2` |

冻结算法：SHA-256。所有路径相对于 `E:\Temp-Projects\PRL`。

## 3. 七项修订的冻结映射

| v02 检查项 | v03 冻结处理 | 主证据 |
|---|---|---|
| `V02-REF-TRACTION-001` | 每个 material tether 登记 `g0_pair`；黏附用 `delta_g=g-g0_pair`；参考总装配力/矩成为 bundle seal 门 | geometry、contract、verification |
| `V02-GEOM-ID-001` | 显式种子顶点/面、subdivision ID 顺序、ECM 六 tetra、固定 binary64 运算和 canonical serialization | geometry |
| `V02-TETHER-SPEC-001` | 冻结 quadrature、邻接、ray hit、coverage、record fields、owner、gap limits 和动态 steric event guard | geometry、contract、verification |
| `V02-BOUNDARY-MAP-001` | lateral 方向 subtype、完整外边界 owner/零牵引；错误周期用例从 v03 移除 | geometry、cases |
| `V02-REFINEMENT-001` | v03 只保留 base topology；空间几何族成为 Stage 2 前独立硬门 | geometry、contract、cases、verification |
| `V02-PROTOCOL-METRIC-001` | 冻结 5T0 输入包络、6T0 链协议、combined synchrony、metric 公式及 observables | contract、specialization、cases |
| `V02-SUPPORT-POWER-001` | 只允许固定支撑参考；support/fixture base powers 均为零；移动能力需要新合同 | geometry、contract、ledger |

## 4. 冻结前检查证据

### 文件与交叉引用

- UTF-8 JSON：4/4；
- CSV：2/2；
- 静态交叉检查：23/23；
- case：14 个、ID 唯一、全部 `not_run_unauthorized`；
- ledger：29 个唯一 term ID；
- verification registry：67 个唯一 test ID；
- ledger 到 verification 的引用：全部存在；
- v03 geometry hash 引用：全部为当前值；
- direct-input hashes：全部匹配；
- 旧 v03 geometry hash：无残留。

### 方程与几何 sanity check

- 10/10 通过；
- 20 个种子面全部向外；
- 种子 Euler characteristic 为 2；
- subdivision-2 为 162 顶点/320 面；
- 六 tetra 单位 brick 体积和为 1（浮点结果 `0.9999999999999999`）；
- 自然间隙把 v02 的代表性非零物理 gap 变成参考 `delta_g=0`；
- cohesive C1 边界、主动功率正号、支撑矩阵、载荷包络和 ECM 参考能均通过解析/数值 sanity check。

### 历史不变性

- 复核 v01/v02 共 17 个受控文件；
- 漂移数：0。

上述静态检查不等价于材料化、单元测试、方向导数运行或 Gate A–E 通过。

## 5. v03 主动注册和延期注册

### v03 主动注册

- 一个固定 base topology；
- Gate A–E 的 14 个 required cases；
- 时间加密 `dt=0.02,0.01,0.005`；
- 固定参考 Kelvin–Voigt 支撑；
- material tether 自然间隙和动态 steric；
- 67 个验证项。

### 不在 v03 主动注册

- 周期敏感性；
- coarse/base/fine 空间几何族；
- 移动支撑；
- 两层心肌敏感性；
- Stage 1/Stage 2 执行。

周期与空间离散化不是被判定为“不需要”，而是不得在缺少独立几何规范时伪注册。任何 Stage 2 科学执行之前，必须另行批准并封存空间离散化验证版本。

## 6. 变更与解冻规则

1. 冻结清单中任一文件发生字节级变化，本记录立即失效。
2. 方程、参数、自然间隙、pair 构造、边界 owner、时间协议、case、metric 或阈值变化，必须创建新版本。
3. 未来参考网格实例必须作为独立 bundle 封存，不得写回 v03 规范文件。
4. 未来 periodic 或 coarse/base/fine 几何必须使用独立版本和哈希。
5. Stage 1 必须由用户另行明确授权；冻结 v03 不构成授权。

## 7. 下一动作

允许的自然下一步：对本冻结清单执行只读科学检查。

禁止自动执行：

- 几何材料化；
- solver/AD 实现；
- Gate A–E；
- 参数调整；
- 结果图、机制结论或 stable memory。
