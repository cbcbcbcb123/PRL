---
document_id: PRL-Z1-MYO-STRIP-LOAD-BC-A-EXECUTION-V01
status: current
completed_at: 2026-09-14T10:07:19+08:00
numerical_status: failed
qualified_status: failed_numerical_safety_stop
visual_status: passed
biological_validation_status: blocked_data
parent_z1_status: blocked
---

# 五细胞心肌条带端部负载判别执行记录 v01

## 1. 裁决

`Z1-MYO-STRIP-LOAD-BC-A` 的一次性正式 CPU 矩阵已执行，最终状态为 **`failed / failed_numerical_safety_stop`**，不得解释为通过。

- 计划的 6 条轨迹中 5 条完成；
- `SYNC_FREE_LOW_LOAD` 在算法相位 `phi=0.375`、激活量 `0.853553` 时，最小三角角降到 `7.997446 deg`，触发冻结的 `8 deg` 安全停机；
- 失败点最大相对体积误差为 `0.728601%`，最大自由节点力为 `0.0197837`；
- 原 v01 验证器因失败轨迹没有终态 `kernel_metrics.json` 返回 `blocked`，这是验证器对中途安全停机的分类缺口。原始执行日志与最后有效状态已证明本次是数值失败，而不是外部依赖阻断；
- 正式授权已消费，没有自动重跑、没有修改阈值、没有删除或覆盖失败证据，GPU 使用量为 0。

## 2. 冻结模型与工况

模型仍是 5 个长轴心肌 DCM 沿长轴串联的单细胞厚条带，4 个界面各有 7 条固定材料链接。每个主动细胞保留 7 条胞内长轴收缩单元，20% 主动参考缩短只是高信号合成探针。`CENTER` 仅激活中央细胞，`SYNC` 激活全部 5 个细胞。

本阶段只比较三种端部边界：

| 边界 | 定义 |
|---|---|
| `ISOMETRIC` | 两端帽三轴固定 |
| `COMPLIANT` | 两端横向固定，轴向连接 `k_support=0.05` 线性支撑 |
| `FREE_LOW_LOAD` | 左端帽三轴固定，右端帽仅横向固定且轴向自由 |

材料、主动机制、固定链接、阻尼、网格、体积项、面积项与冻结数值门均未改变。`phi` 是算法激活/松弛坐标，不是生理时间；全部力学量仍为未标定模型单位。

## 3. 已完成轨迹的直接结果

| 工况 | 峰值整体缩短 | 峰值轴向端载增量 | 最小三角角 | 最大体积误差 |
|---|---:|---:|---:|---:|
| `CENTER_ISOMETRIC` | 0.000% | 0.329012 | 33.548 deg | 0.748057% |
| `CENTER_COMPLIANT` | 1.561% | 0.127868 | 27.503 deg | 0.748329% |
| `CENTER_FREE_LOW_LOAD` | 1.532% | 0.119522 | 16.760 deg | 0.748273% |
| `SYNC_ISOMETRIC` | 0.000% | 1.746849 | 46.274 deg | 0.741631% |
| `SYNC_COMPLIANT` | 8.536% | 0.662799 | 8.581 deg | 0.747808% |
| `SYNC_FREE_LOW_LOAD` | 未完成 | 未裁决 | **7.997 deg 安全停机** | 0.728601%（停机点） |

已完成轨迹显示，释放端部轴向约束会显著增加整体缩短并降低端载：例如 `SYNC` 从等长的 0% 缩短、1.746849 端载，变为柔性支撑下 8.536% 缩短、0.662799 端载。这支持“此前整体形变较小主要受刚性边界影响”的方向性解释。

但完整判别门没有通过。`CENTER_FREE_LOW_LOAD` 的缩短 1.532% 略低于 `CENTER_COMPLIANT` 的 1.561%，违反预登记的严格排序；当前 `FREE_LOW_LOAD` 用左端整帽全固定消除刚体平移，因此并不是平移中性的纯零载边界。与此同时，20% 同步近自由收缩使固定拓扑曲面产生严重剪切；`SYNC_COMPLIANT` 的 8.581 deg 也已非常接近 8 deg 安全门。

### 完成不等于数值合格

从原始 `state_metrics.csv` 重算，`CENTER_COMPLIANT`、`CENTER_FREE_LOW_LOAD`、`SYNC_COMPLIANT` 的最大保存自由节点力分别为 `0.001405946 / 0.003414898 / 0.003504355`，均超过冻结 `1e-3` 门。`SYNC_COMPLIANT` 最小保存角为 `8.584776 deg`，也低于 15 deg 验收门（其全程最小角 8.581190 deg 尚未触发 8 deg 安全停机）。因此上表三个卸载工况的响应仅为未充分收敛的诊断读数；严格排序的物理含义尚不能裁决，也不能仅凭这些值确定零载边界是失败的唯一原因。

## 4. 失败现象、待验证原因与不能声称的内容

本次结果暴露数值质量失败，同时提出两项待验证的原因：

1. **边界定义问题**：一端整帽全固定会引入不对称约束和非零平均外载，不能作为干净的零载比较器；
2. **网格/拓扑适用范围问题**：稀疏固定链接条带在 20% 同步近自由收缩下出现曲面剪切退化，当前动态重网格又因材料链接身份约束而关闭。

因此本阶段不能标定细胞被动柔软度，不能宣称 `FREE > COMPLIANT > ISOMETRIC` 全矩阵成立，也不能据此把五细胞稀疏链接条带外推为连续二维心肌层。不得通过降低 8 deg 安全门、只忽略失败工况或覆盖原包来改判。

## 5. 图像与证据验收

create-only 失败诊断包已生成并人工目视通过：

- 三种边界模型结构图；
- 失败轨迹最后 3 个有效求解器状态 GIF；
- 最小角、体积误差与自由节点力的失败过程图；
- 已完成工况的缩短—端载比较图；
- 失败前最后有效状态的曲率、压力、胞内收缩牵引与界面牵引网格图；
- 4 组 PNG/SVG 成对文件、1 个 3 帧 GIF 和 9 个离线链接均通过检查。

这些图是实际求解器状态与结果，不是概念图。失败轨迹只保存到 `phi=0.25` 的最后有效输出；不得补画不存在的后续状态。

## 6. 下一步裁决建议

不建议继续修补这个即将被替代的五细胞稀疏链接条带，也不建议重跑 20% 近自由工况。当前部分结果已经足以证明端部约束强烈影响表观形变，而失败又说明该条带的固定链接和非对称近自由边界不适合承担二维组织验证。

建议下一步单独冻结 **`2D-M0`：4×4 单层长轴心肌细胞的被动致密接触预检**：

- 16 个细胞在二维平面内致密排列，初始间距进入生产 node-face 接触捕获区；
- 先只验证几何、真实接触、邻接图、体积、网格质量和接触场，不施加主动收缩；
- 不使用五细胞条带的稀疏材料链接冒充连续组织；
- 不包含 ECM、心内膜、生理时间或 GPU；
- 被动预检通过后，再另行冻结较低幅度的二维主动边界比较。

该建议不在本次已消费授权内；`2D-M0` 尚未运行。生物学验证保持 `blocked_data`，父 Z1 保持 `blocked`。

具体后续方案见 [4×4 心肌层 2D-M0 实施方案](ventricle_myocardial_sheet_2d_m0_design_v01.md)，状态为 proposed，尚未启动新组织求解。

## 7. 权威证据

- 冻结合同：`project_control/ventricle_myocardial_strip_load_boundary_contract_v01.md`
- 授权记录：`project_control/ventricle_myocardial_strip_load_boundary_authorization_v01.md`
- 原始执行账本：`results/ventricle_z1/z1_myo_strip_load_boundary_v01_20260914/execution_ledger.json`
- 原始失败目录：`results/ventricle_z1/z1_myo_strip_load_boundary_v01_20260914/`
- create-only 失败裁决：`results/ventricle_z1/z1_myo_strip_load_boundary_failure_diagnostic_v02_20260914/verdict.json`
- 图文入口：`results/ventricle_z1/z1_myo_strip_load_boundary_failure_diagnostic_v02_20260914/index.html`
- 视觉验收：`results/ventricle_z1/z1_myo_strip_load_boundary_failure_diagnostic_v02_20260914/visual_qa.json`
- 链接验收：`results/ventricle_z1/z1_myo_strip_load_boundary_failure_diagnostic_v02_20260914/link_validation.json`
