---
record_id: PRL-FEM-EXPERT-REVIEW-EXPORT-V01
date: 2026-09-18
status: passed
scientific_status_changed: false
new_solver_runs: 0
---

# 当前FEM核心代码与进展：桌面专家评审交付

用户本轮授权：“现在把目前的核心代码及进展打包到桌面，我找专家评审”。
本授权覆盖以下新建桌面交付物；不是删除、联网发送、科研运行或改写原始证据的授权。

## 交付物

- 目录：`C:\Users\chenb\Desktop\PRL_FEM_Expert_Review_20260918_v01`
- 压缩包：`C:\Users\chenb\Desktop\PRL_FEM_Expert_Review_20260918_v01.zip`
- 浏览入口：目录内 `00_评审入口.html`，本地离线HTML，无CDN或服务依赖。
- 目录404文件，247,431,103 bytes；ZIP 123,117,396 bytes（约117.4 MiB）。
- ZIP SHA-256：`d4874e773bfebc8ac2604249430431b943bee5ca68789bfe9503009296eed3ea`。
- 包内MANIFEST SHA-256：`d6cc69a85d4b753aa59525d9746d8aa23dbdea9bc25e6324964a2513e1412322`。
- 代码快照：`main / 1913bfbc5d8a3b0a2e86d650805804adcb78c1d3`；最近科学提交 `69d2d47`。

这些是正式交付物而非临时目录；本轮没有建立可清理临时副本，没有执行删除。

## 精选范围

1. 中文模型/材料/边界/载荷、进展、证据边界、专家问题和代码导读。
2. 当前FEM及独立验证器的静态本地依赖闭包，共30个模块（含3个导出入口适配）。
3. 17份原始路线决定、模型合同、执行记录和FEniCSx后端ADR。
4. F6-S1-S9、F6-S2-D1、D2A、D2B四个阶段的配置、报告和精选原始证据。
5. 五套完整图版本：二维主动总览、五载荷态、三维粗细网格、网格质量诊断、非结构化候选。
   每套保留源数据、methods、Notebook、辅助代码、PNG和SVG；不重绘、不改写原QA。
6. 三维粗细网格的原始状态、M1迭代、失败记录与候选MSH。重复数组核对SHA后只保存一份，
   SELECTION明确指向包内相同字节，不能把原阶段子集称作原完整包。

不含全部二维全场历史、完整Git、求解器二进制、Docker镜像、旧DCM内核或公开影像大数据。
SOURCE_MANIFEST保留原阶段完整清单，SELECTION逐项说明保留和省略；原项目未删除任何文件。

## 导出中发现的代码组织边界

`prl.fem`、`prl.runs`、`prl.verification`原包入口存在历史功能的自动导入，
其中runs/verification会将旧DCM路线带入依赖闭包。因此仅在评审副本中将这三个__init__.py
改为有明确说明的轻量命名空间；原入口原样另存于`PRL/packaging_originals/src/prl`。

所有科学实现模块字节不变，主项目的三个入口也未修改。本处理是评审打包适配，
不是生产仓库架构修复。包内PROVENANCE和DEPENDENCIES均明确记载，且不声称支持完整CLI。

## 实际验收

- 四个冻结原结果manifest及其全部列出文件先验核对通过。
- 392个复制来源逐项与导出文件SHA一致，并完成复制后的来源复核。
- 包内403项文件哈希（不含manifest自身）、30个核心Python语法和81个HTML入口链接通过。
- ZIP CRC、文件集合以及全部ZIP成员逐项SHA与交付目录一致。
- 在导出目录以隔离Python运行只读复核，无需原项目PYTHONPATH；不运行生产入口。
- 从原始u/p重新计算M0/M1：仅`local_volume`失败，max|J-1|分别
  0.015227429672391546与0.014495602988764067，与原证据一致。
- 从保存MSH重新解析候选：同边界检查通过，2611四面体；q05=0.24885680850759945，
  仍仅失败`global_q05_improves_5percent`。候选FEM继续`not_run`。
- 上述“复核passed”只表示原失败被准确复现；三维资格仍`failed`，生长/FSI未执行。
- 未执行Notebook，因此不声称本次动态重绘复现。未启动Docker、Gmsh或FEM；0 GPU。

项目科学状态未变化，原驾驶舱裁决和唯一下一步不改写。等待用户带回专家意见后另行登记采纳，
本轮不在`plan/`中伪造专家指导。不安装、不创建服务、不推送、不上传或代发专家。

## 复核命令与项目记录

在解压后的评审根目录运行（标准库完整性检查）：

```
python -B -X utf8 review_check.py
```

已有numpy/scipy/meshio时可只读重算保存证据；本地另外使用`-I`隔离环境检查：

```
python -I -B -X utf8 review_check.py --numerics
```

机器可读交付记录：
[export_receipt.json](evidence/expert_review_export_v01/export_receipt.json)。
打包脚本与三份源文稿保留于同目录；脚本默认只读计划，`--build`仅允许create-only导出，
并冻结原代码HEAD与四份manifest，不允许覆盖已有评审包。
