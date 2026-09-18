---
document_id: PRL-FEM-MIXED-LINEAR-REPLAY-EXECUTION-V01
status: passed
executed_at: 2026-09-18
contract: project_control/ventricle_fem_mixed_linear_replay_contract_v01.md
scientific_pressure_space_status: failed
result_root: E:/Temp-Projects/PRL-results/ventricle_fem/f6s1s2_linear_report_replay_v01_20260918
---

# F6-S1-S2：MUMPS工作空间不足已定位

本轮批准的同初值诊断重放完成，报告与独立复核passed。原DG2受压平衡仍failed。
一次15.351秒单CPU容器，固定镜像、0 GPU、0平衡求解、0自动重跑。
11组CSR/右端/映射数组与F6-S1-S逐项完全相同；5组前后状态逐字节相同。

| 记录 | 观察 |
|---|---:|
| KSP reason | -11（PC失败） |
| PC failed reason | 3 |
| MUMPS INFOG(1) | -9 |
| MUMPS INFOG(2) | 1321 |
| MUMPS ICNTL(14) | 20 |
| SuperLU独立相对残量 | 3.169966713272061e-13 |
| SuperLU估计1-范数条件数 | 1.0909860156e9 |
| 容器OOMKilled | false |

## 直接原因与纠正

MUMPS官方指南将`-9`定义为主内部实/复工作数组S过小；`INFOG(2)>0`表示报错当时缺少的数值条目数。
因此1321不是MiB，也不是整个求解最终所需的全部额外条目。`-10`才是数值奇异或零主元错误码。
`ICNTL(14)`是相对于估计工作空间的额外百分比，本次为20。

这次以完全相同的矩阵和原配置重现了线性后端失败，定位到内部因子化工作空间预分配不足。
没有观察到容器OOM杀死，不能把此故障解释为8 GiB容器总内存已耗尽。
之前仅凭块尺度差把“近奇异/小主元”列为首要假设，证据不足以支持其作为直接根因；本记录纠正这一优先级。
块尺度差与约1e9的条件数仍是数值风险，但其是否通过选主元/填充导致工作数组不足，尚未因果验证。

同矩阵SuperLU给出小残量，支持该右端在线性层面可以得到数值解；这不等于非线性平衡、任意右端稳定性或生物学验证。
不再仅凭小残量宣称“排除精确代数奇异”；矩阵满结构秩也不等于数值满秩。

## 证据完整性

MUMPS基本错误码、完整诊断、SuperLU诊断、各自线性向量、矩阵指标及前后状态分别写出。
`+Inf/NaN`明确编码为字符串，原非有限解仍保存在NPZ中；不把无效结果伪造成0或通过。
本次`solution_norm=+Inf`和`relative_residual=NaN`解释了原写报告失败的具体值；不能反推上次未保存字段逐项相同。
受保护375父文件及120个F6-S1-R/S源结果文件哈希保持，原失败包保持原裁决。
独立复核42个正式调用文件身份、规范固定行、解残量及前后状态；后处理没有全局求解或因子化。

19项独立证据检查全部passed；针对性回归53项测试及21项子测试passed。
命令：`python -B -X utf8 -m pytest -q -p no:cacheprovider tests/prl/test_fenicsx_linear_system.py tests/prl/test_fenicsx_linear_system_render.py tests/prl/test_fenicsx_pressure.py tests/prl/test_fenicsx_ring.py tests/prl/test_fem_only_cli.py`。
测试环境提示CuPy未检测到CUDA路径，不涉及GPU启动；本轮实际科学容器仅单CPU。

图件包含实际896单元三层圆环及载荷/规范点、MUMPS错误码、独立残量与证据边界。
v01图稿因字体缺少上标9而保留为未认可稿，v02用1.09e9表示且通过目检。

## 唯一下一步（尚未执行）

最小修复验证应优先只调整`mat_mumps_icntl_14: 20 → 100`，在保存的同一CSR上新建求解器，
一次因子化；比较MUMPS的INFOG=0、有限解及相对残量≤1e-8，并与已保留SuperLU向量交叉核验。
它不改变刚度矩阵、材料、压力空间、边界、加载或1%门；不需要立即做块缩放或压力静态消元。
此设置是否足够尚未验证。通过后再另行恢复圆环非线性被动资格；轮廓、主动、三维、FSI、生长均未在本轮执行。

参考：[MUMPS用户指南第8节](https://mumps-solver.org/doc/userguide_5.9.1.pdf)；
[PETSc MUMPS接口与ICNTL(14)](https://petsc.org/release/manualpages/Mat/MATSOLVERMUMPS/)。
