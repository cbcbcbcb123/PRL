---
review_id: REVIEW-PAPER2-FIGURE2-FEM-ONLY-NUMERICAL-CREDIBILITY-EXECUTION-V01-01
status: MINOR_REVISION
reviewed_at: 2026-09-04
reviewer: independent_supervisor
reviewed_contract: project_control/paper2_figure2_fem_only_numerical_credibility_execution_contract_v01.md
reviewed_contract_sha256: 2cbbae0f09bb966e9292a306f4c7a698952f9bf962139c772b1cfb02e4b7c070
baseline_commit: c52b2de7536a055699b2e23011fa221a6f2f1019
baseline_upstream_ahead_behind: 0/0
execution_authorized: none
next_gate: executor_v02_then_independent_supervisor_review
---

# Paper 2 Figure 2 FEM-only 数值可信度执行合同 v01 Supervisor 审阅 v01

## 1. 结论

结论为 `MINOR_REVISION`。v01 已正确冻结 15 个拟新增实现文件、40 个唯一动态端点、
无环门禁、create-only 根事务、公共数组 schema、S1 digest 解盲和 3600 秒资源总门；
没有重新引入心肌 DCM，也没有执行任何代码或计算。

当前仍有五组会让未来实现者自行选择数值语义或破坏事务可审计性的阻塞。它们不改变
科学架构、病例或硬阈值，因此不属于重大方案重做，但必须在 v02 中一次关闭。

本审阅不授权实现、测试、solver、Docker、结果目录、Git 提交或推送。

## 2. 已通过项

| 检查项 | 独立结果 | 状态 |
|---|---:|---|
| 基线、v03、决定、CURRENT_STATUS | SHA-256 一致；HEAD=upstream，0/0 | PASS |
| 核心源码锁 | 八个 `src/paper2_hybrid` 文件哈希一致且只读 | PASS |
| 拟新增范围 | 7 个验证模块、1 个 runner、7 个测试，共 15 个 | PASS |
| 端点去重 | 36 个开发/零状态 + 4 个 S1；S2/S3/S4=11/17/12 | PASS |
| 门禁 DAG | G4a→G5→G4b→G4，无环且 S1 位于 digest 后 | PASS |
| 公共映射 | 空间解析 P0、相位解析段平均、步积分交叠守恒三路分离 | PASS |
| 结果体量 | NPZ 键/shape/dtype 已列出，未压缩约 43 MiB，小于 128 MiB | PASS |
| 资源设计 | 单根事务预计 2400 s，硬门 3600 s；内存硬门 8 GiB | PASS_WITH_REVISION_REQUIRED |
| 删除边界 | 容器不自动删除；后续清理仍须人类明确批准 | PASS |
| 文本完整性 | 880 行，42668 bytes，无尾随空格，公式定界符配对 | PASS |

## 3. v02 必须关闭的阻塞

### B1. 冻结唯一的周期、样本和步区间切片

v01 写了“原生完整周期数组（去掉重复端点）”，但未规定从两周期输出中取哪一周期、
节点数组和步积分数组的精确切片。未来实现可在 cycle 1、cycle 2、两周期平均或不同端点
处理之间选择，足以改变 Fourier 系数、相位、功率和收敛误差。

v02 必须冻结并对 shape fail closed：

1. 若状态/波形数组长度为 `2N+1`，生产共同量只取第二周期半开节点切片 `N:2N`；
2. cycle 1 的半开节点切片只用于 G7，与 cycle 2 比较；重复终点 `2N` 只作闭合，不进入
   Fourier、L2、峰值段或公共数组；
3. 若逐步功/耗散数组长度为 `2N`，生产周期只取步切片 `N:2N`；
4. 任一数组长度、时间坐标或相位起点不符合上述 schema 即
   `SOURCE_OR_PROTOCOL_DRIFT_FAIL`，不得自动截取、平均或循环移位；
5. ECM 峰值/积分摘要、能量和 χ_D 也必须声明来自同一冻结周期或明确的两周期 G7
   对照路径。

### B2. N1/N2 仍缺可重复的探针与谱算法参数

“多步长中心差分平台最优误差”和“稀疏谱算法记录参数”仍允许实现阶段选择有利步长、
随机方向、特征对数量和 eigensolver 配置。

v02 必须预先冻结：

- 所有制造场/向量的解析定义、归一化、确定性 seed；
- 主动共轭方向、无量纲中心差分步长列表、误差定义及“最优值”的唯一取法；
- N2 对各矩阵的缩放、已知两平移模正交投影、最小代数/最小模特征值检查；
- eigensolver 名称、`k/which/tol/maxiter`、初始向量/seed、Ritz 残量门和不收敛停止规则；
- `Kmat` 的负谱检查与零模计数必须分开，不能只用最小模特征对推断 PSD。

具体常数可由 v02 选择，但必须在看正式结果前写死并进入 protocol digest。

### B3. floor 与 QoI registry 仍需逐机器量唯一化

当前 registry 是类别清单，未给每个机器量的源数组、单位、范数/积分、适用门和参考
端点；`N_Q` 也未说明如何聚合 S2/S3/S4 的真零控制。实现仍可能漏掉不利 QoI 或改变
归一化。

v02 必须增加机器级表或等价 schema，至少逐项冻结：

- machine key、核心源路径、单位/量纲、时间/空间 reduction、floor 类；
- 进入 N4、N5、G4a、G5、G4b、G6、G7、S1 的确切门集合；
- 每个比较的参考端点和方向；
- `N_Q` 为哪些 G0/P0 真零控制的何种绝对范数，并冻结跨 S2/S3/S4 的聚合规则；
- S1 热点 Hausdorff/Jaccard/峰值幅度只比较 `S3/T256` 与 `S4/T256`；T128 只参与
  fine-reference 混合差，除非 v03 明确另有要求。

### B4. reported traction、物理作用力与 holdout digest 绑定不完整

NPZ 使用通用 `reported_side`，但 v03 要求保存一个明确界面侧的物理作用力。v02 必须
冻结或重命名为下列唯一映射：

- 心肌–ECM：保存 ECM 所受 `t_m_to_e = t_me_rep`，心肌所受
  `t_e_to_m = -t_me_rep`；
- 心内膜–ECM：保存 ECM 所受 `t_n_to_e = t_ne_rep`，心内膜所受
  `t_e_to_n = -t_ne_rep`；
- 合力、功率、热点、数组 key 和 Figure 2 方向均引用该映射，不使用无侧别的
  `reported_side` 解释。

此外，`pre_holdout_digest.json` 中 36 个开发端点数组的逐键内容 SHA，必须在 FINAL
打包前与 `common_observables.npz` 的 formal 数组逐键复算并完全一致；不一致即
`HOLDOUT_RULE_DRIFT_FAIL`，不得生成 PASS。否则 digest 只锁住运行时内存声明，没有锁住
最终交付字节。

### B5. host create-only、容器超时和根工件顺序仍有空档

当前 `results/paper2_figure2/` 父目录实际不存在；单写 `mkdir(exist_ok=False)` 无法保证
嵌套根目录可创建。容器命令又保留 stopped container，但未规定宿主 3600 秒超时后如何
停止仍在运行的容器；只终止 Docker 客户端可能留下后台计算。

v02 必须冻结：

1. 只允许在项目内创建缺失的 `results/paper2_figure2/` 父目录，然后对 r01 根目录执行
   独占创建；不得创建项目外文件；
2. 顺序为“确认 r01 不存在 → 独占创建根与 `host_create_lock.json` → 记录其余 Git/镜像/
   源锁 precheck”；这样 precheck 失败也能留下 failure summary 与 ledger；
3. 宿主总计时从首次 precheck 开始；到 3600 秒时对精确容器名执行非删除式 stop，等待
   停止并记录状态；禁止 `--rm`、remove/prune 或自动重试；
4. 为只读根文件系统冻结 `TMPDIR=/root/.cache/tmp`（或等价的已声明 tmpfs 路径），
   防止编译器/pytest 回落写 `/tmp`；
5. `host_create_lock.json`、`manifest_events.jsonl`、全部 stage manifest 与 complete/failed
   文件必须进入正式 inventory 和最终 ledger；FINAL 的 completion/summary/ledger 顺序
   必须无循环依赖；
6. “95% 上界”若保留，必须给确定的 benchmark 样本、计算式和安全因子；否则改称并
   冻结为确定性预算上界，不能留下未定义的统计口径。

## 4. v02 验收门与停止边界

v02 必须保留 v01 已通过的架构、40 端点、DAG、N1–N11 阈值、S1 独立解盲、128×256、
NPZ 上限、单 CPU/8 GiB/3600 s 和不自动删除容器等全部边界，只关闭 B1–B5。

Executor 只获准新增版本化
`project_control/paper2_figure2_fem_only_numerical_credibility_execution_contract_v02.md`，
完成后再次停在 Supervisor Gate。不得修改 v01、v03 设计合同、验收决定、
CURRENT_STATUS、核心源码、测试或结果；不得运行 solver/Docker、创建结果目录、Git 暂存、
提交或推送。
