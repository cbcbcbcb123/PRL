---
check_id: CHECK-PRL-ROUTE-H-STAGE2-GATE-A-PHYSICAL-ACCEPTANCE-V03-V01
contract_id: CONTRACT-PRL-ROUTE-H-STAGE2-GATE-A-PHYSICAL-ACCEPTANCE-V03
execution_id: EXEC-PRL-ROUTE-H-STAGE2-GATE-A-PHYSICAL-ACCEPTANCE-V03
checker: Codex current task
checked_at: 2026-08-05T01:21:07+08:00
status: ready_for_human_review_failed_gate
independent_inspection: false
---

# Route H Stage 2 Gate A M1 v03 交付前只读自检

## 范围与独立性

本记录是同一执行任务的只读自检，不冒充独立 Inspector。用户仍是阶段终审者。

## 合同完成度

- 数值接受机制按预注册规则实现，没有修改力学、参数、时间步或门槛；
- 原 step79 已通过所有复算门槛；
- 正式套件在首个新失败 step86 fail-fast，未为追求通过而继续 coarse/fine 或调参；
- accepted trajectory 与 rejected candidate 在内存对象、文件、CSV/JSON 和图中分离；
- 因正式套件没有四条完整轨迹，M1 v03 的 Gate A acceptance criteria 明确未满足。

## 证据核验

- 旧冻结：Gate A v01 `29/29` SHA-256 与 bytes 匹配；
- 代码：stage2 tests `7/7` 通过，相关 Ruff 通过；
- 正式输出：A0 完整，A1 `dt=0.02` 仅接受到 `t=1.70`；step86 failure 单独保存；
- 数值：所有 accepted residual `<=1e-8`，所有 accepted gauge `<=1e-12`，accepted
  geometry 有限、正体积、0 翻面、0 退化；
- 新失败：最小 trial residual `1.310584667e-8`，0/162 trial 达标；正式与重放
  candidate 最大坐标差为 0；
- 图形：两个版本包 Notebook、PNG/SVG、methods、自动检查和视觉 QA 通过；残差图
  `10 × 5 in` 主轴框及 CB style manifest 通过；
- 报告层字段命名更正已登记，未改 solver 或结果数组。

## 可支持与不可支持的结论

可支持：M1 v03 修复了原 step79 的 callback/physical-gate 失配，并把有效轨迹推进
`0.14 s` 至 `t=1.70`；step86 是所有 line-search trial 均未到 residual gate 的数值限制，
候选几何仍有效。

不可支持：Gate A 通过、5 s 自由收缩稳定、三个时间步收敛、生理参数有效、真实前/后
负荷、Ca²⁺—横桥、ECM/组织耦合或 EFE 机制。

## 人工终审请求

请用户查看状态图和 residual 图，并决定是否：

1. 接受 M1 v03 为“原问题修复但 Gate 仍失败”的阶段结果；
2. 批准起草 M1 v04 数值方法合同，保持物理模型和 `1e-8` 门槛不变，改进求解
   projected force-balance 的尺度/conditioning；
3. 或要求先补充对现有图和 step86 证据的解释。
