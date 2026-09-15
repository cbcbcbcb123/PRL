"""CPU-bounded native-contact regression and repair qualification, create-only evidence."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import time
import numpy as np
from run_myo_sheet_2d_m0_v01 import geometry, write_mesh, write_json, probe_summary, read_nodes

ROOT=Path(__file__).resolve().parents[1]
EXE=ROOT/'b/z1m0a/Release/prl_myo_sheet_contact_probe_v02.exe'
SOURCES=['scripts/run_myo_sheet_contact_repair_v02.py','src/ventricle_simucell3d_m0/myo_sheet_contact_probe_v02.cpp','external/simucell3d/include/contact_models/contact_node_face_via_spring.hpp','external/simucell3d/src/contact_models/contact_node_face_via_spring.cpp','external/simucell3d/include/global_configuration.hpp','project_control/ventricle_myocardial_sheet_contact_repair_contract_v02.md','b/z1m0a/Release/prl_myo_sheet_contact_probe_v02.exe']

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--phase',choices=['dev01','dev02','dev03','formal'],required=True);args=parser.parse_args()
    suffix='' if args.phase=='formal' else '_'+args.phase
    out=ROOT/f'results/ventricle_z1/z1_myo_sheet_contact_repair_v02{suffix}_20260914'
    if out.exists():raise SystemExit('create-only output exists')
    out.mkdir();(out/'inputs').mkdir()
    write_json(out/'ownership.json',{'purpose':'retained contact regression evidence','phase':args.phase,'gpu':0})
    write_json(out/'source_hashes_before.json',{p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in SOURCES})
    start=time.monotonic();ledger=[];metrics=[]
    def invoke(tag,cells,faces,normal,adhesion_scale=1.0):
        path=out/'inputs'/f'{tag}.mesh';write_mesh(path,cells,faces)
        cmd=[str(EXE),str(path),str(out/'raw'/tag),'4']
        if args.phase!='dev01':cmd.extend(['quadrature',str(adhesion_scale)])
        elapsed=time.monotonic()-start;budget=900 if args.phase=='formal' else 300
        if elapsed>=budget:raise RuntimeError('frozen CPU wall budget exhausted')
        result=subprocess.run(cmd,capture_output=True,text=True,timeout=min(60,budget-elapsed))
        ledger.append({'case':tag,'command':cmd,'returncode':result.returncode,'stdout':result.stdout,'stderr':result.stderr,'input_sha256':hashlib.sha256(path.read_bytes()).hexdigest()});write_json(out/'execution_ledger.json',ledger)
        if result.returncode:raise RuntimeError(result.stderr)
        record=probe_summary(read_nodes(out/'raw'/tag/'nodes.csv'),faces,normal)
        extra=out/'raw'/tag/'contact.json'
        if extra.exists():record.update(json.loads(extra.read_text()))
        record['nodes']=f'raw/{tag}/nodes.csv';record['input']=f'inputs/{tag}.mesh'
        return record
    try:
        for level in [2,3]:
            points,faces=geometry(level)
            for direction in ['END','SIDE']:
                normal=np.array([1.,0,0]) if direction=='END' else np.array([1.665,4.6,0]);normal/=np.linalg.norm(normal)
                center=np.array([9.2,0,0]) if direction=='END' else np.array([4.6,4.995,0]);original=float(center@normal-2*np.max(points@normal))
                for gap in [-.035,.07,.70]:
                    cells=[points,points+center+normal*(gap-original)]
                    record=invoke(f'{direction}_L{level}_G{gap:+.3f}',cells,faces,normal)
                    record.update(direction=direction,level=level,gap=gap,type_id=4);metrics.append(record)
                    write_json(out/'contact_metrics.json',metrics)
                    print(direction,level,gap,record['normal_force_on_first'],flush=True)
        refinement=[]
        for direction in ['END','SIDE']:
            for gap in [-.035,.07]:
                a,b=[next(r['normal_force_on_first'] for r in metrics if r['direction']==direction and r['level']==level and r['gap']==gap) for level in [2,3]]
                difference=abs(a-b)/max(abs(b),1e-30)
                refinement.append({'direction':direction,'gap':gap,'relative_difference':difference,'threshold':.05,'passed':bool(difference<=.05 and abs(b)>1e-12)})
        gates={'finite':all(r['finite'] for r in metrics),'adhesion':all(r['normal_force_on_first']>1e-12 for r in metrics if r['gap']==.07),'repulsion':all(r['normal_force_on_first']<0 for r in metrics if r['gap']<0),'far_zero':all(r['force_absolute_sum']==0 and r['maximum_geometry_projection']==0 for r in metrics if r['gap']==.7),'balance':all(r['force_balance_relative']<=1e-10 and r['torque_balance_relative']<=1e-10 for r in metrics),'refinement':all(r['passed'] for r in refinement),'no_projection':all(r['maximum_geometry_projection']==0 and r['coupled_nodes']==0 for r in metrics)}
        extra_metrics=[];derivatives=[];invariances=[];negative_controls=[]
        if args.phase=='formal':
            points,faces=geometry(2)
            for direction in ['END','SIDE']:
                normal=np.array([1.,0,0]) if direction=='END' else np.array([1.665,4.6,0]);normal/=np.linalg.norm(normal)
                for gap in [-.035,.07]:
                    base=next(r for r in metrics if r['level']==2 and r['direction']==direction and r['gap']==gap)
                    data=read_nodes(out/base['nodes'])
                    cells=np.stack([np.column_stack([data[data['cell']==cid][k] for k in ['x','y','z']]) for cid in [0,1]])
                    force=np.stack([np.column_stack([data[data['cell']==cid][k] for k in ['fx','fy','fz']]) for cid in [0,1]])
                    modes=['normal_translation']+(['transverse_deformation'] if direction=='END' else [])
                    for mode in modes:
                        displacement=np.zeros_like(cells)
                        if mode=='normal_translation':displacement[0]=normal
                        else:displacement[:,:,1]=cells[:,:,1]/np.max(np.abs(cells[:,:,1]))
                        analytical=-float(np.sum(force*displacement));series=[]
                        for epsilon in [1e-2,1e-3,1e-4,1e-5,1e-6,1e-7]:
                            pair=[]
                            for sign in [1,-1]:
                                tag=f'FD_{direction}_{gap:+.3f}_{mode}_{epsilon:g}_{sign:+d}'
                                item=invoke(tag,cells+sign*epsilon*displacement,faces,normal)
                                item.update(kind='derivative',direction=direction,gap=gap,mode=mode,epsilon=epsilon,sign=sign);extra_metrics.append(item);pair.append(item)
                            numerical=(pair[0]['contact_energy']-pair[1]['contact_energy'])/(2*epsilon)
                            series.append({'epsilon':epsilon,'analytical':analytical,'numerical':numerical,'relative_error':abs(numerical-analytical)/max(abs(analytical),1e-12),'plus':pair[0]['nodes'],'minus':pair[1]['nodes']})
                        derivatives.append({'direction':direction,'gap':gap,'mode':mode,'base_nodes':base['nodes'],'series':series,'passed':bool(min(r['relative_error'] for r in series)<=1e-6)})
                    if gap==.07:
                        off=invoke(f'NO_ADHESION_{direction}',cells,faces,normal,adhesion_scale=0.0);extra_metrics.append(off)
                        negative_controls.append({'direction':direction,'nodes':off['nodes'],'passed':off['force_absolute_sum']==0 and off['contact_energy']==0})
                        axis=np.array([1.,2.,3.]);axis/=np.linalg.norm(axis);angle=.37
                        cross=np.array([[0.,-axis[2],axis[1]],[axis[2],0.,-axis[0]],[-axis[1],axis[0],0.]])
                        rotation=np.eye(3)*np.cos(angle)+(1-np.cos(angle))*np.outer(axis,axis)+np.sin(angle)*cross
                        transformed=cells@rotation.T+np.array([2.3,-1.7,.8])
                        rotated=invoke(f'RIGID_{direction}',transformed,faces,normal@rotation.T);extra_metrics.append(rotated)
                        transformed_data=read_nodes(out/rotated['nodes'])
                        transformed_force=np.stack([np.column_stack([transformed_data[transformed_data['cell']==cid][k] for k in ['fx','fy','fz']]) for cid in [0,1]])
                        force_error=float(np.linalg.norm(transformed_force-force@rotation.T)/max(np.linalg.norm(force),1e-12))
                        energy_error=abs(rotated['contact_energy']-base['contact_energy'])/max(abs(base['contact_energy']),1e-12)
                        invariances.append({'kind':'rigid','direction':direction,'nodes':rotated['nodes'],'base_nodes':base['nodes'],'force_relative_error':force_error,'energy_relative_error':energy_error,'passed':force_error<=1e-10 and energy_error<=1e-10})
                        if direction=='END':
                            swapped=invoke('SWAPPED_END',cells[::-1],faces,normal);extra_metrics.append(swapped)
                            swapped_data=read_nodes(out/swapped['nodes'])
                            swapped_force=np.stack([np.column_stack([swapped_data[swapped_data['cell']==cid][k] for k in ['fx','fy','fz']]) for cid in [0,1]])
                            error=float(np.linalg.norm(swapped_force-force[::-1])/max(np.linalg.norm(force),1e-12))
                            invariances.append({'kind':'swap','nodes':swapped['nodes'],'base_nodes':base['nodes'],'force_relative_error':error,'passed':error<=1e-10})
                    write_json(out/'extra_metrics.json',extra_metrics)
                    write_json(out/'mechanical_checks.json',{'derivatives':derivatives,'invariances':invariances,'negative_controls':negative_controls})
            gates.update(energy_gradient=all(x['passed'] for x in derivatives),objectivity=all(x['passed'] for x in invariances),adhesion_off=all(x['passed'] for x in negative_controls),extra_finite=all(x['finite'] and np.isfinite(x['contact_energy']) for x in extra_metrics))
        verdict={'phase':args.phase,'matrix_status':'passed' if all(gates.values()) else 'failed','C0':'unknown' if all(gates.values()) else 'failed','gates':gates,'refinement':refinement,'calls':len(ledger),'elapsed_seconds':time.monotonic()-start,'static_relaxation':'not_run','energy_gradient':'not_run','biological_validation':'blocked'}
        if args.phase=='formal':
            verdict['C0']='passed' if all(gates.values()) else 'failed'
            verdict['energy_gradient']='passed' if gates['energy_gradient'] else 'failed'
            verdict['qualification_scope']='synthetic_static_double_cell_contact_only'
        write_json(out/'verdict.json',verdict);print(json.dumps(verdict,indent=2))
    except Exception as error:
        write_json(out/'failure.json',{'status':'failed','error':str(error),'calls':len(ledger),'elapsed_seconds':time.monotonic()-start});raise

if __name__=='__main__':main()
