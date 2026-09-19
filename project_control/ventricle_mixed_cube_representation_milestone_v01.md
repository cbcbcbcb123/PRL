---
document_id: PRL-MIXED-CUBE-REPRESENTATION-MILESTONE-V01
date: 2026-09-19
authorization: user_authorized_resolve_representation_milestone_20260919
status: failed
execution_result: ventricle_mixed_cube_representation_milestone_result_v01.md
native_interface: passed
complete_candidate_qualification: failed
scope: native_P3_interfaces_and_same_load_manufactured_solution_qualification
---

# 一次解决离散表示资格问题：里程碑授权

用户最新明确决定：“你能一次性修好目前的问题吗？目前额度不限制，阶段性解决一个大问题在回复我”。
本记录取代该问题中此前“一次容器用尽就必须再次审批”的微批次次数限制；不改写旧失败合同或旧批准记录。
在本里程碑内，可以根据保留的失败证据修正接口/验证实现，重新运行必要的资格检查和原同载八工况，
不再逐小修补请求授权。不是任意项目、模型、参数、外部路径或运行环境修改的无限授权。

## 完成目标

1. P3导出、原生表达式/装配/切线、非零patch、接受态及路径独立验证一致。
2. 完成原[同载八工况](ventricle_mixed_cube_representation_batch_v01.md)：原制造解、材料、载荷、边界、网格和八阶积分不变。
3. 独立读回所有保存状态，6/8点Gauss-Duffy积分复核、旧Q6/新Q8积分对照、P3/P1与P3/P2配对误差及成本明确。
4. 判定P3/P2是否满足预注册κ100资格门，以及压力表示是否贡献于原位移误差；不得预设必须passed。
5. 保存结构/真实求解状态/误差图、更新导航、普通推送main后，汇报这个完整问题，而非单一小修复。

## 不变的安全与科学边界

- 原门限不放宽，旧失败和原始包不可覆盖。每次尝试create-only且登记原因、代码哈希、配置、结果和总次数。
- 每次容器仍为已有固定本地镜像、单CPU/8GiB、1800秒含120秒保全、0GPU、禁网、只读项目；
  无后台无条件自动重试循环。追加尝试必须由明确错误和修正/待验证假设驱动，不重复未改变的失败。
- 一次只运行一个科学任务。磁盘余量保护、至少128MiB停止保全、代码仓3GiB保持；不恢复固定阶段结果配额。
- 接口/装配、哈希漂移、写入或安全失败必须先停止当前计算，保留证据，再有依据地修正；不能绕过前置检查。
- 若只是控制工况精度未过，但安全与方程合格，仍完成独立候选；候选不通过时先分析原因，不篡改门限。
- 不改材料/载荷来制造通过，不自动引入新单元家族或更大的科学参数扫描。
- 不启动/修复/停止Docker Desktop，不安装/更新/拉取，不删除文件、创建映射或触碰运行时目录。
- 不运行心室、三维主动、生长、FSI或DCM；本里程碑通过也不等于原心室κ1000合格。

首个新尝试为`representation_v02`：
`E:\Temp-Projects\PRL-results\ventricle_fem\mixed_cube_representation_v02_20260919`。
已有`representation_v01`及此前所有重要证据纳入保护。若需后续尝试，仍在已批准PRL-results内建立清楚编号的新包，
只运行需要复验/尚未完成的登记工况并保留其与完整矩阵的映射；不复制第二套求解器。

输出与代码按用户要求仅正常同步，不额外创建评审包。定量图基于真实保存状态，迭代不是生理时间。
如遇新外部权限需求、资源不足或需要实质更换科学方案，报告实质阻断；不能因“额度不限”推断这些授权。
