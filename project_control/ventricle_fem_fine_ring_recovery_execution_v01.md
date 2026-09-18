---
document_id: PRL-FEM-FINE-RING-RECOVERY-EXECUTION-V01
status: passed
executed_at: 2026-09-18
contract: project_control/ventricle_fem_fine_ring_recovery_contract_v01.md
native_diagnosis: passed
runtime_interface: passed
fine_passive_sequence: passed
original_two_mesh_qualification: passed
evidence_delivery: passed
result_root: E:/Temp-Projects/PRL-results/ventricle_fem/f6s1s6_fine_ring_v01_20260918
---

# F6-S1-S6：零载诊断崩溃修复，原两网格被动圆环资格通过

新增M1五态全部通过，M0五态全部只读复用，粗网格0次重算。材料、载荷和原门限未改变。
本轮通过的是二维理想圆环被动固体的原两级数值资格，不是三维、真实轮廓或生物学验证。

## 诊断事实与最小修复

同一固定镜像中的6自由度负例：SNES返回reason=2、iterations=0、residual=0，KSP reason=0；
`getFactorMatrix()`返回非空对象，随后`getMumpsInfog(1)`出现原生段错误。
逐调用标记停在`get_infog_enter`，Python故障回溯精确指向该语句；负例6.407秒、容器退出15，OOMKilled=false。
因此已定位到“无本次线性求解却读取因子统计”的诊断边界，而不是细网格零载不平衡或内存耗尽。
上游MUMPS内部实现细节未进一步排查，不声称改修了PETSc本身。

最初自动分类器额外要求Mat句柄为空，实际记录不满足，该次分类failed原样保留。
只读复核纠正的是这个空句柄假设，不是物理验收门；新的`native_diagnosis_review.json`将调用位置判定为passed。
负例未重复运行，旧日志/源码/失败裁决全部保留。
官方[MatMumpsGetInfog接口](https://petsc.org/release/manualpages/Mat/MatMumpsGetInfog/)要求MUMPS因子矩阵；
在线文档3.25.5不是固定运行时3.25.1的实现证据，本次结论主要来自真实负例和后续复验。

生产`Ring.solve`只抽出安全的因子报告方法：本次Newton更新数为0时不访问KSP/PC因子，
报告not_run及null，避免无效读取和陈旧统计；存在实际更新时仍核验KSP/PC，再读取原MUMPS统计。
不为生成诊断额外分解矩阵，不更改残量、切线、能量、线搜索、容差或任何材料参数。
增加有限的调用边界记录，作为保留诊断资产；没有临时插值或伪造末态。

两项生产solve协议回归在修复前因多余factor调用失败，修复后通过；另覆盖有效KSP与失败/未运行KSP。
真实修复后6自由度检查包含零载、非零右端、已收敛解再次调用：Newton更新数为0/1/0，全部通过。
零更新时所有因子读数为null；非零更新时实际INFOG=0、ICNTL(14)=100。随后才允许M1求解。

## 五个新增细网格接受态

| p/mu | 腔面积变化 | max abs(J−1) | 相对不可压解析响应误差 | Newton更新 |
|---:|---:|---:|---:|---:|
| 0 | 0% | 0% | 不适用 | 0 |
| 0.02 | +4.675989% | 0.00255889% | 0.0582068% | 3 |
| 0.04 | +9.897397% | 0.00540304% | 0.0621881% | 3 |
| 0.06 | +15.776386% | 0.00859115% | 0.0668167% | 3 |
| 0.08 | +22.460165% | 0.01219238% | 0.0722750% | 3 |

M1零载保存最终reason=2和完整零向量，独立复核passed；没有因子分解，明确not_run，不伪报MUMPS通过。
全部正压局部J偏差低于原1%，解析面积响应和径向位移L2误差低于原1%；
最大径向L2相对误差0.0589786%。峰值自由力残量1.1733e-13，弱压力残量1.1910e-15。
峰值DG2点态体积约束误差2.0020e-13，远低于1e-9；压力虚功和规范反力等原门通过。

粗细峰值面积响应差0.000865913个百分点（无量纲绝对差8.65913e-6），相对差0.00385533%，
满足原绝对0.002/相对5%门。其余压力差亦报告。保留5个M0态与新增5个M1态共10个接受态；
M1网格及混合映射与上轮失败前网格逐数组相同，原CG1同网格对照只读复用。
有限kappa模型与严格不可压解析参照并非同一精确解，不要求解析差随此两级加密单调下降。
两个网格层级通过不等于多级渐近收敛，也不证明应力热点收敛或实验吻合。

## 运行与保全

负例6.407秒；修复后接口及5态运行51.511秒。合计2个预声明串行容器、1次科学调用，单CPU/8GiB/禁网/0GPU。
980个父/祖先文件与50项无关工作区修改保持；162个正式调用文件不改写。
69项独立范围/网格/初值链/逐态/粗细检查通过；M1共17个实际Newton向量（零载1个、正压各4个）。
76项定向回归及21项子测试通过，不代表所有退役代码或生物学验证。

正式容器前曾有新增入口括号笔误和锁内读取Windows互斥锁文件的预检查错误，0容器/0求解；
修正后仅恢复原路径上3个保护清单及其错误记录，未删除或覆盖旧科研包。
互斥锁仍跨整个实际容器调用持有，锁文件哈希在锁外前后核验，未放弃保护检查。

两套Notebook已执行，600dpi PNG/SVG、自动样式与目检验收通过。仅使用保留u/p独立重算，包含结构、1倍形变、应力、局部J、解析及粗细响应；
5个压力步骤不是心动时刻，不合成中间帧。三层被动参数相同，尚无主动载荷。
本轮没有安装、升级、拉取、Docker修复/重启、删除、GPU或推送。
绘图运行缓存候选为`E:\Temp-Projects\PRL-results\ventricle_fem\f6s1s6_fine_ring_v01_20260918\figure_runtime`，
所有权/用途已登记，未获删除授权而保留；正式图与输入位于figures，不依赖此缓存。

运行（已消耗）：`python -B -X utf8 -m prl run fem-fenicsx-fine-ring --phase diagnose`及`--phase complete`。
只读独立复核：`python -B -X utf8 -m prl verify fem-fenicsx-fine-ring --phase complete`。
结果入口：[结构/压力态/独立复核](../../PRL-results/ventricle_fem/f6s1s6_fine_ring_v01_20260918/index.html)。

## 唯一下一步待确认

回到原图像外轮廓（内腔及三层界面仍为构造），以同一P2/DG2和原参数，
仅检验粗/细网格零载与首个p/mu=0.02被动压力态，最多4态，原1%门限不变、失败即停。
不重复圆环，不开启主动或三维/FSI/生长；通过后再裁决后续压力和主动收缩。
