# PRL评审：证据位置与原文摘录

评审日期：2026-09-18。原始包：`PRL_FEM_Expert_Review_20260918_v01.zip`。
ZIP SHA256：`d4874e773bfebc8ac2604249430431b943bee5ca68789bfe9503009296eed3ea`。
以下L编号由实际文件逐行枚举，属于本地源码/文档行号，不是平台File citation。所有摘录均来自同一上传包；不引用其他项目或未提供的历史版本。
原包只读，完整性校验通过。候选网格在本次仅从已保存NPZ复算；未重新读取MSH。

<a id="e1"></a>
## E1｜项目目标、模型边界与已完成状态

路径：`01_项目进展与模型.md`
范围：L1–L110。SHA256：`64b67f19e4a899121b00d81d1a5e9eb60f17cc81ca5655e9b694b8f9db3adff2`。

```text
L1: # PRL：斑马鱼心室FEM核心模型与进展（专家评审稿）
L2: 
L3: 快照日期：2026-09-18。当前代码基线：main / 1913bfb；最近科学提交：69d2d47。
L4: 这是精选技术评审包，不是完整仓库备份、投稿结论或新实验。所有 failed / not_run 状态保留。
L5: 
L6: ## 1. 想回答的科学问题
L7: 
L8: 研究斑马鱼发育过程中，心肌主动收缩、血流、组织生长和ECM重塑怎样共同影响心室形态与泵血功能。
L9: 首个拟研究问题是：暂时抑制收缩及随后恢复，是否通过累积的生长/ECM反馈造成不同的发育轨迹。
L10: 这是待检验假说，不是当前计算已经证明的生物学机制。
L11: 
L12: 项目现在只采用FEM连续体，不恢复DCM。尚无自有实验；先用理想化三维模型及公开morphoHeart资料，
L13: 后续将自有几何、壁运动、材料和纤维数据逐项替换。目前的三维半椭球尚未用morphoHeart拟合。
L14: 既有二维外轮廓来自公开72 hpf Fish 4资料，但内腔/层界由缩放构造，不能当作真实三层分割。
L15: 
L16: ## 2. 当前三维模型：到底算了什么
L17: 
L18: | 项目 | 当前实现与边界 |
L19: |---|---|
L20: | 几何 | z≤0的半椭球壳，外半轴(1,1,1.5)，径向层界(20/27,21/27,22/27,1) |
L21: | 组织 | 构造的心内膜、ECM、心肌三域；当前三层同被动材料，并非实验校准的组织差异 |
L22: | 材料 | 有限变形、近不可压混合Neo-Hookean；μ=1、κ=1000，均为无量纲设定 |
L23: | 自由度 | 仿射四面体几何；P2三分量位移/P1连续压力；六阶体/面积分 |
L24: | 约束 | 基底环z=0全位移固定；外壁自由 |
L25: | 加载 | 内壁随动压力p_lumen/μ=0.01；已计算的三维态Ta=0 |
L26: | 腔体积 | 由内壁加固定z=0虚拟平盖定义；平盖不是组织或瓣膜 |
L27: | 主动项 | 心肌域的切平面分散主动张力已编码，但尚未运行三维主动状态 |
L28: | 时间 | 准静态加载级/数值延拓；没有标定生理心动周期 |
L29: | 后端 | 固定本地FEniCSx镜像，PETSc/SNES Newton线搜索与MUMPS；Gmsh用于候选网格 |
L30: 
L31: 明确区分混合压力变量 p_m 和施加的腔压 p_lumen：二者不是同一个场。
L32: 
L33: ```
L34: F = I + Grad(u),   J = det(F)
L35: W_pass = μ/2 [J^(-2/3) tr(F^T F) - 3] + p_m (J-1) - p_m^2/(2κ)
L36: A = (I - n0⊗n0)/2
L37: W_act = Ta/2 [tr(F A F^T) - tr(A)]        仅心肌域
L38: P_act = Ta F A
L39: σ_act = Ta F A F^T / J
L40: Π_pressure = -p_lumen V_c
L41: V_c = -(1/3) ∫inner (X+u)·cof(F)N dS
L42: ```
L43: 
L44: A是理想化等权切向分散张量，不是实测心肌螺旋纤维。三维主动项尚未经载荷资格验证。
L45: 原始模型合同、生产形式和独立NumPy验证器均随包保留，便于专家直接对照公式。
L46: 
L47: ## 3. 已完成的证据与尚未过关之处
L48: 
L49: ### 二维低压主动加载：数值资格passed，不是实验验证
L50: 
L51: F6-S1-S9：P2位移/DG2压力，两个轮廓网格；p/μ=0.02固定，Ta/μ从0至0.1。
L52: 8个新增平衡态通过该阶段验收；最大激活相对同压力零激活基线缩腔约1.85%。
L53: 这是二维平面应变准静态结果，不是三维心跳，不证明任意压力/网格稳定性。
L54: 此前高压工况仍failed；低压passed不是对高压失败的修复或掩盖。
L55: 
L56: ### 三维粗细网格首压力：平衡收敛，但局部体积门failed
L57: 
L58: | 指标 | M0 | M1 |
L59: |---|---:|---:|
L60: | 四面体 | 1344 | 3960 |
L61: | 腔体积增幅 | 1.089525% | 1.105919% |
L62: | 最大位移/L | 0.004041971 | 0.004139627 |
L63: | 采样max abs(J-1) | 1.522743% | 1.449560% |
L64: | 超1%门的单元 | 96 | 120 |
L65: | 远离基底的max abs(J-1) | 0.529615% | 0.459731% |
L66: 
L67: M1零载passed，压力态3次Newton达到平衡，独立残差和场量重算通过；但局部体积误差仍超过预设1%。
L68: M1超限全部邻接固定基底：心内膜72个、ECM48个、心肌0个。不能用整体体积响应接近代替局部质量。
L69: M0→M1同时改变了曲面离散；不是同几何的纯h细化，也不能声明应力热点或渐近收敛。
L70: 
L71: ### 网格质量审查：不能把“网格规则”认定为单一病因
L72: 
L73: M1比M0总体形状指标改善，但仍有基底超限。M1的120个超限中，72个没有触发形状筛查；
L74: 384个远区形状标记单元又没有超体积门。位置、薄层、约束与压力空间的影响尚未分离。
L75: 筛查阈值和相关性只用于诊断，不是普适正确性证明；单元也不是独立生物学重复。
L76: 
L77: ### 最新非结构化候选：几何保持，质量门failed，FEM not_run
L78: 
L79: 保持M1内外壁、层界和基底三角形，生成一个Gmsh候选：3960→2611单元，预计DOF 19119→13483。
L80: 内腔体积差0，各层相对差≤2.22e-16。q=3r/R的5%分位改善4.442271%，未达预设5%；
L81: 最差q反而从0.2220降至0.0292，少数ECM单元变差。最小内二面角6.638°→6.811°。
L82: 
L83: 原执行在网格生成后因Gmsh节点重编号发生读取错误；候选MSH已完整保存。
L84: 只读解析保存的MSH后得到上述质量判断；原失败不改写。当前代码已修订精确坐标映射并补测，
L85: 但修订后的完整容器路径尚未重跑。本阶段新增FEM为0，没有候选应力/变形结果。
L86: 最新132项测试及21项子测试passed属于项目回归，不代表三维加载或生物学通过。
L87: 
L88: ## 4. 当前判断与优先路线
L89: 
L90: 目前主要瓶颈是三维近不可压局部体积控制，而非Docker启动、Newton不收敛或图片显示。
L91: 具体根因仍unknown：三维混合空间的局部约束能力、薄层分辨率、基底强约束及其组合均需检验。
L92: 不应根据现有证据简单断言某一种网格或压力空间“必然正确”。
L93: 
L94: 拟先设计小型三维混合离散基准，审查稳定性、锁死、体积误差与自由度成本，再回到同载心室。
L95: 是否保留1%采样门、是否同时需要弱约束误差/能量误差/场收敛指标，请专家独立评价；
L96: 当前包没有事后放宽旧门，也不把门的讨论当作旧失败通过。
L97: 
L98: 后续顺序：可靠三维被动/主动固体 → 生长公式基准及规定式三维生长 → 双向FSI →
L99: 周期平均力学生长反馈 → ECM反馈 → 公开数据检验 → 自有实验验证。
L100: 生长将采用F=Fe Fg，近不可压约束针对Je，不应把总J≈1误用于禁止真实生长。
L101: 生长、ECM反馈、三维血流、双向FSI、真实心动时间及物种特异性校准均not_run/unknown。
L102: 
L103: ## 5. 本包能和不能复现什么
L104: 
L105: 已包含当前核心模块依赖闭包、公式/边界合同、三维原始失败态和迭代、网格MSH、独立验证、
L106: 五套完整图版本包（source data、methods、Notebook、辅助代码、PNG、SVG），以及来源/哈希清单。
L107: 未打包DCM、完整Git历史、Docker镜像、第三方求解器二进制、全部公开影像或全部历史探索。
L108: 二维仅精选完整图数据及配置/核验报告，未复制其大型全场原包；SELECTION列出了明确省略项。
L109: 三维重复原始数组逐字节哈希核验后仅在D1保存一份，其他阶段的SELECTION指向包内同一证据。
L110: 
```

<a id="e2"></a>
## E2｜生产混合能量、压力空间、基底与主动项

路径：`PRL/src/prl/fem/fenicsx_ventricle.py`
范围：L52–L98。SHA256：`b0ceb28eba7bace08bbc3e82ba69eda290b1410315fc3c5073dbe13fafc8d781`。

```text
L52:         ue=basix.ufl.element('Lagrange','tetrahedron',2,shape=(3,))
L53:         pe=basix.ufl.element('Lagrange','tetrahedron',1)
L54:         self.space=fem.functionspace(domain,basix.ufl.mixed_element([ue,pe]))
L55:         self.w=fem.Function(self.space)
L56:         self.vspace,self.vmap=self.space.sub(0).collapse()
L57:         self.pspace,self.pmap=self.space.sub(1).collapse()
L58:         self.vmap=np.asarray(self.vmap,dtype=np.int32).reshape(-1)
L59:         self.pmap=np.asarray(self.pmap,dtype=np.int32).reshape(-1)
L60:         self.coords=self.vspace.tabulate_dof_coordinates()
L61:         self.cells=np.array([self.vspace.dofmap.cell_dofs(c) for c in self.cell_ids])
L62:         self.pcells=np.array([self.pspace.dofmap.cell_dofs(c) for c in self.cell_ids])
L63:         self.fixed=np.repeat((np.abs(self.coords[:,2])<1e-12)[:,None],3,axis=1)
L64:         mapped=self.vmap.reshape(-1,3)
L65:         bcs=[fem.dirichletbc(PETSc.ScalarType(0),mapped[self.fixed[:,k],k],self.space.sub(0).sub(k)) for k in range(3)]
L66:         self.fixed_mixed=mapped[self.fixed]
L67:         self.free_mixed=np.ones(len(self.w.x.array),dtype=bool); self.free_mixed[self.fixed_mixed]=False
L68:         u,pressure=ufl.split(self.w)
L69:         self.load=fem.Constant(domain,PETSc.ScalarType(0))
L70:         self.activation=fem.Constant(domain,PETSc.ScalarType(0))
L71:         F=ufl.variable(ufl.Identity(3)+ufl.grad(u)); J=ufl.det(F)
L72:         x=ufl.SpatialCoordinate(domain)
L73:         normal=ufl.as_vector([x[k]/config['axes'][k]**2 for k in range(3)])
L74:         normal=normal/ufl.sqrt(ufl.inner(normal,normal))
L75:         active_tensor=(ufl.Identity(3)-ufl.outer(normal,normal))/2
L76:         passive=config['mu']/2*(J**(-2/3)*ufl.inner(F,F)-3)+pressure*(J-1)-pressure**2/(2*config['kappa'])
L77:         active=self.activation/2*(ufl.inner(F*active_tensor,F)-ufl.tr(active_tensor))
L78:         dx=ufl.Measure('dx',domain=domain,subdomain_data=cell_tags,metadata={'quadrature_degree':6})
L79:         ds=ufl.Measure('ds',domain=domain,subdomain_data=facet_tags,metadata={'quadrature_degree':6})
L80:         cavity=-ufl.dot(x+u,ufl.cofac(F)*ufl.FacetNormal(domain))/3*ds(1)
L81:         active_energy=active*dx(3); pressure_energy=-self.load*cavity
L82:         test=ufl.TestFunction(self.space)
L83:         residual=ufl.derivative(passive*dx+active_energy+pressure_energy,self.w,test)
L84:         self.parts={'pressure':ufl.derivative(pressure_energy,self.w,test),
L85:                     'active':ufl.derivative(active_energy,self.w,test),'total':residual}
L86:         self.residual_form=fem.form(residual); self.volume_form=fem.form(cavity)
L87:         self.active_energy_form=fem.form(active_energy)
L88:         self.problem=petsc.NonlinearProblem(residual,self.w,bcs=bcs,petsc_options_prefix='V3D_'+self.name+'_',
L89:             petsc_options={k:v for k,v in config['solver'].items() if k!='mat_mumps_icntl_14'})
L90:         self.factor_options=self.bind_factor_options()
L91:         chi=fem.Function(fem.functionspace(domain,('DG',0)))
L92:         for c in self.cell_ids:
L93:             chi.x.array[chi.function_space.dofmap.cell_dofs(c)]=float(self.layers[c]==3)
L94:         pa=chi*ufl.diff(active,F); piola=ufl.diff(passive,F)+pa
L95:         self.qpoints,self.qweights=basix.make_quadrature(basix.CellType.tetrahedron,6)
L96:         fq,fw=basix.make_quadrature(basix.CellType.triangle,6)
L97:         self.expressions={k:fem.Expression(value,self.qpoints) for k,value in
L98:                           {'F':F,'J':J,'stress':piola*F.T/J,'active_stress':pa*F.T/J}.items()}
```

<a id="e3"></a>
## E3｜独立弱约束及体积验收实现

路径：`PRL/src/prl/verification/ventricle_3d.py`
范围：L59–L180。SHA256：`8229ab2bcca70adcc05dfe4beb984e2442f1aead396d7e035b9ff930f3e5fa78`。

```text
L59: def fields(data,state,config):
L60:     F,J,gradients,detmap,bary,vertices=kinematics(data,state['u'],data['qpoints'])
L61:     if not np.isfinite(J).all() or np.min(J)<=0:
L62:         raise ValueError('Nonpositive/nonfinite reconstructed J')
L63:     weights=detmap[:,None]*data['qweights']
L64:     position=np.einsum('qa,cai->cqi',bary,vertices)
L65:     normal=position/np.square(config['axes'])
L66:     normal/=np.linalg.norm(normal,axis=-1)[...,None]
L67:     tensor=(np.eye(3)-np.einsum('cqi,cqj->cqij',normal,normal))/2
L68:     pressure_values=np.asarray(state['pressure'])
L69:     expected=len(data['pressure_coordinates'])
L70:     if pressure_values.shape not in ((expected,),(1,expected)):
L71:         raise ValueError('Unrecognized scalar pressure layout')
L72:     pressure_values=pressure_values.reshape(expected)
L73:     pressure=np.einsum('qa,ca->cq',bary,pressure_values[data['pressure_cells']])
L74:     inverse_t=np.linalg.inv(F).swapaxes(-1,-2)
L75:     invariant=np.sum(F*F,axis=(-1,-2))
L76:     passive=config['mu']*J[...,None,None]**(-2/3)*(F-invariant[...,None,None]/3*inverse_t)
L77:     passive+=pressure[...,None,None]*J[...,None,None]*inverse_t
L78:     factor=(data['layers']==3)[:,None,None,None]*float(state['activation'])
L79:     active=factor*np.einsum('cqik,cqkj->cqij',F,tensor)
L80:     P=passive+active
L81:     stress=np.einsum('cqik,cqjk->cqij',P,F)/J[...,None,None]
L82:     active_stress=np.einsum('cqik,cqjk->cqij',active,F)/J[...,None,None]
L83:     force=np.zeros_like(data['coordinates']); active_force=np.zeros_like(force)
L84:     for target,piola in [(force,P),(active_force,active)]:
L85:         local=np.einsum('cqij,cqaj,cq->cai',piola,gradients,weights)
L86:         np.add.at(target,data['cells'].ravel(),local.reshape(-1,3))
L87:     weak=np.zeros(len(data['pressure_coordinates']))
L88:     local=np.einsum('qa,cq,cq->ca',bary,J-1-pressure/config['kappa'],weights)
L89:     np.add.at(weak,data['pressure_cells'].ravel(),local.ravel())
L90:     FA=np.einsum('cqik,cqkj->cqij',F,tensor)
L91:     energy=float(.5*float(state['activation'])*np.sum(weights*(data['layers']==3)[:,None]*(np.sum(FA*F,axis=(-1,-2))-1)))
L92:     return {'F':F,'J':J,'stress':stress,'active_stress':active_stress,'force':force,
L93:             'active_force':active_force,'active_energy':energy,'weak':weak,'weights':weights}
L94: 
L95: 
L96: def cavity(data,u,pressure):
L97:     # Inner triangles are oriented away from the lumen. The fixed z=0 cap has zero volume term.
L98:     n,dn=triangle_shape(data['facet_qpoints'])
L99:     nodes=(data['coordinates']+u)[data['inner_faces']]
L100:     position=np.einsum('qa,fai->fqi',n,nodes)
L101:     tangents=np.einsum('qar,fai->fqir',dn,nodes)
L102:     area_vector=np.cross(tangents[:,:,:,0],tangents[:,:,:,1])
L103:     weights=data['facet_qweights']
L104:     volume=float(np.einsum('fqi,fqi,q->',position,area_vector,weights)/3)
L105:     force=np.zeros_like(u)
L106:     local=pressure*np.einsum('qa,fqi,q->fai',n,area_vector,weights)
L107:     np.add.at(force,data['inner_faces'].ravel(),local.reshape(-1,3))
L108:     return volume,force
L109: 
L110: 
L111: def mapping_checks(data):
L112:     local=data['coordinates'][data['cells']]
L113:     midpoints=np.stack([(local[:,i]+local[:,j])/2 for i,j in EDGES],axis=1)
L114:     return {'p2_order':bool(np.max(np.abs(local[:,4:]-midpoints))<1e-12),
L115:             'p1_order':bool(np.max(np.abs(data['pressure_coordinates'][data['pressure_cells']]-local[:,:4]))<1e-12),
L116:             'volume_weights':abs(float(data['qweights'].sum())-1/6)<1e-13,
L117:             'surface_weights':abs(float(data['facet_qweights'].sum())-.5)<1e-13}
L118: 
L119: 
L120: def state_audit(data,state,metadata,config):
L121:     result=fields(data,state,config)
L122:     volume,external=cavity(data,state['u'],float(state['load']))
L123:     reference,_=cavity(data,np.zeros_like(state['u']),0.)
L124:     fixed=data['fixed'].astype(bool); residual=result['force']-external
L125:     reaction=np.where(fixed,residual,0.)
L126:     position=data['coordinates']+state['u']
L127:     force_balance=float(np.linalg.norm((reaction+external).sum(axis=0)))
L128:     moment_balance=float(np.linalg.norm(np.cross(position,reaction+external).sum(axis=0)))
L129:     errors={k:float(np.max(np.abs(result[k]-state[k]))) for k in ['F','J','stress','active_stress']}
L130:     free=float(np.linalg.norm(residual[~fixed])); weak=float(np.linalg.norm(result['weak']))
L131:     force_error=float(np.max(np.abs((residual-state['force_residual'])[~fixed])))
L132:     weak_error=float(np.max(np.abs(result['weak']-state['weak_residual'])))
L133:     _,sample_j,_,_,_,_=kinematics(data,state['u'],extra_points())
L134:     max_j=max(float(np.max(np.abs(result['J']-1))),float(np.max(np.abs(sample_j-1))))
L135:     min_j=min(float(result['J'].min()),float(sample_j.min()))
L136:     delta=.01*np.sin(data['coordinates']+np.array([.2,.4,.6])); delta[fixed]=0.
L137:     h=1e-5; p=float(state['load'])
L138:     plus,_=cavity(data,state['u']+h*delta,p); minus,_=cavity(data,state['u']-h*delta,p)
L139:     pressure_work=float(np.sum(external*delta)); pressure_difference=p*(plus-minus)/(2*h)
L140:     active_work=float(np.sum(result['active_force']*delta))
L141:     if float(state['activation'])!=0.:
L142:         ep=fields(data,{**state,'u':state['u']+h*delta},config)['active_energy']
L143:         em=fields(data,{**state,'u':state['u']-h*delta},config)['active_energy']
L144:         active_difference=(ep-em)/(2*h)
L145:     else:
L146:         active_difference=0.
L147:     checks={**mapping_checks(data),
L148:         'mixed_map_consistency':bool(np.array_equal(state['u'].ravel(),state['mixed_state'][data['mixed_u_map'].ravel()])
L149:             and np.array_equal(state['pressure'].ravel(),state['mixed_state'][data['mixed_p_map'].ravel()])),
L150:         'snes':metadata['snes_reason']>0 and metadata['iterations']<=30,
L151:         'solver_free_residual':metadata['free_residual_norm']<=1e-9,
L152:         'independent_free_force':free<=2e-6,'weak_pressure':weak<=1e-8,
L153:         'kinematics':max(errors['F'],errors['J'])<=1e-10,
L154:         'stress':max(errors['stress'],errors['active_stress'])<=2e-7,
L155:         'free_force_agreement':force_error<=2e-7,'weak_agreement':weak_error<=2e-7,
L156:         'positive_J':min_j>0,'local_volume':max_j<=.01,
L157:         'cavity_volume_agreement':abs(volume-metadata['cavity_volume'])<=1e-10,
L158:         'fixed_displacement':float(np.max(np.abs(state['u'][fixed])))<=1e-12,
L159:         'force_balance_with_support':force_balance<=2e-6,
L160:         'moment_balance_with_support':moment_balance<=2e-6,
L161:         'pressure_virtual_work':abs(pressure_work-pressure_difference)<=2e-6,
L162:         'active_virtual_work':abs(active_work-active_difference)<=2e-6,
L163:         'active_energy':abs(result['active_energy']-metadata['active_energy'])<=2e-7,
L164:         'active_localization':bool(np.max(np.abs(result['active_stress'][data['layers']!=3]))==0),
L165:         'linear_solver':metadata['linear_solver']['status']==('not_run' if metadata['iterations']==0 else 'passed'),
L166:     }
L167:     if p==0 and float(state['activation'])==0:
L168:         checks['zero_displacement']=float(np.max(np.abs(state['u'])))<=1e-10
L169:     return {'status':'passed' if all(checks.values()) else 'failed','checks':checks,
L170:             'failed_checks':[k for k,v in checks.items() if not v],
L171:             'pressure':p,'activation':float(state['activation']),'cavity_volume':volume,
L172:             'reference_volume':reference,'volume_change':volume/reference-1,
L173:             'max_abs_J_minus_one':max_j,'J_min':min_j,
L174:             'quadrature_max_abs_J_minus_one':float(np.max(np.abs(result['J']-1))),
L175:             'max_displacement':float(np.max(np.linalg.norm(state['u'],axis=1))),
L176:             'independent_free_force':free,'weak_pressure_norm':weak,'force_assembly_error':force_error,
L177:             'field_errors':errors,'force_balance':force_balance,'moment_balance':moment_balance,
L178:             'pressure_virtual_work_error':abs(pressure_work-pressure_difference),
L179:             'active_virtual_work_error':abs(active_work-active_difference),
L180:             'cavity_reconstruction_error':abs(volume-metadata['cavity_volume'])}
```

<a id="e4"></a>
## E4｜M0已有投影诊断与原失败保留

路径：`PRL/project_control/ventricle_fem_idealized_3d_resume_execution_v01.md`
范围：L27–L77。SHA256：`f905a1118800bdc84748d6eeec22c3fee170edcbc3864cda01928a91ad4b49d9`。

```text
L27: ## 实际结果
L28: 
L29: 仅一次31.453212秒固定本地镜像容器，1CPU/8GiB/禁网/0GPU，无重跑、无OOM。
L30: 仅新增M0的pressure_1：p/mu=0.01、Ta=0。3次Newton，收敛理由2、自由残差1.690593e-16；
L31: MUMPS状态passed，icntl14读回100。生产/独立F、J、应力误差均在1.33e-15内。
L32: 
L33: | 指标 | 结果 | 原门及裁决 |
L34: |---|---:|---|
L35: | 腔体积相对无载变化 | +1.089525% | 已计算，不是接受状态 |
L36: | 最大位移/L | 0.004041971 | 真实1倍形变 |
L37: | 积分点max abs(J-1) | 1.314813% | 也超过1% |
L38: | 积分点与额外56点max abs(J-1) | 1.522743% | 1%门failed |
L39: | 最小J | 0.98477257 | 正Jacobian passed |
L40: | 独立自由力残差 | 1.9551e-16 | passed |
L41: | 压力弱残差 | 1.8071e-18 | passed；不能替代逐点门 |
L42: 
L43: 25项状态检查仅local_volume失败。首失败停止：新增尝试1、接受0、原无载复用1；
L44: M0余5态及M1全部7态共12态not_run，主动加载、网格响应、生长、FSI和生物学验证均not_run。
L45: 保留压力态混合向量/u/p/F/J/应力、初态、Newton 0/1/2/3四个实际状态和原失败日志。
L46: 
L47: ## 只读定位及未确认点
L48: 
L49: 按cb-diagnose从保存数组独立重算，不追加FEM或修改物理实现。
L50: 96/1344单元超过1%门，全部是具有固定基底顶点的单元；
L51: 心内膜48个、ECM48个，心肌0个。非基底相邻960个单元的最大偏差0.529615%。
L52: 最差单元144、心内膜域、J=0.98477257；这说明失真集中于基底邻近第一圈，
L53: 并不声称最差采样点位于z=0约束面本身。
L54: 
L55: 体积加权平均J-1为5.769975e-6；额外点上max abs(p_material/kappa)=1.7221e-5，
L56: 但max abs(J-1-p_material/kappa)=0.01522748。
L57: 确认：弱平衡及连续P1压力矩已满足，局部体积条件未满足；不是接口、未收敛或MUMPS故障。
L58: 基底约束、粗网格和压力空间各自贡献尚未分离，不能凭本次结果断言单一根因。
L59: 不提高kappa、不降低载荷规避、不放宽原1%门，也不直接切换三维不连续压力空间。
L60: 
L61: ## 交付与保全
L62: 
L63: 运行前85测试、交付后87测试通过；主机/容器独立报告按计算前合同容差一致。
L64: cb-paper-figure-workflow及cb-plot-unified-style生成物理数据副本、可执行Notebook、600dpi PNG和SVG。
L65: 图中A是原结构，B/C为失败压力态真实1倍形变上的应力/局部J；D为原无载与该压力态响应。
L66: 只有两个实存加载级，不伪造5个平衡态；Newton迭代不称为生理时间。
L67: 首次图件校验因缺FIGURE_SIZE_IN元数据失败；只补图形元数据并重执行绘图，未改科学数据。
L68: 
L69: 结果：E:\Temp-Projects\PRL-results\ventricle_fem\f6s2r_idealized_3d_resume_v01_20260918。
L70: 123文件17,765,106 bytes，manifest覆盖122项，SHA-256：
L71: cb846ad96711d6706a7a9b2912ddf9100a65c2a3645e9dd7f7af14c0eafd455c。
L72: 1817父/祖先文件、71调用文件、50项无关修改及执行源代码哈希全部保持。
L73: 仓库约2.038GB，低于3GiB；结果不进Git。无安装、拉取、Docker修复、删除或推送。
L74: 本次tmp/f6s2r_checks仅含受控检查缓存，保留；任何删除仍需精确清单及单独确认。
L75: 
L76: [结构与结果图](../../PRL-results/ventricle_fem/f6s2r_idealized_3d_resume_v01_20260918/index.html) ·
L77: [原失败](../../PRL-results/ventricle_fem/f6s2r_idealized_3d_resume_v01_20260918/failure.json) ·
```

<a id="e5"></a>
## E5｜M1执行时间、同载细化与交付要求

路径：`PRL/project_control/ventricle_fem_3d_fine_pressure_execution_v01.md`
范围：L1–L81。SHA256：`9631407cf3108e22f28d79a61d1c2c83fff6c96473a535c53b3cf98f7938b2fd`。

```text
L1: ---
L2: document_id: PRL-F6-S2-D1-3D-FINE-PRESSURE-EXECUTION-V01
L3: status: failed
L4: date: 2026-09-18
L5: contract: project_control/ventricle_fem_3d_fine_pressure_contract_v01.md
L6: nonlinear_equilibrium: passed
L7: fine_zero: passed
L8: fine_pressure_acceptance: failed
L9: evidence_delivery: passed
L10: ---
L11: 
L12: # 同压力粗细网格诊断：整体响应接近，基底局部门仍失败
L13: 
L14: ## 实际执行
L15: 
L16: 只新增已有M1的zero和pressure_1两次SNES，0主动张力；M0原失败数据逐字节保留，无重算。
L17: 半椭球、三层同mu=1/kappa=1000、P2/P1、六阶积分、全固定基底/外壁自由与随动压力不变。
L18: 生产求解器、协议及原独立力学验证文件与父包交付快照SHA-256一致，未复制新内核。
L19: M1输入几何原件复制，3960四面体、6083个位移节点、19119混合DOF。
L20: 
L21: 一次44.488051秒固定本地容器，1CPU/8GiB/禁网/0GPU；无OOM、自动重跑、Docker修复或拉取。
L22: 无载0次Newton、J=1、passed；p/mu=0.01、Ta=0经3次Newton平衡，
L23: 自由残差1.39655e-16、MUMPS passed，独立自由残差1.58117e-16、场量最大差1.24e-15。
L24: 首压力仍仅local_volume检查failed，按约定停止；新增尝试2、接受1（仅zero）。
L25: 压力Newton 0/1/2/3、各态初始/全混合向量/u/p/F/J/应力/残差及原失败完整保存。
L26: 
L27: ## 对照结果
L28: 
L29: | 指标 | M0（原始保留） | M1（本次） |
L30: |---|---:|---:|
L31: | 四面体数 | 1344 | 3960 |
L32: | 腔体积相对各自无载增加 | 1.089525% | 1.105919% |
L33: | 最大位移/L | 0.004041971 | 0.004139627 |
L34: | 采样max abs(J-1) | 1.522743% | 1.449560% |
L35: | 积分点max abs(J-1) | 1.314813% | 1.255314% |
L36: | 超过原1%门的单元 | 96/1344 | 120/3960 |
L37: | 非基底相邻区域max abs(J-1) | 0.529615% | 0.459731% |
L38: | 压力态裁决 | failed | failed |
L39: 
L40: 腔体积响应绝对差0.000163936（0.016394个百分点），相对差1.482348%，
L41: 通过预先固定的0.002绝对且5%相对参考门；不能替代两网格均失败的局部体积门。
L42: 最大局部失真仅改善4.805976%，没有解决问题。
L43: 超限单元全部有固定基底顶点；M1心内膜72、ECM48、心肌0。
L44: 不同网格单元数/体积不同，不能直接用120>96断言整体变差。
L45: 
L46: ## 科学解释与边界
L47: 
L48: 确认：弱平衡收敛和整体响应接近，并不保证局部近不可压质量；
L49: 问题在本次细网格仍集中于基底邻近区域，不是未收敛、MUMPS或已修正接口故障。
L50: 两网格的曲面近似也变化，不是同边界几何纯h细化；不能分离几何、夹持、压力空间贡献，
L51: 也不能称渐近/热点收敛。当前证据不支持简单继续同类加密就能解决局部门。
L52: 没有放宽1%门、提高kappa、降低压力或松开夹持，也没有继续主动、生长、FSI。
L53: 两次科学状态只对应加载级，没有生理时间；三层/几何/参数未实验标定。
L54: 
L55: ## 交付验收
L56: 
L57: 运行前后91项测试passed；主机与容器verify报告在计算前冻结容差内一致。
L58: cb-diagnose用于单变量失败诊断，不擅自实施物理修复；
L59: cb-paper-figure-workflow/cb-plot-unified-style用于实际数据副本、Notebook、600dpi PNG/SVG及目检。
L60: 图为两套真实参考结构和同压力态的应力/J，1倍形变、共用轴限/色标、无平滑。
L61: 原始两载荷级及Newton状态均留存；不伪造五个平衡态。
L62: 
L63: 结果包E:\Temp-Projects\PRL-results\ventricle_fem\f6s2d1_3d_fine_pressure_v01_20260918：
L64: 128文件41,493,908 bytes（约39.57MiB），127项manifest；SHA-256：
L65: 7bd712585b82c5ca4689f56292536a918b060ace2acf9051790ecba9a790e0f4。
L66: 1940父/祖先文件、75调用文件、50项无关修改及执行源码哈希保持；代码仓低于3GiB。
L67: 本地main精确提交，不推送；无删除、安装、拉取、GPU或工作区外未授权输出。
L68: tmp/f6s2d1_checks检查缓存保留，删除仍须另行列单审批，不处理任何旧目录。
L69: 
L70: [结构与场量对照](../../PRL-results/ventricle_fem/f6s2d1_3d_fine_pressure_v01_20260918/index.html) ·
L71: [独立粗细诊断](../../PRL-results/ventricle_fem/f6s2d1_3d_fine_pressure_v01_20260918/mesh_diagnostic.json) ·
L72: [原始失败](../../PRL-results/ventricle_fem/f6s2d1_3d_fine_pressure_v01_20260918/failure.json)。
L73: 只读复核：`python -B -X utf8 -m prl verify fem-idealized-3d --fine-first-pressure`，预期failed。
L74: 相应run为create-only拒绝重跑；两态已用尽，本记录不授权新加载。
L75: 
L76: ## 唯一下一步：先形成体积约束离散资格方案（待确认）
L77: 
L78: 保留材料、载荷和基底，先审查并冻结更局部的体积约束离散单变量方案。
L79: 包括三维压力表示所需阶次、自由度/稳定性、近不可压锁死及小基准门；
L80: 不能直接把二维通过的压力空间当作三维资格。方案审查不启动新的FEM。
L81: 小基准/同载壳执行另按明确合同确认，再决定是否需要基底约束对照。
```

<a id="e6"></a>
## E6｜候选网格实际结果、接口失败、图件返工与not_run

路径：`PRL/project_control/ventricle_fem_3d_unstructured_execution_v01.md`
范围：L1–L79。SHA256：`1159ca80df497c16379e97a9b6488af8adea4ce6cba6acf9c61236def37ee062`。

```text
L1: ---
L2: document_id: PRL-F6-S2-D2B-EXECUTION-V01
L3: status: failed
L4: date: 2026-09-18
L5: candidate: one_consumed_no_retry
L6: FEM: not_run
L7: new_FEM_solves: 0
L8: ---
L9: 
L10: # 同边界非结构化候选：几何保持，质量门未通过
L11: 
L12: 依据[原合同](ventricle_fem_3d_unstructured_comparison_contract_v01.md)和
L13: [本次采纳及固定选项](ventricle_fem_3d_unstructured_adoption_v01.md)，仅运行一个候选。
L14: 本轮是网格工程对照，不是心肌收缩、发育、细胞随机性或FSI结果。
L15: 
L16: ## 结果
L17: 
L18: | 指标 | 原M1 | Gmsh候选U1 |
L19: |---|---:|---:|
L20: | 四面体 | 3960 | 2611 |
L21: | 混合P2/P1预计自由度 | 19119 | 13483 |
L22: | q=3r/R的5%分位 | 0.2382721 | 0.2488568 |
L23: | q中位数 | 0.3272215 | 0.3505279 |
L24: | 最差q | 0.2220354 | 0.0292329 |
L25: | 最小内二面角 | 6.637914° | 6.811118° |
L26: | 薄层基底区q的5%分位 | 0.2267100 | 0.2397507 |
L27: 
L28: 边界和两个层界的三角形逐坐标集合、材料邻接完全一致；拓扑、正体积、
L29: 无重复/悬空顶点、资源门通过。内腔体积相对差0，各层最大相对差2.22e-16。
L30: 薄层基底的q05及最小角度非下降门通过，但全体q05仅提高**4.442271%**，
L31: 未达预设5%（目标0.2501857210），因此质量资格 **failed**。
L32: 此外少数ECM单元最差q降至0.02923；不能仅凭中位数或Gmsh日志判定优质。
L33: DOF减少29.48%，不是同DOF严格拓扑因果对照，也未进行渐近收敛验证。
L34: 
L35: ## 首失败与只读恢复
L36: 
L37: Gmsh 4.15.2成功完成一次Delaunay生成和一次显式默认优化，保存了
L38: fixed_surfaces.msh、before_optimization.msh、candidate.msh及全部选项/日志。
L39: 随后输出适配器按原节点标签查找外壁，因Gmsh自动重编号触发KeyError(726)。
L40: 原调用与failure.json保持failed，未重新启动容器，未进行任何FEM。
L41: 
L42: 使用已安装meshio 5.3.5读取该唯一candidate.msh，按**精确坐标**建立面片映射，
L43: 不舍入、不近邻粘合、不补点、不修改网格。offline/保存完整派生网格和独立质量核验。
L44: 上述质量门失败来自该只读复核，不是当时已成功执行的在线门。
L45: 生产适配器已改为精确坐标映射，新增重编号/坐标漂移/重复坐标回归；
L46: 修订后完整容器路径 **not_run**，不以单元测试代替再次实跑证明。
L47: 
L48: 原三维M0/M1首压力失败1.5227%/1.4496%保持。U1无zero/pressure状态，
L49: 所以不能比较U1的J、应力或变形；图中只有实际参考网格及质量统计，没有伪造场量。
L50: 
L51: ## 交付与复算
L52: 
L53: - [结果入口和真实结构/质量图](../../PRL-results/ventricle_fem/f6s2d2b_unstructured_v01_20260918/index.html)
L54: - [独立网格比较](../../PRL-results/ventricle_fem/f6s2d2b_unstructured_v01_20260918/offline/mesh_comparison.json)
L55: - [原失败](../../PRL-results/ventricle_fem/f6s2d2b_unstructured_v01_20260918/failure.json)
L56: - [离线复核与交付审计](../../PRL-results/ventricle_fem/f6s2d2b_unstructured_v01_20260918/delivery_audit.json)
L57: - [源代码](../src/prl/fem/unstructured_geometry.py)、[独立体网格核验](../src/prl/verification/mesh_equivalence.py)
L58: 
L59: 只读复核：`python -B -X utf8 -m prl verify fem-unstructured-3d`。
L60: 运行命令`python -B -X utf8 -m prl run fem-unstructured-3d`已经消耗，create-only禁止重复。
L61: 132项测试、21项子测试passed；包括原力学/协议/CLI、接口重编号和首失败停机。
L62: 每个图版本保存物理复制数据、方法、Notebook、质量公式和样式，导出PNG/SVG并目检。
L63: 首次图件校验发现STYLE_SOURCE声明缺失，已在未冻结版本补全并重新执行；
L64: 目检发现图注与横轴标题邻接过近，增加显式底部空间后重新导出，无数据改动。
L65: 
L66: 一容器7.934秒（容器内2.118秒）、单CPU、8GiB、禁网、0GPU、0自动重跑。
L67: 原输入、失败、执行源快照及全部受保护祖先不改写；确切保护计数及哈希见交付审计。
L68: 无关50项工作区修改保持。无删除、迁移、安装、拉取、Docker修复或推送。
L69: 任务临时检查目录`E:\Temp-Projects\PRL\tmp\f6s2d2b_checks`保留，未经确认不删除。
L70: 
L71: ## 裁决与唯一下一步
L72: 
L73: 停止本候选，不将4.44%改判为5%，也不为了passed继续调网格选项。
L74: 这是固定边界、固定尺寸规则下的一个反例，不证明所有非结构化网格无效，
L75: 更不证明“规则网格”就是原压力误差的根因。
L76: 
L77: 建议下一步先形成**近不可压三维混合离散的小基准资格方案**：审查稳定性、
L78: 局部体积控制和夹持热点，再选定可验证的位移/压力空间；不是直接把二维DG方案
L79: 搬到三维。方案确认后再做有界基准，未授权新的求解、修改材料/边界或继续生长/FSI。
```

<a id="e7"></a>
## E7｜候选工程门与首失败停止的原合同

路径：`PRL/project_control/ventricle_fem_3d_unstructured_comparison_contract_v01.md`
范围：L1–L54。SHA256：`d9e8d54890ac6b55d3b259c8b0245edf80c6f4157115a31b2f346b60c6ee97df`。

```text
L1: ---
L2: document_id: PRL-F6-S2-D2B-UNSTRUCTURED-COMPARISON-V01
L3: status: not_run
L4: date: 2026-09-18
L5: proposal_basis: user approved quality review followed by controlled unstructured comparison
L6: execution_authorization: pending_confirmation_of_this_bounded_candidate
L7: ---
L8: 
L9: # 候选：同一多面体边界的非结构化四面体对照
L10: 
L11: 这是D2A审查后的具体下一步，尚未执行。已发现本地固定镜像中的gmsh模块，
L12: 但其本机库加载与所需网格操作尚未验证。不得安装、拉取、启动或修复Docker。
L13: 
L14: ## 要回答的问题
L15: 
L16: 在完全相同的离散边界几何和力学模型上，仅改变内部四面体剖分，是否减轻基底局部J误差？
L17: 本轮不同时改善曲面近似，也不测试高阶几何、不同材料、压力空间或放松基底。
L18: 非结构化不等于随机细胞形态，不通过扰动节点来伪装网格优化。
L19: 
L20: ## 候选与几何阶段
L21: 
L22: - 基准为原M1：3960四面体、19119混合DOF；不重算原失败解。
L23: - 从原M1提取内壁、外壁、两个组织层界及三层基底三角面。
L24:   完全保留这些面片、顶点坐标及实体几何，用共享界面的一次体剖分构造三域；
L25:   不分别生成三层后使用最近邻粘合，不允许重复/重叠/缝隙。
L26: - 使用固定本地镜像已有Gmsh；记录实际版本和全部选项。
L27:   单线程Delaunay体网格与固定一次质量优化，不使用随机几何扰动，不做参数扫或自动重试。
L28: - 固定边界意味着外观可能仍规则；本轮隔离的是内部连接/布点，不声称完整解剖网格升级。
L29: - 候选最多7920四面体、38238混合DOF（基准两倍）；超过则停止，不自动放宽。
L30: - 前后内腔及各层体积相对差<=1e-10；外部/内部面片逐坐标集合及层邻接严格相同，
L31:   容许顶点重编号但不容许面片改变；正体积、无重复单元、正确面邻接和无悬空顶点。
L32: - 比较各层、基底相邻/远区的q分布、最小二面角、正则映射条件数。
L33:   原始q/角度均可计算不是“优质”证明；至少全体q的5%分位较M1提高5%，
L34:   薄层基底区q的5%分位不下降、最小二面角不下降，才进入力学对照。
L35:   这些是本候选工程改善门，不是普适FEM正确性门。未达门保存候选并停止，不反复改选项追求passed。
L36: 
L37: ## 条件式力学阶段
L38: 
L39: 仅候选几何/质量/资源门全部passed后，最多两个新平衡：zero及p/mu=0.01、Ta=0。
L40: 原NH、mu=1/kappa=1000、仿射四面体/P2位移-P1连续压力、六阶积分、全固定基底、
L41: 外壁自由、内壁随动压力与全部独立力学门保持，包括采样max abs(J-1)<=1%。
L42: 沿用原生产力学/独立验证实现，输入接口适配另有测试，不复制新内核。
L43: 单CPU/8GiB/禁网/0GPU，整个候选运行1800秒，停止保全预留120秒；一次容器，
L44: 一次网格候选，最多2次SNES，首失败停止，0自动重试，不进入收缩/生长/FSI。
L45: 原网格的失败不因新候选passed而改写。比较整体响应、局部误差、热点和实际DOF；
L46: DOF不同是明确局限，不能宣称只靠拓扑的严格因果证据或完成渐近收敛。
L47: 
L48: ## 存储与交付
L49: 
L50: 拟create-only：E:\Temp-Projects\PRL-results\ventricle_fem\f6s2d2b_unstructured_v01_20260918。
L51: 预计768MiB+64MiB停止空间+10GiB磁盘余量，代码仓3GiB保持；仅已批准结果根。
L52: 保留D2A/D1及全部祖先和无关修改；保存真实候选、日志、原始状态、独立核验、
L53: 原/新结构与场量图、Notebook和失败/未运行裁决。无删除、迁移、安装、推送。
L54: 若固定边界不允许足够的形状改善，先报告该限制；改变表面细化或薄层分辨率属于另一个对照。
```

<a id="e8"></a>
## E8｜薄层法向区间与尚未执行的载荷计划

路径：`PRL/src/prl/fem/ventricle_geometry.py`
范围：L6–L25。SHA256：`51336a2f036d0e4b190ec3710fc1d79b73d937a9ca4bd3e4a031399bed509c48`。

```text
L6: def configuration():
L7:     return {
L8:         'schema_version':'prl.idealized_3d.v1', 'mu':1., 'kappa':1000.,
L9:         'axes':[1.,1.,1.5], 'radii':[20/27,21/27,22/27,1.],
L10:         'meshes':[{'name':'M0','segments':16,'bands':4,'radial':[1,1,2]},
L11:                   {'name':'M1','segments':24,'bands':6,'radial':[1,1,3]}],
L12:         'states':[{'label':'zero','p':0.,'Ta':0.,'initial':None},
L13:                   {'label':'pressure_1','p':.01,'Ta':0.,'initial':'zero'},
L14:                   {'label':'pressure_2','p':.02,'Ta':0.,'initial':'pressure_1'},
L15:                   {'label':'active_1','p':0.,'Ta':.05,'initial':'zero'},
L16:                   {'label':'active_2','p':0.,'Ta':.1,'initial':'active_1'},
L17:                   {'label':'combined_1','p':.02,'Ta':.05,'initial':'pressure_2'},
L18:                   {'label':'combined_2','p':.02,'Ta':.1,'initial':'combined_1'}],
L19:         'solver':{'snes_type':'newtonls','snes_linesearch_type':'bt','snes_atol':1e-11,
L20:                   'snes_rtol':1e-10,'snes_stol':0.,'snes_max_it':30,'ksp_type':'preonly',
L21:                   'pc_type':'lu','pc_factor_mat_solver_type':'mumps','mat_mumps_icntl_14':100},
L22:         'quadrature_degree':6, 'retain_solver_iterates':True, 'diagnostic_trace':True,
L23:         'maximum_equilibrium_solves':14,'resources':{'seconds':1800,'threads':1,'gpu':0,'automatic_retries':0},
L24:         'active_rule':'A=(I-n0*n0)/2; equal tangent-plane dispersion, not measured fibers',
L25:         'scope':'idealized 3D solid; uncalibrated; no flow/growth/physiological clock',
```

<a id="e9"></a>
## E9｜M1原始Newton记录与求解耗时

路径：`PRL-results/ventricle_fem/f6s2d1_3d_fine_pressure_v01_20260918/raw/M1_state_pressure_1.json`
范围：L1–L34。SHA256：`463bbfaac3bd49c6eeb043c0faebc28b646a22b014a8bb66e240ef184c2a99fb`。

```text
L1: {
L2:   "snes_reason": 2,
L3:   "iterations": 3,
L4:   "history": [
L5:     {
L6:       "iteration": 0,
L7:       "residual": 0.002438377513634495
L8:     },
L9:     {
L10:       "iteration": 1,
L11:       "residual": 2.248652013637537e-05
L12:     },
L13:     {
L14:       "iteration": 2,
L15:       "residual": 6.570536222759189e-10
L16:     },
L17:     {
L18:       "iteration": 3,
L19:       "residual": 1.39654944185453e-16
L20:     }
L21:   ],
L22:   "free_residual_norm": 1.39654944185453e-16,
L23:   "cavity_volume": 1.2545555131860968,
L24:   "active_energy": 0.0,
L25:   "linear_solver": {
L26:     "ksp_reason": 4,
L27:     "pc_failed_reason": 0,
L28:     "mumps_infog_1": 0,
L29:     "mumps_infog_2": 0,
L30:     "mumps_icntl_14": 100,
L31:     "status": "passed"
L32:   },
L33:   "elapsed_seconds": 7.3114360550000015
L34: }
```

<a id="e10"></a>
## E10｜本次新增诊断的定义与结果

数据文件：`PRL_review_audit_20260918.json`；复算脚本：`prl_independent_audit.py`。
保存状态复核调用包内NumPy验证器；投影残差及体积加权统计在评审脚本中额外定义。不是独立重新求解的有限元解。
r_h = J_h − 1 − p_m,h/κ。RMS以参考实体体积加权，积分使用原24点规则；max还覆盖原额外56点。
“超限单元体积分数”指含至少一个超限采样点的单元体积和占比，不是连续超限区域的精确体积分数。

| 指标 | M0 | M1 |
|---|---:|---:|
| max abs(J−1) | 1.522742967% | 1.449560299% |
| max abs(p_m/κ) | 0.001722103% | 0.002043734% |
| RMS(r_h) | 0.165123649% | 0.120037090% |
| max abs(r_h) | 1.522748300% | 1.449577096% |
| 超限单元体积分数 | 4.526990550% | 2.497691610% |
| 原压力态求解秒数 | 2.227738010 | 7.311436055 |

候选NPZ质量报告与原报告在绝对/相对容差1e−12内全部一致，最大数值差1.0658141036401503e-14。
本次额外执行4项四面体质量解析/不变性测试，通过。见`PRL_review_shape_tests.txt`和XML。全部项目回归测试未重跑。
图版本目录合计224084344字节，占未压缩包90.564339%。这是存储占比，包含数据/Notebook/图件；不是工时占比。
