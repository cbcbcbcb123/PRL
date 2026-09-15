---
document_id: NCS-M0-REPORT-v01
status: passed
method_positioning_status: unknown
completed_at: 2026-09-10
execution_scope: read_only_source_evidence_public_literature_and_derivation
next_contract: ncs_m1_frozen_spec_v01.md
---

# NCS-M0 实际报告：方法定位、能力审计与 M1 入口

## 1. 收口结论

M0 **PASS**：仓库能力、四类方法近邻、可证伪缺口、M1 数学与独立参考、运行环境、协议、阈值和预算已经闭合；可以按 `ncs_m1_frozen_spec_v01.md` 进入 M1a。这个 PASS 只表示 M0 规格门通过。

方法新意仍为 **UNKNOWN**。已有方法已经分别覆盖显式细胞组织、细胞—流体、分区耦合和守恒重映射；本项目只能检验一个更窄的候选贡献：在同等事件、身份和状态信息下，事件一致转移是否能同时降低非物理功、物质漂移和历史变量误差，并在局部场精度或成本上优于强基线。M1 只验证全 FEM 参照物，不构成该贡献的证据。

本阶段未运行求解器、数值测试、Docker、GPU 或安装程序；未修改用户 Figure2 合同、旧 runner、旧结果或失败包。

## 2. 仓库基线与保护边界

- 分支：`codex/simucell3d-hybrid-feasibility`。
- HEAD：`b45650a9e370be138a70acf305b6c3a21e6a7ed2`，与路线采纳记录一致。
- 工作树：dirty，含大量既有未提交材料；本任务只创建 NCS v01 文件并更新入口/驾驶舱，不把 HEAD 冒充全部材料的版本。
- 用户修改的 `project_control/prl_figure2_spatial_tolerance_validation_contract_v02.md` 保持只读；当前 SHA256 为 `633be2cd534c05ac3d3416e4ca046d52b2b17bef4f4b373fbb1a242a72e33274`，与保护记录一致。

| 能力 | 文件/函数与 SHA256 | 理论假设 | 已有验证 | 适用限制 | 复用判断 | 状态 |
|---|---|---|---|---|---|---|
| 二维 P1 平面应变 FEM、结构网格与稀疏直接解 | `src/paper2_hybrid/model.py` 的 `_constitutive_matrix`、`_structured_mesh_arrays`、`_strain_operator`；SHA256 `d43129c...e800` | 旧模型含周期方向、两连续层及离散心内膜 | 旧范围有 UFL/手工刚度交叉检查和正式运行记录 | 依赖当前主机缺失的 dolfinx；旧边界、拖曳和心内膜表示与 NCS-M1 不同 | 复用公式与装配思路；新建小型 SciPy 适配层 | passed |
| 主动应变及主动功账本 | `src/paper2_hybrid/model.py` 的 `_active_fem_full`、`_material_energy`；`src/paper2_hybrid/numerics.py` 的离散账本；SHA256 分别 `d43129c...e800`、`620381c...31e4` | 规定主动应变、二次能量 | 旧合同范围有精确离散功账本 | 旧生产算子保留背景拖曳；不能直接充当零拖曳新基准 | 复用符号与账本结构，重新装配 | passed |
| SLS/Maxwell 内变量 | 同上 `matrix_sls`、`matrix_sls_dissipation` 与 CN 风格离散；旧 `paper2_m1/idealized_strip.py` 也有 Maxwell 内变量 | 旧实现与新模型的层/阻尼边界不同 | 有旧数值证据，不等于新 M1 验证 | 新 M1 要求完整二维张量、不同支路泊松比且零背景阻尼 | 需适配 | passed |
| 共形界面与公共物理积分 | `src/paper2_hybrid/projection.py`；SHA256 `3bd590f...2176c` | 旧接口含共同分段投影 | 有制造检查 | 新 M1a 为共形全 FEM，不需要旧弹簧接口；M2 才需要非匹配映射 | 仅复用公共积分/比较思路 | passed |
| 闭合显式细胞几何、分裂及局部重网格 | `external/simucell3d/.../cell_divider.*`、`local_mesh_refiner.*` | 闭合三角曲面、过阻尼细胞力学 | 上游/项目内有分裂与重网格测试记录 | 不是 M1 心内膜连续层；细胞分裂几何不等于状态/物质/功守恒 | M2/M3 候选资产 | passed |
| 持久身份与重网格事件接口 | `external/simucell3d/include/prl_cell_engine/remesh_contract.hpp`，SHA256 `a2c872...e472`；`docs/hybrid_architecture_v06.md` | cell-scoped revision 与同步事件 | 旧范围覆盖 swap/split/merge 回调和材料状态迁移 | 尚未闭合真实分裂后的母女状态、物质和事件能量账本 | 需扩展 | passed |
| DCM 组织层 | SimuCell3D 能表示闭合细胞和增殖；本仓库存在单胞/事件资产 | 显式表面细胞 | 单胞和局部事件有旧证据 | NCS 所需有限心内膜细胞层、公平连续强对照和事件账本尚未实现 | M2/M3 缺失 | unknown |
| FSI | 历史文件只见规定压力/WSS、腔体或耦合规划 | 无已确认的流体守恒离散 | 未找到当前主线真实流体方程求解证据 | 压力载荷、lumen 实体或 preCICE 计划均不等于 FSI | M5 缺失 | unknown |

状态说明：表中 `passed` 表示该有限能力或证据已定位，不表示 NCS-M1 数值已通过。主机 Python 3.13.7 可找到 NumPy、SciPy、Matplotlib；找不到 dolfinx、petsc4py、UFL。M1 冻结为纯 NumPy/SciPy 的小型 P1 适配层，因此环境闭合且无需安装；不得为复用旧 UFL 路径自行安装依赖。

## 3. 方法近邻与最强反例

| 类别 | 最相关原始来源 | 已报告能力 | 对本项目的约束/未知 |
|---|---|---|---|
| 显式细胞组织模型 | [SimuCell3D, Nature Computational Science 2024](https://doi.org/10.1038/s43588-024-00620-9) | 闭合三角表面、组织尺度三维细胞、局部重网格、生长与增殖、ECM/腔体表示 | 已证明“显式细胞+分裂”不是新意；论文未被本轮证实含 NCS 所需的母女历史变量、离散功率与物质联合账本，记 UNKNOWN |
| 细胞—流体模型 | [LBIBCell, Bioinformatics 2015](https://doi.org/10.1093/bioinformatics/btv147) | 弹性多边形细胞与 Newtonian fluid 的 immersed-boundary 耦合，可处理形态发生及细胞事件 | 已证明“细胞+流体+分裂”不是首次；其事件状态/功率/历史转移是否满足本项目门禁未确认 |
| 通用分区耦合 | [preCICE v2 reference paper](https://doi.org/10.12688/openreseurope.14445.2) | 黑箱多物理分区耦合、加速、通信及非匹配网格数据映射 | 强基线应采用其可实现的一致/守恒映射与耦合策略；仅把 FEM、DCM、FSI 接起来不构成方法贡献 |
| 守恒重映射/事件转移 | [Farrell et al., conservative interpolation via supermesh](https://doi.org/10.1016/j.cma.2009.03.014)；[Menon & Schmidt, polyhedral extension](https://doi.org/10.1016/j.cma.2011.04.025) | 利用 common refinement/supermesh 在变化或不相干网格间保守传递场；支持重复重映射误差比较 | 这是当前最强反例之一：成熟保守投影可能已足够。它是否同时处理细胞身份、强度/广延量、SLS 历史变量和事件功仍需 M2/M3 公平实现，不能预判“不具备” |

最强反例是“common-refinement 守恒投影 + 同信息动态材料域 FEM + 成熟分区耦合”已经在相同事件上达到相同局部误差、功/物质收支和成本。若成立，则“新型守恒 FEM–DCM–FSI 方法”主张 FAIL；项目应收缩为可靠应用平台，或只保留一个经实测仍未解决的母女身份/历史变量语义问题。

## 4. 可证伪方法缺口

候选假说：在一个有限细胞层的一次受控分裂中，事件一致转移相对于上述强基线，在不减少输入信息的条件下，同时满足：

1. 母女身份和预注册局部状态继承规则；
2. 广延物质闭合、强度量由物质/体积重建；
3. 固定界面与事件前后离散功率/能量跳变可分账；
4. SLS 等历史变量按本构可接受状态转移；
5. 局部场误差或同误差成本有实质改善。

比较轴固定为：表示轴（均质 FEM、同信息动态材料域 FEM、DCM）与算法轴（最强可实现守恒投影、候选事件一致转移、去掉守恒/事件处理的消融）。反例、失败率、同误差成本和局部场精度必须报告。M0 只确认该比较可执行，不确认候选获胜。

## 5. M1 数学闭合摘要

采用二维平面应变、单位厚度、无量纲 `L=E0=T=1`。工程应变向量为 `e=[εxx, εyy, γxy]^T`，各向同性平面应变矩阵

`C(E,ν)=[[λ+2μ,λ,0],[λ,λ+2μ,0],[0,0,μ]]`，其中 `λ=Eν/((1+ν)(1−2ν))`、`μ=E/(2(1+ν))`。

心肌 `σm=Cm(e−ea)`；ECM `σe=Ceq e+CM(e−z)`、`τ zdot=e−z`；心内膜 `σn=Cn e`。`ea=[−α p(x),0,0]^T`。位移界面连续且弱牵引平衡。平面单元使用 `ux=ebar x+wx`、周期 `w`、底面 `uy=0`、`mean(wx)=0` 精确乘子和零广义轴力；顶面自由。

总储能、耗散与主动功为

`Psi=∫myo 1/2(e−ea):Cm:(e−ea)+∫ecm[1/2 e:Ceq:e+1/2(e−z):CM:(e−z)]+∫endo 1/2 e:Cn:e`，

`D=∫ecm τ zdot:CM:zdot >=0`，`Pa=−∫myo σm:eadot`，从虚功和平衡得 `dPsi/dt+D=Pboundary+Pa`。本基准 `Pboundary=0`，但约束反力与功单列。

CN 内变量精确写为

`z[n+1]=a z[n]+b(e[n]+e[n+1])`，`a=(2τ−dt)/(2τ+dt)`，`b=dt/(2τ+dt)`。

因此中点满足 `(z[n+1]−z[n])/dt=(e_mid−z_mid)/τ`；二次储能差可用中点恒等式精确计算，离散账本与相对连续参考的时间误差分开验收。

### 5.1 均匀平面独立参考

采用 `exp(iωt)`。ECM 完整复刚度为 `Ceq+g CM`，`g=iωτ/(1+iωτ)`；先相加完整张量，再作横向零应力 Schur 消元：

`D*=Cxxxx*−Cxxyy*Cyyxx*/Cyyyy*`。

各层共享宏观轴向应变，零总轴力给出

`ebar_hat=hm Dm ea_hat/(hm Dm+he De*+hn Dn)`。

DC 用 `Ceq`；谐波用 `C*`。横向应变为 `eyy=−Cyyxx*/Cyyyy* (exx−ea_xx)`（无主动层去掉 `ea_xx`），再由完整张量恢复应力、储能与耗散。参考只使用 2×2/3×3 代数，不调用二维 FEM 组装矩阵。

### 5.2 圆环独立参考

轴对称位移 `u(r)` 有 `err=u'`、`ett=u/r`，满足 `dσrr/dr+(σrr−σtt)/r=0`。各常系数被动层通解为 `A r+B/r`。心肌主动环向应变 `ea_tt=−α` 时，方程为

`u''+u'/r−u/r^2=2 μ α/((λ+2μ)r)`，

故增加特解 `c r ln r`，`c=μ α/(λ+2μ)`。对 DC 使用松弛参数，对谐波在 ECM 使用复 `λ*,μ*`；以两自由边界 `σrr(1)=σrr(1.55)=0` 和两个界面的 `u、σrr` 连续组成独立 6×6 线性系统。该参考不调用二维圆环组装，并在正式 M1b 以加倍精度/高精度残差把自身误差界压到验收阈值的 1/10。

## 6. 应用与数据边界

当前 `data/` 未定位到可独立验证的斑马鱼心室影像、分割、追踪或个体级读出；历史图包是旧模拟/图表材料，不能当新生物验证。数据来源、使用授权、成像分辨率、分割误差和参数可辨识性均为 **UNKNOWN**。这不阻塞 M1 合成基准，但阻塞生物验证和投稿水平主张。

第一验证候选固定为：用全局心室运动/激活和少量训练个体标定参数，预测未参与校准的局部心内膜位移、应变与相位；输入的全局运动不得再当验证。优先按个体或发育阶段留出。第二组织尚无已确认数据，状态 **UNKNOWN**；另一个椭圆几何不算跨组织。

## 7. 做了什么、未做什么与下一唯一切片

- 已做：受控树/能力审计、来源比较、反例、数学推导、环境和冻结规格。
- 未做：任何 M1 求解、代码测试、参数标定、DCM/FSI 扩展、方法优势或生物验证。
- 能力存在：局部 `passed`；M0 文档与规格：`passed`；M1 数值：`not_run`；方法优越：`unknown`；NCS 投稿水平：`unknown`。
- 下一唯一切片：按冻结规格执行 M1a；仅当全部必需门通过才进入 M1b。

