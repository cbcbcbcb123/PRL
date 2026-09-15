---
document_id: NCS-M1A-EXECUTION-RECORD-v01
status: passed
completed_at: 2026-09-10T17:31:32+08:00
result: results/ncs_m1_all_fem/v02_20260910/m1a/summary.json
supersedes_for_stage_decision: ncs_m1a_v01_ledger_failure_record_v01.md
next_stage: M1b
---

# NCS-M1a 平面三层全 FEM 正式执行记录

## 判定

create-only v02 复验包的 17 个冻结协议全部通过，M1a 状态 **passed**，科学分类为该平面合成基准范围内的 **PASS**。因此满足 M1a→M1b 门禁。该结论不证明 DCM 优势、事件一致转移、生物有效性、方法新意或投稿水平。

v01 包因协议计数遗漏已由 `ncs_m1a_v01_ledger_failure_record_v01.md` 否决并原样保留；v02 修正只涉及 ZERO/PATCH 账本计数，没有改变物理、网格、阈值或数值算法。

## 正式命令与身份

`F:\python\python.exe -X utf8 -B scripts/run_ncs_m1_all_fem_v01.py --stage m1a --output results/ncs_m1_all_fem/v02_20260910`

- 分支/HEAD：`codex/simucell3d-hybrid-feasibility` / `b45650a9e370be138a70acf305b6c3a21e6a7ed2`；运行时工作树 dirty。
- `summary.json` SHA256：`94e08dad43667ae73e0bdcf52ed08d37f395dcb14f93eb8d0ab80ccc4f520c5d`。
- runner SHA256：`12efd84f116099e3cacbfcb5753990567bb5f3da640913adc90a9fc070ef9306`。
- 核心模块 SHA256：`0c189603dd5f6c3481d3c7139fe750686be6b171735da1d729182014c5804553`。
- 冻结规格 SHA256：`66238b849cc1042fcf8198a494c1e7ed422c78940930b0bed1714687c5309144`。
- Python 3.13.7、NumPy/SciPy、单进程 CPU、0 GPU；正式运行无网络。

## 账本与门禁

| 项目 | 实际值 | 门/判定 |
|---|---:|---|
| 协议 | 17 | 清单完整，PASS |
| 分解 / RHS | 16 / 17028 | ZERO 为 1/1；完全规定的 PATCH 为 0/0，差异已明示 |
| 协议累计 / 端到端墙钟 | 61.7033774000 s / 65.8194466000 s | `<=1800 s`，PASS |
| 最大单协议墙钟 | 10.7759 s | `<=120 s`，PASS |
| 最大 backward residual | `9.1373e-16` | `<=1e-10`，PASS |
| U 独立参考最大误差 / 相位 | `2.8124e-6` / `1.1311e-4 deg` | `<=1e-3` / `<=0.2 deg`，PASS |
| 最大离散能量残差 | `7.9531e-16` | `<=1e-8`，PASS |
| 最大界面归一化失配 | `1.3323e-14` | `<=1e-8`，PASS |
| 最大周期差 | `6.7729e-10` | `<=1e-6`，PASS |
| 最大绝对应变 | `0.00714987` | `<=0.05`，PASS |

U/H 时间门、H 空间解析门、G1/G2 镜像门、零输入、仿射 patch、弹性极限及快/慢松弛门均通过；逐读出、阶数、绝对误差和轨迹数组以正式摘要及各协议 NPZ/JSON 为准。

## 下一步与停止边界

下一唯一切片为冻结的 M1b 二维圆环七协议。只有圆环独立参考、空间/时间、旋转、能量和假设门全部通过，才可把整体 M1 记为 PASS。无论 M1b 结果如何，本授权不进入 M2。

