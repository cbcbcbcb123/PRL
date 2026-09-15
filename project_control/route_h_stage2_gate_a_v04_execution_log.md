---
execution_id: EXEC-PRL-ROUTE-H-STAGE2-GATE-A-CURVATURE-MEMORY-V04
contract_id: CONTRACT-PRL-ROUTE-H-STAGE2-GATE-A-CURVATURE-MEMORY-V04
executor: Codex current task
started_at: 2026-08-09T17:34:31.878591+08:00
completed_at: 2026-08-09T17:35:52.845255+08:00
status: completed_failed_gate
formal_gate_status: failed_invalid_numerics
deviation_records:
  - "首次外层启动器误设 1 秒超时，Python 在创建 v04 输出目录前被终止；核对无进程、无文件、无 response 节点后，以同一冻结入口和充分外层时限启动唯一正式套件"
---

# Route H Stage 2 Gate A M1 v04 执行记录

## 批准范围与唯一修改

用户于 2026-08-09 要求继续任务，本轮按
`route_h_stage2_gate_a_v04_curvature_memory_contract.md` 执行。M1 v03 的力学、几何、参数、时间离散、候选验收语义与 `1e-8` residual 门槛全部保持不变；唯一数值修改是把 L-BFGS-B 的 `maxcor` 从 20 增至 40。

## 预注册前只读预检

冻结 step 86 的单变量预检显示：单独收紧 `gtol`、增加 `maxls` 或 `maxiter` 均不能越过该点；只有 `maxcor=40` 在第 88 次目标评估达到 residual `9.455399901e-9`。该预检不落盘、不进入 response 指标，已在任何 v04 正式轨迹前登记于合同。

## RED–GREEN 实施

- RED：新增公共行为测试，要求 `A1_ACTIVE, dt=0.02` 到达 `t=1.72`；v04 模块不存在时按预期 collection failure；
- GREEN：从 v03 建立独立版本化入口，仅把 `maxcor` 改为 40；step 86 完整通过 residual、gauge、严格增量势下降和几何门槛；
- 回归：v03 与 v04 针对路径测试 `2/2` 通过；最终 `tests/stage2` 为 `8/8` 通过。

## 正式套件结果

正式 runner 按 A0、A1 coarse/base/fine 顺序 fail-fast：

1. `A0_ZERO_dt0.01` 完整到达 `t=5.0`，500 步零响应；
2. `A1_ACTIVE_dt0.02` 成功越过原 v03 step 86，并接受到 step 193、`t=3.86`；
3. step 194、`t=3.88` 的返回候选 residual 为 `1.199104775e-8 > 1e-8`，因此状态为 `failed_invalid_numerics`；
4. 按合同停止，未运行 `dt=0.01` 与 `dt=0.005`，因此无 time-refinement 证据，Gate A 未通过。

最后接受状态 `t=3.86` 的 activation 为 `0.4759%`，轴向缩短 `0.7469%`，两个横向尺度变化为 `+2.4212%` 和 `-0.2271%`。整条已接受轨迹峰值轴向缩短为 `9.7809%`，最大绝对体积误差仅 `0.01586%`。

新失败候选保持有限、正体积、0 翻面、0 退化面；relative volume 为 `0.999902226`，最小面面积比 `0.521023`，最小方向余弦 `0.998328`。因此这仍是求解器残差门槛失效，不是细胞几何崩坏或体积异常。

## 图形产物

从正式 v04 输出建立
`results/route_h/stage2_gate_a_v04/Figures/FigM1_v04_cell_state_progress/FigM1_v04_cell_state_progress_v01_20260809/`：

- A 面板为 t=0、峰值激活 t=2、峰值缩短 t=3 和最后接受 t=3.86 的同相机三维细胞状态；
- B 面板为激活、轴向缩短和两个横向尺度变化；灰色区明确标识 t=3.88 后未接受、未模拟；
- 真实数据、模型快照、Notebook、render helper、methods、600 dpi PNG、可编辑文字 SVG 和统一风格 manifest 均保留；
- Notebook 自动执行与版本包校验通过，CB 统一风格校验通过，代理目视检查通过；版本仍等待用户终审，未标记 final。

## 验证

- `pytest -q tests/stage2`：`8 passed`；
- Ruff：v04 solver、test、runner 与 figure renderer 全部通过；
- v04 JSON、CSV、accepted/rejected 数组均有限且节点数一致；
- failure candidate 与最后接受状态分离；
- M1 v03 failure manifest `51/51` 路径、bytes 与 SHA-256 保持一致；
- 正式 suite manifest 明确记录方程、参数、时间步和阈值均未改变。

## 结论与边界

M1 v04 证明增加曲率记忆可以修复原 step 86，并把有效轨迹推进 2.16 个模拟时间单位至 `t=3.86`，覆盖激活上升、平台和大部分舒张回程；但完整 5 秒轨迹与时间步自洽性仍未建立，因此 Gate A 状态保持失败。该结果不支持生理力值、真实前/后负荷、ECM/血流耦合或发育机制 claim。
