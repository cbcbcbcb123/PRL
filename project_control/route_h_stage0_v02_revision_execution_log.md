# Route H Stage 0 v02 修订执行记录

## 1. 控制信息

- 记录 ID：`EXEC-PRL-ROUTE-H-STAGE0-V02`
- 日期：2026-07-29（Asia/Shanghai）
- 状态：`completed_and_sealed_by_route_h_stage0_v02_freeze_record`
- 工作目录：`E:\Temp-Projects\PRL`
- 工作流：单执行者、显式范围、静态复核、哈希冻结；未开启角色窗口。

## 2. 用户授权

本轮直接授权原文：

> 批准按检查报告创建并冻结 Stage 0 v02，修复 B1–B4；仍不授权 Stage 1。

据此允许：

1. 在 v01 保持不变的前提下创建独立 v02；
2. 修复只读科学检查报告中的 B1–B4；
3. 执行只读解析、交叉引用、方程 sanity check 和 SHA-256 封存。

明确不允许：

- Stage 1 求解器实现；
- 参考网格实例化；
- Stage 2 数值执行；
- 任何正式响应、参数扫描、论文图或机制结论。

## 3. 输入基线

| 输入 | 冻结 SHA-256 |
|---|---|
| `project_control/route_h_stage0_stage2_governed_plan_v01.md` | `0658FD7FC3451508D08DBC421FD7F48C6654269F24E09387BFE9481819C6E9EB` |
| `project_control/project_handoff_20260728_v01.txt` | `B1A85678439E6DACBB877DFD7D38E7A319C876F99717F2526F8A928156A8E426` |
| `references/2024 - Nature Computational Science - Iber - SimuCell3D三维组织力学模拟.md` | `991DB9A8FCB156EBA0F8731D9342BBFE741EED228C3867BD7A0B16AE62E23BDA` |
| `project_control/route_h_stage0_freeze_record_v01.md` | `167B4208DBAFF93BF0A1CD20CD58DD820ACB6695E5377F4BF93E4C1EE22DA444` |
| `project_control/route_h_stage0_readonly_scientific_review_v01.md` | `1292F1AC9CA3C2006749BE5DCCC4D51B9F9ACB757B12F04492AC14B725A6B2A4` |

v01 合同、特化、用例、坐标约定、功率账本、验证注册表和主动科学决定共七个冻结件在 v02 写入后重新计算哈希，全部与 v01 冻结记录一致。

## 4. B1–B4 修订

### B1 — 参考态、材料身份与封存

已完成：

- 新增独立参考几何规范；
- 冻结平坦贴片尺寸、细胞模板、表面网格生成算法和 ECM 网格算法；
- `V0`、分面 `A0`、铰链 `theta0` 均改为最终参考网格的精确值；
- `Gamma_minus/Gamma_plus` 按参考参数方向选择并持久化；
- 主动质心和力分配统一采用固定参考三角面积—节点重心权重；
- `Lf0` 定义为参考锚定质心距离；
- ECM 登记 `F0=I`、`J0=1`、`Z0=dev(C_bar0)=0`；
- 要求任何求解器或响应之前封存完整参考 bundle；
- `gamma_s=0`、精确参考目标、零界面间隙、零黏附斜率、零切向滑移和固定支撑参考共同定义无预应力参考态。

### B2 — 动态排斥与冻结材料黏附

已完成：

- 动态几何搜索只产生排斥势；
- 材料黏附配对只从参考几何建立，整条轨迹冻结并哈希；
- 后来接触的表面不会自动获得黏附；
- 定义确定性主面、随动切向基和刚体客观材料滑移；
- 明确要求对间隙、法向、材料/最近点、权重、投影和切向基求完整离散梯度；
- 注册方向导数、作用反作用、刚体客观性、配对身份和穿透测试。

### B3 — Gate C 支撑冲突

已完成：

- Gate C 的唯一顺应支撑改为 `myocardium.opposite_outer`；
- Gate C 的 ECM 心腔侧边界明确为零牵引；
- ECM 不再同时充当细胞界面和外部环境支撑；
- Gate D 所需 ECM 支撑独立命名为测试夹具 `P_FIXTURE_D`，且禁止继承到完整贴片。

### B4 — 完整几何、法向和边界分配

已完成：

- 主贴片为 `3.0 × 1.8` 的平坦参考域；
- 明确 6 个心内膜细胞、12×8×2 ECM 结构区间和 9 个心肌细胞；
- 明确层间坐标、零参考间隙和一层主心肌结构；
- 压力和 WSS 采用当前心内膜顶端外法向；
- 血流端口、完整贴片外侧/侧向支撑、Gate C、Gate D 和周期敏感性均有唯一所有者；
- 支撑能、耗散、K/C 矩阵和功率端口均已登记。

## 5. 新建 v02 冻结候选件

1. `data/route_h/route_h_reference_geometry_spec_v02.json`
2. `src/route_h/route_h_contract_v02.json`
3. `src/route_h/route_h_model_specialization_v02.json`
4. `data/route_h/route_h_cases_v02.json`
5. `docs/route_h/route_h_coordinate_and_sign_convention_v02.md`
6. `docs/route_h/route_h_port_and_power_ledger_v02.csv`
7. `tests/route_h/route_h_verification_registry_v02.csv`
8. 本执行记录

最终 SHA-256 由 `project_control/route_h_stage0_v02_freeze_record.md` 单独封存。

## 6. 冻结前验证

### 6.1 文件和模式

- UTF-8 JSON：4/4 解析成功；
- CSV：2/2 表头稳定且每行列数一致；
- v02 交叉引用与授权锁：通过；
- 15 个 case ID 唯一且 Gate A–E 引用完整；
- 全部 case 初始状态为 `not_run_unauthorized`；
- 功率账本 29 个 term ID 唯一；
- 验证注册表 53 个 test ID 唯一。

### 6.2 合同静态检查

23/23 通过，包括：

- 合同—特化—用例—几何 ID 一致；
- Stage 1 与几何实例化锁定；
- 参考零间隙、无预应力条件和 `Z0`；
- 动态排斥/冻结黏附分离及完整梯度条款；
- Gate C/Gate D 端口所有权；
- B1–B4 验证条目；
- 输入哈希；
- v01 七个冻结件不变性。

### 6.3 方程 sanity check

7/7 通过：

- subdivision-2 细胞表面计数为 162 顶点、320 三角面；
- 制造的首选长度缩短给出正的控制器输入功率；
- 黏附势在 `g=0` 和 `g=g_c` 两端数值零斜率；
- 六个支撑 K/C 矩阵对称且对角非负；
- 心内膜和心肌规则网格精确覆盖贴片面内范围；
- 心内膜—ECM 与 ECM—心肌参考界面均在零间隙闭合。

这些检查仅验证 Stage 0 文本、模式和解析公式；不等于 Stage 1 单元测试或任何数值模型通过。

## 7. 偏差与边界

- 相对用户授权：无范围偏差。
- 相对 v01：v02 是替代未来工作的独立版本，v01 未修改。
- 冻结前内部一致性收紧：将锚定力分配从“当前面积权重”统一为与锚定质心相同的“固定参考面积—节点重心权重”，避免能量导数与中心力声明歧义。
- 网格实例、求解器、响应和结果：均不存在。
- 独立只读科学检查：尚未执行。
- Stage 1：仍未授权。

## 8. 终止条件

本轮终止于 Stage 0 v02 哈希冻结。下一步只能是独立只读检查，或由用户另行明确授权的工作；不得自动进入 Stage 1。
