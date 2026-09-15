# PRL 心室路线 Z0 执行记录 v01

- 执行日期：2026-09-11
- 授权：`project_control/ventricle_z0_execution_authorization_v01.md`
- 合同：`plan/active/PRL_Codex_Stage_Contracts_v03/stages/Z0_ENTRY_DATA_AND_KERNEL_AUDIT.md`
- 结果包：`results/ventricle_z0/v01_20260911/`
- 总状态：`PASS`（仅静态几何、资料审计与可视化范围）
- 物理状态：`PASS_STATIC_GEOMETRY_ONLY`
- 可视化状态：`PASS_LOCALHOST_BROWSER_SMOKE`
- 主张状态：`BLOCKED_DATA`
- 下一阶段：Z1 `NOT_RUN`，未授权

## 实际执行

在 CPU/4 线程上使用 `E:/MeshCell3D/code/muse_dcm` 2.1.0（Git `fa21321b...`）生成单细胞、双细胞和每层 4×4 个细胞的双层片，共 35 个闭合细胞。每细胞 162 节点、320 三角面。没有启动 GPU，没有运行力学、主动、ECM、CFD、FSI 或分裂。

小文件下载累计 11,850,076 bytes：Glasgow 两个 GFP z-stack、作者 GitHub 的一个速度快照及其 README/渲染/配置脚本、Zenodo read-me 与边界追踪脚本。下载脚本均未运行；大包未获取。

## 验收

- 开边/非流形边、反向面、退化面、重复面与凸性违规：35 个细胞合计均为 0。
- 最小三角角：54.397012°，通过冻结门 20°。
- 有向体积与独立 ConvexHull 体积最大相对差：`1.4543002658726643e-15`，通过冻结门 `1e-10`。
- 独立验证器：PASS；pytest：4 passed；CB 定量图样式：PASS；修订后人工视觉 QA：PASS。
- 浏览器：同一离线文件经临时 `127.0.0.1` 只读预览测试，场景、投影、透明度、z 剖切和对象选择通过，控制台无错误。直接 `file://` 因浏览器安全策略被拦截，未将该受限路径伪写为通过。

## 解释边界

公开图像与速度快照未完成共同注册，fish ID、hpf、条件、完整体素信息和实验细胞膜仍缺失。因此实验子项保持 `PARTIAL_BLOCKED_DATA`，不支持生物标定、拟合或验证主张。完整报告见 `results/ventricle_z0/v01_20260911/report.md`。
