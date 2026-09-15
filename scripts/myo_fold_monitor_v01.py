"""Read-only geometry metrics; no physical force or rest-shape definition."""
import io
import numpy as np

def adjacent_normal_minimum(p,tri):
    t=p[tri];normal=np.cross(t[:,1]-t[:,0],t[:,2]-t[:,0]);length=np.linalg.norm(normal,axis=1)
    if not np.isfinite(length).all() or np.any(length<=1e-14):return -1.
    normal/=length[:,None];edges={};pairs=[]
    for fid,ids in enumerate(tri):
        for j in range(3):
            key=tuple(sorted((int(ids[j]),int(ids[(j+1)%3]))))
            if key in edges:pairs.append((edges[key],fid))
            else:edges[key]=fid
    return min((float(normal[i]@normal[j]) for i,j in pairs),default=1.)

def mesh_metrics(p,tri):
    t=p[tri];volume=float(np.einsum('ij,ij->i',t[:,0],np.cross(t[:,1],t[:,2])).sum()/6)
    angles=[]
    for j in range(3):
        u=t[:,(j+1)%3]-t[:,j];v=t[:,(j+2)%3]-t[:,j]
        angles.append(float(np.degrees(np.arccos(np.clip(np.einsum('ij,ij->i',u,v)/(np.linalg.norm(u,axis=1)*np.linalg.norm(v,axis=1)),-1,1))).min()))
    return dict(volume=volume,min_angle=min(angles),adjacent_cosine=adjacent_normal_minimum(p,tri))

class CompleteNodeStream:
    """Consume only complete newline-terminated 388-node snapshots after flush."""
    def __init__(self,path,count=388):
        self.path=path;self.count=count;self.position=0;self.tail='';self.header=None;self.pending=[]
    def poll(self):
        if not self.path.exists():return []
        with self.path.open('r',encoding='utf-8',newline='') as stream:
            stream.seek(self.position);chunk=stream.read();self.position=stream.tell()
        lines=(self.tail+chunk).split('\n');self.tail=lines.pop();complete=[]
        for line in lines:
            if not line.strip():continue
            if self.header is None:self.header=line;continue
            self.pending.append(line)
            if len(self.pending)==self.count:
                data=np.genfromtxt(io.StringIO(self.header+'\n'+'\n'.join(self.pending)),delimiter=',',names=True)
                if len(np.unique(data['snapshot']))!=1:raise RuntimeError('incomplete or misaligned snapshot')
                complete.append(data);self.pending=[]
        return complete
