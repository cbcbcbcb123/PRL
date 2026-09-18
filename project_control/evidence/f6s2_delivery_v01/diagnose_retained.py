"""Replay the actual retained payload; no Docker/FEM invocation and no raw edits."""
import importlib.util
import json
from pathlib import Path
from prl.runs.fenicsx_runtime import save_json
from prl.runs.fenicsx_ring import digest
from prl.verification.ventricle_3d import load_arrays,state_audit

root=Path('E:/Temp-Projects/PRL-results/ventricle_fem/f6s2_idealized_3d_v01_20260918')
workspace=Path(__file__).resolve().parents[3]
original=root/'sources_at_execution/src/prl/verification/ventricle_3d.py'
spec=importlib.util.spec_from_file_location('frozen_failed_audit',original)
old=importlib.util.module_from_spec(spec); spec.loader.exec_module(old)
data=load_arrays(root/'raw/M0_mesh.npz'); state=load_arrays(root/'raw/M0_state_zero.npz')
config=json.loads((root/'configuration.json').read_text())
metadata=json.loads((root/'raw/M0_state_zero.json').read_text())
before={str(p):digest(p) for p in [root/'raw/M0_mesh.npz',root/'raw/M0_state_zero.npz',root/'failure.json',root/'verification.json']}
error=None
try:
    old.state_audit(data,state,metadata,config)
except IndexError as exception:
    error=repr(exception)
after=state_audit(data,state,metadata,config)
source_hashes=json.loads((root/'source_hashes.json').read_text())
changes={p:{'at_execution':sha,'after_fix':digest(workspace/p)}
         for p,sha in source_hashes.items() if digest(workspace/p)!=sha}
checks={'original_error_reproduced':error=="IndexError('index 1 is out of bounds for axis 0 with size 1')",
        'retained_zero_after_fix_passed':after['status']=='passed',
        'raw_failure_native_report_unchanged':all(digest(p)==sha for p,sha in before.items()),
        'changes_only_interface_and_regression':set(changes)=={'src/prl/fem/fenicsx_ventricle.py','src/prl/verification/ventricle_3d.py','tests/prl/test_ventricle_3d.py'}}
report={'status':'passed' if all(checks.values()) else 'failed','checks':checks,
        'original_error':error,'actual_shapes':{k:list(data[k].shape) for k in ['mixed_u_map','mixed_p_map']},
        'pressure_shape':list(state['pressure'].shape),'source_changes':changes,
        'root_cause':'DOLFINx collapse maps retained a leading row dimension; the new adapter omitted flattening used by the existing 2D adapter. Saved scalar pressure became (1,325), and the independent 3D reader assumed (325,).',
        'minimum_fix':'Normalize producer DOF maps; reader accepts exactly (N,) or (1,N), rejects all other shapes and checks mixed-map consistency.',
        'regression_red':'one deterministic row-layout test failed with same IndexError before patch',
        'post_fix_zero_state':after,'original_stage_status':'failed','loaded_3d_qualification':'not_run',
        'native_producer_fix_validation':'not_run','new_FEM_solves':0,'new_container_invocations':0,
        'mumps_unused_option_note':'The zero-load solve took zero Newton updates. An unused MUMPS option warning is not an observed MUMPS failure; LU has not yet been tested in this 3D stage.'}
target=root/'interface_diagnosis.json'
if target.exists():
    raise FileExistsError('Diagnostic evidence is create-only')
save_json(target,report)
print(json.dumps(report,ensure_ascii=False,indent=2))
raise SystemExit(0 if report['status']=='passed' else 1)
