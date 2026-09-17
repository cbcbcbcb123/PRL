---
document_id: PRL-FEM-FENICSX-RING-ACTIVE-EXECUTION-V01
status: failed
executed_at: 2026-09-17
G0_runtime: passed
G1_passive_saved_state_qualification: passed
G2_active: not_run
contract: project_control/ventricle_fem_fenicsx_ring_active_contract_v01.md
result: results/ventricle_fem/f6s0_fenicsx_ring_active_v01_20260917
scientific_invocations: 1
completed_equilibria: 10
scientific_retries: 0
---

# F6-S0：被动圆环资格通过，主动工况尚未运行

## 科学裁决

本机已有FEniCSx镜像的G0导入、JIT和微型装配通过。DOLFINx `0.11.0.post0`、
Basix/FFCx `0.11.0`、UFL `2026.1.0`、PETSc `3.25.1`均已实测，容器为单CPU、
8 GiB、禁网、只读根和只读源码、0 GPU。已知单位面积和仿射场能量误差约1e-14。

唯一科学调用完成两档网格各五个被动压力平衡态。独立保存状态复核的42项汇总门全部passed；
其中每态另外检查非线性收敛、独立力/压力残量、F/J/应力重算、压力虚功及规范反力。

| 指标，最高压力 p/mu=0.08 | M0：896三角形 | M1：3584三角形 |
|---|---:|---:|
| 腔面积增量 | 22.460105% | 22.460227% |
| 相对不可压解析参照误差 | 0.072005% | 0.072548% |
| 最大局部体积偏差 max\|J-1\| | 0.059238% | 0.024258% |
| 独立自由力残量 | 1.65e-13 | 1.17e-13 |
| 位移相对解析L2误差 | 0.061842% | 0.060555% |

两网格末态腔响应相差0.000121920个百分点；细网格局部体积偏差远低于原1%门。
解析式是不可压极限；当前kappa=1000，因此不能将约0.07%的差全归为网格误差，
也不宣称所有误差都随网格严格单调下降。

## 当前模型含义

这是二维P2位移/P1混合压力三角形、三维平面应变本构的理想圆环。
内腔半径20/27、两个层界21/27与22/27、外半径1；三层目前只提供区域标签，
被动材料均为未标定的等容Neo-Hookean mu=1、kappa=1000。
内壁施加当前构形随动压力，外壁自由；外壁(1,0)固定两分量、(-1,0)固定uy，
仅去除刚体模态，其规范反力约1e-16。没有主动张力、血流、真实解剖或生理时间。

本次证明FEniCSx后端在这一被动基准上通过资格。不能据此称F5真实轮廓的局部J失败已修复，
不能当作斑马鱼心动或实验验证。

## 原调用失败与零重算修复

10个平衡态完整保存后，独立验证入口出现`IndexError`：DOLFINx 0.11的collapse映射带有
单行维度，压力被无损保存为`(1, Np)`，旧读取器假设`(Np,)`。
这是字段读取错误；没有丢失压力自由度。程序按冻结门停止，G2没有启动。
原`failure.json`、`execution.json`、stdout/stderr及其清单完整保留，不重新标成成功调用。

修复范围：读取器只接受精确的`(Np,)`或`(1,Np)`并归一化；后续adapter导出显式展平映射。
原执行时adapter和验证器源码另存`sources_at_execution/`，原始source hashes保持。
修复后只对十个原状态独立复算并绘图，0新平衡求解，0自动科学重跑。
全部原始raw和原调用控制记录已相对`formal_invocation_manifest.json`复核哈希一致。

## 工程与交付

- 35个针对性测试和21个子测试通过，包括pressure单行导出回归、P2多项式重现、
  刚转客观性、主动应力定位、闭合压力虚功及FEM-only CLI边界。
- 新增FEniCSx源码的导入边界通过；宿主不导入DOLFINx。
- 全仓旧quick-suite静态扫描仍报告`measured_contour.py`既有图像依赖/绝对数据路径问题；
  本次未扩大修改，也不宣称全仓quick-suite通过。
- 结构图、面积/体积资格图、五状态应力图的600 dpi PNG及可编辑SVG通过CB样式验收和目检；
  预览GIF只显示原始五态，统一色标、1倍形变，不补造中间求解态。
- 绘图首次发现下方图注与轴标题间距不足，增大画布下边距后重绘；不改变原始数组。
- 原F5包哈希不变；无DCM/GPU、拉取、安装、删除、提交或推送。

## 下一步

G1科学资格已通过，但原限定的一次正式调用已结束。剩余G2只需补两网格各8个新状态：
纯主动及压力+主动各4个非零延拓态，共16态；零载与被动压力态沿用本次证据，不重算。
后续有界补算草案见[未运行主动工况续算合同](ventricle_fem_fenicsx_active_completion_contract_v01.md)。

[结果页](../results/ventricle_fem/f6s0_fenicsx_ring_active_v01_20260917/index.html) ·
[独立G1复核](../results/ventricle_fem/f6s0_fenicsx_ring_active_v01_20260917/g1_verification.json) ·
[原调用失败](../results/ventricle_fem/f6s0_fenicsx_ring_active_v01_20260917/failure.json)

实现接口依据：[DOLFINx 0.11 PETSc/SNES API](https://docs.fenicsproject.org/dolfinx/v0.11.0.post0/python/generated/dolfinx.fem.petsc.html)，
[DOLFINx 0.11 mesh API](https://docs.fenicsproject.org/dolfinx/v0.11.0.post0/python/generated/dolfinx.mesh.html)。
