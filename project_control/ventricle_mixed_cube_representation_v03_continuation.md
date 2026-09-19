---
document_id: PRL-MIXED-CUBE-REPRESENTATION-V03-CONTINUATION
date: 2026-09-19
authority: ventricle_mixed_cube_representation_milestone_v01
status: failed
execution_result: ventricle_mixed_cube_representation_milestone_result_v01.md
---

# 只续算尚未启动的三个登记工况

v02完成四例，在第五例mms_p3p1_n4的第28个更新方向触发正J路径保护：20次减半均未获准，PETSc101终止。
最后接受态、原始候选方向、failure_state和失败日志保留，不放宽保护、不把失败态作为初值、不重复该例。
这不是新的材料/载荷扫描。根据本轮用户里程碑授权，继续原矩阵中尚未启动的三个独立工况。

顺序：mms_p3p2_n4、mms_p3p2_n8、mms_p3p1_n8。候选优先，避免诊断控制再度提前中断候选资格。
所有工况配置从原矩阵原样筛选；唯一变化是未运行子集、排序和最多3次SNES登记。
仍为每例零初值、同材料/载荷/BC/八阶积分、原Newton及正J门。
单CPU/8GiB、1800秒、固定本地镜像、禁网、0GPU、0自动重试，不改变Docker运行时。

v02原执行225个文件、31,624,379 bytes已冻结：
`E:\Temp-Projects\PRL-results\ventricle_fem\mixed_cube_representation_v02_20260919\execution_manifest.json`
SHA-256=`843e537ca1a31e19688146ecdfba4957bb4d87868fc7e80778ca6bb6f2bc44aa`。
新包：`E:\Temp-Projects\PRL-results\ventricle_fem\mixed_cube_representation_v03_20260919`，create-only。

v03单包不含完整收敛序列，因此其原始summary可能blocked/failed；里程碑交付必须独立重算并汇总v02/v03。
诊断P3/P1 n4失败不得抹去；全矩阵配对压力贡献若缺合格n4必须unknown，不能以候选成功补齐。
候选κ100资格、接口完整性、控制失败和原心室κ1000未获资格分别报告。
