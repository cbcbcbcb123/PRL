# 心肌细胞为何不整齐：文献到模型的分层建议

2026-09-14；依据公开原始论文/作者全文。本文是内部研究记录，不属于外部专家plan包。文献启发不等于模型参数已标定；下列随机机制尚未实现或运行。

## 先区分三种“不整齐”

1. **细胞之间的稳定差异**：长、宽、厚、体积、局部主轴、端部位置及邻居数不同。
2. **同一细胞表面的结构性起伏**：例如端部闰盘的台阶、互指及褶皱，不应平均撒在整个侧壁。
3. **随时间改变的形状波动**：膜—皮质耦合、骨架周转及主动应力变化等。它们与稳定几何异质性不是同一类变量。

当前代码采用同一模板复制、相同材料、相同恒定骨架方向，初态与驱动具有强对称性；没有空间异质性或随机时变场。确定性力学保留这种对称性很正常，不代表需要把所有表面变“毛”。当前384面粗网格也不能直接解析纳米膜褶皱。

## 最直接可借鉴的原始论文

### 1. Lashgari et al., Medical Image Analysis 82, 102592 (2022)

*Three-dimensional micro-structurally informed in silico myocardium—Towards virtual imaging trials in cardiac diffusion weighted MRI.* [作者全文](https://arxiv.org/html/2208.10623v1)；[DOI](https://doi.org/10.1016/j.media.2022.102592)。重点图1、5、8及方法3.1。

该研究不是把同一种圆柱加噪声，而是结合心肌尺寸分布：椭圆截面堆积后经watershed得到多边形，沿长轴生成不同长度，保留长度/体积分布，并构造错位但互补的上下层端部。其作用是生成心肌扩散MRI的几何体模，**不是力学自组织或形态维持证明**。

PRL可借鉴：采用有分布的体积、纵横比与端部错位，在共同组织分区内生成兼容界面，随后由DCM松弛；不各自随机移动独立细胞导致穿透。统计验证不仅看平均值，还看分布与邻接/取向相关。论文中的p值不构成分布等价证明；其物种/制备和PRL目标需匹配后才能移植参数。

### 2. Pinali et al., Biophysical Journal 108, 498–507 (2015)

*Three-Dimensional Structure of the Intercalated Disc Reveals Plicate Domain and Gap Junction Remodeling in Heart Failure.* [原始论文](https://pmc.ncbi.nlm.nih.gov/articles/PMC4317535/)；[题录及DOI](https://pubmed.ncbi.nlm.nih.gov/25650918/)。重点健康对照图1–4，不把病变形态当正常。

绵羊左室SBF-SEM显示闰盘具有三维台阶、褶皱和指状突起，端部界面并非平板；二维切片中的起伏幅度不能直接当三维突起长度。

PRL可借鉴：首先把**端部接触域与侧壁域分开**；端部用相互兼容的低阶起伏和区域化黏附表征。当前尺度只宜做粗粒化，不能用384面网格声称解析了闰盘超微结构，也不能证明这些结构可单由各向同性表面能自发形成。

### 3. Biswas, Alex & Sinha, Biophysical Journal 113, 1768–1781 (2017)

*Mapping Cell Membrane Fluctuations Reveals Their Active Regulation and Transient Heterogeneities.* [原始论文](https://www.sciencedirect.com/science/article/pii/S0006349517309645)；[题录](https://pubmed.ncbi.nlm.nih.gov/29045871/)。DOI 10.1016/j.bpj.2017.08.041。

贴壁细胞的干涉成像显示：ATP依赖活动与肌动蛋白/肌球蛋白改变膜高度波动，且皮质既可驱动也可限制波动；波动图和时间自相关显示短程、短暂的异质性。对象不是心肌，不能搬用其幅度/时间常数作为心肌参数。

PRL可借鉴：后续若引入动态起伏，应在**力学驱动场**上定义有空间相关长度及时间相关尺度的波动，并检验输出位移谱/自相关；不是每个节点每步独立踢一下。网格细化时保持相关长度与单位面积载荷不变，避免噪声能量随节点数量增加。

### 4. Runser et al., Nature Computational Science (2024), SimuCell3D

*SimuCell3D: three-dimensional simulation of tissue mechanics with cell polarization.* [原始论文](https://www.nature.com/articles/s43588-024-00620-9)；[PMC全文](https://pmc.ncbi.nlm.nih.gov/articles/PMC11052725/)。DOI 10.1038/s43588-024-00620-9。

该模型通过可变形表面、非均匀机械性质、接触、ECM等描述组织；也可直接导入显微分割初态。论文提供局部重网格维持分辨率/质量；张力波动在讨论中被列为可扩展方向，**不能宣称当前原版或PRL已启用随机张力**。

PRL可借鉴：让非均匀性与空间位置/邻接环境有机制联系，并区分模型物理与网格维护。原软件支持重网格不等于当前定拓扑适配器已接入或验证该功能。

### 5. Turlier et al., Nature Physics 12, 513–519 (2016)

*Equilibrium physics breakdown reveals the active nature of red blood cell flickering.* [原始论文](https://www.nature.com/articles/nphys3621)。红细胞的响应与自发波动比较揭示非平衡活动。

PRL可借鉴：热噪声和主动噪声不能仅凭“都在抖动”互相代替；需独立机械响应对照。红细胞不是心肌，不直接移用其谱参数，也不把整个粗粒化DCM面当作单纯脂膜。

## 建议采纳顺序（尚非新增随机计算授权）

**先几何/细胞间差异，再空间力学差异，最后动态波动。**

- 第一步：实测形态分布或显微分割优先；没有数据时用明确标注“合成敏感性”的少量固定种子、有限幅度分布，而不是自称实验再现。保持共同平均体积、组织密度及边界/载荷，以区分异质性效应。
- 第二步：端部/侧壁不同接触域，骨架主轴在胞间及胞内平滑变化；不破坏总体方向性和反作用力守恒。
- 第三步：可考虑有色随机主动应力，例如具有时间相关的OU过程和空间平滑基底。OU只是待选的数学表示，并非上述论文已经验证的心肌定律；需冻结幅度、相关长度、相关时间、种子和网格/步长收敛判据。
- 保留规则模型作数值基准。比较粗糙度RMS、空间谱/相关长度、时间自相关、逐胞尺寸分布、接触面积/间隙、体积与网格质量，不用“图片更像”作为唯一通过门。
- 真实起伏若与单个三角形大小锁定、随细化变化或伴随极小角，应先按数值伪影处理。不能靠加入随机性掩盖未达到平衡或网格退化。

本轮先继续已批准的长程双胞资格，所有正式轨迹仍保持无随机的原控制。随机化的几何/材料矩阵需在该基础可靠后单独冻结。
