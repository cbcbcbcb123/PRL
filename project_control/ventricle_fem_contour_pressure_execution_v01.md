---
document_id: PRL-FEM-CONTOUR-PRESSURE-EXECUTION-V01
status: failed
executed_at: 2026-09-17
contract: project_control/ventricle_fem_contour_pressure_contract_v01.md
result: results/ventricle_fem/f5_contour_pressure_v01_20260917
scientific_invocations: 1
new_scientific_solves: 10
automatic_science_retries: 0
---

# F5｜真实外轮廓被动压力资格失败

按[冻结合同](ventricle_fem_contour_pressure_contract_v01.md)一次单线程CPU调用完成`radial_coarse` 144单元和`radial_fine` 288单元各五个压力平衡态，共10次新求解、0科学重跑。求解用时618.557秒；F2/F4父证据运行前后逐文件哈希不变。独立验证明确为`failed`，因此本阶段没有恢复主动收缩。

## 模型和已通过部分

外边界来自72 hpf Fish 4最大占据XY切片39：冻结36段周期Q2曲线相对mask的IoU为0.9946353，对原轮廓独立采样Hausdorff距离1.248917 µm，解析全段最小方向量0.0126729。构造腔面/层界按20/27、21/27、22/27、1同心缩放；这不是实测内腔或真实层界。静态外形被假定为零压无应力参考态。

材料为同一未标定被动NH `mu=1, kappa=1000`；当前内壁随动压力`p/mu=0/0.02/0.04/0.06/0.08`，外壁自由，无主动、端盖或弹簧。全部`uz=0`，平面内只有三个刚体规范DOF，所以仍是3D实体实现的平面应变资格。

配置、父证据、来源/参考几何、初值链、独立场量重算、自由力/弱压力残差、闭合压力合力和力矩、规范反力、虚功、跨z一致性、腔面积单调性及厚向响应比较均passed。最高压力下coarse/fine构造腔面积变化为68.0255%/68.0587%，绝对差0.03315个百分点；细网格自由力残差1.0031e-11，弱压力残差2.8592e-17。

## 唯一科学失败

两档网格四个正压态都只在`maximum_local_volume_change`子门失败。细网格最大`|J−1|`依次为18.8298%、33.5393%、44.8045%、54.0884%，远高于1%门；末态最小J=0.690293、最大J=1.540884。所有J仍为正，当前内外Q2曲线闭合、简单且严格嵌套，所以不是翻转或边界碰撞。

保存J与独立`det(F)`重算最大差1.3445e-13，暂无验证器误判证据。末态细网格加权平均J=1.0001525，但43.17%的Gauss点、约24.76%的参考体积超过1%局部门；内层最严重。证据支持“弱式总体近不可压、局部压缩/膨胀模态相互抵消”，但尚不能在周向离散、单元畸变和压力空间之间指定唯一原因。径向细化没有改善峰值，因此厚向全局响应一致不能升级为局部数值资格。

## 图件与控制流

正式worker在验证写出failed后生成力学图时触发symlog刻度样式异常，公共CLI退出1；原[failure.json](../results/ventricle_fem/f5_contour_pressure_v01_20260917/failure.json)保留，它记录的是随后发生的绘图异常，不能替代更早的科学失败。原正式调用清单已逐字节保存在[formal_invocation_manifest.json](../results/ventricle_fem/f5_contour_pressure_v01_20260917/formal_invocation_manifest.json)，SHA-256为`d40714b28f8e0a654c91735077c8409785a9d28adab3ac8a734496b24fc044d7`；顶层`manifest.json`在交付末尾重建为全包最终清单。仅修改F5残差面板的轴内刻度后，从已保存状态执行一次纯render；0新求解，raw、Newton和verification哈希不变。

三套600 dpi PNG和可编辑SVG已通过外部样式检查并目检。结构图叠加来源mask、原/平滑轮廓、冻结Q2边界、构造层界、压力和规范点；力学图明确标注`Qualification FAILED`并显示局部J失败；五状态图只用fine真实态、1倍位移、统一总Cauchy von Mises色标。见[结果页](../results/ventricle_fem/f5_contour_pressure_v01_20260917/index.html)、[独立验证](../results/ventricle_fem/f5_contour_pressure_v01_20260917/verification.json)和[重绘审计](../results/ventricle_fem/f5_contour_pressure_v01_20260917/postrender_execution_v01.json)。

阶段包约17 MiB，低于64 MiB；项目仍低于3 GiB。无GPU、DCM、删除、安装、提交、推送或项目外写入。

## 唯一下一步

先冻结一个小型F5-R1数值诊断合同：保持外轮廓、材料、腔面和1%门不变，分离检查周向细化、参考单元质量/曲率热点以及体积约束离散；优先确认局部J模态能否随合适离散收敛。通过前不加入主动张力，不把构造腔面积变化解释为真实射血分数，也不进入材料/周期、生长或ECM反馈标定。
