---
document_id: PRL-REPOSITORY-CLEANUP-BATCH04-CANDIDATE02-EXECUTION-V01
status: passed
recorded_at: 2026-09-15
implementation_status: safe_slice_passed
application_migration: not_run
storage_gate: blocked
scientific_execution: not_run
deletion_executed: false
---

# Batch 4 候选2无物理C++支撑库安全切片执行记录 v01

## 结论

用户确认的候选2安全切片已完成。新增项目自有静态库 `prl_ventricle_support`，只包含 `Vector3`、轻量三角表面网格值类型、带边界检查的文本网格读写、CSV转义和版本化结果表schema。该库不依赖SimuCell3D类型，不包含接触、材料、主动载荷或积分器实现。

本次 `passed` 只表示新支撑边界能够编译，并与一个保留双胞网格和六张保留结果表的格式一致。现有应用尚未切换到该库，8个应用包含旧`.cpp`的问题仍然存在；因此不能把本切片写成候选2完整迁移完成。

## 现场保护与变更

- [实施前基线](evidence/repository_cleanup_v01/batch04_candidate02_source_baseline.json)冻结2个被包含实现和8个应用入口，共10个文件的字节数与SHA-256。
- 新增 `src/prl_ventricle_support/`，共8个源码/构建文件、16,044 bytes。
- 修改 `src/ventricle_simucell3d_m0/CMakeLists.txt`，只加入新库和合同测试子目录；没有让任何旧应用链接新库。
- 新增 `tests/prl/test_cpp_support_boundary.py`，持续检查新库不依赖内核、10个旧源哈希不变、旧应用没有被静默切换。
- 新增本执行记录与[机器验收记录](evidence/repository_cleanup_v01/batch04_candidate02_acceptance.json)。

没有修改10个冻结旧实现/入口、`external/simucell3d`、力学方程、材料参数、阈值或结果文件。没有删除、安装、GPU、Docker或外部服务。

## 构建边界

当前仓库超过3 GiB硬上限，科研运行继续`blocked`。本切片是用户在知晓该状态后明确确认的清理迁移；只复用既有 `b/z1m0a`，不创建新构建目录。构建前该树为51,295,019 bytes，验收后为52,594,779 bytes，新增1,299,760 bytes。

只构建：

```powershell
cmake -S src/ventricle_simucell3d_m0 -B b/z1m0a
cmake --build b/z1m0a --config Release --target prl_ventricle_support_contract_test --parallel 2
ctest --test-dir b/z1m0a -C Release -R '^prl_ventricle_support_contract$' --output-on-failure
```

没有构建或运行科研求解目标。原`prl_myo_contact_barrier_probe_v01.exe --geometry-self-test`只运行既有无输出几何自检。

## 验收

| 检查 | 状态 | 结果 |
|---|---|---|
| 新静态库与测试目标 | `passed` | MSVC Release构建成功；CTest 1/1 |
| 值类型/网格I/O | `passed` | 向量运算、零向量拒绝、网格往返、非法face索引拒绝 |
| 保留真实网格 | `passed` | END双胞输入读取为2胞，每胞194节点/384面 |
| 结果schema | `passed` | `nodes/faces/states/cells/step_audits/separation`六表表头逐字一致 |
| 新库依赖边界 | `passed` | 无SimuCell3D头文件、外部路径或旧`.cpp`实现包含 |
| 旧实现身份 | `passed` | 实施前基线10/10哈希一致；长程冻结来源13/13一致 |
| 旧几何/接触回归 | `passed` | 几何自检通过；选定正间隙、力平衡和折叠监测回归合并18项Python测试通过 |
| 科学状态 | `not_run` | 没有新模拟；静态平衡继续`failed`，父Z1/生物验证继续`blocked` |

首次对真实保留表做schema测试时，新定义把`faces.csv`误写为`cell,a,b,c`，测试立即`failed`；只修正新库为实际的`cell,face,a,b,c`后重建，最终通过。旧源和旧结果均未改动。这一失败保留在本记录和机器验收中，不能被最终绿灯隐藏。

## 未完成与下一门

- 现有8个应用仍通过重命名`main`包含旧`.cpp`；应用迁移为`not_run`。
- 新库当前只是经真实格式验证的迁移seam，不拥有接触、材料或时间推进。
- 没有证明性能改善，也没有形成新的科学结果。

按已采纳顺序，下一步应是候选4的第一安全切片：建立当前quick suite和严格import/路径检查，保留旧测试文件原位；默认测试切换和代码删除继续后置。任何删除仍需新的精确清单与确认。
