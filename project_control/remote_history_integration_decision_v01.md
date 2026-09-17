---
decision_id: PRL-REMOTE-HISTORY-INTEGRATION-V01
status: adopted
decided_at: 2026-09-17
branch: main
remote: https://github.com/cbcbcbcb123/PRL.git
execution_status: passed_local_merge_remote_push_not_run
---

# 远端旧历史与当前FEM主线的衔接

用户要求合并远端全部分支、今后阶段直接提交main；随后提供本仓库地址，并在确认
远端是同一项目旧版本、本地已重建精简FEM基线后要求继续。

## 本轮实现边界

- 先按显式清单提交此前已完成的FEM主线、数据入口、必要Python依赖、测试及执行记录；不改变力学实现。
- 原有DCM/C++未提交修改、历史阶段合同与无关测试修改留在工作区原处，逐项哈希保全。
- 所有旧远端分支均已包含在`b45650a9e370be138a70acf305b6c3a21e6a7ed2`内；获取后再次用本地Git祖先关系复核。
- 新旧根历史不相连时，采用`git merge --allow-unrelated-histories -s ours --no-ff`记录双亲：保留当前FEM树，接入旧远端可达历史，不将退役代码恢复为活动实现。
- 这不是逐文件采用旧分支内容，也不是squash或重写历史。合并提交的树必须与其FEM父提交完全一致，全部六个旧分支头必须成为main祖先。
- 本次明确的历史衔接取代上一规则中“无指定远端时不自动接入无关历史”的暂停状态；不恢复清理中已删除的本地未推送对象、reflog或大包。
- 不创建工作分支或worktree，不强推、不删分支、不清理文件。普通推送仍按用户本次明确答复执行。

## 范围与预算

阶段输入与候选清单见`evidence/git_main_integration_v01/preflight_manifest.json`。
其中selected为最终阶段提交候选141项，excluded为保留未提交的50项；提交前仍须复核哈希与Git索引。
原始结果数组、PNG/GIF、构建和缓存继续按.gitignore保留在本地，不强制入Git。
因此本次Git同步是源码与小型记录同步，不宣称远端包含所有原始数据或可直接查看本地结果图。

阶段新增预算192 MiB，停止保全64 MiB；获取前项目约1.775 GiB，3 GiB总门通过。
只获取该origin的heads，不拉tags或submodules，不自动gc/prune；有界获取180秒，
若Git逻辑大小新增超过192 MiB或总预算不满足即停止，不自动删除下载结果。

## 验收

1. 当前FEM相关单元/CLI回归、Python语法和文件清单检查；已知全仓静态资格问题如实保留，不扩大为科学全通过。
2. 所有未纳入提交的既有文件哈希不变；大型科学结果不被Git操作改写。
3. 合并双亲、树身份及六分支祖先关系全部成立，工作区无合并冲突。
4. 如获准普通推送，只更新远端main；远端其余分支头不变、无强制选项。
5. 同步项目状态与严格链接检查。无新科学阶段、无DCM运行、无GPU、无安装。
