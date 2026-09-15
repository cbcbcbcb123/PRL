"""Authorized long doublet qualification with cooperative per-state geometry gates."""
import hashlib
import json
from pathlib import Path
import subprocess
import time
import numpy as np
import psutil
from run_myo_contact_barrier_v01 import ENGINE,OUT as PREVIOUS,ROOT,hashes,read
from run_myo_sheet_2d_m0_v01 import write_json
from myo_fold_monitor_v01 import CompleteNodeStream,mesh_metrics

OUT=ROOT/'results/ventricle_z1/z1_myo_long_doublet_v01_20260914'
def main():
    assert json.loads((PREVIOUS/'verdict.json').read_text())['status']=='passed'
    assert hashes()==json.loads((PREVIOUS/'source_hashes_before.json').read_text()),'frozen core drift'
    OUT.mkdir(exist_ok=False)
    write_json(OUT/'ownership.json',{'owner':'Codex','purpose':'retained authorized long-doublet qualification','temporary_directories_created':[],'gpu':False})
    source=hashes()
    for p in [Path(__file__),ROOT/'scripts/myo_fold_monitor_v01.py',ROOT/'project_control/ventricle_myocardial_long_doublet_contract_v01.md']:
        source[str(p.relative_to(ROOT))]=hashlib.sha256(p.read_bytes()).hexdigest()
    write_json(OUT/'source_hashes_before.json',source)
    ledger=[];started=time.monotonic();case_matrix=[(direction,dt) for direction in ['END','SIDE'] for dt in [.02,.01]]
    for direction,dt in case_matrix:
        tag=f'{direction}_DT{dt:.2f}';case=OUT/tag;mesh=PREVIOUS/f'S/inputs/{direction}_G0.07.mesh'
        command=[str(ENGINE),str(mesh),str(case),str(dt),str(round(5/dt)),'free','350']
        began=time.monotonic();stream=CompleteNodeStream(case/'nodes.csv');triangles=None;initial=[];observations=[];first_failure=None;peak=0;stop_at=None
        with (OUT/f'{tag}.log').open('w',encoding='utf-8') as logfile:
            process=subprocess.Popen(command,cwd=ROOT,stdout=logfile,stderr=subprocess.STDOUT)
            try:
                while True:
                    if triangles is None and (case/'faces.csv').exists() and (case/'faces.csv').stat().st_size>100:
                        faces=read(case/'faces.csv')
                        if len(faces)==768:triangles=[np.column_stack([faces[faces['cell']==cid][k] for k in ['a','b','c']]).astype(int) for cid in [0,1]]
                    if triangles is not None:
                        for a in stream.poll():
                            record={'snapshot':int(a['snapshot'][0]),'step':int(a['step'][0]),'coordinate':float(a['coordinate'][0]),'cells':[]}
                            for cid in [0,1]:
                                b=a[a['cell']==cid];p=np.column_stack([b[k] for k in ['x','y','z']]);metrics=mesh_metrics(p,triangles[cid])
                                if record['snapshot']==0:initial.append(metrics['volume'])
                                metrics['volume_error']=abs(metrics['volume']/initial[cid]-1);metrics['cell']=cid;record['cells'].append(metrics)
                            observations.append(record)
                            for m in record['cells']:
                                reasons=[name for name,bad in [('volume_error',m['volume_error']>.02),('minimum_angle',m['min_angle']<15),('adjacent_fold',m['adjacent_cosine']<=-.95),('nonpositive_volume',m['volume']<=0)] if bad]
                                if reasons and first_failure is None:first_failure={**record,'reasons':reasons,'cell':m['cell']}
                            if first_failure and stop_at is None:
                                write_json(case/'STOP',{'reason':'frozen_geometry_gate','first_failure':first_failure});stop_at=time.monotonic()
                    done=process.poll() is not None
                    if done:break
                    try:peak=max(peak,psutil.Process(process.pid).memory_info().rss)
                    except psutil.NoSuchProcess:pass
                    budget_failure=None
                    if peak>2*1024**3:budget_failure='memory_2GiB'
                    if time.monotonic()-began>355 or time.monotonic()-started>1435:budget_failure='wall_budget'
                    if (case/'step_audits.csv').exists() and time.time()-(case/'step_audits.csv').stat().st_mtime>30:budget_failure='single_step_30s'
                    if (case/'nodes.csv').exists() and (case/'nodes.csv').stat().st_size>2*1024**3:budget_failure='output_budget'
                    if budget_failure and stop_at is None:
                        first_failure={'reasons':[budget_failure]};write_json(case/'STOP',first_failure);stop_at=time.monotonic()
                    if stop_at is not None and time.monotonic()-stop_at>5:
                        process.terminate();process.wait(timeout=5);break
                    time.sleep(.3)
            finally:
                if process.poll() is None:process.terminate();process.wait(timeout=5)
        write_json(case/'geometry_monitor.json',{'first_failure':first_failure,'states':observations,'scope':'complete flushed states only; shared-edge dihedral gate is not complete vertex-fan topology proof'})
        item={'case':tag,'command':command,'returncode':process.returncode,'elapsed_seconds':time.monotonic()-began,'peak_working_set_bytes':peak,'input_sha256':hashlib.sha256(mesh.read_bytes()).hexdigest(),'first_failure':first_failure,'completed_monitor_states':len(observations)}
        ledger.append(item);write_json(OUT/'execution_ledger.json',ledger);print(tag,item['returncode'],item['elapsed_seconds'],first_failure,flush=True)
        if process.returncode!=0 or first_failure is not None:break
    complete=len(ledger)==4 and all(r['returncode']==0 and r['first_failure'] is None for r in ledger)
    write_json(OUT/'execution_status.json',{'status':'passed' if complete else 'failed','cases_run':len(ledger),'cases_not_run':[f'{direction}_DT{dt:.2f}' for direction,dt in case_matrix[len(ledger):]],'elapsed_seconds':time.monotonic()-started,'next_branch':'eligible_for_independent_verification' if complete else 'not_run_due_to_long_doublet_failure'})

if __name__=='__main__':main()
