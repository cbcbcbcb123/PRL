---
document_id: PRL-VENTRICLE-Z1B-EXECUTION-AUTHORIZATION-V01
status: authorized
authorized_at: 2026-09-11
scope: z1b_reference_state_only
contract: project_control/ventricle_z1b_reference_state_contract_v01.md
---

# Z1-B 参考态实现与验证授权 v01

## 用户明确授权

用户于 2026-09-11 明确确认：

> 确认允许修改 E:\MeshCell3D\code\muse_dcm，为Z1-B实现参考态；PRL中不复制第二套内核，仅保存合同、验证脚本和结果。

## 允许

- 修改唯一 E:\MeshCell3D\code\muse_dcm 内的通用参考态数据结构、力—能量实现、配置读取和聚焦测试；
- 在 PRL 内新增 Z1-B 合同、CPU 验证脚本、新版本结果包、独立验证、图片和状态记录；
- CPU 最多 4 线程、墙钟最多 600 s 的 Z1-B 参考态验证。

## 不允许

- 在 PRL 复制第二套 DCM 内核；
- 启动 GPU、安装/升级软件、删除任何文件或目录；
- 执行 Z1-C、多细胞拥挤桥接、Z2 或后续阶段；
- 提交、推送、发布或把合成比例解释为真实生理标定。

