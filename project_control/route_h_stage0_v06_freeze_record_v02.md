# Route H Stage 0 v06 v02 冻结记录

## 冻结结论

- freeze ID：`FREEZE-PRL-ROUTE-H-STAGE0-V06-V02`
- frozen at：`2026-07-31T10:26:00+08:00`
- status：`frozen_pending_readonly_inspection`
- supersedes：`FREEZE-PRL-ROUTE-H-STAGE0-V06`
- resolved：`V06-EOL-SEAL-001`
- frozen files：103
- package SHA-256：`4066D1BBEBCEA8996D4F9547B7AFDD21037F8B78BACE94E9549A41F89FE3E9F9`
- manifest SHA-256：`392FB910125D73009ACB69BFBCC0A8206D83D2A388E633F5E0A4332DF88AE1A4`
- family SHA-256：`EB29A59A17CC60CBE67E512B8E210F0052794B841504359A52CFE816AEBB6131`
- v05 base 22 arrays byte exact：`true`
- Stage 2 scientific runs before freeze：`0`

## v02 修订

Python、TOML、XML 与 `.gitattributes` 现全部由 Git attribute 固定为 LF；
binary `.bin` 全部固定为 `-text`。v02 freeze 的全部文本文件 carriage-return
违规数为 0，attribute 违规数为 0。

## 证据

- v02 pytest：11/11 passed；
- Stage 1 regression：32/32 passed；
- deterministic replay：66/66 arrays byte exact；
- v01 scientific metrics：hash 不变并由 v02 重新封存；
- coarse/base/fine proper intersections：0 / 0 / 0；
- coarse/base/fine steric energy：0 / 0 / 0；
- registry：86 passed，4 `not_run_stage2_preexecution`。

## 不变性

v02 只修复跨-checkout byte stability；v06 v01 scientific geometry、binary arrays、
contract、parameters、reference metrics 和 Stage 2 authorization boundary 均未改变。
本记录不宣告 Stage 2 任一 gate 通过。
