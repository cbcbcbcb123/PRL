"""Frozen CPU-only barrier qualification; each formal substage is create-only."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import time
import numpy as np
from run_myo_sheet_2d_m0_v01 import write_mesh,write_json,geometry,probe_summary,read_nodes
from run_myo_sheet_short_dynamics_v01 import bounded_run
from diagnose_myo_sheet_saved_geometry_v01 import contained_witnesses,points,inspect_case

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'results/ventricle_z1/z1_myo_contact_barrier_v01_20260914'
PROBE=ROOT/'b/z1m0a/Release/prl_myo_contact_barrier_probe_v01.exe'
ENGINE=ROOT/'b/z1m0a/Release/prl_myo_contact_barrier_relaxation_v01.exe'
OLD=ROOT/'results/ventricle_z1/z1_myo_sheet_relaxation_v01_20260914'
SOURCES=[Path(__file__),PROBE,ENGINE,ROOT/'project_control/ventricle_myocardial_contact_barrier_contract_v01.md',ROOT/'src/ventricle_simucell3d_m0/myo_contact_barrier_probe_v01.cpp',ROOT/'src/ventricle_simucell3d_m0/myo_contact_barrier_relaxation_v01.cpp',ROOT/'external/simucell3d/src/contact_models/contact_node_face_via_spring.cpp',ROOT/'external/simucell3d/include/contact_models/contact_node_face_via_spring.hpp',ROOT/'external/simucell3d/include/contact_models/surface_separation_guard.hpp',ROOT/'src/ventricle_bioform_myo/ventricle_bioform_myo_v03.cpp']
def hashes():return {str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in SOURCES}
def read(path):return np.atleast_1d(np.genfromtxt(path,delimiter=',',names=True))
def static():
    OUT.mkdir(exist_ok=False);out=OUT/'S';out.mkdir();(out/'inputs').mkdir()
    write_json(OUT/'ownership.json',{'owner':'Codex','purpose':'retained approved contact-barrier qualification','temporary_directory':'tmp/contact_barrier_v01_build','gpu':False})
    write_json(OUT/'source_hashes_before.json',hashes())
    ledger=[];metrics=[];gates={};started=time.monotonic()
    def call(command,tag,expected=0):
        budget=min(40.,300-(time.monotonic()-started))
        if budget<=0:raise RuntimeError('static wall budget')
        began=time.monotonic();r=subprocess.run(list(map(str,command)),cwd=ROOT,capture_output=True,text=True,timeout=budget)
        ledger.append({'case':tag,'command':list(map(str,command)),'returncode':r.returncode,'stdout':r.stdout,'stderr':r.stderr,'elapsed_seconds':time.monotonic()-began})
        write_json(out/'execution_ledger.json',ledger)
        if r.returncode!=expected:raise RuntimeError(f'{tag}: {r.stderr}')
        return r
    try:
        call([PROBE,'--geometry-self-test'],'geometry_self_test');gates['geometry_primitives']=True
        p,tri=geometry(2)
        for direction in ['END','SIDE']:
            old=read(OLD/f'D/{direction}_DT0.01/nodes.csv');last=old[old['snapshot']==old['snapshot'].max()]
            bodies=np.stack([points(last[last['cell']==cid]) for cid in [0,1]])
            path=out/'inputs'/f'old_failed_{direction}.mesh';write_mesh(path,bodies,tri)
            call([PROBE,path,out/'unused','4','geometry'],f'old_failed_{direction}',3)
        gates['old_crossing_rejected']=True
        for direction in ['END','SIDE']:
            normal=np.array([1.,0,0]) if direction=='END' else np.array([1.665,4.6,0]);normal/=np.linalg.norm(normal)
            center=np.array([9.2,0,0]) if direction=='END' else np.array([4.6,4.995,0]);initial=float(center@normal-2*np.max(p@normal))
            def invoke(tag,bodies,q=.1,adhesion=1.):
                path=out/'inputs'/f'{tag}.mesh';write_mesh(path,bodies,tri)
                call([PROBE,path,out/tag,'4','quadrature',adhesion,q],tag)
                a=read_nodes(out/tag/'nodes.csv');record=probe_summary(a,tri,normal);record.update(json.loads((out/tag/'contact.json').read_text()))
                record.update(case=tag,direction=direction,input_sha256=hashlib.sha256(path.read_bytes()).hexdigest());metrics.append(record);write_json(out/'metrics.json',metrics)
                return a,record
            for gap in [.07,.20,.70]:
                bodies=np.stack([p,p+center+normal*(gap-initial)])
                if gap==.07:
                    assert not contained_witnesses(bodies[0],bodies[1][tri]) and not contained_witnesses(bodies[1],bodies[0][tri])
                a,record=invoke(f'{direction}_G{gap:.2f}',bodies)
                force=record['normal_force_on_first'];gates[f'{direction}_gap{gap}_direction']=bool(force<0 if gap==.07 else force>0 if gap==.20 else record['force_absolute_sum']==0)
                if gap!=.07:continue
                _,fine=invoke(f'{direction}_Q005',bodies,.05)
                gates[f'{direction}_quadrature']=abs(force-fine['normal_force_on_first'])/abs(fine['normal_force_on_first'])<=.02
                forces=np.stack([np.column_stack([a[a['cell']==cid][k] for k in ['fx','fy','fz']]) for cid in [0,1]])
                for mode in ['translation','area_deformation']:
                    displacement=np.zeros_like(bodies)
                    if mode=='translation':displacement[0]=normal
                    else:displacement[:,:,2]=bodies[:,:,2]/max(abs(bodies[:,:,2]).max(),1.)
                    energy=[];epsilon=1e-6
                    for sign in [1,-1]:
                        _,perturbed=invoke(f'{direction}_FD_{mode}_{sign:+d}',bodies+sign*epsilon*displacement)
                        energy.append(perturbed['contact_energy'])
                    numerical=(energy[0]-energy[1])/(2*epsilon);analytical=-float(np.sum(forces*displacement));error=abs(numerical-analytical)/max(abs(analytical),1e-12)
                    record[f'{mode}_gradient_error']=error;gates[f'{direction}_{mode}_gradient']=error<=1e-4
                _,off=invoke(f'{direction}_adhesion_off',bodies,adhesion=0.)
                gates[f'{direction}_separate_repulsion']=off['normal_force_on_first']<force
        gates['force_torque_balance']=all(r['force_balance_relative']<=1e-10 and r['torque_balance_relative']<=1e-10 for r in metrics)
        gates['finite']=all(r['finite'] for r in metrics)
        write_json(out/'metrics.json',metrics)
    except Exception as error:
        gates['execution']=False;write_json(out/'exception.json',{'error':str(error)})
    verdict={'status':'passed' if all(gates.values()) else 'failed','gates':gates,'calls':len(ledger),'elapsed_seconds':time.monotonic()-started}
    write_json(out/'verdict.json',verdict);print(json.dumps(verdict,indent=2))

def dynamics():
    if json.loads((OUT/'S/verdict.json').read_text())['status']!='passed':raise SystemExit('static prerequisite failed')
    assert hashes()==json.loads((OUT/'source_hashes_before.json').read_text()),'source drift after freeze'
    out=OUT/'D';out.mkdir(exist_ok=False);ledger=[];start=time.monotonic()
    for direction in ['END','SIDE']:
        for dt in [.02,.01]:
            source=OUT/'S/inputs'/f'{direction}_G0.07.mesh';tag=f'{direction}_DT{dt:.2f}'
            command=[str(ENGINE),str(source),str(out/tag),str(dt),str(round(1/dt)),'free','175']
            record=bounded_run(command,out/f'{tag}.log',min(180,720-(time.monotonic()-start)));record['case']=tag;ledger.append(record);write_json(out/'execution_ledger.json',ledger)
            print(tag,record['returncode'],record['elapsed_seconds'],flush=True)
            if record['returncode']!=0:break
        if ledger[-1]['returncode']!=0:break
    write_json(out/'execution_status.json',{'status':'passed' if len(ledger)==4 and all(r['returncode']==0 for r in ledger) else 'failed','elapsed_seconds':time.monotonic()-start})

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('phase',choices=['static','dynamics']);args=parser.parse_args()
    (static if args.phase=='static' else dynamics)()
