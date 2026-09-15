"""Actual adaptive-step and static-force probe evidence; no new solving."""
import json
import numpy as np
import matplotlib.pyplot as plt
import render_myo_sheet_relaxation_v01 as common
from run_myo_long_doublet_v01 import OUT,ROOT
from run_myo_contact_barrier_v01 import read

def main():
    common.FIG=OUT/'figures';common.FIG.mkdir(exist_ok=True);p=json.loads((OUT/'P/verdict.json').read_text())['details'];x=[r['cells'] for r in p]
    curves=[(x,[r[key] for r in p],label,color,'-') for key,label,color in [('contact_seconds','Contact','#2678aa'),('guard_seconds','Geometry guard','#b3653a'),('elapsed_seconds','CLI total','#628745')]]
    common.quantitative('static_cost',curves,'Cell count','Wall time (s)',[2,4,16],[0,4,8,12,16],(-.5,16.5))
    curves=[]
    for direction,color in [('END','#2678aa'),('SIDE','#b3653a')]:
        a=read(OUT/f'A/{direction}/separation.csv');curves.append((a['coordinate'][1:],a['increment'][1:],direction,color,'-'))
    curves.append(([0,.8],[.2,.2],'Requested maximum','#777777','--'))
    common.quantitative('adaptive_steps',curves,'Relaxation coordinate','Accepted increment',[0,.2,.4,.6,.8],[0,.05,.1,.15,.2],(-.01,.23))
    common.spatial_style();fig=plt.figure(figsize=(15,5));tri=np.load(ROOT/'results/ventricle_z1/z1_myo_sheet_2d_m0_v01_20260914/geometry.npz')['faces']
    for i,count in enumerate([2,4,16]):
        a=read(OUT/f'P/{count}_cells/nodes.csv');data=np.zeros(len(a),dtype=a.dtype.descr+[('snapshot','f8'),('fixed','f8')])
        for k in a.dtype.names:data[k]=a[k]
        faces=np.zeros(count*len(tri),dtype=[('cell','i4'),('a','i4'),('b','i4'),('c','i4')])
        for cid in range(count):
            sl=slice(cid*len(tri),(cid+1)*len(tri));faces['cell'][sl]=cid
            for j,k in enumerate(['a','b','c']):faces[k][sl]=tri[:,j]
        ax=fig.add_subplot(1,3,i+1,projection='3d');common.panel(ax,data,faces,0);ax.set_title(f'{count} cells | static force probe')
    fig.suptitle('Actual initial meshes for timing | one sample per size | NOT tissue relaxation')
    fig.subplots_adjust(top=.82,left=.01,right=.99,bottom=.02);common.spatial_save(fig,'scaling_structures')
    path=OUT/'index.html';html=path.read_text(encoding='utf-8');extra='<h2>附加资格：真实步长裁切与静态性能</h2><p>请求步长上限.20时，两例各触发7次裁切。静态性能每个规模只有一次测量，不是统计缩放律；16胞没有推进形态。</p>'
    for title,file in [('实际安全步长裁切','adaptive_steps.png'),('静态探针结构','scaling_structures.png'),('静态接触/几何检查耗时','static_cost.png')]:extra+=f'<h3>{title}</h3><img src="figures/{file}" alt="{title}">'
    extra+='<p><a href="A/verdict.json">步长裁切裁决</a> · <a href="P/verdict.json">静态性能原始计时</a></p>'
    path.write_text(html.replace('</html>',extra+'</html>'),encoding='utf-8');print('Rendered adaptive and static scaling evidence.')

if __name__=='__main__':main()
