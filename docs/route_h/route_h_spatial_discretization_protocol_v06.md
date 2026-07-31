# Route H Stage 0 v06 空间离散验证协议

## 目的

本协议只关闭 v05 的 `STAGE2-DISCRETIZATION-BLOCK`。它不运行主动响应、不改变模型方程，
也不把无量纲验证解释成生理标定。

## 冻结离散族

| level | cell subdivision | 每细胞 vertices/faces | ECM intervals |
|---|---:|---:|---:|
| coarse | 1 | 42 / 80 | 6 / 4 / 2 |
| base | 2 | 162 / 320 | 12 / 8 / 2 |
| fine | 3 | 642 / 1280 | 24 / 16 / 4 |

base 的 22 个二进制数组必须与 Stage 1 v01 reference bundle 逐字节一致。coarse/fine 使用
与 v05 相同的 patch bounds、实体数、拓扑生成顺序、材料身份、作用—反作用 owner 与
canonical serialization。

## coarse 几何 admission erratum

coarse 平面三角形的界面 barycenter 比 base/fine 更远离真实 superellipsoid 界面；
预响应 materialization 显示 cell–ECM 最大自然间隙为
`0.06348416662201481`，超过 v05 为单一 base topology 设置的 `0.05`。

v06 因而在任何求解前冻结 `0.075` 作为三层共同的 cell–ECM **geometry admission
ceiling**。该量只决定 reference tether 是否允许写入 bundle：

- 它不进入 adhesion、steric、support、ECM 或 cell energy；
- 它不进入力、功率账本或求解器；
- 每对 tether 仍使用自身封存的 `g0_pair` 和 `delta_g=g-g0_pair`；
- cell–cell admission ceiling 保持 `0.15`；
- 接触/黏附势、无量纲机械参数和所有 Stage 2 载荷均不变。

## PreStage2 封存门

每个 level 必须同时通过：

1. 数量、ID、canonical hash 与 fresh replay；
2. cell watertight/orientation/quality/positive volume；
3. ECM positive tetra 与至少两个厚度单元层；
4. tether、source map、owner、anchor、gauge 完整覆盖；
5. 被动 reference energy/force、材料 pair force/moment；
6. closed-surface steric energy 为零且无 proper intersection；
7. v06 冻结清单无 hash mismatch。

任一失败均保持 Stage 2 科学运行数为零。

## Stage 2 空间响应协议

- 注册 cases：`E0_ZERO` 与 `E4_COMBINED`；
- 三层都运行，coarse 用于趋势诊断，正式阈值比较 base 与 fine；
- 非零关键量采用
  `|q_base-q_fine|/max(1e-8,|q_base|,|q_fine|) <= 0.03`；
- exact-zero 指标继续使用其原有绝对阈值，不能改用相对误差获得通过；
- 参数、阈值、case 或 observable 均不得在看到响应后调整。

## 明确排除

不注册 periodic geometry，不改变 patch bounds 或细胞数，不运行 parameter sweep、
turnover、非零 `j_myo`、生理标定、论文图或外部科学结论。
