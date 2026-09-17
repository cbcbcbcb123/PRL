"""Preserve the formal invocation then independently audit saved states; no solve."""
from pathlib import Path
import json
import shutil
import numpy as np
from prl.result_store import result_path
from prl.runs.fenicsx_contour import FINE_RESULT
from prl.runs.fenicsx_ring import digest
from prl.runs.fenicsx_runtime import save_json
from prl.verification.fenicsx_fine import verify_fine
from prl.verification.fenicsx_ring import load_arrays

workspace=Path.cwd().resolve()
root=result_path(workspace,FINE_RESULT)
formal=root/'formal_invocation_manifest.json'
if formal.exists(): raise FileExistsError('Preparation is create-only; inspect existing audit instead')
shutil.copyfile(root/'manifest.json',formal)
original=json.loads(formal.read_text())
assert all(digest(root/item['path'])==item['sha256'] for item in original['files'])
report=verify_fine(root,save=True)
geometry=load_arrays(root/'raw/M1_input_mesh.npz')
locations={}
for name,values in report['volume'].items():
    point=np.asarray(values['worst_reference_xy']); boundaries=[]
    for label,key in [('cavity','inner_nodes'),('endo_ECM','interface1_nodes'),('ECM_myo','interface2_nodes'),('outer','outer_nodes')]:
        loop=geometry['xy'][geometry[key]]
        a=loop; direction=np.roll(loop,-1,axis=0)-loop
        t=np.clip(np.sum((point-a)*direction,axis=1)/np.sum(direction*direction,axis=1),0,1)
        distances=np.linalg.norm(point-a-t[:,None]*direction,axis=1)
        index=int(np.argmin(distances))
        boundaries.append({'boundary':label,'distance_over_L':float(distances[index]),
                           'nearest_xy':(a[index]+t[index]*direction[index]).tolist()})
    locations[name]={'peak_reference_xy':point.tolist(),'nearest_boundary':min(boundaries,key=lambda v:v['distance_over_L']),
                     'distance_to_gauge_A_over_L':float(np.linalg.norm(point-geometry['anchors'][0])),
                     'distance_to_gauge_B_over_L':float(np.linalg.norm(point-geometry['anchors'][1]))}
save_json(root/'hotspot_geometry.json',{'status':'passed','scientific_solves':0,'locations':locations,
          'interpretation':'Location only, not a causal proof. Non-smooth boundary geometry and weak volume-constraint discretization remain hypotheses.'})
print(json.dumps({'status':report['status'],'comparison':report['comparison'],'volume':report['volume'],'locations':locations},indent=2))
