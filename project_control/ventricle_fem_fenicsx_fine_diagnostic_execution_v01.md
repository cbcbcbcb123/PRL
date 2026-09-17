---
document_id: PRL-FEM-FENICSX-FINE-DIAGNOSTIC-EXECUTION-V01
status: failed
delivery_status: passed
contract: project_control/ventricle_fem_fenicsx_fine_diagnostic_contract_v01.md
result: E:/Temp-Projects/PRL-results/ventricle_fem/f6s1q_fine_diagnostic_v01_20260917
---

# F6-S1-Q：均匀加密缩小超限区域，但未降低最大局部体积误差

按用户“继续”及[两态合同](ventricle_fem_fenicsx_fine_diagnostic_contract_v01.md)，只补M1零载和p/mu=0.02。
M1与之前保存的细网格逐数组一致，14164单元/7457顶点；0次Gmsh、0次M0新求解。
一次受限容器40.770秒、单CPU、8 GiB、0 GPU，禁网、固定已有镜像；没有安装、拉取或Docker修复。
保存2态、接受零载1态，非零载只在local_volume门失败即停；0重试、0后续加压、0主动收缩。

| 同一p/mu=0.02 | M0保留粗网格 | M1新细网格 |
|---|---:|---:|
| 单元数 | 3541 | 14164 |
| max\|J−1\| | 6.71167% | 11.15248% |
| 超1%积分权重参考体积分数 | 0.485650% | 0.140996% |
| 平均J−1 | 0.00285803% | 0.00285827% |
| 构造腔面积变化（失败态诊断值） | +20.10718% | +20.12104% |
| 含超限点的单元：心内膜/ECM/心肌 | 30/0/39 | 31/0/35 |

腔响应绝对差0.000138658（0.0138658个百分点）、相对差0.0689117%，通过原跨网格面积门。
局部J峰值却增加66.17%，仍超过原1%门，因此不能把面积一致或平均J接近1当作资格通过。
超限体积分数由积分权重估计，不是精确几何体积或生物学样本统计；单元变小后超限单元数不能直接当面积比较。

M1非零载10次Newton更新，残量1.34e-14；独立自由力3.28e-14、弱压力残量3.83e-17。
J范围0.924236至1.111525，全为正；F/J/应力重建、反力、随动压力虚功及其他逐态门通过。
点值混合约束残差max\|J−1−p_m/kappa\|=0.111347，而max\|p_m/kappa\|=0.000734139；
小的离散弱残量不代表点值体积精度已解决。M0的原failed保留，不改写为通过。

## 热点位置与解释边界

M0最大点(0.03772,-0.73039)L距外边界0.001579L；M1最大点(1.07919,0.79779)L距外边界0.001177L。
两者均在心肌标签层，距固定点超过1L。热点位置变化，且局部峰值与超限区域占比走势相反。
这不支持“只需继续均匀加密即可修好”的结论；仍需区分非光滑边界局部效应与体积约束离散。
以上是已保存态的定位，不是根因证明，也不证明FEniCSx或P2/P1方法整体不适用。

## 交付与下一步

375个父文件、50个无关既有改动和正式调用原始文件保持；73测试及21子测试通过。
结构、细网格应力、共享色标粗细局部J图及真实两帧GIF通过Notebook、样式与目检，600dpi PNG/SVG冻结。
大文件位于已批准PRL-results，不进入GitHub；小型索引包含最终manifest哈希。
见[图件/动图/Notebook](../../PRL-results/ventricle_fem/f6s1q_fine_diagnostic_v01_20260917/index.html)、
[独立核验](../../PRL-results/ventricle_fem/f6s1q_fine_diagnostic_v01_20260917/verification.json)、
[交付审计](evidence/f6s1q_fine_diagnostic_v01/delivery.json)。

唯一下一步：制定“边界拐角与局部体积约束离散分离”的最小对照修复合同，先讨论几何允许误差及离散选择，
获准后执行；不直接放宽1%门、不盲目再加密、不开启主动或完整心动周期。当前授权已完成。
本地main阶段提交，不推送；无删除/迁移。figure_runtime为本阶段绘图缓存，另列候选后才能清理。
