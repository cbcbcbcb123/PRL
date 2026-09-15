---
status: current
stage: Z1-MYO-SHEET-C0-REPAIR-V02
date: 2026-09-14
execution_status: passed
contact_qualification: passed
static_relaxation: not_run
biological_validation: blocked
---

# 心肌表面接触修复完成：仅双胞静态资格通过

依用户最新“同意，继续”及[冻结合同](ventricle_myocardial_sheet_contact_repair_contract_v02.md)，本轮已完成接触修订、3个开发矩阵、一次89调用正式矩阵和独立复核。没有运行16胞组织松弛、主动周期、ECM或心内膜；无GPU、删除、安装、工作区外写入。旧v01失败记录不改判。

## 发现并修复了什么

1. **接触分支缺失**：旧MODEL_INDEX=2对心肌类型4只有排斥。单独暴露原spring路径后，4号心肌确有吸引，不需要改成类型0；但原spring粗细力差为端向排斥5.58%、端向吸引40.89%、侧向排斥28.43%、侧向吸引31.22%。此开发失败保存在dev01。
2. **重复面积计权**：原spring对每次节点—目标三角面命中都使用整面面积。修订在当前源曲面求积，每点、每目标细胞只使用唯一最近面，反力按目标重心坐标分配；双向各半权。保留ka=.04、kr=.16、捕获长度.35，不以减小刚度或扩大捕获长度制造通过。
3. **最近特征符号歧义**：仅去重后，dev02仍有6.63%–8.84%的部分细化失败。共面边缘点用任意最近三角面的法向判内外，会因浮点并列选面而翻转符号。修订改用面内部法向、共享边相邻法向和、顶点角度加权伪法向。dev03的12例随后全部通过。此证据表明几何符号歧义是本轮修订残差的原因；不将其倒推为旧v01的唯一原因。
4. **能量/反力记账**：明确接触势远场为0、近场为黏附井，同时计算距离势与当前求积面积的完整导数。没有目标形状、目标边长或参考态膜能，也没有永久材料链接和直接位置投影。

## 实际改动位置

仍只有`external/simucell3d`一套内核。在原`contact_node_face_via_spring`类中增加显式`run_surface_quadrature`方法；新的应用探针只负责加载几何、调用核心和保存节点。`PRL_CONTACT_SPRING_PROBE`只对独立探针构建目标生效；全局CONTACT_MODEL_INDEX仍为2，历史生产调用不自动切换。旧v01七项源/合同/可执行哈希全部匹配。

修订输入是一组显式选择的细胞，不通过生物学类型编号决定能否黏附。本次只传入类型4的两个心肌细胞；尚未验证异质材料对、核/ECM包含关系、非凸复杂表面和拓扑事件。

## 正式结果

12个主探针：END/SIDE×-.035/+.070/+.700×384/1536面；另有72个能量差分调用、2个关闭黏附对照、2个刚体变换、1个细胞顺序置换。89调用全部正常退出，正式调用累计约15.0s，单线程CPU。

| 方向/规定间隙 | 384面法向力 | 1536面法向力 | 结果 |
|---|---:|---:|---|
| END / -.035 | -.07433708 | -.07433708 | 排斥 |
| END / +.070 | +.06833743 | +.06833743 | 黏附 |
| SIDE / -.035 | -.11913278 | -.11913278 | 排斥 |
| SIDE / +.070 | +.09406956 | +.09406956 | 黏附 |
| 两方向 / +.700 | 0 | 0 | 超范围无作用 |

正号定义为第一胞朝第二胞吸引，负号为排斥。最大粗细相对差3.69e-15，低于5%门。两档自由度网格表达同一多面体，接触求积分别细分到相同物理尺度，因此这是离散记权和几何判定的一致性，不是一般曲面/求积误差的独立收敛证明。

六类方向导数（4个法向刚体位移、2个横向形变）各自最佳相对误差3.89e-11–4.03e-9，低于1e-6；保存eps=1e-2至1e-7完整序列，极小步长舍入上升不删除。独立复算的刚体/置换节点力误差最大8.94e-15；合力/合矩通过1e-10。关闭ka后近接触力严格为0；位置投影和耦合节点始终为0。

## 验证、运行与图形

实际命令均在项目根运行，退出码0：

```powershell
cmake --build b/z1m0a --config Release --target prl_myo_sheet_contact_probe_v02 -j 2
python -X utf8 -B scripts/run_myo_sheet_contact_repair_v02.py --phase dev01
python -X utf8 -B scripts/run_myo_sheet_contact_repair_v02.py --phase dev02
python -X utf8 -B scripts/run_myo_sheet_contact_repair_v02.py --phase dev03
python -X utf8 -B scripts/run_myo_sheet_contact_repair_v02.py --phase formal
python -X utf8 -B scripts/verify_myo_sheet_contact_repair_v02.py
python -X utf8 -B -m unittest discover -s tests -p test_myo_sheet_contact_repair_v02.py
```

dev01/dev02的程序正常退出不等于科学通过；它们明确failed。正式独立复核passed，3个原始行为回归通过。编译有既存OpenMP/宏重定义/类型转换警告，未出现编译错误。冻结源与输入均有运行前哈希。

结构图、两方向力比较、能量梯度图、三位置接触牵引网格、曲率/初始化压力场及GIF均来自原始输出。定量图沿用CB统一风格10×5in轴框、600dpi PNG和可编辑SVG；空间图采用等尺度网格。可视化手工与文件/链接检查见交付记录，浏览器交互验收单列not_run，不冒充完整查看器通过。

## 唯一下一步

先为16胞静态维持冻结具体积分与夹持合同，包含接触求积尺度独立复核、短程过阻尼接触稳定性检查；之后以两端有限夹持、上下/横向自由表面、恒定骨架预应力、关闭周期收缩进行整片松弛。保存初态及25%/50%/75%/100%算法状态，并检验连通、体积2%、网格15°/安全8°、自由节点残力1e-3等原门。新接触尚未写入历史生产运行或被宣称为组织稳定。

本轮没有恢复参考态膜能。生物学验证与父Z1仍blocked；通过范围仅为本合同的合成静态双细胞接触。

[本轮图文结果](../results/ventricle_z1/z1_myo_sheet_contact_repair_v02_20260914/index.html) · [独立复核](../results/ventricle_z1/z1_myo_sheet_contact_repair_v02_20260914/independent_verification.json) · [原始命令账本](../results/ventricle_z1/z1_myo_sheet_contact_repair_v02_20260914/execution_ledger.json)
