"""Actual long-doublet geometry, fields and diagnostic plots."""
import io
import json
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.colors import Normalize
from PIL import Image
import render_myo_sheet_relaxation_v01 as common
from run_myo_long_doublet_v01 import OUT
from run_myo_contact_barrier_v01 import read

def main():
    verdict=json.loads((OUT/'long_verdict.json').read_text());common.FIG=OUT/'figures';common.FIG.mkdir(exist_ok=True)
    trajectories={d:(read(OUT/f'{d}_DT0.01/nodes.csv'),read(OUT/f'{d}_DT0.01/faces.csv')) for d in ['END','SIDE'] if (OUT/f'{d}_DT0.01/run.json').exists()}
    if not trajectories:
        case=verdict['details'][0]['case'];trajectories={case:(read(OUT/case/'nodes.csv'),read(OUT/case/'faces.csv'))}
    colors=['#2678aa','#b3653a'];xticks=[0,1.25,2.5,3.75,5]
    for name,column,label,yticks,ylim in [('residual','max_free_force','Free-node force',[0,.1,.2,.3,.4,.5],(-.02,.53)),('minimum_angle','min_angle','Minimum angle (deg)',[0,10,20,30,40],(-1,42))]:
        curves=[]
        for direction,color in zip(trajectories,colors):
            case=direction if '_DT' in direction else direction+'_DT0.01';a=read(OUT/case/'states.csv');curves.append((a['coordinate'],a[column],direction,color,'-'))
        threshold=.001 if column=='max_free_force' else 15.;curves.append(([0,5],[threshold,threshold],'Gate','#555555','--'))
        if column=='max_free_force':
            upper=max(.53,max(float(np.max(c[1])) for c in curves)*1.1);ylim=(-.02,upper);yticks=np.linspace(0,np.ceil(upper*10)/10,5);ylim=(-.02,float(yticks[-1])+.02)
        common.quantitative(name,curves,'Relaxation coordinate',label,xticks,yticks,ylim)
    curves=[]
    for direction,color in zip(trajectories,colors):
        case=direction if '_DT' in direction else direction+'_DT0.01';a=read(OUT/case/'separation.csv');curves.append((a['coordinate'],a['intercell_distance'],direction,color,'-'))
    maximum=max(float(np.max(c[1])) for c in curves);upper=max(.1,np.ceil(maximum*100)/100+.01)
    common.quantitative('minimum_gap',curves,'Relaxation coordinate','Minimum surface gap',xticks,np.arange(0,upper+.0001,.02),(-.003,upper+.003))
    curves=[]
    for direction,color in zip(trajectories,colors):
        case=direction if '_DT' in direction else direction+'_DT0.01';cells=read(OUT/case/'cells.csv');states=read(OUT/case/'states.csv')
        for cid in [0,1]:
            b=cells[cells['cell']==cid];curves.append((states['coordinate'],100*(b['length']/b['length'][0]-1),f'{direction} cell {cid+1}',color,'-' if cid==0 else '--'))
    upper=max(5,np.ceil(max(float(np.max(c[1])) for c in curves)/5)*5)
    common.quantitative('cell_length',curves,'Relaxation coordinate','Long-axis strain (%)',xticks,np.arange(0,upper+.001,5),(-.5,upper+.5))
    common.spatial_style();fig=plt.figure(figsize=(12,5))
    for i,(direction,(data,faces)) in enumerate(trajectories.items()):
        ax=fig.add_subplot(1,len(trajectories),i+1,projection='3d');common.panel(ax,data,faces,0);ax.set_title(direction+' | free doublet')
    fig.suptitle('Actual initial geometry | unchanged deterministic control\nConstant skeleton + positive-gap contact; no random perturbation or reference-shape energy')
    fig.subplots_adjust(top=.80,left=.02,right=.98,bottom=.02);common.spatial_save(fig,'structure')
    maximum=max(common.values(data,'contact').max() for data,_ in trajectories.values());frames=[]
    coordinates=xticks if verdict['status']=='passed' else [float(trajectories[next(iter(trajectories))][0]['coordinate'].max())]
    for index,coordinate in enumerate(coordinates):
        fig=plt.figure(figsize=(13,5.5))
        for i,(direction,(data,faces)) in enumerate(trajectories.items()):
            selected=data[np.isclose(data['coordinate'],coordinate,atol=1e-10,rtol=0)];snap=int(selected['snapshot'][0])
            ax=fig.add_subplot(1,len(trajectories),i+1,projection='3d');common.panel(ax,data,faces,snap,'contact',(0,maximum));ax.set_title(direction)
        cb=fig.add_axes([.91,.22,.016,.5]);fig.colorbar(plt.cm.ScalarMappable(norm=Normalize(0,maximum),cmap='viridis'),cax=cb,label='Contact traction magnitude / model units')
        fig.suptitle(f'Actual coordinate {coordinate:.2f} | algorithmic relaxation, NOT physiological time | true scale')
        fig.subplots_adjust(top=.83,left=.01,right=.87,bottom=.06);buffer=io.BytesIO();fig.savefig(buffer,format='png',dpi=110);buffer.seek(0);frames.append(Image.open(buffer).convert('RGB'));common.spatial_save(fig,f'state_{index}')
    frames[0].save(common.FIG/'long_doublet.gif',save_all=True,append_images=frames[1:],duration=1200,loop=0)
    for direction,(data,faces) in trajectories.items():
        snap=int(data['snapshot'].max());last=data[data['snapshot']==snap];fig=plt.figure(figsize=(15,5.5))
        for i,(field,title) in enumerate([('curvature','Curvature / inverse model length'),('pressure','Cell pressure / model units'),('displacement','Displacement / model length')]):
            values=common.values(last,field);low,high=float(values.min()),float(values.max())
            if field=='pressure':
                # Do not visually magnify sub-micro-unit cell-to-cell differences.
                low=min(0.,low);high=max(.01,float(np.ceil(high*100)/100))
            if high-low<1e-10:low=min(0.,low*1.1);high=max(1e-6,high*1.1)
            ax=fig.add_subplot(1,3,i+1,projection='3d');common.panel(ax,data,faces,snap,field,(low,high));ax.set_title(title);fig.colorbar(plt.cm.ScalarMappable(norm=Normalize(low,high),cmap='viridis'),ax=ax,shrink=.5,pad=.04)
        fig.suptitle(direction+' | actual last state | NOT accepted static equilibrium');fig.subplots_adjust(top=.83,left=.02,right=.96,bottom=.05);common.spatial_save(fig,direction.lower()+'_fields')
    html='<!doctype html><html lang="zh"><meta charset="utf-8"><title>长程双胞资格与形态异质性路线</title><style>body{font:18px sans-serif;max-width:1100px;margin:30px auto;line-height:1.7}img{width:100%}a{color:#246a99}</style><h1>长程双胞资格：'+verdict['status']+'</h1><p>算法坐标扩展至5，仍保持原材料、全自由边界与恒定骨架；无随机扰动、无周期收缩、无参考形状膜能。数值资格与静态平衡分别裁决。</p>'
    for title,file in [('模型结构','structure.png'),('五个实际状态：接触牵引','long_doublet.gif'),('未达到平衡的残力','residual.png'),('网格最小角','minimum_angle.png'),('胞间最小距离','minimum_gap.png'),('逐胞长轴形变','cell_length.png')]:html+=f'<h2>{title}</h2><img src="figures/{file}" alt="{title}">'
    for direction in trajectories:html+=f'<h2>{direction} 曲率、压力、形变</h2><img src="figures/{direction.lower()}_fields.png">'
    html+='<p>压力是逐胞标量，接触牵引不是完整应力张量。当前形态较整齐来自相同模板、相同方向与相同材料，确定性力学没有自然打破这些对称性。下一版本应区分稳定形态差异与时间波动，不能随意对节点加白噪声。</p><ul>'
    for title,path in [('完整数值裁决','long_verdict.json'),('实际命令与资源','execution_ledger.json'),('本轮合同','../../../project_control/ventricle_myocardial_long_doublet_contract_v01.md'),('形态不规则文献及采纳建议','../../../docs/myocardial_shape_variability_literature_v01.md')]:html+=f'<li><a href="{path}">{title}</a></li>'
    (OUT/'index.html').write_text(html+'</ul></html>',encoding='utf-8');print('Actual long-doublet figures rendered.')

if __name__=='__main__':main()
