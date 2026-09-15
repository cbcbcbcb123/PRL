---
document_id: PRL-VENTRICLE-DCM-ECM-CONFLUENT-TRILAYER-PRECHECK-EXECUTION-RECORD-V01
status: current
executed_at: 2026-09-12
stage: Z1-TF2-A
stage_scope_status: PASS_Z1_TF2A_PRECHECK
branch_decision: surface_only_supported
parent_z1_status: unresolved
contract: project_control/ventricle_dcm_ecm_confluent_trilayer_precheck_contract_v01.md
authorization: project_control/ventricle_dcm_ecm_confluent_trilayer_precheck_authorization_v01.md
accepted_result: results/ventricle_z1/z1tf2a_dcm_ecm_precheck_v02_20260912
preserved_failed_result: results/ventricle_z1/z1tf2a_dcm_ecm_precheck_v01_20260912
---

# Z1-TF2-A｜连续 DCM-ECM 三层预检执行记录 v01

## 1. 用户授权与实际范围

用户在采纳“ECM 也用 DCM 模拟”后，于 2026-09-12 明确回复“确认，执行，尽快做出这三层结构”。本轮据此执行冻结的 Z1-TF2-A 合成预检：

- `4×4` 长轴心肌 DCM；
- `1` 个有顶面、底面和侧壁的连续闭合 ECM DCM；
- `4×4` 扁平心内膜 DCM；
- 细胞 `reference_shape_modulus=0`、捕获参考边数为 0；
- 真实 node-face 黏附/排斥接触、ECM 法向/剪切原语和小幅腔压延拓；
- CPU 最多 4 线程、GPU 0、网络 0、累计单包墙钟门 600 s。

没有修改 `E:\MeshCell3D`，没有复制第二套内核，没有进入物理时间、主动周期、Z2、CFD、FSI、分裂或 ECM 周转。

## 2. 运行谱系和失败保留

### v01：`failed`，原样保留

首次正式包为 [z1tf2a_dcm_ecm_precheck_v01_20260912](../results/ventricle_z1/z1tf2a_dcm_ecm_precheck_v01_20260912/index.html)，墙钟 `129.9015799 s`。前六项均通过，但 PRESSURE-PATH 的审核器把曲面压力 z 向合力错误地与“标量曲面面积 × 压力”比较，得到最大相对差 `0.1553579983`。对倾斜三角面，正确共轭量是有向投影面积积分 `∫n_z dA`；因此 v01 判为 **failed** 并完整保留，未把失败改名为通过。

### v02：只修验证定义，重新 create-only 运行

v02 没有改变几何、材料、接触参数、压力、迭代数或任何冻结门，只做三项验证闭合：

1. z 向压力合力与有向投影面积 `∫n_z dA` 独立比较；
2. 在每个接受的延拓端点重新装配曲率、内力、接触力和压力，保证账本与快照是同一几何状态；
3. 以 `f=0` 接触预应力为基线，报告心肌接触合力的压力诱导增量，避免把预应力冒充压力传递。

正式命令为：

```powershell
$env:OMP_NUM_THREADS='4'
$env:OPENBLAS_NUM_THREADS='4'
$env:MKL_NUM_THREADS='4'
$env:NUMEXPR_NUM_THREADS='4'
python -X utf8 -B scripts\run_ventricle_dcm_ecm_precheck_v02.py
python -X utf8 -B scripts\verify_ventricle_dcm_ecm_precheck_v02.py
python -X utf8 -B scripts\render_ventricle_dcm_ecm_final_fields_v01.py
```

v02 墙钟 `139.8448696 s`，退出码 0；独立复核退出码 0。

## 3. v02 冻结结果

| 子门 | 状态 | 关键证据 |
|---|---|---|
| ECM-CLOSED | passed | 顶/侧/底三角面 `216/84/216`；开边、非流形边、重复面均 0 |
| ECM-RIGID | passed | 最大刚体相关相对误差 `3.70433e-15 < 1e-10` |
| ECM-NORMAL | passed | fine 刚度 `6.065268 N m^-1`；粗细相对差 `1.96798e-6`；最大工作误差 `2.00189e-7` |
| ECM-SHEAR | passed | fine 刚度 `0.0335575 N m^-1`；粗细相对差 `1.39934e-4`；最大工作误差 `1.03398e-6` |
| CELL-ECM-CONTACT | passed | 黏附、排斥、分离零接触路径齐全；合力相对残差 `3.22168e-17`；工作误差 `9.51278e-7` |
| TRILAYER-GEOMETRY | passed | 33 个闭合 DCM；总开边/非流形/重复/翻面均 0；最小角 `20.316068°`；中心细胞最少 5 个接触邻居 |
| PRESSURE-PATH | passed | 5 个算法延拓点；压力积分最大相对误差 `8.78897e-16`；最终心肌基线扣除传递比 `0.955279`；最小角 `20.277966°`，翻面 0 |

因此 Z1-TF2-A 在合同限定的合成原语与几何范围内为 **PASS_Z1_TF2A_PRECHECK**，材料分支裁决为 **surface_only_supported**。这允许下一步起草 Z1-TF2-B 致密三层静态成形筛查合同；不自动授权运行该筛查。

## 4. 独立验证与图片验收

- [独立验证](../results/ventricle_z1/z1tf2a_dcm_ecm_precheck_v02_20260912/verification/report.md) 不导入 runner 或 `muse_dcm`，从 NPZ/CSV/JSON 独立复算对象身份、参考态关闭、33 个网格、接触账本、ECM 响应、接触原语、压力路径、快照和 provenance，11/11 项通过。
- 八张 PNG 均以原始分辨率检查；[视觉 QA](../results/ventricle_z1/z1tf2a_dcm_ecm_precheck_v02_20260912/verification/visual_qa_report.md) 为 `passed`。
- 补充的腔面场图在真实快照网格上编码三种量：三角面颜色为曲率，网格边颜色为细胞压力，红节点大小为接触牵引 `|节点接触力|/节点分摊面积`。接触牵引是表面 stress-like 量，不是体相 Cauchy 应力张量。
- 补充场图的 CB 统一风格主轴框为 `10×5 in`，自动验证通过，画布最小净空 `39.6 pt`；人工检查中发现并修复了首版色条标题重叠，未交付该不合格渲染。

## 5. Provenance 与边界

- PRL Git HEAD：`b45650a9e370be138a70acf305b6c3a21e6a7ed2`；工作树开始前已有大量未跟踪/用户文件，本轮未清理或提交。
- MeshCell3D Git HEAD：`fa21321b80a371f107afd398f93d7f69508e20c6`；`code/muse_dcm` 的 44 条既有 dirty 状态在预登记前后逐行一致，本轮未写入该仓库。
- v02 runner SHA-256：`78915c3b4ecb5bd660040f19434f774e25fd62f3abbf1516a49a2a1f62d3d386`。
- 独立 verifier SHA-256：`e5504d36d28f8fae5365aa59cdc1339d28019f25d7b59574937f34fd19945b2f`。
- 补充场图 renderer SHA-256：`255581bbf9ab879bf036fdf209967235ca257ec16dce5555593771278800c8ed`。
- 最终结果入口：[results/ventricle_z1/z1tf2a_dcm_ecm_precheck_v02_20260912/index.html](../results/ventricle_z1/z1tf2a_dcm_ecm_precheck_v02_20260912/index.html)。

## 6. 科学解释限制

- 本 PASS 只说明当前合成 surface-only ECM 壳在规定小探针中具有稳定非零法向与切向响应，并能通过当前接触原语传递小幅压力增量。
- 它不证明 ECM 参数生理正确，不代表胶原纤维尺度材料验证，也不证明长期形态稳定。
- 当前长轴/扁平细胞是受限铺砌初值；尚未证明它们在无参考态膜能下能由细胞骨架、拥挤、ECM、压力和夹持共同形成并维持。
- 父 Z1 仍为 **UNRESOLVED**；主动周期、物理时间、实验标定和 Z2–Z11 仍为 **NOT_RUN**。
