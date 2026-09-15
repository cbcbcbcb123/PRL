---
execution_id: EXEC-PRL-ROUTE-H-STAGE0-V06-V02-EOL-SEAL
source_freeze: FREEZE-PRL-ROUTE-H-STAGE0-V06
source_inspection: INSPECT-PRL-ROUTE-H-STAGE0-V06-V01
executor: Codex current task; single-worker deterministic evidence repair
started_at: 2026-07-31T10:17:00+08:00
completed_at: 2026-07-31T10:24:00+08:00
status: completed
resolved_finding: V06-EOL-SEAL-001
---

# Route H Stage 0 v06 v02 行尾封存修订记录

## 1. Finding

v06 v01 freeze 后检查 Git checkout 稳定性时发现：

- 系统 Git 配置为 `core.autocrlf=true`；
- 原 `.gitattributes` 只固定 JSON、Markdown、CSV 和 TXT 为 LF；
- Python、TOML、XML 没有显式 EOL 规则；
- v06 v01 freeze 当下包含部分 LF、部分 CRLF、部分 mixed-EOL Python 文件；
- 后续 checkout 可能把这些文件统一写为 CRLF，导致 freeze manifest 的 byte hash 变化，
  即使代码语义完全相同。

旧 Stage 1 v02 manifest 对未改 Python 文件记录的也是 LF hash，说明该问题会同时削弱历史
freeze 在 Windows checkout 后的可复核性。

该 finding 编号为 `V06-EOL-SEAL-001`，属于 evidence serialization blocking finding，
不是科学或数值 falsifier。

## 2. 修复

没有修改 v06 v01 freeze manifest、freeze record 或 inspection；它们保留为历史记录。

`.gitattributes` 新增：

```text
.gitattributes text eol=lf
*.py text eol=lf
*.toml text eol=lf
*.xml text eol=lf
*.bin -text
```

随后仅对 `src/`、`scripts/`、`tests/` 下的 Python/XML 与 `pyproject.toml` 做机械 LF
规范化；没有修改代码 token、JSON/CSV/Markdown 科学内容或任何 binary array。

## 3. 修复后检查

- Python/TOML/XML 中 carriage-return 违规文件：0；
- `.bin` Git attribute：`text unset`；
- v05 frozen Stage 0 inputs：hash match；
- coarse/base/fine deterministic replay：66/66 arrays byte exact；
- base 与 v05：22/22 arrays byte exact；
- v06 pytest v02：11/11 passed；
- Stage 1 regression：32/32 passed；
- Ruff：passed；
- v02 JUnit SHA-256：
  `FB85F8964E1BB56C220FAF142F6632FE5CA4F14B910DE7DC4504758B8686DF5A`；
- replay evidence SHA-256：
  `94A3F5CC41E9B0ECFCEB72618A99231A241C39FF2C17FDD000C0489C7FD8EB47`；
- `.gitattributes` SHA-256：
  `939FEA85AF90D59EEA64BCC0A9A7246CD8385831C5C65A21E2065EE660A92EED`。

v01 的三层 scientific metrics、proper-intersection closure、力/力矩和 steric 结论未因
纯 EOL 修复改变；v02 将重新封存规范化后的源码、测试、合同与同一 binary geometry。

## 4. 下一状态

生成 `FREEZE-PRL-ROUTE-H-STAGE0-V06-V02`，并在冻结后只读检查：

1. 全部 v02 manifest 文件 hash；
2. 所有冻结文本类型与 Git EOL attribute 的一致性；
3. binary `-text`；
4. v01 scientific metrics 与 v02 source/replay/test 证据的组合完整性；
5. Stage 2 scientific runs 仍为 0。

只有 v02 检查接受后才关闭该 finding 并进入 Stage 2 numerical lock。
