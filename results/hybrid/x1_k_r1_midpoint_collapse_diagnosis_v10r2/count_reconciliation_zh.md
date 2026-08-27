# X1-K v10r2 计数对账说明

canonical configuration count 的定义是：递归展开 mapping；数组整体作为一个叶值。独立重算结果为 32，完整集合见 `count_reconciliation.json`。

frozen lifecycle blob count 的定义是：取 v09/v10 六个冻结生命周期提交的 changed path 唯一并集，再限定为基线提交中存在的 Git blob。独立重算结果为 102，逐路径及来源提交见 `count_reconciliation.json`。

过程消息中的 37 与 105 没有形成版本化中间集合，无法诚实重建其精确成员。二者因此标为 `non_versioned_interim_miscount_superseded_non_reconstructable`；不得编造 37→32 或 105→102 的转换。它们从未进入冻结 summary、manifest 或 gate。
