"""One four-state DG2-pressure diagnostic in the already-pinned local image."""
import json
from pathlib import Path
import shutil
import time
import traceback

import numpy as np

from prl.fem.fenicsx_ring import Ring,write_json
from prl.verification.fenicsx_contour import geometry_audit
from prl.verification.fenicsx_ring import load_arrays,state_audit,pressure_basis
from prl.verification.fenicsx_pressure import diagnostic_state,verify_pressure,same_displacement_mesh


def main():
    root=Path('/out'); config=json.loads((root/'configuration.json').read_text())
    started=time.monotonic(); attempted=0; accepted=0; current=None
    try:
        resumed=config.get('resume_first_ring',False)
        for kind in config['objects']:
            case={'name':'M0','segments':64,'radial':[1,1,5]}
            cfg={**config,'geometry_kind':'ring' if kind=='ring' else 'image_polygon'}
            child=root/kind; (child/'raw').mkdir(parents=True,exist_ok=False)
            geometry=None
            if kind=='contour':
                geometry=load_arrays(root/'retained_mesh.npz')
                geometry['metrics']=geometry_audit(geometry,load_arrays(root/'geometry_source.npz'))
                write_json(child/'geometry_preflight.json',geometry['metrics'])
                if geometry['metrics']['status']!='passed':
                    raise ValueError('Unchanged contour geometry gate failed')
            current=Ring(case,cfg,child,geometry_input=geometry)
            pressure_basis(current.mesh_data)
            old_root=root/'comparison'/kind
            old_mesh=load_arrays(old_root/'mesh.npz')
            if not same_displacement_mesh(current.mesh_data,old_mesh):
                raise ValueError('The displacement mesh changed; not an isolated pressure-space comparison')
            old=state_audit(old_mesh,load_arrays(old_root/'state.npz'),
                            json.loads((old_root/'state.json').read_text()),
                            json.loads((old_root/'configuration.json').read_text()))
            current.tangent_checks()
            initial=np.zeros_like(current.w.x.array)
            states=list(enumerate(config['passive_loads']))
            if resumed:
                retained=root/'retained_zero'
                original_mesh=load_arrays(retained/'mesh.npz')
                if set(original_mesh)!=set(current.mesh_data) or not all(np.array_equal(original_mesh[k],current.mesh_data[k]) for k in original_mesh):
                    raise ValueError('Retained DG2 mesh or mixed-state map changed')
                zero=load_arrays(retained/'state.npz')
                zero_report=diagnostic_state(original_mesh,zero,json.loads((retained/'state.json').read_text()),cfg)
                write_json(root/'retained_zero_audit.json',zero_report)
                if zero_report['status']!='passed' or float(zero['load'])!=0. or float(zero['activation'])!=0.:
                    raise ValueError('Retained zero state failed its independent gate')
                initial=zero['mixed_state'].copy()
                states=[(1,.02)]
            for i,load in states:
                if time.monotonic()-started>1140 or shutil.disk_usage(root).free<10*1024**3+64*1024**2:
                    raise RuntimeError('Time or disk headroom reached before next state')
                attempted+=1
                initial=current.solve(f'passive_{i}',load,0.,initial)
                path=child/'raw'/f'M0_state_passive_{i}.npz'
                report=diagnostic_state(current.mesh_data,load_arrays(path),json.loads(path.with_suffix('.json').read_text()),cfg,old)
                write_json(path.with_name(path.stem+'_audit.json'),report)
                if report['status']!='passed':
                    raise ValueError('Independent gate failed: '+str([k for k,v in report['checks'].items() if not v]))
                accepted+=1
                write_json(root/'last_valid.json',{'object':kind,'label':f'passive_{i}','accepted_states':accepted})
        report=verify_pressure(root)
        write_json(root/'verification.json',report)
        write_json(root/'progress.json',{'status':report['status'],'attempted_states':attempted,'accepted_states':accepted})
        return 0 if report['status']=='passed' else 2
    except Exception as error:
        write_json(root/'failure.json',{'status':'failed','error':str(error),'traceback':traceback.format_exc(),
                                      'attempted_states':attempted,'accepted_states':accepted})
        if current is not None:
            np.savez_compressed(root/'last_attempt.npz',mixed_state=current.w.x.array)
        traceback.print_exc()
        return 2


if __name__=='__main__':
    raise SystemExit(main())
