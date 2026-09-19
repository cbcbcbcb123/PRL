---
decision_id: PRL-MAIN-BRANCH-STAGE-PUSH-V01
decided_at: 2026-09-19
decider: user
status: approved
remote: origin
remote_url: https://github.com/cbcbcbcb123/PRL.git
allowed_ref: refs/heads/main
---

# 阶段完成后同步远端

2026-09-19后续补充：用户明确默认只同步、不需要评审包。
按[最新决定](main_branch_sync_without_review_package_decision_v01.md)执行；下文关于每次另建审阅包的默认要求已被取代，历史交付保留。

用户原话：“每次完成你都要同步到远端，这样专家才能查看”。

## 长期工作规则

1. 阶段交付物保存、必要检查和证据裁决完成后，在main做明确范围的本地提交，随后普通推送origin/main，不再逐次请求推送确认。
2. 科学failed、blocked或not_run必须保留真实含义。经检查的失败保全记录也需同步；推送成功不代表科学通过。运行仍须有适用合同及授权。
3. 每次推送前核对远端地址、当前分支、工作区/暂存区、待发布提交、文件体积与快进关系。仅暂存本阶段路径，不纳入无关旧改动。
4. 唯一推送目标为 `origin` 的 `refs/heads/main`，显式禁用自动跟随标签：

   ```powershell
   git -c push.followTags=false push --no-follow-tags origin refs/heads/main:refs/heads/main
   git ls-remote --heads --tags origin
   git rev-parse refs/heads/main
   ```

5. 回读远端main与本地提交一致才报告同步完成；同时核对其他远端引用未被本次操作改变。遇到网络、认证、非快进或内容范围异常时停止推送，保存本地成果并说明未同步及原因，不自行强推、合并未知变更、重写历史、删除引用或重置工作区。
6. 阶段报告写清本地提交、远端核验结果及专家可访问入口。未同步不得用“已完成”掩盖发布阻断。

## 专家审阅与存储

- GitHub保留当前源码、合同、验证摘要、来源清单及必要小型结构/结果预览。首页和最新审阅页必须使用仓内相对链接，不能只指向本机结果库。
- 最新小型审阅包放在 `docs/review/<stage>/`；已有认可图件原样复制并核验SHA-256，不改变冻结原包、不伪造新结果。默认只留有直接裁决价值的一套预览，不上传所有试画副本。
- 完整原始数组、大型结果、构建及缓存继续留在已批准的 `E:\Temp-Projects\PRL-results` 等既有受控位置。现有.gitignore及存储预算不放宽；不使用无边界git add或force-add大型结果。
- 在线摘要不能替代原始状态、完整验证或可复现性；原始包不随Git同步时必须说明，仅克隆Git仓不能完成保存态复核。
- 本次补发远端main之后的4个已完成提交，新增最新v03的小型摘要及373656字节原样PNG。50项既有未提交文件不纳入。

## 取代与未改变范围

取代此前“只本地阶段提交、不自动推送”的默认规则及旧导航中的对应陈述。
main唯一长期分支、普通非强制推送、保留旧改动及失败证据、FEM唯一主线继续有效。
不授权额外科学计算、删除、安装、GPU、外部归档或任何其他远端分支/标签操作。
不改写历史执行记录中的“当时未推送”；新的同步记录只补充后续事实。
