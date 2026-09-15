---
plan_id: "PLAN-PRL-ROUTE-H-DCM-ECM-STAGE0-STAGE2-V01"
status: "draft"
lifecycle_state: "user_review"
planner: "Codex primary task acting as Planner only"
planner_runtime: "current Codex runtime; exact model and reasoning label not exposed"
approved_by:
approved_at:
executor:
inspector:
related_memory_entries: []
supersedes: []
historical_regression_only:
  - "03_分析与代码/理论与模拟/level1_curved_canonical_v03/"
  - "03_分析与代码/理论与模拟/level1_curved_canonical_v06_stage4_response_case_registry_route2/"
stage_0_authorized: false
stage_1_authorized: false
stage_2_authorized: false
stage_3_or_later_authorized: false
formal_patch_scientific_solve_authorized: false
figure_gif_video_authorized: false
manuscript_update_authorized: false
memory_update_authorized: false
---

# Route H — 3D deformable-cell-model–ECM hybrid Stage 0–2 受治理执行计划 v01

## 当前生命周期与治理边界

本文件是 `draft`，当前停在 `user_review`。它只定义 Route H 的 Stage 0–2，
不实施、不试跑、不预跑、不生成科学结果。

迁移采用 Direct + Check；本计划涉及细胞力学、有限变形 ECM、主动收缩、载荷端口、
边界条件和证据解释，因此进入 Governed 科学门禁。当前运行约束不授权创建多角色任务；
只有用户批准具体阶段后，才可另行决定执行和独立检查的组织方式。

## Goal

建立一个可证伪、可分阶段验收的早期胚胎心室壁局部 patch 候选：

```text
blood lumen
→ explicit endocardial DCM cells
→ deformable cardiac-jelly ECM mesh
→ explicit active myocardial DCM cells
→ compliant surrounding myocardium
```

Stage 0–2 的目标不是产生论文结果，而是回答更窄的问题：

1. 每个心内膜和心肌细胞能否作为具有独立闭合三角曲面的 DCM 对象工作；
2. 独立有限变形 ECM 网格能否在不与细胞共享顶点的前提下，通过接触/黏附传力；
3. 一个明确的各向异性主动机制能否使单个心肌细胞沿 \(f_i\) 缩短、横向增厚并保持体积；
4. 细胞链、myocardium–ECM sandwich、endocardium–ECM sandwich 和最小完整 patch
   是否依次通过作用—反作用、载荷方向、功率和边界门禁；
5. 能否在 Stage 3 之前把历史 continuum 结果与新 DCM–ECM 证据彻底隔离。

## Inputs

### 权威输入与当前哈希

| 输入 | SHA-256 | 用途 |
|---|---|---|
| `project_control/project_handoff_20260728_v01.txt` | `B1A85678439E6DACBB877DFD7D38E7A319C876F99717F2526F8A928156A8E426` | Route H、层次、授权和禁区 |
| `references/2024 - Nature Computational Science - Iber - SimuCell3D三维组织力学模拟.md` | `991DB9A8FCB156EBA0F8731D9342BBFE741EED228C3867BD7A0B16AE62E23BDA` | 独立闭合三角曲面、体积/面积/弯曲、接触与黏附的参考 |
| `migration/migration_report_v01.md` | `357BA6F2006CAA37ECE9500E73F6F4A30BD21F04355966A0628CED208A1DECB9` | 迁移与可读性边界 |
| `heart_patch_loading_upgrade_inspection_v01.md` | `F39E8967EFC24B7B66C89D838937344E45EDD07FAFB0D45276DDBF43AA2E422A` | 历史 v03 incremental foundation 的 caveat |
| `heart_patch_stage4_response_case_registry_inspection_v02.md` | `17693F6F32A6E8CCF309FB8DC7F8503B512CE3D9CE68D83AC0BD74CAE12CCC28` | 历史 v06 Stage 4 `blocked` 结论 |
| `stage4_case_terminal_status_v02.csv` | `D43FD6B7ACCBC2469F8FC7F14CD70034AE99D2BBA0D423C4FEC0253E3257A2BD` | failed / not-run / rejected 状态边界 |

以上历史文件只读。执行前必须复算哈希；不匹配则停在 Stage 0。

### 历史证据边界

- v03 的 `accepted_with_caveats` 只适用于二维、几何线性、选定心动相位附近的
  dimensionless incremental continuum audit。
- v06 Stage 4 的总体科学状态是 `blocked`；small-increment 与 \(J_s\) 适用域失败已足以
  阻止该 midpoint loading 下继续 registry，且未形成 response/mechanism evidence。
- continuum foundation、v03、v06 和 Stage 4 只能提供符号、ledger、KKT、边界和回归检查
  的历史参考；不得继承 solver pass flag、参数合法性、几何适用域或 Route H 验证结论。

## Stage 0 — 结果前冻结模型合同

Stage 0 只允许写合同、规格、几何定义和验证注册表；不实现求解器，不执行数值轨迹。

### 0.1 坐标、层次与表面 identity

冻结右手坐标：

- \(e_z\)：从 lumen 指向外侧心肌；
- endocardial apical outward normal \(n_{\rm lum}=-e_z\)；
- 血压对 apical face 的牵引为
  \[
  t_p=-p\,n_{\rm lum}=p\,e_z,\qquad p\ge0;
  \]
- WSS 为切向牵引
  \[
  t_\tau=P_{\rm lum}\tau_w,\qquad
  P_{\rm lum}=I-n_{\rm lum}\otimes n_{\rm lum}.
  \]

每个 DCM 细胞必须保存 material face/vertex identity：

- endocardium：`apical_lumen | basal_ecm | lateral`;
- myocardium：`basal_ecm | lateral | opposite_outer`;
- 不允许根据瞬时法向或接触对象在结果后重贴 identity。

每个细胞拥有独立、watertight、定向一致的三角曲面。相邻细胞、ECM 与环境之间不共享
顶点；所有传力必须经过显式 contact/adhesion operator。

### 0.2 DCM 被动力学

Stage 1–2 的共同被动能量候选为

\[
\Psi_{\rm cell}
=\Psi_{\rm area}
+\Psi_{\rm bend}
+\Psi_{\rm vol}
+\Psi_{\rm cc}
+\Psi_{\rm cell-ECM}.
\]

最低合同：

1. `area`：被动 membrane/cortex 面积弹性；可含 face-type-dependent passive tension；
2. `bend`：基于相邻三角面二面角的离散弯曲能；
3. `vol`：体积约束或凸体积惩罚，目标体积 \(V_{0,i}\) 结果前冻结；
4. `cc`：细胞—细胞排斥与黏附；
5. `cell-ECM`：basal 面与 ECM 边界之间的排斥、黏附和可选切向摩擦。

各向同性表面张力只能作为被动 cortex 参数，禁止作为心肌主动收缩的替代。

接触 primary route 采用能量一致的 regularized traction–separation law；每个配对的
两侧离散力必须由同一 interaction potential 产生，保证作用—反作用。若使用非保守
摩擦，必须单独登记非负耗散 \(D_{\rm fric}\)，不得混入黏附储能。

### 0.3 心肌主动机制：唯一 primary 候选

Stage 2 primary 采用沿 \(f_i\) 的 **active preferred length**，不采用各向同性主动表面张力。

对每个心肌细胞，在结果前固定两组 material anchor patches
\(\Gamma_i^-\)、\(\Gamma_i^+\)，其面积加权质心为 \(c_i^-\)、\(c_i^+\)。定义

\[
L_{f,i}=(c_i^+-c_i^-)\cdot f_i,\qquad
L_{f,i}^{\star}(t)=L_{f,i}^{0}\,[1-\alpha_i(t)],
\]

\[
\Psi_{{\rm act},i}
=\frac12 k_{f,i}\left(L_{f,i}-L_{f,i}^{\star}\right)^2 .
\]

其中 \(0\le\alpha_i(t)<1\)，\(f_i\) 是冻结或按批准规则更新的单位材料方向。
anchor forces 必须以分区面积权重回分到膜节点，并满足零净内部力与零净内部力矩。
主动输入功率采用

\[
P_{{\rm act},i}
=-\frac{\partial\Psi_{{\rm act},i}}
        {\partial L_{f,i}^{\star}}
  \dot L_{f,i}^{\star},
\]

其符号在 Stage 0 manufactured test 中冻结。

若该单一 preferred-length 机制不能通过单细胞门禁，Stage 2 立即停止；不得在同一版本
中追加第二种主动机制。内部有限应变细胞体或内部纤维网络必须另起新计划并由用户批准。

### 0.4 ECM 有限变形层

primary ECM 是独立的薄体积 tetrahedral mesh，而不是 cell surface 的共享网格。
Stage 1–2 采用无量纲、有限变形、可压缩性受控的被动黏弹固体：

\[
\Psi_{\rm ECM}
=\int_{\Omega_{\rm ECM,0}}
W_{\rm eq}(F;A,H_{\rm ECM})
+W_{\rm ve}(F,z_{\rm ve};A,H_{\rm ECM})\,dV_0,
\]

其中 \(F\) 为有限变形梯度，\(z_{\rm ve}\) 为黏弹内部变量。

硬性语义：

- \(A\)：ECM areal amount；
- \(H_{\rm ECM}\)：natural/remodeling thickness；
- Stage 1–2 中二者均登记但冻结，不运行 turnover；
- 默认不假设 \(H_{\rm ECM}=A/\rho_{\rm ECM}\)；
- 只有另行批准“有效密度恒定”后才可启用该闭合；
- 网格至少有两个单元层跨越厚度，若几何/网格门禁不能满足则停机；
- 旧 continuum 的 \(A,h_{\rm ECM}\) 数值不得作为本模型参数直接继承。

### 0.5 界面、来源与边界

机械界面：

- endocardium basal surface ↔ ECM lumen-facing boundary；
- myocardium basal surface ↔ ECM outer-facing boundary；
- myocardium opposite surface ↔ compliant surrounding myocardium；
- lateral cell surfaces ↔ 同层细胞。

Stage 1–2 仅验证机械耦合。ECM 来源通量 \(j_{\rm myo}\) 只注册映射：
每个心肌细胞 basal 面的通量必须按接触/最近邻映射进入相邻 ECM 单元；不允许无细胞归属
的均匀源。由于完整 turnover 未授权，Stage 1–2 取 \(j_{\rm myo}=0\) 并只做映射单元测试。

完整 patch 的 primary 周边为有限刚度/阻尼 compliant support；允许 periodic sensitivity，
不允许把四周全部固定。任何为去除刚体模态而使用的 gauge 必须标记 `solver_gauge`，
不得产生物理反力 claim。

### 0.6 血流机械端口与 \(\chi_E\)

压力和 WSS 只作用于 endocardial apical faces：

\[
f_{p,a}=\frac{A_a}{3}\,t_{p,a},\qquad
f_{\tau,a}=\frac{A_a}{3}\,t_{\tau,a}
\]

分配到 face 的三个节点。不得直接施加到 ECM。

机械功分别登记：

\[
P_p=\sum_{a\in\Gamma_{\rm apical}} A_a\,t_{p,a}\cdot v_a,
\qquad
P_\tau=\sum_{a\in\Gamma_{\rm apical}} A_a\,t_{\tau,a}\cdot v_a.
\]

\(\chi_E\) 在 Stage 2 只作为 flow-sensing diagnostic/control state 注册，例如

\[
\tau_\chi\dot\chi_E=G(|\tau_w|)-\chi_E.
\]

其输出不得进入机械功率。KLF2、Notch、WNT9B、NRG1、fibronectin 和 ADAMTS
只作为后续可选生化 target registry；Stage 0–2 不实现基因网络或对 ECM 的反馈。

### 0.7 完整功率账本

Stage 2 最小完整 patch 必须闭合

\[
\frac{d}{dt}
\left(
\Psi_{\rm cells}
+\Psi_{\rm ECM}
+\Psi_{\rm adhesion}
+\Psi_{\rm support}
\right)
+D_{\rm cell}
+D_{\rm ECM}
+D_{\rm contact}
+D_{\rm support}
=
P_{\rm act}
+P_p
+P_\tau
+P_{\rm env}.
\]

约束：

- cell–cell 与 cell–ECM 内力成对抵消，不重复记为 external work；
- contact KKT/constraint reaction 不记为 source、dissipation 或 external work；
- \(\chi_E\) 与血流生化控制不进入机械账本；
- \(A,H_{\rm ECM}\) 在 Stage 1–2 冻结，因此 turnover/source power 为零；
- 若任一黏弹或摩擦耗散为负，立即失败；
- resultant、坐标、法向、traction 和 active sign 必须通过 orientation-reversal test。

## Stage 1 — 被动内核与独立模块

只有 Stage 0 合同经检查并由用户接受后，才可授权 Stage 1。

### 1.1 候选模块

核心实现必须位于
`03_分析与代码/理论与模拟/route_h_dcm_ecm_v01/src/`，notebook 不复制核心求解器：

- `geometry.py`：watertight DCM、ECM tetra mesh、face identity 和质量检查；
- `dcm_cell.py`：面积、弯曲、体积与被动节点力；
- `contact_adhesion.py`：cell–cell、cell–ECM 和 action–reaction；
- `ecm_finite_strain.py`：有限变形黏弹 ECM；
- `coupling.py`：接触搜索、basal 映射和 \(j_{\rm myo}\) 映射测试；
- `loads.py`：pressure、WSS、compliant/periodic support；
- `activation.py`：Stage 2 preferred-length 与预注册 traveling activation protocol；
- `ledger.py`：储能、耗散、外功和 residual；
- `solver.py`：唯一求解入口；
- `contracts.py`：版本、哈希、units、case 和 gate enforcement。

模块名可在 Stage 0 设计检查时缩减，但职责不得重新埋入 notebook。

### 1.2 Stage 1 必须通过的被动 tests

1. **几何**：每个 cell watertight、manifold、outward orientation 一致、无负体积；
   ECM tetra Jacobian 为正，跨厚度单元数满足合同。
2. **能量—力一致性**：area、bend、volume、adhesion、ECM 的解析/自动微分力与
   中心差分 directional derivative 相符。
3. **刚体不变性**：无外载时整体平移/转动不改变保守能；净内力和净内力矩为零。
4. **接触**：两细胞及 cell–ECM pair 的作用—反作用、黏附分离、排斥穿透和
   接触搜索重复性通过。
5. **ECM**：单 tetra/patch test、纯拉伸、简单剪切、体积变化和黏弹松弛；
   \(F\) 与 power conjugacy 正确。
6. **载荷**：平面 endocardial patch 上压力 resultant 纯法向，WSS resultant 纯切向；
   orientation reversal 后物理牵引不变。
7. **ledger**：静态保守路径、黏性松弛和 compliant support 的离散功率闭合。
8. **映射**：每个 basal quadrature/face 只能归属一个登记 cell；\(j_{\rm myo}=0\)
   时 ECM source 严格为零。

Stage 1 不启用心肌主动机制，不生成完整 patch trajectory。

## Stage 2 — 逐级机械验证门禁

只有 Stage 1 inspection 被用户接受后，才可授权 Stage 2。Stage 2 使用无量纲、
非生理标定参数；激活采用结果前冻结的 prescribed traveling phase，仅验证力学传播，
不声称电生理传导。

### Gate A — 单个心肌细胞

- 启用唯一 active preferred-length；
- 轴向 \(L_{f,i}\) 缩短；
- 与体积约束相容的横向增厚；
- 体积误差受控；
- 无非物理刚体漂移；
- active work、储能、阻尼/黏性耗散闭合。

若只有通过提高各向同性表面张力才能缩短，判定失败。

### Gate B — 心肌细胞链

- 3–5 个细胞，独立闭合曲面和 cell–cell contact/adhesion；
- 预注册 traveling activation phase 依次到达；
- junction pair forces 满足作用—反作用；
- 无持续重叠、穿透、非物理脱离或拓扑跳变；
- 链整体在无外部偏置时无净内力/净力矩漂移；
- 激活相位与机械响应的记录分开，不解释为电生理波速。

### Gate C — Myocardium–ECM sandwich

- 心肌 basal 面通过 cell–ECM 黏附向 ECM 传力；
- 首要 ECM 响应为沿 \(f_i\) 的切向牵引；
- 法向响应只能来自接触、曲率、有限变形和体积约束；
- 禁止加入虚假法向 \(q\)；
- \(j_{\rm myo}\) mapping 可审计但数值保持零；
- cell–ECM 内力在整体账本中成对抵消。

### Gate D — Endocardium–ECM sandwich

- \(p\) 只在 apical face 上产生法向载荷；
- \(\tau_w\) 只在 apical face 上产生切向载荷；
- ECM 不接收直接血流载荷；
- 载荷经 endocardial cell skeleton/contact 与 basal adhesion 传递；
- \(\chi_E\) 响应 WSS 但不进入机械功；
- pressure-only、WSS-only、zero-load 三个消融必须保留。

### Gate E — 最小完整 patch verification

只允许一个小型验证 patch，不是正式科学计算：

- 1 层 endocardial cells；
- 独立 ECM finite-deformation mesh；
- 1–2 层 active myocardial cells；
- compliant surrounding support；
- zero、active-only、pressure-only、WSS-only、combined 五个注册 case；
- compliant primary 与 periodic sensitivity；禁止全固定周边；
- KKT/contact、resultant、orientation 和 power ledger 全部闭合；
- 不扫参数、不生成论文图、不解释发育机制。

Gate A–E 严格顺序执行。任一 gate 失败，后续 gate 不运行；失败输出、日志和配置原样保留。

## 预注册验收阈值

以下为 draft 建议值，须在 Stage 0 人工批准后冻结；不得按 response 调整。

| 检查 | 建议阈值 |
|---|---:|
| 单元/面 directional derivative 相对误差 | \(\le 10^{-5}\) |
| pairwise action–reaction 归一残差 | \(\le 10^{-10}\) |
| 静态平衡归一残差 | \(\le 10^{-6}\) |
| 单细胞相对体积误差 | \(\le 5\times10^{-3}\) |
| 无外载刚体质心漂移 | \(\le 10^{-4}L_{\rm cell}\) |
| 接触最大穿透 | \(\le 10^{-2}L_{\rm cell}\) 且通过 mesh refinement |
| active contraction 轴向缩短 | \(1\%\)–\(20\%\)；超出即 scope fail |
| transverse response | 两个横向尺度均非负，至少一个 \(>1\%\) |
| integrated normalized power residual | \(\le 5\times10^{-3}\) |
| 各耗散项 | \(\ge-10^{-10}\)（数值容差后非负） |
| 最后两级时间细化关键量相对差 | \(\le2\%\) |
| 最后两级空间细化关键量相对差 | \(\le3\%\) |
| ECM tetra Jacobian | 全部 \(>0\) |

若量接近零导致相对误差失真，同时报告绝对误差与预注册归一尺度，不得删去该 case。

## Outputs

### Stage 0 候选输出

- `03_分析与代码/理论与模拟/route_h_dcm_ecm_v01/route_h_contract_v01.json`
- `03_分析与代码/理论与模拟/route_h_dcm_ecm_v01/route_h_model_specialization_v01.json`
- `03_分析与代码/理论与模拟/route_h_dcm_ecm_v01/route_h_cases_v01.json`
- `03_分析与代码/理论与模拟/route_h_dcm_ecm_v01/route_h_coordinate_and_sign_convention_v01.md`
- `03_分析与代码/理论与模拟/route_h_dcm_ecm_v01/route_h_port_and_power_ledger_v01.csv`
- `03_分析与代码/理论与模拟/route_h_dcm_ecm_v01/route_h_verification_registry_v01.csv`
- `03_分析与代码/治理/route_h_dcm_ecm_hybrid/route_h_stage0_execution_log_v01.md`

Stage 1–2 的代码、结果目录和 inspection artifacts 只在相应阶段获批后创建。
所有新版本另存；不覆盖 continuum、v03、v06、Stage 4 或现有 Fig.1–Fig.9。

## Implementation Steps

1. 用户只批准或修订本计划的 Stage 0 范围。
2. Stage 0 Executor 复算输入哈希，只写合同、规格、端口和验证注册表。
3. 独立只读检查 Stage 0 的方程、符号、单位、拓扑、active work 和证据边界。
4. 用户接受 Stage 0 后，另行批准 Stage 1 被动内核。
5. Stage 1 实现模块和被动 tests；不启用 active、不运行完整 patch。
6. 独立检查 Stage 1；用户决定 `proceed | revise | replace | stop`。
7. 用户批准后才执行 Stage 2 Gate A–E；每一 gate 通过后才允许下一 gate。
8. Stage 2 独立检查后停机；Stage 3 及正式 patch 计算必须有新计划和新授权。

## Impacted Files Or Modules

当前实际写入仅本 draft plan。

计划获批后的最大候选写域：

- `03_分析与代码/理论与模拟/route_h_dcm_ecm_v01/`
- `03_分析与代码/治理/route_h_dcm_ecm_hybrid/`

只读域：

- `references/`
- `project_control/`
- `migration/`
- continuum foundation、`level1_curved_canonical_v03/`、`v06.../`
- 现有 `02_图表/Fig1`–`Fig9`

禁止写入 C:、D:、旧源项目和任意 `generated_images`。

## Test Plan

### 科学/数学 tests

1. 复推 DCM area、volume、bending 和 active preferred-length forces。
2. 验证 \(P_{\rm act}\) 符号、压力/WSS traction 与 power conjugacy。
3. 复推 contact/adhesion 的 pairwise action–reaction 与 potential/dissipation 分解。
4. 验证 ECM finite-strain stress、黏弹内部变量和离散能量不等式。
5. 验证 \(A\) 与 \(H_{\rm ECM}\) 在状态、单位、配置和输出中完全分离。
6. 验证 \(\chi_E\) 对 WSS 的响应不重复进入机械功。
7. orientation reversal、rigid motion、zero load、zero activation 和 zero adhesion limits。

### 数值 tests

1. mesh manifold、法向、volume、tet Jacobian 和 face identity；
2. finite-difference directional derivative；
3. contact-search deterministic replay；
4. force、moment、equilibrium、penetration 和 volume residual；
5. time/space refinement；
6. power ledger、各耗散非负与重复运行一致性；
7. 每个 failed gate 的 terminal status 与未运行后续 case 的原因完整保留。

### 文件和 provenance tests

1. contract/config/source hash 在每阶段入口和交付时记录；
2. 核心模块不得复制到 notebook；
3. 每个 notebook/脚本记录输入版本、模型版本和输出路径；
4. 不出现指向旧 D: 根目录的运行时依赖；
5. continuum/v03/v06 输出不得进入 Route H case dependency；
6. 不生成 PNG、SVG、GIF、视频或稿件变更。

## Risks

| 风险 | 后果 | 停机/处置 |
|---|---|---|
| preferred-length 不能产生合理缩短/增厚 | surface DCM 主动机制不足 | Gate A 失败；另行申请 preferred metric、active tension 或内部模型 |
| contact penalty 控制结果 | 伪牵引或穿透 | refinement 与 penalty sensitivity 不稳则停止 |
| ECM 过薄或网格翻转 | 有限变形结果无效 | \(J\le0\) 或厚度分辨率不足立即失败 |
| 法向或 WSS 符号错误 | 载荷和功率结论反转 | orientation-reversal test 不通过即停止 |
| 全固定边界制造反力 | patch 结果被边界主导 | 只允许 compliant/periodic/有限位移；全固定 case 不注册 |
| 主动输入和环境运动双计 | ledger 与因果失效 | parent port registry 中每个输入唯一 owner |
| \(\chi_E\) 被当作机械功 | 血流输入重复计算 | Stage 2 feedback 固定 off；mechanical/chemical ledger 分开 |
| \(A\) 与 \(H_{\rm ECM}\) 混写 | turnover 语义失效 | schema/type/unit test 失败即 block |
| 历史 continuum pass 回流 | 错误升级证据 | dependency hash gate 禁止引用旧结果作为 pass |
| 激活相位被误写为电生理 | 过度 claim | 只称 prescribed traveling mechanical activation protocol |
| 数值参数按响应调整 | 不可证伪 | Stage 0 冻结；任何改变新版本并重新检查 |

## Acceptance Criteria

### 本 draft 可批准的条件

1. 用户接受 Route H 的层次、坐标和 load sign；
2. 用户接受独立 closed-surface DCM 与独立 finite-deformation tetra ECM；
3. 用户接受 Stage 2 唯一 primary 为 active preferred length；
4. 用户接受 Stage 1–2 冻结 \(A,H_{\rm ECM}\)，不运行 turnover；
5. 用户接受 \(\chi_E\) 仅为 diagnostic，生化反馈 off；
6. 用户接受 Gate A–E 顺序和建议阈值；
7. 用户接受下一次只授权 Stage 0，不自动授权 Stage 1–2。

### Stage 0 完成条件

1. 合同明确所有 state、energy、force、contact、load、BC、unit 和 ledger owner；
2. \(A\)、\(H_{\rm ECM}\)、\(\chi_E\) 和 active input 不混写；
3. geometry/face identity、normal/traction、action–reaction 和 active work 可独立复推；
4. cases/gates/tolerances 在任何 response 前冻结；
5. 旧 continuum 文件只读，Route H dependency 不继承旧 pass flag；
6. inspection 无 blocking scientific finding，并由用户接受。

### Stage 1 完成条件

所有 1.2 tests 通过，代码与合同一致，没有 active/full-patch trajectory，没有未批准写域。

### Stage 2 完成条件

Gate A–E 依次通过；所有 failed/null case 如实保留；没有正式 parameter sweep、论文图、
发育机制 claim、生理标定或对历史 Stage 4 的重新解释。

## Out Of Scope

- 新的正式科学求解或 claim-bearing patch run；
- Stage 3 及以后；
- 完整 ECM turnover、非零 \(j_{\rm myo}\) 或 \(H=A/\rho\) 闭合；
- Stage 4 response registry 重跑、Stage 5；
- CFD/FSI、真实心室几何、材料/生理参数标定；
- EndoMT、间充质细胞、成熟成纤维细胞或晚期 cushion 模型；
- 心肌细胞内部有限应变体、内部纤维网络或电生理传播模型；
- KLF2/Notch/WNT9B/NRG1/fibronectin/ADAMTS 反馈实现；
- 正式论文图、GIF、视频、动画、稿件修改；
- stable Memory、Git commit/push、旧项目删除。

## Required Memory Updates

本计划及 Stage 0–2 均不授权 stable Memory 更新。只有 Stage 2 独立检查完成且用户接受后，
Memory Curator 才可另行提出最小 `decision_memory` / `inspection_memory` 草案；历史
continuum 结论不得被重写为 Route H evidence。

## Required User Approval

当前下一项需要的唯一科学批准是：

> 批准 `PLAN-PRL-ROUTE-H-DCM-ECM-STAGE0-STAGE2-V01` 的 Route H 候选架构与
> Stage 0 范围；仅授权在
> `03_分析与代码/理论与模拟/route_h_dcm_ecm_v01/`
> 和对应治理目录中创建合同、规格、坐标/符号、端口/功率账本和验证注册表。
> 不授权实现求解器、运行 Stage 1–2、运行正式 patch、生成图件、修改稿件或更新 Memory。
