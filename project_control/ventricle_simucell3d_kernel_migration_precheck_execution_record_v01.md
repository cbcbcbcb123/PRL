---
document_id: PRL-VENTRICLE-SIMUCELL3D-KERNEL-MIGRATION-PRECHECK-EXECUTION-RECORD-V01
status: completed
completed_at: 2026-09-12
stage: Z1-TF2-M0
outcome: passed
decision: PASS_SIMUCELL3D_M0
contract: project_control/ventricle_simucell3d_kernel_migration_precheck_contract_v01.md
result: results/ventricle_z1/z1tf2m0_simucell3d_migration_v01_20260912/summary.json
next_stage: Z1-TF2-B_not_run_not_authorized
---

# Z1-TF2-M0｜SimuCell3D 换核资格门执行记录 v01

## 结论

受控 `external/simucell3d/` 核心与 PRL 最小心室适配层通过本合同的七个冻结子门，裁决为 **PASS_SIMUCELL3D_M0**。这允许下一步单独起草和裁决 SimuCell3D 版 Z1-TF2-B 合同；不自动授权运行该阶段。

## 实际模型与工况

- 真实对象为 16 个长轴心肌细胞、1 个连续闭合且可变形的 ECM 对象、16 个扁平心内膜细胞，共 33 个闭合三角曲面对象；
- 组织片两端仅夹持预登记边界顶点；ECM 其余顶点可变形；
- 心肌施加经投影校正的方向性胞内载荷，使每个细胞净力与质心净矩为零；
- 心内膜腔面施加有向压力载荷；
- 接触使用实际 SimuCell3D 面—面接触装配，没有跨空隙独立弹簧；
- 保存 `λ=0,0.25,0.5,0.75,1` 五个算法延拓状态，拓扑固定；
- 心肌和心内膜未使用逐边参考形状膜能。面积—体积稳态标量从初始生成几何初始化，不等同于指定非球形参考网格。

## 内核适配与可移植性修订

为在当前 Windows/MSVC 环境中建立同一受控核心，完成了可测试的最小修订：

- 将编译期三角函数改为数值常量，避免当前 C++17/MSVC 的 `constexpr` 限制；
- 在初始三角剖分中使用局部 π 常量；
- 为 MSVC 提供不支持 OpenMP 自定义 reduction 时的串行回退；
- 将 ball-pivoting 随机重排改为确定性的 C++17 shuffle；
- 为含 OpenMP lock 的 node 补齐 RAII 安全的构造、复制、移动、赋值与析构；
- Windows/MSVC 采用静态库和短构建路径，避免嵌套测试的 FileTracker 路径长度失败。

完整受控 fork 的 Release CTest 为 `134/134 passed`。PRL 只直接链接 `external/simucell3d/`；没有复制第二套核心。

## 冻结门结果

| 子门 | 结果 | 独立复核关键量 |
|---|---|---|
| `M0-SOURCE` | passed | Release 构建退出 0；CTest 134/134；13 个受控源码哈希已记录 |
| `M0-ROLE-MOBILITY` | passed | 固定点最大位移 `0`；ECM 自由点最大位移 `1.1141055567650548e-3` |
| `M0-LOAD` | passed | 压力积分最大相对残差 `3.102973767139601e-16`；主动净力/净矩最大相对残差 `3.593619597354046e-16 / 3.5605703769630883e-16` |
| `M0-CONTACT` | passed | 探针两侧力范数 `0.5591758511135496 / 0.5591758511135497`；作用—反作用相对残差 `1.1059422953209105e-16` |
| `M0-STEP` | passed | 132 个接受体步；工作—耗散最大相对残差 `6.38281573517357e-15`；几何量有限且为正 |
| `M0-TRILAYER` | passed | 33 个闭合对象；同层接触 240、细胞—ECM 接触 160、心肌—心内膜直接接触 0 |
| `M0-OUTPUT` | passed | 每状态 1470 点；五张真实结果 PNG/SVG；Notebook 数据副本与原始文件哈希一致 |

所有冻结阈值保持不变。当前最小初始面面积为 `0.7729694546480044`；所有持久 ID、节点数、面数及边二重性通过独立检查。

## 执行与复核账本

- 正式求解仅执行 `1/1` 次，CPU/4 线程，退出码 0，内核墙钟 `0.7550345 s`；
- 独立复核器只读取冻结 artifact，不导入或调用 SimuCell3D；
- 复核器尝试 1 因 NumPy 布尔值 JSON 序列化错误在写状态前退出；
- 尝试 2 因交叉报告一致性容差错误而误报 `M0-OUTPUT failed`，失败 JSON 与报告原样保留；
- 修复只给 runner/独立复核的机器累积差设置 `1e-15` 容差，科学压力门仍为 `1e-12`。新增回归测试后 6/6 通过，尝试 3 七门全部 passed；
- 结果包收口时一次复核命令误用了不存在的 `--result-root` 选项，参数解析阶段退出且未读取 artifact；改用位置参数后的最终复核再次七门全部 passed；
- 五张图均由冻结真实数据生成；已执行 Notebook、自动验证和最终人工视觉 QA 均 passed。

## 解释边界与后续状态

本 PASS 仅覆盖内核来源/构建、对象角色与运动学分离、载荷守恒、实际接触、一步耗散、固定拓扑和真实输出链。它不证明：

- 长期静态或动态组织成形；
- 长轴心肌和扁平心内膜已由环境自发形成或稳定维持；
- 生理参数、周期主动收缩或物理时间；
- 父 Z1 已解决；
- Z1-TF2-B 或 Z2 已运行。

`λ` 仅为算法延拓坐标。图中界面牵引是面积归一的接触节点力，不是三维 Cauchy 应力。

下一步状态为 **Z1-TF2-B NOT_RUN / 未授权**，需建立新的 SimuCell3D 静态成形与消融合同并由用户另行批准。MeshCell3D 历史结果、失败包和全部冻结证据继续保留，且不向 SimuCell3D 自动继承科学 PASS。

## 权限与工作区边界

本轮未使用 GPU、Docker、网络或后台 worker，未提交、推送或发布，也未删除既有文件。工作树在本任务前已有大量无关修改与未跟踪内容；本记录只以 `provenance.json` 列明的路径和哈希作为本轮证据。开发构建与烟雾测试目录仍保留，清理需另行列出精确绝对路径并取得用户确认。

## 入口

- 离线结果页：`results/ventricle_z1/z1tf2m0_simucell3d_migration_v01_20260912/index.html`
- 机器摘要：`results/ventricle_z1/z1tf2m0_simucell3d_migration_v01_20260912/summary.json`
- 独立复核：`results/ventricle_z1/z1tf2m0_simucell3d_migration_v01_20260912/verification/independent_verification.json`
- 可视化 QA：`results/ventricle_z1/z1tf2m0_simucell3d_migration_v01_20260912/verification/visual_qa.json`
- 来源与命令：`results/ventricle_z1/z1tf2m0_simucell3d_migration_v01_20260912/provenance.json`、`commands.md`
