---
document_id: PRL-EXTERNAL-RESULT-STORE-EXECUTION-V01
status: passed
scope: storage_engineering_only
scientific_execution: not_run
date: 2026-09-17
---

# 独立结果库工程验收

用户明确批准`E:\Temp-Projects\PRL-results`作为后续结果库；按
[存储决定](external_result_store_decision_v01.md)建立根目录与说明，接入当前FEniCSx轮廓运行器、
保存态读取和`python -m prl storage status`。旧结果不复制、不搬移、不删除；不建立第二套内核或Git仓。

## 实际检查

- 两轮主机JSON写入、一次固定本地镜像的Docker读写均passed。实际`/out`只挂载
  `E:\Temp-Projects\PRL-results\_storage_checks\external_store_io_v01`；项目源码只读。
- 容器单CPU、8 GiB内存、只读根、禁网、0 GPU，0拉取/安装/更新/科学求解/自动重试。
- 162个源码文件在I/O测试前后相同，571个既有FEM文件按历史清单哈希通过；
  外部测试manifest和代码仓小型索引相互核对。测试数据及退出容器保留，不执行清理。
- 路径越界、已有阶段防重跑、磁盘安全底线和超过800 MiB仍可准入均有独立单元测试；
  完成阶段在Docker调用之前拒绝运行。
- 64项回归测试及21项子测试passed；24个HTML链接及321个证据路径均有效。
  50个无关既有文件哈希保持。验收时仓库逻辑占用2,033,861,104 bytes（约1.894 GiB），
  外部结果库1,608 bytes，E盘剩余2,227,740,475,392 bytes；后续提交的元数据会产生少量增量。

证据：[真实I/O记录](evidence/external_result_store_v01/execution.json)、
[Docker检查](evidence/external_result_store_v01/container_inspect.json)、
[最终哈希与导航复核](evidence/external_result_store_v01/delivery_audit.json)。
回归命令及计数见[测试记录](evidence/external_result_store_v01/tests.json)，工程测试不能替代科学资格。

## 生效规则和未改变事项

新结果没有固定256/800 MiB阶段容量上限。启动前要求“可用磁盘>=预计新增量+停止保全空间+10 GiB”；
停止保全至少64 MiB，未来状态更大时须相应提高。运行中检查实际余量，不自动删除旧证据。
代码仓仍3 GiB硬限，外部结果单独统计；普通Git提交只包含源码、决定和小型索引。
公开原始大数据继续按原授权放E:\Data。

已完成阶段的历史配置和失败不改写。旧路线不批量改造；本次没有用新目录重跑任何科学阶段。
F6-S1-P仍为局部J门failed；后续细网格两态诊断为not_run，须有新的科学合同和授权。
未来阶段的最终打包/绘图及索引冻结须在该阶段端到端验收，本次只证明存储接口与I/O可用。

本次修改直接本地提交main，不推送GitHub；50个无关既有改动及已有执行锁保留。
无删除、无旧结果迁移、无Docker运行时修复、无虚拟盘映射。
