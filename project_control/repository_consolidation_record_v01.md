# PRL cell-engine 单仓库迁移记录 v01

日期：2026-08-29

状态：`completed`

性质：仓库结构与 provenance 迁移；不构成科学结果接受或 Human Gate 通过。

## 决策

原私有仓库 `cbcbcbcb123/prl-cell-engine` 与 PRL 属于同一项目。其代码与完整
Git 历史已经并入 `cbcbcbcb123/PRL`，本地路径继续使用
`external/simucell3d/`，从而避免改变现有 CMake、测试与证据路径。该目录现为
普通受版本控制目录，不再是 Git submodule。

历史报告中指向旧仓库、旧分支或 submodule commit 的记录保持原样，作为当时
操作的真实 provenance；它们不再代表当前仓库结构或后续同步入口。

## 可追溯锚点

- 旧仓库最终导入提交：`5864a63d5b77943812ddfeb2b44442dab4f8a068`；
- 旧仓库最终导入树：`8ad3f8067f493962a6d9064c13ab40221a9b1b0c`；
- PRL 历史保留合并提交：`918d20c8e1090f4cbf9887994f50160da5042739`；
- PRL 迁移后换行规范化提交：`57733e86b3a60563c293e0860a76cbe72980344c`；
- PRL 保全标签：`prl-cell-engine-import-20260829`，指向旧仓库最终提交；
- PRL 单仓库标签：`prl-monorepo-integration-20260829`，指向迁移完成提交；
- PRL 远端分支：`codex/simucell3d-hybrid-feasibility`。

历史保留合并提交具有两个父提交：迁移前 PRL 提交
`3dc00c77a6340c12ba8f7fff40c212c218707776` 与旧仓库最终提交
`5864a63d5b77943812ddfeb2b44442dab4f8a068`。迁入时共登记 609 个引擎文件，
未登记本地 `build*` 目录或嵌套 `.git` 元数据。

三个历史文件存在 CRLF/LF 属性不一致。原始字节树先在
`918d20c8e1090f4cbf9887994f50160da5042739` 中完整保留，随后仅对这三个文件
执行换行规范化；忽略行尾空白后无语义差异。

## 迁移后验证

- 内置 cell-engine CPU 构建通过；完整 CTest：`134/134 passed`；
- PRL C++ CPU 构建通过；材料 ABI、v09/v10 回归及 v11 事务测试：
  `17/17 passed`；
- PRL 远端可以直接读取旧仓库最终提交、迁移提交及
  `external/simucell3d/CMakeLists.txt`；
- 两个保全标签均已推送至 PRL；
- 未启动 GPU worker。

## 旧仓库处置

只有在上述 PRL 远端验证全部通过后，才按人类明确批准删除 GitHub 私有仓库
`cbcbcbcb123/prl-cell-engine`。删除后复核结果：GitHub API 无法再解析该仓库，
`git ls-remote` 返回 repository not found；PRL 分支、两个标签和迁入源码仍可读。

后续所有 cell-engine 代码、测试、版本与论文证据均在 PRL 仓库中维护。除非
另有新的人类决策，不再创建或同步独立的 `prl-cell-engine` 远端仓库。
