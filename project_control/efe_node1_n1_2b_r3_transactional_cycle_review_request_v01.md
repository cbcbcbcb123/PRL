---
decision_request_id: DECISION-REQUEST-EFE-NODE1-N1-2B-R3-TRANSACTIONAL-CYCLE-V01
status: pending_human_final_review
requested_at: 2026-08-20
related_plan: project_control/efe_node1_n1_2b_r3_transactional_cycle_plan_v01.md
related_execution: project_control/efe_node1_n1_2b_r3_transactional_cycle_execution_v01.md
formal_n1_2_cycle_stability_evidence: not_accepted
---

# EFE Node 1 N1-2b-r3 事务性周期重算终审请求 v01

## Recommended decision

建议人类终审：

1. 接受 r3 为有效、可复算的事务周期执行；
2. 接受事务 driver 已连续完成 32 个新鲜 worker 的父复核与提交；
3. 接受 cycle 3–4 的全部单步状态门通过；
4. 接受“宏观变形和储能已近周期，但 ECM 黏弹内变量仍处于慢瞬态”；
5. 不接受 N1-2 已达到 T16 周期稳态；
6. 批准下一步 `N1-2b-r4`：使用 cycle 4 实际三维 ECM 变形历史重新构造
   解析周期 SLS 内变量，phase 0 机械重平衡后再运行两个事务验证周期。

## Why not simply run many more transient cycles

当前末态 `Z` 周期差每周期约乘 `0.68`。按该经验收缩率，从 `2.28e-2` 降到
`1e-3` 约需再运行 8 个周期，即约 128 个新鲜 worker。冻结几何 SLS 对给定
周期变形具有闭式周期初值；cycle 4 的宏观几何波形已经近周期，因此以其实际
三维 ECM 历史重新计算周期 `Z`，属于改变初始猜测而非改变模型方程，可显著
减少无信息的瞬态等待。

## Proposed r4 frozen boundary

- 源几何只使用正式 r3 cycle 4 的 17 相位 ECM 顶点历史；
- 按原 SLS 精确更新构造冻结几何周期 `Z`，周期残差要求 `<=1e-12`；
- 使用 cycle 4 零激活几何、解析周期 `Z` 和原接触状态进行 phase 0 机械
  重平衡，KKT、体积、`J`、gap、面面积和 `Z` 结构门保持不变；
- 从该接受重平衡态运行两个完整 D0/E0/F150、T16 事务周期；
- 每步仍为新鲜 worker、父 oracle、SLS/耗散一致性和 create-only 提交；
- 第二验证周期相对第一验证周期的四条波形和周期末 `Z` 全部 `<=1e-3`，
  才作为 N1-2 T16 周期稳态候选；
- 任一步或任一周期门失败即保留负结果并停止，不继续追加周期；
- r4 后再次提交人类终审，不自动进入 T32 或 D1/E1。

## Why this remains scientifically honest

解析 re-periodization 只为求极限周期选择更接近固定点的初始历史，不修改
心肌主动加载、ECM 本构、接触、耦合算法或接受门。最终证据仍来自两个连续、
完全耦合的动态周期；冻结几何解析态本身不会被当作稳态证据。

## Not requested

- 不请求采用 Aitken/Anderson 或放宽周期门；
- 不请求超过两个验证周期；
- 不请求 T32/T64、D1/E1、F200、参数扫描、N1-3 或 Node 2；
- 不请求实验拟合、论文终稿、Git 或发布。

## Exact human gate

请求人类终审明确回复是否接受：

> 接受 r3 事务周期结果及“cycle 4 尚未稳态”的结论；批准 r4 使用 cycle 4
> 实际 ECM 几何历史解析 re-periodization，并执行两个事务验证周期。

在获得明确批准前，不执行 re-periodization 或新增完整周期。

