---
document_id: PRL-REPOSITORY-CLEANUP-CLOSURE-EXECUTION-V01
status: active
authorized_at: 2026-09-15
execution_status: active
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
| Batch 5A旧Git替换及首提交 | active | 旧Git已完全删除，新仓库已初始化；首提交待建立 |
| Python/C++当前入口迁移 | not_run | 不改力学方程和阈值 |
| 接触等价与性能门 | not_run | 失败即停止 |
| Batch 5B其余30路径删除 | not_run | 仅迁移与性能门通过后 |
| 第二提交与Batch 6 | not_run | 新Git无远端 |
| 条件式扩展双胞CPU运行 | not_run | 清理及性能门全部passed后 |

科学状态保持：静态平衡`failed`、父Z1与生物学验证`blocked`。工程清理通过不能替代科学通过。

## Batch 5A部分失败回执

获准的`System.IO.Directory.Delete`在旧`.git`内遇到首个ReadOnly对象后抛出拒绝访问并退出。执行前为10,095文件、438子目录、4,464,182,252字节；失败后剩余9,994文件、381子目录、4,463,695,514字节，因此确认已永久移除101文件、57目录、486,738字节。剩余9,994个普通文件全部带ReadOnly属性，0 reparse point。

首个报告对象为`E:\Temp-Projects\PRL\.git\modules\external\simucell3d\objects\02\e960f45958242b52c35ddab9785404c2443775`，403字节。没有初始化新Git，没有处理其余30个冻结目标，没有运行求解器或GPU。由于局部`.git`元数据已不完整，无约束Git命令会向上发现`E:\Temp-Projects\.git`；本轮只做了只读身份探测，未修改父仓库，后续Git操作已停止。

机器回执见`evidence/repository_cleanup_v01/batch05a_old_git_partial_deletion_v01.json`。按项目安全合同，继续前需用户明确允许仅在同一获准`.git`路径内清除剩余普通文件的ReadOnly属性，再重试同一删除接口。

## Batch 5A恢复

用户随后明确允许仅对同一`.git`目标内剩余9,994个普通文件使用`System.IO.File.SetAttributes`清除ReadOnly属性，并重试原删除接口。复核剩余文件数、目录数、字节、ReadOnly数与0 reparse完全一致后，9,994/9,994属性清除成功，旧`.git`完全消失。随后显式在`E:\Temp-Projects\PRL\.git`建立本地`codex/clean-baseline`，初始18文件、8目录、26,359字节，远端0。父级Git未修改。

首提交范围已冻结在`evidence/repository_cleanup_v01/batch05a_new_git_first_commit_scope_v01.json`；不使用无边界`git add .`。
