# `plan/` 外部专家指导库

本目录专门保存外部专家提供的指导方案及其可追溯信息，供项目执行前参照。内部研究计划、Codex 生成的执行计划、运行日志和结果不得进入本目录。

## 生命周期

- `incoming/`：已经收到，但尚未由用户确认采用；
- `active/`：用户已确认当前有效，或已有项目记录证明其约束处于有效状态；
- `superseded/`：被新版取代、撤回或终止，但仍保留历史证据。

允许的方案状态：

- `received`：已经接收，尚未审阅；
- `active`：原件和采纳状态完整，当前有效；
- `active_constraint_only`：已有生效约束，但原始专家文件或身份不完整；
- `superseded`：被新版取代；
- `withdrawn`：明确撤回；
- `unknown`：无法从现有记录判断。

## 标准方案包

每个方案包使用 `EXP-YYYYMMDD-topic-vNN/` 命名，并至少包含：

- `metadata.yaml`：方案 ID、主题、专家、接收日期、状态、适用范围、取代关系；
- `source/`：专家原始文件或缺失说明；
- `guidance.md`：忠实结构化转录或明确标注的摘要；
- `hashes.sha256`：原件或直接关联证据的完整性哈希。

原始文件一经登记即视为不可变。专家提供修订版时建立新版本包，并在 `INDEX.md` 中登记取代关系。

## 从指导到执行

`plan/` 中的材料不会直接触发代码修改或计算。每条建议必须先在 `project_control/` 中形成采纳记录，状态为 `accept`、`modify`、`defer`、`reject` 或 `needs_user_decision`，再转成范围、预算、验收标准和失败处理均明确的执行合同。

执行结果使用 `passed`、`failed`、`blocked`、`not_run`、`unknown`，并链接回方案 ID 和采纳记录。
