---
document_id: PRL-3D-BEFORE-GROWTH-V01
status: adopted
date: 2026-09-18
authority: user agreed to the proposed 3D-first sequence and said 同意，继续
---

# 先三维固体，再生长与流固耦合

本决定补充而不改写 `ventricle_development_fsg_idealized_public_data_decision_v01.md`。
停止扩展二维参数扫描。下一实际切片为F6-S2理想化三维心室固体资格；
二维只在需要时保留为生长公式的小型验证工具，不另建二维发育主线。

路线：三维被动/主动固体 → 小型生长公式验证及规定式三维基线生长 →
可靠双向FSI → 周期平均力学驱动生长 → ECM反馈。
这些是路线而不是对后续全部计算的授权。三维固体与规定式生长可以先于完整FSI，
但没有血流求解就不能声称流动驱动生长或发育–血流反馈。

后续生长用F=Fe Fg区分可逆弹性与不可逆生长，近不可压约束针对Je，
不将总J=1错误用于禁止组织生长。生长率、材料成熟及反馈律仍未标定。
公开morphoHeart形态只作版本化形态约束，不代替同一个体的动力学数据。

当前仅执行 `ventricle_fem_idealized_3d_contract_v01.md` 的有界切片。
本轮无DCM、FSI、生长、安装、拉取、GPU、删除或远端推送。
