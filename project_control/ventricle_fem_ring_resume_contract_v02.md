---
document_id: PRL-FEM-RING-RESUME-CONTRACT-V02
status: passed
accepted_at: 2026-09-18
authority: user latest 好的，继续推进科学主线 after the proposed bounded interface-first requalification
execution_status: not_run
preserves: project_control/ventricle_fem_ring_resume_contract_v01.md
---

# F6-S1-S4 v02：真实接口先验，首个圆环压力态恢复

本轮执行用户同意的唯一下一步，不改变研究路线、不加入收缩或扩大载荷矩阵。
原v01失败包冻结保留；采用既有入口加 `--resume-first-ring --resume-revision 2`。

## 单次调用的顺序

1. 同一固定容器中做一个6自由度对角方程接口夹具，无FEM几何、材料或科研数据。
   使用真实PETSc SNES监测回调和生产Ring.monitor，检查只读锁向量能读取且留存独立副本。
   使用生产Ring.bind_factor_options，按实际KSP前缀绑定余量100；通过真实MUMPS分解回读ICNTL(14)=100、INFOG(1)=0。
   已知解、独立相对残量和记录的首末向量均核验，阈值1e-12。夹具不计作心室平衡或科学结果。
2. 只有接口夹具passed，才重建原M0圆环，检查与保留零载的网格及DG2混合映射完全一致。
3. 原零载独立验证后，原样作为唯一 `p/mu=0.02, Ta=0` 工况初值；不重算零载，最多1次FEM非线性求解。
4. 保存真实Newton迭代、最终状态、残量及实际MUMPS回读；独立验证后出模型结构及形变/应力/局部J图。
   若不足5个真实状态就如实显示全部，不补造帧；Newton迭代不是生理时间。

## 物理与门限保持

完全继承v01物理、几何、边界、载荷、积分与门限：2D平面应变有限变形NH，mu=1、kappa=1000，
64周向×径向1/1/5层，P2位移/DG2压力；腔面随动压力、外壁自由、三个刚体规范约束。
三层被动材料暂相同；主动应力关闭。SNES/线搜索及30步上限不变。
原max|J-1|<=1%、独立自由力<=2e-6、弱压力<=1e-8、DG2点态约束<=1e-9、解析/CG1响应差<=5%等全部不放宽。
接口通过不代替科学通过；只有原独立物理门也全部通过，才接受该压力态。

## 资源和停止

唯一新结果目录：`E:\Temp-Projects\PRL-results\ventricle_fem\f6s1s4_ring_first_pressure_v02_20260918`，create-only。
一次固定镜像容器，单CPU、8GiB、禁网、0GPU，总限1200秒；预计新增256MiB，64MiB保全和10GiB磁盘余量门。
接口夹具最多1次求解/分解，FEM最多1次非线性尝试；任何一步失败立即保全，不自动重跑、不新增变体。
旧失败证据及619个既有祖先、上一v01新增包均按哈希保护；无关工作区修改保留。
不安装/升级/拉取/重启Docker、不删除文件、不推送。只在main本地精确提交阶段证据。
不运行额外压力、细网格、实际轮廓、主动收缩、3D、FSI、生长或ECM反馈。
