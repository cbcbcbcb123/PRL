"""Render actual saved Q/D/M data; never synthesize unsaved tissue states."""
import io
import json
from pathlib import Path
import sys
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import Normalize
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
from PIL import Image
from verify_myo_sheet_relaxation_v01 import ROOT,OUT,read
sys.path.insert(0,'C:/Users/chenb/.codex/skills/cb-plot-unified-style/assets')
from cb_plot_unified_style import StyleSpec,create_figure_with_axis_box,apply_axes_style,export_figure
# 作图调整参数：沿用项目已确认10×5in主轴框；空间网格例外为真实等比例。
STYLE=StyleSpec(axis_box_size_in=(10.,5.))
FIG=OUT/'figures'
def load(path):return json.loads(path.read_text(encoding='utf-8'))
def quantitative(name,curves,xlabel,ylabel,xticks,yticks,ylim):
    fig,ax=create_figure_with_axis_box(style=STYLE,margins_in=(2.,.8,1.8,2.5))
    for x,y,label,color,ls in curves:ax.plot(x,y,label=label,color=color,ls=ls,lw=3,marker='o',ms=7)
    ax.set(xlabel=xlabel,ylabel=ylabel,ylim=ylim)
    ax.set_xticks(xticks);ax.set_yticks(yticks)
    fig.legend(*ax.get_legend_handles_labels(),loc='upper center',bbox_to_anchor=(.56,.97),ncol=2,frameon=False)
    apply_axes_style(ax,style=STYLE);ax.set_xticks(xticks);ax.set_yticks(yticks)
    export_figure(fig,ax,FIG/name,style=STYLE);plt.close(fig)
def spatial_style():
    plt.rcParams.update({'font.size':11,'axes.labelsize':11,'axes.titlesize':12,'xtick.labelsize':10,'ytick.labelsize':10,'axes.linewidth':.8,'svg.fonttype':'none'})
def spatial_save(fig,name):
    fig.savefig(FIG/f'{name}.png',dpi=180);fig.savefig(FIG/f'{name}.svg');plt.close(fig)
def coords(a):return np.column_stack([a[k] for k in ['x','y','z']])
def values(a,field):
    if field=='contact':return np.linalg.norm(np.column_stack([a[k] for k in ['cfx','cfy','cfz']]),axis=1)/a['area']
    if field=='displacement':return np.linalg.norm(coords(a)-np.column_stack([a[k+'0'] for k in ['x','y','z']]),axis=1)
    return a[field]
def panel(ax,data,faces,snapshot,field='identity',limits=None,top=False):
    a=data[data['snapshot']==snapshot]
    for cid in np.unique(a['cell']):
        b=a[a['cell']==cid];f=faces[faces['cell']==cid];tri=np.column_stack([f[k] for k in ['a','b','c']]).astype(int);p=coords(b)
        colors=plt.cm.tab20(int(cid)%20) if field=='identity' else plt.cm.viridis(Normalize(*limits)(values(b,field)[tri].mean(axis=1)))
        ax.add_collection3d(Poly3DCollection(p[tri],facecolors=colors,edgecolor='#454545',linewidth=.14))
        fixed=b['fixed']>0
        if fixed.any():ax.scatter(*p[fixed].T,color='#e22b34',s=6,depthshade=False)
    p=coords(data);lo=p.min(axis=0)-.4;hi=p.max(axis=0)+.4
    ax.set(xlim=(lo[0],hi[0]),ylim=(lo[1],hi[1]),zlim=(lo[2],hi[2]));ax.set_box_aspect(hi-lo);ax.view_init(90,-90) if top else ax.view_init(48,-63)
    ax.set_axis_off()
def main():
    FIG.mkdir(exist_ok=True)
    q=load(OUT/'Q/verdict.json')['comparisons'];labels=['END -','END +','SIDE -','SIDE +']
    quantitative('quadrature_error',[(np.arange(4),[100*r[key] for r in q],label,color,'-') for key,label,color in [('force_relative','Force','#2678aa'),('energy_relative','Energy','#a86135'),('traction_L2_relative','Traction L2','#5c9d64')]],'Contact case index','Refinement change (%)',[0,1,2,3],[0,.2,.4,.6],(-.03,.65))
    trajectories={d:(read(OUT/f'D/{d}_DT0.01/nodes.csv'),read(OUT/f'D/{d}_DT0.01/faces.csv')) for d in ['END','SIDE']}
    curves=[]
    for direction,color in [('END','#2678aa'),('SIDE','#b3653a')]:
        a=read(OUT/f'D/{direction}_DT0.01/cells.csv')
        for cid in [0,1]:
            b=a[a['cell']==cid];curves.append((np.arange(5)/4,100*(b['length']/b['length'][0]-1),f'{direction} cell {cid+1}',color,'-' if cid==0 else '--'))
    quantitative('doublet_length',curves,'Relaxation coordinate','Long-axis strain (%)',[0,.25,.5,.75,1],[0,1,2,3],(-.15,3.15))
    diagnostic=load(OUT/'saved_geometry_diagnostics.json');penetration_curves=[]
    for record,color in zip(diagnostic['results'][:2],['#2678aa','#b3653a']):
        x=[];y=[]
        for state in record['states']:
            depths=[p['depth'] for pair in state['intercell_witnesses'] for p in pair['first_inside_second']+pair['second_inside_first']]
            x.append(state['coordinate']);y.append(max(depths,default=0))
        penetration_curves.append((x,y,record['case'].split('_')[0],color,'-'))
    quantitative('penetration_failure',penetration_curves,'Relaxation coordinate','Penetration depth',[0,.25,.5,.75,1],[0,.05,.1,.15,.2],(-.008,.21))
    spatial_style()
    fig=plt.figure(figsize=(12,5))
    for i,(direction,(data,faces)) in enumerate(trajectories.items()):
        ax=fig.add_subplot(1,2,i+1,projection='3d');panel(ax,data,faces,0);ax.set_title(direction+' | all surfaces free')
    fig.suptitle('D: two deformable cells | constant skeleton prestress | no cyclic contraction');fig.subplots_adjust(top=.84,left=.02,right=.98,bottom=.02);spatial_save(fig,'doublet_structure')
    maximum=max(values(data,'contact').max() for data,_ in trajectories.values());frames=[]
    for snapshot in range(5):
        fig=plt.figure(figsize=(13,5.5))
        for i,(direction,(data,faces)) in enumerate(trajectories.items()):
            ax=fig.add_subplot(1,2,i+1,projection='3d');panel(ax,data,faces,snapshot,'contact',(0,maximum));ax.set_title(direction)
        cb=fig.add_axes([.91,.22,.016,.5]);fig.colorbar(plt.cm.ScalarMappable(norm=Normalize(0,maximum),cmap='viridis'),cax=cb,label='Contact force / area (model units)')
        fig.suptitle(f'Actual D state: relaxation coordinate {snapshot/4:.2f} | NOT physiological time | true scale');fig.subplots_adjust(top=.83,left=.01,right=.87,bottom=.06)
        buffer=io.BytesIO();fig.savefig(buffer,format='png',dpi=110);buffer.seek(0);frames.append(Image.open(buffer).convert('RGB'))
        spatial_save(fig,f'doublet_state_{snapshot}')
    frames[0].save(FIG/'doublet_relaxation.gif',save_all=True,append_images=frames[1:],duration=1100,loop=0)
    data,faces=trajectories['SIDE'];last=data[data['snapshot']==4]
    fig=plt.figure(figsize=(15,5.5))
    for i,(field,title) in enumerate([('curvature','Curvature / inverse model length'),('pressure','Cell pressure / model units'),('displacement','Displacement / model length')]):
        limits=(float(values(last,field).min()),float(values(last,field).max()))
        if limits[1]-limits[0]<1e-10:limits=(0.,max(1e-6,limits[1]*1.1))
        ax=fig.add_subplot(1,3,i+1,projection='3d');panel(ax,data,faces,4,field,limits);ax.set_title(title);fig.colorbar(plt.cm.ScalarMappable(norm=Normalize(*limits),cmap='viridis'),ax=ax,shrink=.5,pad=.04)
    fig.suptitle('D / SIDE actual endpoint at coordinate 1.00 | short trajectory, NOT static equilibrium');fig.subplots_adjust(top=.83,left=.02,right=.96,bottom=.05);spatial_save(fig,'doublet_fields')
    fig,axes=plt.subplots(2,2,figsize=(13,10));plane=.013
    for row,(direction,(data,faces)) in enumerate(trajectories.items()):
        segments=[];centers=[]
        for cid,color in [(0,'#2678aa'),(1,'#bf642f')]:
            a=data[(data['snapshot']==4)&(data['cell']==cid)];f=faces[faces['cell']==cid];p=coords(a);tri=np.column_stack([f[k] for k in ['a','b','c']]).astype(int);centers.append(p.mean(axis=0))
            for t in p[tri]:
                crossing=[]
                for j in range(3):
                    first,second=t[j],t[(j+1)%3]
                    if (first[2]-plane)*(second[2]-plane)<0:crossing.append(first+(second-first)*(plane-first[2])/(second[2]-first[2]))
                if len(crossing)==2:
                    segment=np.array(crossing);segments.append(segment)
                    for ax in axes[row]:ax.plot(segment[:,0],segment[:,1],color=color,lw=2)
        for ax in axes[row]:ax.set_aspect('equal');ax.set(xlabel='x / model length',ylabel='y / model length');ax.tick_params(labelsize=10)
        allp=coords(data);axes[row,0].set_xlim(allp[:,0].min()-.3,allp[:,0].max()+.3);axes[row,0].set_ylim(allp[:,1].min()-.3,allp[:,1].max()+.3)
        center=(centers[0]+centers[1])/2;axes[row,1].set_xlim(center[0]-1.2,center[0]+1.2);axes[row,1].set_ylim(center[1]-1.2,center[1]+1.2)
        axes[row,0].set_title(direction+' full cross-section');axes[row,1].set_title(direction+' interface magnified spatial view')
    fig.suptitle('Actual D endpoint surface intersections | z = 0.013 slice | blue/orange = separate cells\nZoom changes viewing window only, never node positions');fig.subplots_adjust(left=.08,right=.96,bottom=.07,top=.9,wspace=.26,hspace=.28);spatial_save(fig,'penetration_sections')
    # M fields are rendered only from flushed native snapshots, never from interpolation.
    mpath=OUT/'M/sheet/nodes.csv'
    if (OUT/'M/execution_ledger.json').exists() and mpath.exists() and mpath.stat().st_size>0:
        data=read(mpath);faces=read(OUT/'M/recovered_initial_topology.csv');snaps=np.unique(data['snapshot']).astype(int)
        for snap in [snaps[0],snaps[-1]] if len(snaps)>1 else [snaps[0]]:
            fig=plt.figure(figsize=(12,8));ax=fig.add_subplot(111,projection='3d');panel(ax,data,faces,snap)
            coordinate=float(data[data['snapshot']==snap]['coordinate'][0]);fig.suptitle(f'M: 16 cells | actual coordinate {coordinate:.2f} | red = fixed end-cap nodes');fig.subplots_adjust(left=.02,right=.98,bottom=.02,top=.9);spatial_save(fig,'sheet_initial' if snap==0 else 'sheet_last_saved')
        if len(snaps)>1:
            snap=snaps[-1];last=data[data['snapshot']==snap];fig=plt.figure(figsize=(15,7))
            for i,(field,title) in enumerate([('contact','Contact traction / model units'),('pressure','Pressure / model units'),('displacement','Displacement / model length')]):
                limits=(0.,max(1e-9,float(values(last,field).max())))
                if field=='pressure':limits=(min(0.,float(values(last,field).min())),limits[1])
                ax=fig.add_subplot(1,3,i+1,projection='3d');panel(ax,data,faces,snap,field,limits,top=True);ax.set_title(title);fig.colorbar(plt.cm.ScalarMappable(norm=Normalize(*limits),cmap='viridis'),ax=ax,shrink=.5,pad=.03)
            fig.suptitle(f'M last saved state at coordinate {last["coordinate"][0]:.2f} | NOT accepted equilibrium');fig.subplots_adjust(top=.88,left=.02,right=.95,bottom=.07);spatial_save(fig,'sheet_fields')
        audits=read(OUT/'M/sheet/step_audits.csv')
        if len(audits)>0:
            x=audits['coordinate'];y=audits['max_free_force'];maximum=float(y.max())
            quantitative('sheet_residual',[(x,y,'Maximum free-node force','#2678aa','-'),([0,float(x.max())],[.001,.001],'Equilibrium gate','#b34f4f','--')],'Relaxation coordinate','Free-node force',[0,float(x.max())/2,float(x.max())],[0,.1,.2,.3],(-.01,max(.34,maximum*1.05)))
    print('Rendered actual saved states only.')
if __name__=='__main__':main()
