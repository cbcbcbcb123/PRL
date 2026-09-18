---
document_id: PRL-F6-S2-D2B-ADOPTION-V01
status: passed
date: 2026-09-18
scope: one candidate only; not scientific acceptance
---

# D2B 有界候选执行采纳

用户在具体候选合同提出后最新回复“同意，继续”，采纳
[D2B合同](ventricle_fem_3d_unstructured_comparison_contract_v01.md)的全部边界。
合同中原先的 pending_confirmation 是提出时状态；本记录仅解除该候选执行等待，
不覆盖原始失败、不新增科学范围、不授权清理或推送。

## 运行前固定的实现细节

- 原 M1 每一三角面转为相同三个坐标的平面 CAD 面；边和点全局共享。
  各组织域用有向闭合面壳定义；两个内部界面为相邻域共享的同一面。
  预置全部点、线段及三角形网格，只生成缺失的三维单元。
- Gmsh 单线程；Algorithm3D=1（Delaunay）；MeshOnlyEmpty=1；ElementOrder=1；
  MeshSizeMin=MeshSizeMax=0.18（无量纲L）；FromPoints=FromCurvature=ExtendFromBoundary=0；
  Optimize=OptimizeNetgen=0（关闭隐式优化）；一次显式默认四面体优化，niter=1，
  OptimizeThreshold=0.3。RandomSeed=1只固定算法内部顺序，不扰动原节点坐标。
  Mesh.MaxRetries=0；不启用曲面重网格、Netgen、安装或自动后备算法。
  保存全部显式选项的读回、完整 Gmsh 选项文件、实际版本及日志。
- 薄层基底区：材料1（心内膜）/2（ECM），单元至少一个顶点满足 abs(z)<1e-12。
  q05不下降按两层各自和合并区域检查；最小内二面角按全域及这三个薄层区域检查。
  非下降比较只容许1e-12舍入余量，不改变1%力学门。
- 质量比较包括各层、基底邻接和远区；只使用同一个最终候选，不根据结果换选项。
  保存生成前后的实际网格用于追溯优化；不对优化前状态做额外FEM。
- 独立核验从两个完整体网格重建面邻接，不采用生成器给出的材料界面判断。
  P2/P1预计DOF用全局唯一顶点与边计数：4V+3E。几何顶点重编号可接受，
  坐标和三角集合用精确浮点值集合比较（不做近邻匹配或舍入）。
- 最多一次容器；网格质量失败即停止，FEM标记not_run。若通过才沿用原
  VentricularSolid / advance_case / 独立state_audit进行zero和原pressure_1两态。

选项依据：[Gmsh官方API与网格选项](https://gmsh.info/doc/texinfo/)。
这些是网格工程实现细节，不改变材料、边界、载荷、积分或压力空间。
