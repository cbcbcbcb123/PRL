---
document_id: PRL-REPOSITORY-CLEANUP-CLOSURE-AND-SCIENCE-RESTART-PROPOSAL-V01
status: authorized_execution_active
frozen_at: 2026-09-15
execution_status: active
deletion_authorized: true
scientific_execution_authorized: conditional_after_all_cleanup_and_performance_gates
---

# PRL 清理收口与科学重启一次性审批包 v01

## 结论

可以用一次精确审批完成余下收口，并在全部门通过后直接继续CPU科学任务。此次审批包冻结31个破坏性目标：15个递归目录和16个单文件；现场统计共10,336个文件、446个子目录、4,598,021,645逻辑字节，0个reparse point。冻结清单SHA-256为 `c44b1eb1ab59ac692453b4829a9b0a427cc4e66a23f81fbb2b1d52caf696446b`。它同时冻结Batch 4候选1/2收口、Batch 5新本地Git基线、Batch 6验收，以及条件式接触性能与扩展双胞平衡切片。

用户已于2026-09-15按冻结清单哈希原样确认，删除前复核为`passed`。Batch 5A首次发生部分删除后按规则停止；用户又明确允许仅在同一`.git`目标内清除剩余9,994个普通文件的ReadOnly属性并重试。旧Git现已完全删除，本地`codex/clean-baseline`已创建且远端为0；其余30目标、求解器和GPU尚未处理，执行继续进入首提交保全。

## 一次审批后的固定执行顺序

1. **删除前总复核**：先核对[机器清单](evidence/repository_cleanup_v01/final_closure_deletion_targets_v01.txt)SHA-256仍为 `c44b1eb1ab59ac692453b4829a9b0a427cc4e66a23f81fbb2b1d52caf696446b`，再逐项读取、规范化绝对路径，核对工作区边界、类型、递归范围、文件数、字节数、Git状态和reparse point。新增路径、范围扩大、发现链接/唯一成果或保护路径缺失时立即停止。
2. **Batch 5A旧Git替换**：永久删除旧 `E:\Temp-Projects\PRL\.git`，随即建立无远端的本地 `codex/clean-baseline`。第一个根提交只保留当前有效源码、上游内核/许可证、治理与计划，以及[48项精选迁移前来源](evidence/repository_cleanup_v01/final_closure_selected_source_set_v01.txt)，不保留全部旧历史。
3. **Batch 4代码收口**：完成 `python -m prl run / verify / render / storage / test`；把8个C++应用从“重命名main并包含旧.cpp”迁移到正常头文件/实现库；建立当前根级构建入口；运行器与独立验证器只共享格式层。先用旧/新小规模输出做数值对照，不改力学方程或门限。
4. **性能候选工程门**：只优化表面求积的候选面搜索，按[科学合同](ventricle_contact_performance_and_extended_equilibrium_contract_v01.md)完成数值等价、作用反作用、能量梯度、正间隙和2/4/16胞静态性能门。工程门失败即停止，不使用candidate做科学运行。
5. **Batch 5B活动树精简**：上述迁移与回归全部通过后，永久删除旧 `scripts/`、16个根级旧测试、12个无当前合同引用的Z1开发/烟测目录及一个误建零字节目录；随后提交清洁的第二个本地提交。若迁移失败，Batch 5B不执行。
6. **Batch 6验收**：验证最终HEAD可独立检出、构建、跑quick suite和紧凑fixture；旧结果独立复核仍一致；所有清单目标消失，新 `.git` 身份明确，保护路径存在，严格链接通过；项目≤2 GiB目标及3 GiB硬门真实生效。
7. **条件式科学重启**：只有前六步全部`passed`且存储准入通过，才运行4条CPU扩展双胞轨迹并生成实际结构、场量、结果曲线和五状态GIF。任何失败均不自动重跑或改参数。

Batch 5A与Batch 5B是同一审批包内两个预先冻结的子批次；任一子批次出现部分失败，立即停止，不进入后续子批次。

## 破坏性目标与不可恢复影响

完整路径逐项见[冻结清单](evidence/repository_cleanup_v01/final_closure_deletion_targets_v01.txt)，现场数值见[机器盘点](evidence/repository_cleanup_v01/final_closure_inventory_v01.json)。

17:39存储门复核时工作区共15,002个普通文件、1,666个目录、5,773,809,821逻辑字节，另有78个保留的历史取证reparse point。它们均不在冻结目标内且盘点未跟随；31个目标自身及其后代仍为0个reparse point。删除冻结目标后的静态底数约为1,175,788,176字节；新Git、构建和科学输出仍必须分别通过2 GiB目标与3 GiB硬门，不能把该估算当作最终验收。

| 子集 | 路径数 | 文件数 | 逻辑字节 | Git/证据判断 | 永久影响 |
|---|---:|---:|---:|---|---|
| 旧 `.git` | 1目录 | 10,095 | 4,464,182,252 | 不是工作树材料；含8本地分支、3标签、5快照、7检查点、569条reflog及2个不可达commit | 本地旧对象库、reflog、未推送/不可达历史永久不可恢复；远端不改变 |
| 旧 `scripts/` | 1目录 | 119 | 1,953,400 | 22个旧Git跟踪文件；活动入口迁移后不再运行。34个当前/来源绑定脚本先进入新根提交 | 其余旧脚本不再可运行；历史结果只能按精选来源和记录解释 |
| 根级旧测试 | 16文件 | 16 | 41,009 | 当前旧Git均未跟踪；4个来源绑定测试先进入新根提交，当前物理门迁入`tests/prl` | 旧位置测试不可直接运行 |
| Z1开发/烟测 | 12目录 | 105 | 131,844,984 | 0跟踪、0链接、0当前合同引用、0 reparse；部分字节与正式包重复，其余是被正式包/诊断取代的开发轨迹 | 非重复的中间逐步数组永久丢失，不能再声称这些烟测原包完整 |
| 误建目录 | 1目录 | 1 | 0 | 仅含零字节 `ventricle_z.lua`，0跟踪、0引用、0 reparse | 无科学内容可恢复 |

旧Git详情已写入[元数据快照](evidence/repository_cleanup_v01/batch05_old_git_snapshot_v01.json)。该快照只证明引用身份，不能恢复4.16 GiB对象库。

待捕获的[48项迁移前来源](evidence/repository_cleanup_v01/final_closure_selected_source_set_v01.txt)均存在，共528,865逻辑字节、0个reparse point；清单SHA-256为 `c6335f6614d35857367acac6e5219008c14a4280224040f9acd9601e2147528b`。按“相对路径|字节数|文件SHA-256”组合得到的来源记录集SHA-256为 `5736c10d921976315ca579d63dc53b9a758f3eed6d3b27f3f9f9c6a91366abc3`。它们必须先进入新Git第一个根提交，才允许删除旧入口。

12个Z1临时目录中，逐字节比较确认TF2B v01的6/6文件全部在正式材料中存在精确副本；其他目录仍含非重复开发账本。因此删除依据不是“重复文件”，而是它们均为无合同引用的开发/烟测输出，关键结论已经进入正式结果、失败诊断或执行记录。本次明确接受其不可完整复算的影响。

## 必须保留并复核的路径

- `E:\Temp-Projects\PRL\AGENTS.md`、`START_HERE.md`、`README.md`、`pyproject.toml`；
- `plan/active/PRL_Codex_Stage_Contracts_v03/` 与 `plan/INDEX.md`；
- `project_control/`、`memory/project_cockpit/`、`docs/`、`references/`；
- `external/simucell3d/` 的源码、`License`、`PRL_FORK.md`；
- `src/prl/`、`src/prl_ventricle_support/` 及当前C++应用源码；
- `tests/prl/` 和迁移后的当前回归；
- `b/z1m0a/` 中与保留结果哈希绑定的当前可执行文件，至少保留到新构建及对照完成；
- `results/ventricle_z1/` 的13个当前/关键包，尤其长程双胞、正间隙接触、二维几何和关键失败包；
- `tmp/pdfs/`、两个含reparse point的Paper2取证目录、其他Paper2宿主取证目录及 `tmp/z1_bioform_myo_repair_v03_diagnosis_20260913/`。

未列入冻结清单的路径一律不删除。保留的Paper2临时目录是历史取证依赖，不参加当前运行；其reparse point不跟随。

## 新Git基线合同

新仓库仅本地建立，分支 `codex/clean-baseline`，不配置remote、不fetch、不push、不强推。两个提交的目的分别是：

1. `baseline: preserve selected pre-refactor evidence`：捕获有效配置、当前源、唯一上游源码/许可证、治理记录、当前专家包、34个选择脚本、4个来源绑定旧测试和10个被迁移C++源；
2. `refactor: establish current PRL mainline`：记录稳定`prl`入口、正常C++边界、当前测试、存储门与已批准旧入口删除。

最终默认不跟踪 `results/`、`b/`、`tmp/`、`artifacts/`、渲染预览、运行原始数组或缓存；禁止无边界 `git add .`。正式结果仍保留在本机工作区并由哈希/清单管理。新建紧凑fixture只包含独立验证所需的标量账本和最小几何，确保最终HEAD检出后能构建和验证，不把227 MiB长程结果写入Git。

## 停止点

出现下列任一情况即停止并报告：冻结路径集合或递归属性漂移；发现reparse point、原始材料或唯一成果；任何保护身份不一致；C++/Python迁移行为对照失败；接触数值等价或性能门失败；新基线不能独立构建/验证；项目仍高于3 GiB；科学输出预算不足；需要GPU、安装、工作区外写入或扩大删除范围。

本审批不授权其他路径、其他删除接口、自动重跑、参数放宽、远端Git操作、GPU或工作区外写入。

## 审批前独立复核

- 31/31目标存在、类型和递归属性一致；全部位于 `E:\Temp-Projects\PRL` 下，不含工作区根，目标内0个reparse point；目标合计仍为10,336文件、446子目录、4,598,021,645字节。
- 48/48项迁移前来源存在、位于工作区内且0个reparse point；清单与组合记录集哈希均已登记。
- 历史Batch 4身份文件保持原样；当前README导航与有界身份加载器的两项有意变化另存于[收口身份覆盖记录](evidence/repository_cleanup_v01/final_closure_identity_overrides_v01.json)。最终默认pytest与显式quick suite均为19/19 passed。
- 长程双胞保留结果独立复核为passed；这只确认既有证据未漂移，静态平衡仍为failed，父Z1与生物学验证仍为blocked。
- 驾驶舱严格检查通过28个本地链接和207个证据路径，0缺失。存储门正确返回hard-limit-exceeded，科研求解器未启动。

## 待确认的唯一授权语句

`确认执行PRL清理收口与科学重启v01：授权按SHA-256=c44b1eb1ab59ac692453b4829a9b0a427cc4e66a23f81fbb2b1d52caf696446b的final_closure_deletion_targets_v01.txt冻结清单，对15个目录使用System.IO.Directory.Delete递归删除、对16个文件使用System.IO.File.Delete；授权永久替换E:\Temp-Projects\PRL\.git并建立无远端的本地codex/clean-baseline两提交基线；授权完成Batch 4候选1/2、Batch 5/6及接触性能工程门，并仅在全部清理验收passed且项目不超过3GiB时执行ventricle_contact_performance_and_extended_equilibrium_contract_v01的单线程CPU任务，0 GPU、不自动重跑；不授权其他路径或接口。`
