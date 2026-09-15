---
check_id: CHECK-PRL-ROUTE-H-STAGE2-GATE-A-OBSERVABILITY-V02-V01
contract_id: CONTRACT-PRL-ROUTE-H-STAGE2-GATE-A-OBSERVABILITY-V02
execution_id: EXEC-PRL-ROUTE-H-STAGE2-GATE-A-OBSERVABILITY-V02
checker: Codex current task
checked_at: 2026-08-04T14:51:41+08:00
status: ready_for_human_review
independent_inspection: false
---

# Route H Stage 2 Gate A M1 v02 交付前只读自检

## Scope and independence

本记录是同一执行任务完成的只读自检，不冒充独立 Inspector 意见。用户仍是阶段终审者。

## Contract completion

- v02 只新增可观测入口、结果和图，没有修改冻结求解器、力学定律、阈值或 v01 证据；
- accepted trajectory 与 rejected candidate 在数据结构、CSV/JSON 语义和图中均分离；
- 失败时间、残差、gauge、优化器状态、优化轨迹和网格有效性均已保存；
- 两张图均只使用版本包中物理复制的真实模型输出，不含虚构或插值数据。

## Verification

- Gate A v01 freeze：`29/29` 哈希匹配；
- pytest：`6/6` 通过；
- Ruff：通过；
- 两个 Figure 包自动校验和目视验收：通过；
- 残差图 CB 统一风格 manifest：通过；
- 图中文字、图例、状态颜色和门槛线无裁切或遮挡；
- red rejected candidate 的图注明确说明它不属于有效轨迹。

## Evidence and claim boundary

可支持的结论：

1. 失败前细胞沿主动轴缩短并横向增粗，体积误差保持约 `1e-4`；
2. 第 79 步候选没有几何崩坏；
3. 该步存在满足 physical residual gate 的 line-search trial，但 callback accepted iterates
   未满足门槛，随后 L-BFGS-B 异常退出；
4. 下一修订应针对数值停止/接受机制，而不是改变细胞力学加载定律。

不可支持的结论：Gate A 通过、完整自由收缩轨迹稳定、时间收敛、生理有效、真实力值、
Ca²⁺/横桥机制或 ECM/组织耦合成立。

## Remaining risks

- 当前只诊断 `dt=0.02` 的首个失败；尚未运行新的 `dt=0.01/0.005` 有效轨迹；
- 只看到 trial residual 达标，不代表可以不经新合同直接把 trial 当 accepted state；
- 下一方法必须同时验证增量势下降、物理残差、gauge、重复性和三个时间步，不能只消除
  `ABNORMAL` 消息。

## Human decision requested

请人工终审选择：接受 M1 v02 并批准起草/执行 M1 v03 数值接受机制修订，或要求修改本诊断图/解释。
