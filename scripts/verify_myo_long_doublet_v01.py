"""Offline saved-state adjudication after the complete long-run ledger closes."""
import hashlib
import json
import numpy as np
from run_myo_long_doublet_v01 import OUT,ROOT
from run_myo_contact_barrier_v01 import read
from run_myo_sheet_2d_m0_v01 import write_json
from diagnose_myo_sheet_saved_geometry_v01 import points,contained_witnesses,crossing_count
from myo_fold_monitor_v01 import mesh_metrics

def main():
    if not (OUT/'execution_status.json').exists():raise SystemExit('execution still running; no partial adjudication')
    ledger=json.loads((OUT/'execution_ledger.json').read_text());gates={};details=[];endpoints={};comparisons=[]
    provenance=json.loads((OUT/'source_hashes_before.json').read_text());gates['source_unchanged']=all(hashlib.sha256((ROOT/k).read_bytes()).hexdigest()==v for k,v in provenance.items())
    gates['matrix_complete']=len(ledger)==4 and all(r['returncode']==0 and r['first_failure'] is None for r in ledger)
    for record in ledger:
        case=OUT/record['case'];a=read(case/'nodes.csv');faces=read(case/'faces.csv');states=read(case/'states.csv');sep=read(case/'separation.csv');audits=read(case/'step_audits.csv');cells=read(case/'cells.csv')
        events=[];volumes0=[];v_errors=[];angles=[];cosines=[];area_errors=[];swept=[];previous=None
        tris=[np.column_stack([faces[faces['cell']==cid][k] for k in ['a','b','c']]).astype(int) for cid in [0,1]]
        snaps=np.unique(a['snapshot'])
        for index,snap in enumerate(snaps):
            meshes=[];b=a[a['snapshot']==snap];assert len(b)==388
            for cid in [0,1]:
                body=b[b['cell']==cid];p=points(body);t=p[tris[cid]];m=mesh_metrics(p,tris[cid]);meshes.append((p,t))
                if index==0:volumes0.append(m['volume'])
                v_errors.append(abs(m['volume']/volumes0[cid]-1));angles.append(m['min_angle']);cosines.append(m['adjacent_cosine'])
                dual=np.zeros(len(p));area=np.linalg.norm(np.cross(t[:,1]-t[:,0],t[:,2]-t[:,0]),axis=1)/2
                for j in range(3):np.add.at(dual,tris[cid][:,j],area/3)
                area_errors.append(float(abs(dual-body['area']).max()))
            p=points(b)
            if previous is not None:
                moved=float(np.linalg.norm(p-previous,axis=1).max());old=sep[min(index-1,len(sep)-1)]
                swept.append(2*moved/min(old['intercell_distance'],old['nonincident_distance']))
            previous=p;coordinate=float(b['coordinate'][0])
            if index==len(snaps)-1 or any(abs(coordinate-event)<1e-10 for event in [0,1.25,2.5,3.75,5]):
                (p,t),(q,u)=meshes;events.append({'coordinate':coordinate,'contained_nodes':len(contained_witnesses(p,u))+len(contained_witnesses(q,t)),'crossing_pairs':crossing_count(t,u),'self_crossings':sum(crossing_count(meshes[c][1],meshes[c][1],tris[c],tris[c]) for c in [0,1])})
        last=a[a['snapshot']==snaps[-1]];endpoints[record['case']]=points(last)-np.column_stack([last[k+'0'] for k in ['x','y','z']])
        numerical=all(np.isfinite(a[k]).all() for k in a.dtype.names) and abs(float(states['coordinate'][-1])-5)<1e-10 and max(v_errors)<=.02 and min(angles)>=15 and min(cosines)>-.95 and sep['intercell_distance'].min()>1e-8 and max(swept)<=.80000001 and max(area_errors)<1e-12 and audits['work_residual'].max()<=1e-10 and all(sum(e[k] for k in ['contained_nodes','crossing_pairs','self_crossings'])==0 for e in events)
        gates[record['case']]=bool(numerical);per_cell=[]
        for cid in [0,1]:
            b=cells[cells['cell']==cid];per_cell.append({'cell':cid,**{k+'_strain':float(b[k][-1]/b[k][0]-1) for k in ['length','width','thickness']}})
        details.append({'case':record['case'],'states':len(snaps),'final_coordinate':float(states['coordinate'][-1]),'minimum_gap':float(sep['intercell_distance'].min()),'final_gap':float(sep['intercell_distance'][-1]),'minimum_angle':min(angles),'minimum_adjacent_cosine':min(cosines),'maximum_volume_error':max(v_errors),'maximum_swept_ratio':max(swept),'maximum_area_error':max(area_errors),'maximum_work_residual':float(audits['work_residual'].max()),'final_force':float(states['max_free_force'][-1]),'static_equilibrium':'passed' if states['max_free_force'][-1]<=.001 else 'failed','events':events,'per_cell':per_cell})
    for direction in ['END','SIDE']:
        names=[f'{direction}_DT{dt:.2f}' for dt in [.02,.01]]
        if all(k in endpoints for k in names):
            error=float(np.linalg.norm(endpoints[names[0]]-endpoints[names[1]])/max(np.linalg.norm(endpoints[names[1]]),1e-12));gates[direction+'_dt']=error<=.02;comparisons.append({'direction':direction,'displacement_relative_error':error})
    report={'status':'passed' if all(gates.values()) else 'failed','gates':gates,'details':details,'comparisons':comparisons,'static_equilibrium':'passed' if len(details)==4 and all(d['static_equilibrium']=='passed' for d in details) else 'failed','scope':'algorithmic horizon 5 numerical qualification only; not asymptotic stability, biological validation or proof excluding every incident-vertex fold'}
    write_json(OUT/'long_verdict.json',report);print(json.dumps(report,indent=2))

if __name__=='__main__':main()
