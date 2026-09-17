---
document_id: PRL-FEM-CURVED-PRESSURE-EXECUTION-V01
status: passed
executed_at: 2026-09-17
contract: project_control/ventricle_fem_curved_pressure_contract_v01.md
result: results/ventricle_fem/f4_curved_pressure_v01_20260917
scientific_invocations: 1
new_scientific_solves: 10
automatic_retries: 0
---

# F4｜曲线壁段与随动压力通过

按[冻结合同](ventricle_fem_curved_pressure_contract_v01.md)一次运行完成8/24单元的两档网格，各保存五个压力平衡态。求解部分30.633秒，含验证和图件的worker为50.099秒，公共CLI退出0。科学与图件均直接passed，无科学重试或后处理补跑。

## 实现和场景

在同一Q2/Q1内核新增显式等参分支：每单元每Gauss参考Jacobian、逆映射梯度与正det权重；旧affine分支保持。新增当前Q2表面面积/法向的压力结点力和解析一致切线；残差减外力，切线减其导数，不加入参考形态能量或额外弹簧。材料源未改，Newton残差/迭代/回溯门不变。精确可逆核心补丁在本包source_patch。

四分之一圆柱壁段A=1、B=1.25、H=0.5；theta=0固定uy、theta=pi/2固定ux，所有uz=0，其他自由；内腔p=0/0.02/0.04/0.06/0.08，外壁无牵引。NH mu=1、kappa=1000，无主动收缩或端盖压力。是3D实体的平面应变工程检查，不是自由三维心室。

## 核心结果

| 指标 | coarse | fine |
|---|---:|---:|
| 最高压力内壁参考面积加权径向位移 | 0.144521854 | 0.144525272 |
| 相对不可压圆柱解析位移的差 | 0.083700% | 0.086066% |
| 所有态最大局部 \|J−1\| | 0.044518% | 0.029733% |
| 参考几何体积相对误差 | 0.004932% | 0.0003093% |

解析极限峰值位移为0.144400991；两网格末态位移相对差0.00236493%，通过合同5%门。最大独立自由力残差4.1426e-12、弱压力残差1.2783e-13；保存Newton最大1.8898e-12。全场重算最大F/J/Green误差约3.33e-15，总Cauchy误差2.65e-11。

[独立八门](../results/ventricle_fem/f4_curved_pressure_v01_20260917/verification.json)均passed。验证器独立重建Q2/Q1、参考/当前Jacobian、能量差分应力、当前压力表面力、反力、边界和弱压力；保存的零残差或expected_status不能作为判断真值。正式运行后save=False复算与保存报告逐值一致。

不可压解析参照不是有限kappa=1000的精确解。fine相对该参照的差略大于coarse，因此不称为“细化后所有误差单调下降”；当前差混合了可压缩性、几何插值和FE离散影响。两档近似一致只支持本次圆柱/载荷范围，不证明任意心室网格已收敛。局部J接近1也不等于严格点态不可压。

## 图件、回归与证据

228项开发测试及36个子测试通过（全套221项与新增绘图转换7项；末次运行器/绘图17项复核通过）。采用cb-governed-project-supervisor的Direct+Check流程，不另建审批链；绘图按cb-plot-unified-style输出三套600dpi PNG/可编辑SVG并通过外部样式验证。主代理已目检结构、力学对照和五状态图：实际Q2曲线空间插值、1倍位移、固定色标，保留轴向约束标注；压力状态不是生理时间。

原始全部十个u/p、Gauss场、当前外力/反力、初值、Newton记录已保存，图件显示的是含sigma_zz的三维总Cauchy von Mises应力。energy是内部材料密度，不含开放面压力功，不用它宣称总势下降。见[完整图页](../results/ventricle_fem/f4_curved_pressure_v01_20260917/index.html)。

父F3-B62项及F3-C38项，连同两个冻结manifest，运行前后逐项bytes/SHA不变；不重复旧13工况、不覆盖历史失败。本包original_invocation_manifest记录原调用产物，最终manifest包含补丁和交付审计。32 MiB阶段预算及3 GiB项目门通过；单线程CPU、0 GPU、0 DCM、0自动重试。没有删除、安装、提交、推送或项目外写入。

## 唯一下一步

将已检查的有限变形曲线/压力接口接回既有真实斑马鱼外轮廓，明确构造内腔、壁厚/层界与面外约束，先验证被动加载再恢复方向性主动收缩。新阶段未运行，不重做块梁或圆柱矩阵。真实自由三维心室、生理周期、材料标定、血流、生长及ECM反馈仍not_run。
