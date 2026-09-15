"""Q subgate: refine integration only, not cell topology; bounded native CPU calls."""
import hashlib
import json
from pathlib import Path
import subprocess
import time
import numpy as np
from run_myo_sheet_2d_m0_v01 import write_json,read_nodes,geometry,probe_summary
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'results/ventricle_z1/z1_myo_sheet_relaxation_v01_20260914'
PREVIOUS=ROOT/'results/ventricle_z1/z1_myo_sheet_contact_repair_v02_20260914'
EXE=ROOT/'b/z1m0a/Release/prl_myo_sheet_contact_probe_v03.exe'

def main():
    if OUT.exists():raise SystemExit('create-only result exists')
    OUT.mkdir();out=OUT/'Q';out.mkdir()
    write_json(OUT/'ownership.json',{'task':'myocardial sheet Q-D-M relaxation','purpose':'retained formal scientific evidence','gpu':0})
    paths=[Path(__file__),EXE,ROOT/'src/ventricle_simucell3d_m0/myo_sheet_contact_probe_v03.cpp',ROOT/'project_control/ventricle_myocardial_sheet_relaxation_contract_v01.md',ROOT/'external/simucell3d/src/contact_models/contact_node_face_via_spring.cpp']
    write_json(out/'source_hashes_before.json',{str(p.relative_to(ROOT)).replace('\\','/'):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths})
    metrics=[];ledger=[];start=time.monotonic();_,faces=geometry(2)
    for direction in ['END','SIDE']:
        normal=np.array([1.,0,0]) if direction=='END' else np.array([1.665,4.6,0]);normal/=np.linalg.norm(normal)
        for gap in [-.035,.07]:
            source=PREVIOUS/'inputs'/f'{direction}_L2_G{gap:+.3f}.mesh'
            for edge in [.20,.10,.05]:
                tag=f'{direction}_G{gap:+.3f}_Q{edge:.2f}';command=[str(EXE),str(source),str(out/tag),'4','quadrature','1',str(edge)]
                remaining=120-(time.monotonic()-start)
                if remaining<=0:raise RuntimeError('Q budget exhausted')
                result=subprocess.run(command,capture_output=True,text=True,timeout=min(30,remaining))
                ledger.append({'case':tag,'command':command,'returncode':result.returncode,'stdout':result.stdout,'stderr':result.stderr,'input_hash':hashlib.sha256(source.read_bytes()).hexdigest()});write_json(out/'execution_ledger.json',ledger)
                if result.returncode:raise RuntimeError(result.stderr)
                data=read_nodes(out/tag/'nodes.csv');record=probe_summary(data,faces,normal);record.update(json.loads((out/tag/'contact.json').read_text()))
                record.update(direction=direction,gap=gap,quadrature_edge=edge,level=2,nodes=f'{tag}/nodes.csv');metrics.append(record)
                print(direction,gap,edge,record['normal_force_on_first'],flush=True)
    write_json(out/'metrics.json',metrics);comparisons=[]
    for direction in ['END','SIDE']:
        for gap in [-.035,.07]:
            a,b=[next(r for r in metrics if r['direction']==direction and r['gap']==gap and r['quadrature_edge']==edge) for edge in [.10,.05]]
            da,db=read_nodes(out/a['nodes']),read_nodes(out/b['nodes']);fa=np.column_stack([da[k] for k in ['fx','fy','fz']]);fb=np.column_stack([db[k] for k in ['fx','fy','fz']])
            field=float(np.sqrt(np.sum((fa-fb)**2/db['area'][:,None])/np.sum(fb**2/db['area'][:,None])))
            force=abs(a['normal_force_on_first']-b['normal_force_on_first'])/abs(b['normal_force_on_first']);energy=abs(a['contact_energy']-b['contact_energy'])/abs(b['contact_energy'])
            comparisons.append({'direction':direction,'gap':gap,'force_relative':force,'energy_relative':energy,'traction_L2_relative':field,'passed':bool(force<=.02 and energy<=.02 and field<=.05)})
    gates={'finite':all(r['finite'] and np.isfinite(r['contact_energy']) for r in metrics),'directions':all(r['normal_force_on_first']*r['gap']>0 for r in metrics),'balance':all(r['force_balance_relative']<=1e-10 and r['torque_balance_relative']<=1e-10 for r in metrics),'quadrature':all(r['passed'] for r in comparisons)}
    verdict={'Q':'passed' if all(gates.values()) else 'failed','D':'not_run','M':'not_run','gates':gates,'comparisons':comparisons,'calls':len(ledger),'elapsed_seconds':time.monotonic()-start}
    write_json(out/'verdict.json',verdict);print(json.dumps(verdict,indent=2))

if __name__=='__main__':main()
