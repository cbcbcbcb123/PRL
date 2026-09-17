---
adr_id: ADR-PRL-0002
title: FEniCSx 作为 FEM-only 主线的生产求解后端
status: accepted
accepted_at: 2026-09-17
decision_owner: project user
applies_from: F6-S0
---

# ADR-PRL-0002：FEniCSx 生产后端

## 决定

从 F6-S0 起，新的心室连续体计算采用开源 FEniCSx 作为生产 FEM 后端。当前项目内
`mixed_hex.py` 等自编单元继续保留，用于解释和复核 F3--F5 历史证据，但不再扩展为真实轮廓、
主动心肌、生长或 ECM 反馈的生产求解器。

生产基线冻结为本机已有镜像候选 `dolfinx/dolfinx:v0.11.0`。每次使用前必须实查镜像 ID、
DOLFINx/PETSc/Basix/UFL 版本和容器约束；历史 image ID 不能替代当前核验。不得联网拉取、
安装或静默升级。FEBio 只作为后续简单工况的独立跨求解器对照，F6-S0 不运行。

## 原因

- FEniCSx/UFL 能把近不可压有限变形、随动腔压、纤维主动应力、主动应变、生长和 ECM
  反馈写成明确变分形式，并自动生成一致 Jacobian。
- PETSc/SNES 提供比项目内小型 Newton--SciPy 内核更成熟的非线性与线性求解路径。
- Python 配置、保存状态和独立验证可继续遵守现有 `run / verify / render / storage` 证据边界。
- 当前 F5 的局部 `J` 失败说明不能继续把自编 Q2/Q1 六面体实现直接扩展到主动真实轮廓。

FEniCSx 官方 0.11 文档和超弹性示例分别位于
<https://docs.fenicsproject.org/dolfinx/v0.11.0.post0/python/> 与
<https://docs.fenicsproject.org/dolfinx/v0.11.0.post0/cpp/demos/demo_hyperelasticity.html>。

## 软件边界

新的 runner 不得直接散布 Docker、UFL、PETSc 和结果 schema 细节。F6 实现应形成一个真实的
后端 seam：项目层只提交冻结的几何、区域、材料、载荷、边界和输出要求；FEniCSx adapter
负责函数空间、变分形式、SNES 和原始场导出。独立验证器不得导入生产 UFL 形式作力学裁决。

历史自编求解器不作为第二个活跃生产后端，也不要求 FEniCSx 重现 F5 的失败场。最先使用解析
圆环和制造检查建立新后端自身资格，然后才接回图像轮廓。

## 主动力学口径

心肌收缩实现为仅作用于心肌体积的纤维方向主动应力，不是边界节点力或规定缩短。腔压是内壁
边界载荷；被动材料、主动应力和腔压分别记账。初始 F6 使用无量纲准静态激活，只验证力学实现；
没有实验标定前不得称为生理收缩或心动周期。

## 后果与风险

- 收益：公式透明、单元和压力空间可替换、非线性求解与并行路径成熟，并为后续生长/ECM反馈
  保留直接扩展面。
- 成本：Windows 依赖受控 Linux 容器；FFCx JIT、PETSc 参数和网格标签必须纳入运行时证据。
- 风险：更换求解器不能自动修复 F5；若圆环被动门或局部 `J` 门失败，主动阶段必须停止。
- 本决定不修改、覆盖或删除 F3--F5 结果，也不恢复任何 DCM 前向路线。

本 ADR 在当前 FEM-only 主线内优先于 `ADR-PRL-0001` 的旧内核方向；旧 ADR 仍用于解释其
原适用阶段，不改写历史。
