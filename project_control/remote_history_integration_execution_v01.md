---
record_id: PRL-REMOTE-HISTORY-INTEGRATION-EXECUTION-V01
executed_at: 2026-09-17
local_merge: passed
remote_push: passed
scientific_stage_execution: not_run
---

# 旧远端六分支历史并入main，保留当前FEM内容

## 已完成

已将用户确认的`https://github.com/cbcbcbcb123/PRL.git`登记为origin，获取全部六个heads，
没有获取tags/submodules或执行prune/gc。取回约83 MiB，18.06秒，低于192 MiB/180秒预算。
本地Git复核确认所有分支头都已包含在`b45650a9e370be138a70acf305b6c3a21e6a7ed2`中。

先创建`bc85d202`，提交149个明确列出的文件：FEM主线、必要Python历史读取依赖、测试、
来源/阶段记录和本次审计。源码及小型记录约1.9 MB；旧C++/DCM改动等50项仍留在工作区，
逐项哈希不变。提交代码不授权重新运行DCM。

随后创建`bbc4b5be`双亲合并提交，第一父为上述FEM检查点，第二父为远端历史总头`b45650a9`。
方式为`--allow-unrelated-histories -s ours --no-ff`：只接上历史，工作树以当前FEM内容为准。
两提交树均为`a8cd5f369b5193ef5848fbbbb7553ab025e298b8`，逐文件差异0。
这不是把旧科学代码逐项恢复；原两套历史均保持可达，没有强推或历史改写。

六个远端分支头现均为本地main祖先；没有新建任务分支、worktree，没有删除文件或远端分支。
当前工作区不是全干净状态：50项原有修改/未跟踪历史材料保留，未擅自提交或清除。

## 验收与边界

- FEM相关回归348通过、44子测试通过；无Docker/GPU或新科学阶段运行。
- 合并树与FEM父树完全一致，未解决冲突0，76个源码/数据工具哈希不变。
- Git完整性检查退出0，32条dangling对象提示原样保留，不做垃圾清理；驾驶舱24个HTML链接与308个证据路径检查通过。
- F6-S0父包69项、主动子包76项清单哈希全部一致；既有失败记录及原始数组保留。
- 工作区扫描1,993,155,457逻辑字节（约1.856 GiB），9,831普通文件，无扫描错误，低于2 GiB目标与3 GiB硬限。
- 默认Git空白检查发现11处既有文件末尾空行；只在检查时忽略blank-at-EOF，不改写这些文件，其他空白检查通过。
- 已知全仓图像依赖/绝对路径静态资格问题未处理，不宣称全仓测试或生物学验证通过。
- 原始结果数组、PNG/GIF仍按既有.gitignore保留本地；Git同步不等于完整数据备份，远端相对结果链接不保证可用。

详见[提交范围](evidence/git_main_integration_v01/checkpoint_scope.json)、
[前后保全清单](evidence/git_main_integration_v01/preflight_manifest.json)、
[获取回执](evidence/git_main_integration_v01/fetch_report.json)和
[合并复核](evidence/git_main_integration_v01/merge_verification.json)。

## 远端发布

用户随后明确授权“普通推送main”。2026-09-17已普通快进推送，将远端main从`16bf8843`
更新至`dd30620a`，随后提交并普通推送本次状态回执。没有force选项、没有推送tags或其他分支。
初次推送后读取全部heads确认其余五个分支头逐项未变；50项原有未提交文件哈希仍一致。
见[推送回执](evidence/git_main_integration_v01/push_execution_v01.json)。
后续阶段继续直接本地提交main；本次明确推送不扩大为自动强推或删除远端分支的权限。
