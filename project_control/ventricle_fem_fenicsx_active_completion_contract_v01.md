---
document_id: PRL-FEM-FENICSX-ACTIVE-COMPLETION-CONTRACT-V01
status: adopted
approval: current_user_scientific_continuation_with_no_repeated_equilibria
parent_contract: project_control/ventricle_fem_fenicsx_ring_active_contract_v01.md
parent_evidence: results/ventricle_fem/f6s0_fenicsx_ring_active_v01_20260917
planned_result: results/ventricle_fem/f6s0_active_completion_v01_20260917
---

# F6-S0未运行主动工况续算

仅补原F6-S0的G2，不重新计算已通过的G0/G1。原因是首次正式调用在保存10个被动状态后，
验证器读取单行压力数组异常，已修复并从保存态复核G1全部通过。

唯一新增科学调用：两档既有圆环网格，各运行纯主动与压力+主动两条延拓，
lambda=[0.25,0.5,0.75,1]，共16个新平衡态。Ta*=0.10mu，混合工况p*=0.04mu，
lambda=0及P1A0=0.04mu直接引用父包。不得通过重算被动态、更换参数或放宽阈值补齐。
仅心肌层加入Ta(Ff0)⊗f0，父合同全部材料、几何、边界、局部1%J和网格门保持。

续算前逐项复核父包原始数据/网格哈希、G1裁决、镜像ID及单行压力映射回归；
新状态必须保存实际初值、完整u/p、F/J/被动与主动应力、SNES历史、反力及独立复核。
四终态图引用两个父状态和两个新终态，另输出真实主动延拓态及动图。

新路径create-only；固定本地镜像、--pull=never、单CPU、0 GPU、禁网、不安装、不删除；
最多1200秒，128 MiB阶段上限另留64 MiB停止空间，项目3 GiB门。
第一次失败即停止，不自动新增版本或重跑，不提交或推送。

用户本轮“好的，继续我们的科学问题”继续了已提出的G0→G1→G2范围。
本执行补充将读取错误后的G2恢复视为同一授权科学阶段的继续：允许一个额外受限容器仅计算
尚未运行的16态，不重试任何已有平衡态。实际容器/调用次数如实记为2，原调用失败不改写。
这是对原内部合同“一次调用”工程包装限制的明确补充，不扩大模型、工况或科研预算。

累计正式容器墙钟上限仍为1200秒；第二次上限取1200减首次实耗，并至多600秒。
父包与续算包的合计逻辑输出上限仍为128 MiB，另留64 MiB停止空间；首次数据、来源及
独立资格全部只读引用。停止条件、阈值、CPU/GPU和禁网边界保持。
