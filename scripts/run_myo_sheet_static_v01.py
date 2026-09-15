"""Conditional create-only M run, fixed CPU budget, no retries."""
import hashlib
import json
from pathlib import Path
from run_myo_sheet_short_dynamics_v01 import ROOT,OUT,EXE,bounded_run
from run_myo_sheet_2d_m0_v01 import write_json
import numpy as np
def main():
    for stage in ['Q','D']:
        if json.loads((OUT/stage/'verdict.json').read_text())[stage]!='passed':raise SystemExit(stage+' failed')
    if json.loads((OUT/'independent_verification.json').read_text())['status']!='passed':raise SystemExit('independent checks failed')
    out=OUT/'M'
    if out.exists():raise SystemExit('create-only M exists')
    out.mkdir()
    source=ROOT/'results/ventricle_z1/z1_myo_sheet_2d_m0_v01_20260914/inputs/sheet.mesh'
    paths=[Path(__file__),EXE,source,ROOT/'src/ventricle_simucell3d_m0/myo_sheet_relaxation_v01.cpp',ROOT/'scripts/run_myo_sheet_short_dynamics_v01.py',ROOT/'project_control/ventricle_myocardial_sheet_relaxation_contract_v01.md']
    write_json(out/'source_hashes_before.json',{str(p.relative_to(ROOT)).replace('\\','/'):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths})
    command=[str(EXE),str(source),str(out/'sheet'),'.01','4000','clamp','1795']
    write_json(out/'launch.json',{'command':command,'cpu_threads':1,'budget_seconds':1800,'input_sha256':hashlib.sha256(source.read_bytes()).hexdigest()})
    record=bounded_run(command,out/'sheet.log',1800);write_json(out/'execution_ledger.json',[record])
    audits=np.atleast_1d(np.genfromtxt(out/'sheet/step_audits.csv',delimiter=',',names=True))
    summary={'M':'failed' if record['returncode']!=0 else 'unknown','native_returncode':record['returncode'],'resource_stop':record['resource_stop'],'completed_steps':int(audits[-1]['step']) if len(audits) else 0,'last_coordinate':float(audits[-1]['coordinate']) if len(audits) else 0,'equilibrium':'not_adjudicated','contact_geometry':'not_adjudicated'}
    failure=out/'sheet/failure.txt'
    if failure.exists():summary['failure_reason']=failure.read_text().strip()
    write_json(out/'verdict.json',summary);print(json.dumps(summary,indent=2))
if __name__=='__main__':main()
