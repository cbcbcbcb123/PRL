"""Offline penetration witnesses on saved meshes; negatives are not a proof of no contact."""
import json
import numpy as np
from verify_myo_sheet_relaxation_v01 import OUT,read
def points(a):return np.column_stack([a[k] for k in ['x','y','z']])
def nearest_distance(p,t):
    e=t[:,1]-t[:,0];f=t[:,2]-t[:,0];v=p-t[:,0]
    aa=np.einsum('ij,ij->i',e,e);bb=np.einsum('ij,ij->i',e,f);cc=np.einsum('ij,ij->i',f,f)
    ve=np.einsum('ij,ij->i',v,e);vf=np.einsum('ij,ij->i',v,f);den=aa*cc-bb*bb
    u=(cc*ve-bb*vf)/den;w=(aa*vf-bb*ve)/den
    distances=np.full(len(t),np.inf);inside=(u>=0)&(w>=0)&(u+w<=1)
    distances[inside]=np.linalg.norm(v[inside]-u[inside,None]*e[inside]-w[inside,None]*f[inside],axis=1)
    for i in range(3):
        edge=t[:,(i+1)%3]-t[:,i];delta=p-t[:,i]
        alpha=np.clip(np.einsum('ij,ij->i',edge,delta)/np.einsum('ij,ij->i',edge,edge),0,1)
        distances=np.minimum(distances,np.linalg.norm(delta-alpha[:,None]*edge,axis=1))
    return float(distances.min())
def contained_witnesses(p,t):
    selected=np.flatnonzero(np.all((p>t.min(axis=(0,1))-1e-9)&(p<t.max(axis=(0,1))+1e-9),axis=1));result=[]
    for i in selected:
        a,b,c=(t[:,j]-p[i] for j in range(3));la,lb,lc=(np.linalg.norm(v,axis=1) for v in [a,b,c])
        numerator=np.einsum('ij,ij->i',a,np.cross(b,c));denominator=la*lb*lc+np.einsum('ij,ij->i',a,b)*lc+np.einsum('ij,ij->i',b,c)*la+np.einsum('ij,ij->i',c,a)*lb
        winding=float(np.sum(2*np.arctan2(numerator,denominator))/(4*np.pi))
        if abs(winding)>.5:
            depth=nearest_distance(p[i],t)
            if depth>1e-8:result.append({'node':int(i),'depth':depth,'winding':winding})
    return result
def crossing_count(a,b,tri_a=None,tri_b=None):
    overlap=np.all(a.min(axis=1)[:,None,:]<=b.max(axis=1)[None,:,:]+1e-10,axis=2)&np.all(b.min(axis=1)[None,:,:]<=a.max(axis=1)[:,None,:]+1e-10,axis=2)
    ia,ib=np.where(overlap)
    if tri_a is not None:
        keep=(ia<ib)&~np.any(tri_a[ia,:,None]==tri_b[ib,None,:],axis=(1,2));ia,ib=ia[keep],ib[keep]
    if not len(ia):return 0
    first,second=a[ia],b[ib];hit=np.zeros(len(ia),dtype=bool)
    for source,target in [(first,second),(second,first)]:
        e1=target[:,1]-target[:,0];e2=target[:,2]-target[:,0]
        for j in range(3):
            start=source[:,j];direction=source[:,(j+1)%3]-start;h=np.cross(direction,e2);det=np.einsum('ij,ij->i',e1,h)
            valid=abs(det)>1e-12;inv=np.divide(1.,det,out=np.zeros_like(det),where=valid)
            s=start-target[:,0];u=inv*np.einsum('ij,ij->i',s,h);q=np.cross(s,e1);v=inv*np.einsum('ij,ij->i',direction,q);fraction=inv*np.einsum('ij,ij->i',e2,q)
            hit|=valid&(u>=-1e-9)&(v>=-1e-9)&(u+v<=1+1e-9)&(fraction>1e-8)&(fraction<1-1e-8)
    return int(hit.sum())
def inspect_case(case):
    nodes=read(case/'nodes.csv');topology=case.parent/'recovered_initial_topology.csv' if case.name=='sheet' else case/'faces.csv';faces=read(topology);records=[]
    for snap in np.unique(nodes['snapshot']):
        meshes=[]
        for cid in np.unique(nodes['cell']):
            a=nodes[(nodes['snapshot']==snap)&(nodes['cell']==cid)];f=faces[faces['cell']==cid];tri=np.column_stack([f[k] for k in ['a','b','c']]).astype(int);p=points(a);meshes.append((p,tri,p[tri]))
        pairs=[];self_cross=[]
        for i,(p,tri,t) in enumerate(meshes):
            count=crossing_count(t,t,tri,tri)
            if count:self_cross.append({'cell':i,'crossing_triangle_pairs':count})
            for j in range(i+1,len(meshes)):
                q,_,other=meshes[j]
                if np.any(p.min(axis=0)>q.max(axis=0)+1e-9) or np.any(q.min(axis=0)>p.max(axis=0)+1e-9):continue
                first=contained_witnesses(p,other);second=contained_witnesses(q,t);crossings=crossing_count(t,other)
                if first or second or crossings:pairs.append({'cells':[i,j],'first_inside_second':first,'second_inside_first':second,'crossing_triangle_pairs':crossings})
        records.append({'snapshot':int(snap),'coordinate':float(nodes[nodes['snapshot']==snap]['coordinate'][0]),'intercell_witnesses':pairs,'self_crossing_witnesses':self_cross})
    return {'case':case.name,'states':records,'scope':'Positive proper crossing/inside-node witnesses identify overlap; no witnesses is not a complete coplanar-overlap proof.'}
def self_check():
    p=np.array([[0.,0,0],[1,0,0],[0,1,0],[0,0,1]]);tri=np.array([[0,2,1],[0,1,3],[0,3,2],[1,2,3]])
    assert len(contained_witnesses(np.array([[.1,.1,.1],[2,2,2]]),p[tri]))==1
    assert crossing_count(p[tri],p[tri],tri,tri)==0
    a=np.array([[[0.,0,0],[1,0,0],[0,1,0]]]);b=np.array([[[.2,.2,-1],[.2,.2,1],[.8,.2,1]]])
    assert crossing_count(a,b)==1
    assert crossing_count(a,b+10)==0
def main():
    self_check();results=[]
    for direction in ['END','SIDE']:results.append(inspect_case(OUT/f'D/{direction}_DT0.01'))
    if (OUT/'M/execution_ledger.json').exists():results.append(inspect_case(OUT/'M/sheet'))
    target=OUT/'saved_geometry_diagnostics.json'
    target.write_text(json.dumps({'self_checks':'passed','results':results},indent=2),encoding='utf-8')
    print(json.dumps([{'case':r['case'],'states':[{'coordinate':s['coordinate'],'overlapping_pairs':len(s['intercell_witnesses']),'self_crossing_cells':len(s['self_crossing_witnesses'])} for s in r['states']]} for r in results],indent=2))
if __name__=='__main__':main()
