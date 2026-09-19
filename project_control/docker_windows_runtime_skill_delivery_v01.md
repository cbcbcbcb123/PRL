# Windows Docker 运行时技能交付 v01

日期：2026-09-19。技能工程与安装 `passed`；Docker 运行时 `blocked`；原四工况仍 `not_run`。

## 授权与交付

用户要求将既往 Docker 故障处置写成 skill，随后明确批准只新增
`C:\Users\chenb\.codex\skills\cb-docker-windows-runtime`。
本次已在该原先不存在的目录 create-only 安装 5 个文件，合计 31,025 bytes；
没有修改其他全局配置、全局 memory、Docker 文件、权限或软件。

可审阅源码：[SKILL.md](../tools/skills/cb-docker-windows-runtime/SKILL.md)。
源码保存在 `tools/skills/`，不是第二份自动发现目录，避免本机出现两个同名技能。
当前宿主已有的个人技能目录及用户指定安装路径优先；未额外创建 `.agents` 用户目录、
未重启 Codex，UI 实时发现状态为 `not_run`，不以文件安装冒充 UI 验证。
技能格式与显式/隐式调用语义参考 [OpenAI 官方技能文档](https://learn.chatgpt.com/docs/build-skills)。

## 固化的决策

- 在普通启动之前核对历史与当前套接字；引擎不可用且 ACL 报1920时立即阻断。
- 零字节/ReparsePoint、旧日志、后台进程存在均不能单独决定损坏或引擎就绪。
- 普通启动、精确路径修复、科学计算分开授权；受控修复后复发不自动轮换目录。
- 只读脚本限定本机 Linux 引擎管道、无重试、每探针15秒上限；不随当前远端 context 连接外部主机。
- 不提供启动、修复、删除或科学执行脚本。原模型、本构、阈值、运行器均未改。

## 验证与保留的失败

[安装及最终验证](evidence/docker_runtime_skill_v01/installation.json)：
16 项回归测试、标准 skill 格式检查、5 文件源码/安装副本逐字节 SHA-256、
已保存 JSON 的无子进程重放均通过；重放返回2，正确保留 `blocked`。
测试覆盖误判、远端环境覆盖、超时不重试、镜像不匹配、复发停止与环境不修改。

第一次实机探针遇到**检查器自己的兼容问题**：PowerShell 7 向 Windows PowerShell 5.1
传递模块搜索路径，导致 `Get-Acl` 模块无法加载。首次检查未误报通过，记录见
[失败原包](evidence/docker_runtime_skill_v01/first_probe_collector_issue.json)。
只在检查器的 Windows PowerShell 子进程中不继承 `PSModulePath`，让其使用本机默认模块；
未改用户环境变量、模块、执行策略或 ACL。补回归后第二次实机检查成功读取到原错误。

[最终只读实机快照](evidence/docker_runtime_skill_v01/live_preflight.json)：
18:32:10（UTC+8），五个当前套接字 ACL 均报1920，Server=null，WSL docker-desktop Stopped；
判定 `stop_recurrence_no_directory_rotation`。日志仍为18:06那次已保存失败，并非本次新崩溃。
本次2次实机**只读检查**、0 Desktop启动、0修复/移动/删除/改权限/拉取/安装、0容器/JIT/FEM/GPU。
208 个受保护文件（含50项既有无关修改）哈希检查通过；没有触动此前失败包。

## 边界与唯一下一步

skill-creator 的行为测试要求促成了实机检查及兼容问题修复；技能能规范后续判断，
不能修复 Docker 底层故障，也未接入或替换科学运行器。
当前仍需单独裁决运行环境恢复方式；正常启动权限已用完，旧修复授权不能复用。
环境通过后才按既有授权继续原四工况，不扩大矩阵、不放宽门、不重回 DCM。
本轮无新计算，故未生成冒充求解结果的结构/场量图。

按长期规则提交并普通推送 `origin/main`；远端同步不等于运行时恢复或科学通过。
