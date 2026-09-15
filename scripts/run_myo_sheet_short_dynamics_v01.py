"""Frozen D subgate; actual deformable cells, CPU resource guard, no tissue run."""
import hashlib
import json
from pathlib import Path
import subprocess
import time
import numpy as np
import psutil
from run_myo_sheet_2d_m0_v01 import write_json
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'results/ventricle_z1/z1_myo_sheet_relaxation_v01_20260914'
EXE=ROOT/'b/z1m0a/Release/prl_myo_sheet_relaxation_v01.exe'

def bounded_run(command,log_path,budget):
    started=time.monotonic();peak=0;reason=None
    with log_path.open('w',encoding='utf-8') as stream:
        process=subprocess.Popen(command,stdout=stream,stderr=subprocess.STDOUT,cwd=ROOT)
        try:
            while process.poll() is None:
                try:peak=max(peak,psutil.Process(process.pid).memory_info().rss)
                except psutil.NoSuchProcess:pass
                if peak>2*1024**3:reason='memory_budget_2GiB'
                if time.monotonic()-started>budget:reason='wall_budget'
                audit=Path(command[2])/'step_audits.csv'
                if audit.exists() and time.time()-audit.stat().st_mtime>30:reason='single_step_wall_budget'
                if reason:process.terminate();process.wait(timeout=10);break
                time.sleep(.5)
        finally:
            if process.poll() is None:process.terminate();process.wait(timeout=10)
    return {'command':command,'returncode':process.returncode,'elapsed_seconds':time.monotonic()-started,'peak_working_set_bytes':peak,'resource_stop':reason}

def main():
    if json.loads((OUT/'Q/verdict.json').read_text())['Q']!='passed':raise SystemExit('Q prerequisite failed')
    out=OUT/'D'
    if out.exists():raise SystemExit('create-only D exists')
    out.mkdir();paths=[Path(__file__),EXE,ROOT/'src/ventricle_simucell3d_m0/myo_sheet_relaxation_v01.cpp',ROOT/'src/ventricle_bioform_myo/ventricle_bioform_myo_v03.cpp',ROOT/'external/simucell3d/src/contact_models/contact_node_face_via_spring.cpp',ROOT/'project_control/ventricle_myocardial_sheet_relaxation_contract_v01.md']
    write_json(out/'source_hashes_before.json',{str(p.relative_to(ROOT)).replace('\\','/'):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths})
    ledger=[];start=time.monotonic()
    for direction in ['END','SIDE']:
        for dt in [.02,.01]:
            source=ROOT/f'results/ventricle_z1/z1_myo_sheet_contact_repair_v02_20260914/inputs/{direction}_L2_G+0.070.mesh'
            tag=f'{direction}_DT{dt:.2f}';command=[str(EXE),str(source),str(out/tag),str(dt),str(round(1/dt)),'free','145']
            record=bounded_run(command,out/f'{tag}.log',min(150,600-(time.monotonic()-start)));record.update(case=tag,input_sha256=hashlib.sha256(source.read_bytes()).hexdigest());ledger.append(record);write_json(out/'execution_ledger.json',ledger)
            print(tag,record['returncode'],record['elapsed_seconds'],flush=True)
            if record['returncode']!=0:
                write_json(out/'verdict.json',{'D':'failed','M':'not_run','reason':'native_or_resource_stop','failed_case':tag,'calls':len(ledger)});return
    gates={};comparisons=[]
    for direction in ['END','SIDE']:
        arrays=[np.genfromtxt(out/f'{direction}_DT{dt:.2f}/nodes.csv',delimiter=',',names=True) for dt in [.02,.01]]
        endpoints=[a[a['snapshot']==a['snapshot'].max()] for a in arrays]
        displacements=[np.column_stack([a[k]-a[k+'0'] for k in ['x','y','z']]) for a in endpoints]
        change=float(np.linalg.norm(displacements[0]-displacements[1])/max(np.linalg.norm(displacements[1]),1e-12))
        comparisons.append({'direction':direction,'displacement_dt_change':change,'passed':change<=.02})
    for item in ledger:
        states=np.genfromtxt(out/item['case']/'states.csv',delimiter=',',names=True);audits=np.genfromtxt(out/item['case']/'step_audits.csv',delimiter=',',names=True);nodes=np.genfromtxt(out/item['case']/'nodes.csv',delimiter=',',names=True)
        gates[item['case']]=bool(all(np.isfinite(nodes[k]).all() for k in nodes.dtype.names) and len(states)==5 and np.allclose(states['coordinate'],[0,.25,.5,.75,1],atol=1e-12,rtol=0) and max(audits['max_volume_error'])<=.02 and min(audits['min_angle'])>=15 and min(states['contact_support_area'])>0 and max(audits['work_residual'])<=1e-10)
    gates['dt_convergence']=all(r['passed'] for r in comparisons)
    verdict={'D':'passed' if all(gates.values()) else 'failed','M':'not_run','gates':gates,'comparisons':comparisons,'calls':len(ledger),'elapsed_seconds':time.monotonic()-start,'coordinate':'algorithmic_relaxation_not_physiological_time'}
    write_json(out/'verdict.json',verdict);print(json.dumps(verdict,indent=2))

if __name__=='__main__':main()
