---
figure_id: FIG-EFE-NODE0-01-V01
status: draft_for_human_gate_0
purpose: Nature Physics manuscript theory figure
style: ordinary_light_publication_review
aspect_ratio: 3:2
source_contract: docs/theory/efe_node0_minimal_theory_contract_v01.md
---

# Figure 1 v01：EFE 快—慢三层理论框架绘图规格

## 1. 图的核心命题

- **这张图要回答什么问题**：快速心搏、腔压与 WSS 如何通过心内膜—ECM—心肌三层结构产生局部周期机械统计量，并在慢时间上驱动竞争性细胞来源和纤维弹性 ECM 重塑？
- **最重要的一句话结论**：EFE 被建模为“快速活动器官力学 → 慢细胞状态/ECM 生长 → 反向改变快速力学”的候选闭环，而不是预设的增厚材料层。
- **读者必须记住**：细胞来源、状态跃迁和机械记忆是待检验假说；规定压力/WSS 不是双向 FSI。

## 2. 面板规划

- **推荐图型**：A–D 多子图总结图，结合 framework atlas 与 mechanism schematic。
- **画布比例**：3:2，论文印刷友好的浅底布局。
- **A：三层解剖—力学对象**：横向局部心室壁剖面；自上而下画出 lumen、endocardial DCM、cardiac-jelly/fibrous ECM FEM、active myocardial DCM；标出压力、WSS、主动收缩和两个非匹配界面。
- **B：快—慢算子分解**：左侧一个心搏波形和快速力学求解，中间周期统计量 `M(s,T)`，右侧慢状态 `qE/qM/rho_c/rho_el/A_c/F_g`，再用反馈箭头返回下一心搏。
- **C：细胞来源竞争**：并列 `H1-Endo`、`H2-Mes`、`H3-Mixed` 三个微型组织剖面，分别画心内膜转化、间充质细胞迁入和两者共同作用。
- **D：候选状态与功能反馈**：健康、可逆重塑、候选持续 EFE 三个状态；显示病理边界层增厚后 `Lambda_enc` 上升，并可能限制缩短、舒张和发育；橙色虚线表示“尚待分岔验证”的状态边界。

## 3. 必画对象清单

1. 心腔蓝色流体区域与红细胞/流线暗示；
2. 青绿色多边形心内膜细胞层；
3. 浅蓝三维 FEM 网格表示正常 cardiac jelly；
4. 红色长条心肌细胞及相向收缩箭头；
5. 心内膜下胶原波纹纤维和弹性纤维；
6. 压力法向箭头与 WSS 切向箭头；
7. 一个周期心搏/应变波形；
8. 周期统计量的小型字段/波形图标；
9. EndMT 样细胞形态改变；
10. 既有间充质来源细胞的迁入路径；
11. 健康薄层、可逆局部沉积、持续增厚包裹三种状态；
12. `Lambda_enc = E_EFE h_EFE / (E_m h_m)` 的刚度—厚度比。

## 4. 必画关系 / 箭头清单

- 心肌相向橙色箭头：主动收缩输入；
- 压力蓝色法向箭头：规定腔压作用于心内膜；
- WSS 青色切向箭头：规定流体剪切作用于心内膜；
- 快时间实线箭头：三层力学求解生成周期统计量；
- 慢时间紫色箭头：细胞状态推动胶原、弹性纤维和生长更新；
- 病理 ECM 返回心搏求解的红色回环箭头：机械反馈；
- H1/H2 到 H3 的虚线汇聚：竞争来源假说而非既定事实；
- 健康到病理之间的橙色虚线边界：候选状态跃迁，尚待验证；
- `Lambda_enc` 增大到功能受限的红色箭头：待检验预测。

## 5. 必含文字标签清单

图中使用英文短标签以适配 Nature Physics：

- `A  Trilayer fast mechanics`
- `lumen pressure p(s,t)`
- `wall shear stress tau_w(s,t)`
- `endocardial DCM`
- `cardiac-jelly + fibrous ECM FEM`
- `active myocardial DCM`
- `B  Beat-to-remodelling map`
- `one representative beat`
- `cycle statistics M(s,T)`
- `slow cell state + ECM growth`
- `C  Competing cellular origins`
- `H1 Endocardial/EndMT-like`
- `H2 Mesenchymal-derived`
- `H3 Mixed`
- `D  Candidate tissue states`
- `healthy`
- `reversible remodelling`
- `persistent EFE candidate`
- `Lambda_enc`
- `prescribed loads, not two-way FSI`
- `hypotheses, not simulation results`

## 6. 背景、配色与字体

- 白色背景、极浅灰面板底、细灰边框；普通论文科研审阅图风格；3:2。
- 红色：心肌和病理反馈；青绿：心内膜；浅蓝：cardiac jelly/FEM；紫色：慢状态；橙色：主动输入和候选阈值；灰色：未解问题。
- 英文使用 Arial/DejaVu Sans；数学符号使用 Matplotlib mathtext；主标签中等粗体。
- 不使用强阴影、荧光、玻璃质感或商业海报效果。

## 7. 禁止简化项

- 不得把图简化成三个色块加一条空箭头；
- 不得省略 lumen、心内膜、ECM、心肌的空间顺序；
- 不得把压力和 WSS 合并成一个“mechanical force”；
- 不得省略快时间与慢时间的分离；
- 不得只画 EndMT 单一来源；
- 不得把 `persistent EFE candidate` 画成已经证实的病理结果；
- 不得把 prescribed loads 标为 FSI；
- 不得伪造应力数值、显著性、病理厚度或实验曲线；
- 不得使用大段正文、空白标签框或低密度装饰图。

## 8. Final Prompt

Use case: scientific-educational. Asset type: Figure 1 theory schematic for a Nature Physics manuscript. Create a publication-ready 3:2, white-background, four-panel A–D scientific vector-style figure with crisp lines, pale gray panel cards and readable English labels. Panel A shows a local ventricular-wall cross-section in the exact order lumen → polygonal cyan endocardial DCM → light-blue tetrahedral cardiac-jelly plus fibrous ECM FEM → red elongated active myocardial DCM; include separate normal pressure arrows, tangential wall-shear arrows, myocardial contraction arrows and two interfaces. Panel B shows a two-timescale loop: one representative heartbeat waveform and fast trilayer solve → cycle statistics M(s,T) with strain, traction, WSS and phase icons → slow variables qE, qM, rho_c, rho_el, A_c and F_g → a red feedback arrow returning remodeled ECM to the next beat. Panel C compares three cellular-origin hypotheses with small tissue cross-sections: H1 Endocardial/EndMT-like, H2 Mesenchymal-derived, H3 Mixed; use dashed hypothesis arrows and do not privilege one source. Panel D shows healthy, reversible remodelling and persistent EFE candidate states, progressively increasing the subendocardial collagen/elastin layer; include Lambda_enc = E_EFE h_EFE/(E_m h_m), an orange dashed unverified transition boundary, and restrained arrows toward impaired shortening, relaxation and growth. Semantic colors: red myocardium/pathological feedback, cyan endocardium/WSS, light blue cardiac jelly/FEM, purple slow states, orange active input/unverified threshold, gray uncertainty. Include exact labels “prescribed loads, not two-way FSI” and “hypotheses, not simulation results”. Do not fabricate data, numerical fields, disease thickness or significance. Do not reduce the figure to generic boxes, decorative gradients, a pure text-card layout or a single-source EndMT story.
