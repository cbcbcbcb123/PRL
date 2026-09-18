---
document_id: PRL-MIXED-CUBE-BENCHMARK-EXECUTION-V01
date: 2026-09-18
status: failed
scientific_qualification: not_run
SNES_calls: 0
container_invocations: 1
automatic_retries: 0
native_retest: not_run
next_execution_authorization: required
---

# 八工况基准：求解前接口失败，原始现场保留

用户授权：“确认执行八工况基准批次”。依据[已批准合同](ventricle_volume_qualification_adoption_v01.md)，
使用固定本地FEniCSx 0.11.0.post0镜像，一次容器、单CPU/8GiB/0GPU/禁网，最多1800秒。
实际14.443秒后退出2，无超时/OOM，未修复Docker、未拉取/安装/删除，未自动重跑。

**实现入口已建立，批次执行failed；八个平衡工况全部not_run，不是材料或网格收敛失败。**
第一个仿射patch在独立装配对照前读取原生表达式时抛错，尚未调用SNES。
不得因为实际求解次数为0而重新解释“一次容器”上限；再次运行需要新的明确确认。

| 范围 | 实际状态 |
|---|---|
| n=2/4/8三个输入网格 | 已登记；48/384/3072四面体 |
| 原生n=2网格与P2/P1映射 | passed；已导出实际结构 |
| 第一个非零patch表达式读取 | failed；hash不匹配 |
| 两个patch、六个MMS平衡/精度检验 | not_run；0 SNES、0平衡态 |
| 原失败保全及插值态独立读回 | passed；不是平衡验证 |
| 候选修订后宿主测试 | 46 passed；运行前44 passed |
| 候选修订后的原生症状消失 | unknown；未复验 |
| 原心室1%体积门/主动/生长/FSI | failed / not_run / not_run / not_run，全部不变 |

## 故障证据与最小修订

原报错：`Expression was created on a different mesh. Cannot tabulate.`。
[实际原生源码](evidence/mixed_cube_benchmark_v01/README.md)表明这是**坐标单元哈希**比较失败，
不能直接说已证实用了两张网格。FFCx对化简后无域表达式给出hash=0；两个仿射patch的解析体力恒为0。
因此“零体力化简丢失网格域”是高可信候选，但原日志未保存具体表达式key，归因仍unknown。
原JIT缓存位于易失tmpfs，未声称其被保全；只从已停止容器复制4份已安装源码作静态检查，无exec/start。

候选修订：两个patch体力改为绑定当前域的零Constant；MMS仍用−Div(P*)。
添加逐表达式编译hash与失败key。保持材料公式、所有载荷数值、求解选项、网格与验收门不变。
原心室被动能量仅原样抽出共享函数，宿主逐项数值等价测试通过；没有运行修改后的心室。
独立NumPy力学验证不导入生产本构；宿主通过不替代原生实现资格。

## 原始状态分类缺陷的显式更正

原`summary.json`将缺失的MMS序列也标记failed；原`post_verification.json`在没有平衡态时给出读回passed。
两份原件均不改写，新增`delivery_interpretation.json`说明：**收敛资格not_run，验证过的平衡态为0**。
未来汇总已修订，缺失序列不再伪装成实测精度失败；不完整序列为blocked。
`failure_state.npz`是解析位移插值、p=0的检查向量，J约1.00029942；不是求解结果或可重启心动状态。
没有伪造多时间点图；交付实际网格和执行统计，不产生无依据应力/形变图。

## 交付、保全与Git

[结果入口](../../PRL-results/ventricle_fem/mixed_cube_benchmark_v01_20260918/index.html) ·
[完整分层裁决](../../PRL-results/ventricle_fem/mixed_cube_benchmark_v01_20260918/delivery_interpretation.json) ·
[交付验收](../../PRL-results/ventricle_fem/mixed_cube_benchmark_v01_20260918/delivery_audit.json)。

外部包81文件、1,007,051 bytes；manifest记录80个载荷文件，SHA-256：
`5d3c7d623c4cb80404946a7bd04f1be104296b48ab0f213bb1a5b240c4b575fb`。
208个保护文件、50项既有无关修改及20份实际执行源码快照核验通过。
失败时源码与修订后源码分开保存，原始失败、合同和阈值不覆盖。无任务临时目录删除。
160dpi探索结构/执行图布局和目检passed；投稿600dpi检查两项failed照录，不冒充投稿终稿。
只按长期授权提交本地main，不推送；大型结果不进入Git。

## 唯一下一步：待确认的v02

建议一次确认**修订后同一八工况基准批次v02**：新create-only结果目录
`E:\Temp-Projects\PRL-results\ventricle_fem\mixed_cube_benchmark_v02_20260918`，不覆盖v01。
保持原合同八工况、门限、单CPU/8GiB/0GPU/禁网、一次额外容器、最多8次SNES及1800秒。
先逐表达式/装配/切线接口检查；通过才进入两patch及六MMS。任何接口失败停止，0自动重跑。
不包括心室重跑、薄层、主动、生长、FSI、安装或Docker修复。此提议当前not_run，尚未获新授权。
