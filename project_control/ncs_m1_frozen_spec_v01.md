---
document_id: NCS-M1-FROZEN-SPEC-v01
status: frozen_active
frozen_at: 2026-09-10
source_plan: ncs_m1_all_fem_baseline_plan_v01.md
prerequisite_report: ncs_m0_report_v01.md
implementation_target: scripts/run_ncs_m1_all_fem_v01.py
result_target: results/ncs_m1_all_fem/v01_20260910
---

# NCS-M1 v01 冻结执行规格

本文件细化已采纳方案，不改变物理、阈值或预算。M1a 失败或未解析时停止，不创建或运行 M1b 正式包；M1b 未通过时保留 M1a 的局部结论，但整体 M1 不写全通过。

## 1. 固定实现与环境

- 单进程、1 CPU、无 GPU、正式运行无网络；内存上限 8 GiB。
- 主机 `F:\python\python.exe`，Python 3.13.7；使用已存在的 NumPy/SciPy/Matplotlib，不依赖 dolfinx、petsc4py、UFL，不安装软件。
- 二维三节点 P1 三角形、工程剪切应变、每单元常应变；材料积分和主动 profile 采用固定三点二阶三角求积。
- 平面以周期 fluctuation DOF + 宏观 `ebar` DOF 表示；`mean(wx)=0` 用精确 KKT 乘子，底面 `uy=0` 直接消元。圆环用三个精确 KKT 刚体约束。
- 稀疏矩阵按相同网格/`dt` 复用一次 SuperLU 分解；逐次 RHS 记账。缩放后 normwise backward residual 门为 `1e-10`。
- 实现及测试文件是 create-only；正式结果目录是 create-only。开发输出进入项目内 `tmp/ncs_m1_all_fem_v01_dev/`，不得充当正式证据或清理旧目录。

## 2. 固定模型、离散和读出

模型、材料、层厚、U/H 输入、圆环半径、网格 G0/G1/G2、`Nt=64/128/256`、最多 20 周期、区域、标度和所有门完全沿用 `ncs_m1_all_fem_baseline_plan_v01.md`。

空间比较使用细网格单元重心及固定物理求积点，将粗网格的 P1 位移和单元应变/应力按物理坐标定位后比较；不按节点编号比较。整体与局部标量同时保留绝对误差和固定标度归一化误差。镜像按 `x→−x` 对位移/应力作向量/张量变换；圆环旋转按 17° 坐标协变比较。

固定读出：`ebar`；顶面位移 L2 范数和基频；三层平均 `εxx`；ECM/心内膜两个固定区域的平均应变与应力；三层储能、主动功、Maxwell 耗散和残差；两个界面的弱合力、合力矩与功率。最大总应变在全部单元和全部保存时点计算。

## 3. 独立参考

- U 平面：使用 `ncs_m0_report_v01.md` 的完整复刚度 Schur 消元代数；DC 与基频分开，恢复横向量、应力、功和耗散。不得调用二维 FEM 矩阵。
- M1b 圆环：使用分层 `Ar+B/r+c r ln r` 的独立 6×6 系数系统；DC/谐波分开。以长双精度残差及独立高精度求解复核，使参考相对误差估计 `<=1e-4`（主门 `1e-3` 的 1/10）。
- 时间误差相对连续频域参考；离散功账本用 CN 中点恒等式，两者不得互相替代。

## 4. M1a 正式协议清单（最多 17）

| ID | 类型 | 固定内容 | 预计分解/RHS |
|---|---|---|---:|
| U-G0-T256、U-G1-T256、U-G2-T256 | 时域 | U，三网格，至稳态或 20 周期 | 各 1 / `256×实际周期` |
| H-G0-T256、H-G1-T256、H-G2-T256 | 时域 | H，主 `/` 取向，三网格 | 各 1 / `256×实际周期` |
| U-G2-T64、U-G2-T128 | 时域 | U 时间收敛；T256 复用 | 各 1 / `Nt×实际周期` |
| H-G2-T64、H-G2-T128 | 时域 | H 时间收敛；T256 复用 | 各 1 / `Nt×实际周期` |
| H-G1-MIRROR、H-G2-MIRROR | 时域 | `\` 取向，Nt256 | 各 1 / `256×实际周期` |
| ZERO | 静态 | 零输入、零初态 | 1 / 1 |
| PATCH | 单元 | 被动仿射常应变、精确 Dirichlet | 1 / 1 |
| ELASTIC | 频域 | U、关闭 Maxwell，G0 | 1 / 1 |
| TAU-FAST、TAU-SLOW | 频域 | U、G0、`τ/T=0.01,10` | 各 1 / 1 |

程序按阶段输出实际分解数、RHS 数、装配/分解/求解/后处理墙钟。正式 M1a 累计求解墙钟 `<=1800 s`、任一协议 `<=120 s`、单次线性求解 `<=30 s`；开发诊断最多 600 s 和两轮可定位修正。

## 5. M1a 固定门

逐字采用源方案：零输入/patch `<=1e-8`；backward residual `<=1e-10`；U G2/Nt256 参考误差 `<=1e-3`、相位 `<=0.2°`；时间阶 1.8–2.2（误差底规则不变）；H G1→G2 整体 `<=0.5%`、局部 `<=1%` 且差值比 `<=0.7`；镜像 `<=1e-8`；能量残差 `<=1e-8`、`D>=−1e-12 Wref/T`；界面弱反力/力矩/功率 `<=1e-8`；周期差 `<=1e-6`；`max|ε|<=0.05`。相位幅值下限和近零量规则不变。

任何实现/残差/功率/镜像门失败记 `failed`；空间或时间未解析且非实现错误记 `unknown` / 科学分类 `NOT_RESOLVED`；环境缺失记 `blocked`。不得自动增加 G3、改变读出或阈值。

## 6. M1b 固定协议（仅 M1a 全部门通过后，最多 7）

| ID | 类型 | 固定内容 |
|---|---|---|
| R-G0-F、R-G1-F、R-G2-F | 频域 | 三档圆环与独立径向参考 |
| R-G2-T64、R-G2-T128、R-G2-T256 | 时域 | G2 启动到稳态，时间参考 |
| R-G1-ROT17 | 频域 | 整体坐标旋转 17° |

每个频域协议预计 1 次复分解/1 RHS；每个时域协议 1 次实分解/`Nt×实际周期` RHS。M1b 累计求解墙钟 `<=900 s`，其他单协议/单求解上限不变。空间、时间、能量、假设、独立参考门沿用 M1a；旋转协变门 `<=1e-8`，多边形几何误差包含在总误差中。

## 7. 命令、哈希与落盘合同

首个正式命令固定为：

`F:\python\python.exe -X utf8 -B scripts/run_ncs_m1_all_fem_v01.py --stage m1a --output results/ncs_m1_all_fem/v01_20260910`

只有 M1a `passed` 后，第二命令为：

`F:\python\python.exe -X utf8 -B scripts/run_ncs_m1_all_fem_v01.py --stage m1b --output results/ncs_m1_all_fem/v01_20260910`

正式包记录：命令、UTC/本地时间、Python/NumPy/SciPy 版本、CPU/进程约束、Git 分支/HEAD/dirty、runner/合同/输入 SHA256、协议清单、实际分解/RHS/墙钟、逐门结果、轨迹与场数组、参考、能量/界面账本、失败分类及 `summary.json`。失败也保留，不覆盖。

M1a 全部门通过才允许 M1b。M1b 之后无论结果如何都停止；M2 未获本规格授权。
