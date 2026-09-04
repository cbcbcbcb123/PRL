---
plan_id: PLAN-PAPER2-M2-IDENTITY-FAILURE-DIAGNOSTIC-V07
status: approved_under_human_standing_authority
approved_at: 2026-09-04
standing_authority: project_control/paper2_autonomous_execution_and_chart_reporting_decision_v01.md
authorization: project_control/paper2_m2a_v06_1_no_go_identity_supervisor_acceptance_and_v07_diagnostic_decision_v01.md
source_identity_result: results/paper2_m2/identity_gate_v06_v02_20260904/
source_t128: results/paper2_m2/identity_2d_v04_t128_v02_20260903/
source_t256: results/paper2_m2/identity_2d_v05_t256_v02_20260904/
result_path: results/paper2_m2/identity_no_go_diagnostic_v07_v01_20260904/
executor_thread_id: 019fc73d-393d-71a3-98cb-d3c0cd0c8eda
execution_authorized: read_only_existing_evidence_discrepancy_decomposition_only
---

# Paper 2 M2A 主动心肌 FEM 身份失败诊断合同 v07

## 1. 诊断问题与结论边界

本阶段只回答：v06.1 已确认的 DCM–FEM `NO-GO-ID`，最符合下列哪类已冻结诊断解释：

- `NORMALIZATION_DOMINANT`；
- `COMPONENT_BASIS_CANDIDATE`；
- `EXTRACTION_IMPLEMENTATION_CANDIDATE`；
- `MODE_SELECTIVE_CONSTITUTIVE_MISMATCH`；
- `MIXED`；
- `INCONCLUSIVE`。

本阶段是已知 identity 失败后的解释性诊断。以下阈值用于区分诊断假说，不是前瞻身份
门，也不得改变 v06.1 的 `NO-GO-ID`。

## 2. 输入、源锁与 fail-closed 条件

只读输入：

1. v06.1 正式结果包及 10/10 hash ledger；
2. T256 成功包中六个正式留出工况、DCM/FEM、S4/T256/D0 的 12 个动态 NPZ；
3. T128 成功包中对应数值变化资料；
4. v06/v06.1 冻结共同投影与 identity 实现；
5. 生成 DCM/FEM 界面牵引和载荷分量的生产源码。

执行前必须复核：v06.1 分类仍为 `NO-GO-ID`，45 条记录仍为
`35 pass / 4 maybe / 6 no_go`，T128/T256/v06.1 ledger 及源文件哈希均一致。任一源锁、
文件集合、解析或有限值检查失败即 `BLOCKED`；不得重算端点、覆盖旧包或修改源文件恢复。

## 3. 冻结数组与加权规则

牵引沿用 v06 的 64 个共同分段守恒投影，数组顺序冻结为 `(space, component, time)`，
分量顺序为源码声明的 `x, y`。动态窗口只取首个完整 T256 周期 `[0:256]`，空间积分沿用
共同分段弧长权，时间使用等权周期采样。

对参考 `d`（DCM）与候选 `f`（FEM），所有归一化范数使用
`max(||d||_w, ||f||_w, 1e-10)` 作分母。内积、最小二乘比例和余弦均使用同一时空权；
近零分量必须报告绝对范数并标为 `NEAR_ZERO_COMPONENT`，不得用不稳定相对差分类。

## 4. 牵引幅值、方向与分量分解

对六个正式留出、两条界面分别输出：

1. 完整二维向量的冻结 normalized-L2 差、两臂范数比 `||f||/||d||` 与加权余弦；
2. `x`、`y` 分量各自的 normalized-L2 差、绝对范数和能量占比；
3. 每条记录的最优实标量
   `alpha = <d,f>_w / <d,d>_w`，以及 `||f-alpha*d||_w/||f||_w`；
4. 全部 v06.1 正式失败牵引记录共享的一个全局实标量及其逐记录残差；
5. 符号一致性、主导分量与矢量方向误差。

单记录最优比例只作形态诊断；不得把它当作模型参数或身份修复。

## 5. 空间与时间模态分解

对每条牵引记录和每个分量分解：

- 空间均值场与零均值空间异质场，并报告二者的能量占比及 DCM–FEM 差；
- 时间 DC、基频复场与二阶及以上谐波残余，报告各自能量占比和差异；
- 基频的幅值比、加权复相关与相位差；
- 差异主要位于 `mean/heterogeneity`、`DC/fundamental/higher-harmonic` 或无法归类。

傅里叶归一化必须在测试中用纯 DC、纯正弦、纯余弦和混合信号验证。所有分量能量之和
须与原信号 Parseval 能量在 `1e-12` 相对误差内闭合。

## 6. 有限坐标基审计

穷举二维的 8 个 signed-permutation 正交矩阵：不交换或交换 `x/y`，并独立取两个分量
符号。每个矩阵只能施加到完整 DCM 牵引矢量，然后以原 v06 时空权与 FEM 比较。

必须报告每条记录的最佳矩阵，同时寻找一个对所有 v06.1 正式失败牵引记录共同使用的
最佳矩阵。不得按工况或界面选择不同矩阵来宣称共同基差异，也不得搜索一般旋转、仿射
变换或连续拟合矩阵。

## 7. 纯模式传递向量

使用冻结工况：

- `ID-A2`：纯主动模式；
- `ID-LN`：纯法向载荷模式；
- `ID-LS`：纯切向载荷模式。

分别构造 DCM/FEM 的传递向量：峰值缩短、缩短基频、法向/切向位移基频、两条界面的
`x/y` 牵引 DC 与基频、周期耗散和储能。每项保持原单位并另给无量纲两臂差；不得把
不同物理量直接拼接后只报告一个总范数。

## 8. 组合载荷叠加审计

从冻结载荷生成源码核对并记录工况分量：

- `ID-C0 = active + in-phase normal`；
- `ID-CQ = active + quarter-phase normal`。

对两臂分别比较 C0/CQ 的输出 DC 与基频复场，和由 A2/LN 对应纯模式按源码相位组合得到
的预测值。至少覆盖缩短、法向/切向位移及两条界面的 `x/y` 牵引。

叠加残差使用同一加权 normalized-L2；同时报告对应 T128→T256 数值变化量。该审计只
识别响应中的叠加缺陷或模式耦合，不假定模型线性，也不把叠加通过等同 identity 通过。

## 9. 生产公式与实现审计

逐项记录 DCM 与 FEM 生产路径中：

1. Cauchy / Piola 或其他应力度量及其转换；
2. 法向方向、牵引符号与界面两侧约定；
3. 长度、面积/厚度、时间和力的单位；
4. 节点量、积分点量、分段积分量及权重；
5. 参考构形或当前构形的测度；
6. 心肌–ECM 与心内膜–ECM 两条界面的提取对称性；
7. 共同 64 分段投影前后的守恒量；
8. 相关文件路径、函数/行号区间与 SHA-256。

源审计只读。只有发现与既有合同或同一物理量定义不一致、且能给出明确代码证据时，才
可支持 `EXTRACTION_IMPLEMENTATION_CANDIDATE`；表示本身不同但已被合同明确记录，不等于
实现缺陷。

## 10. 冻结诊断分类

先逐项计算，再按以下规则分类：

- `NORMALIZATION_DOMINANT`：identity 基不变，单个全局实标量使全部正式失败牵引记录
  残差均 `<=5%`，且逐记录最优比例相对全局比例的差均 `<=5%`；源审计无提取不一致。
- `COMPONENT_BASIS_CANDIDATE`：一个共同的非 identity signed-permutation 矩阵使全部
  正式失败牵引记录残差均 `<=5%`；源审计存在相容的坐标约定证据。
- `EXTRACTION_IMPLEMENTATION_CANDIDATE`：只读源码审计发现明确、非预期的单位、符号、
  测度、权重或界面提取不一致，并且其方向与失败记录一致。不得在本阶段修复或重算。
- `MODE_SELECTIVE_CONSTITUTIVE_MISMATCH`：提取审计干净，且至少一个纯模式或物理分量在
  全局比例与共同有限基审计后仍有 `>15%` 残差；差异能定位到空间或时间模态。
- `MIXED`：上述至少两类各有独立证据，但任何单一类均不能解释全部正式失败记录。
- `INCONCLUSIVE`：证据不足以满足以上任一规则，或关键分量因近零量无法稳定识别。

分类必须给出机器可读的逐条件布尔值和反证。不得以视觉判断代替数值条件。若源锁失败，
正式结果为 `BLOCKED`，不得同时给出上述诊断标签。

## 11. Create-only 输出

目标目录：`results/paper2_m2/identity_no_go_diagnostic_v07_v01_20260904/`。

至少输出：

- `preflight.json`；
- `traction_scale_direction_components.json`；
- `spatiotemporal_mode_decomposition.json`；
- `signed_permutation_basis_audit.json`；
- `pure_mode_transfer_audit.json`；
- `superposition_audit.json`；
- `source_formula_audit.json`；
- `diagnostic_classification.json`；
- `finite_value_audit.json`；
- `run_manifest.json`；
- `hash_ledger.json`；
- `pass_summary.json` 或 `failure_summary.json`。

输出只允许 JSON 和必要的小型文本日志；不得生成新 NPZ。所有 JSON 必须严格有限；ledger
覆盖除自身外的完整文件集合。目标路径已存在则 fail-closed，不得续接或覆盖。

## 12. 实现、测试与独立复核

优先新增：

- `src/paper2_m2/identity_no_go_diagnostic_v07.py`；
- `scripts/run_paper2_m2_identity_no_go_diagnostic_v07.py`；
- `tests/paper2_m2/test_identity_no_go_diagnostic_v07.py`；
- `project_control/paper2_m2a_v07_identity_no_go_diagnostic_execution_record_v01.md`。

测试至少覆盖：加权范数、最优标量、全局标量、近零分量、8 个 signed-permutation、共同
基限制、空间均值/异质分解、傅里叶/Parseval、纯模式字段、复数相位叠加、分类边界、源锁
fail-closed、有限值与 create-only 路径。

Executor 完成后，Supervisor 必须独立复核 ledger、源哈希、分类计数，并从原始 T256
动态数组独立重算至少：全部正式失败牵引记录的全矢量差、分量差、最优标量残差和共同
signed-permutation 结果。

## 13. 资源与停止条件

CPU-only，总时间 `<=600 s`，峰值内存 `<=8 GiB`；不得使用 GPU、网络、Docker、求解器
或运行任何新端点。不得修改或覆盖 v01-v06.1 实现与结果包。

完成后停止在 Supervisor Gate。任何代码修复、模型映射、重新标定、身份重试、M2B、
三维、整心房、流体/CFD/FSI 或实验阶段均未授权，须先向人类报告 v07 证据并形成新决定。
