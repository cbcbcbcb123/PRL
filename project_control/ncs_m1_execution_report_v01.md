---
document_id: NCS-M1-EXECUTION-REPORT-v01
status: passed
completed_at: 2026-09-10
scope: two_dimensional_plane_strain_three_layer_all_fem_synthetic_baselines
next_stage: M2_not_run_not_authorized
---

# NCS-M1 三层全 FEM 基线执行总报告

## 阶段判定

NCS-M0、M1a 与 M1b 已按顺序完成。M1a create-only v02 的平面三层基准与 M1b create-only v03 的三层圆环基准均通过冻结门，因此 **M1 在冻结的二维、小应变、三层 all-FEM 合成基准范围内为 PASS**。

该判定不证明 DCM 相对优势、事件一致转移、生物有效性、方法新意或 Nature Computational Science 投稿水平；这些状态仍为 **UNKNOWN** 或 **NOT_RUN**。本轮授权在 M1b 后耗尽，M2 未获授权且未运行。

## 阶段证据

| 阶段 | 状态 | 权威证据 | 边界 |
|---|---|---|---|
| M0 方法定位与规格 | passed | `project_control/ncs_m0_report_v01.md`；`project_control/ncs_m1_frozen_spec_v01.md` | 规格闭合，不是方法新意通过 |
| M1a 平面三层 | passed | `results/ncs_m1_all_fem/v02_20260910/m1a/summary.json`；`project_control/ncs_m1a_execution_record_v01.md` | 仅二维平面合成基准 |
| M1b 三层圆环 | passed | `results/ncs_m1_all_fem/v03_20260910/m1b/summary.json` | 仅二维圆环合成基准 |
| M2 固定细胞层 | not_run | 无执行合同、无结果 | 本轮明确停止于 M2 前 |

## 正式命令、环境与身份

M1a 正式通过包：

`F:\python\python.exe -X utf8 -B scripts/run_ncs_m1_all_fem_v01.py --stage m1a --output results/ncs_m1_all_fem/v02_20260910`

M1b 正式通过包：

`F:\python\python.exe -X utf8 -B scripts/run_ncs_m1_all_fem_v01.py --stage m1b --output results/ncs_m1_all_fem/v03_20260910 --m1a-summary results/ncs_m1_all_fem/v02_20260910/m1a/summary.json`

- 分支/HEAD：`codex/simucell3d-hybrid-feasibility` / `b45650a9e370be138a70acf305b6c3a21e6a7ed2`；正式运行时工作树 dirty。
- Python 3.13.7，NumPy 2.2.6，SciPy 1.16.2；单 CPU 线程，0 GPU；正式运行无网络。
- M1b v03 `summary.json` SHA256：`a55e34e4c5f60b54efaea75454f1a5795032e0a836454784147a68f8cc87fd55`。
- M1b v03 `manifest.json` SHA256：`25bf51796e1ad4440fe4249d46ede07ef768e065602395c729c186f9cd7d6f47`。
- M1a v02 `summary.json` SHA256：`94e08dad43667ae73e0bdcf52ed08d37f395dcb14f93eb8d0ab80ccc4f520c5d`。
- M1b 正式运行时 runner SHA256：`df2319d8276062ddf74113ee216f280f98b977a1a02637a903164fbf90e03dfc`；核心模块 SHA256：`550b3b17428415c7193b9166d188577ec8eacc99682987f33569cdf5f471c94c`。
- 冻结规格 SHA256：`66238b849cc1042fcf8198a494c1e7ed422c78940930b0bed1714687c5309144`；M0 报告 SHA256：`b465575e1d6eb3290a4b5602c5b533d8e8f3098834e4aab43923cfed3aada995`。

M1a 的运行时 runner/核心模块历史哈希以 `project_control/ncs_m1a_execution_record_v01.md` 为准；圆环实现随后加入，使当前文件哈希与 M1a 时点不同，未改写 M1a 结果包。

## M1a 通过摘要

M1a v02 共 17 个冻结协议、16 次分解、17028 个 RHS；协议累计墙钟 61.7033774 s，端到端 65.8194466 s。最大 backward residual `9.1373e-16`，独立参考最大误差 `2.8124e-6`、相位误差 `1.1311e-4 deg`，最大能量残差 `7.9531e-16`，最大界面失配 `1.3323e-14`，最大周期差 `6.7729e-10`，最大绝对应变 `0.00714987`。空间、时间、镜像、零输入、仿射 patch、松弛、界面、收支与预算门均通过。

## M1b 通过摘要

M1b v03 的七个协议为 `R-G0-F`、`R-G1-F`、`R-G2-F`、`R-G2-T64`、`R-G2-T128`、`R-G2-T256`、`R-G1-ROT17`。共 7 次分解、3588 个 RHS；协议累计墙钟 52.8868996 s，端到端 56.1129092 s。

| 门 | 关键实测值 | 判定 |
|---|---:|---|
| 线性代数 | 最大 backward residual `6.9266e-16`；最大约束残差 `9.5913e-18` | passed |
| 独立频域参考 | 最大误差 `1.5864e-4`；相位 `7.4744e-4 deg` | passed |
| 独立时域参考 | 最大误差 `1.6061e-4`；相位 `8.9262e-4 deg` | passed |
| 时间收敛 | 误差 `3.3689e-7 → 8.4200e-8 → 2.1049e-8`；阶 `2.00039, 2.00010` | passed |
| 空间收敛 | 七个读出 `G1→G2 / G0→G1` 比值 `0.2536–0.2574` | passed |
| 旋转协变 | 最大误差 `1.0261e-13` | passed |
| 物理收支 | 最大相对残差 `4.2691e-17`；最小耗散 `2.1961e-10` | passed |
| 界面 | 最大归一化失配 `2.1924e-13` | passed |
| 稳态与小应变 | 最大周期差 `5.4667e-11`；最大绝对应变 `0.0115883` | passed |
| 预算 | 7 协议、7 分解、3588 RHS；最大单协议 29.2910 s | passed |

解析圆环参考自检线性残差 `2.1691e-18`、积分自检误差 `1.3022e-16`，通过。逐协议数组与完整读出保存在 v03 M1b 目录，以上摘要不替代原始 JSON/NPZ。

## 保留的失败现场

1. `results/ncs_m1_all_fem/v01_20260910/m1a`：数值门虽返回通过，但摘要漏计 ZERO/PATCH，协议总数错误；阶段 PASS 被否决。失败记录为 `project_control/ncs_m1a_v01_ledger_failure_record_v01.md`，原摘要 SHA256 为 `2cfeab28d3a1c3073ed5fef7512c23a066ba7c6d84e62d65f61bf9f347c1b9ab`。
2. `results/ncs_m1_all_fem/v02_20260910/m1b`：时间门混合了固定空间误差，返回 NOT_RESOLVED；其余门通过，但不得据此放行。失败记录为 `project_control/ncs_m1b_v02_time_gate_failure_record_v01.md`，原摘要 SHA256 为 `cbfe796ab9ec8a0b302fc8754b900fe2066d4585e44b1afeb94c2b423c6cb89d`。

两次修正均限定为可定位的门实现/账本错误，采用 create-only 新版本，未更改科学问题、冻结阈值、物理、网格或算力上限；失败目录未覆盖、未删除。

## 诊断图与验收

诊断展示包位于 `results/ncs_m1_all_fem/v03_20260910/Figures/NCS_M1_diagnostics_v01_20260910/`，含平面响应、空间收敛、圆环能量账本和模型/变形示意四图的 600 dpi PNG、SVG 与样式清单。四份样式清单均通过验证，最新版已目视检查；`figure_manifest.json` SHA256 为 `64a823e61a24eddc359a1263e5d56fe80157feec08ded42a499b6581d045e068`。

这些图的角色是 `diagnostic_display_not_publication_figure`，不构成独立科学验证或投稿成图。

## 收口与下一门

本阶段在 M1b PASS 后停止。M2、DCM 替换、细胞事件、ECM 更新、FSI、三维、生物留出和方法优势均为 **NOT_RUN**；方法新意、生物有效性与投稿准备度为 **UNKNOWN**。若继续，须先形成并批准 M2 的独立执行合同，不从本轮授权、预算或失败修正额度自动继承。
