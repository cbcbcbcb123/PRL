---
document_id: PRL-VENTRICLE-Z1C-EXECUTION-RECORD-V01
status: superseded_by_contact_repair_execution_record_v02
executed_at: 2026-09-11
stage: Z1-C
substage_status: FAIL_NUMERICAL
parent_stage_status: BLOCKED_DEPENDENCY
---

# Z1-C 受控双细胞接触执行记录

> 该记录保留修复前 `FAIL_NUMERICAL` 证据。当前前向裁决见 `ventricle_z1c_contact_repair_execution_record_v02.md`；本记录中的失败不得覆盖修复后的 v07，但继续作为诊断谱系保存。

## 1. 授权与范围

用户在同意 Z1-C 后补充要求：“同意，最好在网格上标记出曲率，应力，压力等力学量”。本轮依 [Z1-C 合同](ventricle_z1c_controlled_contact_contract_v01.md) 在 CPU/4 线程、0 GPU、0 网络、0 安装条件下执行球形对照、心肌端对端/侧对侧、心内膜边对边/面对面五条规定路径。

`E:\MeshCell3D\code\muse_dcm` 是唯一计算内核，本轮按只读策略使用，Git HEAD 为 `fa21321b80a371f107afd398f93d7f69508e20c6`；没有复制第二套内核，也没有修改 MeshCell3D 源码。

## 2. 最终裁决

最终 create-only 结果包为 [z1c_v06_20260911](../results/ventricle_z1/z1c_v06_20260911/index.html)，Z1-C 为 **FAIL_NUMERICAL**。独立验证为 `PASS_VERIFICATION`，其含义只是完整复现失败分类，不是科学通过。父 Z1 保持 **BLOCKED_DEPENDENCY**；多细胞桥接与 Z2–Z11 均未运行。

通过的冻结门：接触分段定律、远距零力、黏附/排斥均被激活、合力/合矩与逐对作用—反作用、ID 交换、加载—卸载可逆、体积、压力公式、机械场有限性、可视化和预算。

失败的冻结门：

- 工作共轭最差最佳相对误差 `7.238856e-5`，高于 `1e-5`；
- medium→fine 峰值反力最大变化 `0.8127104`，高于 `0.05`。

其余关键量包括：最大平衡误差 `2.305834e-16`，最大体积相对变化 `5.000000e-4`，最大压力公式误差 `0`，最大细胞压力 `3.000750 Pa`。

## 3. 失败诊断

[独立诊断](../results/ventricle_z1/z1c_v06_20260911/diagnostics/diagnosis.md) 进一步隔离了两个失败来源：

- 固定形状、只作刚性相对平移时，接触能量—力误差至多 `4.498896e-13`；
- 允许面片面积随形变变化时，当前面积加权的接触能量误差升至 `7.180530e-5`；冻结面积权重后误差恢复至 `1.520749e-12`。因此，当前接触力没有包含重建能量中当前面片面积变化的导数项；这不是差分步长假象。
- 在零压缩、纯平移探针中，medium 与 fine 仍有多个非球形方向出现反力变号，且活动 node–face 对数与最小有符号距离随细化剧烈变化。因此，网格失败来自当前 node–face 采样/接触面积离散，不是 `5e-4` 小压缩造成的。

本诊断只定位机制，不授权或实施内核修复。

## 4. 网格力学场

最终图直接在保存的 medium 三角网格上显示：

- 内核离散曲率，单位 `µm^-1`，全包最大值 `2.286912 µm^-1`；
- 参考度量产生的二维膜力合量，单位 `N/m`，全包最大值 `2.129460e-7 N/m`；
- 细胞压力，单位 `Pa`，峰值状态为细胞内均匀标量，最大值 `3.000750 Pa`；
- 面均节点接触牵引，单位 `Pa`，节点场全包最大值 `538.218956 Pa`。

当前壳模型没有厚度参数，因此“应力”没有被伪装成三维 Cauchy 应力 `Pa`；交付的是物理可定义的二维膜力合量 `N/m`。Z1-C v05 的压力图曾把约 `1e-12 Pa` 的浮点差放大到全色阶，已原样保留并记录；v06 改用从零开始的共同物理量程并标明 `cell-uniform`，数值计算未改变。

## 5. 证据与核验

- runner：`scripts/run_ventricle_z1c_v06.py`，SHA-256 `becfbe60376390a8090d0dc0ec9bca7c00e358b1826f183df76b33d4601c3e41`；
- 诊断器：`scripts/diagnose_ventricle_z1c_v02.py`，SHA-256 `f754026fdf87138803d548aa90f55c672316ee78b75d63391f4dee84d936bf37`；
- 独立验证器：`scripts/verify_ventricle_z1c_v06.py`，SHA-256 `45bcb53cfd2cf06ea196a16639700eda3c8723e9d91ef720fa905b7ce41c57db`；
- 两张定量图的 CB 统一样式清单分别验证为 `PASS`，均为 `10 × 5 in` 轴框、600 dpi；
- 四张最终图已人工检查，记录见 `results/ventricle_z1/z1c_v06_20260911/visual_qa.json`；
- Z0、Z1-A、Z1-B、Z1-C 共 20 项相关回归测试通过。

Z1-C v01–v04 的实现/绘图失败包、v05 的数值失败及首次压力图均保留，未覆盖、未删除。

## 6. 下一步边界

不得进入 `Z1-MULTICELL-BRIDGE` 或 Z2。下一最小工作应先形成一个待用户授权的 MeshCell3D 接触离散修复合同，至少同时处理：

1. 接触能量与当前/参考面积度量的一致选择及完整变分；
2. node–face 接触积分在 80/320/1280 面网格上的客观收敛与避免重复/漏采样；
3. 修复后的球形、两种心肌方向和两种心内膜方向全矩阵回归。

只有修复后重新满足原冻结门，Z1-C 才能重新裁决；不能通过提高阈值、只保留球形或进入多细胞拥挤来绕过失败。
