---
document_id: PRL-FEM-FENICSX-RETAINED-PASSIVE-EXECUTION-V01
status: failed
contract: project_control/ventricle_fem_fenicsx_retained_passive_contract_v01.md
result: results/ventricle_fem/f6s1p_retained_passive_v01_20260917
geometry_gate: passed
storage_admission: passed
passive_mechanics: failed
active_mechanics: not_run
saved_equilibria: 2
accepted_equilibria: 1
---

# F6-S1-P：预算已解除，非零压力态局部体积门失败

本轮落实用户800 MiB阶段输出预算决定。项目默认新阶段预算与本次运行均为800 MiB，
停止空间另64 MiB，3 GiB项目硬上限不变；旧合同/原始证据不改写。
复用candidate_0的冻结网格，0次Gmsh调用。粗/细3541/14164单元，几何与存储准入通过。

一次科学容器25.932秒，1 CPU、8 GiB、0 GPU、禁网、固定已有镜像，Docker服务端只读检查通过。
没有重启或修复Docker、没有安装/拉取。两次平衡求解均保存；零载验证通过，p/mu=0.02失败。
遵守首失败停止，后续粗网格三态及细网格五态均not_run，无自动重试。

## 实际结果及区别

| 检查 | p/mu=0.02实际结果 | 裁决 |
|---|---:|---|
| SNES收敛 | 10次更新；残量6.81e-15 | passed |
| 独立自由力范数 | 1.69e-14 | passed |
| 混合压力弱残量 | 3.22e-17 | passed |
| J正性 | 0.933579至1.067117 | passed，无积分点翻转 |
| 最大局部体积偏差 | 6.71167%，要求≤1% | failed |
| 参考体积加权平均J−1 | 0.002858% | 不能替代局部门 |
| 腔面积变化 | +20.10718% | 失败态诊断值，不是接受的响应 |

F/J重建最大误差约2.98e-13、应力重建3.48e-13、压力虚功误差5.15e-13，
作用力、规范反力、零主动应力及其余逐态门均通过。不是简单的求解未收敛或符号错误证据。
位移最大值0.408399 L，确实发生明显大变形；不能因变形可见就接受其物理结果。

## 保存数据的定位，不重跑

69个单元至少一个积分点超过1%：构造心内膜30/840、ECM 0/861、心肌39/1840。
最差点在心肌区局部弯折附近，参考坐标(0.0377192,-0.730390)L。
积分权重估计约0.48565%的参考体积超过1%；这是积分点统计，不是精确连续域分割面积。

混合项要求弱形式满足J−1−p_m/kappa=0，但当前离散解的点值残差最大0.0667932，
而max|p_m/kappa|仅0.000601079。这里p_m是混合压力未知量，不能与加载腔压力混淆。
因此，小弱残量及接近1的平均J并不保证逐点不可压精度。这支持优先检查空间离散/局部
约束分辨率，不支持直接降低体积模量或放宽1%门。是否能用细网格改善尚未验证。

## 交付与边界

308个父文件保持SHA-256，原F6-S1网格失败、F6-S1-M预算阻断及更早失败包不变。
相关测试54项与21子测试passed，开发测试通过不能替代失败的科学门。
图件遵循可复算Notebook流程，数据物理副本、辅助代码/样式、600dpi PNG与SVG均保留。
四面板包含结构、1倍变形应力、逐单元最大J偏差及两态面积；两帧GIF无时间插值，
明确零载passed、非零载failed，不补造五态或舒张回程，不称生理心动。

[图件和两态动图](../results/ventricle_fem/f6s1p_retained_passive_v01_20260917/index.html) ·
[完整独立核验](../results/ventricle_fem/f6s1p_retained_passive_v01_20260917/verification.json) ·
[局部体积定位](../results/ventricle_fem/f6s1p_retained_passive_v01_20260917/local_volume_diagnosis.json) ·
[交付审计](../results/ventricle_fem/f6s1p_retained_passive_v01_20260917/delivery_audit.json)。

## 唯一下一步（待确认）

只运行尚未求解的M1细网格p/mu=0及0.02两个状态，保持物理和1%门，
与本次M0保全结果比较。不是重跑粗网格，也不是继续提高压力或开始主动收缩。
若局部偏差明显下降，才进一步讨论局部加密；若仍明显失败，再审查不可压离散方案。
本轮已在首失败处结束，不自动进入该诊断切片。

新建临时缓存位于E:\Temp-Projects\PRL\results\ventricle_fem\f6s1p_retained_passive_v01_20260917\figure_runtime。
仅保留为待批准清理候选，不自动删除，也未处理旧缓存。阶段本地提交main，不自动推送。
