# Route H Stage 0 v03 修订执行记录

## 1. 控制信息

- 记录 ID：`EXEC-PRL-ROUTE-H-STAGE0-V03`
- 日期：2026-07-30（Asia/Shanghai）
- 状态：`completed_and_sealed_by_route_h_stage0_v03_freeze_record`
- 工作目录：`E:\Temp-Projects\PRL`
- 工作流：单执行者受控修订 + 静态检查；未创建角色窗口。

## 2. 授权解释

用户在 v02 只读检查报告交付后指示：

> 继续下一步

按连续上下文，本轮将其解释为：

- 依据 `route_h_stage0_v02_readonly_scientific_review_v01.md` 创建并冻结 Stage 0 v03；
- 只修复报告列出的 7 项；
- v01/v02 保持只读；
- 不生成参考网格实例；
- 不实现或授权 Stage 1；
- 不运行 Gate A–E 或 Stage 2。

## 3. 直接输入

| 输入 | SHA-256 |
|---|---|
| `project_control/route_h_stage0_stage2_governed_plan_v01.md` | `0658FD7FC3451508D08DBC421FD7F48C6654269F24E09387BFE9481819C6E9EB` |
| `project_control/project_handoff_20260728_v01.txt` | `B1A85678439E6DACBB877DFD7D38E7A319C876F99717F2526F8A928156A8E426` |
| `references/2024 - Nature Computational Science - Iber - SimuCell3D三维组织力学模拟.md` | `991DB9A8FCB156EBA0F8731D9342BBFE741EED228C3867BD7A0B16AE62E23BDA` |
| `project_control/route_h_stage0_v02_freeze_record.md` | `6067237F996EC42F2BBC1CB7B90C4816CBF94B4819F248B37043A824D4845359` |
| `project_control/route_h_stage0_v02_readonly_scientific_review_v01.md` | `66C7CAEFAC75ED6750AC73FACA478811AAA043F1A74C3639F0D03D576B754869` |

## 4. 七项修订

### 4.1 V02-REF-TRACTION-001

- 不再以全界面 `nominal gap=0` 代替真实局部间隙；
- 每个材料 tether 保存 `g0_pair`；
- 黏附使用 `delta_g=g-g0_pair`；
- 动态排斥仍使用物理 gap `g`；
- 参考 bundle seal 增加总装配参考力和力矩门。

### 4.2 V02-GEOM-ID-001

- 列出 12 个种子顶点及 20 个有向种子面；
- 冻结 face traversal、edge traversal、midpoint ID 和 child-face 输出顺序；
- 冻结 ECM vertex/brick ID 和六四面体局部数组；
- 冻结 little-endian 数组序列化与 SHA-256；
- `p=8` 映射的八次方和八次根改为固定乘法顺序及三次 correctly-rounded `sqrt`，避免跨语言 `pow` 末位漂移。

### 4.3 V02-TETHER-SPEC-001

- 每个 eligible master face 使用一个 barycenter quadrature；
- cell–ECM 和同层 +x/+y 邻居分别采用确定性 ray mapping；
- 冻结 nearest-hit、tie-break、固定 slave barycentric point、pair record 和排序；
- 要求精确 100% master-face 覆盖；
- 动态 steric 单独定义为对称 vertex–triangle operator，并登记 triangle-intersection guard。

### 4.4 V02-BOUNDARY-MAP-001

- `lateral` 面增加 x-/x+/y-/y+ 永久 subtype；
- 主贴片周边心肌支撑按 grid index 和方向 subtype 唯一分配；
- 周边心内膜和 ECM lateral 边界显式为零牵引；
- v02 的错误周期配对不再注册，周期影像与 ECM 周期约束推迟到独立版本。

### 4.5 V02-REFINEMENT-001

- v03 只冻结一个 base topology；
- 删除与固定 identity/hash 冲突的空间 edge-scale 加密；
- 新增 Stage 2 阻断门：任何科学执行前必须另行批准并封存 coarse/base/fine 几何族。

### 4.6 V02-PROTOCOL-METRIC-001

- 冻结 5T0 的零延拓—余弦 ramp—hold—余弦 release 包络；
- 三细胞链延迟为 0、0.5、1.0，总时长 6T0；
- combined case 的主动、压力和 WSS 同步；
- 冻结 directional derivative、pair force/moment、equilibrium、leakage、integrated power 和 time-refinement 的分子、分母、范数、floor 与时间求积；
- 冻结 time-refinement observable 清单。

### 4.7 V02-SUPPORT-POWER-001

- v03 仅允许固定 Kelvin–Voigt 支撑参考；
- `P_support_base=0`；
- `P_fixture_D_base=0`；
- 一般 moving-support 能力从合同中删除；若以后需要，必须创建新合同并登记完整阻尼基座功。

## 5. v03 产物

1. `data/route_h/route_h_reference_geometry_spec_v03.json`
2. `src/route_h/route_h_contract_v03.json`
3. `src/route_h/route_h_model_specialization_v03.json`
4. `data/route_h/route_h_cases_v03.json`
5. `docs/route_h/route_h_coordinate_and_sign_convention_v03.md`
6. `docs/route_h/route_h_port_and_power_ledger_v03.csv`
7. `tests/route_h/route_h_verification_registry_v03.csv`
8. 本执行记录

最终哈希由 `project_control/route_h_stage0_v03_freeze_record.md` 封存。

## 6. 用例与延期项

- Gate A–E：14 个 required cases；
- 所有 case 初始状态：`not_run_unauthorized`；
- E5 周期敏感性：不在 v03 注册；
- 空间加密：不在 v03 注册；
- 时间加密：`dt=0.02,0.01,0.005`；
- 周期几何和 coarse/base/fine 几何族：必须在 Stage 2 前另行批准、定义和封存。

删除未闭合敏感性不代表其科学必要性消失；它们被提升为后续独立版本门，不能由 base patch 结果替代。

## 7. 冻结前检查

### 7.1 模式与交叉引用

23/23 通过：

- UTF-8 JSON 4/4；
- CSV 2/2；
- geometry hash、artifact ID 和 direct-input hash；
- 14 个唯一且未授权的 cases；
- 周期与空间加密未激活；
- 确定性 arithmetic/serialization；
- 方向面及边界 owner；
- 自然间隙和 tether 离散闭合；
- 时间协议与 metric 公式；
- 固定支撑功率；
- 7 项检查发现映射；
- 29 个唯一 ledger term；
- 67 个唯一 verification test；
- ledger→verification 引用完整；
- 无旧 v03 geometry hash 残留。

### 7.2 方程与几何 sanity check

10/10 通过：

- 20 个种子面全部向外，最小 orientation dot 为 `0.760845213036123`；
- 种子网格 30 条唯一边，Euler characteristic 为 2；
- subdivision-2 计数为 162 顶点、320 面；
- 六个局部 tetra determinant 为 `1,-1,-1,1,1,-1`，方向修正后均为正；
- 六 tetra 的单位 brick 体积和为 `0.9999999999999999`；
- v02 代表性心内膜/心肌物理间隙分别为 `0.009959514815439453` 和 `0.023238867902692063`，在 v03 中各自保存为 `g0_pair` 后参考 `delta_g=0`；
- cohesive potential 在 `delta_g=0` 和 `delta_g=g_c` 满足 C1 边界；
- 制造的 preferred-length shortening 给出正的 `P_active`；
- 六个 K/C 支撑矩阵对称且非负对角；
- load envelope 在四个内部时间结点连续，ECM 参考储能为零。

### 7.3 历史不变性

复核 v01/v02 合同、特化、用例、文档、账本、注册表、执行/冻结/检查记录等 17 个受控文件：

- 漂移：0；
- v01/v02 未修改。

## 8. 无效检查尝试

两次初步 PowerShell 几何 sanity script 因数组表达式被包装为 `Object[]`，产生除法/减法类型错误和假失败。处理如下：

- 未接受或引用其几何结论；
- 未写入任何文件；
- 改用纯内存 JavaScript 数值复核；
- JavaScript 复核得到 10/10 通过的有效结果。

## 9. 偏差与边界

- 范围偏差：无。
- 科学路线收缩：按 v02 检查建议，将未闭合 periodic sensitivity 和 spatial refinement 从 v03 active registry 移出，并保留 Stage 2 前硬门。
- 额外一致性收紧：固定 `p=8` 的运算顺序，避免跨实现哈希漂移。
- 参考网格实例：未生成。
- 求解器、AD、响应和结果：未生成。
- 独立只读科学检查：尚未执行。
- Stage 1/Stage 2：未授权。

## 10. 终止条件

本轮终止于 v03 静态验证和 SHA-256 冻结。下一自然动作只能是对冻结 v03 做只读科学检查；不得自动进入 Stage 1。
