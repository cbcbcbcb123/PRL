"""Independent saved-geometry and provenance checks; no solver invocation."""
import hashlib
import json
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'results/ventricle_z1/z1_myo_sheet_relaxation_v01_20260914'
def read(path):return np.atleast_1d(np.genfromtxt(path,delimiter=',',names=True))
def main():
    checks={};details=[]
    for stage in ['Q','D']:
        hashes=json.loads((OUT/stage/'source_hashes_before.json').read_text())
        checks[stage+'_source_unchanged']=all(hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==h for p,h in hashes.items())
    for case in sorted((OUT/'D').glob('*_DT*')):
        if not case.is_dir():continue
        nodes=read(case/'nodes.csv');faces=read(case/'faces.csv');cells=read(case/'cells.csv')
        errors=[];angles=[];area_errors=[]
        for snap in np.unique(nodes['snapshot']):
            for cid in np.unique(nodes['cell']):
                a=nodes[(nodes['snapshot']==snap)&(nodes['cell']==cid)]
                f=faces[faces['cell']==cid];tri=np.column_stack([f[k] for k in ['a','b','c']]).astype(int)
                p=np.column_stack([a[k] for k in ['x','y','z']]);v=p[tri]
                vol=np.einsum('ij,ij->i',v[:,0],np.cross(v[:,1],v[:,2])).sum()/6
                row=cells[(cells['snapshot']==snap)&(cells['cell']==cid)][0]
                errors.append(abs(vol-row['volume'])/row['target_volume'])
                dual=np.zeros(len(p));areas=np.linalg.norm(np.cross(v[:,1]-v[:,0],v[:,2]-v[:,0]),axis=1)/2
                for j in range(3):np.add.at(dual,tri[:,j],areas/3)
                area_errors.append(float(np.max(abs(dual-a['area']))))
                for j in range(3):
                    u=v[:,(j+1)%3]-v[:,j];w=v[:,(j+2)%3]-v[:,j]
                    angles.append(float(np.degrees(np.arccos(np.clip(np.einsum('ij,ij->i',u,w)/(np.linalg.norm(u,axis=1)*np.linalg.norm(w,axis=1)),-1,1))).min()))
        ok=max(errors)<1e-12 and max(area_errors)<1e-12 and min(angles)>=15
        checks[case.name+'_geometry']=bool(ok);details.append(dict(case=case.name,volume_reporting_error=max(errors),dual_area_error=max(area_errors),minimum_angle=min(angles)))
    result=dict(status='passed' if all(checks.values()) else 'failed',checks=checks,details=details,scope='Independent saved mesh volume, nodal area, angle, source hashes; not biological validation')
    (OUT/'independent_verification.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps(result,indent=2))
if __name__=='__main__':main()
