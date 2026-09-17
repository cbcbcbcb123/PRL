---
document_id: PRL-FEM-MEASURED-CONTOUR-EXECUTION-V01
status: failed
completed_at: 2026-09-17
decision: project_control/ventricle_fem_only_measured_contour_decision_v01.md
contract: project_control/ventricle_fem_measured_contour_contract_v01.md
result: results/ventricle_fem/f2_measured_contour_v01_20260917
---

# F2｜真实外轮廓FEM已求解，数值资格未通过

## 路线和执行

用户明确要求本项目不再采用任何DCM，并在现有真实斑马鱼轮廓上移植上一版FEM。本次完成1次正式阶段调用、两级网格各41个状态，单线程CPU、0 GPU、0 DCM、0科学重跑。历史DCM文件保留，稳定CLI的8个历史DCM运行入口及内核诊断入口已拒绝执行；历史独立模块仅作证据，不声称已物理删除或全仓封锁。

命令：`python -B -X utf8 -m prl.runs.fem_measured_contour --workspace E:\Temp-Projects\PRL`。控制进程设置单线程环境与600秒上限，TIFF显式单解码线程；结果create-only。源码来源、配置、依赖版本、原始状态均在结果包内。FEM几何接口4项测试、CLI15项测试passed；旧全套含历史DCM检查，not_run。未删除、安装、提交或推送。

## 实测与假设

实测输入是已验收Zenodo包内Fish 4组织mask，最大占据XY切片z索引39，像素0.2071606 µm；非投影。取最大连通域时排除1个孤立像素，无内部孔洞需要填充。平滑后轮廓与mask的IoU=0.997773886、双向采样Hausdorff=0.531849 µm；独立扫描线及距离块重算通过。

G0/G1实际多边形与源mask的IoU分别0.9947805/0.9968074，采样Hausdorff为2.19268/0.811309 µm。合同对平滑轮廓设门、对离散多边形误差仅报告，未事后把G0误差伪装成通过2 µm门。

腔面、心内膜/ECM/心肌层界、局部切向、材料与负载均为假设。内部按旧F0比例同心缩放；中心[114.262908,148.725237] µm由轮廓内核最大边距几何规则确定，不是实测腔中心。这产生非均匀壁厚，尤其凹陷区较窄，不能称为真实分层解剖。

沿用二维平面应变P1小应变材料E=1/0.5/2.5、nu=0.3；心肌峰值3%切向主动本征应变，内外零牵引、无腔压/夹持，只去除刚体运动。41相位是负载延拓，不是生理时间；应力未标定，面内压力不是腔压。

## 数值结果与失败门

| 指标 | G0 | G1 | 裁决 |
|---|---:|---:|---|
| 节点/三角形 | 864/1,536 | 3,264/6,144 | 完成 |
| 构造腔面积峰值变化 | -3.59436% | -2.63239% | 收缩存在 |
| 外轮廓面积峰值变化 | -3.07947% | -2.51276% | 仅截面面积 |
| 最大绝对应变分量 | 0.054343 | 0.068936 | 两级均超过0.05 |
| 最小变形三角面积（归一化） | 1.89567e-4 | 3.85673e-5 | 正面积passed |
| 求解器后向残差 | 6.18e-17 | 1.16e-16 | passed |

G1最大位移3.00528 µm；最大应变分量位于构造ECM层，单元中心约[88.4897,149.8435] µm。独立场量重算最大绝对误差1.24e-14。G1三角质量`4sqrt(3)A/sum(edge^2)`最小0.08562、中位0.53372；此为追加只读诊断，不是新设门。

两级构造腔变化差0.00961968，即0.961968个百分点，超过0.002门。因此整体`failed`。这说明**该离散/本构试算尚未取得数值资格**，不等于FEM不能处理真实轮廓。几何离散、方向离散与分层质量可能共同影响响应，尚未分离贡献，不能把根因单独归给网格或材料。

`summary.json`继承的`peak_inner_long_span/peak_inner_short_span`字段实际为坐标x/y跨度，不是形状主轴；本报告未用它们解释长轴/短轴。

## 图件修复与来源审计

原流程在数值状态已完整保存后因绘图刻度超出可视范围触发风格检查失败，原`failure.json`保留。按cb-plot-unified-style要求修复可视范围内刻度和图例边距，仅重绘保存状态，没有科学重跑。结构图、应力/位移/压力图、五状态图、41帧790×740 GIF均已目检，3份PNG/SVG风格清单passed。所有变形1倍，坐标与场量色标固定；结果图明确标示Qualification FAILED。

独立验证器的扫描线裁切保护在最初来源哈希采样后完成，渲染器也有上述修复。未改写最初`source_hashes.json`或原验证结果：最终源码、差异和原始数组哈希另存`postrender_provenance_v01.json`，按最终验证器对保存状态重算得到`post_verification_v01.json`。失败门不变。

结果包约44 MiB，低于128 MiB；项目逻辑占用约1.59 GiB，低于3 GiB（统计不跟随既有reparse links）。小型字体缓存保留在结果包`runtime_cache`并计入预算，无新外部缓存目录。状态和驾驶舱按失败裁决更新，原候选分割与DCM历史不改写。

## 下一步

固定这份真实外轮廓，先完成FEM分层网格/方向定义的收敛资格，再验证有限变形本构及激活；随后才考虑明确腔压、内部解剖限定和公开动态轮廓对照。当前不自动追加计算、不放宽原门、不恢复DCM、不把逐细胞分割设为前置。

真实三维生理跳动、材料标定、血流、生长及反馈为`not_run`。

[结果页](../results/ventricle_fem/f2_measured_contour_v01_20260917/index.html) · [最终独立复核](../results/ventricle_fem/f2_measured_contour_v01_20260917/post_verification_v01.json) · [来源差异审计](../results/ventricle_fem/f2_measured_contour_v01_20260917/postrender_provenance_v01.json)
