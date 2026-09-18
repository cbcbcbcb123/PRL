---
document_id: PRL-FEM-MIXED-LINEAR-DIAGNOSIS-EXECUTION-V01
status: completed_with_failed_delivery
executed_at: 2026-09-18
contract: project_control/ventricle_fem_mixed_linear_diagnosis_contract_v01.md
result_root: E:/Temp-Projects/PRL-results/ventricle_fem/f6s1s_linear_system_diagnosis_v01_20260918
---

# F6-S1-S 混合线性系统诊断执行记录

## 裁决

- **受控执行：failed。** 唯一一次诊断容器返回2；没有自动重跑。
- **独立事后复核：passed。** 正式调用文件、F6-S1-R源包和受保护父证据均未变化，保存的CSR可独立读取和复算。
- **诊断交付：failed。** 程序完成矩阵组装以及各一次MUMPS、SuperLU尝试后，在写`diagnosis.json`时遇到非有限浮点值；严格JSON拒绝`inf`，因此KSP、PC、MUMPS INFOG及SuperLU结果没有持久化。
- **根因确认：not_evaluable。** 证据支持“混合块严重尺度差/小主元”假设，但不足以把它标记为已经确认的MUMPS根因。
- **科学状态不变：failed。** DG2受压平衡仍不存在；轮廓、三维、FSI、生长和ECM反馈均未运行。

## 实际执行

- 输入：F6-S1-R理想圆环M0（896个三角形）的零载接受态及`p/mu=0.02`失败初值。
- 离散：二维平面应变，P2位移/DG2逐单元压力，`mu=1`、`kappa=1000`，六阶积分。
- 边界和载荷保持原合同：内壁随动压力0.02；外壁自由；3个位移自由度用于去除刚体运动；主动张力为0。
- 资源：固定FEniCSx镜像，单CPU、8 GiB、禁网、只读项目挂载、0 GPU。
- 次数：1次容器、1次切线组装、1次MUMPS线性步尝试、1次SuperLU交叉尝试、0次非线性平衡求解、0次自动重跑。
- 容器墙钟16.327秒；所有容器隔离检查通过，375个受保护父文件及76个F6-S1-R结果文件身份保持。

## 已保存矩阵证据

独立复算`matrix_csr.npz`得到：

| 指标 | 结果 |
|---|---:|
| 混合系统阶数 | 9,216 |
| 非零元 | 245,760 |
| 位移/压力/固定DOF | 3,840 / 5,376 / 3 |
| 非有限矩阵或残量值 | 0 |
| 结构秩 | 9,216（满结构秩） |
| 零行 / 零列 | 0 / 0 |
| 相对非对称误差 | 1.15905e-16 |
| 右端范数 | 0.008667040857 |
| `uu` / `pp` Frobenius范数 | 574.1033 / 1.83059e-5 |
| 单元压力块最小 / 最大奇异值 | 2.78956e-8 / 6.48058e-7 |
| 最大对角 / 最小压力奇异值 | 3.72054e8 |
| `uu` / `pp`块范数比 | 3.13616e7 |

每个三角形有6个DG2压力自由度，但初始态局部`p-u`耦合秩均为3；896个单元至少有2,688个高阶压力模态只受有限体积模量压力块约束。该压力块逐单元满秩，因此排除了结构零行、结构秩亏和单元压力质量块本身奇异；同时约`10^7–10^8`的块尺度差支持小主元/数值尺度风险。

## 为什么没有确认求解器根因

执行脚本先完成矩阵保存，再调用SuperLU与MUMPS，最后一次性写报告。保存报告时抛出：

`ValueError: Out of range float values are not JSON compliant: inf`

独立复算的所有矩阵指标均有限；执行时的SuperLU条件数估计也已有非有限保护。因此可把未序列化的`inf`定位到MUMPS报告子树，但无法恢复它究竟来自解范数、相对残量还是某个`RINFOG`字段。也无法恢复KSP reason、PC failed reason、MUMPS `INFOG(1/2)`或当次SuperLU成败。后处理没有再次因子化，避免把重复尝试伪装成独立验证。

序列化代码已修正为把`NaN/+Inf/-Inf`显式写成字符串并有回归测试；这个工程修正没有用于重跑，也没有改变本构、离散、材料或门限。

## 证据边界

- `post_verification.json`通过只表示保存矩阵及执行边界可审计，不把原诊断执行改写成passed。
- 满结构秩不等于数值条件良好，也不证明代数满秩；单元压力块满秩不等于P2/DG2满足严格不可压极限的inf-sup条件。
- F6-S1-R零载态0次Newton更新，因此此前的零载passed从未实际证明该DG2矩阵可由MUMPS分解。
- 未保存诊断后状态，故“因子化后状态逐字节未变”记为not_evaluable；但本轮没有调用SNES或NonlinearProblem的solve入口，也没有生成新平衡态。

## 下一步

若用户批准，下一切片只重放这一矩阵诊断一次，使用已修正的非有限值序列化，获取KSP/PC/MUMPS及SuperLU明细；仍不做平衡求解、不更新状态、不改变材料、几何或1%门。取得明细后再决定是否测试块缩放或局部压力静态消元，不能直接跳到新科学工况。
