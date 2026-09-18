# v01失败定位的只读原生源码证据

来自已停止的`prl-mixed-cube-benchmark-v01-20260918`容器，镜像及源路径见`native_runtime/source_manifest.json`。
仅用`docker cp`取出已安装源码；没有exec/start、新建容器、安装或拉取。原版权及许可证头保留。
这四个文件仅作诊断证据，不作为项目求解实现导入。原始FFCx/DOLFINx归属不变。

- `assembler.h` 74–79行：抛错条件是坐标单元hash不相等。
- `ffcx_representation.py` 597–600、680–684行：化简后表达式无域时，坐标单元hash为0。
- `function.py` 288–292行：Expression.eval通过原生tabulate_expression求值。
- `Expression.h`：表达式保存编译所得坐标单元hash。

不能从这些源码单独证明v01失败的key就是body；原运行没有记录key，原JIT缓存为易失tmpfs，不假称已保全。
两个仿射patch的body恒为0由解析式及独立宿主测试确认，MMS的body仍保持−Div(P*)。
修订仅将patch零体力明确绑定网格并增加逐表达式诊断；原环境复现是否消失仍unknown。

`finalize.py`只做失败证据读回、源码分版保全、宿主测试与绘图，不启动容器/求解器。
其一次性产物在外部结果包，已存在时拒绝覆盖。原失败源码和修订源码分别保留。
