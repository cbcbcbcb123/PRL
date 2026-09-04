---
decision_id: DEC-PAPER2-M2A-V07-ACCEPT-MODEL-ARCHITECTURE-HUMAN-GATE-V01
status: accepted_awaiting_human_model_architecture_decision
decider: supervisor_under_human_standing_authority
decided_at: 2026-09-04
standing_authority: project_control/paper2_autonomous_execution_and_chart_reporting_decision_v01.md
accepted_execution: project_control/paper2_m2a_v07_identity_no_go_diagnostic_execution_record_v01.md
accepted_result: results/paper2_m2/identity_no_go_diagnostic_v07_v01_20260904/
accepted_diagnostic_label: MODE_SELECTIVE_CONSTITUTIVE_MISMATCH
frozen_identity_decision: NO-GO-ID
execution_authorized: none_pending_human_model_architecture_decision
recommended_route: role_separated_hybrid_without_forced_myocardial_identity
---

# Paper 2 M2A v07 Supervisor 验收与模型架构 Human Gate v01

## 1. Supervisor 验收决定

Supervisor 接受 v07 正式诊断标签 `MODE_SELECTIVE_CONSTITUTIVE_MISMATCH`，并冻结 v06.1
的 `NO-GO-ID`。当前证据否定了“统一幅值归一化”“共同有限坐标换基”和“非预期牵引
提取差异”三种简单解释；最支持的解释是：DCM 与主动心肌 FEM 在主动驱动及特定空间/
时间分量下具有不同的表示级本构响应。

本验收不判断哪种表示更真实，也不授权修改模型。下一步将改变模型角色、科学命题或
校准策略，属于人类持续授权中明确保留的重大决策，因此停在 Human Gate。

## 2. 独立复核证据

| 检查项 | Supervisor 独立结果 | 结论 |
|---|---:|---|
| v07 定向测试 | 22/22 | PASS |
| v04–v06.1 相关轻量回归 | 74/74 | PASS |
| 静态检查 | 3 个新增文件 | PASS |
| 正式结果包 | 12/12 JSON 有限；0 NPZ | PASS |
| hash ledger | 11/11 文件集合、字节数和 SHA-256 一致 | PASS |
| 源锁 | 15 个冻结源码当前哈希与 manifest 一致；前后快照一致 | PASS |
| 原始数组独立复算 | 4/4 正式失败牵引的全矢量、分量、比例与基审计逐值一致 | PASS |
| 傅里叶 / 空间能量闭合 | 最大 `4.1077e-16 / 4.1317e-16 < 1e-12` | PASS |
| 资源 | `13.7765 s`；`0.05043 GiB`；单 CPU | PASS |
| 禁止项 | 无 solver、端点重跑、Docker、GPU、网络或模型修改 | PASS |

独立原始数组复算确认：

- `ID-A2` 两条界面即使使用逐记录最优比例，残差仍为
  `0.7905789767 / 0.7890933080`；
- 失败记录的逐项最优比例跨越 `0.2847384113–1.1208747290`，不存在共同标度；
- 8 个 signed-permutation 的共同最优仍是 identity，拼接残差
  `0.2021687541`，最大单记录残差 `0.8040305799`；
- DCM/FEM 使用同一 penalty 界面位移跳跃牵引、同一分量顺序、参考测度与 64 段守恒
  投影，源码审计没有发现能解释正式失败的非预期提取分支。

执行记录页眉中最初写错的 `plan_id` 与 `authorization` 已更正为实际合同标识符；该更正
只修复治理元数据，不改变代码、结果或分类。

## 3. 科学含义

v07 显示，当前问题不是“把 FEM 输出乘一个系数即可替代 DCM”。纯主动 `ID-A2` 的差异
同时改变牵引方向、空间异质性、DC 与基频传递；而 C0/CQ 的 A2+LN 主要模态叠加残差仅
`0.2306%`。因此更值得检验的候选物理命题是：

> 主动驱动与心肌粗粒化可能不对易；这种不对易以载荷模式和界面传递分量为选择性，
> 而不是一个普适的幅值校正。

该命题目前只是 v07 支持的候选机制，尚未形成无量纲规律、跨几何稳健性或实验验证，
不能据此声称达到 Nature Physics 证据标准。

## 4. Human Gate 路线选项

### A. 角色分离的混合模型（Supervisor 推荐）

正式固定：心内膜细胞使用 DCM；主动心肌使用 FEM；ECM 使用黏弹 FEM。心肌 DCM 支路
降级为机制对照，不再要求与心肌 FEM 全观测量 identity。停止 M2B identity 扩展，下一
阶段改为研究“主动驱动 × 粗粒化”的模式选择性差异及其适用域。

优点：与项目已确定的器官级架构一致；不为通过 identity 而过拟合；可把 NO-GO 转化为
真正的物理问题。风险：必须重新定义论文的核心命题和图件逻辑，并建立新的前瞻机制门。

### B. 机制匹配的 DCM→FEM 映射修订

引入可表示空间异质性与方向耦合的主动 FEM 映射，再以独立校准/留出集重新检验 identity。
禁止只拟合一个比例或直接用六个留出反推参数。

优点：若成功，可保留跨表示转换路线。风险：自由度、过拟合和识别性问题显著增加；在
缺少实验约束时可能把表示差异“校准掉”，削弱而不是增强物理叙事。

### C. 保留严格 identity 要求并暂停扩展

在 DCM 与 FEM 达到冻结 identity 门之前，不进入器官级混合模型。

优点：最保守。风险：与“不同层使用不同表示”的既定架构不完全相容，并可能把大量工作
投入到项目并不需要的心肌 DCM 可替代性上。

## 5. 推荐路线 A 的下一阶段轮廓（未授权）

若人类选择 A，下一版合同应先做理论与既有证据阶段，不立即上三维或整心房：

1. 冻结生产角色：`endocardium=DCM`、`myocardium=active FEM`、`ECM=viscoelastic FEM`；
2. 把心肌 DCM 明确标为 comparator，不参与生产模型校准；
3. 从主动幅值、空间异质尺度、界面刚度和 ECM 松弛时间构造最小无量纲组；
4. 预注册“粗粒化–主动驱动不对易”观测量：两侧界面牵引模态、缩短、热点位置和功率；
5. 先在理想化二维做最小可证伪状态图，再决定是否进入三维和整心房；
6. 流体仍作为后续分层加入，不用于修复当前固体 identity；
7. 实验优先约束主动牵引的幅值/空间异质性、ECM 松弛和心内膜边界载荷，不用于事后
   调整 identity 阈值。

## 6. 当前停止边界

当前没有后续执行授权。不得修改模型/本构/映射/生产提取、重新标定、重跑 identity、
进入 M2B、三维、整心房、流体/CFD/FSI、实验拟合或参数扫描。人类选择路线后，须先建立
新版本科学合同和校准/留出边界，再由 Executor 执行。
