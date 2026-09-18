"""Four authorized contour equilibria, using the existing qualified Ring kernel."""
import json
from pathlib import Path
import shutil
import time
import traceback

import numpy as np


def main(root=Path('/out')):
    from prl.fem.fenicsx_ring import Ring, write_json
    from prl.verification.fenicsx_ring import load_arrays, pressure_basis
    from prl.verification.fenicsx_contour import geometry_audit
    from prl.verification.fenicsx_pressure import same_displacement_mesh, saved_iterates_audit
    from prl.verification.fenicsx_contour_pressure import scope_checks, contour_state_audit, verify_contour_pressure, GEOMETRY_HASHES
    import hashlib

    config = json.loads((root/'configuration.json').read_text())
    qualified = json.loads((root/'prerequisite/configuration.json').read_text())
    started = time.monotonic(); attempted = accepted = 0; current = None; label = None
    try:
        if not all(scope_checks(config, qualified).values()):
            raise ValueError('Frozen contour scope changed')
        (root/'raw').mkdir(exist_ok=False)
        source = load_arrays(root/'geometry_source.npz')
        for name in ['M0','M1']:
            path = root/'input'/f'{name}_input_mesh.npz'
            if hashlib.sha256(path.read_bytes()).hexdigest() != GEOMETRY_HASHES[name]:
                raise ValueError('Frozen input geometry changed')
            geometry = load_arrays(path)
            geometry['metrics'] = geometry_audit(geometry, source)
            if geometry['metrics']['status'] != 'passed':
                raise ValueError('Original geometry gate failed')
            current = Ring({'name':name}, config, root, geometry_input=geometry)
            pressure_basis(current.mesh_data)
            if not same_displacement_mesh(current.mesh_data, load_arrays(root/'comparison'/name/'mesh.npz')):
                raise ValueError('Geometry, displacement map or boundary conditions changed')
            current.tangent_checks()
            initial = np.zeros_like(current.w.x.array)
            for index, pressure in enumerate([0., .02]):
                if attempted >= 4 or time.monotonic()-started > 1140 or shutil.disk_usage(root).free < 10*1024**3+64*1024**2:
                    raise RuntimeError('Authorization, time or disk headroom exhausted')
                label = f'passive_{index}'; attempted += 1
                record = {'status':'unknown','mesh':name,'state':label,'attempted_states':attempted,'accepted_states':accepted}
                write_json(root/'progress.json', record)
                # Ring.solve writes its own progress; restore cumulative counters even on failure.
                try:
                    initial = current.solve(label, pressure, 0., initial)
                finally:
                    write_json(root/'progress.json', record)
                statepath = root/'raw'/f'{name}_state_{label}.npz'
                state = load_arrays(statepath); meta = json.loads(statepath.with_suffix('.json').read_text())
                report = contour_state_audit(current.mesh_data, state, meta, config)
                iterates = saved_iterates_audit(root/'iterates'/f'{name}_{label}', current.mesh_data, state, meta, config)
                report['checks']['saved_iterates'] = iterates['status'] == 'passed'
                report['status'] = 'passed' if all(report['checks'].values()) else 'failed'
                write_json(statepath.with_name(statepath.stem+'_audit.json'), report)
                if report['status'] != 'passed':
                    raise ValueError('Independent gate failed: '+str([k for k,v in report['checks'].items() if not v]))
                accepted += 1
                write_json(root/'last_valid.json', {'mesh':name,'state':label,'accepted_states':accepted})
                write_json(root/'progress.json', {**record,'accepted_states':accepted})
            current = None  # Release one mesh's solver before constructing the next.
        report = verify_contour_pressure(root)
        write_json(root/'verification.json', report)
        write_json(root/'progress.json', {'status':report['status'],'attempted_states':attempted,'accepted_states':accepted})
        return 0 if report['status'] == 'passed' else 2
    except Exception as error:
        write_json(root/'failure.json', {'status':'failed','error':str(error),'traceback':traceback.format_exc(),
            'mesh':current.name if current else None,'label':label,'attempted_states':attempted,'accepted_states':accepted})
        if current is not None:
            np.savez_compressed(root/'last_attempt.npz',mixed_state=current.w.x.array,
                u=current.w.x.array[current.vmap].reshape(-1,2),pressure=current.w.x.array[current.pmap],
                load=float(current.load.value),activation=float(current.activation.value))
        traceback.print_exc()
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
