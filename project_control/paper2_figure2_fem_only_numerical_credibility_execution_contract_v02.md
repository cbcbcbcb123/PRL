---
contract_id: CONTRACT-PAPER2-FIGURE2-FEM-ONLY-NUMERICAL-CREDIBILITY-EXECUTION-V02
status: draft_for_independent_supervisor_review
created_at: 2026-09-04
created_by: executor
governance_mode: governed_computational_paper
baseline_commit: c52b2de7536a055699b2e23011fa221a6f2f1019
baseline_upstream_ahead_behind: 0/0
accepted_design_contract: project_control/paper2_figure2_fem_only_numerical_credibility_contract_v03.md
accepted_design_contract_sha256: 796de6a6cfa6167e30cae592128379206709ace720d4fcbe3ae80366fb504249
supersedes_reviewed_contract: project_control/paper2_figure2_fem_only_numerical_credibility_execution_contract_v01.md
supersedes_reviewed_contract_sha256: 2cbbae0f09bb966e9292a306f4c7a698952f9bf962139c772b1cfb02e4b7c070
source_review: project_control/paper2_figure2_fem_only_numerical_credibility_execution_contract_v01_supervisor_review_v01.md
source_review_sha256: 0a02656853625b52ff10b99379d7c5421e90b528fcf0a804ec33820e49edfb4d
active_architecture: endocardium_discrete_chain__myocardium_active_fem__ecm_viscoelastic_fem
evidence_level: prospective_execution_contract_not_implementation_or_numerical_evidence
implementation_authorized: none
execution_authorized: none
next_gate: independent_supervisor_review
---

# Paper 2 Figure 2 FEM-only 数值可信度执行合同 v02

## 0. 修订目的、成功含义与本轮边界

本合同规范性纳入经审阅且 SHA 锁定为
`2cbbae0f09bb966e9292a306f4c7a698952f9bf962139c772b1cfb02e4b7c070` 的执行合同 v01
全部未冲突条款，并一次关闭审阅 B1–B5：冻结第二周期切片、制造探针与谱算法、逐
machine key 的 QoI/floor/参考方向、ECM 侧物理牵引与 digest—NPZ 绑定，以及父目录、
非删除式超时、正式 inventory/ledger 和确定性资源上界。

规范优先级唯一为：已接受设计合同 v03 最高；本 v02 的 B1–B5 澄清次之；经审阅 v01
的其余条款再次之。v01 与 v02 共同构成完整执行合同，任何实现不得把 v02 未重复的 v01
schema、阶段输入/输出、stop label、事务或证据边界解释为撤销；冲突时只按上述优先级，
不得自行选择。

未来候选标签 `FIGURE2_FEM_ONLY_NUMERICAL_CREDIBILITY_PASS_V03` 只有在以下全部成立时
才可生成：

1. 八个核心模型文件、设计合同、本执行合同、获批实现和环境前后锁一致；
2. 开发门按
   `G0 → G1 → G2 → G3 → G4a → G5 → G4b → G4 → G6 → G7` 逐门通过；
3. 开发规则、结果和 36 个 formal 数组内容 digest 已写入并重读一致；
4. digest 后才首次求解 S1，且全部适用 S1 子门通过；
5. 资源、数组、inventory、ledger 与根 completion 验证通过；
6. 独立 Supervisor 与人类终审随后接受。

该标签只支持当前二维 FEM-only 三层模型在冻结有限阶梯上的数值可信度，不支持生理
真实性、EFE 机制、三维/整心房、流体、实验验证或 Nature Physics 级普适规律。

本轮只新增本 v02 文档；不修改 v01、其审阅、v03、CURRENT_STATUS、源码、测试或
结果，不运行 solver/Docker，不创建结果目录，不执行 Git 暂存、提交或推送。

## 1. 不可变核心与将来拟新增文件

### 1.1 核心只读 SHA 锁

| 对象 | SHA-256 |
|---|---|
| Figure 2 v03 | `796de6a6cfa6167e30cae592128379206709ace720d4fcbe3ae80366fb504249` |
| Figure 1 v02 | `a669e142dfd0548bf3840e06482bbde9e339d8dd1d56a716f3c577b461ee61a7` |
| `src/paper2_hybrid/__init__.py` | `4626ee6f49cac099734728fe0dc2f3412ded11cf5066b32aff556cc39324783f` |
| `src/paper2_hybrid/config.py` | `0a83aedbabeb944b89f9584511dac5a597401327a68ac5c6411cb30e81ced6fe` |
| `src/paper2_hybrid/model.py` | `d43129c746c133294fcc92149d519a6c94bd633f2be54c898beea5d23190e800` |
| `src/paper2_hybrid/numerics.py` | `620381c4f0165801f2af03defe587e8381c9b6859f8bbd9d2f84198a555331e4` |
| `src/paper2_hybrid/projection.py` | `3bd590f0deef1fbe47cfdf01dea48664b25ff5a8716a546e4758bc4a0642176c` |
| `src/paper2_hybrid/protocol.py` | `f96d779cfcd6c76e9535f90a9941a6156b545d53a0270f04a564c68a304fe3ca` |
| `src/paper2_hybrid/roles.py` | `beb447ab12b8c433973ca807bba07331b8640b9fb9d4c944e3595510a3a501ec` |
| `src/paper2_hybrid/validation.py` | `6cfc1f383dbe92b6684eb1bd7f228610815ad67bd60ba1ecaaef8ab91cb1f0c5` |

八个 `paper2_hybrid` 文件必须只读；验证层只能调用它们，禁止 monkey patch、复制替换
方程或改变生产观测语义。任何方程、参数、几何、载荷、病例、阈值、公共域、物理力
方向、生产观测量或 DAG 变化均使本合同失效。

### 1.2 唯一拟新增实现清单

| 文件 | 唯一职责 |
|---|---|
| `src/paper2_figure2/__init__.py` | 只导出执行协议、门禁和证据接口 |
| `src/paper2_figure2/spec.py` | 端点、DAG、machine registry、尺度、floor、阈值和 stop code |
| `src/paper2_figure2/manufactured.py` | N1/N2 确定性制造、共轭、谱与零 RHS |
| `src/paper2_figure2/projection.py` | 空间解析 P0、中心化相位解析平均、步量交叠映射 |
| `src/paper2_figure2/observables.py` | 第二周期提取、ECM 侧物理量、能量分解与立即压缩 |
| `src/paper2_figure2/adjudication.py` | N1–N11、G0–G7、S1 与最终裁决 |
| `src/paper2_figure2/evidence.py` | create-only writer、inventory、NPZ registry、digest 与 ledger |
| `scripts/run_paper2_figure2_fem_only_numerical_credibility_v01.py` | 唯一宿主/容器双模式 runner |
| `tests/paper2_figure2/test_spec_v01.py` | 协议、端点、DAG、machine registry 与禁用路线 |
| `tests/paper2_figure2/test_source_lock_v01.py` | 核心 SHA、导入图和实现锁 |
| `tests/paper2_figure2/test_projection_v01.py` | 三类映射、切片、shape/time 与守恒 |
| `tests/paper2_figure2/test_manufactured_v01.py` | N1/N2 固定探针和算法参数 |
| `tests/paper2_figure2/test_adjudication_v01.py` | N1–N11、floor、方向、FAIL 与短路 |
| `tests/paper2_figure2/test_evidence_v01.py` | create-only、digest—NPZ、inventory、ledger、completion |
| `tests/paper2_figure2/test_runtime_smoke_v01.py` | S2/P0、S2/A2 最小运行 smoke |

不得新增第二 runner、协议源或 writer。未来实现验收必须另建
`project_control/paper2_figure2_fem_only_numerical_credibility_implementation_lock_v01.json`，
冻结验收 commit、上述 15 文件和核心文件的字节数/SHA；缺失即
`MISSING_VALIDATION_INTERFACE_FAIL`。

## 2. 冻结端点、调用与无环 DAG

### 2.1 病例与唯一调用

- 开发集：`A2/LN/LS/C0/CQ`；
- `P0`：formal index 0 的 S2/T64 真零 RHS，同时用于 floor/G1；它不计独立物理病例，
  也不另作一次动态 API 调用；
- `P1`：仅 G0 affine patch/tangent，不形成动态端点；
- `A1`：只作当前输入与 A2 的别名审计，不重复求解或计证据；
- `S1`：digest 后独立留出。

除 P0 外的 39 个 formal/holdout 动态端点只调用
`paper2_hybrid.model.build_system` 与
`paper2_hybrid.numerics.simulate_endpoint`；禁止旧
`paper2_hybrid.model.simulate_endpoint` 账本路径。D0 只是固定 SuperLU 标签，不是
tolerance 轴。

### 2.2 36+4 端点固定轴

| formal 索引 | 病例 | 空间 | 时间 | 数量 |
|---:|---|---|---|---:|
| 0 | P0 | S2 | T64 | 1 |
| 1–5 | A2、LN、LS、C0、CQ | S2 | T64 | 5 |
| 6–10 | A2、LN、LS、C0、CQ | S3 | T64 | 5 |
| 11–15 | A2、LN、LS、C0、CQ | S3 | T128 | 5 |
| 16–20 | A2、LN、LS、C0、CQ | S3 | T256 | 5 |
| 21–25 | A2、LN、LS、C0、CQ | S2 | T128 | 5 |
| 26–30 | A2、LN、LS、C0、CQ | S4 | T128 | 5 |
| 31–35 | A2、LN、LS、C0、CQ | S4 | T256 | 5 |

S1 轴依次为 `S1__S3__T128__D0`、`S1__S3__T256__D0`、
`S1__S4__T128__D0`、`S1__S4__T256__D0`。总计 S2=11、S3=17、S4=12；每个端点
记录只生成一次，后续门复用同一压缩对象。其中 formal index 0 复用 G0 的 S2/T64 真零
求解，不调用 `simulate_endpoint`；`formal_native_steps_per_cycle[0]=64`。S3/S4 的 G0 真零
控制只用于跨层 \(N_Q\)，不加入 36+4 轴或 40 个端点记录。S1 对象在 digest 成功重读前
不得实例化。

### 2.3 唯一阶段顺序

```text
HOST_CREATE
  -> PRECHECK
  -> G0 -> G1 -> G2 -> G3 -> G4a -> G5 -> G4b -> G4 total -> G6 -> G7
  -> pre_holdout_digest write + disk reread + recompute
  -> S1-G1 -> S1-G4a -> S1-G5 -> S1-G4b -> S1-G4 -> S1-G6 -> S1-G7
  -> FINAL summary -> inventory -> ledger -> root completion
  -> Supervisor Gate
```

任一硬门失败立即短路。G4 只在 G4a、G5、G4b 全 PASS 后由真值表形成，不调用
求解器。任何后续端点在注册前均先过 N3；失败立即 `ALGEBRAIC_FAIL`。

## 3. B1 — 第二周期、重复端点与步区间的唯一切片

### 3.1 节点数组 shape 与时间坐标

令端点每周期步数为 \(N\in\{64,128,256\}\)，
\(\Delta t=T/N\)。下列节点数组必须具有精确 shape：

| 源字段 | 精确 shape |
|---|---|
| `time_two_cycles`, `activation_two_cycles`, `limited_shortening_two_cycles`, `free_shortening_two_cycles` | `(2N+1,)` |
| `mean_endocardial_*_displacement_two_cycles` | `(2N+1,)` |
| `state_two_cycles` | `(state_size,2N+1)` |
| `*_traction_two_cycles` | `(2*n_interface_nodes,2N+1)`，随后唯一 reshape 为 `(n_interface_nodes,2,2N+1)` |

必须逐点满足 `time[i]=i*T/N`，绝对误差 `le 64*eps_float64*T`，并满足
`time[0]=0,time[N]=T,time[2N]=2T`。shape、单调性、起点或相位不符立即
`SOURCE_OR_PROTOCOL_DRIFT_FAIL`；禁止自动截取、平均、排序或循环移位。

### 3.2 生产周期与 G7 对照

- 所有 Fourier、公共 P0、L2、合力、热点和正式波形只取第二周期半开节点切片
  `N:2N`，归一相位坐标为 `time[N:2N]-T`；
- 第一周期半开节点切片 `0:N` 只用于 G7 与第二周期逐点比较；
- 重复终点索引 `2N` 只与索引 `N` 作闭合检查，不进入 Fourier、L2、峰值段、公共数组
  或任何时间积分；
- G7 同时比较 `0:N` 对 `N:2N`，并单列节点 `0/N/2N` 的闭合误差；
- 不允许 cycle 1、cycle 2 平均或用第一周期替代正式输出。

### 3.3 步数组与第二周期账本

原生生产步区间唯一为
`[T+n*dt,T+(n+1)*dt), n=0,...,N-1`，归一后为 `[n*dt,(n+1)*dt)`。

当前只读代码事实固定为：`finalize_endpoint` 用 `slice(0,N+1)` 生成的
`ledger_energy` 长度是 `N+1`，每个 `ledger_*_steps` 长度是 `N`，它们全部是第一周期
sidecar；本合同禁止假设其长度为 `2N`，也禁止对它们做 `N:2N` 切片。

production ledger 唯一方案是新验证层固定导入
`paper2_hybrid.numerics._loads_for_endpoint` 与
`paper2_hybrid.numerics.discrete_ledger`：先以完整 `states.shape=(state_size,2N+1)` 生成
确定性 two-cycle loads，再把 `state[:,N:2N+1]`、`activation[N:2N+1]` 和
`loads[:,N:2N+1]` 传给 `discrete_ledger`。所得 production energy 必须精确 shape
`(N+1,)`，每个 production step array 必须精确 shape `(N,)`，再把这 N 步保守映射到
256 个中心化 bins。

上述两个私有/公开符号的固定导入路径、签名与 `numerics.py` SHA 属于实现锁；任一漂移
立即 `MISSING_VALIDATION_INTERFACE_FAIL`，不得复制一套未校验 load 公式替代。测试必须
对 P0 只取 G0 S2/T64，对 A2/LN/LS/C0/CQ 取其冻结的 N=64/128/256 端点：使用
`_loads_for_endpoint` 重算第一周期 ledger，
并把每个 energy/step array 与现有 first-cycle ledger 逐元素比较；随后独立验证第二周期
energy/step shape、周期平移和 exact ledger 闭合。任一不符立即
`SOURCE_OR_PROTOCOL_DRIFT_FAIL` 或
`POWER_LEDGER_FAIL`。

ECM 峰值点摘要固定来自第二周期节点 `N+N/2`；ECM 周期积分/范数来自第二周期
`N:2N` 或第二周期重算步区间。\(\chi_D\) 只用第二周期重算的 drag/SLS 周期和。
能量 G7 对照可读两周期节点；正式能量/功率只用第二周期。

## 4. B2 — N1 确定性制造探针

### 4.1 seed、坐标和归一化

唯一 seed 基值为 `20260904`，随机生成器固定为 NumPy `PCG64`。每个 level/task 的 seed
为 `20260904 + 100*level_code + task_code`，其中 S2/S3/S4 的 `level_code=2/3/4`，
`task_code` 固定为 active=1、interface=2、spectrum=3。禁止 Python `hash()` 派生 seed。

连续体用 (X=x/L\in[-1/2,1/2])、(Y=y/h\in[0,1])。制造位移固定为

\[
u_x=10^{-4}(2X+0.25Y),\qquad
u_y=10^{-4}(-X+1.5Y).
\]

离散链节点用同一 \(X_i\)，固定

\[
u_{n,x}=10^{-4}(1.25X_i),\qquad
u_{n,y}=10^{-4}(-0.5X_i+0.25).
\]

误差 numerator 为离散算子输出减解析输出的面积/长度加权 L2；denominator 为解析输出
同范数与对应 floor 的较大者。连续体、链 affine patch 分开记录，阈值均 `1e-10`。

### 4.2 SLS 制造

固定制造应变复幅
\(\widehat\epsilon=10^{-4}(1,-0.5,0.25)^T\)，DC 应变唯一取
\(\epsilon_0=10^{-4}(1,-0.5,0.25)^T\)，并使用
\(z_0=\epsilon_0\)。离散谐波使用当前 CN 因子

\[
\widehat z=
\frac{\tfrac12(1+\zeta)}{\tau(\zeta-1)/\Delta t+\tfrac12(1+\zeta)}
\widehat\epsilon,
\qquad \zeta=e^{i2\pi/N},
\]

并在 N=64/128/256 分别检查，不与连续时间解比较。DC 与离散谐波相对误差均
`le 1e-10`。

### 4.3 主动共轭与作用反作用

主动测试状态由相应 active seed 的 `standard_normal(state_size)` 生成，除
`ecm_internal_slice` 乘 `1e-4`、其余分量乘 `1e-3`，宏观应变分量在归一前覆盖为
`1e-4`，随后对完整向量固定欧氏归一使 `norm(q)=1e-3*sqrt(state_size)`。激活点
`a_star=0.037`，方向为激活标量正方向 `+1`。

中心差分步长唯一列表为
`activation_peak * [1e-4,3e-5,1e-5,3e-6,1e-6]`。每个步长都报告

\[
e_h=\frac{|[\Psi(q,a+h)-\Psi(q,a-h)]/(2h)-\partial_a\Psi(q,a)|}
{\max(|\partial_a\Psi|,10^{-12}S_W/a_0)}.
\]

`platform_best_error` 唯一定义为上述五个预注册值的数值最小值；禁止增加步长或删点，
阈值 `le 1e-7`。界面 action–reaction 探针用对应 level 的 interface seed 初始化 PCG64，
生成 `standard_normal(state_size)`；macro 与全部 z 分量覆盖为 0，只保留第 5.1 节冻结的
三个位移块。令 `n_displacement=n_m+n_e+n_n`，把完整位移子向量按欧氏范数唯一归一到
`1e-3*sqrt(n_displacement)`，归一前零范数立即 `STATIC_OR_MANUFACTURED_FAIL`。两界面必须
使用同一个冻结状态。

对每个界面，分别以 `interface_weights[i]` 对 ECM 侧和对侧物理节点力求和成二维向量
\(F_e,F_o\)，误差唯一为
\(\|F_e+F_o\|_2/\max(\|F_e\|_2+\|F_o\|_2,10^{-12}S_f)\)，两界面各自必须
`le 1e-12`，不得先合并或以未加权节点和替代。

## 5. B2 — N2 确定性谱与惯性算法

### 5.1 缩放与已知平移模

对需缩放实对称矩阵 \(A\)，取 \(D=\operatorname{diag}(A)>0\)，
\(\widehat A=D^{-1/2}AD^{-1/2}\)。S2/S3/S4 都执行。

块边界不得由矩阵零模式反推。唯一取
`n_m=system.myocardium_mesh.periodic_projection.shape[1]`、
`n_e=system.ecm_mesh.periodic_projection.shape[1]`、`n_n=2*level.nx`；三个位移块依次为
`[0,n_m)`、`[n_m,n_m+n_e)`、`[n_m+n_e,n_m+n_e+n_n)`，macro 标量必须位于
`system.macro_strain_index`，SLS z 必须精确为 `system.ecm_internal_slice`。三个块长度必须均为
偶数，且 macro index、z 起点和 `state_size` 必须与上述边界连续一致，否则
`MATRIX_INERTIA_FAIL`。

在全局状态坐标中，x 平移向量在上述三个块各自的偶数局部索引置 1，y 平移向量在各块
各自的奇数局部索引置 1；另一分量、macro strain 和全部 SLS z 均置 0。缩放坐标向量为
\(D^{1/2}r_x,D^{1/2}r_y\)，以固定 x 后 y 顺序 modified Gram–Schmidt 两遍正交归一成
\(U\)。必须检查
`norm(Ahat@U)_F/(max(lambda_max,1e-30)*norm(U)_F) le 1e-10` 和与目标全场平移的回代
残差 `le 1e-10`。

完整未缩放 `Ks` 先检查对角线：任一 `diag(Ks)<0.0` 立即
`MATRIX_INERTIA_FAIL`；支撑 DOF 集唯一为
\(J_s=\{i:\operatorname{diag}(K_s)_i>0.0\}\)，支撑子空间矩阵只取主子矩阵
`Ks[J_s,J_s]` 后再按其正对角缩放。完整 `Ks` 的无量纲负谱尺度唯一为
\(S_K=\max(|\lambda_{SA,\min}|,|\lambda_{LM}|,10^{-30})\)，其中两项来自下表
完整未缩放 `Ks` 的 SA 与 LM 调用，\(\lambda_{LM}\) 是 `which="LM"` 返回的唯一最大模
特征值；负谱判据使用 \(\lambda_{SA,\min}/S_K\)。

### 5.2 eigensolver 固定表

统一使用 `scipy.sparse.linalg.eigsh`、`tol=1e-11`、`maxiter=200000`。记
\(\widehat K_{mat}=D_{mat}^{-1/2}K_{mat}D_{mat}^{-1/2}\)。基础 `v0` 来自 spectrum seed
的 `standard_normal(n)`：\(\widehat K_{mat}\) 的未投影 SA/SM/LA 调用先加
`0.1*(U[:,0]+sqrt(2)*U[:,1])` 后归一以保证与已知零模有重叠；补空间调用才投影掉 U；
无 U 的矩阵直接归一。每个 Ritz 对记录
`norm(Ahat*v-lambda*v)_2/max(norm(Ahat)_F*norm(v)_2,1e-30)`，必须 `le 1e-8`；ARPACK 未收敛、
返回数不足或非有限即 `MATRIX_INERTIA_FAIL`。

| 对象/目的 | k | which | 唯一判据 |
|---|---:|---|---|
| `Khat_mat` 负谱 | 6 | `SA` | 最小代数值 `ge -1e-10`；与零模计数分开 |
| `Khat_mat` 零模计数 | 8 | `SM` | `abs(lambda) le 1e-10*lambda_max` 恰有 2 个 |
| `Khat_mat` 最大值 | 1 | `LA` | 定义正的 `lambda_max` |
| `Khat_mat+2*lambda_max*U*U.T` 补空间 | 3 | `SA` | 三个值均 `gt 1e-12*lambda_max` |
| 完整未缩放 `Ks` 负谱 | 6 | `SA` | `lambda_min/max(max_abs_lambda,1e-30) ge -1e-10` |
| 完整未缩放 `Ks` 尺度 | 1 | `LM` | 定义上一行 `max_abs_lambda` |
| 支撑 DOF 子空间缩放 `Ks` | 3/1 | `SA/LA` | 归一最小值 `ge -1e-10`，记录设计核，不要求全空间 SPD |
| `widehat(Kmat+Ks)` | 3/1 | `SA/LA` | `lambda_min/lambda_max gt 1e-12` |
| `Ghat` | 3/1 | `SA/LA` | `lambda_min/lambda_max gt 1e-12` |

若矩阵维数 `n<=k+1`，唯一 fallback 为 `scipy.linalg.eigh` 全谱；不得换另一稀疏算法。
`Kmat` PSD 的负谱检查与 `SM` 零模计数都唯一在 `Khat_mat` 上执行并必须各自通过；禁止
把缩放坐标的 U 加到未缩放 `Kmat`，也禁止用最小模结果推断无负值。
复谐波矩阵不进入 SPD 表，只过 N3 可逆性、残差和后向误差。

## 6. B3 — machine QoI、源字段、reduction 与参考方向

### 6.1 machine registry

下表每一行是不可省略的 machine key 族；x/y、两界面、能量分量和 work channel 必须
展开成独立记录，不得用合并范数掩盖单项失败。

| machine key | 唯一核心源/派生 | 单位尺度 | 时间/空间 reduction | floor 类 | 适用门与参考方向 |
|---|---|---|---|---|---|
| `shortening.waveform` | `limited_shortening_two_cycles[N:2N]` | \(S_\epsilon\) | DC+基频解析到 256 bin；时间 L2 | strain | N4: S3 T128→T256，T64 只给阶；N5: T128 S3→S4，S2 给收缩；G4a: S4/T256 |
| `shortening.fundamental_amplitude` | 同上固定 DFT | \(S_\epsilon\) | `abs(qhat)` 标量；qhat 已含 `2/N` | strain | N4/N5/G4a，同上 |
| `shortening.phase` | 同上与固定输入基频 | rad | wrapped `atan2` | parent amplitude | N4/G4a；参考见 6.3 |
| `endo.displacement.{x,y}.waveform` | `mean_endocardial_*_displacement_two_cycles[N:2N]` | \(S_u\) | 256 解析 bin、时间 L2 | displacement | N4/N5/G4a；同一参考 |
| `interface.{me,ne}.traction_on_ecm.{x,y}` | 两 traction 源 reshape 后第 7 节映射 | \(S_t\) | 空间解析到 128 × 相位解析到 256；公共 L2 | traction | G5: T128 S3→S4，S2 给收缩；G4b: S4/T256；S1 同结构 |
| `interface.{me,ne}.force_on_ecm.{x,y}` | 上一公共场乘 `dx=L/128` 求和 | \(S_f\) | 每 bin 合力及时间 L2 | force | N4/N5/G4a；G5 守恒；S4/T256 参考 |
| `ecm.strain_l2` | 第二周期 state→`ecm_transform`→`ecm_strain_operator_full` | \(S_\epsilon\) | 单元面积加权 L2；第二周期时间 L2 | strain | N4/N5/G4a |
| `ecm.internal_z_l2` | `state[ecm_internal_slice,N:2N]` | \(S_\epsilon\) | 单元面积加权 L2；第二周期时间 L2 | strain | N4/N5/G4a/G7 |
| `ecm.stress_l2` | strain、z 与两冻结 constitutive matrices | \(S_t\) | 单元面积加权 L2；第二周期时间 L2 | traction | N4/N5/G4a |
| `ecm.maximum_von_mises_proxy` | 第二周期 ECM stress | \(S_t\) | 每节点/单元先 proxy，再取周期最大 sidecar | traction | N4/N5/G4a；名称不得去掉 proxy |
| `energy.{myo,ecm_eq,ecm_ve,endo,interface,support,material}` | state、active 与 `component_matrices` 的精确二次/双线性分解 | \(S_W\) | 第二周期节点波形；周期积分/端点差 | energy | N4/N5/G4a/G6/G7 |
| `work.{active,lumen,support}.cycle` | 第二周期 production ledger | \(S_W\) | N 个 step 求和 | energy | N4/N5/G4a/G6 |
| `dissipation.{drag,sls}.cycle` | 第二周期 production ledger | \(S_W\) | N 个 step 求和及逐步最小值 | energy | N4/N5/G4a/G6 |
| `ledger.{equilibrium_defect,residual}` | 第二周期 production ledger | \(S_W\) | 逐步最大相对值与周期和 | energy | G6 |
| `solver.{dc,harmonic}.relative_residual` | `direct_solver_assurance` 数值字段；忽略其 v08 pass boolean | 1 | 同端点最大值 | residual | 每端点 N3；参考自身 RHS |
| `solver.{dc,harmonic}.backward_error` | 同上数值字段 | 1 | 同端点最大值 | residual | 每端点 N3 |
| `periodicity.{state,traction,energy}` | cycle1 `0:N` 对 cycle2 `N:2N` | 1 | 相同权重归一 L2 | parent QoI | G7；闭合节点另记 |
| `s1.chi_D` | 第二周期 `D_sls/(D_sls+D_drag)` | 1 | 周期标量 | energy denominator | S1-G4a；S4/T256 参考 |
| `s1.hotspot` | `-traction_on_ecm[me,x,:,phase128]` | \(S_t\) | 128 段集合/峰值 | traction | 只比较 S3/T256→S4/T256 |

`free_shortening_two_cycles` 只登记为 `prescribed_input_comparator`，不是求解输出。现有
`Endpoint.summary` 的 peak/hotspot 只作 sidecar，不能替代本表量。

令 \(q\) 为完整状态、\(a\) 为激活，\(h=\mathtt{active\_vector\_h}\)、
\(c=\mathtt{active\_scalar\_c}\)。能量映射与公式唯一为

\[
\begin{aligned}
\Psi_m&=\tfrac12q^TK_{myo}q+a h^Tq+\tfrac12ca^2,\\
\Psi_{e,eq}&=\tfrac12q^TK_{ecm,eq}q,\qquad
\Psi_{e,ve}=\tfrac12q^TK_{ecm,ve}q,\\
\Psi_n&=\tfrac12q^TK_{endo}q,\qquad
\Psi_I=\tfrac12q^T(K_{int,me}+K_{int,ne})q,\\
\Psi_s&=\tfrac12q^TK_{support}q,\qquad
\Psi_{mat}=\Psi_m+\Psi_{e,eq}+\Psi_{e,ve}+\Psi_n+\Psi_I.
\end{aligned}
\]

其中各 \(K\) 依次精确来自 `component_matrices["myocardium"]`、
`["ecm_equilibrium"]`、`["ecm_viscoelastic"]`、`["endocardium"]`、
`["interface_myocardium_ecm"]`、`["interface_endocardium_ecm"]` 与 `["support"]`。
`interface` machine key 保存 \(\Psi_I\)，`material` 排除 support 且包含主动双线性和主动
标量项；每个节点必须检查 \(\Psi_{mat}\) 与核心 `_material_energy(system,q,a)` 在舍入容差内
相等。功率账本仍使用 `discrete_material_energy_increment` 的精确中点增量，不得用端点总能差
替代。

对 `ecm.strain_l2`、`ecm.internal_z_l2` 与 `ecm.stress_l2`，令 \(X_{c,n}\) 为相应单元三
分量量、\(A_c\) 为 `ecm_mesh.cell_areas[c]`、\(\Delta t=T/N\)，唯一第二周期时空范数为

\[
\|X\|_{L^2(\Omega_e\times T)}=
\sqrt{\Delta t\sum_{n=N}^{2N-1}\sum_c A_c\|X_{c,n}\|_2^2}.
\]

`maximum_von_mises_proxy` 仍先逐单元逐节点计算 proxy，再按 registry 取最大值，不改为
上述 L2。

### 6.2 P0 真零噪声与跨层聚合

P0 是 formal index 0 的 S2/T64 真零控制，并在 G0 生成；它是 formal 记录但不是独立动态
API 调用。G0 的 S2/S3/S4 零控制统一固定 `N=64`，各自构造一次系统，共 3 个系统、6 次
真实零求解；严禁调用 `simulate_endpoint(...,"P0",...)` 或复用 `model.py` 的 P0 直接置零
分支。对每一层：

1. 取 \(A=\mathtt{system.matrix\_a}\)、\(G=\mathtt{system.matrix\_g}\)、
   \(b_{dc}=0\)、\(b_{\omega}=0\)，以实际 direct factorization/solve 求
   \(Aq_{dc}=b_{dc}\)；
2. 固定 \(\zeta=\exp(i2\pi/64)\)、\(\Delta t=T/64\)，构造与核心完全相同的
   \(H=((\zeta-1)/\Delta t)G+\tfrac12(1+\zeta)A\)，再以实际 complex direct
   factorization/solve 求 \(H\widehat q=\tfrac12(1+\zeta)b_\omega\)；
3. 在 129 个节点 \(t_j=j\Delta t\) 上构造
   \(q_j=q_{dc}+\Re(\widehat q\exp(i2\pi j/64))\)，activation 与 load 节点数组全零；
4. 以与动态端点完全相同的观测、ECM/界面场提取、第二周期 `64:128`、中心化相位解析
   平均、空间 P0、生产 ledger 与 reduction 路径生成零控制量，并执行相同 shape、有限性、
   能量分解和方向检查。

G0 由此生成 \(N_Q^{S2},N_Q^{S3},N_Q^{S4}\)。其中 S2/T64 对象还唯一填入 formal index
0 的六个 NPZ slice，且 `formal_native_steps_per_cycle[0]=64`；S3/S4 对象不进入 formal
NPZ 或端点计数。零 RHS 的 N3 只用绝对 residual 与解范数
floor，不能用相对 RHS 分母；六次 solve 的 factorization/solve 证据必须写入 G0 审计。
每个 machine key 的噪声唯一为

\[
N_Q=\max(N_Q^{S2},N_Q^{S3},N_Q^{S4}),\qquad
F_Q=\max(10^{-12}S_Q,10N_Q).
\]

- 标量取绝对值；
- 256-bin 波形取 Δt 加权 L2；
- 128×256 场取 ΔxΔt 加权 L2；
- 合力波形取 Δt 加权 L2；
- 周期积分/能量取绝对值；x/y 和两界面分别聚合；
- phase、\(\chi_D\) 与 hotspot 不另造零值，分别使用父幅值、energy denominator 和
  traction floor 的适用前提。

不得用 `1e-30`、非零病例、S1 或观察到的最小非零值定义 floor。全部 \(N_Q\)、\(F_Q\)
及三层贡献在 G1 前冻结并进入 protocol digest。

### 6.3 相位、低幅与比较参考

相位只在输入和输出基频幅值均 `gt 10*F_Q` 时定义；否则写
`PHASE_UNDEFINED_LOW_AMPLITUDE`。A2 参考主动输入，LN 参考法向载荷，LS 参考切向载荷，
C0/CQ 参考主动时钟并另记法向载荷相位，S1 参考主动输入。C0/CQ 不称单输入传递函数。

通用参考唯一为：N4 用 S3/T256；N5 用 S4/T128；G4a/G4b 用 S4/T256；G5 空间场收缩
用 S4/T128；S1 terminal time/space 与 mixed 均用 S4/T256。低于 floor 时不计算相对误差
或观察阶，只允许绝对差 `le F_Q`。

G7 的周期一致性不复用通用 QoI 误差。令 `state_size=m`，状态逐自由度缩放向量唯一为：
三个 displacement block 取 \(S_u\)，macro strain 与全部 z 分量取 \(S_\epsilon\)。若
\(\widetilde q=q/S\)，两周期半开状态误差为

\[
E_q=\frac{\sqrt{N^{-1}\sum_{j=0}^{N-1}
\|\widetilde q_j-\widetilde q_{N+j}\|_2^2}}
{\max(\sqrt{N^{-1}\sum_{j=0}^{N-1}\|\widetilde q_{N+j}\|_2^2},
10^{-12}\sqrt m)}.
\]

牵引对每个界面和 x/y 分量分别计算
\(\sqrt{\Delta t\sum_{j=0}^{N-1}\sum_iw_i
(t_{i,j}-t_{i,N+j})^2}\)，分母为第二周期同范数与
\(F_t\sqrt{LT}\) 的较大者。能量对 `myo/ecm_eq/ecm_ve/endo/interface/support/material`
逐分量计算 \(\sqrt{\Delta t\sum_{j=0}^{N-1}(\Psi_j-\Psi_{N+j})^2}\)，分母为第二
周期同范数与 \(F_W\sqrt T\) 的较大者。不得先合并界面、分量或能量项。

节点闭合另对 `(0,N)`、`(N,2N)`、`(0,2N)` 三对逐项记录：状态用相同逐自由度缩放后
的欧氏误差和 `max(reference,1e-12*sqrt(m))` 分母；牵引用界面权重空间 L2 和
`max(reference,F_t*sqrt(L))`；每个能量分量用绝对差和 `max(reference,F_W)`。半开周期
误差和全部节点闭合误差均须 `le 1e-10`。

## 7. B4 — ECM 侧物理牵引、功率与热点映射

### 7.1 唯一侧别

| 界面 | 核心 reported 源 | NPZ 保存的 ECM 侧物理力 | 对侧物理力 |
|---|---|---|---|
| 心肌–ECM | `myocardium_ecm_traction_two_cycles` = \(t_{me}^{rep}\) | \(t_{m\to e}=t_{me}^{rep}\) | 心肌受力 \(t_{e\to m}=-t_{m\to e}\) |
| 心内膜–ECM | `endocardium_ecm_traction_two_cycles` = \(t_{ne}^{rep}\) | \(t_{n\to e}=t_{ne}^{rep}\) | 心内膜受力 \(t_{e\to n}=-t_{n\to e}\) |

NPZ key 只能使用 `traction_on_ecm`/`force_on_ecm`，禁止 `reported_side` 无侧别名称。
合力由保存的 ECM 侧场积分；Figure 2 箭头和图例使用上表方向。S1 压缩热点固定为
\(t_{e\to m,x}=-t_{m\to e,x}\)，即 NPZ 心肌–ECM x 分量取负。

### 7.2 界面功率守恒审计

每个原生步先取端点牵引的算术中点 \(t^{mid}\) 和两侧边界位移增量。心肌–ECM 唯一为
\(W_e=\sum_iw_i t_{m\to e,i}^{mid}\cdot\Delta u_{e,i}\)、
\(W_m=\sum_iw_i(-t_{m\to e,i}^{mid})\cdot\Delta u_{m,i}\)，并检查
\(W_e+W_m+\Delta\Psi_{I,me}=0\)。心内膜–ECM 唯一为
\(W_e=\sum_iw_i t_{n\to e,i}^{mid}\cdot\Delta u_{e,i}\)、
\(W_n=\sum_iw_i(-t_{n\to e,i}^{mid})\cdot\Delta u_{n,i}\)，并检查
\(W_e+W_n+\Delta\Psi_{I,ne}=0\)。这里每个 \(\Delta\Psi_I\) 是对应二次 penalty 能在该步
两端的精确差。

必须先在每个原生空间—时间单元按上述符号积分，再映射到公共 bins；禁止“平均牵引 ×
平均速度”。两侧总功与 penalty 能量增量的离散恒等式、原生—公共周期和相对误差均记录，
阈值 `le 1e-10`。

### 7.3 公共空间、相位与步映射

空间公共边界固定为 `linspace(-L/2,L/2,129)`；原生分片线性场与每个目标段逐交点解析
积分，即使 S2/S3→128 是目标更细也不得复制节点值。常量/线性制造与合力误差
`le 1e-12`。

只对 machine registry 中 `single_frequency_eligible` 的
`shortening.waveform`、两个 `endo.displacement` 波形和两界面两分量 traction（以及由
traction 积分的 force）使用第二周期半开节点 `N:2N` 恢复

\[
Q_0=N^{-1}\sum_{n=0}^{N-1}Q_n,\qquad
\widehat Q_1=2N^{-1}\sum_{n=0}^{N-1}Q_ne^{-i2\pi n/N}.
\]

上述 eligible 量的高次 Fourier 能量或 DC+基频重建误差高于对应 floor 即
`UNEXPECTED_HIGHER_HARMONIC_FAIL`。256 个周期中心化 P0 段唯一使用

\[
Q_j=Q_0+\operatorname{Re}\!\left[
\widehat Q_1e^{i\omega jT/256}
\frac{2\sin(\omega T/512)}{\omega T/256}\right].
\]

能量、von Mises proxy、空间范数和 step-integral channels 不属于 single-frequency
eligible，不得强行丢弃其高次成分；它们按 machine registry 的原生第二周期 reduction。
禁止端点/中心点/FFT 重采样值替代解析平均。第二周期 N 个 production step integrals
先除以 Δt 成分段常量密度，再与 256 个目标段周期交叠积分；`I0` 拆为
`[0,T/512)` 与 `[T-T/512,T)`，所有 bins 之和相对误差 `le 1e-10`。

## 8. N1–N11 阈值、适用门与 FAIL 标签

| 规则 | 机器硬门 | 主要阶段 | FAIL 标签 |
|---|---|---|---|
| N1 | assembly/affine/SLS `le 1e-10`；active `le 1e-7`；symmetry/action-reaction `le 1e-12` | G0 | `STATIC_OR_MANUFACTURED_FAIL` |
| N2 | Kmat PSD `min ge -1e-10` 且恰 2 平移零模；Kmat+Ks/G scaled ratio `gt 1e-12`；Ritz `le 1e-8` | G0 | `MATRIX_INERTIA_FAIL` |
| N3 | 非零 RHS residual `le 1e-10`；backward `le 1e-12`；零 RHS 绝对 floor | 每个端点 | `ALGEBRAIC_FAIL` |
| N4 | T128–T256 `le 2e-3`；phase `le 1e-2 rad`；误差下降；适用时 order `ge 1.5` | G2/S1 | `TIME_DISCRETIZATION_FAIL`/`S1_HOLDOUT_FAIL` |
| N5 | S3–S4 global `le 2e-2`；适用时 `e34 le 0.8*e23` | G3/S1 | `SPACE_DISCRETIZATION_FAIL`/`S1_HOLDOUT_FAIL` |
| N6 | fine-reference mixed `le 0.5*max(et,es,1e-12)` | G4a/G4b/S1 | `G4A_MIXED_FAIL`/`G4B_FIELD_MIXED_FAIL`/`S1_HOLDOUT_FAIL` |
| N7 | 128×256；manufacture `le 1e-12`；force/work `le 1e-10`；field `d2 le 5e-2` 且适用时 `d34 le 0.8*d23` | G5/S1 | `COMMON_PROJECTION_FAIL`/`S1_HOLDOUT_FAIL` |
| N8 | range `gt 10Ft`、coverage `le 25%`；S3/T256→S4/T256 Hausdorff `le L/32`、Jaccard `ge 0.5`、amplitude `le 5e-2` | S1 | 退化只写 `HOTSPOT_DEGENERATE`；非退化失败 `S1_HOLDOUT_FAIL` |
| N9 | ledger-minus-equilibrium `le 1e-10`；step/cycle `le 1e-8`；dissipation `ge -1e-12*S_W` | G6/S1 | `POWER_LEDGER_FAIL`/`S1_HOLDOUT_FAIL` |
| N10 | two-cycle state/traction/energy `le 1e-10`，标 by-construction | G7/S1 | `PERIODIC_CONSISTENCY_FAIL`/`S1_HOLDOUT_FAIL` |
| N11 | 单 CPU、8 GiB、3600 s、无网络/GPU/socket、正式量有限 | FINAL | `RESOURCE_LIMIT_FAIL`/`NONFINITE_OUTPUT_FAIL` |

N4 观察阶仅在两级原始差均 `gt 10F_Q` 时适用；低于 floor 用绝对门。S1
\(\chi_D=D_{SLS}/(D_{SLS}+D_{drag})\) 只在分母 `gt F_W` 时定义，否则写
`CHI_D_UNDEFINED_LOW_DISSIPATION`，不强置 0/1。定义时检查 terminal time `le 2e-3`、
terminal space `le 2e-2` 与 N6 mixed。热点稳定性**只**比较 S3/T256 与 S4/T256；
T128 只进入 S1 mixed difference，不进入热点 Hausdorff/Jaccard/amplitude。

## 9. B4 — holdout digest 与 FINAL NPZ 字节绑定

### 9.1 pre-holdout commitments

G7 PASS 后、任何 S1 对象建立前，runner 对 36 个 formal endpoint 分别冻结以下 slice：

```text
limited_shortening_p0[endpoint,:]
mean_endocardial_displacement_p0[endpoint,:,:]
traction_on_ecm_p0[endpoint,:,:,:,:]
force_on_ecm_p0[endpoint,:,:,:]
step_integrals_overlap_p0[endpoint,:,:]
native_steps_per_cycle[endpoint]
```

每个 slice 内容 SHA 定义为
`sha256(b"array-v1\\0" || dtype.str || b"\\0" || canonical_shape_json || b"\\0" ||
C_contiguous_bytes)`。`pre_holdout_digest.json.formal_array_commitments` 必须按 36 个 endpoint
id × 6 个 key 形成 216 条排序记录，并另锁公共坐标轴内容 SHA、machine registry、floor、
阈值、DAG、源文件、实现文件、开发 JSON 和环境。

digest 以独占写入关闭并 fsync 后，从磁盘重读、重算全部输入；一致后才允许 S1。任何
差异即 `HOLDOUT_RULE_DRIFT_FAIL`，同一 run 不得再次解盲。

### 9.2 FINAL 反向核对

FINAL 写 `common_observables.npz` 后必须用 `allow_pickle=False` 重读。对六个 formal key
的 36 个 endpoint slice 逐条按同一算法复算，必须与 pre-holdout 的 216 条 commitment
逐字节一致；公共坐标轴也必须一致。S1 keys 可以新增，但 formal slice 不得因 concatenate、
dtype cast、轴重排或压缩前复制而变化。

任一不一致立即 `HOLDOUT_RULE_DRIFT_FAIL`，不得写候选 PASS。这样 digest 锁定的是最终
交付 NPZ 中的 formal 数组字节，而不是仅锁运行时声明。

## 10. NPZ 精确 schema 与物理方向

### 10.1 坐标/轴 keys

| key | shape | dtype |
|---|---:|---|
| `formal_endpoint_id` | `(36,)` | `<U24` |
| `s1_endpoint_id` | `(4,)` | `<U24` |
| `space_edges` | `(129,)` | `float64` |
| `space_centers` | `(128,)` | `float64` |
| `phase_centers` | `(256,)` | `float64` |
| `phase_bin_start_unwrapped` | `(256,)` | `float64` |
| `phase_bin_stop_unwrapped` | `(256,)` | `float64` |
| `interface_code` | `(2,)` | `int8` |
| `component_code` | `(2,)` | `int8` |
| `step_channel_code` | `(8,)` | `int8` |

`interface_code=[0,1]` 唯一映射为 `[myocardium_ecm,endocardium_ecm]`，且两者都表示 ECM
侧物理力；`component_code=[0,1]` 为 `[x,y]`。中心坐标只作标签，不是采样值。

### 10.2 formal keys

| key | shape | dtype |
|---|---:|---|
| `formal_limited_shortening_p0` | `(36,256)` | `float64` |
| `formal_mean_endocardial_displacement_p0` | `(36,2,256)` | `float64` |
| `formal_traction_on_ecm_p0` | `(36,2,2,128,256)` | `float64` |
| `formal_force_on_ecm_p0` | `(36,2,2,256)` | `float64` |
| `formal_step_integrals_overlap_p0` | `(36,8,256)` | `float64` |
| `formal_native_steps_per_cycle` | `(36,)` | `int16` |

### 10.3 S1 keys

| key | shape | dtype |
|---|---:|---|
| `s1_limited_shortening_p0` | `(4,256)` | `float64` |
| `s1_mean_endocardial_displacement_p0` | `(4,2,256)` | `float64` |
| `s1_traction_on_ecm_p0` | `(4,2,2,128,256)` | `float64` |
| `s1_force_on_ecm_p0` | `(4,2,2,256)` | `float64` |
| `s1_step_integrals_overlap_p0` | `(4,8,256)` | `float64` |
| `s1_native_steps_per_cycle` | `(4,)` | `int16` |
| `s1_hotspot_traction_e_to_m_x` | `(4,128)` | `float64` |
| `s1_hotspot_mask` | `(4,128)` | `bool` |

step channels 固定为主动功、腔面功、支撑功、物质能增量、drag 耗散、SLS 耗散、平衡
缺陷功、ledger residual。`s1_hotspot_traction_e_to_m_x` 必须逐值等于
`-s1_traction_on_ecm_p0[:,0,0,:,128]`。

NPZ 用 `numpy.savez_compressed`，读取必须 `allow_pickle=False`；禁止 object、全状态、
系统矩阵、重复周期、逐单元 ECM 全场和对侧重复力。压缩后 `le 128 MiB`。每 key 记录
shape、dtype、单位、侧别、内容 SHA；缺/多 key、错 shape/dtype、非有限或超限即
`ARRAY_CONTRACT_FAIL`。

## 11. B5 — create-only 父目录与阶段事务

### 11.1 HOST_CREATE 唯一顺序

宿主 monotonic 总计时在任何文件系统或 Git/镜像 precheck 前启动。随后固定：

1. 解析项目根必须精确为 `E:\Temp-Projects\PRL`，并验证 `results` 是项目内真实目录；
2. 若且仅若 `results/paper2_figure2/` 不存在，允许在项目内创建该一个父目录；若它是
   symlink/reparse point、解析越界或创建失败，立即停止；
3. 确认
   `results/paper2_figure2/fem_only_numerical_credibility_v03_20260904_r01/` 不存在；
4. 以 `mkdir(exist_ok=False)` 独占创建 r01 根，并立即独占写/fsync
   `host_create_lock.json`；
5. 只有根已留痕后，才检查 Git、源 SHA、实现锁、镜像 ID、资源和 container name；
6. 任一 precheck 失败都在 r01 内写 failure summary、inventory、ledger 和 root completion。

r01 已存在即 `OUTPUT_PATH_EXISTS_FAIL`，不得清空、覆盖、续接、移动或自动改 r02。所有
失败重试必须另立合同/run id。

### 11.2 子包与原子完成

固定子目录：`00_precheck`、`01_g0`、`02_g1`、`03_g2`、`04_g3`、
`05_g4_pipeline`、`06_g6_g7_digest`、`07_s1`、`08_final`。每个子包依次独占写
`stage_manifest.json`、阶段工件，最后写 `stage_complete.json` 或 `stage_failed.json`。

只有 complete 存在、依赖哈希匹配且 failed 不存在才算完成；缺 completion 的中断包为
`INCOMPLETE_TRANSACTION`，永不续跑。所有 host lock、`manifest_events.jsonl`、stage
manifest、complete/failed、JUnit 和正式 JSON/NPZ 都进入 inventory 与 ledger。

### 11.3 无循环 FINAL 顺序

根级 summary/inventory/ledger/completion 的唯一 owner 是同一宿主 runner。容器只写已到达
的阶段工件、容器内 resource snapshot，并仅在全部 S1 子门通过后独占创建候选
`common_observables.npz`、完成容器内 schema/有限性/第 9.2 节 216 项 commitment 校验，
随后退出；容器不得写根 summary、inventory、ledger 或 completion。宿主 `docker wait` 后
必须先完成第 13 节 `docker inspect`、宿主资源取证和 postlock，再只读重读 NPZ 并独立复核
schema/有限性/216 项 commitment，绝不第二次写或改 NPZ，随后才进入下列根级 FINAL。
若容器未启动或被 watchdog 停止，也由该宿主 runner 对当时已有工件封账。这样 Docker
退出状态与 postlock 进入 resource/provenance audit，而不会在 completion 之后补写证据。

FINAL 先按到达状态分为三个互斥入口，禁止失败路径伪造未到达阶段：

- **PASS path**：仅当 G0–G7、digest、全部 S1 子门、容器内 NPZ 校验、容器退出与隔离/
  resource、宿主 postlock 及宿主只读 NPZ 复核均已 PASS，宿主才写 `resource_audit.json`、
  `gate_summary.json` 和 `pass_summary.json`；
- **late FAIL path**：NPZ 路径已产生后的任一失败，包括 create/fsync/容器内或宿主 NPZ
  校验、Docker exit/OOM/inspect、resource、postlock 或后续封账前检查失败。任何已经实际
  产生的 NPZ 字节必须原样保留，禁止删除、覆盖或修补；不得写 `pass_summary.json`，而写
  对应首失败标签的 `failure_summary.json`，并把实际 NPZ、失败证据及此前全部工件纳入
  inventory/ledger；
- **early FAIL path**：在 NPZ 路径产生前的首次硬门失败后短路，不创建
  `common_observables.npz`、
  `pass_summary.json`，也不创建任何尚未真实到达的 S1 或后续阶段工件；只保留此前合法
  产生的实际工件，并写适用于已执行范围的 `resource_audit.json`、`gate_summary.json` 和
  `failure_summary.json`。若失败发生在 S1 内，只能登记失败前已经真实产生的 S1 工件。

三条路径随后共享且只执行一次以下无循环结尾：

1. 关闭并 fsync 最后一条 `manifest_events.jsonl`；此后不再追加；
2. 在内存生成确定性的 `root_completion.json` bytes；其内容只含 run id、PASS/FAIL、
   summary path、ledger path 和 `no_files_after_completion=true`，不含 ledger SHA；
3. 写 `artifact_inventory.json`：只列实际存在或已冻结待写的工件；它对自身只列 path 与
   role，不列自身 bytes/SHA，对 `hash_ledger.json` 只列 path 与
   `self_excluded_from_hash_ledger` role，对待写 `root_completion.json` 列精确
   path/bytes/SHA；
4. 实际写成 inventory 后计算其真实 bytes/SHA；对全部实际现有工件加上待写 completion
   的预计算 bytes/SHA 形成排序 ledger。ledger 必须包含 inventory 的实际哈希和 completion
   的预计算哈希，且唯一排除自身 `hash_ledger.json`，随后独占写 ledger；
5. 最后独占写预先冻结的 `root_completion.json` bytes，不再写任何文件；
6. 只读复算 completion SHA、ledger、inventory 与全目录；PASS 路径一致才允许 exit 0，
   late/early FAIL 路径一致后仍以对应非零 stop code 退出。

因此 ledger 能覆盖最后 completion，而 completion 不反向包含 ledger SHA，没有循环依赖。
自检失败时退出非零，已有 summary 不构成完整 PASS；禁止再写第二 summary 修补。

### 11.4 根正式工件

PASS 根正式工件至少包括：`host_create_lock.json`、`manifest.json`、`manifest_events.jsonl`、
`provenance.json`、`case_matrix.json`、`g0_static_manufactured.json`、
`algebraic_audit.json`、`convergence_audit.json`、`projection_audit.json`、
`g4b_field_mixed_audit.json`、`g4_total_adjudication.json`、`power_audit.json`、
`periodic_audit.json`、`pre_holdout_digest.json`、`s1_holdout_audit.json`、
`resource_audit.json`、`gate_summary.json`、`common_observables.npz`、一个 summary、
`artifact_inventory.json`、`hash_ledger.json`、`root_completion.json` 和全部子包工件。

late/early FAIL 根工件只要求第 11.3 节规定的实际已到达工件、failure summary、inventory、
ledger 与 completion，不得拿 PASS 清单反向补造文件。三条路径的 inventory 都必须逐项
解释工件角色，并与全目录严格相等。

JSON 必须 UTF-8、排序键、禁止 NaN/Infinity/重复键；ledger 不自哈希。运行结束后任何
工件变化都使事务失效。

## 12. 容器、TMPDIR 与非删除式超时

### 12.1 镜像与唯一命令参数

本地 tag 固定 `dolfinx/dolfinx:v0.11.0`。启动前只读
`docker image inspect` 的 image ID 必须精确等于
`sha256:2ae4bfbc0d9077268880faf04c72750528bee986c94ab223a2c159969bd56fa8`；不符即
`CONTAINER_ID_MISMATCH_FAIL`，不得 pull 或把 image ID 当 registry digest。

```text
docker run
  --name paper2-figure2-nc-v03-r01
  --network none
  --cpus 1
  --memory 8g
  --memory-swap 8g
  --pids-limit 256
  --read-only
  --cap-drop ALL
  --security-opt no-new-privileges
  --tmpfs /root/.cache:rw,exec,nosuid,size=2g
  --mount type=bind,source=E:\Temp-Projects\PRL,target=/workspace,readonly
  --mount type=bind,source=E:\Temp-Projects\PRL\results\paper2_figure2\fem_only_numerical_credibility_v03_20260904_r01,target=/output
  --workdir /workspace
  --env TMPDIR=/root/.cache/tmp
  --env OMP_NUM_THREADS=1
  --env OPENBLAS_NUM_THREADS=1
  --env MKL_NUM_THREADS=1
  --env NUMEXPR_NUM_THREADS=1
  --env PYTHONDONTWRITEBYTECODE=1
  dolfinx/dolfinx:v0.11.0
  python3 scripts/run_paper2_figure2_fem_only_numerical_credibility_v01.py
    --inside-container --project-root /workspace --output-root /output --run-id r01
    --implementation-lock /workspace/project_control/paper2_figure2_fem_only_numerical_credibility_implementation_lock_v01.json
```

Docker socket 不挂载，不出现 GPU 参数。唯一持久可写挂载是本次 r01；JIT/pytest 临时
文件只在 tmpfs。容器入口在导入 Python/FEniCSx 前独占创建 `/root/.cache/tmp`，并核对
`TMPDIR` 指向该目录。容器不自动删除，停止后保留；清理必须另获人类批准。

### 12.2 3600 秒宿主 watchdog

watchdog 以 HOST_CREATE 前启动的 monotonic 起点计时。总耗时达到 3600 秒时，宿主只对
精确名称 `paper2-figure2-nc-v03-r01` 执行
`docker stop --time 30 paper2-figure2-nc-v03-r01`，随后 `docker wait` 并以
`docker inspect` 确认不再运行。禁止自动删除、prune 或重试。

容器停止后，宿主同一 runner 才可在 r01 内写 `host_timeout.json`，并按第 11.3 节为已有
工件完成 FAIL inventory/ledger/completion。任何宿主 FINAL 前已经存在的
`root_completion.json` 都是 provenance/transaction violation：保留现有字节，不覆盖、
不继续正常封账并以非零退出。若容器根本未创建（包括 prelaunch failure），`docker wait`/
`docker inspect` 明确记为 NOT_APPLICABLE，不能以容器不存在覆盖已冻结的首失败标签。
超时统一 `RESOURCE_LIMIT_FAIL`，后台计算不得继续。

## 13. 确定性资源上界

历史 v08 六个 S4/T64 各 `25.74–26.05 s`，总 `189.14686104100838 s`，峰值
`0.7554397583007812 GiB`，只作预算锚点，不作 Figure 2 PASS。

本合同不采用统计型资源上界，改用看结果前冻结的确定性工作量上界：

| 工作量 | 数量 × 单项硬 cap | 上界 |
|---|---:|---:|
| PRECHECK、pytest、JIT | 固定一次 | 240 s |
| G0 制造与全部谱任务 | 固定 S2/S3/S4 | 600 s |
| S2 formal 记录 | 10 个动态调用 × 8 s + G0 P0 复用/提取 8 s | 88 s |
| S3 动态端点 | 17 × 20 s | 340 s |
| S4/T128 端点 | 6 × 60 s | 360 s |
| S4/T256 端点 | 6 × 90 s | 540 s |
| 公共投影、G4/G6/G7、digest、S1 裁决 | 固定一次 | 650 s |
| NPZ、inventory、postlock、ledger | 固定一次 | 300 s |
| 未分配确定性 reserve | 固定 | 482 s |
| 总计 | 40 个 formal/holdout 记录（39 个动态调用 + 1 个 G0 P0 复用）+ 固定任务 | 3600 s |

每个端点和 G0/后处理组都由 monotonic timer 执行单项 cap；超 cap 立即
`RESOURCE_LIMIT_FAIL`。单项 cap 未用完时间不能授权另一单项超过其 cap；root 仍有独立
3600 秒 watchdog。实现验收 smoke 若任一任务已超过对应 cap，正式运行前拒绝本合同，
不得事后拆包或放宽。

runner 每端点完成 N3、G7 对照、第二周期提取和必要摘要后立即释放全状态/逐单元场。
容器入口从 `resource.getrusage(resource.RUSAGE_SELF).ru_maxrss` 读取进程峰值（Linux 单位
KiB，乘 1024 转 bytes）；并优先读 cgroup v2 `/sys/fs/cgroup/memory.peak`，仅当 v2 文件
不存在时回退到 cgroup v1 `memory.max_usage_in_bytes`。宿主 runner 若可取得自身
Working Set/RSS，也记录为独立来源。硬峰值定义为全部可读数值来源的最大值；宿主来源
不可得不单独致败，但 cgroup peak 与容器 `ru_maxrss` 两者均不可读即
`RESOURCE_LIMIT_FAIL`。

停止后宿主还必须保存并校验 `docker inspect`：容器 ID/名称与启动记录一致，
`HostConfig.Memory=8589934592`、`HostConfig.MemorySwap=8589934592`，State 不再 running，
并记录 `State.OOMKilled`、`State.ExitCode`。inspect 不可读、cap/身份/运行态不一致、
`OOMKilled=true`，或 PASS completion 对应非零 ExitCode，均为 `RESOURCE_LIMIT_FAIL`；
late/early FAIL 或 timeout 的非零 ExitCode 必须与记录的 stop code/timeout 状态一致。峰值必须
`le 8 GiB`。只允许一个计算 worker，BLAS/OpenMP 线程均为 1。

## 14. 最小测试与前后锁

PRECHECK 串行执行：

1. `test_spec_v01.py`、`test_source_lock_v01.py`；
2. `test_projection_v01.py`，含 B1 shape/time/second-cycle、B4 side mapping；
3. `test_adjudication_v01.py`、`test_evidence_v01.py`，含 216 commitment 到 FINAL NPZ；
4. 既有 `test_static_architecture.py`、`test_projection.py`；
5. `test_manufactured_v01.py`，逐常数核对 N1/N2；
6. `test_runtime_smoke_v01.py` 与既有 `test_fenicsx_runtime.py`。

测试必须覆盖 `_loads_for_endpoint` 固定导入/签名、G0 S2/T64 P0 以及
A2/LN/LS/C0/CQ 冻结 N 的 load 周期平移、first-cycle sidecar 与 second-cycle ledger
shape/闭合，并断言 S2 P0 被 formal index 0 复用、S3/S4 P0 不进入端点轴。pytest cache 禁用，
basetemp=`/root/.cache/pytest_tmp`，仅 JUnit 写入 `00_precheck/pytest_junit.xml`。测试通过
只放行 G0，不是数值 PASS。

运行前后逐项锁定 HEAD/upstream/0-0、v03/v02/实现锁、8 个核心文件、15 个新增文件、
roles/config/cases/endpoints/DAG/machine registry、镜像/库版本、CPU/memory/network/GPU/
socket 与项目 scoped status。正式 HEAD 必须等于未来实现验收 commit；任一漂移即
`SOURCE_OR_PROTOCOL_DRIFT_FAIL`。

## 15. stop code、S1 与最终裁决

| code | 首失败 |
|---:|---|
| 0 | 所有适用门、inventory/ledger/completion 通过；仍待 Supervisor |
| 10/11/12 | source/protocol drift；retired route；missing interface |
| 20/21 | static/manufactured；matrix inertia |
| 30 | algebraic |
| 40/41/42 | time；space；G4a mixed |
| 43/44/45/46 | common projection；higher harmonic；G4b；G4 total |
| 50/51 | power ledger；periodic consistency |
| 60/61 | S1 holdout；holdout digest drift |
| 70/71/72/73/74/75 | array；output exists；container ID；resource；nonfinite；post-hoc change |
| 99 | unclassified runtime；不得生成科学结论 |

`HOTSPOT_DEGENERATE` 只撤销唯一热点主张：range/coverage 前提不满足时，热点稳定性记
NOT_APPLICABLE，Figure 2 不画唯一热点；其他门可继续。非退化后 N8 失败是 code 60。

只有 G0/G1/G2/G3/G4a/G5/G4b/G4/G6/G7、全部 S1 子门、source/implementation lock、
resource、array、digest、inventory、ledger、completion 全部适用项 PASS，才可把候选标签
写入 summary。之后立即停在 Supervisor Gate；不制图、不更新旧 Figure 2 FINAL、不进入
Figure 3、不提交或推送。

## 16. v02 验收门与停止边界

Supervisor 仅在以下全部成立时接受：

1. B1 第二周期节点/步数组、重复端点、ECM/energy/\(\chi_D\) 来源唯一且 shape fail closed；
2. N1 probe/seed/步长与 N2 eigensolver 参数、Ritz、负谱/零模分路完全冻结；
3. machine key、源、单位、reduction、floor、适用门、参考方向与跨层 \(N_Q\) 聚合唯一；
4. traction 明确为 ECM 侧，热点只比较 S3/T256→S4/T256，216 formal commitments 与
   FINAL NPZ 逐字节绑定；
5. 父目录、r01 先创建后 precheck、TMPDIR、非删除式 timeout、inventory/ledger/completion
   顺序和确定性 3600 秒上界闭合；
6. v01 已通过的 40 端点、DAG、N1–N11 阈值、S1、128×256、128 MiB、单 CPU/8 GiB/
   3600 秒和不自动删除容器均未回退；
7. 本文件仍只是执行合同，不冒充实现、测试或数值证据。

本文件新增后立即停止。本轮不授权修改任何旧文件，不授权代码/测试、solver/Docker、
结果目录、Git add/commit/push，亦不授权心肌 DCM、identity、三维、流体或参数扫描。
