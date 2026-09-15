---
decision_id: DEC-PRL-ROUTE-H-PHASE-DELIVERY-GIT-SYNC-V01
status: approved
decider: user
decided_at: 2026-07-30T19:07:06+08:00
related_plan: PLAN-PRL-ROUTE-H-DCM-ECM-STAGE0-STAGE2-V01
related_inspection: INSPECT-PRL-ROUTE-H-STAGE0-V03-V01
memory_target:
---

# Route H 阶段打包、请示门与 GitHub 同步规则 v01

## 1. 用户授权

用户要求：

> 把项目分成阶段；阶段内部由 Codex 先打包完成一部分，只在有必要时请示；阶段性与 GitHub 远端同步。

本决定取代原计划中“Git commit/push 不在授权范围”的限制，但不改变科学阶段的进入门：

- 当前允许正常创建分支、提交和推送 Route H 阶段产物；
- Stage 1、Stage 2 和更高阶段仍须在进入时获得用户授权；
- 不授权删除项目材料、改写 Git 历史、强制推送、发布论文结论或绕过科学 falsifier。

## 2. 工作方式

采用单任务、阶段包推进，不建立总管窗口或多角色窗口。

每个阶段内部按以下闭环连续完成：

1. 修订工作版本；
2. 做最小充分的科学、格式和交叉引用检查；
3. 发现可在本阶段原路线内修复的问题时，直接生成下一小版本；
4. 达到稳定检查点后冻结并生成简明记录；
5. 提交并推送远端工作分支；
6. 达到阶段退出条件后，再向用户报告完整阶段包。

不再为下列阶段内部动作逐项请示：

- 创建 v04、v05 等同阶段修订版本；
- 修复检查报告中已经明确的 blocking finding；
- 更新合同、几何规格、cases、ledger 和 verification registry；
- 运行解析、静态一致性、哈希和只读科学自检；
- 新增修订日志、冻结记录和检查报告；
- 在当前阶段远端工作分支上正常 commit/push；
- 修复普通拼写、格式、路径、引用和测试登记问题。

## 3. 阶段划分

### Phase 0 — Stage 0 模型合同收敛

当前阶段，已授权继续。

范围：

- 模型层次、方程、符号、单位、边界、接触/黏附、载荷端口和功率账本；
- 确定性参考几何规范；
- cases、验证指标和 falsifier；
- 只读科学复核和必要的小版本修订。

当前入口：

- v03 已冻结；
- v03 检查状态为 `revision_required`；
- 下一内部工作包修复：
  - `V03-STERIC-SIGN-001`；
  - `V03-BLOOD-LOAD-DISCRETE-001`；
  - `V03-SOURCE-MAP-001`；
  - 同时显式记录两个 caveat。

退出条件：

- 冻结版本不存在 blocking scientific finding；
- 冻结件解析、交叉引用和 hash 检查通过；
- Stage 0 最终检查状态为 `accepted` 或 `accepted_with_caveats`；
- 没有网格实例、求解器或数值响应被提前创建。

Phase 0 内部修订无需再次批准。只有当修复必须更换核心科学路线时才请示。

### Phase 1 — Stage 1 被动内核

进入前需要用户一次性批准。

批准后可在阶段内部连续完成：

- reference bundle materialization；
- DCM 被动能、ECM 有限变形、contact/adhesion、loads、support、ledger；
- 单元与模块测试；
- 失败修复、加密和阶段检查；
- 阶段性 GitHub 同步。

退出条件：

- Stage 1 注册测试全部终止且状态可审计；
- blocking 测试通过；
- 未启用主动完整 patch trajectory；
- 检查状态为 `accepted` 或 `accepted_with_caveats`。

### Phase 2 — Stage 2 机械验证 Gate A–E

进入前需要用户一次性批准。

批准后 Gate A–E 严格顺序自动推进：

- 当前 gate 通过才进入下一 gate；
- 普通数值修复和重复验证在阶段内部完成；
- falsifier 触发、需要改变模型机制或参数证据边界时停止请示；
- 不为每个正常通过的 gate 单独请求批准。

退出条件：

- A–E 的 pass/fail/not-run 状态完整；
- 功率、作用—反作用、接触、时间/空间离散证据完整；
- 无正式论文图、机制 claim 或生理标定。

### Phase 3 — 数据、标定、正式图件与论文主张

进入前必须另行批准范围、数据和 claim。

Phase 3 不由 Phase 2 自动授权。

## 4. 仅在这些情况下请示

1. 进入 Phase 1、Phase 2 或 Phase 3；
2. 必须更换核心模型路线、主动机制、接触形式或证据解释；
3. falsifier 已触发，继续需要在多个科学方案间选择；
4. 需要新增外部数据、非零生物源、参数标定或扩大研究对象；
5. 需要删除材料、覆盖冻结件、强制推送、改写 Git 历史或其他难恢复操作；
6. 需要发布论文图、稿件、release、公开结论或其他对外 claim；
7. 权限、凭据或远端冲突无法在不损坏历史的前提下解决。

普通错误、同阶段版本迭代和正常 Git 推送不属于请示门。

## 5. GitHub 同步策略

远端：`origin`。

分支策略：

- 每个活动阶段使用 `codex/<phase-scope>` 远端工作分支；
- 当前使用 `codex/stage0-closure`；
- `main` 只接收达到阶段退出条件的稳定包；
- 禁止 force push 和历史重写。

同步点：

1. 阶段开始或已有历史首次纳入版本控制；
2. 每个冻结版本及其检查报告形成后；
3. 重要修订包通过本地检查后；
4. 向用户提交阶段决策前；
5. 阶段闭合并进入稳定主线后。

每次推送前：

- 只纳入 Route H 当前阶段范围文件；
- 检查 `git status` 和 staged diff；
- 运行该检查点所需的解析/测试/hash；
- 不推送明显破损的瞬时草稿；
- 若远端前进，先获取并安全整合，不强制覆盖。

提交命名：

- `stage0: ...`
- `stage1: ...`
- `stage2: ...`
- `governance: ...`

## 6. 当前执行决定

1. 将 v02、v03、相应执行/冻结/检查记录和本决定组成 Phase 0 历史检查点；
2. 建立并推送 `codex/stage0-closure`；
3. 随后在该分支内自主完成 Stage 0 修订闭环；
4. 只在 Stage 0 达到退出条件或遇到第 4 节真实请示门时再集中报告；
5. Stage 1 仍不授权。
