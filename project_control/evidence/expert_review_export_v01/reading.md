# 代码导读与只读复核

从00_评审入口.html开始，再读01_项目进展与模型.md和02_专家问题.md。

## 核心代码阅读顺序

1. PRL/src/prl/fem/ventricle_geometry.py：配置、规则三层半椭球体网格及几何检查。
2. PRL/src/prl/fem/fenicsx_ventricle.py：真正三维混合有限变形形式、约束、随动压力、主动项、原始状态输出。
3. PRL/src/prl/fem/fenicsx_ring.py：二维形式，以及三维继承的向量、切线检查、SNES/PETSc记录。
   三维类没有调用二维构造/solve/monitor；共享簿记不意味着三维已继承二维科学资格。
4. PRL/src/prl/fem/ventricle_protocol.py：状态先后、初值和首失败停止，不实现力学裁决。
5. PRL/src/prl/verification/ventricle_3d.py：独立NumPy形函数、F/J、应力、体积与残差重算。
6. PRL/src/prl/verification/ventricle_mesh_probe.py、tetra_quality.py：局部体积热点与网格质量诊断。
7. PRL/src/prl/fem/unstructured_geometry.py、ventricle_unstructured.py：冻结边界候选及条件式FEM入口。
8. PRL/src/prl/verification/mesh_equivalence.py、saved_gmsh.py：独立拓扑/面片/体积/质量与原始MSH读回。
9. PRL/src/prl/fem/fenicsx_pressure.py、fenicsx_contour_pressure.py及verification/fenicsx_contour_active.py：二维资格参照。

PRL/src只保留这些核心入口的静态本地依赖闭包，具体模块见DEPENDENCIES.json。
导出包有三处明确的非力学适配：fem、runs、verification的__init__.py不再自动导入历史路线，
改为只有说明文字的命名空间入口。原入口完整保存在PRL/packaging_originals/src/prl下。
这不改求解、材料、验证公式或项目原代码；也不能当作主项目架构耦合已修复。
没有复制CLI、大批历史runner或另一套维护内核。历史执行源在各证据包sources_at_execution中供对照，
它们不是当前可直接运行的独立项目。当前源与执行时源可能不同（特别是节点重编号适配器），清单分别记载。

## 默认安全复核（仅Python标准库）

在解压目录运行：

```
python -B -X utf8 review_check.py
```

检查每个打包文件的SHA-256、代码语法、入口链接、来源复制一致性记录；不安装、不写回、不求解。
如已有numpy/scipy/meshio，可进一步运行：

```
python -B -X utf8 review_check.py --numerics
```

这只读取保存状态，独立重算原M0/M1首压力及候选几何/质量。预期：
M0/M1压力验收均failed，候选质量failed；若准确复现这些失败，脚本的“证据复核”可以passed。
不能把复核passed写成科学门通过。此脚本不是新FEM或新网格生成器。

## 运行环境与限制

- 当前生产依赖：FEniCSx/DOLFINx 0.11.0固定镜像、Basix/UFL/PETSc/MUMPS；实际版本见环境JSON与原命令记录。
- 镜像摘要：sha256:2ae4bfbc0d9077268880faf04c72750528bee986c94ab223a2c159969bd56fa8。
- 网格候选实际Gmsh 4.15.2；只读MSH读取meshio 5.3.5。
- 图版本含可编辑Notebook、源数据和辅助模块；本次打包没有重新执行Notebook。
- 不附Docker镜像、二进制、第三方安装器或实验大影像，不自动联网拉取/安装/启动Docker。
- 没有新增科学运行授权。生产入口存在写结果/调用求解器能力，请勿将评审包当作“一键批量重跑”。
- 原项目目前未发现根许可证；当前原创源码供本次受邀评审，不额外授予商业或公开再分发许可。
  第三方项目仍受各自许可证约束，包内不重新分发其求解器二进制。

## 清单与来源

MANIFEST.json校验本评审包；PROVENANCE.json记录每份复制物的原路径和哈希。
各阶段SOURCE_MANIFEST.json是原完整运行包清单，SELECTION.json明确哪些文件被选择/省略。
省略不表示源文件已删除。图版本按完整目录原样复制，没有改名内部文件或更新原QA。
原合同中的跨包/绝对路径是历史来源记录，新的评审入口链接则在本包内闭合。
