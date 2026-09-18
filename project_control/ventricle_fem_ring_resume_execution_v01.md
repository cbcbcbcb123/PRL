---
document_id: PRL-FEM-RING-RESUME-EXECUTION-V01
status: failed
executed_at: 2026-09-18
contract: project_control/ventricle_fem_ring_resume_contract_v01.md
evidence_preservation: passed
patch_protocol_tests: passed
patch_runtime_validation: not_run
result_root: E:/Temp-Projects/PRL-results/ventricle_fem/f6s1s4_ring_first_pressure_v01_20260918
---

# F6-S1-S4：记录接口引入失败，未取得受压平衡

本次不是材料、网格或生物学失败的证据。Codex新增的监测代码在第0次SNES回调
使用 `solver.getSolution().array.copy()`，请求可写数组；PETSc已将该向量锁为只读。
原始堆栈明确从 `Vec.array -> array_w -> VecGetArray -> VecSetErrorIfLocked` 报错73，
经SNES回调返回101。首次Newton更新前即退出；0个接受受压态。

这暴露了本阶段测试遗漏：配置/独立力学测试没有覆盖真实PETSc监测接口。
58项事前测试和21项子测试通过，不代表这一新接口已通过集成验证。

## 唯一调用及保存状态

- 一次16.914秒固定镜像容器，单CPU/8 GiB/禁网/0 GPU，退出码2；运行时/挂载安全检查全部通过。
- 尝试非线性平衡1次，接受0次；零载复算0次，自动重跑0次。
- 网格及DG2混合映射与保留源逐数组一致；原零载的18项独立门通过，原3项切线差分检查通过。
- 保存的初始向量、末次尝试向量、原零载混合向量逐字节相同。
- 独立重算该加载初值自由力残量为 **0.008667040857078805**，远高于2e-6。
  此时J=1只是未更新初值，不能标记1%体积资格通过，也不能生成后续形变/应力帧。
- 619个父/祖先证据文件保持；原F6-S1-R/S/S2/S3失败与成功记录未改。

命令：`python -B -X utf8 -m prl run fem-fenicsx-pressure --resume-first-ring --workspace E:\Temp-Projects\PRL`。
已有目录create-only拒绝；本轮不建立替代结果目录重跑。

## 修复写入，但原环境尚未复验

1. 监测改成 `getArray(readonly=True).copy()`；先保全残量历史，再读向量，避免记录异常抹掉诊断。
   针对实际monitor方法的只读锁协议夹具先复现失败、修复后通过，确认不修改原向量、保存独立副本。
2. 同时审计stdout中的未使用 `M0_mat_mumps_icntl_14` 警告。通过只读 `docker cp` 从本阶段停止容器
   取实际安装源码（`runtime_source/dolfinx_petsc.py`），没有启动额外容器。
   源码1300–1314显示NonlinearProblem在SNES.setFromOptions后移除临时选项；
   矩阵因子化晚于该步骤，不能仅向构造器字典加入此参数就声称已接通。
   改为在构造器之后按实际KSP前缀保留该选项到LU设置，并要求实际因子矩阵ICNTL回读。
   本次在分解前已失败，因此本次因子的实际ICNTL值为unknown，不倒推成20或100。

修复后60项测试及21项子测试通过；其中接口夹具不是PETSc/DOLFINx集成测试。
完整原容器复验 **not_run**；不得把补丁或单元测试称为已消除原环境症状。
材料、步长/载荷、离散空间和独立力学门没有改变。

复核命令：`python -B -X utf8 -m prl verify fem-fenicsx-pressure --resume-first-ring`，结果failed（无受压状态）。
测试命令：`python -B -X utf8 -m pytest -q -p no:cacheprovider tests/prl/test_fenicsx_linear_system.py tests/prl/test_fenicsx_linear_system_render.py tests/prl/test_fenicsx_pressure.py tests/prl/test_fenicsx_ring.py tests/prl/test_fem_only_cli.py`。

接口依据：[PETSc getArray只读参数](https://petsc.org/release/petsc4py/reference/petsc4py.PETSc.Vec.html#petsc4py.PETSc.Vec.getArray)；
[DOLFINx选项对象及动态前缀说明](https://docs.fenicsproject.org/dolfinx/main/python/generated/dolfinx.fem.petsc.html#dolfinx.fem.petsc.NonlinearProblem)。
网络文档版本可能高于固定镜像；本地实际源码与失败堆栈是当前版本行为的主要依据。

## 图件、交付及下一步

实际三层初始网格/边界载荷图，以及从保留加载初值独立重算的未平衡力网格图，
均由物理复制输入和已执行Notebook生成；600 dpi PNG、SVG、样式及目检通过。
没有新接受态，所以不补造5帧或心动动图。`figure_runtime`为有用途登记的缓存，未授权删除。
不删除任何文件、不安装/拉取/重启Docker、不推送；无关50项工作区变更保留。

唯一下一步（待用户确认）：一次有界v02调用中，先在同一固定环境做只读锁向量与MUMPS选项的微型接口烟测
（不建FEM模型），通过后才从保留零载续算同一首个p/mu=0.02受压态。
0 GPU、单CPU、不重跑零载、不改原1%门、任一失败即停；不扩展压力、细网格、轮廓、主动、3D、FSI或生长。
