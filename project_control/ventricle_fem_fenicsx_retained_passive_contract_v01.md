---
document_id: PRL-FEM-FENICSX-RETAINED-PASSIVE-V01
status: adopted
authorization: user raised the project stage budget to 800 MiB and instructed continuation
parent: project_control/ventricle_fem_fenicsx_thin_mesh_contract_v01.md
planned_result: results/ventricle_fem/f6s1p_retained_passive_v01_20260917
---

# F6-S1-P：复用合格网格的十态被动验证

用户本轮明确“本项目预算提高到800MiB，继续执行”。按前文语境将项目新阶段默认
输出预算从256 MiB提高到800 MiB，不是把整个项目缩减为800 MiB，也不提高3 GiB项目硬限。
原历史合同和失败包不改写。停止保全空间另外预留64 MiB；单一任务、超预算停止、
不自动删除证据、不自动重跑的规则保持。此合同同时记录该存储决定。

## 仅改变输出预算与输入复用方式

复用F6-S1-M的raw/candidate_0_mesh.npz，SHA-256
`157265c350367a95f36c40c5951117272ceeccac9f273ec65e5000eb81627f65`。
不再次调用Gmsh；粗网格3541单元，细网格只作中点四分14164单元，同一多边形域。
再次独立核验两网格正面积、20度、共享层界、源轮廓及参考面积门后进入力学。
源几何SHA及外轮廓、内腔/层界、规范点与父合同保持一致。

沿用P2位移/P1压力，六阶积分、三维平面应变近不可压Neo-Hookean，mu=1、kappa=1000。
A固定ux/uy、B固定uy，其余外壁自由；内壁随动压力p/mu=[0,.02,.04,.06,.08]。
两网格最多10个唯一平衡态，首个力学失败立即停止并保全，不改变步长或阈值重试。
保留父合同全部残量、应力重算、虚功、局部max|J-1|<=1%、两网格响应门。
主动应力只做既有Jacobian一致性检查，不进行主动收缩平衡态或生理心动模拟。

一次科学容器，1200秒、1 CPU、8 GiB、0 GPU；固定已有镜像、禁网、不拉取/安装。
执行前只读核验Docker服务端及镜像；不修复/重启Docker。阶段800 MiB包含全部输入副本、
源码、原始状态、日志和图件，另64 MiB保全空间；项目3 GiB硬限。当前预测307.35 MiB，
不利用新增预算扩大参数矩阵。每次状态前检查时限和完整状态保全空间。

所有旧包和原failed/blocked保持。新包create-only；仅读取真实状态生成结构及形变/J/应力图，
有五态则给五态图或GIF，不足则明确实际数量，不填补虚构状态。加载级不是生理时间。
无项目外新建、删除、GPU、安装、远端推送。验收后按现行决定本地提交main。
