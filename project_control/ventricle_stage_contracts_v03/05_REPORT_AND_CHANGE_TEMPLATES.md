# Codex 报告、预登记和变更模板

模板没有实测数值。字段待实际运行填入；null、空表或 NOT_RUN 不能转成 PASS。真实 CLI/路径只有在实际存在并执行过后才能填写。

## 1. 阶段报告 report.md

```markdown
# <阶段 ID> 执行报告

## 状态和范围
- overall_status:
- physics_status:
- visualization_status:
- claims_status:
- 已完成子项:
- 未完成/阻断子项:
- 可以支持的结论:
- 明确不能支持的结论:

## 环境与输入
PRL/内核位置、提交/dirty 状态、硬件、单位、参数来源、随机种子、前置证据、预登记哈希。

## 实际执行
列真实命令、开始/结束、运行 ID、每次修复/重跑版本。区分 PILOT 与正式运行。

## 最重要结果
给原始数值、单位、参考值、误差、阈值和来源文件定位；不只说“趋势正确”。

## 可视化入口
离线 HTML、静态图、动画/视频或交互播放、原始数据、检查点、查看器测试截图。

## 独立验收
验证器实际命令和输出；空间/时间/迭代误差、守恒、对照及未解析项。

## 失败与限制
最后有效时刻、首次异常对象、失败包、原因证据、尚不能确认的内容。

## 代码修改和资源
修改文件清单、共享内核回归、CPU/内存/存储/总运行量与预算；保留用户修改的说明。

## 下一阶段合同
是否就绪、需要什么证据；未执行下一阶段。
```

## 2. 预登记最小字段

模板见 `templates/preregistration.template.json`。内容必须包含真实：方程/参数/关闭项、几何/单位、载荷、实验矩阵、网格/时间序列、观测区域、误差范数/非零参考尺度、阈值、求解策略、预算、输出频率、数据来源和版本。

流程为 `DRAFT → FROZEN → RUNNING → ACCEPTED/FAILED/STOPPED`，与运行状态分开。冻结哈希在正式结果前保存；修订创建新版本，不覆盖。若阈值靠预检选定，说明预检只用于尺度/预算/正确性摸底，不能用于事后调低正式标准。

## 3. 机器可读摘要

建议采用如下语义，不强制覆盖项目已有 schema：

```json
{
  "stage_id": "REPLACE_WITH_STAGE",
  "run_id": null,
  "overall_status": "NOT_RUN",
  "physics_status": "NOT_RUN",
  "visualization_status": "NOT_RUN",
  "claims_status": "NOT_RUN",
  "scope_passed": [],
  "excluded_claims": [],
  "completed_subchecks": [],
  "blocked_subchecks": [],
  "last_valid_time": null,
  "metrics_file": null,
  "viewer_path": null,
  "verification_log": null,
  "next_stage_executed": false
}
```

指标长表至少有 case_id、metric_id、value、unit、reference_scale、threshold、comparison、status、source_file、source_locator。记录“未计算”不是 value=0。一个主指标通过不自动覆盖所有必需子项。

## 4. 失败包模板

```text
failure_reason.md
minimal_config.json
last_valid_checkpoint/
first_invalid_snapshot/
residuals_before_failure.csv
geometry_or_contact_ids.csv
stdout_stderr.log
reproduce_commands.md
versions_and_environment.json
```

可视化同时标最后有效和首异常状态，首异常的数据类型/数值失效可见；不能只给一张漂亮最后帧。超预算也保存正常中止包，不当 crash 隐藏。

## 5. 模型/阈值变更请求 change_request.md

```markdown
# 变更请求 <ID>
当前阶段与原合同版本：
原定义/公式/阈值：
发现的问题与证据：
建议的新定义/公式：
为何不只是代码修复：
对能量、质量、参考态、对照和生物主张的影响：
受影响的历史结果/测试：
必要回归/重跑：
新增预算/依赖：
在获准前可继续的无关工作：
状态：等待用户决定；未执行语义变更。
```

只修复索引/符号等实现错误而不改变合同方程时，使用 bugfix 记录：旧最小失败、代码 diff、回归与新结果。不得把 bugfix 隐藏成原来就 PASS。

## 6. 最终回复合同

Codex 对用户的阶段结束回复必须给：精确状态/范围、真实离线结果入口、3 个最重要定量结果及单位、未完成/失败项、实际修改、下一阶段合同。不要只有“已完成”或十个文件名；也不要提交一篇新计划却不做授权工作。

没有开始计算时，定量结果只报告真实几何/资料审计指标；不得生成虚构模拟数值凑满三项。下一阶段是否可执行不等于已经执行。
