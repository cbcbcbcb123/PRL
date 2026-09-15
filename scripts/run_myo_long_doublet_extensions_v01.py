"""Conditional actual adaptive-step and static scaling probes; no tissue dynamics."""
import hashlib
import json
from pathlib import Path
import subprocess
import time
import numpy as np
from run_myo_long_doublet_v01 import OUT,ROOT
from run_myo_contact_barrier_v01 import ENGINE,OUT as PREVIOUS,read
from run_myo_sheet_short_dynamics_v01 import bounded_run
from run_myo_sheet_2d_m0_v01 import write_json,write_mesh
from diagnose_myo_sheet_saved_geometry_v01 import inspect_case

PROBE=ROOT/'b/z1m0a/Release/prl_myo_contact_scaling_probe_v01.exe'
def adaptive():
    assert json.loads((OUT/'long_verdict.json').read_text())['status']=='passed'
    target=OUT/'A';target.mkdir(exist_ok=False);ledger=[];results=[]
    for direction in ['END','SIDE']:
        case=target/direction;command=[str(ENGINE),str(PREVIOUS/f'S/inputs/{direction}_G0.07.mesh'),str(case),'.20','4','free','55']
        record=bounded_run(command,target/f'{direction}.log',60);ledger.append(record);write_json(target/'execution_ledger.json',ledger)
        if record['returncode']!=0:
            write_json(target/'verdict.json',{'status':'failed','reason':'native/resource exit','calls':len(ledger)});return
        sep=read(case/'separation.csv');states=read(case/'states.csv');nodes=read(case/'nodes.csv');clipped=[];ratios=[]
        for j in range(1,len(sep)):
            before=float(sep['coordinate'][j-1]);next_event=(np.floor((before+1e-10)/.2)+1)*.2
            request=min(.2,.8-before,next_event-before)
            if sep['increment'][j]<request-1e-10:clipped.append(int(sep['step'][j]))
            old=nodes[nodes['snapshot']==j-1];new=nodes[nodes['snapshot']==j];movement=np.linalg.norm(np.column_stack([new[k]-old[k] for k in ['x','y','z']]),axis=1).max()
            ratios.append(float(2*movement/min(sep['intercell_distance'][j-1],sep['nonincident_distance'][j-1])))
        geometry=inspect_case(case);write_json(case/'offline_geometry.json',geometry)
        okay=bool(clipped) and abs(states['coordinate'][-1]-.8)<1e-10 and states['min_angle'].min()>=15 and states['max_volume_error'].max()<=.02 and max(ratios)<=.80000001 and all(not r['intercell_witnesses'] and not r['self_crossing_witnesses'] for r in geometry['states'])
        results.append({'direction':direction,'passed':bool(okay),'clipped_steps':clipped,'accepted_steps':len(sep)-1,'minimum_gap':float(sep['intercell_distance'].min()),'maximum_swept_ratio':max(ratios)})
        if not okay:break
    write_json(target/'verdict.json',{'status':'passed' if len(results)==2 and all(r['passed'] for r in results) else 'failed','details':results,'scope':'actual adaptive clipping safety at requested dt .20; not time-accuracy qualification'})
    print(json.dumps(results,indent=2))

def performance():
    assert json.loads((OUT/'A/verdict.json').read_text())['status']=='passed'
    target=OUT/'P';target.mkdir(exist_ok=False);(target/'inputs').mkdir()
    source=ROOT/'results/ventricle_z1/z1_myo_sheet_2d_m0_v01_20260914/geometry.npz';data=np.load(source);ledger=[];started=time.monotonic()
    write_json(target/'source_hashes.json',{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [PROBE,Path(__file__),source,ROOT/'src/ventricle_simucell3d_m0/myo_contact_scaling_probe_v01.cpp']})
    for count,indices in [(2,[0,1]),(4,[0,1,4,5]),(16,list(range(16)))]:
        mesh=target/'inputs'/f'{count}_cells.mesh';write_mesh(mesh,data['points'][indices],data['faces']);case=target/f'{count}_cells';command=[str(PROBE),str(mesh),str(case),'4','quadrature','1.0','.10'];began=time.monotonic()
        r=subprocess.run(command,cwd=ROOT,capture_output=True,text=True,timeout=min(60,180-(time.monotonic()-started)))
        record={'cells':count,'command':command,'returncode':r.returncode,'stdout':r.stdout,'stderr':r.stderr,'elapsed_seconds':time.monotonic()-began}
        if r.returncode==0:
            record.update(json.loads((case/'contact.json').read_text()));a=read(case/'nodes.csv');p=np.column_stack([a[k] for k in ['x','y','z']]);force=np.column_stack([a[k] for k in ['fx','fy','fz']]);total=np.linalg.norm(force,axis=1).sum();torque=np.cross(p-p.mean(axis=0),force)
            record['force_balance']=float(np.linalg.norm(force.sum(axis=0))/max(total,1e-12));record['torque_balance']=float(np.linalg.norm(torque.sum(axis=0))/max(np.linalg.norm(torque,axis=1).sum(),1e-12))
        ledger.append(record);write_json(target/'execution_ledger.json',ledger);print(count,record,flush=True)
        if r.returncode!=0:break
    okay=len(ledger)==3 and all(r['returncode']==0 and r['force_balance']<=1e-10 and r['torque_balance']<=1e-10 for r in ledger)
    write_json(target/'verdict.json',{'status':'passed' if okay else 'failed','details':ledger,'scope':'one static force assembly per tissue size, not dynamic tissue validation or statistically precise scaling law; performance optimization not implemented'})

if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser();parser.add_argument('phase',choices=['adaptive','performance']);args=parser.parse_args()
    (adaptive if args.phase=='adaptive' else performance)()
