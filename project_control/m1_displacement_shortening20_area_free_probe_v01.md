---
record_id: M1-DISPLACEMENT-SHORTENING20-AREA-FREE-PROBE-V01
status: completed_kinematic_preview_only
authorized_at: 2026-08-09
authorized_by: human_final_reviewer
scope: single-cell displacement-loading development probe
formal_gate_change: false
preserves:
  - existing active-contraction baseline and failure records
  - volume-conservation requirement
---

# M1 位移控制缩短20%与面积释放试验记录 v01

## 1. 人类终审授权的修改

1. 轴向缩短由主动弹簧力加载改为规定变形加载；
2. 端部距离必须达到20%缩短；
3. 释放原六个表面区域的面积守恒惩罚；
4. 保持细胞体积不变并检查最终形态。

## 2. 首次端部位移—自由平衡尝试：拒绝

首次尝试把两端锚定面夹持并逐步靠近，内部节点在 `k_area=0, k_volume=100` 下自由平衡。
端部缩短虽然达到20%，但该状态不得接受：

- 体积下降11.15%；
- 总表面积下降11.42%；
- 最小面面积比降至 `1.45e-9`；
- 自由节点力梯度残差仍很大；
- 增大体积罚刚度至10000后仍出现近退化三角形和未收敛状态。

原因是原区域面积项不仅限制面积，也提供了主要的面内正则化；直接将 `k_area` 置零后，当前
被动表面模型只剩弯曲和全局体积项，无法形成良定的自由表面平衡问题。

该拒绝结果保存在：
`results/route_h/m1_displacement_shortening20_area_free_v01/`。

## 3. 修正后的等体积位移控制预览

为了独立展示“必须缩短20%且面积不受约束”的几何效果，采用齐次等体积规定变形：

`F = diag(0.8, 1/sqrt(0.8), 1/sqrt(0.8))`。

结果为：

- 轴向缩短：20.000%；
- 两个横向方向膨胀：各11.803%；
- `det(F)=1`；
- 体积比：1.000000；
- 总表面积比：0.970501，即减少2.950%；
- 六个区域面积比分别约为
  `0.9046, 0.9046, 1.2112, 1.2112, 0.8962, 0.8962`；
- 最小面面积比：0.8944；
- 最小面朝向余弦：0.9887；
- 翻转面和退化面均为0。

结果保存在：
`results/route_h/m1_isochoric_displacement20_area_free_v01/`。

## 4. 证据边界

该结果是满足规定变形和精确等体积条件的可接受运动学状态，能够用于审阅20%缩短后的形态；
它不是删除面积项后的被动力学平衡，也不是能够自主收缩的心肌细胞模型。

下一步若继续采用位移控制，应补充独立于区域面积守恒的面内剪切/网格正则化或实体材料本构，
并使用真正的不可压缩约束，再求解仅在端部施加位移时的内部平衡。
