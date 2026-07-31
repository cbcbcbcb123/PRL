# 混合架构说明 v01

## 组件边界

| 组件 | 责任 | 不负责 |
|---|---|---|
| SimuCell3D cell engine | 细胞表面、局部重网格、接触候选、极性、增长/分裂能力 | 体积 ECM 本构 |
| persistent surface registry | 跨重网格保存材料点 ID、状态、权重和界面归属 | 生成物理黏附定律 |
| tetrahedral ECM engine | 有限变形超弹性、黏弹内部变量、厚度方向应力 | 细胞拓扑 |
| coupling adapter | 非匹配投影、tether、作用—反作用、功率端口 | 隐式创造或删除能量 |
| Route H oracle | 小规模 manufactured/reference 检查 | 大规模生产求解 |

## 上游源码审计基线

- source: `https://git.bsse.ethz.ch/iber/Publications/2024_runser_simucell3d.git`
- pinned commit: `38af45154070b2b08dcdb25cbe629de499f382d9`
- license: BSD 3-Clause
- language/build: C++17, CMake, OpenMP；官方 Windows 路径为 WSL，另提供 Dockerfile；
- remeshing operations: edge split、edge merge、edge swap；
- Python binding: pybind11，可选构建。

## 已发现的扩展 seam

1. `split_edge` 显式把两个旧 face type 复制到四个新面；
2. `swap_edge` 删除两个旧面并创建两个新面，但没有通用连续材料状态转移；
3. `merge_edge` 处理节点位置及动量/previous-force，但没有本项目所需的持久材料点注册表；
4. 上游 face type 是有限类别参数，不足以直接承载每个 tether 的持久 ID、reference weight、主动纤维状态和 ECM 内部变量；
5. 因此本项目首先在 adapter 层建立 topology-independent registry，再决定是否向上游 C++ 类添加 hook。

## 状态所有权

- cell geometry owner: SimuCell3D cell engine；
- cell material-point owner: persistent surface registry；
- ECM deformation/internal-variable owner: tetrahedral ECM engine；
- tether constitutive owner: coupling adapter；
- remesh event owner: cell engine；
- remesh transfer audit owner: persistent registry；
- power ledger owner: coupled driver。

## 首个垂直切片

X0-B 使用几何完全相同、拓扑不同的三角 patch 验证：

1. edge split 后材料点重新绑定；
2. diagonal swap 后材料点重新绑定；
3. ID、标签、连续状态和 reference weight 不变；
4. barycentric nodal scatter 前后合力与合力矩不变；
5. 新表面超出允许几何距离时 fail-fast，不静默重绑。
