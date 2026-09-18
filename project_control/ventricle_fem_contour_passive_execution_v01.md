---
document_id: PRL-FEM-CONTOUR-PASSIVE-EXECUTION-V01
status: failed
delivery_status: passed
controlled_stop: passed
date: 2026-09-18
contract: project_control/ventricle_fem_contour_passive_contract_v01.md
result: E:/Temp-Projects/PRL-results/ventricle_fem/f6s1s8_contour_passive_v01_20260918
---

# F6-S1-S8：中间压力通过，0.08局部体积超限后停止

按用户“继续”及[六态上限合同](ventricle_fem_contour_passive_contract_v01.md)，
从已接受M0/M1的0.02态续算，不重算零载/0.02、圆环或网格。
一次57.462秒、1CPU/8GiB/禁网/0GPU容器；M0新增3态，2态通过、1态failed。
M1的0.04/0.06/0.08全部not_run。首失败停止、隔离和证据交付passed；完整被动资格failed。

## 模型和数值结果

同一3541/14164三角形、P2位移/DG2压力、六阶积分、有限变形平面应变NH，mu=1/kappa=1000。
内壁随动压力、外壁自由、A固定ux/uy与B固定uy；Ta=0，三层同一未标定被动材料。
只有72 hpf Fish 4外轮廓来自图像，内腔和三层界面为构造。
重启逐项核验全部混合DOF映射相同；生产Ring和独立力学核心均与父包一致。

| M0压力p/mu | 来源 | 腔面积变化 | max\|J−1\| | 原1%局部门 |
|---|---|---:|---:|---|
| 0 | 复用 | 0% | 0% | passed |
| 0.02 | 复用 | +20.056188% | 0.323434% | passed |
| 0.04 | 新算 | +32.807874% | 0.587402% | passed |
| 0.06 | 新算 | +48.055961% | 0.920140% | passed |
| 0.08 | 新算 | +68.266151% | 1.173743% | failed |

M1只有原已通过0/0.02：0.02腔面积+20.105502%、max|J−1|=0.358062%。
不得把M0的0.04/0.06通过表述为这两个压力的粗细资格通过。
0.08：SNES reason=2、5次更新、残量1.748e-14，真实MUMPS INFOG=0/ICNTL(14)=100；
独立自由力4.281e-14、弱压力9.211e-17、DG2点态约束最大差2.487e-13，均passed。
只有原局部体积门失败；Jmin=0.9882625712、Jmax=1.0082887427、平均J=1.0001524631。
最终48项汇总检查中44通过；4个失败项分别为M0的0.08物理门、M1序列未完、6新态未全接受、全压力粗细比较未完。
新状态共17个真实Newton向量全部保存；没有伪造中间帧或生理时间。

## 已保存状态的诊断边界

独立重建定位：3541单元中1个单元（1369）的2个积分点超1%；
峰值在构造心肌层，参考位置(1.068405,0.763228)L，距外边界约0.03261L，
距A/B固定点约2.13463/1.71623L，不是固定点邻域。
峰值混合压力p_m/mu=-11.73743，满足J−1=p_m/kappa；因此这次不是此前CG1未充分表示局部约束，
也不是MUMPS或Newton未收敛。当前已收敛有限bulk离散解的局部体积响应越过原门。
几何凹口应力集中、网格依赖和有限bulk响应的因果贡献尚未区分，不擅自归因或调大kappa。
超限点对应参考积分权重比例3.2142e-5，仅为采样估计，不能据此忽略最坏点或改变原1%门。

全部7个保存态的二次边界每边24/48段采样均未见自交、腔室仍被包含；
0.08最小采样壁间距约0.0526106L。它不是精确曲线或全局单射证明。
这不是实验校准、心动/三维/FSI/生长验证；这些均not_run。

## 图件、交付与完整性

两套执行过的Notebook、600dpi PNG/可编辑SVG完成CB样式与目检，实际1倍形变。
结构/失败态应力与局部J、五个真实M0载荷态及原门曲线均保留；M1未运行点不补造。
使用cb-paper-figure-workflow、cb-plot-unified-style；失败定位按cb-diagnose只读保存态复核，无科学修复/重跑。

交付比较首次failed：已有有限差分虚功舍入余量没有传播到由其计算的pressure_virtual_work_error。
三个派生误差跨平台差1.35e-12至3.55e-12。保留原失败与1failed/9passed的回归红例。
仅交付比较器先核验两个误差都确实等于abs(work−difference_work)/max(1,abs(work))，
再传播已有机器精度/压力/面积/差分步长余量；其他字段原rtol/atol、所有分类精确比较和物理门均不变。
修复后132tests+21subtests passed，独立报告比较passed；0FEM重算。原科学failed没有被改写。

1358父/祖先文件、94正式调用文件、38输入/源码副本及50项无关修改哈希保持。
结果包160文件、115,310,640 bytes（约109.97MiB），根manifest直接覆盖158文件，
父manifest另由已入清单的input_identities.json覆盖（159个数据文件全部有哈希链）；根manifest SHA-256：
`58a708f93a3b3c0f290912054a19a00c3b17a9ec94aa2008247322416d6b3c21`。
冻结时仓库2,036,847,473 bytes，低于3GiB；外部结果不进入GitHub。无安装/拉取/Docker修复/删除/推送。
临时目录E:\Temp-Projects\PRL\tmp\f6s1s8_checks及结果figure_runtime均有所有权说明，未获删除授权而保留。

[结构与真实压力态图件](../../PRL-results/ventricle_fem/f6s1s8_contour_passive_v01_20260918/index.html) ·
[独立复核](../../PRL-results/ventricle_fem/f6s1s8_contour_passive_v01_20260918/post_verification.json) ·
[局部超限定位](../../PRL-results/ventricle_fem/f6s1s8_contour_passive_v01_20260918/boundary_observations.json) ·
[原失败](../../PRL-results/ventricle_fem/f6s1s8_contour_passive_v01_20260918/failure.json)。

只读复核命令：设置PYTHONPATH=src后，
`python -B -X utf8 -m prl verify fem-fenicsx-contour-pressure --complete-passive`。
返回failed是保留的科学裁决；run为create-only，不允许原地重跑。

## 唯一下一步提议（尚未授权）

建议保留高压失败并暂停追高压，改在**两网格已通过的p/mu=0.02**基线上做心肌主动张力递增对照，
研究主动缩腔如何抵消压力扩张，保持原材料/1%门、1CPU/0GPU、首失败停止。
该提议是把“完整高压序列通过再主动”改为“已通过载荷范围内研究主动”，必须用户明确确认后另立有界合同。
本轮没有执行主动或自动批准该路线改变；0.08失败仍是当前适用性边界，不能称已解决。
