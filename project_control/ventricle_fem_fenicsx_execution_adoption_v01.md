---
document_id: PRL-FEM-FENICSX-EXECUTION-ADOPTION-V01
status: passed
adopted_at: 2026-09-17
contract: project_control/ventricle_fem_fenicsx_ring_active_contract_v01.md
---

# F6-S0 执行采纳

用户在Docker修复验收后指示“好的，继续我们的科学问题”。本轮据此继续已提出的F6-S0：
先完成G0容器导入、JIT与微型装配，G0通过后执行合同内唯一一次G1→G2科学调用，
G1失败即停止G2。原合同的材料、网格、载荷、误差门、1200秒、128 MiB阶段上限及
64 MiB停止余量保持有效。运行器保持单CPU、禁网、固定本地image ID、0 GPU、0自动重跑。

容器只读挂载项目源码；正式结果单独挂载当前项目内create-only结果路径至`/out`。
此可写挂载仅保存本阶段受预算约束的证据。G0不写容器持久文件，结果由宿主保存。
退出容器保留，不删除Docker隔离目录，不拉取、安装、更新、提交或推送。

本次新增记录明确取代原合同“尚未授权”的执行状态描述，不改写原合同的冻结科学内容。
