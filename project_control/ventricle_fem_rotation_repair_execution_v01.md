---
document_id: PRL-FEM-ROTATION-REPAIR-EXECUTION-V01
status: passed
executed_at: 2026-09-17
contract: project_control/ventricle_fem_rotation_repair_contract_v01.md
result: results/ventricle_fem/f3c_rotation_repair_v01_20260917
scientific_invocations: 1
new_scientific_solves: 5
automatic_scientific_retries: 0
---

# F3-C｜初值修复和刚转补充资格

## 科学裁决

按[补充合同](ventricle_fem_rotation_repair_contract_v01.md)完成一次有界单线程CPU调用：四个原缺失角度15°/30°/45°/60°，加一次60°固定内部扰动恢复，总计五次新求解，求解部分3.376秒。0°状态及history逐字段沿用父包，不重算已通过的13个拉伸/主动/弯曲工况。

[独立验证](../results/ventricle_fem/f3c_rotation_repair_v01_20260917/verification.json)全部passed：父包完整性、刚转、0°来源、history、预测及扰动恢复。结合原被哈希锁定的13工况和材料点/网格/体积模量子门，**有限变形工程块梁的组合资格passed**。原F3-B包及其failed状态保持不动，新补充不是改写历史。

这不是三维真实心室、外部Land完整基准或实验吻合。旧F3-A真实二维轮廓的数值失败也未因本次通过而被改写。

## 修复内容与未改变项

只在`src/prl/fem/mixed_hex.py`增加显式调用的`lift_dirichlet_initial`。对规定边界位移的增量，逐分量用参考Q2 Laplace延拓到内部，检查预测Gauss点J>0，再送给原Newton。它是几何初值，不是新物理能量/弹簧；125个位移节点中98个边界节点固定转动，27个内部节点仍自由。

该6137-byte插入块在内存移除后严格恢复原文件SHA-256，证明`solve`、`assemble`及既有其他字节未改。原材料、载荷、压力初值和`1e-9 / 30 / 16`门不变。见[精确补丁与恢复证明](../results/ventricle_fem/f3c_rotation_repair_v01_20260917/source_patch/core_change_v01.json)。旧运行器不覆盖；新补充运行器显式使用lifting。

## 定量结果

| 检查 | 结果 | 判断 |
|---|---:|---|
| 五角度最大位移偏离解析刚转 | 1.3323e-15 | 低于1e-10 |
| 最大Green应变 | 4.7740e-15 | 低于1e-10 |
| 最大总Cauchy应力 | 7.9110e-15 | 低于2e-7 |
| 最大|J−1| | 4.8850e-15 | 低于1e-10 |
| 固定扰动初始最大位移误差 | 0.002 | 非平凡，边界不扰动 |
| 扰动初始最小J | 0.992334 | 正J |
| 扰动恢复接受的Newton更新 | 2 | 不是只填入解析解 |
| Newton残差 | 0.006522→2.419e-5→3.333e-11 | 严格下降并低于1e-9 |
| 恢复后最大位移误差 | 2.5584e-12 | 低于1e-10 |
| 恢复后最大Green应变 | 1.1107e-11 | 低于1e-10 |
| 恢复后最大独立Cauchy应力 | 9.7450e-11 | 低于2e-7 |

四次原初值预测接近精确仿射刚转，初始残差即足够小；因此它们主要验证边界提升/客观性，不能单独声称Newton恢复能力。固定非仿射扰动的两次接受更新才提供恢复证据。

压力和位移使用合同运行前明确的分变量门：恢复压力与未扰动60°状态最大差1.2952e-10，低于压力/应力2e-7；位移差2.5588e-12，低于位移1e-10。不能把有不同物理含义的整个混合向量误差套用同一位移门。

## 运行与后处理记录

136项针对性测试与34个subtests通过；回归先复现原0→15°初猜翻转再验证修复。另一个开发用随机扰动仅满足默认残差、Green约1.593e-10，不满足严格1e-10刚转门，已保留该限度，未用它宣称任意初值都严格通过。正式资格使用运行前固定的60°sin-bubble扰动，不扫描/挑选参数。

启动前和科学计算后验证父manifest的62文件不变。16 MiB阶段预算、64 MiB保全余量、3 GiB项目门、300秒上限和科学任务锁生效；超预算先判定再发布状态，失败快照的二次写错误不会掩盖原失败。模拟写失败回归是工程检查，不是断电/重启可恢复性证明。

原调用的科学计算与独立验证passed，随后因对数轴越界刻度和次刻度格式未通过绘图验收而退出1。`failure.json`、`progress.json`及`original_invocation_manifest_v01.json`保留此事实。允许的后续修改仅针对绘图格式，重新读取保存结果作图，绝不重新求解；最终交付状态另记于`postrender_execution_v01.json`。图件通过不能替代科学判断。

使用`cb-diagnose`形成原失败路径回归并分离初值/求解/后处理问题；图件按`cb-plot-unified-style`使用真实1倍坐标、真实角度状态和未放大舍入误差的固定色标。见[结构、刚转与恢复结果图](../results/ventricle_fem/f3c_rotation_repair_v01_20260917/index.html)。角度不是生理时间，刚体旋转不是心肌收缩。

## 下一步边界

只补齐了规则三维工程块梁的有限变形资格。下一步是把单元推广到曲线心壁几何并验证腔面随动压力，再把有限变形主动模型放回已有真实轮廓；不得将目前仅适用于结构化直方块的Jacobian实现直接用于曲线网格。材料标定、生理周期、真实三维心室、血流、生长及ECM反馈仍not_run。

本轮0 GPU、0 DCM、0科学自动重试，无删除、软件安装、Git提交/推送或项目外新建文件。
