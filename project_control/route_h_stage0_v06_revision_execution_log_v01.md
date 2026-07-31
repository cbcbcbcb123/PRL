---
execution_id: EXEC-PRL-ROUTE-H-STAGE0-V06-DISCRETIZATION-V01
plan_id: PLAN-PRL-ROUTE-H-DCM-ECM-STAGE0-STAGE2-V01
authorization_id: DEC-PRL-ROUTE-H-STAGE0-V06-DISCRETIZATION-V01
executor: Codex current task; single-worker governed execution
started_at: 2026-07-31T09:35:21+08:00
completed_at: 2026-07-31T10:14:00+08:00
status: completed_with_repaired_prefreeze_findings
deviation_records:
  - V06-GEOMETRY-ADMISSION-001
  - V06-FLOAT-INTERFACE-SNAP-001
---

# Route H Stage 0 v06 空间离散族执行记录

## 1. 授权与执行边界

依据用户“批准 v06 方案，继续”的明确决定，执行 coarse/base/fine identity-bearing
geometry family 的生成、校验和待冻结证据构建。执行期间：

- Stage 2 scientific runs：0；
- active mechanism enabled：false；
- full-patch trajectory：未运行；
- periodic、turnover、非零 `j_myo`、parameter sweep：均未启用；
- v01–v05 与 Stage 1 v02 冻结文件：未修改。

采用受控单工作者流程；本记录不冒充人员独立复核。

## 2. 实现

### 参数化生成

- cell surface subdivision：coarse/base/fine = 1/2/3；
- ECM intervals：6×4×2、12×8×2、24×16×4；
- 三层各生成 22 个 canonical arrays；
- coarse/fine 使用确定性 vectorized nearest-ray 搜索；
- base 保留 v05 scalar 搜索，22 个数组与 Stage 1 v01 bundle 逐字节一致；
- 每层独立封存 face identity、anchor、material tether、source map、boundary owner、
  gauge weights 与 SHA-256。

### 合同与注册

新增 v06 geometry-family spec、contract、specialization、cases、空间验证协议和
verification registry。v05 的方程、无量纲机械参数、接触/黏附势、载荷、功率账本和
Gate A–E 顺序通过结构相等测试保持不变。

Stage 2 空间响应只注册 `E0_ZERO`、`E4_COMBINED`；比较 base/fine，非零关键量阈值
`<=3%`，exact-zero 指标沿用绝对阈值。

## 3. 预冻结 finding 与修复

### V06-GEOMETRY-ADMISSION-001

初次 coarse materialization 显示 myocardial–ECM 最大 reference natural gap 为
`0.06348416662201481`，超过 v05 针对唯一 base topology 的 `0.05` admission ceiling。

修复：在任何响应前，为 v06 三层冻结 `0.075` 的 geometry-only cell–ECM materialization
ceiling。该量不进入 energy、force、power 或 solver；逐对 `g0_pair`、`delta_g`、
接触/黏附势和所有机械参数均未改变。

### V06-FLOAT-INTERFACE-SNAP-001

初次完整 fine seal audit 得到 6 个有事件的 myocardial–ECM entity pairs。逐三角形定位
表明：解析上应位于 `z=0.2` 的极点被 binary64 写成
`0.19999999999999996`，使相邻 fine 三角形被误判为 transverse crossing。

修复：coarse/fine 在 identity/tether 生成前对相差不超过
`8*eps*max(1,|coordinate|)` 的解析 cell extrema 执行 reference-plane snap；
base 禁用该规则以保持 v05 byte identity。修复后：

- fine minimum myocardial z：`0.2`；
- fine proper intersections：0；
- coarse/base/fine steric energy：均为 0；
- base 22 arrays：仍全部 byte exact。

该修复只消除 one-ULP 几何歧义，不改变解析几何、拓扑、方程、参数或响应。

## 4. 检查结果

- v06 pytest：11/11 passed；
- Stage 1 regression：32/32 passed；
- Ruff：passed；
- deterministic replay：coarse/base/fine 各 22/22 arrays byte exact；
- family SHA-256：
  `EB29A59A17CC60CBE67E512B8E210F0052794B841504359A52CFE816AEBB6131`；
- family manifest SHA-256：
  `8E3F35BA8B69DD518D9EF4551D8791910F1AC260C3AE50A4B7211D5AEBDCBF0B`；
- metrics SHA-256：
  `C1656B2BCBF2979D72240B33DB6456DD76D419487D4C517DB3213585ECBBDBE1`；
- verification results SHA-256：
  `4E7B7D792992617BBDBE3ABD7144298FA97D02F4714B87B36EEE192D939D3565`。

| level | tethers | source maps | proper intersections | max tether force | net force | net moment |
|---|---:|---:|---:|---:|---:|---:|
| coarse | 468 | 144 | 0 | 1.879e-16 | 8.943e-31 | 1.972e-31 |
| base | 1828 | 504 | 0 | 2.732e-17 | 7.583e-31 | 2.911e-30 |
| fine | 7268 | 1944 | 0 | 1.672e-17 | 7.733e-31 | 1.171e-30 |

新版 registry 共 90 行：86 个 `passed`，4 个 Stage 2 response 项保持
`not_run_stage2_preexecution`；未继承或伪造 Stage 2 pass。

## 5. 输出与下一状态

v06 candidate 已达到冻结条件。下一步为生成 freeze manifest/record，然后进行单工作者
只读科学/代码检查。只有检查无 blocking finding，才允许关闭 PreStage2 block 并返回
Stage 2 Gate A。
