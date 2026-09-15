---
inspection_id: INSPECTION-PRL-FIG2-SPATIAL-TOLERANCE-V01
status: revision_required
inspector: gpt-5.6-sol_xhigh_readonly
inspected_at: 2026-08-30
source_commit: a0c874e7a97350429c5b8dcec9f21daa91b6887e
source_branch: origin/codex/simucell3d-hybrid-feasibility
related_plan: project_control/prl_figure2_spatial_tolerance_validation_contract_v01.md
thread_id: 01a052f9-a82c-74b0-94d9-66bc621bacff
---

# PRL Figure 2 空间与容差合同 v01 独立审阅

## 裁决

`REVISION_REQUIRED`。v01 的方向、证据边界和 fail-closed 框架合理，但尚不足以
可靠分离空间、边界和代数误差，不得批准或执行。

## 必须修订项

1. **边界比较必须嵌套。** 现有 E2/F150 与 E2/F200 在 x 方向存在半单元网格
   相位偏移；共同域插值不能消除该混杂。F200 必须原样嵌入 F150 中央网格，或
   另设独立网格相位控制。
2. **容差证据必须覆盖空间比较端点。** 单独 S4→S5 只能证明终局工况的容差
   敏感性，不能证明 S1–S3 的 C0 误差可忽略。每个控制空间比较的两个端点都需
   C1 复算，或使用经验证的逐工况 QoI 代数误差估计器。
3. **C1 必须贯穿全链路。** 当前 worker、父审计、L-BFGS、Newton 和跳过阈值
   存在硬编码。ST0 必须建立唯一求解配置、序列化 provenance 和严格残差门。
   零压力/WSS 下 follower tolerance 是休眠参数，不得作为已验证证据。
4. **逐场冻结共同求积。** 必须分别定义 P1 位移、DG0 ECM 场、DCM 表面场和
   离散界面牵引的重构、权重、分母、近零尺度、相位、聚合与映射硬门。
5. **热点不能只看质心。** 还需热点集合重叠或传输距离，防止热点分裂、交换和
   对称抵消被质心掩盖。
6. **功率账本必须离散一致。** 不得保留“其他物理耗散”开放桶；主动广义功、
   全部可恢复能、界面功和唯一耗散项须闭合。现有 SLS 割线率耗散只是非负代理，
   不能直接作为指数更新的严格能量恒等式。
7. **合矩必须按 `F×L` 归一化。** 不能继续只用力尺度归一化合矩残差。
8. **细网格需独立时间触发门。** D0/E0/F150 的 T64→T128 通过不能自动继承到
   D1/E2/F200。若不做终局 T128，只能报告固定 T64 的空间敏感性。

## 已关闭的疑点

只读构造核验确认当前 D0 与 D1 的心肌包围盒完全相同，因此 S2→S3 没有实际
发生 ECM 物理域变化。D0/D1 的双界面 tether 数由 `52/60` 增为 `182/242`，
属于预期的 DCM—界面联合离散变化。后续仍须显式冻结绝对 ECM bounds、界面
选择规则、tether 计数和总权重，防止实现漂移。

## 下一步

ST0 可以继续作为唯一候选下一阶段，但必须在 v02 合同经人类批准后才能执行。
ST0 只允许嵌套网格证明、C0/C1 全链路参数化、共同求积映射测试、离散功率制造
解、阈值表和成本预检；不得运行 S1–S5 完整周期。

本审阅全程只读，没有修改文件、运行科学计算、启动 GPU、提交或推送。
