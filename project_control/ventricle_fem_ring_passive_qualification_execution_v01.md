---
document_id: PRL-FEM-RING-PASSIVE-QUALIFICATION-EXECUTION-V01
status: failed
executed_at: 2026-09-18
contract: project_control/ventricle_fem_ring_passive_qualification_contract_v01.md
coarse_pressure_sequence: passed
fine_execution: failed
mesh_comparison: not_run
evidence_delivery: passed
result_root: E:/Temp-Projects/PRL-results/ventricle_fem/f6s1s5_ring_passive_v01_20260918
---

# F6-S1-S5：粗圆环完整压力通过；细圆环零载出现原生段错误

本轮不是整阶段passed。新增M0的0.04/0.06/0.08均接受；结合复用的零载与0.02，
粗网格5个压力态已全部通过独立物理门和原2%解析响应门。
随后M1在零载调用中出现PETSc信号11，未保存最终状态与收敛报告。细网格执行failed，粗细比较not_run。
没有自动重跑、额外容器、材料改变或门限放宽。

## 已获得的科学结果

| p/mu | 来源 | 腔室面积变化 | max abs(J−1) |
|---:|---|---:|---:|
| 0 | 复用 | 0% | 0% |
| 0.02 | 复用 | +4.675918% | 0.00262844% |
| 0.04 | 本轮新增 | +9.897205% | 0.00568533% |
| 0.06 | 本轮新增 | +15.775963% | 0.00927253% |
| 0.08 | 本轮新增 | +22.459300% | 0.01348334% |

全部局部体积偏差低于原1%门。最大相对不可压解析面积响应误差为0.0684168%，低于M0原2%门。
本轮3个新态各3次Newton更新，实际MUMPS余量100、INFOG=0；最高独立自由力残量1.637e-13，
DG2点态约束误差最高1.934e-13，小于1e-9。
腔室面积扩大并不要求壁组织体积膨胀；这是未标定理想圆环的数值证据，不是实验心室的验证。
主动收缩仍为0，压力是规定边界；没有求解血流、三维、生长或ECM反馈。

## 细网格停止：事实、推断及未知

- 一次23.705秒单CPU/8GiB/禁网容器，镜像SHA仍为`2ae4bfbc0d9077268880faf04c72750528bee986c94ab223a2c159969bd56fa8`。
- 9项容器设置通过，OOMKilled=false；stderr记录SIGSEGV信号11、MPI Abort(59)，容器退出码15。
- 尝试4态、接受3态；M1零载之前，M1几何及切线检查已经通过。
- M1只保存monitor迭代0，求解器记录残量2.1753447692e-16；混合向量全部为0，与保存初猜逐数组相同。
  独立复算自由力/弱压力残量0、J=1，但没有最终SNES原因或完整末态，不能计为已接受平衡。
- Python异常处理未执行，不能把不存在的failure.json当作已保全的原生调用栈。
  真实stderr、container_inspect、M1网格/初猜/monitor向量和最后有效M0态均保持原位。

优先排查假设：`Ring.solve`在取得最终求解数据后、保存完整末态前，无条件查询PC/MUMPS因子。
新M1零载可能0次Newton即收敛，尚无LU因子；这一诊断边界需与零次更新情形区分。
但目前没有原生栈或逐调用标记，**尚未证实SIGSEGV发生在此处**；也未排除SNES返回及对象生命周期问题。
官方[PCFactorGetMatrix说明](https://petsc.org/release/manualpages/PC/PCFactorGetMatrix/)和
[MatMumpsGetInfog说明](https://petsc.org/release/manualpages/Mat/MatMumpsGetInfog/)均针对因子矩阵。
当前[官方实现](https://petsc.org/release/src/ksp/pc/impls/factor/factimpl.c.html)对未建立因子有顺序错误检查；
在线版本为3.25.5、固定镜像已核验为3.25.1，不能用在线源码直接宣称解释了本次原生段错误。
本轮按cb-diagnose停留在日志/源码/已保存状态诊断，没有修改Ring、再次求解或宣称修复通过。

## 图件、复核及保全

两套物理复制输入的Notebook：结构/1倍峰值形变/解析响应/局部J门，以及5个真实压力态共享色标应力图和峰值局部J图。
前2态明确标记复用，后3态为本轮新增；载荷延拓不是生理时间，不插值补帧。
细网格没有受压场量，不生成或借用粗网格图冒充细网格结果。
PNG 600dpi与SVG完成自动样式及目检；图件通过不改变整阶段failed。

事前67测试+21子测试通过；补充“不补造缺失细网格状态”绘图回归后68测试+21子测试通过。
这些测试没有覆盖此次真实PETSc零次更新/原生退出路径，不代表该接口已通过。
826个父/祖先文件、50项无关工作区修改及98个正式调用文件哈希保持。
结果与缓存均在批准的外部结果根，缓存有用途登记，本轮不删除任何文件。

运行（已消耗，create-only）：`python -B -X utf8 -m prl run fem-fenicsx-pressure --complete-passive-ring --workspace E:\Temp-Projects\PRL`。
只读复核：`python -B -X utf8 -m prl verify fem-fenicsx-pressure --complete-passive-ring --workspace E:\Temp-Projects\PRL`，预期failed（缺少细网格末态）。
测试：`python -B -X utf8 -m pytest -q -p no:cacheprovider tests/prl/test_fenicsx_linear_system.py tests/prl/test_fenicsx_linear_system_render.py tests/prl/test_fenicsx_pressure.py tests/prl/test_fenicsx_ring.py tests/prl/test_fem_only_cli.py`。

[本轮总览、场量与全部压力态](../../PRL-results/ventricle_fem/f6s1s5_ring_passive_v01_20260918/index.html) ·
[独立核验](../../PRL-results/ventricle_fem/f6s1s5_ring_passive_v01_20260918/post_verification.json) ·
[故障事实与假设](../../PRL-results/ventricle_fem/f6s1s5_ring_passive_v01_20260918/failure_diagnosis.json)。

## 下一步待确认

先针对零次Newton收敛后的诊断路径做同环境微型接口测试，增加故障回溯与必要调用边界记录；
定位后做最小修复，因子尚未建立时不读取MUMPS、不为取得报告额外求解。
微测通过后只恢复未完成的M1零载及4个压力态；不重复本轮已接受的3个M0态，不改1%/解析/粗细门。
仍为单CPU、0GPU、失败即停，不恢复原轮廓/主动/三维/FSI/生长。恢复科学运行需新的明确确认。
