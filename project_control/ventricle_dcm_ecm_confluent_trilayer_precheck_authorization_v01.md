---
document_id: PRL-VENTRICLE-DCM-ECM-CONFLUENT-TRILAYER-PRECHECK-AUTHORIZATION-V01
status: authorized
authorized_at: 2026-09-12
source: user_message
authorization_text: 确认，执行，尽快做出这三层结构
contract: project_control/ventricle_dcm_ecm_confluent_trilayer_precheck_contract_v01.md
---

# Z1-TF2-A 连续 DCM-ECM 三层预检授权 v01

用户在当前会话中确认执行已冻结的 Z1-TF2-A，并要求尽快形成心肌 DCM—连续闭合 ECM DCM—心内膜 DCM 三层结构。本记录据此授权一次 create-only、CPU 最多 4 线程、累计预检墙钟最多 600 秒的合成原语与几何预检，以及必要的 PRL 内运行器、验证器、真实网格图片、结果包和状态同步。

授权不包括修改 `E:\MeshCell3D\code\muse_dcm`、GPU、软件安装、网络下载、删除或覆盖既有结果、主动周期、完整 Z3/Z4、CFD、FSI、分裂、ECM 周转、提交、推送或外部发布。若现有唯一内核不能满足冻结原语，必须保存失败证据并停在 `blocked_dependency`。

