---
document_id: PRL-VENTRICLE-CONTACT-PERFORMANCE-AND-EXTENDED-EQUILIBRIUM-EXECUTION-V01
status: completed
executed_at: 2026-09-15
contract: project_control/ventricle_contact_performance_and_extended_equilibrium_contract_v01.md
q_status: passed
equilibrium_status: failed_equilibrium
gpu: false
automatic_retries: 0
---

# 接触性能与扩展双胞平衡资格执行记录 v01

## 结论

正式Q为`passed`，扩展双胞E为有效负结果`failed_equilibrium`。接触候选在保持逐节点力、接触能、支撑面积和21项保留回归一致的前提下，将16胞静态接触组装中位时间从12.0441 s降至4.7788 s（2.5203×）；2胞candidate/baseline比为0.9432，没有小系统性能回退。

END/SIDE × `dt_max=0.02/0.01`四条轨迹均从冻结输入重新积分至算法坐标20，未自动重跑。四条均通过正间距、独立穿透/自交见证、体积、网格角、相邻面、工作残差、固定拓扑和完整状态门；粗细步长末态位移相对误差为END 0.01806%、SIDE 0.01850%。但末态最大自由力仍为0.01775–0.02133，超过冻结的0.001平衡门17.7–21.3倍，因此不得称为静态平衡。

## 模型与边界

- END端对端与SIDE侧邻各两个闭合三维心肌细胞，每胞194节点、384面；四条轨迹全部自由，`fixed=false`。
- 内力来自皮质、面积/体积约束、恒定方向骨架预应力、黏附和正间隙屏障；没有参考形状膜能、周期收缩或外部牵引。
- 没有心内膜、ECM、腔压或端部夹持。图中`pressure`是体积约束的胞内压力，不是心室腔压。
- 横轴是算法松弛坐标，不是秒、心动周期或生理时间。

## Q：正式三重复性能与等价性

| 细胞数 | baseline中位数/s | candidate中位数/s | 结果 |
|---:|---:|---:|---|
| 2 | 0.205944 | 0.194246 | candidate/baseline=0.943，passed |
| 4 | 1.865812 | 1.678888 | 等价，passed |
| 16 | 12.044062 | 4.778800 | 2.520×，passed |

9组baseline/candidate配对的active sample完全一致，接触能、支撑面积和逐节点力最大相对误差均为0。候选合力归一残差最大`1.72e-14`，合矩归一残差最大`2.23e-15`；21/21保留接触回归通过。Q只证明本机单线程静态组装资格，不是16胞动力学。

## E：扩展双胞矩阵

| 工况 | 末态自由力 | 最小间距 | 最大体积误差 | 最小角 | 最大工作残差 | 安全 |
|---|---:|---:|---:|---:|---:|---|
| END_DT0.02 | 0.0177488 | 0.0493965 | 0.3340% | 22.0488° | 5.45e-16 | passed |
| END_DT0.01 | 0.0177700 | 0.0494090 | 0.3340% | 22.0528° | 5.54e-16 | passed |
| SIDE_DT0.02 | 0.0213059 | 0.0545276 | 0.3387% | 22.5986° | 5.45e-16 | passed |
| SIDE_DT0.01 | 0.0213268 | 0.0545314 | 0.3387% | 22.6218° | 4.66e-16 | passed |

每条保存算法坐标0/5/10/15/20五个完整网格；20个事件状态的胞间穿透、包含节点和自交见证均为0。四进程总墙钟1247.58 s，求解器输出11,111,536 bytes；完整结果包在绘图后为128文件、13,393,641 bytes，低于256 MiB阶段预算。

## 图像、哈希与视觉验收

- [Q性能图](../results/ventricle_z1/z1_myo_contact_performance_equilibrium_v01_20260915/figures/performance_gate.png)
- [实际2/4/16胞结构](../results/ventricle_z1/z1_myo_contact_performance_equilibrium_v01_20260915/figures/model_structure.png)
- [残力与平衡门](../results/ventricle_z1/z1_myo_contact_performance_equilibrium_v01_20260915/figures/residual_vs_coordinate.png)
- [间距、体积与网格角](../results/ventricle_z1/z1_myo_contact_performance_equilibrium_v01_20260915/figures/gap_and_mesh_quality.png)
- [曲率、压力与接触牵引](../results/ventricle_z1/z1_myo_contact_performance_equilibrium_v01_20260915/figures/curvature_pressure_contact_traction.png)
- [END五状态动图](../results/ventricle_z1/z1_myo_contact_performance_equilibrium_v01_20260915/figures/end_five_states.gif)；[SIDE五状态动图](../results/ventricle_z1/z1_myo_contact_performance_equilibrium_v01_20260915/figures/side_five_states.gif)

PNG/SVG和两份5帧GIF已视觉检查；标注、坐标和门线可读，内容与裁决一致。压力几乎为胞内常值，颜色条的偏移标记反映很小的胞内数值差，不应解读为腔压梯度。机器摘要与结果哈希见`evidence/ventricle_contact_performance_equilibrium_v01/execution_summary_v01.json`。

## 下一步边界

下一步不是直接进入4×4、心内膜或ECM，而是先利用现有逐步账本分析残力是否继续指数衰减或形成平台，并分解末态骨架、皮质/面积体积和接触分量，定位维持非零残力的机制。若只是尚未收敛，再另行冻结有停止预测的延长合同；若存在持续预应力不相容，则先修订物理机制。当前授权已消费，不自动继续运行。
