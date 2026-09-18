# PRL独立评审与复核材料｜2026-09-18

首先阅读：PRL_项目评审与提速建议_20260918.md。

- PRL_review_evidence.md：上传包的真实路径、源码/文档行号及必要摘录。
- PRL_review_audit_20260918.json：M0/M1保存态复算、附加投影缺陷指标、候选NPZ质量复核与完整性结果。
- prl_independent_audit.py：只读复算脚本，需要原评审ZIP解压目录、Python>=3.10及NumPy。以 --help 查看参数；输出必须位于原目录以外且不得覆盖。
- PRL_review_shape_tests.txt / .xml：本次实际执行的4项四面体质量测试结果。不是全项目132项测试复现。
- REVIEW_MANIFEST.json：本次评审交付文件的哈希清单。

本评审未启动FEniCSx生产求解、Gmsh、Notebook或完整项目回归测试。候选从已有NPZ复核，未重新解析MSH。没有更改原failed/not_run。

输入包SHA256：d4874e773bfebc8ac2604249430431b943bee5ca68789bfe9503009296eed3ea。
本次所有执行、停止与加速安排均为评审建议，不授权新生产计算，不修改用户现有合同。
