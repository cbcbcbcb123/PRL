---
document_id: PRL-REPOSITORY-CLEANUP-CLOSURE-EXECUTION-V01
status: completed
authorized_at: 2026-09-15
execution_status: cleanup_passed_q_passed_e_failed_equilibrium
gpu: forbidden
remote_git_operations: forbidden
---

# PRL清理收口与科学重启执行记录 v01

## 授权与范围

用户已确认SHA-256为`c44b1eb1ab59ac692453b4829a9b0a427cc4e66a23f81fbb2b1d52caf696446b`的31路径冻结清单：15个目录仅使用`System.IO.Directory.Delete`递归删除，16个文件仅使用`System.IO.File.Delete`。另授权永久替换旧`.git`、建立无远端的本地`codex/clean-baseline`两提交基线、完成Batch 4候选1/2与Batch 5/6，以及在全部门通过后执行冻结的单线程CPU科学合同。未授权其他路径、接口、GPU、远端操作或自动重跑。

## 删除前复核

状态：`passed`。31/31目标与冻结类型、文件数、目录数、逻辑字节、Git跟踪数和reparse属性一致；合计10,336文件、446子目录、4,598,021,645字节、22个旧Git跟踪文件、0个reparse point。全部目标严格位于`E:\Temp-Projects\PRL`下且不等于工作区根或盘符根。

48/48项迁移前来源存在，共528,865字节、0个reparse point，组合记录集SHA-256为`5736c10d921976315ca579d63dc53b9a758f3eed6d3b27f3f9f9c6a91366abc3`。20个关键保护入口存在；默认与quick回归各19/19、保留长程双胞独立复核、严格链接检查均通过。机器回执见`evidence/repository_cleanup_v01/final_closure_preflight_v01.json`。

## 固定执行账本

| 步骤 | 状态 | 说明 |
|---|---|---|
| Batch 5A旧Git替换及首提交 | passed | 旧Git已完全删除；无父提交根基线`d53ca553`已建立，远端0 |
| Python/C++当前入口迁移 | passed | 统一Python入口、根构建及8个C++应用正常库边界已建立 |
| 接触等价与性能工程门 | passed | 预检中2胞无回退，16胞2.665×，节点力/能量/支撑面积等价；正式Q待Batch 6后执行 |
| Batch 5B其余30路径删除 | passed | 同一冻结清单30/30永久删除，释放133,839,393 bytes，保护入口无缺失 |
| 第二提交与Batch 6 | passed | 两提交、无远端、Git fsck、全构建、CTest、quick、长程/紧凑复核、严格链接和存储门均通过 |
| 条件式扩展双胞CPU运行 | completed | 正式Q passed；E四轨迹安全完成但静态残力门failed，裁决`failed_equilibrium` |

科学状态保持：静态平衡`failed`、父Z1与生物学验证`blocked`。工程清理通过不能替代科学通过。

## Batch 5A部分失败回执

获准的`System.IO.Directory.Delete`在旧`.git`内遇到首个ReadOnly对象后抛出拒绝访问并退出。执行前为10,095文件、438子目录、4,464,182,252字节；失败后剩余9,994文件、381子目录、4,463,695,514字节，因此确认已永久移除101文件、57目录、486,738字节。剩余9,994个普通文件全部带ReadOnly属性，0 reparse point。

首个报告对象为`E:\Temp-Projects\PRL\.git\modules\external\simucell3d\objects\02\e960f45958242b52c35ddab9785404c2443775`，403字节。没有初始化新Git，没有处理其余30个冻结目标，没有运行求解器或GPU。由于局部`.git`元数据已不完整，无约束Git命令会向上发现`E:\Temp-Projects\.git`；本轮只做了只读身份探测，未修改父仓库，后续Git操作已停止。

机器回执见`evidence/repository_cleanup_v01/batch05a_old_git_partial_deletion_v01.json`。按项目安全合同，继续前需用户明确允许仅在同一获准`.git`路径内清除剩余普通文件的ReadOnly属性，再重试同一删除接口。

## Batch 5A恢复

用户随后明确允许仅对同一`.git`目标内剩余9,994个普通文件使用`System.IO.File.SetAttributes`清除ReadOnly属性，并重试原删除接口。复核剩余文件数、目录数、字节、ReadOnly数与0 reparse完全一致后，9,994/9,994属性清除成功，旧`.git`完全消失。随后显式在`E:\Temp-Projects\PRL\.git`建立本地`codex/clean-baseline`，初始18文件、8目录、26,359字节，远端0。父级Git未修改。

首提交范围已冻结在`evidence/repository_cleanup_v01/batch05a_new_git_first_commit_scope_v01.json`；不使用无边界`git add .`。

首提交已完成：`d53ca553fd8bba9965d850106fd9305da76be668`，提交说明为`baseline: preserve selected pre-refactor evidence`，父提交0、远端0。首提交后没有amend；旧历史不可恢复。

## Batch 4迁移与性能工程门

根级CMake入口已经建立；心肌自由态与M0实现分别形成`prl_bioform_model`和`prl_m0_model`，8个当前应用不再通过重命名`main`包含历史`.cpp`。旧/新2胞静态输出与4步动力输出逐表一致。稳定Python包现提供`run / verify / render / storage / test / validate`，当前测试不再导入`scripts/`。

接触候选只改变最近目标面的候选枚举：大于4胞时把原生USPG候选按体素和目标细胞预分组；2/4胞保留冻结线性求积路径。预检中2胞候选/基线中位数比为`0.8620`，16胞从冻结`12.1500 s`降至`4.5597 s`（`2.6646×`）；2胞和16胞节点力最大绝对差均为0，active sample、能量和支撑面积一致。证据见`evidence/repository_cleanup_v01/contact_performance_engineering_preflight_v01.json`。这只允许进入正式三重复Q，不是正式Q本身，也不是科学平衡通过。

## Batch 5B删除与删除后复核

删除前在同一PowerShell进程中重新加载SHA-256为`c44b1eb1ab59ac692453b4829a9b0a427cc4e66a23f81fbb2b1d52caf696446b`的冻结清单，排除已经完成替换的`.git`后，剩余30目标逐项匹配原盘点：14个递归目录、16个单文件，共241个普通文件、8个子目录、133,839,393字节、0 reparse point、0 ReadOnly。新根提交使其中38个来源成为已跟踪项，这是审批包预定的保全后退役，不是内容或范围漂移。

仅对14个目录调用`System.IO.Directory.Delete(..., true)`，仅对16个文件调用`System.IO.File.Delete`。30/30目标永久消失，未完成目标0，14个关键保护入口无缺失，未处理任何未授权路径。删除的开发/烟测中间数组不能完整恢复；首提交捕获的34个脚本和4个旧测试仍可由`d53ca553`读取。删除后根级全构建、CTest 1/1、quick 27/27、保留长程结果与紧凑fixture独立复核均通过。

删除后存储扫描为7,218个普通文件、1,975个目录、1,332,608,921逻辑字节；扫描不跟随78个保留历史取证reparse point且无扫描错误。当前占用低于2 GiB目标；加入256 MiB科学输出和64 MiB停止保全后投影为1,668,153,241字节，低于3 GiB硬限。

## Batch 6收口验收

状态：`passed`。当前分支为`codex/clean-baseline`、提交数2、远端0；无父首提交仍为`d53ca553`，旧历史没有恢复。`git fsck --full`、根级Release配置与全构建、CTest 1/1、quick 27/27、保留长程双胞及紧凑fixture独立复核均通过；驾驶舱24个HTML链接和214条证据引用无缺失。

最新准入扫描为7,306个普通文件、1,975个目录、1,332,845,967逻辑字节；加入256 MiB任务预算和64 MiB停止保全后投影1,668,390,287字节，仍低于2 GiB目标和3 GiB硬限。机器裁决见`evidence/repository_cleanup_v01/final_closure_verdict_v01.json`。本裁决只证明清理/工程门通过；正式Q和扩展平衡在裁决时仍为`not_run`。

## 条件式科学重启结果

清理门通过后仅运行获准的单线程CPU合同，0 GPU、0自动重跑。正式Q执行39次调用并独立裁决`passed`：16胞中位加速2.5203×、2胞candidate/baseline为0.9432，9组逐节点力/能量/支撑等价且21/21旧回归通过。随后E的4/4双胞轨迹安全到达算法坐标20，粗细步长位移误差小于0.019%，但末态自由力0.01775–0.02133仍高于0.001，因此严格记录为`failed_equilibrium`。详见`ventricle_contact_performance_and_extended_equilibrium_execution_v01.md`。

绘图后科学结果包为128文件、13,393,641 bytes；写入最终治理元数据前的工作区检查点为1,346,360,270逻辑字节，仍低于2 GiB目标和3 GiB硬限。该负结果不推翻数值安全或Q性能通过，也不构成心肌组织、生物学或三层模型验证。后续需另行冻结末态残力分解，不自动继续计算。
