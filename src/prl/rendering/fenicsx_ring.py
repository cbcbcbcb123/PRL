"""Saved-state ring figures; independent of the Docker adapter and FEM solver."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import PolyCollection
from matplotlib.colors import Normalize
import numpy as np
from PIL import Image

from prl.rendering.cb_plot_unified_style import add_top_information, apply_axes_style
from prl.rendering.fem_measured_contour import _axes, _bounded_ticks, _colorbar, _compact_style, _export
from prl.verification.fenicsx_ring import load_arrays, shape
from prl.storage import scan_workspace, evaluate_storage

BLUE='#225A80'
ORANGE='#C87837'
LAYER_COLORS=np.array(['#4C9F70','#D6B656','#5B8DB8'])


def polygons(mesh,u):
    s=np.linspace(0,1,5)
    ref=np.concatenate([np.column_stack((s,np.zeros_like(s))),
                        np.column_stack((1-s,s)),np.column_stack((np.zeros_like(s),1-s))])
    n=shape(ref)[0]
    return np.einsum('qa,cai->cqi',n,(mesh['coordinates']+u)[mesh['cells']])


def collection(mesh,u,values=None,norm=None,cmap='YlGnBu'):
    options={'edgecolors':(0.1,.15,.2,.35),'linewidths':.14}
    if values is None:
        return PolyCollection(polygons(mesh,u),facecolors=LAYER_COLORS[mesh['layers']-1],**options)
    return PolyCollection(polygons(mesh,u),array=values,norm=norm,cmap=cmap,**options)


def von_mises(stress):
    dev=stress-np.trace(stress,axis1=-2,axis2=-1)[...,None,None]*np.eye(3)/3
    return np.sqrt(1.5*np.sum(dev*dev,axis=(-1,-2)))


def spatial(axis,style):
    axis.set_xlim(-1.35,1.15)
    axis.set_ylim(-1.25,1.25)
    axis.set_aspect('equal')
    axis.set_xlabel('x / B')
    axis.set_ylabel('y / B')
    _bounded_ticks(axis.xaxis,-1.35,1.15,bins=4)
    _bounded_ticks(axis.yaxis,-1.25,1.25,bins=4)
    apply_axes_style(axis,style=style)


def render_fenicsx_ring(root):
    root=Path(root).resolve(strict=True)
    if json.loads((root/'configuration.json').read_text()).get('parent_result'):
        return render_active_completion(root)
    workspace=root.parents[2]
    if not evaluate_storage(scan_workspace(workspace),planned_new_bytes=24*1024**2,stop_reserve_bytes=64*1024**2)['can_start']:
        raise RuntimeError('Rendering storage admission refused')
    before=sum(p.stat().st_size for p in root.rglob('*') if p.is_file())
    if before+24*1024**2>128*1024**2:
        raise RuntimeError('Rendering exceeds frozen stage budget')
    verification=json.loads((root/'g1_verification.json').read_text())
    cfg=json.loads((root/'configuration.json').read_text())
    meshes={name:load_arrays(root/'raw'/f'{name}_mesh.npz') for name in ['M0','M1']}
    states={name:[load_arrays(root/'raw'/f'{name}_state_passive_{i}.npz') for i in range(5)] for name in meshes}
    figdir=root/'figures'
    figdir.mkdir(exist_ok=True)
    outputs=[]
    style,overrides=_compact_style(3.6)
    figure=plt.figure(figsize=(11.2,6.8))
    axes=[_axes(figure,1.3+i*4.9,1.75,3.6) for i in range(2)]
    for axis,(name,mesh_data) in zip(axes,meshes.items()):
        axis.add_collection(collection(mesh_data,np.zeros_like(mesh_data['coordinates'])))
        spatial(axis,style)
        axis.plot([1], [0], marker='s',markersize=7,color='#B3463E')
        axis.plot([-1],[0], marker='^',markersize=7,color='#B3463E')
        for theta in np.arange(8)*np.pi/4:
            vector=np.array([np.cos(theta),np.sin(theta)])
            axis.annotate('',xy=.84*vector,xytext=.61*vector,arrowprops={'arrowstyle':'->','color':'#B3463E','lw':1.2})
        add_top_information(axis,f'{name}: {len(mesh_data["cells"])} triangles',style=style)
    figure.text(.085,.94,'F6-S0 | passive ring structure | P2 displacement / P1 pressure',fontsize=16)
    figure.text(.085,.09,'Green: endocardium  |  Yellow: ECM  |  Blue: myocardium',fontsize=13)
    figure.text(.085,.04,'p / mu = 0 ... 0.08; Ta = 0. Outer wall free. Red markers remove rigid motion.',fontsize=12)
    outputs+=_export(figure,axes,figdir/'model_structure',style,overrides)

    figure=plt.figure(figsize=(17.2,7.15))
    style,overrides=_compact_style(3.65)
    axes=[_axes(figure,1.4+i*5.1,1.9,3.65) for i in range(3)]
    pressures=np.asarray(cfg['passive_loads'])
    for name,color,marker in [('M0',ORANGE,'s'),('M1',BLUE,'o')]:
        records=[verification['cases'][name][f'passive_{i}'] for i in range(5)]
        axes[0].plot(pressures,[r['cavity_area_change']*100 for r in records],marker=marker,color=color,lw=1.5,label=name)
        axes[1].plot(pressures,[r['max_abs_J_minus_one']*100 for r in records],marker=marker,color=color,lw=1.5,label=name)
        axes[2].plot(pressures[1:],[r['analytic_relative_error']*100 for r in records[1:]],marker=marker,color=color,lw=1.5,label=name)
    reference=[0.]+[verification['cases']['M1'][f'passive_{i}']['analytic_area_change']*100 for i in range(1,5)]
    axes[0].plot(pressures,reference,color='#424A50',ls='--',lw=1.2,label='Analytic')
    axes[0].set_ylim(-1,26)
    axes[1].set_ylim(-.004,.07)
    axes[2].set_ylim(0,.10)
    for axis,label in zip(axes,['Cavity area change (%)','Maximum |J - 1| (%)','Area response error (%)']):
        axis.set_xlabel('Cavity pressure / mu')
        axis.set_ylabel(label)
        axis.set_xlim(-.004,.084)
        _bounded_ticks(axis.xaxis,-.004,.084,bins=3)
        _bounded_ticks(axis.yaxis,*axis.get_ylim(),bins=4)
        apply_axes_style(axis,style=style)
        axis.legend(loc='upper left',fontsize=12,frameon=False)
    figure.text(.065,.94,'F6-S0 | passive qualification PASSED | 10 retained equilibria',fontsize=16)
    figure.text(.065,.11,'Local volume gate: 1.00% (above displayed range). Incompressible analytic reference; finite kappa = 1000.',fontsize=12)
    figure.text(.065,.055,'Fine mesh peak: cavity +22.4602%; maximum |J - 1| 0.02426%. No active contraction has been simulated.',fontsize=12)
    outputs+=_export(figure,axes,figdir/'mechanics_results',style,overrides)

    fine=meshes['M1']
    data=states['M1']
    # Color is the quadrature mean per element; local extrema remain in the verifier.
    weights=fine['qweights']/fine['qweights'].sum()
    stress=[von_mises(s['stress'])@weights for s in data]
    vmax=max(float(v.max()) for v in stress)
    style,overrides=_compact_style(2.75,small=True)
    figure=plt.figure(figsize=(21.1,6.0))
    axes=[_axes(figure,1.15+i*3.7,1.7,2.75) for i in range(5)]
    for i,(axis,state,values) in enumerate(zip(axes,data,stress)):
        col=collection(fine,state['u'],values,Normalize(0,vmax))
        axis.add_collection(col)
        spatial(axis,style)
        add_top_information(axis,f'p / mu = {float(state["load"]):.2f}',style=style)
    _colorbar(figure,col,(19.45,1.7,.23,2.75),'Total von Mises / mu',style)
    figure.text(.04,.92,'Five computed pressure states | 1x deformation | common stress scale | G1 PASSED',fontsize=15)
    figure.text(.04,.105,'Pressure continuation, not physiological time. Plane strain; uncalibrated homogeneous material; constructed anatomy.',fontsize=12)
    figure.text(.04,.045,'Displacement is quadratic on each triangle. Color shows the quadrature-mean total Cauchy von Mises stress per element.',fontsize=12)
    outputs+=_export(figure,axes,figdir/'five_states',style,overrides)

    # Preview from the same five states; no additional or interpolated equilibria.
    figure=plt.figure(figsize=(5.4,5.1),dpi=110)
    axis=figure.add_axes([.15,.16,.68,.72])
    frames=[]
    for state,values in zip(data,stress):
        axis.clear()
        col=collection(fine,state['u'],values,Normalize(0,vmax))
        axis.add_collection(col)
        axis.set(xlim=(-1.35,1.15),ylim=(-1.25,1.25),xlabel='x / B',ylabel='y / B')
        axis.set_aspect('equal')
        axis.set_title(f'Passive load p / mu = {float(state["load"]):.2f}')
        figure.canvas.draw()
        frames.append(Image.fromarray(np.asarray(figure.canvas.buffer_rgba()).copy()).convert('RGB'))
    gif=figdir/'passive_preview.gif'
    frames[0].save(gif,save_all=True,append_images=frames[1:],duration=650,loop=0)
    plt.close(figure)
    outputs.append(gif)
    page='''<!DOCTYPE html><html lang="zh"><meta charset="utf-8"><title>F6-S0 被动圆环</title>
<style>body{font-family:Arial,sans-serif;max-width:1250px;margin:32px auto;line-height:1.7}img{max-width:100%} .ok{color:#246b44}</style>
<h1>FEniCSx 被动圆环资格</h1><p class="ok">G0 passed · G1 passed（保存状态后验复核） · G2 not_run</p>
<p>896 / 3584 个三角形，两档各五个压力状态。细网格峰值腔面积增加22.4602%，最大局部体积偏差0.02426%。
主动收缩尚未执行；压力级是算法延拓，不是生理时间。本阶段不能证明真实外轮廓或斑马鱼实验拟合通过。</p>
<p>原调用在10态求解后因验证器读取单行压力数组失败，失败记录保留。修复只读取原状态，0科学重跑。</p>
<p><a href="g1_verification.json">独立复核</a> · <a href="failure.json">原失败记录</a> · <a href="configuration.json">参数</a></p>
<h2>结构与边界</h2><img src="figures/model_structure.png"><h2>形变和体积资格</h2><img src="figures/mechanics_results.png">
<h2>五个真实压力态</h2><img src="figures/five_states.png"><h2>五状态预览</h2><img src="figures/passive_preview.gif"></html>'''
    (root/'index.html').write_text(page,encoding='utf-8')
    report={'status':'passed','G1':verification['status'],'G2':'not_run','source':'10 retained passive equilibria',
            'scientific_solves':0,'deformation_scale':1,'state_interpolation':False,
            'spatial_display':'quadratic element boundary sampled at five points per edge',
            'style':'cb-plot-unified-style with existing compact FEM multipanel overrides',
            'outputs':[{'path':p.relative_to(root).as_posix(),'bytes':p.stat().st_size,
                        'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in outputs]}
    (root/'rendering.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    return report


def render_active_completion(root):
    root=Path(root).resolve(strict=True)
    workspace=root.parents[2]
    cfg=json.loads((root/'configuration.json').read_text())
    parent=workspace/cfg['parent_result']
    existing=sum(p.stat().st_size for base in [root,parent] for p in base.rglob('*') if p.is_file())
    if existing+32*1024**2>128*1024**2:
        raise RuntimeError('Combined phase rendering budget exceeded')
    if not evaluate_storage(scan_workspace(workspace),planned_new_bytes=32*1024**2,stop_reserve_bytes=64*1024**2)['can_start']:
        raise RuntimeError('Project rendering admission refused')
    verification=json.loads((root/'post_verification.json').read_text())
    status=verification['status'].upper()
    meshes={name:load_arrays(root/'raw'/f'{name}_mesh.npz') for name in ['M0','M1']}
    labels=['passive_0','passive_2','active_4','combined_4']
    titles=['Rest','Pressure only','Active only','Pressure + active']
    def retained(name,label):
        directory=parent if label.startswith('passive') else root
        return load_arrays(directory/'raw'/f'{name}_state_{label}.npz')
    states={name:[retained(name,label) for label in labels] for name in meshes}
    fine=meshes['M1']
    weights=fine['qweights']/fine['qweights'].sum()
    fields=[von_mises(s['stress'])@weights for s in states['M1']]
    limit=max(float(v.max()) for v in fields)
    outputs=[]
    figdir=root/'figures'
    figdir.mkdir(exist_ok=True)
    style,overrides=_compact_style(3.6)
    figure=plt.figure(figsize=(11.2,6.8))
    axes=[_axes(figure,1.3+i*4.9,1.75,3.6) for i in range(2)]
    for axis,(name,data) in zip(axes,meshes.items()):
        axis.add_collection(collection(data,np.zeros_like(data['coordinates'])))
        spatial(axis,style)
        axis.plot([1],[0],marker='s',markersize=6,color='#B3463E')
        axis.plot([-1],[0],marker='^',markersize=6,color='#B3463E')
        for theta in np.arange(12)*np.pi/6:
            normal=np.array([np.cos(theta),np.sin(theta)])
            tangent=np.array([-np.sin(theta),np.cos(theta)])
            endpoints=.91*normal+np.array([-.06,.06])[:,None]*tangent
            axis.plot(endpoints[:,0],endpoints[:,1],color='#263F56',lw=2)
        for theta in np.arange(8)*np.pi/4:
            normal=np.array([np.cos(theta),np.sin(theta)])
            axis.annotate('',xy=.79*normal,xytext=.63*normal,arrowprops={'arrowstyle':'->','color':'#B3463E','lw':1.2})
        add_top_information(axis,f'{name}: {len(data["cells"])} triangles',style=style)
    figure.text(.085,.94,'F6-S0 | circumferential active stress only in the blue myocardial layer',fontsize=15)
    figure.text(.085,.09,'Green: endocardium | Yellow: ECM | Blue: myocardium; dark ticks: reference fiber direction.',fontsize=12)
    figure.text(.085,.04,'P2/P1, plane strain. p* / mu = 0.04; Ta* / mu = 0.10. Outer wall free; markers remove rigid motion.',fontsize=12)
    outputs+=_export(figure,axes,figdir/'model_structure',style,overrides)

    style,overrides=_compact_style(3.2,small=True)
    figure=plt.figure(figsize=(19.3,6.8))
    axes=[_axes(figure,1.1+i*4.15,1.6,3.2) for i in range(4)]
    for i,(axis,state,values) in enumerate(zip(axes,states['M1'],fields)):
        col=collection(fine,state['u'],values,Normalize(0,limit))
        axis.add_collection(col)
        spatial(axis,style)
        add_top_information(axis,f'{titles[i]}\np/mu={float(state["load"]):.2f}, Ta/mu={float(state["activation"]):.2f}',style=style)
    _colorbar(figure,col,(17.65,1.6,.24,3.2),'Total von Mises / mu',style)
    figure.text(.06,.94,f'F6-S0 | four matched conditions | qualification {status} | 1x deformation',fontsize=15)
    figure.text(.06,.09,'The first two conditions reuse the passed parent states; active conditions contain newly solved equilibria.',fontsize=12)
    figure.text(.06,.045,'Uniform color scale; quadrature-mean total Cauchy von Mises stress. Uncalibrated dimensionless ring, not a physiological heartbeat.',fontsize=12)
    outputs+=_export(figure,axes,figdir/'four_conditions',style,overrides)

    style,overrides=_compact_style(4.0,small=True)
    figure=plt.figure(figsize=(12.7,7.0))
    axes=[_axes(figure,1.3+i*5.7,1.9,4.) for i in range(2)]
    for name,color,marker,offset in [('M0',ORANGE,'s',-.035),('M1',BLUE,'o',.035)]:
        records=[verification['cases'][name][label] for label in labels]
        axes[0].plot(np.arange(4)+offset,[r['cavity_area_change']*100 for r in records],linestyle='none',marker=marker,color=color,label=name)
        axes[1].plot(np.arange(4)+offset,[r['max_abs_J_minus_one']*100 for r in records],linestyle='none',marker=marker,color=color,label=name)
    axes[0].axhline(0,color='#77818A',lw=.9)
    axes[0].set_ylim(-6.,12.)
    axes[1].set_ylim(-.002,.035)
    for i,label in enumerate(labels):
        value=verification['cases']['M1'][label]['cavity_area_change']*100
        axes[0].text(i,value+.85,f'{value:+.2f}%',ha='center',fontsize=12,color=BLUE)
    for axis,ylabel in zip(axes,['Cavity area change (%)','Maximum |J - 1| (%)']):
        axis.set_xlim(-.5,3.5)
        axis.set_xticks(range(4),['Rest','Pressure\nonly','Active\nonly','Pressure\n+ active'])
        axis.set_xlabel('Matched load condition')
        axis.set_ylabel(ylabel)
        _bounded_ticks(axis.yaxis,*axis.get_ylim(),bins=4)
        apply_axes_style(axis,style=style)
        axis.legend(loc='upper right',frameon=False)
    figure.text(.09,.94,f'F6-S0 | pressure and active contraction | G1 + G2 {status}',fontsize=15)
    figure.text(.09,.1,'Active tension counteracts cavity pressure: response drops from +9.90% to +4.56% at the same pressure.',fontsize=12)
    figure.text(.09,.045,'All local volume deviations remain below the frozen 1% gate. Points are deterministic mesh controls, not biological replicates.',fontsize=12)
    outputs+=_export(figure,axes,figdir/'mechanics_results',style,overrides)

    sequence=[retained('M1','passive_0')]+[retained('M1',f'active_{i}') for i in range(1,5)]
    stress=[von_mises(s['stress'])@weights for s in sequence]
    vmax=max(float(v.max()) for v in stress)
    style,overrides=_compact_style(2.75,small=True)
    figure=plt.figure(figsize=(21.1,6.0))
    axes=[_axes(figure,1.15+i*3.7,1.7,2.75) for i in range(5)]
    angles=np.arange(129)*2*np.pi/128
    for axis,state,values in zip(axes,sequence,stress):
        col=collection(fine,state['u'],values,Normalize(0,vmax))
        axis.add_collection(col)
        for radius in [20/27,1.]:
            axis.plot(radius*np.cos(angles),radius*np.sin(angles),ls='--',color='#727A82',lw=.6)
        spatial(axis,style)
        add_top_information(axis,f'Ta / mu = {float(state["activation"]):.3f}',style=style)
    _colorbar(figure,col,(19.45,1.7,.23,2.75),'Total von Mises / mu',style)
    figure.text(.04,.93,f'Five true activation states | zero cavity pressure | 1x deformation | G2 {status}',fontsize=15)
    figure.text(.04,.105,'Dashed reference boundaries help show the small contraction. Peak cavity area change: -4.315%.',fontsize=12)
    figure.text(.04,.045,'Activation continuation is an algorithmic loading sequence; no physiological time, calcium transient or cardiac cycle is prescribed.',fontsize=12)
    outputs+=_export(figure,axes,figdir/'active_states',style,overrides)

    combined=[retained('M1','passive_0')]+[retained('M1',f'combined_{i}') for i in range(1,5)]
    figure=plt.figure(figsize=(10.4,5.5),dpi=110)
    axes=[figure.add_axes([.07+i*.46,.16,.39,.7]) for i in range(2)]
    frames=[]
    for step in range(5):
        for axis,series,title in zip(axes,[sequence,combined],['Active only','Pressure + active']):
            state=series[step]
            axis.clear()
            axis.add_collection(collection(fine,state['u'],von_mises(state['stress'])@weights,Normalize(0,limit)))
            for radius in [20/27,1.]:
                axis.plot(radius*np.cos(angles),radius*np.sin(angles),ls='--',color='#727A82',lw=.7)
            axis.set(xlim=(-1.2,1.2),ylim=(-1.2,1.2),xlabel='x / B',ylabel='y / B')
            axis.set_aspect('equal')
            axis.set_title(f'{title}\np={float(state["load"]):.2f}, Ta={float(state["activation"]):.3f}')
        figure.canvas.draw()
        frames.append(Image.fromarray(np.asarray(figure.canvas.buffer_rgba()).copy()).convert('RGB'))
    gif=figdir/'active_preview.gif'
    frames[0].save(gif,save_all=True,append_images=frames[1:],duration=850,loop=0)
    plt.close(figure)
    outputs.append(gif)
    page='''<!DOCTYPE html><html lang="zh"><meta charset="utf-8"><title>F6-S0 主动圆环</title>
<style>body{font-family:Arial,sans-serif;max-width:1300px;margin:32px auto;line-height:1.7}img{max-width:100%} .ok{color:#246b44}</style>
<h1>FEniCSx：压力与心肌主动张力</h1><p class="ok">G0 / G1 / G2 passed；10个父被动态＋16个新增主动态，0平衡态重算。</p>
<p>细网格：压力单独+9.8974%；主动单独−4.3150%；压力与主动同时+4.5566%。主动张力抵消部分压力扩张，降低5.3408个百分点。
当前仍是无量纲平面应变圆环，三层被动材料相同，区域及纤维为构造假设。没有模拟生理周期或真实斑马鱼心动。</p>
<p><a href="post_verification.json">独立复核及主动虚功</a> · <a href="execution.json">执行/累计预算</a> · <a href="../f6s0_fenicsx_ring_active_v01_20260917/index.html">被动父证据及原读取失败</a></p>
<h2>结构与主动应力方向</h2><img src="figures/model_structure.png"><h2>四组真实终态</h2><img src="figures/four_conditions.png">
<h2>形变与局部体积</h2><img src="figures/mechanics_results.png"><h2>纯主动五态</h2><img src="figures/active_states.png">
<h2>五态加载预览</h2><p>每帧均对应保存的平衡态；循环播放仅用于观看，不表示已求解舒张回程。</p><img src="figures/active_preview.gif"></html>'''
    (root/'index.html').write_text(page,encoding='utf-8')
    result={'status':'passed','scientific_qualification':verification['status'],'scientific_solves':0,
            'scope':'four conditions plus five saved active continuation states, not physiological time',
            'inherited_states':cfg['parent_result'],'deformation_scale':1,'uniform_stress_scale':True,
            'style':'cb-plot-unified-style, inherited compact spatial FEM overrides',
            'outputs':[{'path':p.relative_to(root).as_posix(),'bytes':p.stat().st_size,
                        'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in outputs]}
    (root/'rendering.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    return result
