---
document_id: PRL-CURRENT-STATUS
status: current
last_verified: 2026-09-19
branch: main
git_workflow_decision: project_control/main_branch_stage_commit_decision_v01.md
git_stage_push_decision: project_control/main_branch_stage_push_decision_v01.md
git_integration_decision: project_control/remote_history_integration_decision_v01.md
git_integration_execution: project_control/remote_history_integration_execution_v01.md
git_remote_push: passed
git_remote_push_record: project_control/evidence/mixed_cube_controls_v01_preflight/publication_readback.json
git_published_science_commit: a468bc11385d3e330665114381581b284698055f
git_published_review_commit: a468bc11385d3e330665114381581b284698055f
verified_commit: a468bc11385d3e330665114381581b284698055f
current_lifecycle: fem_only_four_controls_blocked_after_one_failed_docker_start
documentation_updated_at: 2026-09-19
current_repository_cleanup: closure_v01_passed
current_repository_cleanup_contract: project_control/repository_cleanup_master_contract_v01.md
current_contract: project_control/ventricle_mixed_cube_control_batch_v01.md
last_completed_contract: project_control/ventricle_fem_3d_unstructured_comparison_contract_v01.md
current_render_contract: ../PRL-results/ventricle_fem/mixed_cube_load_diagnosis_v01_20260919/visual_review.json
next_stage_contract: project_control/ventricle_mixed_cube_control_batch_v01.md
current_authorization: user_confirmed_four_control_cases_20260919_once
development_route: project_control/ventricle_3d_before_growth_decision_v01.md
default_new_external_stage_budget_mib: null
project_hard_limit_gib: 3
external_results_root: E:/Temp-Projects/PRL-results
external_results_storage_decision: project_control/external_result_store_decision_v01.md
external_results_storage_execution: project_control/external_result_store_execution_v01.md
current_clarification: results/ventricle_z0/v01_20260911/data_gaps.md
current_geometry_decision: project_control/ventricle_fem_only_measured_contour_decision_v01.md
execution_authorized: four_control_cases_one_container_no_retry_only
runtime_start_authority: consumed_one_normal_start_failed_no_retry_or_repair
current_execution_log: project_control/ventricle_mixed_cube_control_execution_v01.md
latest_completed_execution_log: project_control/ventricle_mixed_cube_load_diagnosis_v01.md
latest_completed_scientific_gate: F6-S1-S9_low_pressure_active_contour_two_mesh_passed
latest_result_package: ../PRL-results/ventricle_fem/mixed_cube_load_diagnosis_v01_20260919/summary.json
latest_supervisor_decision: project_control/ventricle_3d_before_growth_decision_v01.md
current_theory_contract: project_control/ventricle_fem_finite_strain_contract_v01.md
preserved_ncs_contract: project_control/ncs_m1_all_fem_baseline_plan_v01.md
historical_theory_contract: project_control/paper2_figure1_three_layer_theory_contract_v02.md
preserved_legacy_lifecycle: prl_figure2_spatial_tolerance_st1_a1_cycle_stability_failed_human_gate
preserved_legacy_contract: project_control/prl_figure2_spatial_tolerance_validation_contract_v02.md
current_mainline: FEM_only_no_DCM_forward_execution
current_mainline_decision: project_control/ventricle_fem_only_measured_contour_decision_v01.md
current_physical_removal_record: project_control/paper2_myocardial_dcm_physical_removal_execution_record_v01.md
standing_authority: no_scientific_stage_or_cleanup_execution_without_applicable_confirmation
historical_standing_authority: project_control/paper2_autonomous_execution_and_chart_reporting_decision_v01.md
supervisor_thread_id: 01a067cf-d740-7d50-9ada-4743e9f19141
executor_thread_id: 019fc73d-393d-71a3-98cb-d3c0cd0c8eda
---

# PRL 项目当前状态（单一入口）

本页是项目的**当前状态索引**。合同、决定、执行记录和失败记录仍各自保留为不可替代的证据；若旧文档中的“当前状态”与本页冲突，应先核对本页列出的最新决定，而不是改写历史记录。

## 阶段远端同步（2026-09-19新增长期规则）

用户要求每次完成后同步远端供专家查看。阶段交付经必要检查后，直接提交main并普通推送origin/main，
不再逐次请求推送确认；不强推、不更新其他分支或标签，不纳入50项无关旧改动。
见[长期规则](main_branch_stage_push_decision_v01.md)。
[最新在线审阅包](../docs/review/mixed_cube_benchmark_v03_20260919/README.md)含原样PNG与小型摘要；
完整原始状态仍在本机PRL-results，仅Git克隆不能完成保存态复算。本次不新增科学计算。
已普通推送4个未同步科学阶段提交及审阅页；远端main回读为fd6090d，与该次发布的本地HEAD一致，
其他分支/标签引用未变。见[远端回读记录](evidence/stage_main_sync_v01/publication_readback.json)。
此passed仅指发布验收；下述数值资格仍failed，不能因同步成功改写科学结论。

## 当前：2026-09-19 一次获准Docker启动失败，四工况仍0新求解

后续工程交付：[Windows Docker 技能已安装](docker_windows_runtime_skill_delivery_v01.md)。
16项行为测试、格式与安装哈希通过；18:32只读复核仍为五套接字1920。
0新增启动/修复/容器/求解；这项交付不改变下述科学阻断。

用户批准仅正常启动现有Docker一次；18:06:25实际启动，18:06:59 backend报告崩溃。
新日志直接指向Ingest初始化：`sailor-ingest.sock`重命名失败，文件不可访问；
启动前五个套接字ACL读取error1920。原生引擎仍Server=null，故未创建容器或运行任何FEM。
这是宿主运行时直接故障，不是科学模型失败；套接字异常反复出现的深层原因unknown。
1启动、0重试、0修复/删除/隔离/安装/更新/拉取、0容器/求解/GPU。
668保护文件、50旧改动、控制源码和配置核验未变。原四工况授权未消耗，但启动权限已用完。
见[本次执行记录](ventricle_mixed_cube_control_execution_v01.md)及[启动失败证据](evidence/mixed_cube_controls_v01_startup/startup.json)。
唯一下一步是单独裁决运行环境恢复方式，不能继续自动重启或轮换套接字目录。
待环境就绪后原批次续行，不改本构、单元、误差门或原八工况/心室失败。

## 上一步：四工况实现就绪，初次Docker预检blocked

用户已整批批准四工况；同一求解器增加两个解析场、独立验证与配置入口，65项宿主测试passed。
代码及blocked记录已普通推送main，远端回读a468bc1一致；[发布核验](evidence/mixed_cube_controls_v01_preflight/publication_readback.json)仅证明同步，不代表原生计算通过。
原材料/积分/单元/保护/误差门未改。启动前Docker Server=null且引擎管道不存在，
Desktop/backend进程均不在；日志有idle graceful shutdown，但此前error1920是否复发unknown。
0容器、0求解、0重试、0GPU，结果目录未创建；不把宿主测试当原生或科学通过。
详见[本次执行与阻断](ventricle_mixed_cube_control_execution_v01.md)。
唯一下一步是取得一次现有Docker启动授权或由用户启动；引擎就绪后续跑已批准四工况。
无任何运行时修复、移动/删除、安装/更新/拉取；不重开旧失败或扩展到心室主动/生长/FSI。

## 最近完成：2026-09-19 保存态压力载荷表示诊断passed，原科学资格仍failed

本轮响应“继续项目、科学进展较慢”，将当前问题一次诊断到可区分的候选机制；不增加新平衡求解。
3个κ100旧终态，高阶积分及精确虚功核对；固定解析F*下构造压力—虚位移矩阵，
识别P1压力不能平衡的精确压力力分量：n2/4/8占比29.13%/12.04%/3.27%，
其节点力范数为等容力的13.05/5.50/1.49倍。最细网格该分量约1.09e−3，积分差仅3.44e−9。
载荷积分误差不足以作为目前优先解释，压力载荷表示/位移污染成为最直接待验证机制。
这些是固定基底上的离散力欧氏投影指标，不是压力场百分比、inf-sup定理或原心室根因证明。

80.126秒离线分析，42项针对性测试、派生数组读回与639个源/保护文件哈希passed。
29文件1104018 bytes；manifest `fae715c181ee24be5ca384e6a43c0257fa52ffcad1d34c5a6a0a58e85652fac1`。
首次log域外刻度导出失败保留，纯布局修正后160dpi探索图/目检passed；投稿600dpi检查不冒充通过。
0新FEM、0 Docker、0 GPU；原科学门failed不变，无删除/安装/全局记忆更新。
见[在线审阅与数据](../docs/review/mixed_cube_load_diagnosis_v01_20260919/README.md)和
[本次执行](ventricle_mixed_cube_load_diagnosis_v01.md)。
唯一下一步为[四工况控制批次](ventricle_mixed_cube_control_batch_v01.md)，用户已明确整批确认，当前not_run。
授权一次容器及最多四次求解；不重开旧八工况或直接进入心室/主动/生长/FSI。

## 历史：2026-09-19 v03候选正J保护passed，场精度与高κ粗网格平衡仍failed

按用户“同意，继续”实施接受前保护及同八工况一次复验。唯一修改为候选方向正J区间准入，
保持全部材料/网格/载荷/原误差门及30次Newton上限。单CPU/0GPU/禁网，一次72.0377秒；
6次SNES尝试、5个有效终态，第6例候选减半20次耗尽，余两例not_run；无自动重跑。

两patch再次passed。原生precheck保存32个X/Y候选，31条获准并成为接受步、14次缩短；
独立驻点法证实采样路径正性及接受步落在该方向段内；37个保存态均独立读回。
高κ粗网格最后min J=1.62e−7、最大节点位移0.28016L、残差0.41464，未取得平衡；
下一候选2^-20仍有路径负J=−2.32e−8，安全拒绝而不接受，不继续增加减半次数。

κ=100误差与v02逐值相同，最细u L2/H1/J RMS 4.3239%/43.6485%/0.15618%仍超原门。
同网格解析场P2插值H1误差2.3785%，提示表示能力不是唯一问题；插值不是平衡/最佳逼近下界，
不据此断言锁死、inf-sup失稳或材料错误。下一诊断应转向制造载荷积分/混合压力约束的误差放大。

54宿主测试passed，434保护文件与50旧改动保持；全部v01/v02失败不改写。
原心室1%门仍failed、未重算；薄层/三维主动/生长/FSI not_run。无删除/安装/拉取/推送/新全局记忆。
探索图160dpi布局/目检passed，通用600dpi检查failed照录；算法迭代不是生理时间。
[本批执行裁决](ventricle_mixed_cube_benchmark_v03.md) ·
[结构及诊断结果](../../PRL-results/ventricle_fem/mixed_cube_benchmark_v03_20260919/index.html)。
唯一下一步建议是保存态误差机制鉴别；新原生计算尚未授权，不能自动续跑后两例。

## 历史：2026-09-19 v02非零patch通过；场精度和高κ变形安全failed

按用户“同意，记忆”批准的一次v02执行完成。64.026秒，6次SNES尝试、5个有效终态、1个安全失败、2例未运行。
两个非零patch passed，原表达式接口症状未复现。κ=100三网格误差下降、阶次达门，但n=8
u L2/H1相对误差4.3239%/43.6485%、J误差RMS 0.15618%，分别超过2%/15%/0.1%门；压力误差2.0733%达门。
κ=1000、n=2的第1Newton步：积分点min J=+0.023899，额外点min J=−0.176372、6个单元检出负J，触发安全停止。
不把残差下降、弱矩满足或积分点正J当成精度/有效形变证明。后两例not_run；未自动重跑或修改门限。
5个终态/24个监测状态独立复算通过，49项宿主测试passed；原生数值源码运行后未改。
289保护文件与50旧改动保持，原v01完整失败保留；用户要求的记忆更新已保存，明确候选/验证和权限边界。
145文件16,593,908 bytes；manifest `c59044955f3609509f8b8c61d620384ae800f9e2cebfa469d005cd61a9aaedda`。
[执行与裁决](ventricle_mixed_cube_benchmark_v02.md) · [结果入口](../../PRL-results/ventricle_fem/mixed_cube_benchmark_v02_20260918/index.html)。
唯一下一步：制定并确认试探步正J保护及同基准精度复验的有界批次，尚未授权；不进入心室、主动、生长或FSI。
探索图160dpi非投稿；首次绘图次刻度问题及合成测试参数选错记录保留，修正仅涉及显示/测试，不改生产门限。

## 历史：2026-09-18 八工况基准接口失败，八个平衡工况not_run

用户确认后执行一次固定镜像容器，单CPU/0GPU/禁网，14.443秒退出2；无超时/OOM/自动重跑。
首patch读取表达式时坐标单元hash检查失败，尚未SNES，0个平衡态；不是材料或误差收敛结论。
高可信候选为零体力编译化简丢域，但原日志未记录表达式key，归因unknown。
已改为网格绑定零Constant并增加逐表达式诊断；46项宿主测试passed，原生症状消失尚未验证。
原summary把缺失MMS写成failed、空集合读回写成passed，两份原件保持，新增裁决明确八例not_run。
实际结构及执行统计图已交付，不用插值检查态冒充平衡/应力/心动结果。
81文件1,007,051 bytes，manifest `5d3c7d623c4cb80404946a7bd04f1be104296b48ab0f213bb1a5b240c4b575fb`。
208保护文件/50原有改动保持；20份失败时源码与修订后源码分版保存。原三维压力门仍failed。
[完整执行](ventricle_mixed_cube_benchmark_execution_v01.md) ·
[结果入口](../../PRL-results/ventricle_fem/mixed_cube_benchmark_v01_20260918/index.html)。
唯一下一步：待确认修订版v02同八工况一次容器，原参数与门限不变；无其他新求解授权。

## 历史：2026-09-18 专家意见采纳与保存态投影诊断完成，新基准待整批确认

用户提供专家意见及八成员复核ZIP，原件/附件哈希验收并登记于plan/active。
新代码仅独立分析已有M0/M1压力态，生产本构、原验证器、配置与原D1证据127文件未改。
8项专家数字逐网格一致至1e-12，弱压力矩约1e-18，正交分解及保全源码复算passed。
全域投影缺陷r=J−1−p_m/κ的RMS从0.165124%降至0.120037%（下降27.30%），
max|p_m/κ|仅0.001722%/0.002044%，但原max|J−1|仍1.522743%/1.449560%，压力门failed。
固定d≥0.30L仍含全域峰值，M1峰值位于d=0.301956L；“邻接基底”不能替代固定距离分析。
一区RMS略升；结果不是纯h收敛、锁死或不稳定证明，因果根因unknown。

交付一页真实结构/全部单元/固定分区诊断PNG+SVG、可重绘源码和全部派生数据。
14项针对性测试passed；收口时首次测试子进程因未设PYTHONPATH而未收集测试，
仅补显式src路径后通过，原收集失败记录保留；无新FEM、Gmsh或Docker调用。
探索图160dpi例外已声明；投稿级600dpi检查failed保留，不声称投稿图验收passed。
整包21文件1,664,438 bytes，manifest SHA-256
`78a9542bd69d6373a4e25f4bec421f6ea5441a49e4d5334932811201cd85628b`。

[结果及复算](../../PRL-results/ventricle_fem/volume_projection_audit_v01_20260918/index.html) ·
[采纳与预注册八工况](ventricle_volume_qualification_adoption_v01.md) ·
[专家原件](../plan/active/EXP-20260918-FEM-review-v01/README.md)。

唯一下一步是一次确认后实施2非零patch+6制造解；单CPU/0GPU、0自动重跑，先当前P2/P1。
新批次not_run，不运行薄层/原心室回归、主动、生长或FSI；旧1%门及失败全部保持。
旧非结构化候选授权已消耗，不继续靠随机换网格争取通过。

## 历史：2026-09-18 F6-S2-D2B同边界候选质量未通过，FEM未运行

用户明确确认后执行一个Gmsh 4.15.2候选，原M1边界及两层界面片完全保持。
3960→2611单元，19119→13483预计混合DOF。内腔体积差0，各层相对差<=2.22e-16；
独立拓扑、共享界面、几何及资源门passed。整体q05为0.238272→0.248857，
仅提高4.442271%未达预设5%，质量门failed；最差q 0.2220→0.0292（少数ECM单元），
最小二面角6.637914°→6.811118°。未降低或事后修改门限。

原容器在网格生成后因节点重编号读取KeyError(726)停止；完整原始MSH已保存。
原失败记录不变，仅用已有meshio精确坐标映射读取保存候选得到上述质量核验。
适配器已修订并补回归；修订后完整容器not_run。新增候选0、新增FEM0、无重跑。
原M0/M1压力局部体积偏差1.5227%/1.4496%仍failed；U1没有应力/形变结果。

132项测试+21子测试、独立读回、真实结构与质量分布图及Notebook交付passed。
本包94文件22,018,556 bytes、manifest93项；SHA-256：
c6528c6a25ca3affdef4fe15a9af6288ad121fb79aef57873a0d3a4f1df23282。
375内部+1760外部保护文件、50无关修改保持。单CPU/0GPU，无删除/安装/拉取/推送。
本地main科学提交69d2d47；结果外置，不进入Git。

[结构/质量图及候选原始文件](../../PRL-results/ventricle_fem/f6s2d2b_unstructured_v01_20260918/index.html) ·
[执行记录](ventricle_fem_3d_unstructured_execution_v01.md) ·
[采纳及固定选项](ventricle_fem_3d_unstructured_adoption_v01.md)。

唯一下一步：先形成近不可压三维混合离散的小基准资格方案，审查稳定性、
局部体积控制及夹持热点；不能直接把二维DG搬到三维。新计算需具体方案确认。
本候选授权已消耗，不自动调网格选项，不更改材料/基底/1%门，不继续生长/FSI。

## 历史：2026-09-18 F6-S2-D2A网格形状审查完成，原因尚未分离

只读原M0/M1实存u/p进行离线重算，0新FEM求解；原生产/几何/协议/力学验证器哈希不变。
最小二面角4.410972°→6.637914°，最小q=3r/R为0.151387→0.222035；形状改善。
但原局部J偏差1.522743%/1.449560%仍超1%门，原failed不变。
M1全部120个超限单元邻接基底，其中72个无形状筛查标记；384个远区形状标记单元无一超门。
q<0.2或最小二面角<10°只是诊断筛查，非普适合格门；整体相关系数不可当因果。
同层且基底相邻子集的q-J相关符号反转，提示层别/位置混杂；夹持与压力表示仍未区分。

121项回归+21项子测试、逐单元复算、实际参考结构/质量/J图和Notebook验收passed。
包67文件35,551,399 bytes、manifest66项；SHA-256：
c3df60d71c49de891d41e5c20b3fb01eddd922ef4ba3f8591a912b77a0cb24da。
保护1693外部+375内部文件及50项无关修改；无删除/安装/拉取/GPU/推送。
唯一只读镜像探针发现gmsh模块；实际本机库导入/网格生成尚not_run。

[结构/质量图与证据](../../PRL-results/ventricle_fem/f6s2d2a_mesh_quality_v01_20260918/index.html) ·
[执行](ventricle_fem_3d_mesh_quality_execution_v01.md) ·
[下一步具体候选合同](ventricle_fem_3d_unstructured_comparison_contract_v01.md)。
候选执行待确认：同M1多面体边界与层界，仅一次内部非结构化剖分；先几何与质量门，
合格才最多zero和p=0.01两态。保持力学/基底/压力空间及原1%门，不进入主动/生长/FSI。

## 历史：2026-09-18 F6-S2-D1细网格同压力仍不满足局部体积门

仅新增M1零载和p/mu=0.01、Ta=0两态，保留M0失败不重算；生产/协议/原独立力学文件哈希不变。
一次44.488051秒、1CPU/8GiB/禁网/0GPU/0重跑。M1零载passed；首压力3次Newton收敛，
MUMPS及独立场量passed，但max abs(J-1)=1.449560%仍超过原1%门，首失败停。

M0/M1单元1344/3960，腔体积增加1.089525%/1.105919%，响应相对差1.482348%通过参考门；
局部最大偏差1.522743%/1.449560%，仅改善4.805976%，两压力态均failed。
M1的120个超限单元全部与基底相接，远区最大0.459731%；夹持/压力空间/几何贡献未分离。
不能以整体响应接近宣称局部或渐近收敛；不改材料、门限或夹持，不继续主动、生长、FSI。

91测试、主机/容器复核、真实1倍/共同色标结构-应力-J图及Notebook交付passed。
结果128文件41,493,908 bytes、manifest127项，SHA-256：
7bd712585b82c5ca4689f56292536a918b060ace2acf9051790ecba9a790e0f4。
1940父文件、75调用文件、50项无关修改保持；本地main提交，不推送。

[粗细对照图及证据](../../PRL-results/ventricle_fem/f6s2d1_3d_fine_pressure_v01_20260918/index.html) ·
[执行及科学边界](ventricle_fem_3d_fine_pressure_execution_v01.md)。
唯一下一步待确认：先形成局部体积约束离散的单变量资格方案，材料/载荷/基底暂不变；
审查三维压力表示、自由度/稳定性/锁死与小基准门。方案审查不启动FEM，新运行另按合同确认。

## 历史：2026-09-18 F6-S2-R原生接口通过，三维首压力局部体积门失败

原M0无载逐项身份/原生接口门passed，不重新求解无载；材料、几何、边界、力学公式及门限不变。
一次31.453212秒单CPU/0GPU/0重跑，新增M0 p=0.01、Ta=0一个状态。
3次Newton达到平衡，MUMPS passed，残差1.69e-16；腔体积扩大1.089525%、最大位移0.004042L。
局部max abs(J-1)=1.522743%超过原1%，积分点本身也为1.314813%；首失败停止。
新态接受0，原无载复用1；后续12态、主动、M1平衡、生长、FSI及生物学验证not_run。

只读定位：96个超限单元全部与固定基底相接，非相邻单元最大0.529615%。
弱压力残差1.81e-18不能替代逐点体积门；网格、夹持和连续P1压力空间的贡献未分离。
87测试、主机/容器复核一致、真实结构/应力/J/响应图及Notebook验收passed，不改failed科学裁决。

[结果图及证据](../../PRL-results/ventricle_fem/f6s2r_idealized_3d_resume_v01_20260918/index.html) ·
[执行与定位](ventricle_fem_idealized_3d_resume_execution_v01.md)。
123文件17,765,106 bytes，manifest122项，SHA-256：
cb846ad96711d6706a7a9b2912ddf9100a65c2a3645e9dd7f7af14c0eafd455c。
1817父文件、71调用文件、50项无关修改保持；原F6-S2 failed不改写。

唯一下一步待确认：已有M1仅零载及同p=0.01两个状态，对照保留M0失败；
不改材料/边界/离散/1%门、不进入主动/生长/FSI，首失败停。通过也只代表有界离散诊断。

## 历史：2026-09-18 F6-S2三维结构建成，首接口失败后停止

半椭球三层壳、三维P2/P1四面体；M0/M1几何1344/3960单元通过预定几何门。
基底环固定、外壁自由；计划内腔随动压力及心肌切平面分散张力，几何/材料未标定。
一次26.462148秒单CPU/8GiB/禁网/0GPU调用，仅完成M0无载SNES（0Newton、残差1.2368e-16）。

原生独立复核遇压力数组(1,325)按一维读取的IndexError，首失败停，原failed保持。
已用实际保留数据回放并最小修正映射/读取接口；离线无载26项检查passed：u=0、J=1。
81测试与可执行Notebook/PNG/SVG验收passed；这不代表修正生产端已在原生运行中验证。
压力、主动、组合和M1平衡余13态均not_run；FSI/生长/生物学验证not_run。

[结构与真实无载图](../../PRL-results/ventricle_fem/f6s2_idealized_3d_v01_20260918/index.html) ·
[执行及修正证据](ventricle_fem_idealized_3d_execution_v01.md)。
外置98文件10,616,566 bytes，97项manifest，SHA-256：
991710ecfb62d72bca971f8254199f119518d8fe199312e1bcea7949645d3e42。
1719父文件、53原调用文件、50项无关修改保持；无删除/拉取/安装/自动重跑。

唯一下一步待确认：只读复用原M0无载，核对修正后的精确DOF映射，再有界续算余13态。
不扩参数、放宽门限或加入生长/FSI。路线调整见[先三维再生长](ventricle_3d_before_growth_decision_v01.md)。

## 历史：2026-09-18 F6-S1-S9低压主动收缩对照通过

固定p/mu=0.02，从原受压态增加Ta/mu=0.025/0.05/0.075/0.10，M0/M1共8个新平衡全部接受。
相对同压力零张力基线，最高张力缩腔1.846775%/1.844892%；相对无载参考仍扩张17.839020%/17.889685%。
主动张力使腔面积单调减少，但目前只是部分抵消压力扩张，不是实验幅度心跳。
最高张力局部max|J−1|=0.342390%/0.330124%，全部状态保持原1%门；
73项独立汇总检查与粗细总面积门passed，热点/渐近收敛不据此宣称通过。

同一生产和独立力学内核、P2/DG2有限变形平面应变NH；mu=1/kappa=1000、三层同被动参数未标定。
内壁随动压力、外壁自由，A固定ux/uy、B固定uy。外侧构造心肌层主动能量Ta/2(|Ff0|²−1)，
f0=(-Y,X,0)/sqrt(X²+Y²)为原点环向假设，不是实测纤维或轮廓切向。
只外轮廓来自图像，内腔和层界构造；加载级不是生理时间。

一次201.218秒1CPU/8GiB/禁网/0GPU，32个新Newton向量，4旧态复用，0重跑。
152测试+21子测试及两套Notebook/600dpi PNG/SVG验收passed；1518父文件、140调用文件、41副本、50无关修改保持。
外置201文件350,554,617 bytes；manifest直接覆盖200文件，SHA-256：
80b0ecbe6bd35e6d00479fbeb1e424c89969e862a01bdb0885bb43dab9734c2b。
旧0.08高压失败仍failed；本轮没有再次修补物理/门限/跨平台比较。

唯一下一步待确认：理想化三维心室固体的几何、网格和纤维方向，再验证低压与主动载荷。
不直接继承二维DG2资格，不自动执行三维、FSI、生长或实验验证。
见[执行与边界](ventricle_fem_contour_active_execution_v01.md)及
[结构、场量、五个真实张力态与Notebook](../../PRL-results/ventricle_fem/f6s1s9_contour_active_v01_20260918/index.html)。

## 历史：2026-09-18 F6-S1-S8中间压力通过，高压局部体积失败即停

从原两网格0.02已接受态续算上限6态，实际M0尝试3态、接受2态；0.08失败后M1后续3态全部not_run。
M0的0.04/0.06/0.08腔面积变化分别+32.807874%/+48.055961%/+68.266151%，
max|J−1|分别0.587402%/0.920140%/1.173743%；最后一态超过原1%门，门限未调整。
SNES/MUMPS与独立力平衡、DG2点态约束仍passed，因此不是求解器不收敛；原科学failed保留。
仅1/3541单元的2个积分点超限，位于构造心肌域外轮廓凹口附近，离固定点较远；
当前不能区分几何尖角效应与网格依赖，也不把平均J约1.000152当作局部门通过。

同一几何、P2/DG2、有限变形平面应变NH、mu=1/kappa=1000、Ta=0、内壁随动压力/外壁自由/规范固定点。
一次57.462秒1CPU/8GiB/禁网容器，4旧态复用、17新Newton向量；0GPU/重网格/圆环/重算/安装/拉取/删除。
48独立汇总项44通过；余4项对应0.08物理门失败与后续序列/粗细检查未完，不混称全部passed。
失败即停、运行隔离、两套Notebook/600dpi PNG/SVG和132tests+21subtests验收passed。
局部边界24/48段采样无自交，但不是精确曲线或全局单射证明。

交付比较派生虚功误差的1.35e-12至3.55e-12跨平台舍入差已修复：
先核验派生误差代数一致，再传播原有限差分舍入余量；其他字段/物理门/原科学裁决不变。
原failed比较和回归红例均保留，0科学重跑。1358父文件、94调用文件、38副本、50项无关修改保持。
包160文件115,310,640 bytes；根manifest直接覆盖158文件，父manifest由input_identities间接覆盖，全部数据有哈希链。
根manifest SHA-256：58a708f93a3b3c0f290912054a19a00c3b17a9ec94aa2008247322416d6b3c21。

唯一下一步提议：保留高压失败，转在**两网格已通过的0.02**基线上研究有界心肌主动张力递增。
这是改变“完整高压先于主动”的顺序，须用户明确确认并另立合同；本轮主动/三维/FSI/生长/实验验证均not_run。
见[执行与诊断](ventricle_fem_contour_passive_execution_v01.md)及
[结构、五个真实M0压力态与Notebook](../../PRL-results/ventricle_fem/f6s1s8_contour_passive_v01_20260918/index.html)。

## 历史：2026-09-18 F6-S1-S7原轮廓两网格首压力通过

原保存M0/M1各零载和p/mu=0.02，4态全部接受，24个真实Newton向量保留。
局部max|J−1|粗/细0.323434%/0.358062%，低于不变的1%门；旧CG1的6.71167%/11.15248%仍failed。
腔室面积扩张20.056188%/20.105502%，粗细差0.0493142个百分点、相对差0.245277%，原面积门通过。
细网格独立自由力3.295e-14、DG2点态约束误差3.470e-13，40项独立范围检查与全部逐态原门通过。

同一外轮廓、材料和BC，仅DG2压力表示；内腔与三层仍为构造，三层相同未标定被动材料。
正压两网格均10次Newton、实际MUMPS余量100/INFOG=0；零载0更新因子not_run/null。
一次122.067秒单CPU/8GiB/禁网容器，0GPU/圆环重算/网格生成/自动重跑/安装/拉取/删除。
1194父文件、102正式调用文件、50项无关修改保持；110测试+21子测试passed。
两套Notebook/PNG/SVG目检与样式通过，4个真实状态为1倍形变，不是心动时刻。
附加二次边界24/48段采样筛查未见自交，不能替代精确曲线全局单射证明。

交付逐字段比较曾因唯一有限差分虚功字段跨平台差1.332e-12而停止；原失败/报告保持。
仅交付比较采用该差分量的机器精度缩放余量，物理门和分类不变；原反馈环及回归复验passed，0FEM重算。
包164文件184,644,758 bytes、163清单条目，manifest SHA-256：
`524b1560a9ba63a0b99a19f20188cdaf704bd05a0d507a65e32c1cf21ccf0704`。

当前只通过首压力两级资格，完整轮廓被动序列、热点收敛、主动、三维/FSI/生长和实验验证未完成。
唯一下一步待确认：复用已接受0.02态，补两网格0.04/0.06/0.08，最多6新态；
同几何/材料/1%门、单CPU/0GPU、首失败停止，不重算已接受态或夹带主动。
见[执行与证据边界](ventricle_fem_contour_dg2_execution_v01.md)及
[结构/4态场量与Notebook](../../PRL-results/ventricle_fem/f6s1s7_contour_dg2_v01_20260918/index.html)。

## 历史：2026-09-18 F6-S1-S6零载诊断修复，原两网格被动资格通过

5个M1新态全部接受，5个M0态全部复用，0粗网格重算。69项独立数值检查passed，原物理与门限不变。
细网格峰值腔面积+22.460165%，壁局部max|J−1|=0.01219238%（门1%）；
最大相对不可压解析面积响应误差0.0722750%、径向L2误差0.0589786%（门均1%）。
粗细峰值响应差0.000865913个百分点，相对差0.00385533%，满足原门。
仅为未标定二维圆环的两级被动资格，不是多级渐近、热点收敛、真实心室或生物学验证。

原生6自由度负例确认：SNES reason=2、0次Newton返回后，getMumpsInfog(1)崩溃；
Mat对象实际上非空，最初空句柄假设及其failed分类保留。修复仅跳过本次无更新时的当前/陈旧因子读取。
真实零载/非零载/已有解接口检查passed后，M1零载获得完整末态与最终SNES报告，因子明确not_run/null；
正压均3次Newton更新，实际MUMPS余量100、INFOG=0。共17个M1真实Newton向量保留。

负例6.407秒、修复后接口及5态51.511秒，2个预声明容器/1次科学调用，单CPU/8GiB/禁网/0GPU。
980父文件、162正式调用文件和50项无关修改保持；76测试+21子测试通过。无安装、拉取、删除或自动重跑。
两套Notebook、结构/场量/5压力态PNG/SVG已验收，1倍形变，压力延拓不是生理时间。
包110,166,407 bytes、214文件；213个manifest条目哈希通过，manifest SHA-256为
`0f98f486aea555bb84d3691fc3c821d8fc049e20c86c4f8b0494dcd0df4345c4`。
上轮S5原生失败及旧轮廓CG1局部J失败保持原始裁决，没有回写为passed。

唯一下一步待确认：原图像外轮廓、构造内腔/层界的粗细网格，零载和首个p/mu=0.02，最多4态。
同一P2/DG2/材料/1%门，单CPU/0GPU/失败即停，不再重算圆环，不夹带主动/三维/FSI/生长。
见[执行、负例定位及修复](ventricle_fem_fine_ring_recovery_execution_v01.md)与
[结构/5个细网格压力态场量及Notebook](../../PRL-results/ventricle_fem/f6s1s6_fine_ring_v01_20260918/index.html)。

## 历史：2026-09-18 F6-S1-S5粗圆环5态通过，细圆环零载原生退出

一次23.705秒单CPU/8GiB/禁网容器，尝试4态、接受3个新M0态，0自动重跑/GPU。
结合复用的零载与0.02态，粗网格0/0.02/0.04/0.06/0.08全部通过原1%局部J及M0的2%解析门。
峰值腔室面积+22.4593%，max|J−1|=0.0134833%，独立自由力残量1.637e-13，
最大相对不可压解析面积响应误差0.0684168%。这些是未标定二维理想圆环证据，不是实验验证。

细网格几何和切线通过；M1零载monitor-0残量2.175e-16后PETSc SIGSEGV 11，容器退出15、OOMKilled=false。
只有初猜与迭代0，没有最终SNES原因或完整末态，不能接受M1零载或宣称粗细网格通过。
优先排查零次Newton后的因子诊断，但没有原生栈，准确调用点未知；本轮没有Ring修复或额外容器。
整阶段failed / 粗网格passed / 细网格执行failed / 粗细比较not_run / 图件与保全passed。

68测试+21子测试通过；826父/祖先文件、98正式调用文件及50项无关修改保持。
两套可复算Notebook与结构/结果图已验收，5个真实压力态统一应力色标、1倍形变，不是生理时间。
结果包57,517,914 bytes、154文件；153个manifest文件哈希通过，manifest SHA-256为
`080bf5d223d41ea106c4c560d7fe3a98fb838d452715c30d335a4110e9355c48`。
原轮廓6.71%/11.15%局部J失败仍冻结保留；主动/原轮廓/三维/FSI/生长本轮均not_run。

唯一下一步待确认：同环境零载/零次Newton接口微测定位与最小修复，通过后仅补细网格5态；
不重复粗网格、不改材料及1%/解析/粗细门、单CPU/0GPU/失败即停。
见[执行及故障边界](ventricle_fem_ring_passive_qualification_execution_v01.md)与
[结构/5个压力态场量及Notebook](../../PRL-results/ventricle_fem/f6s1s5_ring_passive_v01_20260918/index.html)。

## 历史：2026-09-18 F6-S1-S4 v02首个DG2粗圆环压力平衡通过

同环境真实监测/因子选项12项接口检查passed后，仅从原保存零载续算p/mu=0.02、Ta=0。
一次21.891秒单CPU容器，FEM求解约0.554秒；3次Newton更新得到1个接受态，0零载重算/自动重跑/GPU。
实际MUMPS余量100、INFOG=0。材料、边界、网格和1%门不变；21项范围检查及20项末态物理门通过。

腔室面积+4.675918128%，壁局部max|J−1|=0.002628443%，独立自由力残量约1.70e-14。
相对不可压解析面积响应误差0.0566923%；相对旧CG1同网格面积响应差0.00123356%。
这些是单个粗圆环被动压力点的数值证据，不是整个DG2粗细收敛或生物学验证。
全部4个实际Newton状态与独立重算形变/应力/J图保留，1倍位移、无虚构帧；迭代不是生理时间。

63测试+21子测试passed；709父/祖先文件及50项无关改动保持，61个正式调用文件哈希未变。
本包40,774,544 bytes、117文件（含manifest）；116个清单文件逐项通过，manifest SHA-256为
`e5caa254680ebe03111d67213d8635ab6cac848540344d228a0b92106103444f`。
原v01监测失败包及CG1轮廓6.71%/11.15%局部J失败仍冻结保留。本轮不运行原轮廓或主动收缩。

唯一下一步待确认：补完原粗圆环0.04/0.06/0.08和细圆环零载至0.08，最多8个新平衡，
不重算已接受态、不改材料/1%门、首失败停止。通过后再回原轮廓；三维/FSI/生长未在本轮执行。
见[本轮执行](ventricle_fem_ring_resume_execution_v02.md)与
[结构/场量/实际Newton状态及Notebook](../../PRL-results/ventricle_fem/f6s1s4_ring_first_pressure_v02_20260918/index.html)。

## 历史：2026-09-18 F6-S1-S4监测接口失败；修复已写入，当时原环境未复验

从保留零载态仅尝试圆环p/mu=0.02。一次16.914秒单CPU容器，在第0次监测回调的可写Vec.array访问处失败；
PETSc只读锁错误73/101来自Codex本轮新增的记录代码，首次Newton更新前终止。0个接受受压态。
保存初值与末次尝试完全相同；独立初始自由力残量0.00866704，不满足平衡，初始J=1不构成体积资格。
619父/祖先证据文件及50项无关修改保持，44个正式调用文件未变；单CPU、0 GPU/零载复算/自动重跑/安装/删除。

补丁改为只读读取，并根据实际安装DOLFINx源码修正矩阵因子选项的生命周期；本次实际MUMPS余量unknown。
60项测试+21子测试passed，但接口协议夹具不等同于原环境验证，补丁原环境复验not_run。
科学与工程执行failed；证据保全和可复算结构/失败图passed；不生成虚假形变或多时刻状态。
本包11,523,182 bytes，89个manifest文件哈希一致，SHA-256为f6f8d75d3ea8282b1a08214b15e6bcdd2282c227032ab18f13e177b5315765b9。

唯一下一步待确认：同一固定环境先做只读锁向量及MUMPS选项微型接口烟测，通过后才恢复同一首个压力态；
不改物理/1%门、不重跑零载、任何失败即停。其余压力、轮廓、主动、3D、FSI、生长均不在本轮运行。
见[执行记录](ventricle_fem_ring_resume_execution_v01.md)及
[结构与初始未平衡力图/Notebook](../../PRL-results/ventricle_fem/f6s1s4_ring_first_pressure_v01_20260918/index.html)。

## 历史：2026-09-18 F6-S1-S3同矩阵工作空间修复验证通过

同一保存CSR上仅ICNTL(14)由20改100；一次8.380秒单CPU容器，MUMPS INFOG(1)=0、KSP=4、PC=0。
独立残量7.47726e-11低于1e-8，与保留SuperLU向量相对差1.44635e-8低于1e-6。
矩阵/右端/初值不变，14个其他可读控制项相同；0重组装/新SuperLU因子化/非线性求解/状态更新/求解重跑。
19项证据检查及7项线性门passed；375父文件和176来源文件保持，56测试+21子测试通过。
首次Docker镜像查询超时未创建结果或容器；只读SHA/空容器列表检查恢复响应后才启动首次科学调用，0重启/拉取/安装。

线性工作空间问题在保存切线上已消除，原DG2受压平衡和轮廓1%局部J门仍failed。
一次小残量不证明所有后续切线、非线性资格或生物学有效；三维/FSI/生长仍not_run。
唯一下一步待确认：从保留零载接受态，以余量100只续算圆环首个p/mu=0.02非线性被动态，原门限不变、首失败保全。
不重跑零载；通过后再裁决其余圆环压力点/粗细资格与真实外轮廓，不在本轮扩大运行。
见[执行记录](ventricle_fem_mumps_workspace_execution_v01.md)及
[结构/残量图与Notebook](../../PRL-results/ventricle_fem/f6s1s3_mumps_workspace_v01_20260918/index.html)。

## 历史：2026-09-18 F6-S1-S2诊断通过；直接故障为MUMPS工作空间不足

一次15.351秒单CPU容器，可靠保存同一初值的MUMPS/SuperLU报告。11组CSR/右端/映射与上轮相同，
5组前后FEM状态逐字节相同；无非线性平衡或状态更新、无自动重跑。
MUMPS返回KSP=-11、PC=3、INFOG(1)=-9、INFOG(2)=1321、ICNTL(14)=20。
`-9`为内部数值工作数组过小，而不是`-10`的数值奇异/零主元；容器OOMKilled=false。
同矩阵SuperLU独立残量3.16997e-13；估计1-范数条件数1.09e9，尺度/精度风险仍在。
这纠正了上轮未取得错误码时的假设优先级；不能将小残量视为非线性或1%体积资格。

诊断交付及19项独立复核passed；原DG2受压平衡与轮廓1%局部J门仍failed。
375父文件及120个F6-S1-R/S文件保持；53测试+21子测试passed。原失败包原位保留。
唯一下一步待确认：同一保存矩阵只将MUMPS ICNTL(14)由20改为100，一次线性验证，不更新状态；
通过后再另行恢复圆环非线性被动资格。轮廓、三维、FSI与生长未在本轮运行。
见[本轮执行](ventricle_fem_mixed_linear_replay_execution_v01.md)及
[结构与结果图](../../PRL-results/ventricle_fem/f6s1s2_linear_report_replay_v01_20260918/index.html)。

## 历史：2026-09-18 F6-S1-S保存矩阵可审计；求解器明细写出失败

用户同意先用理想化三维与morphoHeart公开资料，后续补自有实验并替换输入。
路线为固体资格→三维主动心室→双向FSI→基础生长→力学生长反馈→ECM反馈。
详见[已采纳决定](ventricle_development_fsg_idealized_public_data_decision_v01.md)；不是三维或生物学完成声明。

F6-S1-S只在上述圆环`p/mu=0.02`失败初值组装一次P2/DG2切线，并各做一次MUMPS与SuperLU尝试；
不调用非线性solve、不改变FEM状态或任何材料/几何/1%门。唯一一次16.327秒单CPU容器完成计算，
但`diagnosis.json`写出时，MUMPS报告子树中的非有限`inf`被严格JSON拒绝。原执行与诊断交付failed，
0自动重跑。KSP/PC/MUMPS INFOG与SuperLU结果没有持久化，科学根因必须记为not_evaluable。

保存的9,216阶CSR经独立复核：245,760个存储项，矩阵/右端有限、0零行/列、满结构秩，
896个6×6压力块均满秩，最小奇异值2.78956e-8。每单元局部p-u耦合秩为3，至少2,688个
高阶压力模态只受有限体积模量压力块约束；`uu/pp`块范数比3.13616e7。这排除明显结构缺陷并支持
尺度/小主元风险，但不能代替丢失的MUMPS错误码。轮廓、三维、FSI和生长仍not_run。

375个父文件和76个F6-S1-R源文件保持；51测试+21子测试passed。非有限序列化已加回归修复，
但未用于重跑。唯一下一步待确认：同一保留初值仅重放一次报告诊断，取得KSP/PC/MUMPS/SuperLU明细；
仍不求平衡或改参数，再裁决块缩放/静态消元。工程交付与科学裁决分开。
见[执行记录](ventricle_fem_mixed_linear_diagnosis_execution_v01.md)及
[外置矩阵证据与图件](../../PRL-results/ventricle_fem/f6s1s_linear_system_diagnosis_v01_20260918/index.html)。

## 历史：2026-09-17 F6-S1-Q细网格局部体积门仍失败

只补14164单元M1的p/mu=0及0.02两态，与已保存M0对照；一次40.770秒容器，0粗网格重跑。
非零载局部J峰值6.71167%→11.15248%，超限积分权重参考体积分数0.48565%→0.14100%。
腔面积变化20.10718%/20.12104%，只差0.01387个百分点；全局面积门通过而局部1%门失败。
热点靠近外边界、远离规范固定点，尚不能确定是几何局部效应还是体积约束离散主导。
零载passed，非零载仅local_volume失败；后续载荷、主动和生物验证not_run。

375父文件与50无关既有改动保持；73测试/21子测试通过，结构、应力、J粗细图和两帧GIF冻结。
新包已使用外置PRL-results；当前授权完成，不自动重复。下一步为边界/离散分离对照的合同与裁决。
见[执行记录](ventricle_fem_fenicsx_fine_diagnostic_execution_v01.md)及
[本地结果页](../../PRL-results/ventricle_fem/f6s1q_fine_diagnostic_v01_20260917/index.html)。

## 历史：2026-09-17 F6-S1-P局部体积门失败

本次科学调用按用户批准的800 MiB阶段预算执行，原3 GiB项目硬限与64 MiB停止空间保持。
复用合格candidate_0，无Gmsh重生成；3541/14164单元两级几何与存储准入通过。
一次25.932秒容器保存2态：零载passed；p/mu=0.02求解收敛但max|J−1|=6.71167%>1%，
按合同停止。1态接受、1态失败，细网格力学及其余8态not_run，无自动重跑。

弱压力残量3.22e-17、独立自由力1.69e-14，平均J−1=0.002858%；69个单元含超限积分点。
腔面积+20.10718%及明显变形只能作为失败态诊断。优先验证空间离散影响，不能放宽1%门。
308父文件不变；54测试+21子测试passed；结构/应力/局部J图及真实两帧GIF已验收。
下一科学切片待确认：只补尚未运行的细网格0和0.02两态，不重跑粗网格，不恢复主动。

用户已批准`E:\Temp-Projects\PRL-results`。后续新结果取消固定阶段体积限额，使用磁盘余量准入；
代码仓3 GiB硬限保留，旧结果不复制、不搬移、不删除。两轮主机读写及一次Docker挂载I/O passed，
571个既有FEM文件哈希保持，0新科学求解。此次存储变更不改变上述局部J failed，也不授权新的求解。
见[存储决定](external_result_store_decision_v01.md)及[工程验收](external_result_store_execution_v01.md)。

[执行记录](ventricle_fem_fenicsx_retained_passive_execution_v01.md) ·
[图件与动图](../results/ventricle_fem/f6s1p_retained_passive_v01_20260917/index.html)。

## 历史：2026-09-17 F6-S1-M网格通过，完整输出预算阻断

按用户确认的有界修复，将局部边长适配相邻层间距；三个预声明候选均通过原20度及全部几何门。
最小合格候选1958顶点/3541单元、最小角23.0435度；旧网格45个坏角单元降为0，
外轮廓IoU99.5882%及Hausdorff1.66974微米保持，内腔与层界仍为构造。

该候选两网格十态输出预测307.35 MiB，超过本轮256 MiB；更细两候选也超限。
一次正式容器13.698秒后停止，0平衡求解。原failed退出不改写，独立交付裁决为
geometry passed / storage blocked / mechanics not_run；不是材料失稳或RAM不足。
260个父证据文件保持，47测试及21子测试passed；Notebook结构/质量/预算图已验收。

唯一下一步待确认：复用raw/candidate_0_mesh.npz（不是停止时最后候选M0_input_mesh），
建议下一被动阶段预算384 MiB、另64 MiB停止空间、项目3 GiB硬限保持，执行原十态。
不重剖分、不改材料/载荷/门限，首个力学失败即停；主动收缩仍not_run。

[本次执行](ventricle_fem_fenicsx_thin_mesh_execution_v01.md) ·
[图件与Notebook](../results/ventricle_fem/f6s1m_thin_mesh_v01_20260917/index.html)。

## 历史：2026-09-17 F6-S1真实外轮廓在网格门停止

用户在普通推送main后要求继续项目。本轮完成源轮廓适配、显式几何输入接口、共形Gmsh网格与独立审计。
1042顶点/1828三角形；mask IoU=99.5882%、原始轮廓采样Hausdorff=1.66974微米，
正面积/闭合边/共享层界/标签/构造层面积通过。最小角12.8687度低于20度，45个单元未通过：
心内膜20、ECM25、心肌0。粗网格门失败后即停，0平衡求解，真实轮廓力学仍not_run。

唯一正式科学容器9.131秒，另有一次只读模块探针；无科学重跑、GPU、安装、删除或自动推送。
218个父包文件哈希不变；153测试和27子测试passed，不能替代尚未运行的力学门。
实际结构/质量分布图及Notebook保全，图中红色是坏角单元，不是应力。
下一步F6-S1-M只修薄构造层局部剖分，保持源多边形和原物理/阈值；新有界尝试待用户确认。

[执行记录](ventricle_fem_fenicsx_contour_passive_execution_v01.md) ·
[结构与诊断图](../results/ventricle_fem/f6s1_contour_passive_v01_20260917/index.html)。

## 最近通过的力学阶段：2026-09-17 FEniCSx理想圆环G0/G1/G2全部通过

896/3584单元两档P2/P1三角形，有限变形平面应变，未标定Neo-Hookean材料mu=1、kappa=1000。
内壁随动压力、外壁自由；三个固定自由度仅消除刚体运动。参考环向主动张力只作用于心肌层。

在p/mu=0或0.04、Ta/mu=0或0.10的四组终态中，细网格腔面积相对零载分别为：
零载0%、仅压力+9.897410%、仅主动−4.314957%、压力＋主动+4.556580%。
主动张力使同一压力下的腔面积响应降低5.340830个百分点；组合工况相对零载仍是扩张。
主动与组合末态max|J−1|分别0.007705%和0.005376%，两网格腔响应绝对差1.62e-7和1.51e-7。
82项汇总门、独立局部F/J/应力/力平衡与主动虚功门全部passed。

第一次容器保存10个被动态后遇到单行压力字段读取错误；原failed调用和raw完整保留。
修复读取后，按[有界续算范围](ventricle_fem_fenicsx_active_completion_contract_v01.md)只补16个未运行主动态。
共2次科学容器、26个唯一平衡态、0重复平衡求解，累计69.032秒；原门限和总预算没有放宽。
36个针对性测试及21子测试通过，四套结构/结果图和五个真实状态GIF已交付并通过样式及目检。
全仓既有图像依赖/绝对路径静态问题不在本次范围，不宣称全仓测试全部通过。

见[完成执行记录](ventricle_fem_fenicsx_active_completion_execution_v01.md)、
[独立复核](../results/ventricle_fem/f6s0_active_completion_v01_20260917/post_verification.json)、
[结果图与动图](../results/ventricle_fem/f6s0_active_completion_v01_20260917/index.html)。
原F5真实外轮廓失败保持；圆环通过不等于斑马鱼实验验证，也不是生理心动周期。
唯一下一步为F6-S1：将同一后端接回72 hpf Fish 4图像外轮廓，明确内腔/层界仍为构造几何，
先通过被动压力及1%局部J门，再加入主动收缩。F6-S1尚未运行。
0 GPU/DCM、拉取、安装、删除、提交或推送；Docker隔离目录和退出容器均保留。

## 历史工程阶段：2026-09-17 F6-S0主机运行时恢复

F6-S0采用本机已有FEniCSx作为新的FEM主后端，先在理想三层圆环上验证近不可压有限变形、
闭合随动压力和只作用于心肌层的方向性主动应力。它是开源后端资格，不是F5真实轮廓的重跑，
也不自动修复F5的局部体积失败。见[F6-S0合同](ventricle_fem_fenicsx_ring_active_contract_v01.md)。

Windows AF_UNIX error 1920阻断已按两批精确授权完成可逆隔离。Docker Desktop
`4.89.0 (238018)`、Engine `29.7.2`和运行中的WSL2后端已核验；本地
`dolfinx/dolfinx:v0.11.0`解析为固定image ID
`sha256:2ae4bfbc0d9077268880faf04c72750528bee986c94ab223a2c159969bd56fa8`。
四个v01/v02隔离目录保留，`Docker\wsl`未触碰；0删除、0拉取、0安装、0更新、0 GPU。
详见[运行时恢复记录](ventricle_fem_fenicsx_runtime_repair_execution_v01.md)。

该恢复只通过宿主运行时与本地镜像身份门。容器创建、DOLFINx导入、FFCx JIT、微型装配、
G1被动圆环和G2主动张力均为`not_run`，F6-S0科学执行尚未获得本轮授权。唯一下一步是另行确认
G0受限容器资格；G0失败即保全停止，通过后才进入G1，G1通过后才进入G2。

## 最近科学结果：2026-09-17 F5图像外轮廓被动压力资格failed

按[F5合同](ventricle_fem_contour_pressure_contract_v01.md)把F4已通过的曲线Q2/Q1和当前面随动压力接到72 hpf Fish 4保留外轮廓。只有外边界来自图像；腔面/层界按20/27、21/27、22/27、1同心缩放，静态图像被假定为零压无应力参考态。全层同一NH `mu=1, kappa=1000`，全部`uz=0`，内压`p/mu=0→0.08`；仍是平面应变资格，不是真实自由3D心室。

唯一正式单线程CPU调用完成144/288单元两档各五态，共10次新求解、0科学重跑。来源几何、参考映射、历史/初值链、独立场量、平衡、压力合力/力矩、虚功、跨z一致性、腔面积单调性和厚向全局响应比较均passed。细网格构造腔面积在`p/mu=.02/.08`增加19.83%/68.06%；两档末态仅差0.03315个百分点。

整体资格仍为failed：两档网格四个正压态均超过局部`|J−1|<=1%`门，fine最大偏差为18.83%/33.54%/44.80%/54.09%，末态`Jmin=.6903`、`Jmax=1.5409`。边界保持简单嵌套且全部J为正；保存J与独立重算最大差1.34e-13，不支持验证器误判。末态加权平均J约1.00015却有43.17%的Gauss点超过门，表明总体近不可压掩盖局部压缩/膨胀模态；径向细化没有改善峰值。

正式worker在独立验证写出failed后又因残差图symlog刻度样式异常退出1；原failure/progress不改，原正式清单以原字节和原SHA-256另存。随后仅修F5刻度并从保存态重绘一次，0新求解，raw/Newton/verification哈希不变；顶层manifest在交付末尾重建为完整最终清单。三套图通过外部样式检查和目检，明确显示`Qualification FAILED`。见[执行裁决](ventricle_fem_contour_pressure_execution_v01.md)、[模型](../docs/fem_contour_pressure_model.md)、[独立验证](../results/ventricle_fem/f5_contour_pressure_v01_20260917/verification.json)、[诊断](../results/ventricle_fem/f5_contour_pressure_v01_20260917/local_volume_diagnosis_v01.json)和[结果页](../results/ventricle_fem/f5_contour_pressure_v01_20260917/index.html)。

唯一下一步是另行冻结F5-R1：保持外轮廓、材料、腔面、载荷定义和1%门不变，分离检查周向细化、参考网格/曲率热点及体积约束离散。通过前不恢复主动收缩；材料/周期标定、真实内腔和壁厚、自由3D、血流、生长与ECM反馈均not_run。无GPU/DCM、删除、安装、提交、推送或项目外新建。

## 历史阶段：2026-09-17 F4曲线等参几何与随动压力资格passed

用户同意继续曲线/压力资格。按[F4合同](ventricle_fem_curved_pressure_contract_v01.md)一次单线程CPU调用完成两档8/24单元、各五个压力平衡态。Q2等参参考Jacobian、当前表面压力力及一致切线已接入原Q2/Q1有限变形内核，旧affine路径保留、材料及Newton门不变。参考四分圆柱A=1、B=1.25、H=0.5，两切面施加对称约束、所有uz=0；这是平面应变工程资格，不是自由3D心室。

NH mu=1、kappa=1000，内壁随动腔压0→0.08，无主动或端盖压力。峰值内壁参考面积加权径向位移coarse=0.144521854、fine=0.144525272；两档差0.00236493%，与不可压解析极限差0.08370%/0.08607%，均通过预设5%门。全部态最坏局部|J−1|0.04452%（fine0.02973%），最大独立自由力残差4.14e-12，弱压力残差1.28e-13，八项独立门全部passed。不可压参照不是相同有限kappa问题的精确解，不宣称网格误差单调收敛。

十态完整保留，求解30.633秒、含验证绘图worker50.099秒，CLI退出0，无重试或后处理补跑。228开发测试+36子测试通过，三套结构/力学/真实五态图通过样式及目检。父F3-B62文件与F3-C38文件及manifest原哈希不变；所有历史失败保持。见[执行](ventricle_fem_curved_pressure_execution_v01.md)、[模型](../docs/fem_curved_pressure_model.md)、[独立验证](../results/ventricle_fem/f4_curved_pressure_v01_20260917/verification.json)和[结果图](../results/ventricle_fem/f4_curved_pressure_v01_20260917/index.html)。

下一步接回已有真实外轮廓，明确构造内腔/厚度/层界与面外约束，先验证被动加载再恢复方向性主动收缩，新阶段not_run。不重做块梁/圆柱矩阵；无GPU/DCM、删除、安装、提交、推送或项目外新建。真实自由3D心室、材料/周期标定、血流、生长及ECM反馈仍not_run。

## 历史阶段：2026-09-17 F3-C初值修复及有限变形组合工程资格passed

按[补充合同](ventricle_fem_rotation_repair_contract_v01.md)，只补四个缺失刚转15°/30°/45°/60°和一次60°固定内部扰动恢复。一次单线程CPU调用、五次新求解、3.376秒；原13完整工况不重算，0°状态与history逐字段沿用。原F3-B的62文件与manifest哈希不变，原failed保留。

初值修复只增加显式参考Q2位移增量延拓，内部27节点仍自由，压力、原材料和Newton门不改。五状态最大Green应变4.774e-15、总Cauchy应力7.911e-15、|J−1|4.885e-15。四个无扰动预测本身满足平衡；额外固定非仿射内部扰动经两次真实Newton更新，残差6.522e-3→2.419e-5→3.333e-11、恢复位移误差2.558e-12。独立六门及结合父13工况的组合资格passed，不宣称任意初值/复杂网格均通过。

136项针对性测试与34个subtests通过；图件只读取保存状态。原控制器科学计算和独立验证passed，随后因log轴格式退出1；原failure/progress和原manifest保留，仅修绘图刻度后重绘通过，没有科学重试。见[执行裁决](ventricle_fem_rotation_repair_execution_v01.md)、[独立验证](../results/ventricle_fem/f3c_rotation_repair_v01_20260917/verification.json)、[图件](../results/ventricle_fem/f3c_rotation_repair_v01_20260917/index.html)及[最终交付审计](../results/ventricle_fem/f3c_rotation_repair_v01_20260917/postrender_execution_v01.json)。

唯一下一步是曲线心壁等参几何与腔面随动压力资格，再回到已有真实轮廓；当前常Jacobian直方块实现不能直接用于任意曲线网格。本次不是三维真实心室或斑马鱼实验验证；旧F2/F3-A失败不改写，材料/时间标定、生长与ECM反馈仍not_run。新科学阶段尚未启动；0 GPU、0 DCM、0自动科学重试，无删除、安装、提交、推送或项目外文件新建。

## 历史阶段：2026-09-17 F3-B三维有限变形已实现，13工况通过，刚转初猜失败

用户同意升级非线性FEM。本次按[F3-B合同](ventricle_fem_finite_strain_contract_v01.md)实现三维Q2/Q1混合实体、Neo-Hookean / Guccione型等容超弹性及规定的第二Piola型纤维主动张力。对象是无量纲工程块/梁，不是真实心室，也不是F3-A二维轮廓的非线性解。

一次单线程CPU正式调用完成13个完整工况和刚转0°，共78/82个有效状态。13完整工况均通过独立复核；Guccione主动块峰值轴缩16.857%、横向各增厚9.645%、体积变化−0.046106%；NH解析最大归一误差2.705e-10。梁两级网格末端位移差3.021%/3.030%，两κ细梁差0.343%，符合本次5%门。细梁局部|J−1|仍约2.123%，不能称为各积分点严格不可压或复杂心室已合格。

刚转15°时，98边界节点已转，27内部节点却仍为0°初猜；216 Gauss点中12个J≤0，minJ=-1.183927，在本构求值及Newton前停止。这是非齐次Dirichlet初值提升缺失，不是材料失稳证据。阶段整体failed；配置矩阵存在不代表82状态已完成，材料点客观性不能替代缺失FE刚转资格。最后有效0°检查点与被拒绝初猜分开保全。

见[模型](../docs/fem_finite_strain_model.md)、[执行与诊断](ventricle_fem_finite_strain_execution_v01.md)、[独立验证](../results/ventricle_fem/f3b_finite_strain_v01_20260917/verification.json)及[结构/力学/五状态图](../results/ventricle_fem/f3b_finite_strain_v01_20260917/index.html)。修订仅限后处理JSON标量序列化及失败包展示，原科学源和raw不变，0科学重试。旧F2/F3-A仍为原证据状态。

唯一下一步是可行内部位移预测与前态到非零边界的集成回归，之后经明确授权仅补刚转资格，不重复已完成13工况。通过前不启动真实心室、心腔压力或新参数扫描。材料标定、生理时间、三维真实心室、生长/ECM反馈等仍not_run。0 GPU、0 DCM，无删除、安装、提交或推送。

## 历史阶段：2026-09-17 F3-A固定输入细化工程passed，响应收敛和小应变门failed

用户同意继续网格及有限变形资格并询问来源。本次已澄清：材料E/E_ref=1/0.5/2.5和nu=0.30是F0工程假设；模型仍是二维平面应变；3%余弦激活为规定准静态相位，没有实测周期/心率，见[来源说明](../docs/fem_model_sources_and_time.md)。

按[F3-A合同](ventricle_fem_fixed_mesh_contract_v01.md)冻结原F2 G1的多边形、层界、主动张量和原节点规范，做两次共享边中点四分。一次单线程CPU调用完成6,144/24,576/98,304单元、每级5个真实静力状态。原F2相应状态重放误差0；独立几何、材料/主动继承、场量、平衡和嵌套能量检查passed。

构造腔面积峰值变化为-2.6324%/-1.6332%/-0.8853%；最后两档差0.74791个百分点、相对84.481%，未通过全局响应门。最大应变分量升至11.306%，小应变门failed。固定输入后仍明显敏感，确认存在FE离散贡献，不再把F2差异全部归给轮廓/载荷变化。L2保存解中Green应变二次项范数为线性项的17.762%，只是有限变形必要性诊断，不是已运行有限变形。

见[执行记录](ventricle_fem_fixed_mesh_execution_v01.md)、[独立验证](../results/ventricle_fem/f3a_fixed_mesh_v01_20260917/verification.json)和[结构/响应/应力/五状态图](../results/ventricle_fem/f3a_fixed_mesh_v01_20260917/index.html)。本轮不自动增加P1细化级；下一子阶段应以小型制造解/弯曲基准分离薄层网格和单元阶次，并验证有限变形本构/客观性/主动加载，再回到真实轮廓。有限变形、材料标定、三维心室、生理周期、腔压、血流、生长与反馈均not_run。只采用FEM，0 GPU、0 DCM、无删除或安装。

## 历史阶段：2026-09-17 FEM唯一主线；F2真实外轮廓求解完成，数值资格failed

用户明确排除本项目所有DCM前向建模；见[FEM唯一主线决定](ventricle_fem_only_measured_contour_decision_v01.md)。原DCM路线、恢复与比较停止，历史证据不删除。精细细胞分割退出主线前置条件，原候选资格保持原状态，不能因此升级为真值。

按[F2合同](ventricle_fem_measured_contour_contract_v01.md)从已验收72 hpf Fish 4组织mask的最大占据XY切片（索引39）提取真实外轮廓；假设腔面及心内膜/ECM/心肌界面，沿用峰值3%主动应变、零牵引、无压自由边界。一次单线程CPU调用完成G0/G1各41个真实状态，0 DCM、0 GPU、0科学重跑。

G1构造腔面积峰值变化-2.6324%、外面积-2.5128%、最大位移3.0053 µm；最大应变6.8936%，超过5%小应变门。G0--G1腔面积变化差0.96197个百分点，超过0.2个百分点门。几何、KKT平衡、场量独立复核和正面积门通过，但整体资格为failed；不把求解完成当作模型已收敛或实验吻合。见[执行与失败记录](ventricle_fem_measured_contour_execution_v01.md)、[验证](../results/ventricle_fem/f2_measured_contour_v01_20260917/verification.json)与[结构/结果/动图](../results/ventricle_fem/f2_measured_contour_v01_20260917/index.html)。

下一步是固定该真实轮廓的FEM网格与有限变形资格，不是DCM，也不是等待逐细胞实例分割。完整三维跳动、实测内部腔面/层界、腔压、材料标定、血流、生长和反馈仍not_run。旧章节的“唯一下一步/当前”仅描述当时状态，均须服从本节最新决定。

## 历史阶段：2026-09-17 F1-Seg-A 候选工程门 passed，人工验证 not_run

按[候选分割合同](ventricle_fem_surface_cell_segmentation_candidate_contract_v01.md)直接读取 Zenodo `15509350` 的72 hpf处理后栈。Fish 4 是唯一开发样本：三个确定性曲面 ROI 比较12组预登记参数，冻结 `cfg03`；Fish 3/5 随后以同一配置哈希各运行一次，没有查看留出结果后调参。作者 surface point 只用于局部切平面，不能当作细胞中心。

G0曲面提取 `passed`：三鱼各3个ROI，物理尺度一致，局部基正交误差小于 `1e-6`。G1候选工程门 `passed`：Fish 3/4/5 分别从101/97/90个分区中保留32/39/28个有限候选；面积中位数为50.404/54.331/45.126 µm²，跨鱼最大/最小1.204；长宽比中位数跨鱼最大/最小1.112。配置哈希一致，结果包8,409,761 bytes，低于64 MiB。见[执行记录](ventricle_fem_surface_cell_segmentation_candidate_execution_v01.md)和[结果包](../results/ventricle_fem/f1seg_surface_cell_candidate_v01_20260917/README.md)。

G1只证明工程候选可复算。九ROI审计图显示部分边界与闭合高亮信号一致，但条带、模糊区和浅层曲面投影混叠同样会被分水岭闭合。项目没有独立人工实例标签，G2固定为`not_run`，总体为`blocked_human_validation`。这些候选不得称为真实细胞网格，也不得直接进入真实形态FEM/DCM。

唯一下一步是 F1-Seg-B：冻结 Fish 3/5 的少量 ROI，由独立人工描绘可辨识实例边界，再一次性评价计数误差、边界重合、漏分割、并分割和闭合率。通过前不启动真实形态 FEM/DCM、材料标定、生长、ECM反馈或FSI。

## 上一阶段：2026-09-16 F1-R 真实静态形态数据资格 passed

公开包 `Data.zip` 为8,013,661,132 bytes，本地MD5与上游 `fc94a41c8654b817cdbe5cd131f4a90c` 一致；522个成员没有危险路径或链接，未整包解压，也未执行上游代码。冻结主样本 Fish 4 的110×1024×1024栈具有 `0.2071606 × 0.2071606 × 1 µm` 尺度；507个表面点带法向、director和局部nematic order。该阶段限定为 `real_static_morphology_resegmentable`；组织mask不是实例标签、Marker_X身份冲突未解、停跳静态数据不提供周期运动。见[执行记录](ventricle_fem_measured_cell_shape_data_qualification_execution_v01.md)。

## 上一阶段：2026-09-16 F1-S 合成长轴方向场敏感性 passed，真实细胞形态场当时 not_run

用户指出项目目前没有真实细胞形态场，并同意先完成均一场与受控随机场的 FEM 对照。按[合同](ventricle_fem_synthetic_orientation_sensitivity_contract_v01.md)完成唯一一次正式单线程 CPU 阶段调用：在 F0 同一二维三层椭圆环中，将心肌标记为2×24个材料赋值斑块；均一组沿局部切向，随机组使用固定种子、均值为零、RMS 7.655°、最大18°的方向偏移。两组几何、被动材料、主动应变幅度、相位和边界完全相同，斑块不是显式细胞或实验分割。

G1峰值位移场相对差异为7.947%，心肌等效应力场面积加权相对差异为12.597%；对应G0--G1漂移为0.137%和0.814%，两项均通过预注册的1%门和两倍离散漂移门。uniform/random峰值腔面积变化分别为-5.9322%/-5.8857%，只相差0.0465个百分点。因此当前证据支持“合成长轴排列明显重分配局部位移与应力”，不支持“该随机场显著改变整体泵血”。随机组应力CV没有增加，也不能声称随机性必然增强应力集中。

四条轨迹各保存41个真实准静态状态；全部有限、无翻转，最大应变0.04643，最大独立后向残差3.33e-16。独立验证从保存状态重建方向场并重算应变、应力、面内压力、腔面积、KKT残差和配对指标，误差均为0。结构图、裁决图已目检，GIF独立读取为41帧。见[执行记录](ventricle_fem_synthetic_orientation_sensitivity_execution_v01.md)和[结果页](../results/ventricle_fem/f1s_synthetic_orientation_v01_20260916/index.html)。

本轮只通过合成方向接口门。其当时的唯一下一步是F1-R真实形态数据资格；该数据门现已由上文记录完成，但真实逐细胞分割和`measured / uniform-mean / shuffled`映射仍未运行。不得继续调大合成扰动替代数据。

## 上一阶段：2026-09-16 二维三层主动 FEM 工程基线 passed，斑马鱼标定 not_run

用户在此前暂停 FEM 后明确要求先做 FEM 尝试。按[合同](ventricle_fem_active_elliptic_pilot_contract_v01.md)完成一次正式单线程 CPU 阶段调用，内部求解 G0/G1 两级共形三层椭圆环；每级保存 41 个规定激活相位。模型由心内膜、薄 ECM 和心肌组成，仅心肌施加峰值 0.03 的局部切向主动本征应变；内外表面无牵引、无腔压，所有量为无量纲合成量。

独立验证全部通过：G1 峰值腔面积变化 -5.9322%，最大绝对应变 0.04559，最小变形后三角形面积 5.001e-4；最大归一化后向残差 2.17e-16。G0/G1 峰值响应差 7.12e-4，低于 2e-3 门。独立重算应变、应力和腔面积误差均为 0，41 状态 GIF 和两张正式图已目检。见[执行记录](ventricle_fem_active_elliptic_pilot_execution_v01.md)和[结果包](../results/ventricle_fem/f0_active_elliptic_pilot_v01_20260916/README.md)。

该通过只建立小应变连续体 FEM 工程路径。它没有离散细胞、随机形态、血流、腔压或真实几何，不能评价不规则细胞形态作用，也不等于斑马鱼实验吻合或 FEM 优于 DCM。现有公开 GFP 栈缺少冻结尺度、周期配准和心室分割，未用于标定。

唯一下一步是 F1 实验数据资格：先冻结发育阶段、尺度、壁/腔分割、周期配准和留出形变观测，再制定有限变形、真实几何和明确负载的 FEM 合同。F1 尚未授权，不能继续以合成参数调图。

## 上一状态：2026-09-16 规则2×2第0级进入显式松弛极限环，后续载荷未运行

按[合同](ventricle_regular_2x2_load_hold_contract_v01.md)复用已验收长轴单细胞，建立四个完全相同细胞的规则2×2 DCM小片；方向性骨架和显式黏附—排斥接触开启，无随机性、收缩、永久连接或参考形状膜能。第0级盒壁不移动，唯一一次单线程CPU运行完成1200请求步、2993接受子步和9个真实状态，见[执行记录](ventricle_regular_2x2_load_hold_execution_v01.md)和[结果包](../results/ventricle_z1/z1_regular_2x2_load_hold_v01_20260916/verification.json)。

数值安全通过：独立交叉0，最小角46.36°，最大相对本级输入体积变化0.786%，最小接触求积间隙0.0732，零回退。静力门失败：初始残力0.00255，第1步降到0.001998，但第5步过冲到0.338，末态0.3428；最初/最后200子步平均残力0.2498/0.2467，没有衰减。根因是显式过阻尼更新只按几何安全和固定边长比例限位，没有候选态残力下降门，`dt=0.25`过冲后形成有限振幅极限环。延长同参数运行无依据。

第0级虽报告四个活跃胞对，但它们只是0.35截断范围内的黏附求积；最终真实曲面仍相距0.0933，不能称为连续组织界面。在该 R0-B 裁决时，0.20–0.40四级、规则5×5、随机异质性、收缩和FEM均为`not_run`；其后用户明确恢复了上文记录的 F0 FEM 尝试。

该阶段为 DCM 路线留下的下一步是冻结R0-C最小收敛资格：同一第0级输入增加残力下降回退/线搜索，以两档稳定步长或等效阻尼检查轨迹一致性，并用真实间距、接触面积和牵引共同定义连续接触。不得直接重跑R0-B、增加拥挤或加入随机性。

## 上一阶段：2026-09-16 R0-A回退/接触工程路径passed，规则片与FEM not_run

按[共同极限合同](ventricle_regular_dcm_fem_common_limit_contract_v01.md)完成原位坐标事务回退、接触求积间隙限步、原生几何/快照自测和两细胞有界压近轨迹，见[执行记录](ventricle_regular_dcm_fem_common_limit_r0a_execution_v01.md)。21个真实状态全部安全，旧的全曲面距离步长地板未触发；但胞间距由0.070增至0.0805、末态残力0.2227，未进入近零接触或平衡。因此该结果只通过工程子门，不能作为组织或FEM比较对象。

## 当前：2026-09-16 准静态双倍目标在接触形成处触发回退步长下限，K15未运行

按[合同](ventricle_myocardial_crowded_quasistatic_growth_contract_v01.md)完成两个K30数值控制，见[执行记录](ventricle_myocardial_crowded_quasistatic_growth_execution_v01.md)和[失败结果包](../results/ventricle_z1/z1_myo_crowded_quasistatic_growth_v01_20260916/README.md)。初始25胞网格、异质目标和固定盒身份通过；最终目标仍为逐胞体积×2、面积×`2^(2/3)`、q不变。粗/精细接触控制分别使用0.40/0.05和0.20/0.01离散/运动尺度，单线程CPU、0 GPU、0自动重跑。

两组均只保留状态0。粗控制完成33个接受子步，到目标分数0.55417、31个活跃细胞对时停止；精细控制完成77个接受子步，到0.57917、35对时停止。两者最后胞间曲面距离均约1.0e-8，接受步长分别缩到2.88e-10和1.40e-10，最终同以`crowded-box backtracked step reached the frozen floor`退出。此时接触积分最小有符号间隙仍为正值0.02224/0.008754，最小角45.68°/46.25°、壁面余量0.325/0.284均正常。

因此首要问题不是盒壁或已验证的材料刚度，而是全三角距离守卫与接触积分的几何口径不一致：真实接触接近时，守卫先把步长压到0。目标也在自由力约0.75–0.79时继续增长，不是严格的载荷—平衡延拓。另有回退快照`cell→face→cell`强引用循环的性能缺陷，下一次运行前必须消除。K30粗细均未完成，数值收敛`failed`；K15按条件门为`not_run`，材料敏感性不可评价。静力平衡、最终接触网络、生物验证和收缩均未完成。

唯一下一步是冻结X2-C接触形成资格：原位事务回退；连续无穿透接触判据；每个目标增量先松弛到残力门并保存网格；失败前保存最后有效态。工程探针通过后才可另立create-only结果比较K30/K15，不能直接放宽距离门或重跑。

## 当前：2026-09-16 双倍异质参考体积在状态1前触发正间隙屏障，未形成组织态

按[合同](ventricle_myocardial_crowded_volume_x2_contract_v01.md)完成一次单线程CPU、0 GPU、0自动重跑试验，见[执行记录](ventricle_myocardial_crowded_volume_x2_execution_v01.md)和[失败结果包](../results/ventricle_z1/z1_myo_crowded_volume_x2_v01_20260916/README.md)。25胞初始网格、材料/几何异质性、0.14间隙、接触、盒壁和5%平面压缩均与上一随机目标条件相同；每胞参考体积精确乘2、参考面积乘 `2^(2/3)`，逐胞q不变。目标与初始身份门全部通过。

正式求解器只调用1次，在第一个0.02请求步完成前以`positive-gap barrier requires disjoint surfaces`停止。仅保留状态0和4条接受子步：状态0最大节点力34.6068、平均压力20.7894；最后接受坐标0.00494091、体积变化10.2547%、活跃胞对29、最小角46.55°、壁面余量0.3449、功耗散残差2.19e-16；审计中出现8.97e5力尖峰。由于没有状态1–8，数值保存态安全`failed`，静力平衡和接触网络均`unknown`，29对接触不得解释为形成组织。

当前结论是：把参考体积从基线瞬时跳到2倍产生过强初始压力和多体接触碰撞，现有积分/正间隙屏障组合不能安全穿过接触形成事件。目标总体积约占最终盒体积81.16%，本结果不证明准静态增长一定失败，也不证明最终几何可实现。

唯一下一步是先冻结“准静态目标增长资格”合同：体积目标尺度从1逐级延拓到2，面积按尺度的三分之二次方同步变化，并预注册增长步、接触事件步长、每级保存/回退和停止门。当前一次运行授权已消费，不能直接重跑、放宽门限或进入收缩。

## 上一阶段：2026-09-16 高拥挤5×5统一/随机参考目标配对数值安全passed，静力平衡与接触网络failed

按[合同](ventricle_myocardial_crowded_target_pair_contract_v01.md)完成两个预登记条件各一次单线程CPU运行，见[执行记录](ventricle_myocardial_crowded_target_pair_execution_v01.md)和[结果包](../results/ventricle_z1/z1_myo_crowded_target_pair_v01_20260916/summary.json)。两组使用同一个25胞初态、材料/几何异质性、盒壁与接触参数；初始相邻AABB间隙从0.24降至0.14。统一组每胞使用相同参考体积/面积，随机组在完全相同总体均值下使用逐胞冻结目标（体积CV 2.858%、面积CV 2.316%）。无收缩、固定节点、永久胞间连接或参考形状膜能。

两组各9个真实状态的数值安全均`passed`：独立交叉筛查为0，最大相对自身初态体积变化分别7.338%/9.978%，最小三角角39.89°/40.35°，无穿壁，功—耗散门通过。最终最大节点力0.06215/0.06001均高于1e-3，静力平衡均`failed`。最终40个预登记网格邻接中均只有17对活跃，且同有细胞ID 4孤立，接触网络均`failed`。

相对上一0.24间隙pilot，活跃接触由10对增至17对、最小胞间面距由0.2097降至0.1045/0.0768，说明拥挤确实增强，但仍不是汇合心肌层。随机目标组最终体积CV为2.857%，统一目标组仅0.027%，目标因子与最终配对体积差相关系数0.99999995；然而压力总体分布、平均长轴跨度和接触网络几乎不变。因此当前随机目标主要建立尺寸差异，尚未产生明显不规则多边形形态或贯通传力。

唯一下一步是冻结“实际曲面距离控制的几何汇合初始化”合同：使40个正交邻接在无穿透下进入受控接触带，同时保持本轮随机目标、材料、5%盒压缩和接触参数不变。不得自动加大随机幅度、延长松弛或启动收缩。

## 上一阶段：2026-09-16 透明薄盒5×5异质心肌细胞拥挤pilot数值安全passed，静力平衡failed

按[合同](ventricle_myocardial_crowded_box_pilot_contract_v01.md)完成一次单线程CPU运行，见[执行记录](ventricle_myocardial_crowded_box_pilot_execution_v01.md)和[结果包](../results/ventricle_z1/z1_myo_crowded_box_pilot_v01_20260916/summary.json)。模型含25个独立闭合长轴细胞，无固定节点、无永久胞间材料连接、无主动缩短；x/y盒尺寸缓慢缩小5%，z高度不变。

数值安全pilot通过：9个真实状态完整，保存态最小胞间面距0.2097，独立交叉筛查0，最大体积误差0.6003%，最小三角角39.75°。投影占据率从0.6506增至0.6991，最终10对细胞进入有效接触，平均去平移形变RMS为0.09639。

结构并未形成汇合心肌层：5×5阵列仍较规则，40个最近邻对仅10对有效接触；接触牵引峰值约2.50e-4，显著低于盒壁牵引峰值约0.169，载荷主要由边界承受。最终最大节点力0.06301高于1e-3，静力平衡为`failed`。因此当前结果只能称为安全的有限松弛拥挤态；生物学验证与收缩均`not_run`。

唯一下一步是先冻结第二个拥挤资格工况，优先只减小初始胞间间隙并保持5%盒压缩与现有力学参数不变；不得自动重跑或同时改变多项拥挤控制量。

## 当前：2026-09-16 异质五细胞链数值稳态门通过，字段拆分门failed，v02 not_run

按[合同](ventricle_myocardial_heterogeneous_row_equilibrium_contract_v01.md)完成一次单线程CPU运行，见[执行记录](ventricle_myocardial_heterogeneous_row_equilibrium_execution_v01.md)和[结果包](../results/ventricle_z1/z1_myo_heterogeneous_row_equilibrium_v01_20260916/summary.json)。模型使用此前长轴单细胞真实末态网格，5胞首尾材料连接、两端夹持；固定种子赋予细胞间长宽厚、低频起伏、体积模量、表面张力、面积模量和骨架预应力差异。未使用参考形状膜能，未开启周期收缩。

稳态与安全数值达到预注册门：最终自由力4.052e-4，体积误差0.391%，最小角45.07°，固定端无位移，最终三轴跨度保留非零细胞间差异。但旧输出把零缩短下的被动轴向弹簧恢复力也记为`contraction_traction`，其最大值0.00609，不满足合同要求的0，因此总裁决仍为`failed`，不得称为验收通过。

源码已在不改变总力的前提下，将被动`axial_traction`与主动缩短增量`contraction_traction`代数拆分；7项针对性测试、quick 42/42与C++编译通过，未重新运行。唯一下一步是用户明确批准全新create-only v02同参数单次运行；v02通过后才进入收缩。

## 当前：2026-09-16 匹配心肌片几何passed，组合资格failed，松弛not_run

按[合同](ventricle_myocardial_sheet_pair_contract_v01.md)完成规则/不规则4×4真实闭合DCM初态及18次静态调用，见[执行报告](ventricle_myocardial_sheet_pair_execution_v01.md)和[结果页](../results/ventricle_z1/z1_myo_sheet_pair_v01_20260916/index.html)。两组同体积/材料，固定两侧外端面，上下和横向自由；几何安全passed。

平移方向组合力能差分误差1.194e-5/1.276e-5未达1e-6门，因此短程松弛停止于准入、未执行。误差随eps缩小10倍下降约80–95倍，不能据此确定接触公式错误。唯一下一步是冻结更小尺度与非对称方向的有限判别矩阵；不自动修公式或放宽门限。初始牵引差异同时受法向间距/面积/储能变化影响，不能解读成组织形态效应。

## 历史：2026-09-16 被动力学修复passed（先于匹配片层）

用户同意将第一目标明确为规则/不规则三维DCM心肌单层的匹配对照。已按[重定位与修复合同](ventricle_myocardial_irregular_sheet_recenter_v01.md)完成真实内核RED/GREEN测试；[执行报告](ventricle_myocardial_passive_repair_execution_v01.md)与[结果页](../results/ventricle_z1/z1_myo_passive_audit_v01_20260916/index.html)为当前证据。

张力/压力/面积能账本已修复，面积力补齐当前体积依赖的链式导数；24组差分资格通过，独立复算最差组3.6172e-9，原门1e-6。新编译双胞入口要求共同显式Q0，禁止逐胞从形状推回材料目标。此次修复改变新轨迹，不改判任何旧结果；旧二进制保留，新程序在b/myo-mechanics-v01。

更正：低接触功率不能排除接触对慢模态的影响，骨架功率大也不能单独证明残力根因。以下2026-09-15历史总结中的相反推断已撤回；其原始数据、拟合与负结果仍保留。

唯一下一步是规则/不规则4×4匹配几何及新力学+接触组合预检，然后有界短程组织维持。不再默认追加双胞尾部延长。组织对照、周期收缩、心内膜、ECM仍not_run，生物验证blocked。无删除、GPU或提交；最终工程检查及存储在结果包acceptance.json登记。

## 历史：2026-09-15 清理和Q passed，扩展平衡failed，残力渐近未解析

旧Git已永久删除并替换为无远端`codex/clean-baseline`两提交基线；第一根提交`d53ca553`保全迁移前证据。当前Python统一入口、根级CMake和8个C++应用的正常库边界已通过构建与回归。Batch 5B同一冻结清单的其余30目标已全部永久删除：241文件、8子目录、133,839,393逻辑字节，保护路径无缺失、未处理未授权路径。

正式Q 39/39调用并独立裁决`passed`：16胞静态接触组装中位加速2.5203×，2胞candidate/baseline比0.9432；9组逐节点力/能量/支撑等价且21/21旧回归通过。扩展E四条双胞轨迹均安全到算法坐标20，20个事件网格无穿透、包含或自交见证，粗细步长位移误差小于0.019%；但末态自由力0.01775–0.02133高于0.001门，严格裁决`failed_equilibrium`。

绘图后的验收扫描约1.346 GB，仍低于2 GiB目标和3 GiB硬限。全过程单线程CPU、0 GPU、0自动重跑。结构、残力、安全质量、曲率/体积约束压力/接触牵引及两份五状态动图已生成并视觉验收；算法坐标不是生理时间。

随后只读既有四条轨迹完成末态残力诊断，0次求解器调用。单一零渐近指数的留出误差显著较差；坐标10–20表观截距为END约0.00856、SIDE约0.01241，但冻结的慢双指数判据未在全部窗口通过，正式类别为`not_resolved_by_frozen_rules`。末态最大残力节点的接触力均为0，接触功率绝对占比低于0.7%；持续骨架功率占END约93.3%、SIDE约72.1%，因此接触不是当前限速项。诊断过程和独立12项复核`passed`，静态平衡、父Z1和生物验证仍`blocked`。

依用户批准的[清理总合同](repository_cleanup_master_contract_v01.md)，科研阶段暂停；唯一活动主线仍为SimuCell3D心肌→心内膜→ECM。只读盘点登记34,406个普通文件、8,127,368,982 bytes，每文件含路径、字节、SHA-256和分类；目录reparse point不跟随。Batch 1为`passed`，只代表仓库盘点。

[Batch 2精确提案](repository_cleanup_batch02_deletion_proposal_v01.md)列出的30个缓存、非当前构建及无引用编译烟测路径已经删除。首次`Remove-Item`尝试在进程创建前被环境策略拒绝，记录为[v01](repository_cleanup_batch02_execution_v01.md)；用户随后单独授权同一30路径使用`System.IO.Directory.Delete`，[v02](repository_cleanup_batch02_execution_v02.md)完成30/30、4,338文件、287,147,295 bytes删除。当前活动构建`b/z1m0a`、SimuCell3D源码/许可证、正式results、data与治理记录均存在。

Batch 2裁决`passed`。[Batch 3A执行](repository_cleanup_batch03a_execution_v01.md)也已`passed`：169个精选文件、55,720,718 bytes迁入证据区并通过源/目标及Batch 1基线双重哈希核对，随后19/19旧Hybrid、Route H、Paper2、NCS/FEM结果目录、14,089文件、1,640,809,991 bytes永久删除；净释放1,585,089,273 bytes。旧路径解释见[退役映射](repository_cleanup_retired_path_map_v01.md)。

[Batch 3B执行](repository_cleanup_batch03b_execution_v01.md)已`passed`：保留13个当前/关键Z1包，永久删除42个被取代Z1包和3个本轮缓存，共45路径、1,275文件、490,593,270 bytes（467.866 MiB）。删除后、最终文档写入前工作区为14,982个普通文件、5,773,416,149 bytes（5.377 GiB）；13个保留包、114项当前结果哈希、14项来源哈希和13项无缓存回归通过。首次回归暴露一条指向已退役dev01结果的测试依赖，现已改为读取保留的正式包，未修改力学实现或门限。科学下一步接触性能优化保持暂停，未运行新模型。

[Batch 4架构审计](repository_cleanup_batch04_architecture_audit_v01.md)已`passed`。静态盘点覆盖210个代码/构建文件、3,868,810 bytes：145个脚本中136个带版本号；当前8个长程入口传递到15个脚本；8个C++应用源通过重命名`main`包含旧`.cpp`；32个代码文件仍有75处退役结果路径；默认pytest收集266项但退役Paper2/FEniCSx测试因缺少`basix`产生2个collection error。

用户已确认并完成[候选3退出前安全切片](repository_cleanup_batch04_candidate03_exit_safe_slice_execution_v01.md)及[永久删除](repository_cleanup_batch04_candidate03_deletion_execution_v01.md)：两个宿主包装已保全，退役路线精选源码现共16文件、369,160 bytes；冻结的8目录＋30文件共38路径、61文件、1,541,224 bytes已永久删除，剩余0。删除前35个tracked-clean、26个untracked、0修改、0 reparse；删除后32/32保护身份、范围外Git变化0，默认pytest与显式quick均19/19通过，默认包发现仅`prl`和`prl.verification`。本批删除授权已消费，科学状态和3 GiB存储`blocked`不变。

[清理收口与科学重启一次性审批包](repository_cleanup_closure_and_science_restart_proposal_v01.md)已按精确授权完成清理收口。旧`.git`首次因ReadOnly对象部分失败并如实停止；补充授权后仅在同一目标内清除9,994/9,994普通文件的ReadOnly属性并完成永久替换。冻结清单其余30目标也已永久删除，未处理未授权路径。本地`codex/clean-baseline`为两提交、远端0；Batch 6全构建、测试、证据、链接和存储验收均`passed`。现在仅执行已授权的单线程CPU正式Q；Q通过才进入扩展平衡E，GPU未启动。

## 历史下一步：最小尾部判别延长（已被2026-09-16主线重定位取代）

现有数据已完成力分解并排除接触限速，但有限坐标尚不能区分正平台与更慢的零渐近模态。下一合同应仅覆盖END/SIDE细步长的有界延长，在预设坐标比较局部衰减率、表观截距稳定性和骨架功率；若慢率不恢复且截距稳定，再讨论持续预应力相容性修订。不得直接进入4×4动力学、心内膜、ECM或自动延长。

[诊断执行报告](ventricle_terminal_residual_diagnosis_execution_v01.md)、[诊断结果](../results/ventricle_z1/z1_myo_terminal_residual_diagnosis_v01_20260915/diagnosis.json)、[独立复核](../results/ventricle_z1/z1_myo_terminal_residual_diagnosis_v01_20260915/verification.json)、[图像导航](../results/ventricle_z1/z1_myo_terminal_residual_diagnosis_v01_20260915/README.md)。

## 上一阶段：2026-09-14 长程双胞数值资格passed，未达到静态平衡

依用户“然后你继续任务”和[长程合同](ventricle_myocardial_long_doublet_contract_v01.md)，4条END/SIDE步长对照完成至算法坐标5，另完成2条实际安全裁切轨迹和2/4/16胞各一次静态计时。未改唯一接触核心或原动力学可执行文件，增加外部折叠监测和应用层计时探针。全部CPU；16胞动力学及随机形态not_run。

数值资格passed：体积误差<=.334%，最小角>=22.516°，步长末态位移差<=.054%，事件网格无穿透见证；不构成任意网格不折叠证明。末态残力约.104，高于.001门，静态平衡failed（有限时域未收敛）。逐胞长轴END+6.36%、SIDE+12.21%，为恒定预应力松弛，非周期收缩。生物学验证/父Z1仍blocked。

主要瓶颈已测量：16胞单次静态总耗时13.735秒，其中接触12.150秒、几何检查1.444秒，尚无性能优化。唯一下一步是冻结保持原安全/力能量门的接触计算加速切片，再评估长程收敛和整片预算。不自动扩展16胞或加入噪声。

[执行记录](ventricle_myocardial_long_doublet_execution_v01.md)、[总裁决](../results/ventricle_z1/z1_myo_long_doublet_v01_20260914/verdict.json)、[结构/结果/五状态动图](../results/ventricle_z1/z1_myo_long_doublet_v01_20260914/index.html)、[不规则形态文献建议](../docs/myocardial_shape_variability_literature_v01.md)。文献建议先做统计形态差异和相容界面，再做区域力学/相关涨落，尚未执行。

清理：已批准的tmp/contact_barrier_v01_build删除被执行工具阻止，未删除；本轮tmp/myo_long_doublet_v01_build未批准删除，保留。均无原始或唯一成果，详情见执行记录。旧结果、失败包保留。

## 上一阶段：2026-09-14 正间隙屏障修订及双胞短程验证passed

依用户最新批准和[屏障修订合同](ventricle_myocardial_contact_barrier_contract_v01.md)，唯一SimuCell3D核心增加独立于黏附的正间隙排斥势、非相邻面距离限制步长、三角高度安全界及逐步完整快照。未更改胞内材料、未恢复参考形状膜能。21次静态/几何调用和END/SIDE × dt.02/.01四条短程轨迹passed，停止恢复测试passed。全部为CPU，无16胞重跑。

细档END/SIDE最小正间距.058045/.069975，指定五状态无穿透见证；全程体积误差<=.302%、最小角>=28.7度，步长减半末态位移差.1352%/.1476%。每胞长轴分别+1.6934%/+3.0472%，不是周期收缩。末态自由残力仍约.20，不能称平衡态。相邻共享节点面长期折叠、真实膜尺度及16胞性能未验证，父Z1/生物验证blocked。

权威证据：[执行报告](ventricle_myocardial_contact_barrier_execution_v01.md)、[总裁决](../results/ventricle_z1/z1_myo_contact_barrier_v01_20260914/verdict.json)、[完整独立复核](../results/ventricle_z1/z1_myo_contact_barrier_v01_20260914/D/verdict_final.json)、[图文与动图](../results/ventricle_z1/z1_myo_contact_barrier_v01_20260914/index.html)。原D/verdict.json是第四条尚未结束时的早期不完整核验，按说明保留，不能替代verdict_final。没有重新计算或放宽门限。

唯一下一步：冻结长期双胞接触稳定性及整片扩展前性能资格；另行批准后执行，不自动进入16胞。旧失败、原探针与原动力学可执行文件完整保留。编译临时目录tmp/contact_barrier_v01_build需用户另行确认才可清理。

## 上一阶段：2026-09-14 双胞动态发现穿透，整片静态松弛已停止

依用户“同意，继续”和[静态松弛合同](ventricle_myocardial_sheet_relaxation_contract_v01.md)，实际执行Q的12次CPU接触求积调用、D的4条双胞轨迹与一次16胞M轨迹。Q及D原冻结短程数值门passed；但随后独立闭合网格判内/三角面穿越检查确认D在算法坐标.5起真实穿透，END/SIDE末态最大内部节点深度为.178214/.074852模型长度。因此组织适用性failed，M主动停止于28步；原D数值verdict不篡改，不能孤立引用为组织通过。

[本轮执行报告](ventricle_myocardial_sheet_relaxation_execution_v01.md)、[总裁决](../results/ventricle_z1/z1_myo_sheet_relaxation_v01_20260914/verdict.json)与[独立复核](../results/ventricle_z1/z1_myo_sheet_relaxation_v01_20260914/independent_verification_final.json)为当前证据。求积细化最大合力差0.424%、牵引差0.558%；步长减半位移差小于0.1%，仍不能替代不可穿透。

模型使用恒定方向骨架及皮质/体积/面积约束，无参考形状膜能、无周期收缩。M各行左右最外侧端帽固定xyz，其余自由；无ECM或腔压。末次审计坐标.28、自由残力.257433，未满足1e-3平衡门。M没有保存中途完整网格，仅初态与28步日志；不得拼造末态。原生拓扑文件缓冲截断保留，从冻结输入独立恢复初态拓扑并核对全部3104个已保存节点。

[图文页](../results/ventricle_z1/z1_myo_sheet_relaxation_v01_20260914/index.html)交付真实双胞五状态GIF、形变/场量、穿透截面、16胞初态夹持图和残力曲线。GIF为算法松弛，非生理时间，含失败状态。生物学验证与父Z1继续blocked。

唯一下一步：冻结不可穿透接触、防跨越步进、中止快照和性能修复切片，先通过双胞失败回归再进入新的整片计算。把几何筛查延后至M启动后是本轮流程缺口，下一轮不得重复。本轮授权已消费，不自动重跑、不恢复参考形状膜能、不直接加大惩罚系数。

## 上一阶段：2026-09-14 心肌接触修复通过，准备16胞静态维持

用户在上一轮接触失败报告后再次“同意，继续”，授权 [接触修订合同v02](ventricle_myocardial_sheet_contact_repair_contract_v02.md)。依 [本轮执行报告](ventricle_myocardial_sheet_contact_repair_execution_v02.md) 和 [独立复核](../results/ventricle_z1/z1_myo_sheet_contact_repair_v02_20260914/independent_verification.json)，正式89次CPU接触调用全部完成，修订双细胞C0 passed；16胞静态松弛仍not_run，生物学验证及父Z1仍blocked。

修复了心肌4通道缺乏黏附、重复节点—三角面积计权以及边缘最近特征法向导致的内外符号歧义。新的显式表面接触方法位于唯一SimuCell3D原spring类，包含当前面积导数以满足力—能量共轭；没有目标形状能、永久跨隙链接或直接节点投影。独立构建目标启用修订；历史生产分支和v01七项哈希不变。

端向/侧向近距离吸引分别0.0683374/0.0940696，小压入排斥，远场0。相同多面体上的两档力学网格合力差<=3.69e-15，6类能量方向导数各自最佳误差<=4.03e-9；合力合矩、刚体、置换及关闭黏附控制通过。两档网格使用共同接触积分分辨率，不能视作任意曲面或求积本身已收敛。

[图文结果页](../results/ventricle_z1/z1_myo_sheet_contact_repair_v02_20260914/index.html) 保存真实双胞结构、力比较、能量梯度、三位置牵引、曲率/初始化压力与GIF。GIF是规定间隙扫描，不是生理时间或组织松弛。旧v01、dev01/dev02失败原样保留。

唯一下一步：冻结16胞静态维持合同，先独立验证求积尺度和短程接触稳定性，再以两端有限夹持、上下/横向自由、恒定骨架预应力、关闭周期收缩松弛整片，并保存五个算法状态。

## 上一阶段：2026-09-14 4×4心肌层几何通过，接触失败，整片松弛未运行

用户最新“同意，继续”授权 [2D-M0合同](ventricle_myocardial_sheet_2d_m0_contract_v01.md) 的几何与真实接触预检。[执行报告](ventricle_myocardial_sheet_2d_m0_execution_v01.md) 与 [原始结果页](../results/ventricle_z1/z1_myo_sheet_2d_m0_v01_20260914/index.html) 为本轮证据。以下旧阶段的“尚未授权2D-M0”等表述只代表当时状态，已由本次授权及执行记录取代。

已建立16个三维闭合六棱柱细胞的4×4错列单层，长轴沿x；每胞194节点、384面。全部120对无初始穿透，几何邻接图33边连通，最小三角角31.882°。参考铺砌投影域的内缩空隙比例1.99%，包含边缘内缩，不是实验内部孔隙率。该形态是预设初始几何，不是自由态或组织自发形成的最终形态。

24次原生产内核接触调用完成，确认当前心肌类型4在正间隙下既无吸引力也无节点耦合；当前接触实现只给该类型穿透排斥。侧向压入排斥力粗细差5.697159%，超过冻结5%门。因此G0 passed、C0 failed；整片静态松弛not_run，生物学验证blocked，父Z1 blocked。类型0对照会直接投影耦合节点，不能靠改生物学类型编号替代接触资格验证。

已保存5组结构/结果PNG与SVG，以及3位置接触扫描GIF；GIF不是生理时间或组织运动。曲率、初始化压力及接触牵引来自真实保存网格，压力为初始化0，牵引为节点力/面积代理而非三维Cauchy应力。

唯一下一步：冻结新的接触修订切片，在隔离构建中验证显式心肌面黏附/排斥与5%细化门；两门通过后再运行16胞静态维持。本次不重跑失败包、不改门限、不进入周期收缩、心内膜或ECM。

## 上一阶段：2026-09-14 外载边界校准数值失败，停止稀疏条带加码

依 [外载合同](ventricle_myocardial_strip_load_boundary_contract_v01.md)、[一次性授权](ventricle_myocardial_strip_load_boundary_authorization_v01.md)、[执行记录](ventricle_myocardial_strip_load_boundary_execution_record_v01.md)与 [失败 verdict](../results/ventricle_z1/z1_myo_strip_load_boundary_failure_diagnostic_v02_20260914/verdict.json)，同一个五细胞稀疏链接条带已执行 `CENTER/SYNC × ISOMETRIC/COMPLIANT/FREE_LOW_LOAD` 六工况正式 CPU 矩阵。5 条轨迹完成；`SYNC_FREE_LOW_LOAD` 在算法相位 `phi=0.375`、激活量 `0.853553` 时最小三角角降到 **`7.997446 deg`**，触发冻结的 `8 deg` 安全停机。因此本阶段裁决为 **`failed / failed_numerical_safety_stop`**，正式授权已消费。

完成轨迹仍提供方向性证据：`SYNC_ISOMETRIC` 的整体缩短为 `0%`、峰值端载增量为 `1.746849`；`SYNC_COMPLIANT` 的整体缩短为 **`8.5358%`**、峰值端载增量降到 **`0.662799`**。这说明释放轴向约束确实会把主动作用从端部反力转化为整体缩短。

但完整判别不能通过。`CENTER_FREE_LOW_LOAD` 的缩短 `1.5318%` 略低于 `CENTER_COMPLIANT` 的 `1.5614%`，违反冻结的严格排序；当前用左端整帽全固定消除刚体平移，因此该工况并不是平移中性的纯零载对照。20% 同步近自由收缩还使固定拓扑曲面发生严重剪切，且 `SYNC_COMPLIANT` 的最小角 `8.581 deg` 已逼近安全门。不能用降低门限、删掉失败工况或自动重跑来改判。

[失败图文包](../results/ventricle_z1/z1_myo_strip_load_boundary_failure_diagnostic_v02_20260914/index.html) 保存了三种边界结构、失败轨迹最后 3 个有效求解器状态、直接失败曲线、完成工况比较和最后有效的曲率/压力/胞内收缩牵引/界面牵引网格。4 组 PNG/SVG、3 帧 GIF 与 9 个离线链接通过，人工视觉 QA 为 `passed`。

当前不建议继续修补这条稀疏固定链接条带，因为其边界与拓扑不会代表用户要求的二维致密心肌层。唯一建议下一步是另行冻结 **`2D-M0`：4×4 单层心肌细胞的被动致密真实面接触预检**，先验证排布、接触捕获、无穿透、邻接图、体积与网格质量；不加入主动收缩、ECM、心内膜或生理时间。该阶段尚未起草合同或获得执行授权。生物学验证保持 **`blocked_data`**，父 Z1 保持 **`blocked`**。

补充原始状态复核：`CENTER_COMPLIANT / CENTER_FREE_LOW_LOAD / SYNC_COMPLIANT` 的最大保存残力分别为 `0.001406 / 0.003415 / 0.003504`，均超过 `1e-3`；`SYNC_COMPLIANT` 最小保存角 `8.584776°` 也低于 15° 验收门。因此上述完成轨迹的数值仅为诊断读数，不能视为合格平衡解。非对称夹持的影响仍是待检验解释，尚不能用未收敛排序证实因果。

[2D-M0 具体实施方案](ventricle_myocardial_sheet_2d_m0_design_v01.md) 已完成，列出几何、双细胞接触、组织静态维持三步及各自输出；执行状态 `not_run`，实际接触参数和预算尚待准备后冻结。

## 上一阶段：2026-09-13 高幅度局部形变通过

依 [高幅度合同](ventricle_myocardial_strip_high_amplitude_deformability_contract_v01.md)、[v02 定向修复合同](ventricle_myocardial_strip_high_amplitude_deformability_repair_contract_v02.md)、[v03 最终修复合同](ventricle_myocardial_strip_high_amplitude_deformability_repair_contract_v03.md)、[执行记录](ventricle_myocardial_strip_high_amplitude_deformability_execution_record_v04.md)与 [v03 组合 verdict](../results/ventricle_z1/z1_myo_strip_high_amp_deformability_repair_v03_20260913/verdict.json)，同一个五细胞等长条带已完成 `CENTER` 与 `SYNC` 在 10%、15%、20% 主动参考缩短下的高幅度探针。所有被动材料、方向性骨架、固定链接、阻尼、网格和刚性端夹持保持不变；20% 是合成上限探针，不登记为生理幅度。

v01 的四条新轨迹均完成，但 `CENTER 15%/20%` 的保存残差分别为 `0.00228429 / 0.00175414`，未过 `1e-3` 门；v02 只把两条 CENTER 轨迹的定相位松弛从 3000 增至 6000 步，15% 通过而 20% 仍为 `0.00100638`；v03 最后只把 `CENTER 20%` 增至 7000 步，不改物理参数或门限，最终组合 **61/61 门通过**，裁决为 **`passed_synthetic_isometric_high_amplitude_response`**。v01、v02 失败包完整保留。

逐细胞结果说明当前模型并非“不变形”：`CENTER 20%` 时中央主动细胞长轴应变为 **`-11.6227%`**，横轴/厚度应变为 **`+4.6736% / +3.9391%`**；四个被动邻居沿长轴被拉长约 `2.29%`，所以五细胞平均长轴应变只有 `-0.4903%`。`SYNC 20%` 的五细胞平均长轴应变为 `-2.7159%`。CENTER 与 SYNC 的峰值端反力增量分别由 10% 时的 `0.154504 / 0.879828` 增至 20% 时的 `0.329012 / 1.753258`。因此，此前“几乎不变”的视觉印象主要来自整体平均、真实比例显示和刚性夹持掩盖局部形变。

[v05 图文页](../results/ventricle_z1/z1_myo_strip_high_amp_deformability_visual_v05_20260913/index.html) 保留无标签遮挡的模型示意，并补齐冻结合同要求的 10 倍位移显示图；10 倍图明确标为仅用于观察，不参与数值验收。页面通过人工目视、PNG/SVG 解析、9 帧 GIF、13 个离线链接和证据哈希检查。最大相对体积误差 `0.7481%`、最小三角角 `33.548°`、最大保存自由节点力 `8.523e-4`、固定端位移 `0`。

本轮 PASS 只证明当前合成模型在刚性等长边界下存在连续、明显的局部变形和传力响应，**不能单独标定被动材料柔软度**。唯一下一判别实验应保持材料、连接和主动幅度不变，冻结 `ISOMETRIC / COMPLIANT / FREE-LOW-LOAD` 三种端部边界比较；该合同未起草、未授权。心内膜自由态仍排在这一判别实验之后。生物学验证保持 **`blocked_data`**，父 Z1 保持 **`blocked`**。

## 上一阶段：2026-09-13 激活数量 × 收缩幅度响应通过

依 [幅度合同](ventricle_myocardial_strip_cycle_amplitude_contract_v01.md)、[定向修复合同](ventricle_myocardial_strip_cycle_amplitude_repair_contract_v02.md)、[执行记录](ventricle_myocardial_strip_cycle_amplitude_execution_record_v03.md)与 [v02 组合 verdict](../results/ventricle_z1/z1_myo_strip_cycle_amp_repair_v02_20260913/verdict.json)，同一个五细胞等长条带已完成 `CENTER`（仅中心细胞激活）和 `SYNC`（五细胞同步激活）在 2%、5%、10% 三个主动参考缩短幅度下的比较。两组使用相同的四个固定黏附界面、两端夹持、横向自由表面、材料和网格；5% 轨迹经核心与输入哈希复核后复用，2% 与 10% 补算四条 CPU 单线程轨迹。

v01 六工况均正常完成，但 `CENTER_EPS100` 的最大保存自由节点力 `0.00134317` 和周期末恢复比例 `11.7404%` 未过原 `1e-3 / 10%` 门，因此 v01 保持 **`failed`**。残差在定相位保持中持续下降；v02 只把该独立轨迹每相位松弛由 2000 增至 3000 步，不改模型、载荷或门限。修复后残差为 `8.33649e-4`、恢复比例为 `5.2250%`，组合 **85/85 门通过**，裁决为 **`passed_synthetic_activation_count_amplitude_response`**。

CENTER 在 2%/5%/10% 下的峰值端反力增量为 `0.026538 / 0.071320 / 0.154504`，平均长轴应变为 `-0.0669% / -0.1453% / -0.2681%`；SYNC 对应为 `0.173658 / 0.438734 / 0.879828` 和 `-0.2811% / -0.6848% / -1.3597%`。两个模式均表现为幅度越大，端反力与长轴缩短越大；每个幅度下 SYNC 反力均大于 CENTER。等长夹持下几何变化有限而反力显著增长，支持当前合成模型中的共同传力解释。

[v03 可视化页](../results/ventricle_z1/z1_myo_strip_cycle_amp_visual_v03_20260913/index.html) 提供修复后的结构图、形变网格、分开的胞内收缩/界面黏附牵引网格和三张 9 状态 GIF。首次排版缺陷在独立 v03 图包中修复，PNG/SVG、GIF 帧数和离线链接均通过检查。牵引仍是模型节点力/面积代理，不是三维 Cauchy 应力；`phi` 仍是算法激活坐标，不是生理时间。

该 PASS 只覆盖合成的主动细胞数量与幅度响应。实验比较保持 **`qualitative_consistency_only`**，生物学验证保持 **`blocked_data`**，父 Z1 保持 **`blocked`**。本轮授权已消费；唯一下一步是起草并冻结**心内膜单细胞自由态合同**，尚未授权执行。

## 上一阶段：2026-09-13 五细胞心肌条带合成力链通过

依 [条带决定](ventricle_myocardial_strip_decision_v01.md)、[冻结合同](ventricle_myocardial_strip_contract_v01.md)、[定向修复合同](ventricle_myocardial_strip_repair_contract_v02.md)、[执行记录](ventricle_myocardial_strip_execution_record_v02.md)与 [v02 组合 verdict](../results/ventricle_z1/z1_myo_strip_l5_a_repair_v02_20260913/verdict.json)，五个长轴心肌细胞沿 `p` 轴首尾串联、四个界面各用 7 条固定材料链接、条带外侧端帽夹持的最小组织场景已完成。每个细胞保留 v03 方向性骨架形态支撑，并增加 7 条成对的胞内长轴收缩单元；参考边、参考面度量和目标末态项继续为 0，旧弯曲项继续隔离为 0。

v01 四工况正式矩阵中，`PASSIVE`、`SYNC` 和 `CENTER` 通过；`CENTER_NO_LINK` 的最大保存自由节点力为 `0.00107093`，单独未过冻结的 `1e-3` 门，故 v01 verdict 保持 **`failed`**。残差在固定相位松弛中单调下降，v02 依冻结修复合同只把该独立阴性对照的每相位松弛从 2000 增到 3000 步，不改模型、载荷或门槛；修复后残差为 `5.7740e-4`。组合判定 43/43 门通过，裁决为 **`passed_synthetic_strip_mechanics`**。

`SYNC` 工况端部反力从 `0.00276077` 增至 `0.44149444`；峰值激活时平均长轴缩短 `0.6848%`，横轴和厚度分别增加 `0.2150%` 与 `0.1821%`。仅中心细胞激活时端部主动反力增量为 `0.07132033`；去除所有界面链接后最大端部反力变化为 `0.00072964`，约为有链接传力增量的 `1.02%`。最大体积误差 `0.7257%`、最小三角角 `46.1684 deg`、固定端位移 `0`。五组 PNG/SVG 已完成人工视觉检查。

该 PASS 只证明合成模型中“胞内收缩—固定界面链接—端部反力”的最小力链闭合。刚性夹持、固定材料链接、主动幅值和力单位尚未同实验标定；`phi` 是算法激活坐标而非生理时间。因此实验比较仅为 **`qualitative_consistency_only`**，生物学验证继续 **`blocked_data`**，父 Z1 继续 **`blocked`**，原方案 Z4、可变形 ECM、心内膜和生理周期均未因此通过。

唯一下一步仍是起草并冻结**心内膜单细胞自由态合同**：先验证角色特异的扁平化骨架机制，再考虑把心内膜、心肌与可变形 ECM 放入受限三层组织。该下一步尚未授权执行。

## 上一阶段：2026-09-13 心肌自由态合成机制通过

用户决定把形态机制重新拆开：先验证自由心肌细胞能否在不使用目标末态/参考形状膜能的情况下，由生物学启发的方向性细胞骨架代理形成长轴、横轴和厚度轴分离；心内膜、ECM 和三层组织依次后置。v02 数值失败后，依 [v03 诊断](ventricle_bioform_myocardium_repair_diagnosis_v03.md)、[冻结合同](ventricle_bioform_myocardium_repair_contract_v03.md)、[执行记录](ventricle_bioform_myocardium_repair_execution_record_v03.md)与[结果页](../results/ventricle_z1/z1_bioform_myo_r_v03_20260913/index.html)，唯一一次 8 工况正式修复矩阵已完成并裁决为 **`passed_synthetic_mechanism`**。

v03 将未通过刚体不变性诊断的旧离散弯曲项隔离为 `k_b=0`，保留方向性骨架法向形状牵引，并对总面积加权过阻尼速度只去除 3 个整体平移和 3 个整体转动；自适应子步把单步最大节点位移限制为当前最短边的 10%。目标末态、逐边参考形状和逐面参考度量继续关闭。`k_b=0` 是实现隔离，不代表真实细胞没有弯曲刚度。

主分辨率 `FULL_M320_DT020` 从等体积近球形达到 `E_pq=1.292077`、`F_qr=1.172049`，轴向外包络约 `9.194 × 6.672 × 5.381`；去骨架对照为 `1.00/1.00`。扰动形态比相对差小于 `8e-7`，旋转差小于 `6e-16`；320→1280 面差为 `1.44%/0.88%`，`dt=0.020→0.010` 差约 `2e-7/1e-7`。全矩阵最大体积误差 `0.3634%`，最小逐步三角角 `47.29°`，主轨迹末态/峰值自由力比 `0.002622`。正式矩阵 8/8 完成，独立验证失败门数为 0。

聚焦行为测试 `4/4 passed`，受影响的局部重网格回归 `5/5 passed`；五组 PNG/SVG 的尺寸、哈希和人工视觉检查均通过。正式源码、可执行文件及合同哈希与预登记一致；v02 失败包完整保留。图像中的 `lambda` 是算法加载/松弛坐标，不是生理时间。

该 PASS 只覆盖合成无量纲的单个自由心肌细胞机制资格；同期同区域三维单细胞数据尚未注册，因此生物学验证为 **`blocked_data`**，父 Z1 继续 **`blocked`**。唯一下一步是先起草和冻结**心内膜单细胞自由态合同**，再另行授权；ECM、三层模型、周期动力学和 Z2 均为 **`not_run` / 未授权**。

## 上一阶段记录：2026-09-12 Z1-TF2-B 正式筛查数值失败，修订资格片未运行

用户已冻结并授权 [Z1-TF2-B 合同](ventricle_simucell3d_trilayer_shape_formation_contract_v01.md)。依 [执行记录](ventricle_simucell3d_trilayer_shape_formation_execution_record_v01.md) 与 [结果页](../results/ventricle_z1/z1tf2b_simucell3d_shape_formation_v01_20260912/index.html)，唯一一次 `2×7=14` 正式轨迹矩阵已经完成调度并冻结，互斥裁决为 **`failed_numerical`**。仅 FORMATION/MAINTENANCE 的两个 `NO_LUMEN` 轨迹到达末态；其余 12 条含腔压轨迹均在全局步 84–90 触发冻结的心内膜体积误差 10% 停止门。

共同数值门失败后，FORMATION、MAINTENANCE、镜像和机制消融形态门全部保持 **`not_run`**，不得从预制 MAINTENANCE 外形或局部时间点图推断科学通过。两个完整轨迹的末态/历史峰值自由力比分别为 `0.1651` 和 `0.4957`，均未达到 `≤0.05`；FORMATION 的中央实际接触占有率也未达到 `0.80`，末态中央中位心肌伸长率 `1.0198`、心内膜扁平率 `1.0053`，未形成目标形态。

失败模式将当前问题分成两个正交资格片：一是解释和修复 `0.50` 腔面牵引与现有体积/面积支撑的 P–V 不相容；二是在不扩大 `0.35` 截断、不加入跨隙永久弹簧的前提下，使粗网格近球 FORMATION 的实际同层接触被可靠捕获。二者均为 **NOT_RUN / 未授权**，尚无活动合同；不得直接追加周期力、放宽冻结门或覆盖本正式结果目录。

本次正式矩阵使用 CPU 最多 4 线程、GPU 0，墙钟 `94.399 s`；聚焦测试 `9/9 passed`，受控 SimuCell3D CTest `134/134 passed`，七组 PNG/SVG 已通过文件检查和人工视觉检查。正式运行前后 SimuCell3D 源树哈希同为 `e25abc3f40af6a27a14f7ff39b1e13d52bd62fc7cc87a1b86bee06d5c12d672d`，本轮未追加核心修改。测试通过只证明执行与失败证据可复核，不改变 `failed_numerical` 裁决。

父 Z1 继续为 **UNRESOLVED**，周期主动力学与 Z2–Z11 继续为 **NOT_RUN**。Z1-TF2-B 一次性授权已消费；当前没有任何修订、重跑、GPU、CFD 或 FSI 授权。

## 上一阶段记录：SimuCell3D 换核资格 M0 通过并形成 TF2-B 合同

**本节保留 M0 阶段当时的判断；其中“下一步”“待审”和“未授权”只按当时状态解释，已由上面的 TF2-B 正式结果取代。**

用户已决定 MeshCell3D 进入重构并停止作为当前心室前向内核。依 [SimuCell3D 换核决定 v01](ventricle_simucell3d_kernel_transition_decision_v01.md)，前向实现直接链接项目内受控 `external/simucell3d/`；不得复制第二套核心，不删除或改判 MeshCell3D 历史结果，也不把既有局部 PASS 自动继承给新内核。

依 [Z1-TF2-M0 执行记录](ventricle_simucell3d_kernel_migration_precheck_execution_record_v01.md) 与 [结果页](../results/ventricle_z1/z1tf2m0_simucell3d_migration_v01_20260912/index.html)，七个冻结子门全部通过，裁决为 **PASS_SIMUCELL3D_M0**。实际对象为 `16 + 1 + 16 = 33` 个闭合曲面：长轴心肌、一个连续闭合且可变形 ECM、扁平心内膜。固定点最大位移为 `0`，ECM 自由点最大位移为 `1.1141055567650548e-3`；压力积分、主动净力/净矩、接触作用—反作用与工作—耗散最大相对残差分别为 `3.103e-16`、`3.594e-16 / 3.561e-16`、`1.106e-16` 与 `6.383e-15`。完整受控 fork CTest 为 `134/134 passed`，artifact verifier 测试 6/6，独立文件复核七门全通过；五张真实数据图、已执行 Notebook 与视觉 QA 均已冻结。

正式求解只执行一次；其后的三次独立复核只读取冻结 artifact。前两次分别暴露 NumPy 布尔 JSON 序列化和交叉报告容差过严的审核器缺陷，均已记录；修复没有改变任何冻结科学阈值或重跑内核。

本 M0 只确认受控 SimuCell3D 内核与最小 PRL 适配层具备进入下一合同的资格。它不验证长期组织成形、生理参数、周期主动收缩、物理时间、父 Z1 或 Z1-TF2-B。`λ` 为算法延拓坐标；界面牵引是面积归一接触节点力，不是三维 Cauchy 应力。

MeshCell3D 路线上的 [Z1-TF2-A](ventricle_dcm_ecm_confluent_trilayer_precheck_execution_record_v01.md) `PASS_Z1_TF2A_PRECHECK / surface_only_supported`、旧稀疏 ECM 的 Z1-TF v04 `UNKNOWN`、父 Z1 正式参考态矩阵失败及更早局部结果均作为历史证据保留，但不改变当前 SimuCell3D 阶段状态。

下一最小切片是 [SimuCell3D 版 Z1-TF2-B 致密三层形态形成与维持筛查](ventricle_simucell3d_trilayer_shape_formation_contract_v01.md)。待审合同把问题拆成两个不能互相替代的试验臂：FORMATION 从等体积近球形细胞起步，检验环境是否真正生成长轴心肌和扁平心内膜；MAINTENANCE 从 M0 规定形态加无方向小扰动起步，检验形态是否恢复和维持。两个试验臂均包含去方向性承载、去腔压、去同层黏附、去细胞—ECM 黏附和软 ECM 对照，并要求多个求解器时间点以及曲率、压力、节点力和界面牵引图。

合同继续禁止细胞逐边/逐面方向性参考形状项；为避免球体因最小面积而没有变形余量，只使用不携带方向的角色特异标量总面积储备。根据 M0 初始网格独立重算，候选内核参数 `A^3/V^2` 为心肌 `141.674572586949`、心内膜 `209.181549089029`。这些值是待审的数值稳态目标，不是已验证的细胞骨架或生理参数。

该合同当前仍为 **proposed**，计算为 **NOT_RUN / 未授权**。本轮 M0 授权已经消费；只有用户审定并冻结合同后，才可另行进行一次 create-only CPU 执行，不自动进入主动周期、物理时间或 Z2。

### 保留的父 Z1 正式参考态矩阵失败

依 [父 Z1 正式矩阵执行记录](ventricle_z1_parent_formal_matrix_execution_record_v01.md)，正式动态前置门为
**FAIL_NUMERICAL**，父级 Z1 保持 **UNRESOLVED**。最新冻结结果入口为
[results/ventricle_z1/parent_formal_v04_20260912/index.html](../results/ventricle_z1/parent_formal_v04_20260912/index.html)。

`4:4:1` 扁平心内膜在厚度方向有限端区固定、其余节点自由的零载平衡中，完整组合被动项使网格离开可接受集合：
自由节点最大残力为 `2.148510e-8 N`（门 `1e-14 N`），最小三角形角为 `1.792924657e-5 deg`
（门 `15 deg`），并有 `8` 个翻面。最近数值信赖域边界仍相距 `0.422547 L0`，说明边界未激活。
独立验证从 5 个原始 NPZ 状态重算了最小角和翻面数，判定为 `PASS_VERIFICATION_OF_FAILURE`；这只证明失败包可信，
不是科学通过。

因此该参考态路线的 AXIAL / TRANSVERSE / RELAX 物理时间轨迹、网格/时间/体积罚细化、主动周期拉伸和 Z2–Z11
均为 **NOT_RUN**。当时提出的“预应力兼容参考态或各向异性参考面材料”是历史修复候选；用户随后以 v04 决定停止把参考态膜能作为前向成形机制，并已另行授权上面的静态三层环境成形筛查。

### 继承的父 Z1 本构修复通过

依 [父 Z1 被动力学修复执行记录](ventricle_z1_parent_passive_mechanics_repair_execution_record_v01.md)，唯一 MeshCell3D 内核已闭合弯曲力—能量工作共轭、完整保守能量导出以及刚体协变/合力/合矩问题。本次修复判定为 **PASS_REPAIR**；最新冻结结果入口为 [results/ventricle_z1/parent_repair_v06_20260912/index.html](../results/ventricle_z1/parent_repair_v06_20260912/index.html)。

修复后最差最佳步长方向导数相对误差为 `4.187784028222584e-09`（门 `1e-6`），最大独立能量重建相对误差为 `4.1237918758241266e-13`（门 `1e-2`），最大刚体协变/合力/合矩相对误差为 `2.114501288862503e-14`（门 `1e-10`）。完整单元测试为 159 passed、5 skipped；Numba parity、独立结果包复核、两张定量图样式和五张最终图人工检查均通过。正式运行仅用 CPU，GPU 0、网络 0。

结果包含球形 1:1:1、长轴心肌 3:1:1 和扁平心内膜 4:4:1 的三档网格，以及长轴/扁平细胞各 `lambda=0,0.5,1` 的六个规定路径点。网格图显示曲率、参考边应变、节点力与细胞压力；这些路径点不是物理时间，当前壳模型也未定义三维 Cauchy 应力张量。v05 数值通过但图像人工检查失败，已由重新冻结并完整重跑的 v06 取代且保留失败记录。

父级本构修复的局部通过继续有效，但已不能再表述为“仅等待正式矩阵”：正式前置零载平衡已经实际运行并失败。C++ 扩展未重建，CUDA 弯曲 parity 未运行；相关保守弯曲路径失败关闭到 Python 参考实现。

### 保留的 Z1-C 接触本构通过结果

用户采纳 [细胞几何与多细胞策略 v03](ventricle_cell_geometry_strategy_decision_v03.md)：把细胞自身参考态与拥挤/接触造成的组织成形分开验证。Z1-A 球形路径为 **PASS**；Z1-B 显式参考态为 **PASS_REFERENCE_STATE**；依 [Z1-C 修复执行记录](ventricle_z1c_contact_repair_execution_record_v02.md)，Z1-C 为 **PASS_CONTACT_CONSTITUTIVE**。其最新结果入口为 [results/ventricle_z1/z1c_v08_20260911/index.html](../results/ventricle_z1/z1c_v08_20260911/index.html)，适用边界仍仅是严格球/椭球参考态的规定运动接触本构。

### 保留的上一轮 Z1 综合预检

用户指定 `plan/active/PRL_Codex_Stage_Contracts_v03` 为最新计划，并在 Z0 后授权扩大 Z1 的几何预检：球形基准、3:1:1 长轴心肌探针、4:4:1 扁平心内膜探针和受控双细胞接触。依 [Z1 执行记录](ventricle_z1_execution_record_v01.md)，该次预检触发冻结停止规则，Z1 当时为 **BLOCKED_DEPENDENCY**；完整入口为 [results/ventricle_z1/v01_20260911/index.html](../results/ventricle_z1/v01_20260911/index.html)。其失败证据已由本轮修复正面闭合，但正式加载/恢复/细化矩阵及 Z2–Z11 仍为 **NOT_RUN**。

Z1 在 CPU/4 线程上只读调用唯一 `E:\MeshCell3D\code\muse_dcm` 2.1.0。3 种几何 × 3 档网格均闭合且体积独立复核通过，全矩阵最小角 `15.277559°`；fine 球的 Laplace 压差误差为 `5.299270e-4`；五种接触的最大合力相对残差为 `1.753497e-16`。但是最大能量导出相对差为 `2.435088e3`，弯曲项逐案例最佳梯度误差最差为 `1.105057`，组合内力合力/合矩门也失败，并且内核没有可声明长轴/扁平无应力材料参考态的局部参考度量。独立复核、6 项回归测试、两张定量图样式验证和三张图的目视检查通过；这些只确认失败包可信，不将 Z1 提升为 PASS。

已被 v03 取代的 [细胞几何分工决定 v02](ventricle_cell_geometry_strategy_decision_v02.md) 曾允许在 Z1 中提前使用光滑等体积椭球探针验证几何与方向响应，同时保留球形 Laplace 基准。v03 又把参考态与拥挤分开验证，v04 停止以前向细胞参考态膜能成形；三者均为历史输入。当前科学对象仍服从 [v05 DCM-ECM 决定](ventricle_cell_geometry_strategy_decision_v05.md)，前向软件实现服从后续 [SimuCell3D 换核决定 v01](ventricle_simucell3d_kernel_transition_decision_v01.md)。

Z0 的 `PASS` 仍只覆盖资料/静态几何/可视化；Z1-A/Z1-B/Z1-C、Z1-TF2-A 和本次 SimuCell3D M0 的局部通过都不覆盖完整被动力学。公开 GFP 图像与作者速度快照尚未建立共同鱼、尺度、相位与空间注册，fish ID、hpf、条件和完整体素信息未知，所以实验主张仍 `BLOCKED_DATA`。本轮只增加了受控 SimuCell3D 核心/适配层的固定拓扑资格证据；主动收缩、长期或物理时间组织动力学、标定 ECM 黏弹性、CFD、FSI、泵血和事件均未运行，GPU 与 Docker 均未启动。

新决定取代 NCS 路线、参考态路线、稀疏 ECM 网络路线和 MeshCell3D 前向实现的后续执行优先级，但不抹除历史证据。2026-09-10 NCS-M1 的范围受限 PASS、旧 P1 `NOT_RESOLVED`、所有失败包、原始数据和用户修改继续保留。既有 Z1 子门以及本次 Z1-TF2-M0 的授权均已消费；下一最小切片是先形成并另行授权 SimuCell3D 版 Z1-TF2-B 静态成形与消融合同，不自动进入主动周期或 Z2。

**以下 2026-09-10 NCS 段落及编号章节为保留的历史记录；其中“当前”“下一步”只在原路线和原日期范围解释。**

## 保存的上一条主线：2026-09-10 NCS 方法路线

用户已采纳以 Nature Computational Science 为研究设计目标的 FEM–DCM 方法路线，后续按需扩展 FSI。M0 已按 [实际报告](ncs_m0_report_v01.md) 收口为 **PASS**。M1a 的首包 v01 因协议计数遗漏被否决并保留；create-only v02 按 [执行记录](ncs_m1a_execution_record_v01.md) 通过 17 个冻结协议，平面三层合成基准为 **PASS**。M1b 的 v02 因时间门混入固定空间误差而 `NOT_RESOLVED` 并保留；最后一轮 create-only v03 的七个圆环协议全部通过。依 [M1 总报告](ncs_m1_execution_report_v01.md)，M1 在冻结的二维三层 all-FEM 合成基准范围内为 **PASS**。

新基线先做三层全部 FEM 的二维平面与圆环，再按门禁替换心内膜为 DCM、加入一次细胞事件、ECM 更新、FSI 和最小三维。旧 P1 v03 保持 NOT_RESOLVED（6/8 带空间门未通过），旧 P2/P3 仍冻结；新方法路线不依赖旧 P1 通过，也不授权重开旧失败路线。

本次 M0→M1a→M1b 阶段授权已完整消费并在 M1b 后停止。M2 为 **NOT_RUN / 未授权**，须先形成新的执行合同与用户决定；不从旧自主执行、预算、后台或自动化条款继承权限。方法新意、生物有效性、DCM 相对优势和投稿准备度仍为 **UNKNOWN**。`last_verified` 仍保留历史数值核验日期；NCS 的实际证据日期在各新报告中记录。

**以下编号章节为保留的历史记录。涉及“当前”“最新”“授权”的旧措辞，仅在原日期和原路线范围解释；新路线以本节及采纳决定为准。**

## 1. 一句话状态

最新执行授权（主计划84/简报110，取代下列即时授权）：理论agent与总管已冻结唯一机械刺激、唯一ECM
模量支路及与生产T128谐波算子一致的反馈导数。现允许A1、H=0.3、`tau_e/T=0.2`下S2/S3各一个
基态和8列局部模量灵敏度，第0/3列两档中心差分复核；1 CPU、8GiB、60秒、0 GPU。必须先核查
基态均匀性及平移协变，不能因周期网格直接使用`k`标签。当前弹性链不是闭合胞DCM，任何阳性仅是
机械反馈核可行性；真实DCM/连续强对照、分裂、扩散、流体、频率轴及原4留出均未授权。论文2固定
周期，避免与论文3频率解码—ECM慢记忆主线重叠。

当前最高优先级裁决（主计划82–83/简报108–109）：共享连接的固定拓扑线性机械多端口仍可由普通
耦合弹簧—阻尼网络精确复现，DCM机械独占主张暂停。新入口改为心内膜胞身份/激活状态—局部ECM
沉积—机械读出的闭环，候选核心是“平均心室运动稳定而非均匀胞状态先失稳”的隐藏反馈失稳。
现仅授权推导实际有限厚ECM核`G_h(k)`、反馈符号、稳定性边界及均匀连续/空间连续/DCM三层强对照；
0新数值授权。固定拓扑门通过后才讨论分裂、换邻和状态继承，不自动加入流体或三维。EFE胞来源存在
心内膜EndMT与心外膜衍生间充质两类证据，模型必须保留外源成纤维细胞对照，不把`a_i`直接解释为
已确认的ECM分泌命运。Nature Physics目标及心室/EFE边界不变。

当前裁决（主计划60.4–78/简报86–104，取代下列历史阶段即时授权）：8胞与受载有限厚ECM的
双弱连接静态探针已完成30状态/14指定柔度列。三厚度、两距离均为屏蔽，不支持本采样转变假设。
总管用不同三角梯度、界面积分和胞能量重建全部状态平衡及能量，0新解；理论子agent亦完成
独立源码审查。中心细化变化0.98424%，不认证全区间。求解1.1091311秒、独立重建1.2086616秒。
已纠正近零特征值不能单独认证正定的检查表述，用结构证明与四套基准/下界Cholesky补查。
近零绝对误差门及全局胞坐标标签限制见简报86.3，冻结结果保留；真实UFL交叉仍not_run。
普通标量链对照已完成：它解释所有负号，但0/pi校准不能在观察精度内恢复中心完整作用核；
pi/4谱偏差细网格4.50821%，其粗细变化0.0213234%。这不识别ECM非局域性与胞内部形变。
六块交叉柔度重组已独立验收；总管纠正导数符号与“已定位谱形机制”的过强解释，执行者确认。
计划63再校准谱导数已独立验收，0.0540143秒、0新解/文件；pi/4角与ECM倍率导数相反，
pi/2同负。ECM后者粗细差11.41%，不认证所有灵敏度；未识别唯一谱来源或DCM必要性。
计划64底面运动到连接开度的互易投影已独立验收，执行0.68384秒、总管0.0491792秒，
0新解/文件。四非均匀通道可激发，幅值粗细差按细值最大1.60191%，空间相位最大2.04836度。
两均匀输入零开度；伴随反力不是新输入实际反力/功，不将边界位移代理称已加入主动心肌。
按计划65收口当前静态数值支线，保留科学基线、收缩机制主张。总管筛选下一非重复可证伪候选，
目前尚未选定/下发新的合格数值预测；不自动扩扫、不重派已完成60–64或泛化仿射/Schur支线。
计划66纸面否证已由两方独立验收：普通被动两模态可有静态两端负、中频交叉实部正，
可行性门lambda_1*lambda_2>1；实际幅值导数仍须载荷比j2/j1。不能套到完整多模态/含drag模型。
本步0新解/扫描/模型接入/查新，泛化频率变号候选收口；下一合格细胞预测仍待筛选。
第67节纸面检查完成：唯一零模与正几何刚度已核查，彼时固定底面驱动投影非零尚未证明。
三篇原始文献限定一般非仿射机制的新颖性，不能据此宣布DCM必要性或否定所有细胞物理。
第68节两个网格共4个Q=0系数右端已独立验收：细网格F_h=2.649438561、C_g=335.7499367，
粗细变化分别0.3084075%/0.0519880%，通过限定5%探索门；不是所有场/能量分项的收敛认证。
执行0.6017392秒，总管独立完整单元重建0.2959302秒、0新解；峰值内存不可用，未虚报8GiB实测。
冻结JSON的u0能量标签只指消元代数恒等式，已在简报93勘误并由执行者确认；独立真实边界功闭合
误差最大8.705e-13，不影响F_h/C_g。尚未计算有限形状下Q放大，不能据非零系数声称局部负荷增长。
本系数判零完成，无新的数值批次；下一步须先给出区别普通非仿射响应的具体负荷预测，不自动扩扫。
第69节贡献检查已完成：三篇原始研究对照，理论子agent独立判断0条合格新预测；总管同意收缩67–69
形状软模支线的投稿主张，保留已验收系数基线。胞形—应力推断、应变/张力分离及胞尺度离散效应
已有不同机制的先例；不是对本项目所有创新可能性的否定，也不以连续等价否定细胞物理。
本轮0新右端/模型/代码/实验执行。科学瓶颈是尚无区分预测，不是执行任务故障；不重复派发已完成检查。
第70节纸面检查已独立验收：固定阻尼/非负瞬时刚度类有共同收缩度量，周期刚度调制不足以使
同源扰动逐周期增长；不需刚度对易。局部分量暂态或强迫幅值增大不被排除，限定DAE边界见简报95。
生产matrix_a/matrix_g固定，主动应变只在源项，尚未实现周期切线刚度。此候选收口，0新模拟/机制。
第71节功共轭端口相位锐界已独立验收，作为限定耗散诊断；默认ECM的零drag对照全频上界约16.30644度。
交叉读出可由普通通路相消达到90度，故整体到局部的大相位差不是细胞额外耗散证据；生产有drag不套此界。
本步0新工况/代码/模型/实验，仅常数算术；不越界亦不能证明细胞无耗散。判别基线收口，暂无下一数值批次。
第72节平方时间律识别检查已独立验收：限定固结与弹性/drag杆可同加载端响应/耗散；平方律不唯一识别胞内水力。
两篇原始研究区分胞内孔弹和基底水力；排水控制只是一项条件性破退化办法，现实能力未知，不等于DCM必要性。
该识别候选收缩，0新数值/流体/状态实现/实验。无遗漏执行成果，暂无下一数值批次，目标与原留出不变。
第73节单篇胞内压力原文证据检查完成：独立实验约束存在，但不混同压力代理、计算压力场与直接全场测量。
仅核查可读的正式版索引段落，未完整读取PDF或复算原始数据；由总管逐项核对，不称另一agent独立验收。
72–73水力入场支线收口，不自动接入新状态。下一数值任务尚未选定，须先有细胞—连接负荷的区分预测及独立观测。
本步0新工况/代码/模型/实验；执行任务无故障或遗漏交付，核心机制与DCM物理必要性仍未确认。
第74节记忆候选的具体反馈对照已独立核查：固定有限训练时长下，连接状态的闭环—回放差最早为
慢速率epsilon的二阶，即时机械差可为一阶。普通被动反例说明该差不专属ECM、不保证永久记忆。
仅更新参考态时，固定二次刚度的小探针增量响应可不变；等待残余、自然演化和理想冻结须分开。
接受可计算对照，保留候选而非宣布创新成立。下一理论缺口是具体连接状态的能量、供能及局部负荷读出，
优先检验参考态变化经有限细胞几何影响受力的可能性。本步0新数值/代码/模型实现/实验，原留出保持锁定。
第75节单连接几何读出已独立核查并补齐交接记录：物理弹簧刚度不变，自然长度变化仍可使
小探针刚度与局部轴向张力增益反向变化；须包含平衡松弛及输出方向变化，不能据此称永久记忆。
第76节闭合受约束胞的两自由度解析检查已独立验收：有限面积刚度下保留该相反符号，且可延续到
局部正角度刚度区间。没有量化该区间或认证任意自由细胞；受约束胞不是完整DCM生产模型。
保留并推进候选。下一缺口是加载—等待—测试的状态可达性、快慢时窗及能量对照，随后才评估ECM作用。
本步0新工况/求解/代码/目录/文献/模型实现/实验；数值任务无故障或遗漏，尚未下发新数值批次。
第77节加载—等待—测试的局部可达性已独立核查：弱加载可写入暂存自然长度状态，撤载后逐渐恢复。
接受约化关系及条件性窗口；自然恢复慢不保证探针不改写状态，需更严格的低扰动频率条件。
短训练快层、小信号残余和局部幅值限制须保留；固定二次矩阵不能自身产生训练后增量刚度变化。
下一步为同一有限几何候选设计前瞻数值核验，先定参数/工况/误差对照/预算，不自动加入ECM或其他机制。
本步0新数值/代码/模型实现/实验，原4留出未动；ECM作用、实验可辨识性及核心创新仍未证实。
第78节已固定五条加载—等待历史与误差/功账门，103节前瞻预测经两方独立固定点代数核查。
预测全幅m_wait约0.00679545，条件DeltaK_eff约+0.00683661，DeltaA约-0.00286706，尚非数值结果。
允许一个独立三状态有限几何辅助ODE及固定二次对照，生产接口不变；1 CPU/8GiB，累计求解最多60秒。
执行任务已下发实现，预测提交后明确放行；最多五例与五次末态条件平衡，不扩参数/工况。
条件静态读出与自然动态探针区分；后者本批未授权。数值结果及独立验收待完成，原4留出保持锁定。
第78节现已完成五例/五次条件诊断并独立验收：m_wait=0.0067799748582，条件DeltaK_eff=+0.0068090076424，
DeltaA=-0.0028271428245；相对预注册预测最大偏差1.392411%，半幅、零载、严积分、E2与原功账门通过。
原JSON仍为聚合FAIL：脚本额外要求solver.success，半幅/严格条件解status=5但独立残差<6.7e-16且正定。
总管按原合同验收并保留该辅助告警，未改门、重跑或修改冻结结果。205个保存样点及五个末态已独立重建，
不称全程严格稳定性或十三位精度认证。计算1.4055725秒、峰值工作集约0.072567GiB，无GPU。
接受本理想点的暂存状态/条件静态几何读出支持；下一步须先定义自然小探针与漂移对照，尚无新批次。
第79节现已在首次轨迹前固定自然演化探针：nonlinear/E2各取trained/reference，正/负/零共12条；
正负中心差与零探针对照扣除背景，完整三状态Jacobian预测动态刚度+1.331026%、张力增益-0.404947%。
理论子agent独立复算一致，并在运行前修正偶次污染量纲/窗口定义。预测提交后授权既有执行任务在
1 CPU、8GiB、累计求解60秒内实现并运行。现已完成12/12条并由总管与理论agent独立验收：
动态刚度幅值+1.329437%、单侧张力增益-0.404470%，相对前瞻偏差均约0.12%；固定E2两状态
复增益差约2e-9。自然漂移和探针扰动、拟合/偶次污染、功账、域及保存点稳定门均通过；求解
5.58921秒、峰值约0.075974GiB、0 GPU。接受限定“自然恢复中动态可读”，不等于DCM必要性。
下一步仅授权解析筛选反对称双胞状态能否形成宏观暗/局部亮的一阶模态，尚无新数值批次。
该解析筛选现已完成并否证专属性：宏观偶阶/有符号局部差奇阶只是交换对称性；当前复端口可由
四组正参数的普通双支路Kelvin–Voigt连续模型精确匹配。邻近研究亦已覆盖连接重塑、全局弹性学习、
长程记忆及离散软模。因此不启动双胞扫描。下一门收缩为真实共享连接的跨胞复两端口及严格连续对照；
在得到连续模型不能复现的留出预测前，DCM必要性仍未建立，0新数值授权。
上述8胞静态探针不含心肌主动驱动及宏观仿射缩短，不能用盒长固定作为整体/局部分离证据；生产身份不变。
固定源、等静态加载功、连接开度与连接力分开报告。生产未实现非线性/T1/损伤/流体；原4留出锁定。
目标Nature Physics、心室/EFE方向不变；目前0项核心新机制确认，闭合胞DCM必要性尚待证据。

此前已接受证据：15个固定8自由度复Bloch右端
已完成并通过总管独立几何与解析输入重建；theta=0.02时领先系数误差分别约0.008558%和0.016599%。
本批计算0.0750725000秒，独立复核0.0177348000秒且0新右端；没有新增FEM或解盲原四留出。
长波连接伸长可写成普通应变—曲率恢复，alpha=-0.778458496485260，z_eff/b=0.49625，
严格正参数下0<z_eff<b/2。z_eff是输出恢复高度，不是机械中性面；这些结果不证明DCM独有创新。
连续对照推导已验收：保留精确平移算子只是当前离散胞链的等价重写，无须再计算两者差异。
完整基底端口含平均位移与一阶空间矩各法/切两分量；Y/W都有明确恢复式。
已纠正“连接刚度必不可由形变识别”的过强说法：给定其他组合参数可反演，但当前固定理想点
相对误差放大约75.94倍，提示独立连接力学测量可能更有信息；不是实验精度或普适不可识别定理。
第37节受载ECM边界已独立验收：必须保留P1诱发的全部Bloch谐波；约化刚度非负且受附着上界控制，
但局部位移/应变不因此被禁止放大。k=0厚层中均值端口趋软、胞内坡度端口保持有限；
均匀驱动却仍给Y=W=0，端口反差不是实际局部负荷增长或Nature Physics创新证明。
第38节已独立验收：固定有限h取切向长波极限，原c1公式只需C替换为C_h=a^2*(K_D)_xx；
C_h随厚度非增，所以|c1(h)|非增且有非零下界。这是限定经典响应律，不是厚层所有局部量都减小。
第39节Y/W共同关系与效应上界也已独立验收；固定理想参数下连接伸长的保守相对变化上界
约0.264752%（以薄层幅值为分母）。不据此声称真实组织效应微小或实验不可测。
Y/W关系是依赖独立细胞参数的模型必要检验，不是无参数规律；近零差分不取比，有限k须统一相位。
本阶段收缩“强厚度效应/DCM独占”的创新主张，保留静态分支为基线，不增加扫描或重建平台。
前轮三篇原始研究已确认一般顶底机械隔离、内部耗散模态及心肌/ECM分层材料反演存在先例。
这不是穷尽性查新；目前0项新机制获确认，可辨识性候选的条件结论已验收并收口。
第40节辨识核查已交接并由总管独立代数验收：未知端口轨迹只能确定两个组合，并存在共同尺度
及相对参数退化；两个不同且绝对已知的端口、非退化响应原则上可反演四个有效细胞参数。
这是结构可辨识性，不是实验可操作性、噪声稳健性或Nature Physics创新证明；该辅助分支收口。
第41节压缩提案也已完成。总管源码核实：常Hessian未定义有限压缩支路，不能判定失稳有无；
参照重合配对的二次向量/距离能相同，纠正将二者当作现有歧义的过强说法，见简报67。
本轮已核对2025年PRL的unbuckling与2026年Communications Physics的细胞表面力学/基底
屈曲理论，收缩一般压缩创新主张，不批准新的有限能量实现；文献模型不等于项目模型或EFE验证。
第42节科学综合已完成，总管接受‘经典基线已建立，核心新机制未确认，暂无足够强下一数值假设’。
一般法切传递、相消和压缩路线不再扩算；旧FEM局部峰6.3213%分辨率失败仍保留，非全部验证通过。
不把EFE特异实验残差作为理论探索前置门，也不因等价增强连续体吻合而终止全部细胞物理研究。
三篇连接周转原始研究已核对：一般黏弹恢复促重连、负荷分享与有限簇涨落已有经典解释。
FRAP更新不是承载键占据或单键解离率，不直接据此采用n_j反馈；目前仍0项新机制确认。
原理论agent的最小状态核查已完成，总管独立验收同n/F/机械能乃至同总交换通量的条件反例；
差异来自三阶力矩，属于经典状态闭合边界，不是新机制或DCM唯一性。数学危险率未被采纳为本构。
第44节两篇文献核查已完成：2026年已有周期加载—连接修复—组织稳定性研究，2021年已有
离散瞬态网络/连续近似与局部随机事件比较；本轮读取范围主要为题录/摘要，全文未完整取得。
没有形成可立即开算的新预测，依约收口当前宽泛连接周转支线，不称所有细胞物理已被否定。
第45节实验判别接口已完成：4行映射及一个理想双条件设计见简报72，区分局部输入、
ECM/附着校准、细胞连接读出与可选周转代理；用于反演的条件不再冒充独立验证。
实际实验读出与分辨率尚未核实，不称接口具备实验可行性或创新已成立。
数值角色已完成。第46节只读对接已完成：原规划任务“分析两课题区别与合并方案”交付的
论文2 v3 PDF第13–14页确有E1–E5实验需求及数据隔离规则，但其标题明确为“以后获取”。
本轮核对的任务交付与PDF第13–17页没有实际读出、同步精度或材料标定完成记录；
已请用户提供最新实验准备记录或可用读出清单，不据此推断整个项目没有实验数据。
仅实验能力对接待信息，不将实验准备设为理论前置门；不重复搜索或重开无明确预测的数值批次。
PDF文件v3/内部v4.0属于2026-09-03旧规划，不恢复其中A1优先或完整流固耦合的即时执行要求。
本轮未改PDF、未下发实验、未创建项目外文件、未新增计算，详见简报73。
连续两轮无新科学结果后，总管定位为尚缺具体可检验预测，而不是运行故障或实验前置阻塞。
本轮设定一个不同的纸面问题：原8自由度胞模型中，固定其他正参数，仅令角刚度kappa趋零，
theta=ka的长波展开是否非一致；只查法向输入、连接伸长Y与内部剪切/转动，见简报74。
原理论agent在20分钟预算内完成，总管独立完整能量推导吻合：法向G/theta^2的两个次序极限
分别为c20<0和0；联合尺度为Omega*theta^2/(4kappa)，见简报74.1。固定正参数旧结果不变。
保留内部剪切/转动的连续对照可复现；这不是新机制、失稳、DCM唯一或生理软化证据。
两篇定向原始文献核查已完成：Nature Physics 2018的软转动长度与JMPS 2026作者稿的
尺度分类提供直接基线，详见简报75。后者的接触弯曲刚度不能等同本项目胞内角刚度。
数学推导保留，但本轮没有形成超出已有机制的具体差别；该尺度归为适用性基线，不自动扩算。
主计划51/简报76.1纸面检查已完成：心肌侧法向加载诱发切向均值B_x=-ikAh，且P1法向
高谐波与法切刚度产生同阶J_h源，不能只替换C_h就沿用规定细胞基底迹的软角零极限。
总管发现并纠正初稿的二阶高谐波遗漏；已核对m=0闭合和软角系数，但不接受所有h固定符号。
一个充分参数界可排除“所有有限h都为零”；未确认生理参数满足，也不是DCM独有或新机制证明。
原理论agent在本次20分钟预算内交接并收口，不追全域厚度符号；未新增求值、查新或生产实现。
主计划52/简报77.1已完成并独立验收：零额外drag且C_M<=R*C_eq的诊断对照中，
松弛时间均在[tau,tau*(1+R)]，静态细胞软化不能单独产生无界长记忆；允许多个极点。
R来自完整张量比较，不能用杨氏模量比替代；精确无动力学零模不是无限慢松弛，近零相消不作证据。
生产含三类drag，故该上界不直接用于其长尾；未改变默认参数、执行数值或新增胞黏性。
此无界长记忆候选收口；下一动态主张必须说明如何区别现有drag，不以软空间尺度自动推慢时间。
两轮无新增交付的检查确认没有卡住的角色或遗漏结果；缺口是科学候选，不是工程或实验等待。
主计划53/简报78已完成：同一标量泵浦、固定保守非线性势与普通对称阻尼可产生A^2阶的
周期平均交叉差异；总管与理论agent独立系数吻合。常Hessian生产基线仍互易，不追认已有此效应。
2023受驱颗粒与2026被动齿轮作者稿提供相关时间平均机制先例，但并非相同光滑势的等价证明。
接受的是抽象反例，不是心内膜机制、新颖性或DCM必要性；不采纳有限几何、新本构或Floquet实现。
若保留该方向，下一步须先定义细胞几何/共轭端口映射和空间对称性否证，不直接增加数值工况。
主计划54/简报79已独立验收：胞高/客观内部剪切及其共轭力已定义。自镜像/平移均匀胞不能
承接抽象(1,1)泵浦；有限域全局镜像不等于逐胞剪切为零，局部交叉差可以镜像反号而偶权相消。
同奇偶空间端口只是不被镜像禁止，未证明受激发或非互易；高阶耦合未由二次能量决定。
该直接映射收口。后续若保留异质候选，先从客观胞能和真实P1输入推出耦合/模态投影，
并与保留同等内部自由度的连续对照比较；本轮不实现有限几何、不添加手性或新工况。
主计划55/简报80已独立验收：泛型纯±k子空间的三阶能为0，但完整A^2响应仍可经过
0/±2k回返；强截断不等于消元。P1法向源积分已核对，其cos/sin不是时间滞后，也不等于e/s探针。
受载均匀周期ECM不自动破坏波数守恒；有限侧边界/不兼容支撑才另查，角色过宽表述已纠正。
这只确认约化限制，未证明非零效应；不采纳有限胞能或新增求解器。总管将第78–80节归为
反例/适用性对照，暂不作为核心机制推进实现；下一任务须有具体新假设与可测预测再下发，
不因需要更多谐波而自动进入工程，也不要求实验先完成才可探索。Nature Physics目标不变。
主计划56/简报81已独立验收：固定D、连续状态下，理想解除的前后速度差可消去瞬时背景力，
但完整连接力需独立阻力校准和足够观测秩；原Y不是配对跳跃j的线性函数，角色误映射已纠正。
惯性改变跳跃阶次，奇异D需完整代数一致性，有限采样不能自动沿用瞬时式。此为经典读出接口，
不作新机制或DCM唯一性；未执行实验、解除或损伤实现。实际能力清单仍待核实，理论不以此为前置门。
连续两轮无新增交付后已排除执行/交接故障。主计划57/简报82已完成限时筛选，交0个待开算提案。
所考察底/顶连接刚度反向重分配尚无可区分预测；总管不接受由此否定所有线性/空间组织路线。
已纠正输入敏感度和过严筛选标准：等价连续表示不自动否定物理创新，理想组织不必等实验提供。
本次筛选收口，当前无新模型或数值授权；下一任务须有具体假设再下发，不重复头脑风暴。
数值任务保持完成，15例既有输出本轮只读核实仍全部检查通过；无新计算或原留出读取。
主计划58/简报83已在20分钟预算内完成并独立验收：固定生产刚度时，简单有限极点对
四块耗散倍率的时间敏感度等于模态耗散份额，和为1；局部拟合时间与循环耗散比例不自动满足此式。
源/观测不移动给定A/G的极点，角色过宽表述已纠正。总管纠正初始后向Euler假设，实际是
梯形/中点周期解；其假想衰减的离散限制不代表已观察到伪长尾或生产bug。
本结果归为经典来源判据，不是细胞新记忆或Nature Physics机制，完成收口不自动开展衰减扫描。
生产参数不改，辅助闭合胞未增加动力学；0新计算/查新/实验/原留出。
主计划59/简报84已完成两篇原始研究和概念判别：可逆T1/记忆调控与循环训练弹性已有
相关先例，但未证明纯拓扑周期记忆已被覆盖。第二篇仍按2025预印本及实际读取范围使用。
总管纠正不同邻接图“完全同几何”的可实现性、等待后消失的过度归因和可逆T1定义。
本轮没有形成待开算提案，完成收口；不采纳T1/损伤/反馈，不实现新模型。原4留出和失败证据不变。
这是独立理想边界研究，不是已实现三层耦合；不启动新FEM、扫描、原留出、流体或非线性。
Nature Physics目标保持；生产心肌FEM/ECM黏弹FEM不变，现有链不追认为完整细胞DCM。

以下为保留的阶段证据沿革；其中“当前”“只批准”等措辞仅适用于相应历史阶段。

最新进展：两个闭合细胞16自由度原型v02完成6个小型代数右端，并经总管独立几何/解析源复算验收。
相同能量和法向输入下，两坐标Ritz对共同连接相对伸长幅值高估约15.0008%，compliance差约2.4245%。
这是特定理想子模型的简化误差，不是全场15%误差、真实细胞DCM必要性或Nature Physics创新证明。
v01失败入口及182字节文件保持不变；数值任务停止新算例。四坐标解释已推导并独立核对：
两坐标确实删去了剪切/转动—配对开口模式，但这是当前理想模型的内部柔顺性，不是新机制证明。
第33节周期单胞推导已交接并定点纠错（简报57）：相位项、运动学与实际可达响应、内部量消元及
单向/自洽端口边界已区分；不接受未经证明的O(1)长波遗漏或ka=O(1)必要门。
第34节系数推导已完成并恢复完整交接，总管验收见简报59：当前严格正理想参数下，
切向一阶c1=-0.155691699297052、法向二阶c2=-0.0154524011552324，均非零。
这只是规定迹的普通线性应变/曲率传递，不是ECM耦合、DCM必要性或Nature Physics创新证明。
第35节/简报59授权冻结后执行15个8自由度复代数右端，检验渐近、奇偶、旧特例和零耦合极限；
只用单线程CPU/8GiB，准备30分钟、执行30秒，不新FEM、留出、机制或广扫描。
生产三层架构、旧46周期+30静态FEM及原四留出不变；下列逐阶段记录为历史，不重复执行。

人类于 2026-09-05 明确批准实施 science-first v04：先判断全局收缩与心内膜局部负荷之间
是否存在可预测、非平凡的关系。计算基础具备，核心科学贡献尚未得到证明；允许最多
30 个首轮二维理想体 CPU 工况，首轮已在 26 个完成处收缩；另行授权的第二批完成 8 个、第三批完成 12 个，累计 46 个。
原 4 个留出未运行。探索不必等待完整 Figure 2 认证或 C1 整理。
唯一活跃架构仍为离散心内膜弹性链＋主动心肌 FEM＋黏弹 ECM FEM；器官方向为心室/EFE。
不恢复心肌 DCM，不加入流体、真实三维几何或生物反馈，不把线性滤波当作相变或疾病机制。

最新用户优先级：创新应尽可能突出显式心内膜细胞DCM的必要性，并可由后续实验区分预测。
当前只批准主计划v04第26节/简报第45节的30分钟理论概念筛选；现有链没有独立物理细胞数及
闭合形状，不追认为完整细胞DCM。拟议扩展、局部/增强连续对照与实验接口均尚未实现，
不改生产源码或数值预算；心肌仅FEM、ECM黏弹FEM、Nature Physics和心室/EFE目标不变。
首次概念交接已回，总管排除以仿射残差自动归零作为阳性门，要求补全ECM直接内部载荷；
仅再作一次15分钟纸面补齐，见简报45.4。共同连接伸长复响应只是候选，未冻结独立预测或批准数值。
该补齐现已完成并验收（简报45.5）：共同观测和完整载荷投影明确，但候选仍为NOT_ESTABLISHED。
两任务本阶段结束；下一步由总管筛选细胞形变/连接几何与ECM耦合的具体可区分假设，不重复第26节，
不以实验尚未到位停止理论工作，也不自动启动DCM实现或增加参数扫描。

本轮已核实数值任务仍结束、无新输出。总管完成有界原始文献复核后，设定第27节/简报第46节的
30分钟纸面任务：两细胞周期截面的总周长与逐边弹性，是否允许不同的低刚度形变，且能否同时被
ECM基底驱动、在线性连接长度上观察。它是待检查的具体材料/观测选择，不是已证明的软模机制。
不重复第26节，不运行模型或原四留出；已完成46周期工况+30静态右端，累计数值170.24076614秒。

第27节已完成并验收（简报47）：两细胞交替底边形变可在总周长能下二次软、逐边能下二次硬，
并对共同连接长度可见；这只是材料/观测选择证据，未证明耦合后软模、实际驱动或DCM必要性。
总管设定第28节/简报48的三个旧case投影后处理，冻结后下发数值任务：准备25分钟、CPU后处理30秒，
只新增一个入口和一个JSON。不解新FEM/DCM、不读留出、不加扫描；原模拟计数/预算保持，后处理另记。

准备阶段发现旧actual_config未单列k_ce，数值任务在零写入/零后处理处停止。总管已核对原运行
源码哈希并重建三个完整配置摘要，均吻合且k_ce=7，批准简报48.1限定的四项补充只读来源。
冻结该澄清后恢复原三个case后处理；算法、阈值、输出与资源上限不变，不把缺失字段伪称原有记录。

本轮以前的运行基础为 P5 r03：68 项宿主测试通过、182 项 Linux 测试通过及 2 项预期平台
跳过；不是正式 Figure 2 数值 PASS。证据入口：
`tmp/paper2_figure2_fem_only_precheck_v02_r03_20260904/p5/p5_linux_cpu_precheck_r03_evidence_v01.md`。
C0 已提交同步（c62e383d）；31 个 C1 候选尚未提交，不作为本轮推导及探索前置门。
首轮 26 个非留出工况已完成，结果为 `COMPLETED_WITH_RECORDED_CHECK_FAILURES`。
numerical/summary.json 记录总耗时约 62.72 秒；26/26 单工况结构门与半幅缩放检查通过。
三个代表点中 De=2、H=0.6 的心肌–ECM 牵引峰值 S2→S3 幅值差约 6.32%，超过探索性 5% 门；
不能报告全面收敛。同位置/同分量的既有数组诊断已确认该幅值失败仍成立，
3/3 时间复核及 2/3 空间代表点通过，全部可解释同点相位差小于约 1.061°。
P0 为构造零状态，endpoint 的作用反作用为结构恒等，二者不冒称独立求解测量。
理论源级复核已撤回“当前模型严格平移不变、A1/S1整体短缩必然相同”的初始假设：
对总位移的仿射支撑与阻尼存在宏观—空间模态耦合；原预测及修正在 science_brief.md 中保留。
4 个留出仍未释放/未运行：第 11 节 v2 已登记为读取 26 例后的经验预测，但不能区分经典解释与新机制，未作为验收预测冻结。
26 例数值任务已完成并停止新模拟；纯理论续查第 15–16 节已交接。
无 ECM 的两个对称 Kelvin–Voigt 支路构成反例：等 DC/复基频整体运动与等主动功，仍可有有限的固定位置牵引差。
总管复核配对和功公式后接受其为排除“现象本身是 ECM 特异创新”的反例，而非已解释现有模型全部结果。
第 15.7 节提出的集总对照优化尚未获准：当前阻抗是多端口/多分量，不能预设三个标量 SLS 参数能够完整匹配。
第 17 节两项任务均已交接。既有 18 个基础数组的后处理已完成，9 对等周期主动功的全场 y 牵引 RMS 比为 1.05310–8.11577，
但整体短缩比变为 0.943960–0.972993，不是双约束。最大倍率来自低 A1 基线，不是最大绝对负荷。
总管独立直接 DFT/梯形积分复算最大差 1.776e-15；此为后处理一致性，不是新增空间收敛。
第 18 节理论稿经纠错补回 macro 体应力/drag 功项、内部状态允许集和离散功因子；当前集总容量对照不再开发，
但不以 Schur 表示等价否定全部线性新规律。第 21 节源参数约化预测 H_min^(0)=0.26044558；
第二批 v01 启动失败（0 个 FEM），一次授权的 v02 修复已成功完成 8/8，原失败证据保留。
总管独立复算及理论 agent 核查均支持：A1 在 H=0.260 的上界面 y 牵引均值幅值比 0.210/0.310 低约 9 倍，
两侧 D/(2E) 约 301/296；中心 S1 的 B1/e1 约 53.4，两项冻结探索门 PASS。
这不是连续最小值认证或全场卸载；A1 中心仍有显著 B1，弱法向应力厚度式尚不能定量解释实际牵引低谷深度。
接受范围及完整证据见 science_brief.md 第 23 节；冻结预测仍保存在提交 9842b3bf 的原简报，执行后追加验收不改历史预测。
8 例原始数组独立 DFT/Gauss 投影与结果最大绝对差 9.401e-19，64 个记录的结构子门通过、所有数组有限；
本次为后处理一致性核查，不覆盖旧空间失败。实际容器退出 0、1 CPU/8 GiB、无网络/无 GPU、只读项目/根文件系统。
本批求解 38.73 秒，首批加本批及失败预扣 3 秒的计算预算合计 104.45 秒；两批实际完成 26+8=34。
第 24 节无拟合双输入条件传递已交接，总管从原始数组独立指数矩阵复算，S3 最大复残差 5.8215e-10，
且 S2 残差约为 S3 的四倍；详见第 25 节。这是给定实际整体应变后的均值预测，不是全场或自主源参数预测。
A1 中心相消条件数约 207.64，宏观复应变近似差 0.117879% 对应 c0 幅值差 12.2579%；
chi0 直接套 S1 的相位差约 50.7°，该阴性项保留，不能外推为完整异质驱动规律。
第 12 节现有 8 例后处理与文献核查均已完成，验收见简报第 26 节。后处理 0.32019 秒，
总管独立指数传播与交付系数/预测最大差 2.502e-16，输入摘要一致，全部阴性项保留；没有新 FEM。
五个原始来源已记录读取层级，经典厚度传递/相消/可观测性不是创新证明；均值牵引低谷不能称作耗散低谷。
第 27 节牵引驻点已交接，总管以九个固定点的指数传播/解析导数复核，接受局部候选与条件容限；没有跨刚度独立误差保证。
总管已纠正“充分条件失败就否定预测”和“S3-only 缺少 FEM 误差代理”的建议，并获理论 agent 独立逻辑核查。
第三批按 v04 第 14 节/简报第 28 节已完成12/12，总管独立验收见简报第29节。
K_nx=0.6/1.0 的预报中心 H=0.198283976/0.314541897、各中心±0.03、每点S2/S3，
四侧 D/(2E)=169.87/153.77/120.46/114.70，位置门 PASS；仅这两个预报窗口获支持，不外推全刚度单调定律。
源预测先冻结，实际整体应变未用于重定位；事后宏观充分条件诊断四侧为正，不是严格连续误差界。
两中心B1/|c0|=13.17/3.09，不是全场卸载；主动功不相等。独立原始数组DFT/投影复算最大差4.471e-18，
12份JSON/NPZ和直接源码摘要匹配，96个记录结构子门通过、全部数组有限；不覆盖第一批旧空间失败。
实际容器退出0，1CPU/8GiB、无网络/无GPU、只读项目与根文件系统。本批57.42秒，FEM加失败预扣累计161.87秒。
实际总数46，K=.8未重跑、原4留出未运行。数值任务停止新算；v04第15节理论复核已验收，见简报第30节。
连续均匀A1的非零空间直接源来自总位移的仿射切向支撑与x向drag交叉项；ECM负责传播和法切转换。
六个既有物理点的sin/cos比随细化缩小3.89–3.93倍，cos幅值变化0.66%–1.98%；仅为镜像误差解释的一致性证据，
不证明唯一误差来源或各锚定项贡献。零耦合极限须规约刚体零模，未进行相应退化FEM。
v04第16节第一空间模态推导已交接；总管独立复核本构/平衡与边界符号，接受为待检验连续约化，见简报第31–32节。
公式分列实际宏观应变的锚定项与异质激活项，按复数相加；不闭合宏观行，不宣称已经解释FEM或创新成立。
v04第17节既有8例后处理已完成并验收，详见简报第33节；新增一个入口与一个JSON，没有新FEM。
总管另用不同状态排序及10未知量边界系统复算，系数最大差1.053e-14，原始观测最大差3.879e-18。
S3第一模态幅值差0.518%–0.819%、相位差绝对值≤0.329°；四组eta随细化下降、操作警示未触发。
保留为k=0/1的经典条件基线，不是盲预测、全场/实验认证或创新成立；停止继续精修同一基线。
后处理0.325443秒，总管复算约0.492秒单列；累计FEM仍46、FEM加失败预扣161.8682秒，原四留出锁定。
v04第18节下界候选已完成并收缩，验收见简报第34–35节：当前为NOT_ESTABLISHED，不是已证明固定域无下界。
条件误差界成立，但缺全域系数/误差控制及宏观可达性；两弹簧例子不是同一三层Fourier模型的反例，已收紧。
保持经典条件基线，不继续精修或扩算；总管补查两篇原始来源，记录读取层级，不能将“隐藏效应”本身当创新。
v04第19节已交接，接受及纠错见简报第36节：本次未在现架构内找到足够强候选，不是无创新可能的定理。
局部心肌应力反馈仅为下一候选；补回主动应变到应力的直接项，保留标量到场的维数缺口及未校准生物假设。
单次比例体/剪切谱替换不能隔离纯记忆作用；一般复空间模式须比较正负波数的同单位范数，不能冒充整体功能。
v04第20节已交接验收，见简报第37节：无ECM单元反馈临界反例成立，能量由隐含主动执行器供给。
均值控制器对照只能识别特定控制器家族中的非均匀反馈优势，不能单独识别ECM记忆或证明整体功能正常。
v04第21节已交接，简报第38节仅接受有条件的同波数O(k^-2)估计与功共轭；未证明完整闭环短波稳定。
总管指出标量闭环结论遗漏跨波数耦合，保留全算子、统一余项及频率范围缺口，不报告已排除网格风险。
v04第22节已交接验收，见简报第39节：有限维完整能量/频率界成立；连续尾界仍需统一条件，不继续精修。
下一步v04第23节/简报第40节为静态有限模式筛查：H={0.1,0.26,0.6}各S2/S3，五个固定源导数。
理论判据核查已完成；预登记冻结于2f1c9deebfb6d6a474ffe3ad52576b568cfc877c并已同步远端。
已下发既有数值任务；v01容器因FEniCSx/JIT试图写只读/root/.cache而退出1，0/6装配、0/30右端完成。
总管核对summary/manifest及实际容器状态后接受其为启动失败，不是科学阴性；失败目录、入口与容器均保留。
原两份科学文档与生产源码未变；冻结基线2f1c9dee和实际运行5ba44386分开记录。
本批已计费0.05188476701732725秒，连旧账本累计161.92011524902773秒。
总管依持续自主权限仅批准一次缓存修复重试，不另建科学合同，不释放额外科学点：

- 唯一新入口scripts/run_paper2_static_mode_screen_v02.py，优先以小适配层复用原v01计算，
  不复制整套求解代码或改原v01。唯一新结果results/paper2_static_mode_screen/v02_20260905/；
  唯一新容器prl-paper2-static-mode-screen-v02-20260905。授权前确认这三个目标未占用。
- 只新增容器内/root/.cache的512MiB tmpfs（rw,nosuid,nodev，需允许JIT共享库加载）；
  保留既有/tmp内存缓存、1CPU/8GiB、无网络/GPU、只读根/项目和仅本批结果可写。不改HOME或盘符。
- 修复准备最多15分钟；原科学输入、矩阵、观测及第40节判据完全不变，仍最多6装配/30右端。
  v02计算剩余预算299.9481152329827秒，两次合计不超过原300秒；项目7200秒停止重估规则不变。
- 用首次原定装配检查真实JIT路径是否恢复，不另加FEM烟测。任何再次失败/超限即保存停止，不自动v03。
  v02在原有manifest/summary中记录失败包身份、两次预算、缓存修复、实际启动提交和两个入口SHA256。
  两份科学文档仍使用2f1c9dee对应冻结摘要；运行提交可包含本条操作裁决与已封存失败证据，不能伪记。

v02补充裁决：容器运行时给/root/.cache默认增加noexec，适配层预检因而停止，尚未进入build_system。
总管复核错误日志、启动选项、失败JSON及入口摘要；0装配/0右端，数值计费0，容器墙钟1.041608602秒另记。
本次仍不是科学阴性；前述“不能自动v03”保持为执行者边界。现由总管明确批准一次v03操作修正：
将/root/.cache挂载选项显式设为rw,exec,nosuid,nodev,size=536870912，继续保留真实挂载预检。
唯一新入口scripts/run_paper2_static_mode_screen_v03.py，可机械调整既有小适配层但必须复用未改的v01计算；
唯一新结果results/paper2_static_mode_screen/v03_20260905/，唯一容器prl-paper2-static-mode-screen-v03-20260905。
三个目标授权前已核查未占用。准备最多10分钟，不另建诊断容器或FEM烟测；检查通过即执行原定6系统/30右端。
计算仍使用原剩余299.9481152329827秒，累计起点161.92011524902773秒；不重置或扩大科学预算。
v01/v02入口、失败目录及容器均原样保留；本次实际checkout及两次失败身份在原有summary/manifest中记录。
不改科学文档、参数、阈值或源码，不关掉noexec检查；若仍失败/超限则留存停止，不自动v04或换运行环境。

v03已完成并由总管独立验收，见简报第41节：6装配/30静态右端全部完成，三厚度均为
UNIFORM_DOMINANT_IN_TESTED_SUBSPACE，负差/比较门=134.95/71.14/27.61。停止该静态优先候选。
13个结果/12个来源摘要及原始矩阵复算一致；结构门通过不等于全面收敛，厚层lambda_non网格变化10.04%。
本批数值8.32065秒，累计计费170.24076614秒；原46周期例及4个未运行留出不变。
数值任务本批结束；同一理论agent已下发v04第24节20分钟阴性解释与下一问题筛选，不进行新数值计算。

v04第24节解释已完成并验收，见简报第42节：共同宏观伸长与零均值局部卸载给出相容能量解释，
心肌共轭增益的阴性不能替代牵引排序。有限厚度黏弹牵引已有2026原始文献直接基线，差异本身不计创新。
总管新增简报第43节/主计划第25节的一次20分钟纸面核查：均匀增益下界500/307与
全部零均值连续源上界169/(16pi^2)是否成立。候选尚待独立验收；不增加FEM/参数求值或读取留出。
成立也仅为当前源参数的静态停线条件，不证明动态机制或Nature Physics贡献。

第25节已完成并验收，见简报第44节：固定参数的两条连续静态界成立，关闭零均值源扫波数/厚度方向。
不追认离散全谱、动态或疾病结论。理论agent现已下发第26节，科学主张转向检验细胞级形变/连接
自由度是否对共同可测预测确有必要；必须与公平、可增强的连续对照比较，不能预定DCM胜出。

主量为零均值子空间最大响应减均匀响应，排除完整空间Rayleigh包含造成的平凡阳性；不是等功或记忆实验。
旧46周期工况与新静态右端分开计数；不实施反馈/动态极点，不读原4留出，不修改生产API或正式Figure 2。
4 个留出保持未运行。暂停的是不够独特的科学主张，不是整个项目或 Nature Physics 目标。
初步观测为 A1/S1 整体短缩幅值差约 0.701%–0.722%，链轴向应变峰值幅值差约 0.115%–0.608%，
心内膜侧界面牵引最大分量基频幅值比为 1.28–8.05；峰值位置、非零基线、输入功和经典线性路径仍须区分，
不得将其直接解释为细胞形变、EFE 因果或已达到 Nature Physics 的新机制。
总管已独立核验全部 26 个 case JSON/NPZ 与记录摘要一致，5 项源码输入版本匹配，
容器正常退出且符合 1 CPU/8 GiB/无网络/无 GPU/只读代码边界；没有清理任何旧文件或容器。
后续进度以任务回报和本轮 numerical 实际输出为准；不自动重跑26工况、不扩大本轮预算。
自动化 `prl-paper-2` 已更新并读回核验为 ACTIVE、每 10 分钟、绑定本总管任务；
旧 PRECHECK-only 提示已替换为 science-first 监督规则。
用户随后追加：总管可在研究目标不变时自主探索理论创新，目标期刊固定 Nature Physics；
不自动降档。首轮范围与安全例外不变，下一轮新假设与预算由总管记录后有界下发。

第 1.1–2 节保留的是历史阶段记录，不构成当前执行限制；旧实施-only/PRECHECK-only、
逐图人类门和整心房路线由 v04 对本轮的明确授权替代。正式 Figure 2 标准仍保留，
本轮已用 S1 不得再标为未见留出。历史版本和失败证据不改写。

旧 DCM–FEM–DCM Figure 2 路线的文字证据链继续保留：T128 时间离散阶段 FINAL 不变；
A1 已完成 128 个接受事务，但因 ECM 黏弹内变量未达到周期门而失败。其旧可执行源码和
`results/paper2_m2/` 已物理删除，不能再运行或迁移成 FEM-only 新模型证据。Git 已跟踪
历史仍可从删除前提交 `8f240cf38cb4db38f02b776d320562058439770f` 审计。

## 1.1 Paper 2 M0–M1 最新证据

- 执行计划：`project_control/paper2_m0_m1_idealized_model_execution_plan_v01.md`；
- M0 兼容性审计：`project_control/paper2_m0_compatibility_audit_v01.md`；
- 执行日志：`project_control/paper2_m0_m1_idealized_model_execution_log_v01.md`；
- 最终候选结果：`results/paper2_m1/idealized_strip_v03_20260903/`；
- 诊断图：`results/paper2_m1/idealized_strip_v03_20260903/m1_diagnostic_summary.png`。

M1 是一维 P1 条带加二维切向/法向运动学的身份与端口验证，不是生理标定、正式收敛或二维/三维实体证据。v01/v02 结果包作为不覆盖的开发谱系保留，v03 是当前人类门候选。

## 1.2 Paper 2 M1 接受与 M2 合同门

- 人类决定：`project_control/paper2_m1_acceptance_and_m2_contract_authorization_decision_v01.md`；
- M2 合同草案：`project_control/paper2_m2_active_myocardial_fem_identity_conversion_contract_v01.md`；
- M2A 二维身份转换已获人类授权并进入执行；
- M2A 与 M2B 分门：先做二维直接身份转换，独立检查与人类接受后才可提出三维执行附录。
- 执行授权：`project_control/paper2_m2a_execution_authorization_decision_v01.md`。
- M2A 预检阻塞记录：`project_control/paper2_m2a_preflight_failure_and_human_gate_v01.md`；
- 失败包：`results/paper2_m2/preflight_failure_v01_20260903/preflight.json`；
- 运行时恢复与常规自主执行决定：`project_control/paper2_m2a_runtime_recovery_and_routine_autonomy_decision_v01.md`；
- Docker 修复执行记录：`project_control/paper2_m2a_docker_runtime_repair_execution_record_v01.md`；
- Docker Linux engine 和既定 FEniCSx CPU 容器已验证可用；预检与冻结记录为
  `project_control/paper2_m2a_preflight_freeze_record_v01.md`；
- M2A T64 失败与 Human Gate：
  `project_control/paper2_m2a_t64_spatial_failure_and_human_gate_v01.md`；
- T64 结果包：`results/paper2_m2/identity_2d_v01_20260903/`；不得覆盖或改用其他求解器。
- S3 最小诊断授权：
  `project_control/paper2_m2a_s3_interface_traction_diagnostic_authorization_decision_v01.md`；
  仅允许 T64/C1、ID-A2/ID-S1、DCM/FEM、S2/S3 与共同界面投影比较；
- S3 诊断执行记录：
  `project_control/paper2_m2a_s3_interface_traction_diagnostic_execution_record_v01.md`；
- S3 诊断结果包：
  `results/paper2_m2/s3_interface_traction_diagnostic_v01_20260903/`；
- 诊断为 `OBSERVABLE_DEPENDENT`，不得解释为 M2A 通过或自行替换生产 traction 指标。
- S4 终止型诊断授权：
  `project_control/paper2_m2a_s4_terminal_spatial_diagnostic_authorization_decision_v01.md`；
  仅允许 T64/C1、ID-A2/ID-S1、DCM/FEM、S3/S4 与冻结共同投影比较，现已完成并停止；
- S4 执行记录：
  `project_control/paper2_m2a_s4_terminal_spatial_diagnostic_execution_record_v01.md`；
- S4 create-only 结果包：
  `results/paper2_m2/s4_terminal_spatial_diagnostic_v01_20260903/`；
- S4 正式标签为 `DIAGNOSTIC_PASS`；原生量最大 S3→S4 差为 `0.9398%`，共同投影量
  最大差为 `0.8800%`，四个新 S3 端点摘要对旧 S3 的逐项重放最大相对差为 `0`。
- Supervisor 验收与 v02 梯度决定：
  `project_control/paper2_m2a_s4_supervisor_acceptance_and_v02_ladder_decision_v01.md`；
- 当前增量合同：
  `project_control/paper2_m2_active_myocardial_fem_identity_conversion_contract_v02.md`；
  生产梯度为 S2/S3/S4；108 端点 T64 数值门已在第 53 个端点 fail-closed；
- v02 T64 执行记录：
  `project_control/paper2_m2a_v02_t64_full_numerical_gate_execution_record_v01.md`；
- v02 T64 create-only 失败包：
  `results/paper2_m2/identity_2d_v02_t64_v01_20260903/`；
- 首个失败：`ID-LN__DCM__S4__T64__C0` 功率账本归一化残差
  `1.465114585633258e-07 > 1e-08`；已完成 53/108 端点，没有 T64 通过结论。
- 功率账本最小诊断授权：
  `project_control/paper2_m2a_v02_t64_power_ledger_failure_diagnostic_authorization_decision_v01.md`；
- 功率账本诊断执行记录：
  `project_control/paper2_m2a_v02_t64_power_ledger_diagnostic_execution_record_v01.md`；
- create-only 诊断结果包：
  `results/paper2_m2/power_ledger_diagnostic_v01_20260903/`；
- 正式标签：`DISCRETE_LEDGER_MISMATCH_CONFIRMED`。H2 确认 C0/C1 仅改变验收阈值；
  H1、H3、H5 被证伪，H4 被确认；
- Supervisor 验收与 v03 修复决定：
  `project_control/paper2_m2a_v02_diagnostic_acceptance_and_v03_repair_decision_v01.md`；
- 当前 v03 增量合同：
  `project_control/paper2_m2_active_myocardial_fem_identity_conversion_contract_v03.md`；
- Phase R 端点数量澄清：
  `project_control/paper2_m2a_v03_phase_r_endpoint_count_clarification_decision_v01.md`；
- v03 执行记录：
  `project_control/paper2_m2a_v03_ledger_repair_and_t64_execution_record_v01.md`；
- Phase R create-only 结果包：
  `results/paper2_m2/ledger_repair_v03_pilot_v01_20260903/`，正式标签
  `LEDGER_REPAIR_PILOT_PASS_V03`；
- Phase T64 create-only 结果包：
  `results/paper2_m2/identity_2d_v03_t64_v01_20260903/`，正式标签
  `T64_NUMERICAL_PASS_V03`；54/54 端点、74/74 空间主量、54/54 周期门和 2/2 热点门通过；
- 最大 S3→S4 相对差为 `0.939754% < 1%`；最大 D0 相对残差为
  `2.9681468104030423e-08 < 1e-07`，最大 normwise backward error 为
  `1.0172675692304304e-15 < 1e-12`。该结论仍不是 DCM–FEM identity 判定；
- v03 T64 Supervisor 验收与 T128 授权：
  `project_control/paper2_m2a_v03_t64_supervisor_acceptance_and_t128_decision_v01.md`；
- 当前 v04 T128 增量合同：
  `project_control/paper2_m2_active_myocardial_fem_identity_conversion_contract_v04.md`；
- v04 T128 失败执行记录：
  `project_control/paper2_m2a_v04_t128_execution_failure_record_v01.md`；
- create-only 失败包：
  `results/paper2_m2/identity_2d_v04_t128_v01_20260903/`；
- 正式失败分类：`RUNNER_PATH_NORMALIZATION_ERROR`。T64 源锁、校准锁与定向测试通过，
  但 provenance manifest 在处理命令行相对源路径时异常；0/54 个 T128 端点运行，未形成
  空间门、动态 NPZ 或 74 个时间配对记录；
- 路径修复与重试决定：
  `project_control/paper2_m2a_v04_t128_path_normalization_repair_and_retry_decision_v01.md`；
- 重试使用新 create-only 目录：
  `results/paper2_m2/identity_2d_v04_t128_v02_20260903/`；
- 路径修复与 T128 重试执行记录：
  `project_control/paper2_m2a_v04_t128_path_repair_retry_execution_record_v01.md`；
- 正式阶段标签：`T128_STAGE_PASS_V04`。54/54 个端点、74/74 个空间门、54/54 个周期门、
  2/2 个热点门通过；74 个 T64→T128 配对仅标为 `T64_T128_PAIR_AUDIT_ONLY`，方向保持
  `PENDING_T256`；
- 成功包 14 个 JSON 和 12 个 NPZ（360 个数组）均为有限值，hash ledger 25/25 条目复算
  一致；原 v04 实现、首次失败包及 v03/T64 源证据保持只读。
- Supervisor 独立验收与 T256 决定：
  `project_control/paper2_m2a_v04_t128_supervisor_acceptance_and_t256_decision_v01.md`；
- 当前 v05 增量合同：
  `project_control/paper2_m2_active_myocardial_fem_identity_conversion_contract_v05.md`；
- v05 只授权完整 T256 数值阶段与 74 个三层时间门，create-only 目标为
  `results/paper2_m2/identity_2d_v05_t256_v01_20260904/`；不得在本阶段计算跨表示 identity；
- v05 T256 执行记录：
  `project_control/paper2_m2a_v05_t256_execution_record_v01.md`；
- v05 create-only 失败包：
  `results/paper2_m2/identity_2d_v05_t256_v01_20260904/`；
- 正式失败分类：`T256_ENDPOINT_RUNTIME_BUDGET_EXCEEDED`。18/54 个 T256/D0 端点完成且
  18/18 科学结构门通过；第 18 个端点耗时 `30.38510538799892 s`，超过冻结单端点预算
  `30.0 s`。第 19 个端点、74/54/2 个 T256 汇总门、12 个动态留出和 74 个三层时间门
  均未执行；
- 失败包 12 个 JSON 均有限，hash ledger 11/11 条目复算一致；manifest 中 80 个冻结
  v01-v04/T64/T128 文件当前哈希未变。
- v05.1 资源门修复与重试决定：
  `project_control/paper2_m2a_v05_t256_runtime_budget_repair_and_retry_decision_v01.md`；
- v05.1 唯一合同变化是 T256 单端点资源上限 `30→60 s`；阶段总时间 `5400 s`、内存
  `16 GiB`、科学实现和所有数值门不变；
- 全量重试必须从第 1 个端点开始并写入新 create-only 目录
  `results/paper2_m2/identity_2d_v05_t256_v02_20260904/`，不得续接或覆盖 v01 失败包。
- v05.1 资源修复重试执行记录：
  `project_control/paper2_m2a_v05_1_t256_resource_repair_retry_execution_record_v01.md`；
- v05.1 create-only 成功包：
  `results/paper2_m2/identity_2d_v05_t256_v02_20260904/`；
- 正式标签：`T256_TIME_CONVERGENCE_PASS_V05`。54/54 个端点、74/74 个空间门、
  54/54 个周期门、2/2 个热点门和 74/74 个三层时间门通过；最大 `r_12` 为
  `0.0004150504093643955 < 0.01`；
- 最大直接相对残差为 `2.9681468104030423e-08 < 1e-07`，最大功率账本残差为
  `2.515595272983527e-09 < 1e-08`，最大离散闭合相对误差为
  `2.520540448406629e-14 < 1e-10`；
- 原失败端点本次耗时 `30.62505569300265 s < 60.0 s`。全阶段耗时
  `735.4341055739933 s < 5400 s`，峰值内存 `1.1175003051757812 GiB < 16 GiB`；
- 成功包 16 个 JSON 和 12 个 NPZ（360 个数组）均为有限值，hash ledger 27/27 条目
  复算一致；v05 首次失败包、v05 实现及 T64/T128 源证据保持只读；
- 该结论不拟合收敛阶，也不构成 DCM-FEM identity、生理标定、三维或疾病机制证据。
- v05.1 Supervisor 独立验收与 v06 identity gate 授权：
  `project_control/paper2_m2a_v05_1_t256_supervisor_acceptance_and_identity_gate_decision_v01.md`；
- 当前 v06 identity 合同：
  `project_control/paper2_m2_active_myocardial_fem_identity_conversion_contract_v06.md`；
- v06 只允许读取冻结 T64/T128/T256 包并比较 S4/T256/D0 的 DCM–FEM 留出端点，输出
  `GO-ID`、`MAYBE-ID`、`NO-GO-ID` 或 `BLOCKED` 后停止在 Supervisor Gate；
- v06 不授权重新求解、改参数、改共同投影、改身份阈值、M2B、三维、流体或 GPU。
- v06 执行记录：
  `project_control/paper2_m2a_v06_identity_gate_execution_record_v01.md`；
- v06 create-only 失败包：
  `results/paper2_m2/identity_gate_v06_v01_20260904/`；
- 正式决策：`BLOCKED`。T64 manifest 对
  `tests/paper2_m2/test_protocol_v03.py` 的期望 SHA-256 为
  `4eb28d7c38f8606e590b1216b337fd5bbde3d0fe95afab43682d7d84e66bf25f`，当前文件为
  `502a5c9273c1c5b1c95f9457ffc411ed710c99f0f4e169cc89a23b92f61bf5b5`；
- T64 结果包 ledger、端点、结构门、数值门和动态留出均通过；T128/T256 源锁通过；
  v01 `combined_load_gain` 原算子哈希锁通过。阻塞来自冻结实现精确哈希，而非力学或
  identity 数值失败；
- v06 定向测试 `18 passed`，相关轻量回归 `37 passed`；正式入口耗时 `7.5614 s`，
  峰值内存 `0.03888 GiB`，未使用 GPU、网络或求解器；
- 失败发生在正式 identity 计算之前，因此不得报告 GO-ID、MAYBE-ID 或 NO-GO-ID。
- Supervisor EOF 字节诊断与 v06.1 重试决定：
  `project_control/paper2_m2a_v06_t64_test_eof_hash_diagnosis_and_v06_1_retry_decision_v01.md`；
- 当前文件为 1681 字节；只在末尾追加一个 LF 后为 1682 字节，SHA-256 从
  `502a5c9273c1c5b1c95f9457ffc411ed710c99f0f4e169cc89a23b92f61bf5b5` 精确变为
  T64 manifest 的 `4eb28d7c38f8606e590b1216b337fd5bbde3d0fe95afab43682d7d84e66bf25f`；
- v06.1 仅允许对这一路径和这对精确哈希应用 `ACCEPTED_TEST_EOF_FORMATTING_DELTA`，
  且必须同时核对 Git clean、T128/T256 当前哈希背书和其余全部源锁；
- v06.1 新 create-only 目标为
  `results/paper2_m2/identity_gate_v06_v02_20260904/`，v01 失败包保持冻结。
- v06.1 重试执行记录：
  `project_control/paper2_m2a_v06_1_identity_gate_retry_execution_record_v01.md`；
- 单例兼容正式标签：`ACCEPTED_TEST_EOF_FORMATTING_DELTA`；全部 18 项精确条件通过，
  当前测试文件没有被修改；
- v06.1 正式 identity 决策：`NO-GO-ID`。45 条正式记录为
  `35 pass / 4 maybe / 6 no_go`；只有 `ID-LS` 全部门通过；
- 主要 NO-GO：`ID-A2` 两侧界面牵引差 `80.4031% / 80.3362%`，`ID-LN` 峰值与
  波形缩短差 `18.3367% / 18.0161%`，`ID-S1` 两侧界面牵引差
  `15.0255% / 25.5128%`；
- v06.1 create-only 正式结果包：
  `results/paper2_m2/identity_gate_v06_v02_20260904/`；11/11 JSON 有限，hash ledger
  10/10 一致，源包前后哈希逐项一致，未生成 NPZ；
- 该 `NO-GO-ID` 只适用于冻结理想化二维六留出身份门，不证明任一模型错误，也不外推
  到三维、整心房、生理、EFE、实验或流体。
- v06.1 Supervisor 验收与 v07 诊断决定：
  `project_control/paper2_m2a_v06_1_no_go_identity_supervisor_acceptance_and_v07_diagnostic_decision_v01.md`；
- 当前 v07 只读诊断合同：
  `project_control/paper2_m2_active_myocardial_fem_identity_failure_diagnostic_contract_v07.md`；
- v07 只允许分解既有牵引的幅值、方向、分量、空间/时间模态，穷举一个共同的有限
  signed-permutation 坐标基，审计纯模式/组合载荷与生产提取源码；
- v07 不改变 `NO-GO-ID`，不允许拟合比例、按工况校准、修改实现、重跑端点或进入 M2B；
  若诊断指向实现或模型修订，必须先向人类报告并形成新合同。
- v07 执行记录：
  `project_control/paper2_m2a_v07_identity_no_go_diagnostic_execution_record_v01.md`；
- v07 create-only 正式结果包：
  `results/paper2_m2/identity_no_go_diagnostic_v07_v01_20260904/`；
- 正式诊断标签：`MODE_SELECTIVE_CONSTITUTIVE_MISMATCH`。四个合同条件中只有该条件为真；
  v06.1 `NO-GO-ID` 未改变；
- 四条失败牵引的共同最优实标量为 `1.094511367664237`，但共同缩放后最大残差为
  `1.9168933799157437`；8 个有限坐标基的共同最优仍是 identity，最大记录残差仍为
  `0.804030579944649`；生产单位、符号、测度、权重、分量与共同投影审计干净；
- 差异主要定位在 `ID-A2`：心肌–ECM 的 `x` 为“空间异质/DC”，两侧 `y` 为
  “空间均值/基频”。C0/CQ 的 A2+LN DC/基频叠加最大残差仅
  `0.0023057714266971428`，不改变 identity 失败；
- 正式包 12/12 JSON 有限，hash ledger 11/11 一致，0 个 NPZ；耗时
  `13.776534800010268 s`，峰值内存 `0.050426483154296875 GiB`；未使用 solver、
  endpoint rerun、Docker、GPU 或网络；
- 当前证据只支持冻结理想化二维基准中的表示级本构不等价，不判断哪种模型正确，也不
  外推到三维、整心房、生理、EFE、实验或流体。
- v07 Supervisor 独立验收与模型架构 Human Gate：
  `project_control/paper2_m2a_v07_supervisor_acceptance_and_model_architecture_human_gate_v01.md`；
- Supervisor 原始数组复算逐值重现 4/4 正式失败牵引、共同标量与 8 个有限坐标基结果；
  v07 的 22 项定向测试、74 项轻量回归和静态检查均独立通过；
- v07 Human Gate 已由人类最新决定关闭；“心肌 DCM comparator”方案未被采用。
- 人类最新架构决定：
  `project_control/paper2_myocardial_dcm_retirement_and_fem_only_architecture_decision_v01.md`；
- 最新决定进一步否决“心肌 DCM comparator”：心肌 DCM 从活跃生产、理论、参数空间、
  图件和器官级扩展中完全退役；只有历史证据保留；
- 当前 v08 迁移合同：
  `project_control/paper2_v08_myocardial_fem_only_architecture_migration_contract_v01.md`；
- v08 将建立不导入旧双表示模块的 `src/paper2_hybrid/`，移除 representation 轴、心肌
  DCM 参数/校准/identity 指标，并用六个冻结 T64 FEM 工况做严格 FEM→FEM 迁移等价门；
- v08 不授权删除旧证据、重新标定、参数扫描、三维、整心房或流体。
- v08 执行记录：
  `project_control/paper2_v08_myocardial_fem_only_architecture_migration_execution_record_v01.md`；
- 唯一活跃包：`src/paper2_hybrid/`；生产 import graph 不依赖 `paper2_m2`，公共 API 与
  端点键均无心肌表示轴；
- v08 create-only 正式结果包：
  `results/paper2_v08/fem_only_architecture_parity_v01_20260904/`；
- 正式标签：`FEM_ONLY_ARCHITECTURE_PASS_V08`。`A2/LN/LS/C0/CQ/S1` 六工况全部通过；
  规定标量、每工况 28 个完整数组、原生/共同投影牵引的最大误差均为 `0`，ECM 场
  24/24 组字节哈希相等；
- 矩阵对称性、刚体模态处理、界面作用反作用、制造解、单位/符号、周期与离散功率账本
  门全部通过；
- 正式包 9/9 JSON 有限，hash ledger 8/8 一致，0 个新 NPZ；旧参考 24 项与退役代码
  50 项前后锁一致；耗时 `189.14686104100838 s`，峰值内存
  `0.7554397583007812 GiB`；未使用网络、GPU 或 Docker socket；
- 该标签只证明代码提取迁移等价，不是生理验证或新机制结论。当前证据远未达到
  Nature Physics；该期刊仅作为后续问题设计标准和有条件战略目标。

## 1.3 Paper 2 Figure 1–2 当前理论与数值合同门

- Figure 1 已接受合同：
  `project_control/paper2_figure1_three_layer_theory_contract_v02.md`；
- Figure 2 已接受合同：
  `project_control/paper2_figure2_fem_only_numerical_credibility_contract_v03.md`，SHA-256
  `796de6a6cfa6167e30cae592128379206709ace720d4fcbe3ae80366fb504249`；
- v03 Supervisor 验收与下一步决定：
  `project_control/paper2_figure2_fem_only_numerical_credibility_v03_supervisor_acceptance_and_execution_contract_decision_v01.md`；
- Figure 2 开发门唯一顺序为
  `G0→G1→G2→G3→G4a→G5→G4b→G4→G6→G7→digest→S1`；
- 共同域冻结为 128 个空间 P0 段 × 256 个周期中心化相位 P0 段；单频场取解析段平均，
  逐步功/耗散独立按区间交叠守恒映射；
- S1 是规则和开发结果 digest 后才解盲的独立空间异质留出；
- 已接受执行合同由
  `project_control/paper2_figure2_fem_only_numerical_credibility_execution_contract_v01.md` 与
  `project_control/paper2_figure2_fem_only_numerical_credibility_execution_contract_v02.md`
  按 v02 优先级共同组成；v02 SHA-256 为
  `11ebd843cf23c404c920a0274b409a907e01cd1755a2a5812de1eb8bdc66e253`；
- 执行合同 Supervisor 接受与实现授权：
  `project_control/paper2_figure2_fem_only_numerical_credibility_execution_contract_v02_supervisor_acceptance_and_implementation_authorization_decision_v01.md`；
- 当前只有设计/执行合同被接受，尚无实现验收或 Figure 2 v03 数值 PASS。下一步仅新增
  7 个验证模块、1 个 runner 和 7 个测试，完成后停在实现候选独立复核门。

## 2. 已完成并可引用的阶段证据

- X1-K v11 已得到 `passed_x1_k_v11_transactional_survivor_r1r_c1_f1`，并已由人类终审接受；v01–v10 的失败与修复链继续保留。
- 心肌–ECM–心内膜三层快速力学基线、制造解和分离载荷证据已经形成。
- T16/T32/T64/T128 时间路径已经完成受控裁决；T128 Human Gate 于 2026-08-30 通过。
- Figure 2 v02 已冻结为时间离散阶段 FINAL；它不是整篇论文的最终 Figure 2，也不证明空间、容差或共同极限收敛。
- 空间与容差合同 v02 已闭合 v01 的八项审阅阻塞，独立结论为 `PASS_FOR_HUMAN_REVIEW`；该结论不是执行授权。
- v08 已建立并验证独立 `paper2_hybrid` 活跃命名空间；六工况迁移等价为逐值误差 `0`，
  并已通过独立 Supervisor 复核。
- Figure 1 理论合同 v02 与 Figure 2 数值可信度合同 v03 已通过独立 Supervisor 复核；
  两者是方程/验证规则证据，不是 Figure 2 计算通过证据。

关键证据入口：

- `project_control/hybrid_x1_k_transactional_survivor_repair_execution_report_v11.md`
- `project_control/prl_p6_t128_execution_and_human_gate_review_v01.md`
- `project_control/prl_figure2_v02_time_discretization_freeze_record_v01.md`
- `project_control/prl_figure2_spatial_tolerance_validation_contract_v02.md`
- `project_control/prl_figure2_spatial_tolerance_contract_v02_independent_review_v01.md`

## 3. 尚缺的论文级证据

1. 新 FEM-only Figure 2 的空间细化、时间细化、代数容差、严格离散功率闭合及终局
   细网格时间触发证据；
2. cell/meso-resolved active FEM 与 homogenized active FEM 的共同极限及粗粒化适用域；
3. Figure 3 的最小、预注册 `De × H` 状态图，以及可被证伪的稳定传递律；
4. 跨几何稳健性、独立预测和 Figure 5 验证；
5. 可投稿正文、补充材料和完整 evidence inventory。

在这些缺口闭合前，不得把目前结果表述为“DCM–FEM 已形成普适定律”或“已达到 PRL/PRX Life 投稿证据标准”。

## 4. 保留的旧 Figure 2 ST1 状态（非当前执行授权）

旧 ST0 已在当时授权范围内完成并获人类接受，执行记录为
`project_control/prl_figure2_spatial_tolerance_st0_execution_and_human_gate_review_v01.md`。
其历史授权只包括：

- A1=`D0/E1/F150/T64/C0` 与 B1=`D0/E1/F150/T64/C1`；
- A2=`D0/E2/F150/T64/C0` 与 B2=`D0/E2/F150/T64/C1`；
- 每个工况最多两个事务周期；暖启动不计为证据；
- ECM 4/6/8 层、C0/C1、共同求积、周期和功率裁决；
- 完成后停止在 ST1 Human Gate。

该历史授权现在不自动恢复；A1 失败后 B1/A2/B2 仍未开始。任何再周期化或后续端点都必须重新获得明确授权。

原运行时阻塞记录：`project_control/prl_figure2_spatial_tolerance_st1_runtime_blocker_v01.md`。
Docker/FEniCSx 已恢复；最新失败与人类门记录为
`project_control/prl_figure2_spatial_tolerance_st1_e1_warm_start_failure_and_human_gate_v01.md`。
E1 v03 的映射、SLS 周期性、体积和几何质量均通过，但归一化 KKT 残差
`1.9647424237527947e-05` 高于 C0 门 `1e-05`。按 fail-closed 规则，不进入 A1，
也不自动继续 E2、放宽门限或追加求解。

经人类批准的相位 0 诊断记录为
`project_control/prl_figure2_spatial_tolerance_st1_phase0_kkt_diagnostic_execution_and_human_gate_v01.md`。
一次额外、配置相同的 80-iteration continuation 将 KKT 降至
`9.986340629229005e-06`，全部硬门通过，但 L-BFGS 仍以达到迭代上限退出，且过门
裕量只有约 `0.1366%`。诊断 checkpoint 未直接用于 A1。人类已批准固定两段 80 次、
无第三段/无 fallback 的暖启动入口 v02；从 accepted R0 原始周期重算的 E1 v04
暖启动已通过，A1 已执行两个 T64 事务周期。全部单步硬门通过，但 cycle 2 相对
cycle 1 的界面牵引波形差 `0.0025315`、ECM `Z` 波形差 `0.0299952` 和周期末 `Z`
差 `0.0686534` 高于 `1e-3` 门，A1 端点失败。失败记录为
`project_control/prl_figure2_spatial_tolerance_st1_a1_failure_and_human_gate_v01.md`。
不自动追加第三周期，不进入 B1/A2/B2；当前等待是否批准 A1 再周期化诊断。

ST1 不包含 A3、A4、B3、B4、D1/F200N 完整周期或细网格 T128。

诊断图：`02_图表/Figures/Fig2_spatial_tolerance_st0_diagnostics_v03_20260901/st0_diagnostics.png`。

授权记录：`project_control/prl_figure2_spatial_tolerance_st0_acceptance_and_st1_authorization_decision_v01.md`。

## 5. 当前禁止范围

不恢复已退役心肌 DCM；不覆盖旧结果或已封存证据，不修改生产 API、默认参数、
正式 Figure 2 数值门或观测量以制造通过。当前允许 v04 的独立试验配置、必要 runner、
CPU Docker/FEniCSx及项目内新结果；首批最多30个周期工况已在26个处收缩，另两批已完成8和12个。
当前另行授权v04第23节/简报第40节的6次静态装配、最多30个右端解，冻结后由既有数值任务执行；
静态右端数不与既有46个周期工况混同。不执行正式 Figure 2 大批量计算。
未释放的 4 个留出工况不得提前运行；先存预测，再由总管释放。
不授权 GPU、新外部求解器、CFD、FSI、器官几何扩展、生物反馈、大参数海或历史路线重跑。
删除、项目外写入、GPU、虚拟盘符及不可逆外部动作仍需用户明确确认。

## 6. 最新终局主线与空间/容差门之后的优先级

最新路线见 `project_control/prl_independent_theory_mainline_plan_v04.md`：
先推导与反例、有限探索和留出预测，再裁决继续/收缩/暂停；有证据后才完善正式数值
可信度与稳健性、理想心室、实验校准与独立验证。流体分级后置且每一级需有科学必要性。
Nature Physics 为固定目标，不预设达到，也不自动降档；研究目标内的理论创新与有界
推进由总管自主决定，研究目标或期刊变更再由人类决定。每 10 分钟图表监督，以科学问题和证据衡量进展。

## 7. 仓库一致性待办

- 根目录 `README.md` 仍写有“X1-K 仍未通过”，与已接受的 v11 结果冲突；当前只登记为待修正项，尚未获得修改授权。
- 仓库存在较多未纳入版本控制的结果、图件和过程文件；投稿前必须建立 evidence inventory，逐项确认来源、版本、hash 和是否应纳入仓库。当前不清理、不移动、不提交这些文件。
- 本页的建立不改变任何计算结果、合同状态或执行权限，也不构成提交/推送授权。

## 8. 2026-09-08 Paper 2 反馈核门终局状态

§84 冻结批次已完成并由总管独立裁决。v01 因 FEniCS JIT 缓存未显式允许执行而在装配期
fail-closed，0 次分解、0 个右端；失败 JSON 与容器保留。仅修正缓存 tmpfs 为 `rw,exec` 后，
v02 在 1 CPU、8 GiB、0 GPU、禁网条件下完成，累计求解 28.35689074 s、峰值约 0.459 GiB。

当前分层结论：

- execution completion：`PASS`；
- algebraic/numerical derivative validation：`PASS`；
- preregistered symmetry/Fourier gate：`FAIL`；
- Fourier `k` 标签、跨网格谱比较和 gain window：`NOT_EVALUABLE`；
- scientific interpretation：当前有限链、支撑与共同仿射耦合不支持预设的平移不变标量反馈路线。

S2 的 `U_S=1.0701754314e-3`、`R_c=6.6097842785e-3`；S3 的
`U_S=1.0560189535e-3`、`R_c=7.1009072726e-3`，均超过 `1e-8` 门。完整 `G` 的候选特征值
实部均负，只提示当前基线下局部 ECM 刚化未呈现自放大，不能称为正式稳定性证明。

证据入口：

- `scripts/run_paper2_feedback_kernel_gate_v01.py`；
- `results/paper2_feedback_kernel/v01_20260907/summary.json`；
- `results/paper2_feedback_kernel/v02_20260908/summary.json`，SHA256
  `9b4534b4f455d93a41148e9adf8b5f758164bcf3c3743f5060ce9f1b529b9c2e`。

下一步仅为理论研究：把完整非循环机械算子纳入反馈稳定性分析，并识别胞身份、邻接、状态继承、
分裂事件与 ECM 局部分泌中真正需要 DCM 的条件。尚未授权任何新计算；不得追加 S4、放宽对称性门、
恢复心肌 DCM，或以流体、非线性、三维和反应轨迹补救本次阴性结果。

## 9. 2026-09-08 非循环核与 DCM 事件理论门

- 小复谱允许数学上的高增益 Hopf，但 S2/S3 等时标单位阈值约为 `8.05e5/8.39e6`，跨网格
  漂移约十倍且频率越出慢状态假设；该分支停止，不运行。
- 活跃仓库没有真实心内膜 DCM；现有固定链和通用几何分裂器均缺父女谱系、胞状态、ECM 分泌
  继承及组织级 T1 规则。
- 唯一保留候选为“守恒状态继承下的非对易事件顺序记忆”：真实事件若改变机械核，正序/逆序可
  在有限时间产生不同的谱系级局部读出，而不要求机械反馈符号翻转。
- 当前生命周期为 `PAPER_ONLY_GO`：先定义胞身份/谱系、T1、分裂守恒继承、ECM 足迹源与事件功，
  并检查共同 Lyapunov `no-go`；0 新数值、0 GPU、0 流体/三维扩展。
- DCM 只可争取胞级和谱系级留出预测的经验最小闭合，不得宣称数学独占性。若实际事件核不变、
  共同收缩条件成立或连续强对照同等预测，则路线转为 `NO-GO`。

## 10. 2026-09-08 DCM 事件新颖性与实验边界

- 文献门裁决为 `CONDITIONAL_HIGH_RISK`：一般切换失稳、顺序识别、非交换机械记忆及 T1 反馈
  均已有先例，单独的矩阵交换子或正逆序差异不具 Nature Physics 新颖性。
- 唯一保留目标是“相同最终拓扑与匹配输入/分泌预算后，慢胞状态和 ECM 仍留下可预测、谱系分辨
  的非交换闭环记忆”；暂称谱系—ECM mechanochemical holonomy，不预设拓扑保护。
- 心内膜增殖和幼龄左室机械诱导 EndMT 样状态有实验入口；心室心内膜 T1 闭环、单胞 ECM 分泌及
  EFE 主要细胞来源仍缺证据或存在争议。
- 心内膜 DCM 因而定位为机械感受、身份/邻接记忆和旁分泌控制层；ECM 源必须允许多谱系混合贡献。
- 当前仍为 `PAPER_ONLY_GO`，0 新模拟。下一步冻结两个闭合事件顺序的预算、公共同终态、共同探针、
  强阴性对照和胞系级留出；因果事件实验与留出成功前，期刊成熟度仍未达到 Nature Physics。

## 11. 2026-09-08 T1 路线停止与分裂门控候选

- T1/Floquet/二阶 holonomy 不再作为主线。在“邻接翻转只改变牵引灵敏度 `G_gamma`，分泌足迹、
  状态映射和继承均不变”的约化模型中，事件差算子只有右上块，故六项顺序对比的二阶交换子严格为
  零；纯胞态种子的三阶项亦为零。该 no-go 只适用于此约化类，不外推到会同时改变胞形、足迹、
  分泌映射和事件功的全部真实 T1。
- 唯一保留候选转为“分裂门控的单极—谱系偶极转换及 ECM 存储”。分裂相位门 `q(t)` 改变母胞
  统一平均与女儿独立感受之间的粗粒化边界；面积加权单极 `A` 与女儿差 `D` 满足
  `tau_a*A_dot=-A+chi*s_bar/t_*` 和
  `tau_a*D_dot=-D+chi*q(t)*delta_s/t_*`，因此理想线性门只改变零和偶极，不改变单极。
- 相位响应固定为
  `Phi_q=int_0^v exp[-(v-y)] q(u+r*y) dy`；对镜像等面积女儿和平滑牵引场，
  `delta_s=d_eff*grad(s).p+O(d_eff^3*grad^3(s))`。一般不等面积/非镜像分裂必须保留
  `O(d_eff^2*grad^2(s))`，不得仍宣称纯余弦律。无独立女儿极性标签时只报告 `|cos(theta)|`，
  `90 deg` 为预注册零点。
- ECM 偶极在零初始写入且脉冲后无新刺激时为
  `M=rho*D_e*tau_a/(tau_m-tau_a)*(exp(-t/tau_m)-exp(-t/tau_a))`；
  `tau_a=tau_m=tau` 时取 `rho*D_e*(t/tau)*exp(-t/tau)`。脉冲期已有 ECM 写入则必须使用完整卷积。
- 总分泌守恒仅在以下冻结条件下成立：分裂前后总面积守恒；`a` 是浓度型状态；分泌是母女儿共享
  参数的线性单位面积源；继承为浓度复制。任一条件不满足时必须实测总量，不得用单极—偶极分解
  代替证据。
- 实验/数值比较必须按相同分裂后年龄读出并冻结完整时间表；采用
  `(Y_EG-Y_E0)-(Y_LG-Y_L0)` 只消去加性早/晚分裂主效应，另以无脉冲分裂、未来女儿虚拟分区及
  母/女儿均匀刺激校准排除分裂自生力偶极、取样域差异和细胞周期增益变化。规定主动应变相同不
  冒充输入功或局部牵引相同，两者逐例记录。
- 完整 FEM 牵引读出只允许使用结果前冻结的偶极投影
  `G_D=ell_T^T*(partial t_endo-ECM/partial m)*p_M`；其符号可正、负或不可分辨，近零时不得事后
  改换读出。
- 文献门为 `CONDITIONAL`：尚未找到同时覆盖分裂相位、梯度方向、零单极、谱系偶极和 ECM 存储
  的同构工作，但各组成机制已有先例。DCM 只可称为动态胞域、分裂和谱系继承的自然、可辨识最小
  经验闭合；同信息动态材料域连续体可精确复现方程，因此不存在数学独占性。
- 当前生命周期为 `PAPER_ONLY_GO_PENDING_MINIMAL_CHECK`。下一步仅允许验证恒等式、相位/角度
  极限、参数独立可辨识性及当前主动应变 FEM 的预注册 `G_D` 是否可分辨；尚未释放完整分裂 DCM、
  参数扫描、T1 工况、GPU、流体或三维。Nature Physics 成熟度仍未建立。

## 12. 2026-09-08 分裂偶极机械门终局：有符号牵引投影受镜像对称保护为零

- v01 仅因容器命令的 `PYTHONPATH` 与 runner 冻结前缀不一致而在启动期 `FAILED_CLOSED`：
  0 次分解、0 个右端、0 次求解，不作科学解释。保留失败 JSON，不覆盖或清理。
- v02 在 1 CPU、8 GiB、0 GPU、禁网条件下完成：10 次分解、12 个右端，累计求解
  `7.005438298 s`，峰值约 `0.446789 GiB`。面积加权单极—偶极、`Phi_q` 和相等时标极限的
  代数检查通过；S2/S3 的解析导数、两档中心差分、残差与有限值检查均通过。
- 预注册增益为 S2 `G_D=4.4418265569e-4`、S3 `G_D=1.9854442043e-4`，跨网格相对变化
  `0.5530117669`，未通过 5% 门。独立数值验收为 `ACCEPT_NOT_RESOLVED`，没有发现导数实现错误。
- 独立 parity 复核给出更强结论：均匀 A1 和镜像几何下，基准轴向牵引为奇函数；
  `p_M=I3-I4` 的奇 ECM 扰动产生偶的一阶轴向牵引修正；再与奇的 I3-I4 区域权重积分，连续
  一阶 `G_D` 严格为零，等价于 `Y(m)=Y(-m)`。当前全部采用同一 `/` 对角线的三角网格不在镜像下
  闭合，故离散非零值属于网格伪手性；S3/S2 比为 `0.446988`，与趋零相容。
- 原有 signed global-axial traction-difference 机械回读路线到此停止；不追加 S4、不取绝对值、
  不把两层结果平均或外推为非零，也不事后更换方向、区域、分量或时相。该结果可作为对称性数值
  零检验保留，不能支持分裂机制、DCM 必要性或 Nature Physics 成熟度。
- 主线收缩为“外部机械梯度 -> 分裂门控的谱系状态偶极 -> 局部 ECM 偶极存储”。FEM 继续负责
  冻结输入牵引梯度、整体运动、主动功和峰值牵引；现阶段不声称 ECM 已被证明能回写一个可测的
  有符号牵引偶极。牵引幅值或能量只能在独立生物学依据成立后另立、另行预注册为全新候选。
- 当前生命周期更新为 `PAPER_ONLY_GO_LINEAGE_STATE_ECM`。下一理论门研究分裂导致的感受算子
  秩开启及谱系可观测性，并用同信息动态材料域连续体作强反例；完整分裂 DCM、参数扫描、T1、
  流体、三维和 GPU 仍未释放。

证据入口：

- `scripts/run_paper2_division_dipole_gate_v01.py`，SHA256
  `aa59b306377e50352c4b3a3e1b1b0c36b76aae2d42698031e63ca3a67fb291b2`；
- `results/paper2_division_dipole_gate/v01_20260908/summary.json`，SHA256
  `966de0c7ff308b1723614287a0e3fa2f319f5937f085e7b0d5153c7a4bdd2286`；
- `results/paper2_division_dipole_gate/v02_20260908/summary.json`，SHA256
  `65518f1fb24f441450cbdfbe25e5e447c56088d55ac14988440f59ce46bb7df5`。

## 13. 2026-09-08 独立生物物理先验与 Nature Physics 新颖性门

- 独立原始文献核查不支持有符号切向牵引作为心内膜细胞的 primary cue。当前唯一放行到新合同
  起草阶段的标量候选是：每个未来女儿下方 ECM 物理足迹内，先逐点计算一个周期的振荡小应变张量
  Frobenius RMS，再按预注册纵深核作足迹平均。水平女儿足迹已定，纵深感受核尚未冻结；界面或
  固定近表面带是 primary 候选，全厚度均匀平均只可作理想化敏感性对照。主差值为
  `D_S=S_+-S_-`；点态 RMS 与空间平均不得交换顺序。
- 该选择有心内膜垫直接先例：局部胶体变形/较大应变幅值与侵入细胞相关，抑制或去除心肌收缩会
  减少 EndMT；瓣膜内皮的 10%/20% 周期应变亦产生幅值和方向依赖的 EndMT 响应。它仍只是
  exploration-level 先验，不是心室/EFE 中唯一机械传感器的证明。
- 心内膜机械感受调控局部 ECM 有直接生物入口：斑马鱼 AVC 的 flow-responsive `klf2a` 调控
  `fn1b`/fibronectin 局部合成并影响瓣膜形成。但该证据含流动且属于瓣膜发育，不能冒充当前无流体
  心室/EFE 模型的验证。
- “分裂产生姐妹偶极”以及“ECM 正反馈跨阈值”各自已有强先例；二者简单相加在 Nature Physics
  层面为 `NO-GO`。只有更窄的命题仍为 `CONDITIONAL`：在相同最终几何、总机械剂量和面积加权
  单极下，刺激—分裂顺序选择性开启谱系反对称模态，ECM 只放大并保存该模态；角度、相位和 ECM
  松弛组合必须作为不重拟合留出。
- 后续若研究闭环，必须分别比较单极与偶极环路；候选价值条件是偶极环路先达阈值而单极保持稳定，
  不能只展示一般整体双稳态。新应变标量的定义、解析变分、镜像 parity、近零规则和空间收敛合同
  闭合前，不运行新求解。
- EFE 解释保持保守：心内膜状态可空间指导 EFE-like ECM 沉积或重塑，但不能预设心内膜女儿细胞
  是全部 EFE 成纤维细胞来源；现有遗传追踪对心内膜与心外膜贡献给出竞争结论。

## 14. 2026-09-08 未知纵深感受核下的稳健偶极理论门

- 对任意母女共享、非负且归一化的纵深核 `w(z)`，在 `A_+>0`、`A_->0` 且水平足迹严格分区时，
  面积加权机械单极守恒；未知纵深感受不破坏 rank-opening 的全场代数见证。但在真实机械可达
  子空间中，还须同时验证母平均算子非零，以及女儿差算子在母平均核中没有被动力学或纵深积分消去。
- 新 scalar 的连续 parity 已闭合：均匀基准的周期 RMS 应变幅值为偶，奇 ECM 偶极产生奇的一阶
  scalar 变化，故女儿差导数在对称性上允许非零，但不保证非零或符号。
- 严格镜像的 `/` 与 `\` 网格给出新的数值判据：基准女儿差应反号，偶极导数应同号；前者平均
  消去网格伪手性，后者差值检测镜像/标签/装配错误。镜像配对不能替代 S2/S3 收敛。
- 连续深度增益满足 `g_minus[w]=int w(z)g_minus(z)dz`，所以落在连续剖面本质上下界的凸包内。
  但首轮 8 带输出只能认证“带内常数概率权重”类；若要扩展到任意连续核，必须另给带内上下界
  或做纵深细化。所有凸包判定均使用数值误差扩张后的区间/凸包。
- 动态情形只有在获得深度分辨复传递后才能评价。令 `C_minus` 为除机械深度增益外的稳定因果奇模态
  开环因子；在互联适定且 `w` 不随时间变化时，
  `sup_omega{|C_minus(i*omega)| ess_sup_z|g_minus(z,i*omega)|}<1` 才是对所有 `w` 排除动态失稳的
  充分 small-gain 条件，不是必要条件。当前优先零频/慢反馈，不预设失稳。
- 下一步只允许起草一个 S2/S3 × 镜像双对角、8 个共同 `z/h` 物理带的最小合同；模型 ECM 坐标
  `y=0` 在心肌侧，而理论 `z=0` 在心内膜侧，故冻结 `z/h=1-y/h`。当前数值任务仅做 runner-only
  可行性核查，0 新文件、0 Docker、0 求解。合同独立验收前不运行。

## 15. 2026-09-08 分裂开启机械奇模态的合同冻结候选

- 数值可行性只读核查已确认：S2/S3 各自可在独立 runner 中构造严格 `/`、`\` 镜像网格，不改
  生产 API；四个离散合计预计 20 次分解、24 个 RHS。
- 合同不再只看女儿差导数 `g`，而是在由主动幅值偶切向与 ECM 偶极奇切向张成的二维可达子空间中，
  同时输出母平均 `A`、女儿差 `B`、母平均偶极导数 `a`、女儿差偶极导数 `g`。只有完整
  `A*g-a*B` 区间离零，且对称极限表现为 `A>0`、`B=0`、`a=0`、`g!=0`，才支持该抽样
  子空间内“分裂打开母平均隐藏模态”的 rank-opening。
- 首轮固定 A1、H=0.3、De=0.2、T128、两个网格级、两个镜像方向、八个纵深带与两档中心差分；
  仍不加入真实 DCM 分裂、反馈、流体、三维、非线性或参数扫描。
- 决策只允许：在两网格经验包络内八带同号的 GO、依赖感受深度的条件 GO、当前 scalar/参数点的
  数值 NO-GO，以及未解析/对称性或实现失败。当前严格对称合同不能单独判定“母细胞已经感知”；
  合同独立接受前仍为 0 新计算。
- 若合同接受，唯一新 runner/JSON 路径及 create-only 规则已冻结；执行必须绑定合同提交的精确 SHA，
  并记录相关源文件哈希。不存在自动换名、覆盖旧证据或无门槛启动 S4。

## 16. 2026-09-09 外部专家方案采纳与 P0 执行

- 外部指导 `EXP-20260909-001-paper2-lineage-ecm` 已按原件与原哈希登记到 `plan/active/`；用户已明确要求执行。项目采纳范围为 P0–P2，P3 有前置条件，P4 仅设计，P5 暂缓。
- P0 已 `passed`：v01 不变，新建 v02 runner 与宿主 watchdog；8 个聚焦行为/静态合同测试全部通过。修订覆盖互斥裁决、`RESOLVED_SMALL_GAIN`、任意带内常数纵深核的完整 `R[w]=sum w_b R_b` 保守证书、单次调用门、宿主 watchdog、部分完成留痕及非有限值字段记录。
- P1 当前 `blocked`，科学执行 `not_run`：Docker Desktop 后端未就绪，`com.docker.service` 为 `Stopped/Manual` 且当前权限无法启动。v02 结果目录仍不存在，0 FEM、0 分解、0 RHS，唯一正式尝试未消耗。
- 当前不得进入 P2/P3。恢复条件仅为在有权限的桌面会话中使 Docker Desktop 正常运行，然后重新核对基线、关键源哈希、runner 哈希、镜像与 create-only 路径；不得改阈值、自动重试、生成 v03 或改用 GPU。

证据入口：

- `project_control/external_guidance_adoption_EXP-20260909-001-paper2-lineage-ecm_v01.md`；
- `project_control/paper2_lineage_ecm_active_execution_plan_v01.md`；
- `project_control/paper2_lineage_ecm_p0_stage_report_v01.md`；
- `project_control/paper2_lineage_odd_mode_gate_execution_contract_v02.md`；
- `project_control/paper2_lineage_odd_mode_gate_v02_execution_authorization_v01.md`；
- `scripts/run_paper2_lineage_odd_mode_gate_v02.py`；
- `scripts/run_paper2_lineage_odd_mode_gate_v02_host.ps1`；
- `tests/test_paper2_lineage_odd_mode_gate_v02.py`。

## 17. 2026-09-09 谱系奇模态 P1 v02 正式尝试失败闭环

- Docker Desktop 恢复后，已按一次性授权启动 P1 v02 正式尝试；该授权现已消耗，不允许自动重试。
- 镜像、HEAD、runner、受控源哈希和容器资源门全部通过：1 CPU、8 GiB、禁网、只读根、只读项目挂载、0 GPU。S2/S3 双镜像网格预检亦通过。
- DOLFINx/FFCx 在首个 S2 离散开始前尝试写入 `/root/.cache`，因根文件系统只读触发 `OSError [Errno 30]`。正式结果为 `FAILED_CLOSED`，容器退出码 1。
- 求解账本为 0/20 次分解、0/24 个 RHS、0 s 线性代数，runner 墙钟 3.937876581 s。因此科学状态为 `NOT_EVALUABLE_DUE_TO_EXECUTION_FAILURE`，不是 H0 的 NO-GO。
- 结果 `results/paper2_lineage_odd_mode_gate/v02_20260909/summary.json` 已冻结，SHA256 为 `b2202f295d3521741523c00902e965d3622a2fad41ef2180c0618c3348cc4cf3`；退出容器与失败结果均保留。
- P2/P3 继续阻塞。已形成仅待用户裁决的 v03 最小运行时修复提案：只为 `/root/.cache` 增加 `rw,exec,nosuid,nodev,size=536870912` 的内存 tmpfs，科学规格和资源预算不变；当前尚未获执行授权，未创建 v03 runner，未进行第二次尝试。

证据入口：

- `project_control/paper2_lineage_odd_mode_gate_v02_failure_record_v01.md`；
- `project_control/paper2_lineage_odd_mode_gate_v02_execution_authorization_v01.md`；
- `project_control/paper2_lineage_odd_mode_gate_v03_runtime_repair_proposal_v01.md`；
- `results/paper2_lineage_odd_mode_gate/v02_20260909/summary.json`。

## 18. 2026-09-09 谱系奇模态 P1 v03 最小运行时修复授权

- 用户在收到 v02 `FAILED_CLOSED` 记录与 v03 最小修复提案后明确回复“批准执行”。
- 授权仅覆盖一个 v03 小适配 runner、宿主 60 s watchdog、聚焦静态/行为测试以及一次新的 P1 CPU 正式尝试。
- 唯一运行时变化是为 `/root/.cache` 增加 `rw,exec,nosuid,nodev,size=536870912` 的内存 tmpfs；根文件系统、项目挂载继续只读。
- A1、H=0.3、De=0.2、T128、激活幅值、S2/S3 双镜像网格、八带纵深核、FD、裁决、20 分解/24 RHS、30 s 线性代数和 60 s runner 门均不变。
- 资源仍为 1 CPU、8 GiB、禁网、0 GPU；不安装依赖，不改 `HOME`，不清理 v02，不执行 P2/P3。
- v03 使用全新 create-only runner、wrapper、结果目录和容器名。正式尝试启动后无论成功、失败或超时均消耗，不自动 v04。

证据入口：

- `project_control/paper2_lineage_odd_mode_gate_v03_runtime_repair_proposal_v01.md`；
- `project_control/paper2_lineage_odd_mode_gate_v03_execution_contract_v01.md`；
- `project_control/paper2_lineage_odd_mode_gate_v03_execution_authorization_v01.md`（在 runner/wrapper 哈希冻结后完成）。

## 19. 2026-09-09 谱系奇模态 P1 v03 执行完成但未解析

- v03 唯一正式尝试以退出码 0 完成；执行层 `PASS`，20/20 次分解、24/24 RHS，线性代数 14.470801716 s，runner 墙钟 24.389381747 s，峰值 RSS 0.429302215576172 GiB。
- 1 CPU、8 GiB、禁网、只读根/项目、0 GPU、镜像、源哈希、runner 哈希和 `/root/.cache` 512 MiB 可执行 tmpfs 门全部通过。
- 镜像 parity、线性残差、两档 FD、预期近零 `B/a`、八带同号负 `g`、八带完整行列式离零和混合纵深核保守证书均通过。
- 冻结的 5% 两网格门未通过：8 带中 6 带的 `g` 相对变化超过门限，最大为 7.3426%。最终互斥分类是 `NOT_RESOLVED`，不是 NO-GO，也不能升级为稳健 GO。
- v03 授权已消耗；不追加 S4、v04、改阈值、换 ROI/读出或再次运行。P2/P3 继续阻塞，当前无新数值授权。
- 结果 `results/paper2_lineage_odd_mode_gate/v03_20260909/summary.json` SHA256 为 `d8882a7350996a9be6c364272ca51f9eb383201599bcfed73a8129bff3fd5b2d`；退出容器保留。

证据入口：

- `project_control/paper2_lineage_odd_mode_gate_v03_execution_record_v01.md`；
- `project_control/paper2_lineage_odd_mode_gate_v03_execution_authorization_v01.md`；
- `results/paper2_lineage_odd_mode_gate/v03_20260909/summary.json`。
