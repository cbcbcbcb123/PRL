---
architecture_id: ARCH-PRL-HYBRID-V14
status: frozen_x1_k_failed_spatial_refinement
frozen_at: 2026-08-03
inherits_interface: ARCH-PRL-HYBRID-V13
acceptance_contract: CONTRACT-PRL-HYBRID-X1-K-V01
acceptance_contract_commit: 1241d80
cell_engine_commit: 2d4b2183f5966c2afe3f4234471e727fe5f9e68d
governed_by: CONSTRAINT-PRL-EXTERNAL-SCIENTIFIC-REVIEW-V01
---

# PRL 自有长期混合架构 v14：X1-K 失败冻结

X1-K 按预先提交的固定合同执行，并在 S1 空间 refinement 硬门禁失败后停止。本版本冻结已经获得的部分证据与失败状态，不把 T1 时间 refinement 的通过外推为完整短轨迹通过，也不进入 remesh-on、接触或故障持久化后续 case。

## X1-J 加固接口

X1-J v01 历史包未修改。新接口在其上追加：

- split→merge cycle gate 的最大 rebind 误差判据；
- `cumulative_absolute_inter_event_stored_energy_change`；
- `maximum_absolute_inter_event_stored_energy_change`；
- signed inter-event sum、absolute sum 和 max-per-event 三种语义分别返回，禁止以 `abs(signed sum)` 证明无抵消。

真实 split→merge 的初始主动储能高于 `1.0e-2`，最终漂移、累计绝对算法缺陷、纤维和 rebind 均通过 `1.0e-12` 量级的冻结门禁。构造的 interleaved case 中 signed sum 发生抵消，而 absolute/max 指标正确拒绝“无事件间漂移”结论。

## 固定拓扑主动短轨迹

新增公共 `short_trajectory` 接口，使用显式 barycentric-dual-area damping，记录逐步轴长、收缩、面积比、体积比、面积加权表面质心、主动储能、控制功、黏性耗散、真实步间能量残差、定向、三角质量、最小面积比、独立几何/cache 残差和状态 hash。

T1 的 `dt/dt2/dt4` 三层在共同 `T=0.02` 通过：状态及五个客观 QoI 的观测阶均约为 1；累计正能量残差随 dt 对半近似减半。coverage 仅为 `active_contraction_only`，没有执行被动、接触、ECM 或流体。

## S1 空间 refinement 失败

S1 使用几何等价单位立方体表面，网格为 `8/12`、`26/48`、`98/192` vertices/triangles，连续参数、每面积阻尼、`dt=1e-4` 和 `T=0.002` 全部保持不变。结果为：

| QoI | coarse | base | fine | coarse-base | base-fine | observed order | status |
|---|---:|---:|---:|---:|---:|---:|---|
| area ratio | `0.99997800000799975` | `0.99996200025192739` | `0.99993000203174709` | `1.599975607236015e-5` | `3.1998220180295966e-5` | `-0.99994175072770464` | failed |
| volume ratio | `0.99996800016500043` | `0.99995999989480966` | `0.99995599833048354` | `8.0002701907666562e-6` | `4.0015643261170908e-6` | `0.9994846234517949` | passed |
| registered surface-energy ratio | 与 area ratio 相同 | 与 area ratio 相同 | 与 area ratio 相同 | 同 area | 同 area | `-0.99994175072770464` | failed |

面积与注册表面能的相邻网格差随 refinement 约增大两倍，违反合同要求的单调自收敛和 `p>=0.25`。这不是 NaN、cache、网格质量或能量 coverage 残差造成：最小三角质量为 `0.86599768533958354`，最大 cache 残差为 `2.4825341532472731e-16`，三层归一化正能量残差最大仅 `1.5200192547477984e-10`，这些判据均通过。

## 失败机理边界

从代码与数据可推断，当前失败与立方体尖锐边上的表面张力离散有关：面积梯度力集中在一维棱边，均匀 midpoint refinement 时边上节点力按约 `h` 缩放，而 barycentric dual area 阻尼按约 `h^2` 缩放，因此棱边速度可按约 `1/h` 增长。观测到的 area/energy 负一阶行为与该缩放一致。该解释是诊断性推断，不等于已完成替代离散的证明。

受控 fork 本阶段未修改。若要修复，需要新的科学授权选择：改变非光滑 cube case、为棱边奇异力引入匹配控制度量，或重构被动表面能/阻尼离散；不得通过放宽现有阈值或忽略 area/energy QoI 恢复通过状态。

## 停止边界与 claim guard

按合同，R1 remesh-on、C1 contact 和 F1 failure persistence 未执行，X1-K 状态为 `failed_spatial_refinement_nonconvergent_area_energy`。允许的结论仅为“T1 冻结主动 case 的短时一阶时间自收敛通过，S1 冻结表面张力 cube case 的面积/注册能量空间自收敛失败”。不得宣称完整 X1-K 通过、长期稳定、生理有效、完整 cell–ECM/FSI 或 EFE 机制成立。Route H Gate A v01 继续保持 `failed_invalid_numerics`。
