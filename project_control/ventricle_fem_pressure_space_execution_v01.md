---
document_id: PRL-FEM-PRESSURE-SPACE-EXECUTION-V01
date: 2026-09-18
status: failed
contract: project_control/ventricle_fem_pressure_space_contract_v01.md
result_root: E:/Temp-Projects/PRL-results/ventricle_fem/f6s1r_pressure_space_v01_20260918
automatic_retries: 0
---

# F6-S1-R：压力离散对照在圆环首个非零载线性求解失败

## 用户决定与本轮范围

已将“理想化三维 + morphoHeart公开资料起步、后续自有实验替换”记录为
[发育—FSI路线决定](ventricle_development_fsg_idealized_public_data_decision_v01.md)。
这不是把现有模型改标为三维；当前仍需完成固体数值资格。

用户另行明确同意同几何/材料/压力/1%门的有界压力空间对照；最多四个平衡态，
圆环通过后才进入原轮廓，单CPU、0GPU、失败即停、不自动重跑。
仅启用DG2逐单元二次压力；P2位移、六阶积分、mu=1、kappa=1000、规范固定点和求解器不变。
旧CG1路径仍是默认值，旧对照从保留数据读取，没有重算。

## 实际结果

一次正式容器耗时17.0021136秒，出口码2；主机命令为
`python -B -X utf8 -m prl run fem-fenicsx-pressure`，完整容器命令见结果包command.json。
已检查固定本地镜像、单CPU、8GiB、禁网、只读项目挂载、无GPU和无自动删除。
这条运行命令只用于记录，已有结果路径create-only，不授权再次执行。

| 对象/载荷 | 保存 | 验收 | 解释 |
|---|---|---|---|
| 圆环M0、896三角形、p=0 | 是 | passed | 零位移、零混合压力、J=1 |
| 同圆环、p/mu=0.02 | 是 | failed | 首次线性求解失败，Newton更新0次 |
| 原轮廓零载/首个压力 | 否 | not_run | 严格遵守失败即停 |

保存2个状态，只接受1个零载平衡态。新DG2没有任何合格的受压平衡解。
失败态SNES reason=-3，求解器自由残量0.008667040857078829，独立重算自由力约0.008667040857078805。
按[PETSc枚举文档](https://petsc.org/release/manualpages/SNES/SNESConvergedReason/)，-3表示线性求解失败。
本次未保存KSP/MUMPS详细错误和切线矩阵，具体失败原因unknown，不能直接断言奇异、材料错误或体积锁死。

失败态仍为u=0、p_m=0、J=1；其局部体积检查单项为真，只因未发生任何Newton更新。
独立审计整体failed，不得用J=1宣称体积误差已消除。ring_completed字段仅表示两个文件存在，
不代表两个平衡态均通过；accepted_equilibria=1与contour_status=not_run明确区分。
响应/解析对照检查在此失败态为false，同样不能据此认定锁死，因为根本未得到平衡响应。

## 旧轮廓状态的只读诊断

未新增平衡求解，对已保存CG1状态作L2投影：将J−1分解为连续线性压力空间可表示分量与正交剩余。

| 指标 | 粗3541单元 | 细14164单元 |
|---|---:|---:|
| max abs(J−1) | 6.7116709% | 11.1524774% |
| CG1投影峰值 | 0.0601079% | 0.0734139% |
| 未表示分量的平方L2范数比例 | 99.9161297% | 99.7494406% |

投影与p_m/kappa的点值差约2.48e-14/5.62e-14，符合原弱压力方程。
这是离散约束能力的重要诊断，不是物理组织体积分数，不是唯一根因证明；不能排除边界几何因素。
原1%局部门及F6-S1-P/Q失败裁决保持。DG2试验尚未证明能修复，也未证明足以用于三维或严格不可压极限。

## 数据、图件与交付边界

新结果在[外置结果页](../../PRL-results/ventricle_fem/f6s1r_pressure_space_v01_20260918/index.html)。
formal_invocation_manifest.json保全一次正式调用原件；post_verification.json为保存态独立审计，
volume_projection.json记录旧状态诊断；sources_at_execution保留执行时源码和合同。
455个父证据文件逐一核验不变；本轮未删除/搬移旧证据，未安装/拉取/重启Docker，也未推送远端。

图件按cb-paper-figure-workflow与cb-plot-unified-style保存物理复制数据、可编辑Notebook、
helper/style快照、600dpi PNG和可编辑SVG。结构面板来自新圆环参考网格；应力和J面板明确标为
旧CG1已接受平衡对照；新DG2只画真实迭代0残量。没有伪造五个状态或心动GIF。
显示等效Cauchy应力的积分点算术均值，局部J为单元积分点最大绝对偏差；1倍真实变形、不平滑数据。
图件冻结验收表示图文正确，不表示科学门通过。

开发回归：60测试与21子测试passed，覆盖原CG1、DG2独立基函数/压力约束、相同物理网格、
create-only拒绝与FEM唯一入口。它们不替代受压求解资格或生物学验证。

只读复核命令（预期科学状态failed，CLI退出1）：
`python -B -X utf8 -m prl verify fem-fenicsx-pressure`。
图件Notebook从包内源数据复算，不需要Docker；冻结后修改/重画应新建图版本。

本轮figure_runtime是Codex为Matplotlib/Jupyter创建的专用缓存：
`E:\Temp-Projects\PRL-results\ventricle_fem\f6s1r_pressure_space_v01_20260918\figure_runtime`。
其清理未获精确授权，保留且计入体积；不得连同任何输入、原始状态或唯一图件自行删除。

## 唯一下一步：先诊断混合线性系统

本次有界科学授权已用完，不自动换方案重跑。建议下轮先在保留初值处取得KSP/MUMPS错误、
固定自由度/矩阵维数及压力块信息，检查有限kappa下局部压力块和静态消元等价性，
区分组装/约束、尺度/主元及实际离散响应问题，再冻结一次最小修复对照。
不得预先把原因归结为材料太硬，也不降低kappa或放宽原1%门来获得通过。
新的求解、主动、三维、FSI与生长实现须按对应切片授权；目前全部not_run。
