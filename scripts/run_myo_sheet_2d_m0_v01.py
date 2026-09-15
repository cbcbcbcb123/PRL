"""Bounded geometry and actual SimuCell3D contact qualification; no tissue dynamics."""
from __future__ import annotations
import csv
import hashlib
import io
import json
import subprocess
import time
from collections import Counter
from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import PolyCollection
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/'results/ventricle_z1/z1_myo_sheet_2d_m0_v01_20260914'
EXE = ROOT/'b/z1m0a/Release/prl_myo_sheet_contact_probe_v01.exe'
POLYGON = np.array([[4.6,1.665],[0,3.33],[-4.6,1.665],[-4.6,-1.665],[0,-3.33],[4.6,-1.665]])*.99

def write_json(path, data):
    path.write_text(json.dumps(data,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8')

def geometry(level=2):
    points=np.array([[x,y,z] for z in [-2.65,2.65] for x,y in POLYGON]+[[0,0,-2.65],[0,0,2.65]])
    faces=[]
    for i in range(6):
        j=(i+1)%6
        faces.extend([[12,i,j],[13,i+6,j+6],[i,j,j+6],[i,j+6,i+6]])
    faces=np.array(faces)
    for face in faces:
        p=points[face]
        if np.dot(np.cross(p[1]-p[0],p[2]-p[0]),p.mean(axis=0))<0:
            face[1],face[2]=face[2],face[1]
    for _ in range(level):
        vertices=list(points); mids={}; new=[]
        def midpoint(a,b):
            key=tuple(sorted((int(a),int(b))))
            if key not in mids:
                mids[key]=len(vertices);vertices.append((points[a]+points[b])/2)
            return mids[key]
        for a,b,c in faces:
            ab,bc,ca=midpoint(a,b),midpoint(b,c),midpoint(c,a)
            new.extend([[a,ab,ca],[ab,b,bc],[ca,bc,c],[ab,bc,ca]])
        points=np.array(vertices);faces=np.array(new)
    return points,faces

def quality(points,faces):
    tri=points[faces]; cross=np.cross(tri[:,1]-tri[:,0],tri[:,2]-tri[:,0]); areas=np.linalg.norm(cross,axis=1)/2
    normals=cross/(2*areas[:,None]); max_outside=float(np.max(np.einsum('fvi,fi->fv',points[None,:,:]-tri[:,0,None,:],normals)))
    angles=[]
    for i in range(3):
        u=tri[:,(i+1)%3]-tri[:,i];v=tri[:,(i+2)%3]-tri[:,i]
        angles.extend(np.rad2deg(np.arccos(np.clip(np.sum(u*v,axis=1)/np.linalg.norm(u,axis=1)/np.linalg.norm(v,axis=1),-1,1))))
    directed=Counter((int(face[i]),int(face[(i+1)%3])) for face in faces for i in range(3))
    edges={tuple(sorted(k)) for k in directed}
    volume=float(np.sum(np.einsum('fi,fi->f',tri[:,0],cross))/6)
    return {'nodes':len(points),'faces':len(faces),'euler':len(points)-len(edges)+len(faces),'closed_oriented':all(directed[(b,a)]==v==1 for (a,b),v in directed.items()),'volume':volume,'minimum_angle_deg':float(min(angles)),'area':float(areas.sum()),'convex_outside_max':max_outside,'finite':bool(np.isfinite(points).all() and np.isfinite(areas).all()),'minimum_area':float(areas.min())}

def separation(first,second):
    edges=np.roll(POLYGON,-1,axis=0)-POLYGON
    axes=np.column_stack((edges[:,1],-edges[:,0]));axes/=np.linalg.norm(axes,axis=1)[:,None]
    gaps=[]
    for axis in axes:
        a=first@axis;b=second@axis
        gaps.append(max(float(b.min()-a.max()),float(a.min()-b.max())))
    return max(gaps)

def write_mesh(path, cells, faces):
    with path.open('w',encoding='utf-8') as stream:
        stream.write(str(len(cells))+'\n')
        for p in cells:
            stream.write(f'{len(p)} {len(faces)}\n')
            np.savetxt(stream,p,fmt='%.17g');np.savetxt(stream,faces,fmt='%d')

def save_pair(fig,name):
    fig.savefig(OUT/'figures'/f'{name}.png',dpi=180,bbox_inches='tight')
    fig.savefig(OUT/'figures'/f'{name}.svg',bbox_inches='tight');plt.close(fig)

def read_nodes(path):
    return np.genfromtxt(path,delimiter=',',names=True)

def probe_summary(data, faces, normal):
    force=np.column_stack([data[k] for k in ['fx','fy','fz']]);pos=np.column_stack([data[k] for k in ['x','y','z']]);initial=np.column_stack([data[k] for k in ['x0','y0','z0']])
    scale=np.linalg.norm(force,axis=1).sum();torques=np.cross(pos-pos.mean(axis=0),force)
    traction=np.linalg.norm(force,axis=1)/data['area']
    support=[]
    for cell_id in [0,1]:
        subset=data[data['cell']==cell_id];p=initial[data['cell']==cell_id];tri=p[faces]
        area=np.linalg.norm(np.cross(tri[:,1]-tri[:,0],tri[:,2]-tri[:,0]),axis=1)/2
        support.append(float(area[np.all(subset['coupled'][faces]>0,axis=1)].sum()))
    return {'normal_force_on_first':float(force[data['cell']==0].sum(axis=0)@normal),'force_absolute_sum':float(scale),'force_balance_absolute':float(np.linalg.norm(force.sum(axis=0))),'force_balance_relative':float(np.linalg.norm(force.sum(axis=0))/max(scale,1e-30)),'torque_balance_relative':float(np.linalg.norm(torques.sum(axis=0))/max(np.linalg.norm(torques,axis=1).sum(),1e-30)),'maximum_geometry_projection':float(np.linalg.norm(pos-initial,axis=1).max()),'coupled_nodes':int((data['coupled']>0).sum()),'fully_coupled_face_support_area_mean':float(np.mean(support)),'maximum_contact_traction':float(traction.max()),'finite':bool(all(np.isfinite(data[name]).all() for name in data.dtype.names))}

def render(cells,faces,geom,neighbors,metrics):
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'axes.spines.top':False,'axes.spines.right':False})
    fig=plt.figure(figsize=(13,6));ax=fig.add_subplot(121,projection='3d');top=fig.add_subplot(122)
    for i,p in enumerate(cells):
        color=plt.cm.tab20(i/16);ax.add_collection3d(Poly3DCollection(p[faces],facecolor=color,edgecolor='#555555',linewidth=.13,alpha=.88))
        center=p.mean(axis=0);top.add_patch(plt.Polygon(POLYGON+center[:2],facecolor=color,edgecolor='#333333'));top.text(*center[:2],str(i),ha='center',va='center')
    allp=np.concatenate(cells);lo=allp.min(axis=0);hi=allp.max(axis=0)
    ax.set(xlim=(lo[0]-1,hi[0]+1),ylim=(lo[1]-1,hi[1]+1),zlim=(-4,4));ax.set_box_aspect((hi-lo)*[1,1,1.4]);ax.view_init(35,-65)
    ax.set_title('Actual initial 3D meshes: 16 closed cells')
    top.autoscale_view();top.set_aspect('equal');top.set_title('Staggered packing / cell IDs / x-fiber direction');top.set_xlabel('x (model length)');top.set_ylabel('y (model length)')
    top.annotate('fiber x',xy=(12,-5),xytext=(4,-5),arrowprops={'arrowstyle':'->'})
    fig.suptitle('2D-M0 G0 geometry only | 384 triangles/cell | no shape relaxation yet');fig.tight_layout();save_pair(fig,'model_structure')
    fig,axs=plt.subplots(1,3,figsize=(13,4))
    axs[0].bar(['coarse','fine'],[geom['coarse']['minimum_angle_deg'],geom['fine']['minimum_angle_deg']]);axs[0].axhline(15,color='r',ls='--');axs[0].set_ylabel('Minimum angle (degrees)')
    centers=np.array([p.mean(axis=0)[:2] for p in cells])
    for a,b,gap in neighbors:axs[1].plot(centers[[a,b],0],centers[[a,b],1],color='#888888')
    axs[1].scatter(*centers.T,c=np.arange(16),cmap='tab20');axs[1].set_aspect('equal');axs[1].set_title(f'Geometric neighbors: {len(neighbors)} edges')
    axs[2].bar(np.arange(len(neighbors)),[n[2] for n in neighbors]);axs[2].axhline(.35,color='r',ls='--',label='capture cutoff');axs[2].set(ylabel='Separating-plane gap',xlabel='Neighbor interface');axs[2].legend()
    fig.suptitle('G0 geometric checks | neighbor edges do not imply adhesive bonds');fig.tight_layout();save_pair(fig,'geometry_checks')
    fig,axs=plt.subplots(2,2,figsize=(11,8))
    for col,direction in enumerate(['END','SIDE']):
        for level,style in [(2,'o-'),(3,'s--')]:
            rows=[m for m in metrics if m['direction']==direction and m['type_id']==4 and m['level']==level]
            axs[0,col].plot([r['gap'] for r in rows],[r['normal_force_on_first'] for r in rows],style,label=f'{384 if level==2 else 1536} faces')
            control=[m for m in metrics if m['direction']==direction and m['type_id']==0 and m['level']==level]
            axs[1,col].plot([r['gap'] for r in control],[r['maximum_geometry_projection'] for r in control],style,label=f'type 0 / level {level}')
        axs[0,col].axhline(0,color='k',lw=.6);axs[0,col].set(title=f'{direction}: myocardial type 4',ylabel='Normal force (+ attraction)',xlabel='Prescribed signed gap')
        axs[1,col].set(title='Type-0 diagnostic control only',ylabel='Position change inside contact call',xlabel='Prescribed signed gap')
        axs[0,col].legend();axs[1,col].legend()
    fig.suptitle('Actual kernel contact probes | position sweep, NOT time');fig.tight_layout();save_pair(fig,'contact_results')
    frames=[]
    for gap in [-.035,.07,.70]:
        fig,axs=plt.subplots(1,2,figsize=(11,4))
        for col,direction in enumerate(['END','SIDE']):
            record=next(m for m in metrics if m['gap']==gap and m['type_id']==4 and m['level']==2 and m['direction']==direction)
            data=read_nodes(OUT/record['nodes']);values=[];tris=[]
            for cid in [0,1]:
                d=data[data['cell']==cid];p=np.column_stack([d['x'],d['y'],d['z']]);f=np.column_stack([d['fx'],d['fy'],d['fz']]);traction=np.linalg.norm(f,axis=1)/d['area'];normal=np.cross(p[faces][:,1]-p[faces][:,0],p[faces][:,2]-p[faces][:,0]);mask=normal[:,2]>1e-8
                tris.extend(p[faces][mask,:,:2]);values.extend(traction[faces][mask].mean(axis=1))
            collection=PolyCollection(tris,array=np.array(values),cmap='magma',edgecolors='#777777',linewidths=.3);collection.set_clim(0,max(m['maximum_contact_traction'] for m in metrics if m['type_id']==4 and m['level']==2));axs[col].add_collection(collection);axs[col].autoscale_view();axs[col].set_aspect('equal');axs[col].set_title(direction)
            fig.colorbar(collection,ax=axs[col],label='Contact traction proxy')
        fig.suptitle(f'Type-4 actual contact fields | prescribed gap {gap:+.3f} | NOT time');fig.tight_layout()
        buffer=io.BytesIO();fig.savefig(buffer,format='png',dpi=110);buffer.seek(0);frames.append(Image.open(buffer).convert('RGB'))
        if gap==-.035:save_pair(fig,'contact_traction_mesh')
        else:plt.close(fig)
    frames[0].save(OUT/'figures/contact_gap_scan.gif',save_all=True,append_images=frames[1:],duration=1000,loop=0)

def main():
    if OUT.exists():raise SystemExit('create-only output exists')
    if not EXE.is_file():raise SystemExit('build probe first')
    OUT.mkdir(parents=True);(OUT/'figures').mkdir();(OUT/'inputs').mkdir()
    write_json(OUT/'ownership.json',{'task':'2D-M0 G0/C0','purpose':'formal scientific evidence, not temporary','gpu':0})
    points,faces=geometry(2);fine,finefaces=geometry(3)
    geom={'coarse':quality(points,faces),'fine':quality(fine,finefaces)}
    cells=[points+[col*9.2+(row%2)*4.6,row*4.995,0] for row in range(4) for col in range(4)]
    write_mesh(OUT/'inputs/sheet.mesh',cells,faces)
    np.savez_compressed(OUT/'geometry.npz',points=np.array(cells),faces=faces,polygon=POLYGON)
    neighbors=[];pair_gaps=[]
    for i in range(16):
        for j in range(i+1,16):
            gap=separation(POLYGON+cells[i].mean(axis=0)[:2],POLYGON+cells[j].mean(axis=0)[:2]);pair_gaps.append(gap)
            if gap<.35:neighbors.append([i,j,gap])
    visited={0}
    for _ in range(16):
        for a,b,gap in neighbors:
            if a in visited or b in visited:visited.update([a,b])
    geometry_pass=all(q['finite'] and q['closed_oriented'] and q['euler']==2 and q['volume']>0 and q['minimum_angle_deg']>=15 and q['convex_outside_max']<1e-9 and q['minimum_area']>0 for q in geom.values()) and min(pair_gaps)>0 and len(visited)==16
    geom.update(status='passed' if geometry_pass else 'failed',cell_count=16,neighbors=neighbors,all_pair_minimum_separating_gap=min(pair_gaps),connected_cells=len(visited),footprint_interstitial_fraction=1-.99**2)
    write_json(OUT/'geometry_verdict.json',geom)
    metrics=[];ledger=[];start=time.monotonic()
    if geometry_pass:
        for level in [2,3]:
            p,f=geometry(level)
            for direction in ['END','SIDE']:
                normal=np.array([1.,0,0]) if direction=='END' else np.array([1.665,4.6,0]);normal/=np.linalg.norm(normal)
                center=np.array([9.2,0,0]) if direction=='END' else np.array([4.6,4.995,0])
                original_gap=float(center@normal-2*np.max(p@normal))
                for gap in [-.035,.07,.70]:
                    second=p+center+normal*(gap-original_gap)
                    tag=f'{direction}_L{level}_G{gap:+.3f}'
                    input_path=OUT/'inputs'/f'{tag}.mesh';write_mesh(input_path,[p,second],f)
                    for type_id in [4,0]:
                        name=tag+f'_TYPE{type_id}';destination=OUT/'raw'/name
                        cmd=[str(EXE),str(input_path),str(destination),str(type_id)]
                        result=subprocess.run(cmd,capture_output=True,text=True,timeout=30)
                        ledger.append({'case':name,'command':cmd,'returncode':result.returncode,'stdout':result.stdout,'stderr':result.stderr})
                        write_json(OUT/'execution_ledger.json',ledger)
                        if result.returncode:raise RuntimeError(f'probe failed: {name}: {result.stderr}')
                        data=read_nodes(destination/'nodes.csv');record=probe_summary(data,f,normal)
                        record.update(direction=direction,level=level,gap=gap,type_id=type_id,nodes=str((destination/'nodes.csv').relative_to(OUT)).replace('\\','/'))
                        metrics.append(record)
                        if time.monotonic()-start>300:raise RuntimeError('frozen contact budget exceeded')
    write_json(OUT/'contact_metrics.json',metrics)
    primary=[m for m in metrics if m['type_id']==4]
    near=[m for m in primary if m['gap']==.07]
    adhesive=bool(near) and all(m['normal_force_on_first']>1e-12 or m['coupled_nodes']>0 for m in near)
    contact_status='failed' if not adhesive else 'unknown'
    verdict={'status':'failed' if geometry_pass else 'failed','G0':geom['status'],'C0':contact_status if geometry_pass else 'not_run','M0_static_relaxation':'not_run','reason':'myocardial_type_4_has_no_positive_gap_adhesion_or_coupling' if geometry_pass and not adhesive else 'additional_contact_gates_required','biological_validation':'blocked','parent_Z1':'blocked','gpu':0,'contact_probe_count':len(metrics),'elapsed_contact_seconds':time.monotonic()-start,'coordinate_semantics':'independent_prescribed_gap_probe_not_time','all_primary_force_balance_pass':all(m['force_balance_relative']<=1e-10 for m in primary),'all_primary_torque_balance_pass':all(m['torque_balance_relative']<=1e-10 for m in primary)}
    write_json(OUT/'verdict.json',verdict)
    sources=[Path(__file__),ROOT/'src/ventricle_simucell3d_m0/myo_sheet_contact_probe_v01.cpp',ROOT/'src/ventricle_simucell3d_m0/ventricle_simucell3d_m0.cpp',ROOT/'external/simucell3d/src/contact_models/contact_face_face_via_coupling.cpp',ROOT/'external/simucell3d/include/global_configuration.hpp',ROOT/'project_control/ventricle_myocardial_sheet_2d_m0_contract_v01.md',EXE]
    write_json(OUT/'source_hashes.json',{str(p.relative_to(ROOT)).replace('\\','/'):hashlib.sha256(p.read_bytes()).hexdigest() for p in sources})
    render(cells,faces,geom,neighbors,metrics)
    links=['figures/model_structure.png','figures/geometry_checks.png','figures/contact_results.png','figures/contact_traction_mesh.png','figures/contact_gap_scan.gif']
    body='<h1>2D-M0: geometry and contact qualification</h1><p>G0 '+geom['status']+'; C0 '+contact_status+'; tissue relaxation NOT RUN. Static prescribed-gap probes, not physiological time.</p>'
    body+=''.join(f'<h2>{p}</h2><img src="{p}" style="width:100%">' for p in links)
    body+='<p>Type 0 is a kernel-semantic diagnostic control, not an accepted myocardial replacement. Its contact call may directly project node positions; a zero force alone does not establish no adhesion.</p>'
    body+=''.join(f'<p><a href="{p}">{p}</a></p>' for p in ['verdict.json','geometry_verdict.json','contact_metrics.json','execution_ledger.json','geometry.npz','source_hashes.json'])
    (OUT/'index.html').write_text('<!doctype html><meta charset="utf-8"><title>2D-M0 qualification</title><main style="max-width:1200px;margin:30px auto;font-family:Arial">'+body+'</main>',encoding='utf-8')
    print(json.dumps(verdict,indent=2))
    return 0

if __name__=='__main__':raise SystemExit(main())
