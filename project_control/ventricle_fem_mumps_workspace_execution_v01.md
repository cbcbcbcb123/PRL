---
document_id: PRL-FEM-MUMPS-WORKSPACE-EXECUTION-V01
status: passed
executed_at: 2026-09-18
contract: project_control/ventricle_fem_mumps_workspace_contract_v01.md
scientific_pressure_space_status: failed
result_root: E:/Temp-Projects/PRL-results/ventricle_fem/f6s1s3_mumps_workspace_v01_20260918
---

# F6-S1-S3：同矩阵MUMPS工作空间修复验证通过

只将工作空间额外余量从20%改100%，同一保存CSR上的MUMPS线性求解通过。
没有改变材料、几何、压力空间、载荷、边界或原1%局部体积门；没有重组装或更新FEM状态。

| 指标 | 上轮20%（保留） | 本轮100% |
|---|---:|---:|
| MUMPS INFOG(1) | -9 | 0 |
| MUMPS INFOG(2) | 1321 | 0 |
| KSP reason / PC failed reason | -11 / 3 | 4 / 0 |
| 解有限 | 否 | 是 |
| 独立相对残量 | 非有限 | 7.477259895559e-11 |
| 与保留SuperLU解的相对2范数差 | 不可评价 | 1.4463521450606135e-8 |

预声明残量门1e-8、向量差门1e-6均通过。SuperLU本轮没有重新因子化，其保存向量的独立残量仍3.169966713272061e-13。
PETSc返回残量7.476841096221056e-11与NumPy/SciPy独立乘法的尾数差在预声明一致性容差内。
同一顺序AIJ矩阵、M0_前缀及preonly/LU/MUMPS保持；14个其他已记录ICNTL/CNTL项逐项相同。
因此本次对照支持工作空间预分配不足是所保存切线的直接失败原因，100%余量足以消除该次线性故障。
这不保证所有后续Newton切线都成功，也不证明非线性体积精度或斑马鱼实验拟合。

## 运行与独立证据

一次固定镜像容器8.380秒，内部线性诊断0.644秒，单CPU/8 GiB/禁网/0 GPU。
0次FEM组装、1次MUMPS尝试、0次新SuperLU因子化、0次非线性平衡、0次状态更新、0次求解自动重跑。
11组保存矩阵/右端/映射数组、求解前后3组原生CSR和2组初值字节身份一致。
19项证据检查及7项线性验收检查passed；41个正式调用文件、375父文件和176来源文件身份保持。

首次主机准入在本地镜像标签查询处20秒超时，未创建结果目录或容器。随后有时限只读SHA查询成功，
同名容器列表为空，才继续首次科学调用。共2次主机准入、仅1个正式容器；不是重跑失败计算。
本次超时原因unknown；未观察到/诊断为旧AF_UNIX错误1920，未重启、隔离或删除Docker目录。
见结果包`preflight_observation.json`。不得把这次短暂运行时查询超时混作FEM故障。

回归测试：56项测试与21项子测试通过，3个新增边界/残量测试先失败再通过。
命令：`python -B -X utf8 -m pytest -q -p no:cacheprovider tests/prl/test_fenicsx_linear_system.py tests/prl/test_fenicsx_linear_system_render.py tests/prl/test_fenicsx_pressure.py tests/prl/test_fenicsx_ring.py tests/prl/test_fem_only_cli.py`。
既有50项无关工作区改动不纳入本阶段提交；结果在批准的外部库，不进Git。

## 图件及边界

版本化Notebook从物理复制的保存网格/向量/独立诊断绘制实际三层结构与残量对照，
沿用项目紧凑FEM诊断风格、显式固定轴框，导出600 dpi PNG及可编辑SVG。
图中20%失败无有限残量，不画成0；SuperLU明确为上轮保留；0个新平衡态不伪造多时刻形变图。
完整性、Notebook执行及样式/目检结果以版本包methods和style manifest为准。

`figure_runtime`仅为本阶段Jupyter/Matplotlib临时缓存，包含用途记录，未获删除批准所以原位保留。
不删除旧失败包、旧容器或任何未授权路径。

## 唯一下一步（本轮未执行）

将已验证的`mat_mumps_icntl_14=100`接回原圆环P2/DG2求解器，从保留零载接受态继续首个`p/mu=0.02`被动态。
不重跑零载，不改物理、容差或1%门。一次有界非线性调用，首失败保全；检查非线性平衡、积分点J和独立力平衡。
若该态通过，才进一步裁决剩余圆环压力点及粗细网格资格，之后回到真实外轮廓；主动/三维/FSI/生长仍未执行。

选项定义依据：[PETSc MUMPS接口](https://petsc.org/release/manualpages/Mat/MATSOLVERMUMPS/)。
