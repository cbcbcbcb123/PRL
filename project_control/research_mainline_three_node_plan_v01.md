---
plan_id: RESEARCH-MAINLINE-THREE-NODE-V01
status: approved
approved_by: human_final_reviewer
approved_at: 2026-08-12
executor: codex_primary_single_agent
inspector: human_final_reviewer
evidence_target: connect_scientific_mainline_before_parameter_refinement
---

# 三节点研究主线计划 v01

## Goal

在固定发育时期的快速心搏时间尺度上，按最小可解释复杂度逐级建立通用 DCM–FEM 动态耦合框架：

1. 可调控主动心肌细胞—黏弹性 cardiac jelly；
2. 心肌细胞层—黏弹性 cardiac jelly；
3. 心肌细胞层—黏弹性 cardiac jelly—心内膜细胞层。

当前优先级是先接通科学主线与跨层接口，再细化网格、参数、场量、收敛性和实验标定。每个节点完成后均设置人类图形审阅门，不自动进入下一节点。

## Shared Physical Spine

- 时间尺度：固定发育时期内的单个快速心搏周期；暂不加入生长、重塑、ECM 分泌和细胞增殖。
- 心肌：三维 DCM 表面细胞，轴向主动纤维优选长度由时变激活 `alpha(t)` 调控。
- cardiac jelly：三维四面体 FEM 连续介质，采用有限变形平衡支路与一个偏量黏弹支路。
- 细胞—ECM：材料点 tether 传递法向黏附和切向牵引，保留作用—反作用与力矩审计。
- 动力学：忽略惯性；每个时刻满足机械平衡，cardiac-jelly 内变量保留跨时刻记忆。该“动态”指历史相关的非线性黏弹响应，而非惯性振动。
- 当前单位：归一化模型单位。实验标定前不把应力标为 Pa/kPa，不把周期标为秒。

## Node 1 — 可调控细胞与黏弹性 ECM

### Scientific question

一个主动收缩强度可控的心肌细胞，如何通过单侧界面把周期性载荷传入具有有限松弛时间的 cardiac jelly，并产生相位滞后、迟滞和非负耗散？

### Minimum implementation

- 复用已通过固定拓扑审计的单细胞—三维 ECM 几何和接触接口；
- 将 `mu_ve=0` 升级为 `mu_ve>0, eta_ve>0`；
- 采用一支有限应变黏弹内变量：

  `W = W_eq(F) + mu_ve/4 * ||dev(C_bar)-Z||^2`

  `Z_dot = mu_ve/(2*eta_ve) * [dev(C_bar)-Z]`

  `tau = 2*eta_ve/mu_ve`；

- 使用平滑 `0 → alpha_peak → 0` 单周期激活；
- 使用交错隐式更新：固定 `Z` 求细胞—ECM 平衡，再按当前变形精确松弛 `Z`，迭代至耦合残差满足门限。

### Pilot acceptance

- 完成一个离散单周期并覆盖激活峰值与舒张末期；
- 每个节点细胞体积误差 `<=1e-8`、ECM `J>0`、最小 gap `>=-1e-12`；
- 界面 pair force/moment 残差 `<=1e-10`；
- 黏弹内变量保持对称、无迹，离散耗散非负；
- 输出至少四个时相的三维细胞—ECM 状态图，以及激活—缩短、界面力—缩短和耗散曲线；
- pilot 只证明主线连通，不声称时间步、网格和材料参数收敛。

### Human gate

人类终审查看 Node 1 阶段图后，决定保留、缩小、修订或停止该动力学路线。未经该门批准，不启动 Node 2。

## Node 2 — 心肌细胞层与黏弹性 ECM

### Scientific question

细胞间力学协调、激活同步性或传播延迟如何改变 cardiac-jelly 中的载荷扩散、局部应力集中和周期耗散？

### Minimum implementation

- 将单细胞复制为具有明确邻接关系的一层 DCM 心肌细胞；
- 增加细胞—细胞连接，并保持每个细胞独立体积约束和材料身份；
- 支持同步激活和最小的空间相位延迟；
- cardiac jelly 仍为连续三维 FEM，避免把 ECM 人为切成逐细胞独立块；
- 首先只做小尺度细胞层，不进行组织尺寸外推。

### Human gate

阶段图必须同时显示细胞层时相、ECM 三维场和空间同步/不同步读数。人类批准后才进入 Node 3。

## Node 3 — 心肌—ECM—心内膜结构

### Scientific question

主动心肌外层通过近似不可压缩且黏弹的 cardiac jelly，如何驱动可弯曲的心内膜层位移、间距重排和折叠倾向？

### Minimum implementation

- 在 cardiac jelly 另一侧加入一层 DCM 心内膜细胞；
- 分别定义心肌—jelly 与心内膜—jelly 的材料连接；
- 定义局部层间距 `h(s,t)`、心内膜曲率/折叠代理和 jelly 体积变化；
- 首轮不加入血流；腔内压力只作为后续可选边界条件；
- 在三层固体结构通过后，再决定是否耦合流体。

## Implementation Steps

1. 完成 Node 1 黏弹本构的状态传递接口与单周期求解器。
2. 完成 Node 1 最小测试和低成本主线 pilot。
3. 生成 Node 1 四时相三维状态图和动力学诊断图。
4. 在人类图形审阅门停下。
5. 获得批准后，单独起草 Node 2 几何、细胞连接和激活传播合同。
6. Node 2 通过后，单独起草 Node 3 双界面和层间距合同。

## Test Plan

- 黏弹内变量更新的对称性、无迹性、松弛极限和非负耗散；
- 指定 `Z` 时 ECM 能量—力方向导数检查；
- 单周期激活节点与周期端点检查；
- 每步机械平衡、体积、gap、Jacobian、界面 pair force/moment 检查；
- 后续精化阶段再做时间步、网格、松弛时间和材料参数收敛。

## Risks

- 单周期 pilot 的相位和耗散依赖未标定的 `tau/T`；只能作机制演示。
- 交错耦合存在时间/耦合离散误差；需在主线连通后做精化。
- 单侧 ECM 远端固定边界会影响柔顺性；Node 1 只用于建立接口，不代表完整在体边界。
- Node 2、Node 3 的细胞数量和连接拓扑必须另行依据影像或实验约束，不能从单细胞直接外推。

## Out Of Scope

- 发育时间尺度的生长、重塑、ECM 分泌或 EFE 病变演化；
- 心腔血流、流固耦合和压力标定；
- 在 Node 1 主线 pilot 中追求最终网格/时间步独立性；
- 在实验标定前给出物理单位下的定量预测。

## Required Record

Node 1 完成后记录实际本构参数、离散方案、数值门、阶段图和所有证据边界；Node 2 与 Node 3 的实现必须分别获得新的人类阶段授权。
