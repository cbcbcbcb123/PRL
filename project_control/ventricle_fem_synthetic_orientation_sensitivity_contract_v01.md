---
document_id: PRL-FEM-F1S-SYNTHETIC-ORIENTATION-SENSITIVITY-CONTRACT-V01
status: adopted
authorized_at: 2026-09-16
authorization: user agreed to start the uniform-versus-controlled-synthetic FEM comparison after confirming that no measured cell-shape field is currently available
supersedes_for_this_slice: the prior instruction to stop all synthetic FEM work at F0; the experimental-data qualification gate itself remains not_run
gpu: forbidden
automatic_retries: 0
---

# F1-S｜合成长轴方向场敏感性合同 v01

## 问题与边界

本轮只回答一个工程问题：在完全相同的二维三层心室几何、被动材料、主动应变幅度和边界条件下，把心肌长轴方向从均一局部切向场改为冻结的受控随机场，是否产生高于离散不确定度的位移和应力差异。

这是把“细胞形态信息”接入 FEM 的第一个最小接口门，不是斑马鱼真实细胞形态场。材料斑块没有独立细胞膜、接触、体积、面积或邻接自由度，不得称为显式细胞。通过只说明当前 FEM 对长轴排列场具有可解析敏感性；斑马鱼标定、生物验证、组织生长、ECM 重塑、心内膜增殖、流固耦合和 DCM--FEM 优势均为 `not_run`。

## 单变量配对设计

沿用 F0 的二维平面应变、共形三层椭圆环：由内向外为心内膜、薄 ECM 和心肌。几何、三层各向同性小应变材料、41 个规定激活相位、自由内外边界和三个 KKT 刚体规范均保持不变；无腔压、血流或夹持。

心肌层被标记为 `2×24=48` 个材料斑块：两个跨壁带、24 个周向区。斑块只为赋予主动长轴方向，不引入界面单元或额外刚度。

- `uniform`：每个心肌单元的主动长轴为局部椭圆切向。
- `synthetic_random`：在同一局部切向上叠加斑块常数方向偏移。固定 NumPy PCG64 种子 `20260916`；先生成 `2×24` 标准正态数组，再按 `0.50×本斑块 + 0.20×左右周向邻居 + 0.10×另一跨壁带` 平滑，减去全场算术均值，并将最大绝对偏移缩放为 `18°`。

随机场必须满足：偏移算术均值绝对值不超过 `1e-12°`、最大绝对值为 `18±1e-10°`、RMS 至少 `4°`。两组每个心肌单元的主动本征应变张量迹和 Frobenius 范数相同；峰值激活均为 `0.03`。本轮不随机化面积、体积、主动幅度、被动刚度或几何，避免把方向效应与其他异质性混合。

## 离散、资源与正式调用

- 复用 F0 两级共形网格：`G0` 为 48 周向区间、`G1` 为 96 周向区间；材料斑块边界在两级网格上对齐。
- 每个网格、每个条件保存 41 个真实准静态状态，共 4 条条件--网格轨迹；相位不是生理时间。
- 唯一正式阶段调用；单线程 CPU、0 GPU、0 自动重跑、无安装、无项目外写入、无删除。
- create-only 结果目录：`results/ventricle_fem/f1s_synthetic_orientation_v01_20260916`。
- 最大新增 64 MiB，另预留 64 MiB 停止空间；启动和结束时执行 3 GiB 总量门。

## 预注册门

### 输入与数值门

1. 同一级两组坐标、三角连接、层标签、材料、相位和激活幅度逐项一致；只有心肌方向角不同。
2. 随机场可由独立验证器根据种子和冻结算法重建；G0/G1 的斑块偏移完全一致。
3. 全部状态有限，所有变形后三角形面积为正；最大绝对应变不超过 `0.05`。
4. 归一化线性后向残差和刚体约束残差均不超过 `1e-10`。
5. 每个条件的 G0/G1 峰值腔面积变化绝对差不超过 `2e-3`。
6. 独立验证器从保存的位移、方向场和材料重新计算应变、应力、腔面积、网格方向及平衡残差；不得只读取求解器裁决。

### 方向场敏感性门

在峰值激活下预先定义：

\[
D_u=\frac{\lVert u_{random}-u_{uniform}\rVert_2}
{\lVert u_{uniform}\rVert_2},
\qquad
D_\sigma=\frac{\lVert\sigma^{vm}_{random}-\sigma^{vm}_{uniform}\rVert_{A,2}}
{\lVert\sigma^{vm}_{uniform}\rVert_{A,2}}.
\]

其中第二个范数只在心肌单元上按参考面积加权。方向敏感性记为 `resolved` 仅当：

- G1 的 `D_u>=0.01` 且 `D_sigma>=0.01`；
- 对 `D_u` 和 `D_sigma` 各自都有 `G1值 > 2×|G1值-G0值|`。

峰值腔面积差、心肌应力变异系数和外边界位移不均匀度作为预注册辅助读出，不参与强行判通过。若数值门通过而敏感性门未解析，报告 `engineering passed / sensitivity not_resolved`，不得调大随机幅度或改变阈值后重跑。

## 交付

- 模型结构图：两组相同真实网格、48 个材料斑块及长轴箭头，明确“斑块不是显式细胞”。
- 结果图：同色标峰值应力、应力差、腔面积曲线及 `D_u/D_sigma` 与离散不确定度。
- 41 状态并列 GIF，变形倍率 `1×`。
- 四条原始 NPZ、配置、逐相位指标、配对指标、独立验证、渲染记录、源文件哈希、存储前后检和离线 `index.html`。

本轮结束即停止。真实细胞图像提取、面积/长宽比分布、空间打乱对照、生长及 ECM 反馈只登记为后续接口，不在本次执行。
