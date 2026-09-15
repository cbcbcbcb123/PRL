---
constraint_id: CONSTRAINT-PRL-EXTERNAL-SCIENTIFIC-REVIEW-V01
status: frozen_active
accepted_at: 2026-08-02
scope: hybrid X1-H and later scientific/software claims
preserves: FREEZE-PRL-ROUTE-H-STAGE2-GATE-A-FAILURE-V01
---

# 外部科学评审后续硬约束 v01

## 总体证据等级

当前路线可继续作为“无量纲细胞—ECM 力路机制模型”发展。现有结果不证明完整耦合系统、心脏发育机制、EFE 机械记忆、稳定收缩轨迹或生理预测。软件一致性、数值有效性和生物学验证必须作为三条独立证据线管理。

Route H Gate A v01 的 `failed_invalid_numerics` 证据保持不变。它只表示冻结求解器没有满足自身 residual gate，不是否定理论；任何诊断或修订必须新建版本，不得覆盖 v01 失败包。

## P1 执行顺序

1. **X1-H**：在 PRL owned driver 中接入真实被动力、真实接触力和派生几何缓存刷新，只冻结一个完整、可审计、可传播已捕获失败的单步；
2. **X1-I**：在任何连续轨迹前处理阻尼的空间一致性。优先采用双面积/控制面积加权阻尼；若保留统一节点阻尼，必须以制造解和 coarse/base/fine 证明空间一致性；
3. **X1-J**：为 split/swap/merge 建立 `ΔPsi_remesh` 能量跳变/算法缺陷账本，并验证循环重网格不累积虚假能量、功或纤维漂移；
4. **X1-K**：建立短轨迹门禁，包括时间步 refinement、空间 refinement、体积误差、质心漂移、最小 Jacobian/三角质量、接触穿透、离散能量不等式和失败状态持久化；
5. X1-K 通过前，不接入 ECM/血流长耦合，不做参数标定或论文级机制 claim。

`W_F=D_zeta` 是由 `dx=dt·F/zeta` 得到的代数恒等式，不得作为稳定性、能量收敛或轨迹有效性的证据。

## 科学语义边界

- pressure/WSS 当前是规定载荷，不是双向 FSI；`chi_E` 是全局命令滤波量，不是局部内皮 WSS/应变/相位传感器；
- cardiac-jelly ECM 当前是单相黏弹固体；若预测厚度、压力传递或迟滞，必须比较孔弹/双相或 HA 水化—自然体积机制；
- `A`、`H_ECM`、turnover、`j_myo` 和 `chi_E` 反馈当前冻结，系统尚不能产生 EFE 双稳态或机械记忆；在零流线、Jacobian、分岔、参数可识别性和盲预测完成前，只能使用“候选双稳态/状态跃迁”；
- EFE 细胞来源采用时间依赖双/多来源框架，不预设 EndMT 或心外膜单一来源，当前力学模型不能裁决谱系来源；
- 启用非零 cardiac-jelly 来源时，“心肌为主要来源”只能作为阶段/区域/物种依赖假设，并注册 competing source variants。

## 工程治理

保持 TDD、单步可审计、版本化冻结、claim guard 和阶段性 Git 远端同步。后续版本必须显式引用本约束文件；若改变 P1 顺序或科学语义，必须新建约束版本并记录用户授权。
