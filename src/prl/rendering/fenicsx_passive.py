"""Portable saved-state contour report. No solver, meshing or interpolation in time."""
from dataclasses import asdict
import json
from pathlib import Path
import numpy as np


def load(path):
    with np.load(path,allow_pickle=False) as data:
        return {key:data[key] for key in data.files}


def boundary_polygons(mesh,u):
    # P2 triangle ordering: vertices, then opposite-edge midpoints.
    s=np.linspace(0,1,5)
    points=np.concatenate([np.column_stack((s,0*s)),np.column_stack((1-s,s)),np.column_stack((0*s,1-s))])
    b=np.column_stack((1-points.sum(axis=1),points))
    n=np.column_stack([b[:,i]*(2*b[:,i]-1) for i in range(3)]+[4*b[:,i]*b[:,j] for i,j in [(1,2),(0,2),(0,1)]])
    return np.einsum('qa,cai->cqi',n,(mesh['coordinates']+u)[mesh['cells']])


def stress_values(mesh,state):
    stress=state['stress']
    deviator=stress-np.trace(stress,axis1=-2,axis2=-1)[...,None,None]*np.eye(3)/3
    mises=np.sqrt(1.5*np.sum(deviator*deviator,axis=(-1,-2)))
    return mises@(mesh['qweights']/mesh['qweights'].sum())


def draw_passive(mesh_path,state_paths,geometry_path,verification_path,diagnosis_path,png_path,svg_path,gif_path,
                 style_module,axis_box_size_in=(3.6,3.6),figure_size_in=(14.4,13.0)):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.collections import PolyCollection
    from matplotlib.colors import Normalize
    from matplotlib.ticker import FixedLocator,MaxNLocator
    from PIL import Image

    mesh=load(mesh_path); geom=load(geometry_path)
    states=[load(path) for path in state_paths]
    verification=json.loads(Path(verification_path).read_text())
    diagnosis=json.loads(Path(diagnosis_path).read_text())
    if len(states)!=2 or [float(s['load']) for s in states]!=[0.,.02]:
        raise ValueError('This diagnostic requires exactly the two retained states')
    reports=[verification['cases']['M0'][f'passive_{i}'] for i in range(2)]
    style=style_module.StyleSpec(axis_box_size_in=axis_box_size_in,tick_label_size=16.,axis_label_size=18.,
        annotation_font_size=16.,sample_size_and_stat_font_size=14.,legend_font_size=14.,axes_line_width=1.5,
        major_tick_length_pt=5.,major_tick_width_pt=1.,minor_tick_length_pt=3.,minor_tick_width_pt=.8,
        data_line_width=1.5,tick_label_pad_pt=4.,axis_label_pad_pt=8.)
    default=asdict(style_module.DEFAULT_STYLE)
    overrides=[style_module.StyleOverride(field=k,reason='Reuse compact FEM engineering panel style with equal spatial aspect and explicit margins.')
               for k,v in asdict(style).items() if v!=default[k]]
    fig=plt.figure(figsize=figure_size_in)
    width,height=figure_size_in; side=axis_box_size_in[0]
    positions=[(1.3,7.6),(8.1,7.6),(1.3,2.4),(8.1,2.4)]
    axes=[fig.add_axes((x/width,y/height,side/width,side/height)) for x,y in positions]
    all_nodes=np.concatenate([mesh['coordinates']+state['u'] for state in states])
    low=all_nodes.min(axis=0); high=all_nodes.max(axis=0); center=(low+high)/2; half=max(high-low)*.56
    def ticks(axis,limits):
        values=MaxNLocator(nbins=4).tick_values(*limits)
        axis.set_major_locator(FixedLocator(values[(values>=limits[0])&(values<=limits[1])]))
    def spatial(ax):
        ax.set(xlim=(center[0]-half,center[0]+half),ylim=(center[1]-half,center[1]+half),xlabel='x / L',ylabel='y / L')
        ax.set_aspect('equal'); ticks(ax.xaxis,ax.get_xlim()); ticks(ax.yaxis,ax.get_ylim())
    palette=np.array(['#4C9F70','#D6B656','#5B8DB8'])
    polygons=[boundary_polygons(mesh,state['u']) for state in states]
    axes[0].add_collection(PolyCollection(polygons[0],facecolors=palette[mesh['layers']-1],edgecolors=(.1,.1,.1,.3),linewidths=.15))
    for anchor,marker,label in zip(geom['anchors'],['s','^'],['A','B']):
        axes[0].plot(*anchor,marker=marker,color='#B3463E',ms=7)
        axes[0].annotate(label,anchor,xytext=(5,8),textcoords='offset points',fontsize=14)
    inner=geom['xy'][geom['inner_nodes']]
    for i in np.linspace(0,len(inner)-1,8,dtype=int):
        a,b=inner[[i,(i+1)%len(inner)]]; tangent=b-a
        normal=np.array([tangent[1],-tangent[0]])/np.linalg.norm(tangent); point=(a+b)/2
        axes[0].annotate('',xy=point+.10*normal,xytext=point-.14*normal,arrowprops={'arrowstyle':'->','color':'#B3463E','lw':1.2})
    stress=[stress_values(mesh,state) for state in states]
    peak=max(float(v.max()) for v in stress)
    stress_collection=PolyCollection(polygons[1],array=stress[1],norm=Normalize(0,peak),cmap='YlGnBu',edgecolors=(.1,.1,.1,.25),linewidths=.15)
    axes[1].add_collection(stress_collection)
    deviation=np.max(np.abs(states[1]['J']-1),axis=1)*100
    volume_collection=PolyCollection(polygons[1],array=deviation,norm=Normalize(0,float(deviation.max())),cmap='YlOrRd',edgecolors=(.1,.1,.1,.2),linewidths=.15)
    axes[2].add_collection(volume_collection)
    for ax in axes[1:3]:
        for key in ['inner_nodes','outer_nodes']:
            curve=geom['xy'][geom[key]]; curve=np.vstack((curve,curve[0]))
            ax.plot(curve[:,0],curve[:,1],color='#777777',ls='--',lw=.8)
    worst=diagnosis['worst_cell']
    axes[2].plot(*polygons[1][worst].mean(axis=0),marker='o',mfc='none',mec='#651B16',ms=13,mew=1.5)
    for ax in axes[:3]: spatial(ax)
    def colorbar(collection,x,y,label):
        cax=fig.add_axes((x/width,y/height,.22/width,side/height))
        cb=fig.colorbar(collection,cax=cax); cb.set_label(label,labelpad=8,fontsize=style.axis_label_size)
        ticks(cax.yaxis,(collection.norm.vmin,collection.norm.vmax))
        cax.tick_params(labelsize=16,direction='out')
    colorbar(stress_collection,12.05,7.6,'Mean von Mises / mu')
    colorbar(volume_collection,5.25,2.4,'Max |J - 1| per cell (%)')
    pressures=[float(s['load']) for s in states]
    areas=[r['cavity_area_change']*100 for r in reports]
    axes[3].plot(pressures,areas,color='#777777',ls='--',lw=1.5)
    axes[3].plot(pressures[0],areas[0],'o',color='#4C9F70',ms=9,label='Accepted zero load')
    axes[3].plot(pressures[1],areas[1],'x',color='#B3463E',ms=11,mew=2,label='Failed local-J gate')
    axes[3].set(xlim=(-.002,.025),ylim=(-2,25),xlabel='Cavity pressure / mu',ylabel='Computed cavity area change (%)')
    ticks(axes[3].xaxis,axes[3].get_xlim()); ticks(axes[3].yaxis,axes[3].get_ylim())
    axes[3].legend(loc='upper left',frameon=False)
    titles=['A  Reference structure; p = 0','B  p / mu = 0.02; FAILED','C  Local volume deviation; FAILED','D  Two computed states only']
    for ax,title in zip(axes,titles):
        style_module.apply_axes_style(ax,style=style); style_module.add_top_information(ax,title,style=style)
    fig.text(.065,.958,'F6-S1-P | passive qualification FAILED at the first nonzero load | 1x deformation',fontsize=16)
    fig.text(.065,.925,f'Local max |J - 1| = {deviation.max():.3f}% > 1%; computed cavity change = {areas[1]:+.2f}% (not accepted).',fontsize=14)
    fig.text(.065,.105,'Green / yellow / blue: assumed endocardium / ECM / myocardium. A: ux=uy=0; B: uy=0; outer wall free.',fontsize=12)
    fig.text(.065,.070,'Dashed outlines: reference shape. Pressure steps are numerical continuation, NOT physiological time.',fontsize=12)
    fig.text(.065,.035,'Only 2 states saved: zero load passed; p=0.02 failed. Fine-mesh mechanics and the remaining 8 states were not run.',fontsize=12)
    exported=style_module.export_figure(fig,axes,Path(png_path).with_suffix(''),style=style,overrides=overrides)
    if Path(exported.svg)!=Path(svg_path):
        Path(exported.svg).replace(svg_path)
        manifest=json.loads(Path(exported.manifest).read_text()); manifest['exports']['svg']=str(Path(svg_path).resolve())
        Path(exported.manifest).write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    plt.close(fig)
    preview=plt.figure(figsize=(6.3,6.6),dpi=110); ax=preview.add_axes((.17,.21,.65,.65)); frames=[]
    for i,state in enumerate(states):
        ax.clear(); ax.add_collection(PolyCollection(polygons[i],array=stress[i],norm=Normalize(0,peak),cmap='YlGnBu',edgecolors=(.1,.1,.1,.2),linewidths=.12))
        spatial(ax); ax.set_title(f'p/mu = {float(state["load"]):.2f}; {reports[i]["status"].upper()}',fontsize=13)
        if i==0:
            preview.text(.10,.075,'Two saved states; 1x deformation; no time interpolation.',fontsize=10)
            preview.text(.10,.040,'Loop playback is NOT a simulated cardiac cycle.',fontsize=10)
        preview.canvas.draw(); frames.append(Image.fromarray(np.asarray(preview.canvas.buffer_rgba()).copy()).convert('RGB'))
    frames[0].save(gif_path,save_all=True,append_images=frames[1:],duration=1200,loop=0)
    plt.close(preview)
    return {'states':2,'equilibria_accepted':1,'scientific_gate':'failed','scientific_solves':0}
