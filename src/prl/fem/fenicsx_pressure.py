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


def complete_passive_ring(root,config):
    """Complete only the eight approved states using the existing production Ring."""
    from prl.verification.fenicsx_pressure import passive_state_audit,saved_iterates_audit
    fine_only=config.get('fine_passive_only',False)
    child=root/'ring'
    if not fine_only:
        (child/'raw').mkdir(parents=True,exist_ok=False)
    started=time.monotonic(); attempted=0; accepted=0; current=None; label=None
    original=json.loads((root/'comparison/configuration.json').read_text())
    try:
        expected_plan={'M0':[] if fine_only else [2,3,4],'M1':[0,1,2,3,4]}
        maximum=5 if fine_only else 8
        if config['execution_plan']!=expected_plan or config['maximum_equilibrium_solves']!=maximum:
            raise ValueError('Unapproved passive execution plan')
        if fine_only:
            from prl.fem.fenicsx_zero_newton import fixture
            fixture(root/'runtime_zero_newton',config)
        for case in config['meshes']:
            name=case['name']
            if fine_only and name=='M0':
                continue
            current=Ring(case,config,child)
            if fine_only:
                reference=load_arrays(root/'retained_M1_mesh.npz')
                if set(reference)!=set(current.mesh_data) or not all(np.array_equal(reference[k],current.mesh_data[k]) for k in reference):
                    raise ValueError('Original fine mesh or mixed mapping changed')
            pressure_basis(current.mesh_data)
            old_mesh=load_arrays(root/'comparison'/f'{name}_mesh.npz')
            if not same_displacement_mesh(current.mesh_data,old_mesh):
                raise ValueError('Displacement mesh changed from original CG1 control')
            current.tangent_checks()
            initial=np.zeros_like(current.w.x.array)
            if name=='M0':
                retained=root/'retained_passive'
                mesh=load_arrays(retained/'M0_mesh.npz')
                if set(mesh)!=set(current.mesh_data) or not all(np.array_equal(mesh[key],current.mesh_data[key]) for key in mesh):
                    raise ValueError('Retained coarse DG2 mesh/mixed maps changed')
                previous=None
                for index in [0,1]:
                    path=retained/f'M0_state_passive_{index}.npz'
                    state=load_arrays(path)
                    old_path=root/'comparison'/f'M0_state_passive_{index}.npz'
                    old=state_audit(old_mesh,load_arrays(old_path),json.loads(old_path.with_suffix('.json').read_text()),original)
                    report=passive_state_audit(mesh,state,json.loads(path.with_suffix('.json').read_text()),config,name,old)
                    expected=np.zeros_like(state['mixed_state']) if previous is None else previous
                    if report['status']!='passed' or old['status']!='passed' or not np.array_equal(state['initial_mixed'],expected):
                        raise ValueError('Retained accepted-state prerequisite failed')
                    previous=state['mixed_state']
                initial=previous.copy()
            for index in config['execution_plan'][name]:
                if time.monotonic()-started>1140 or shutil.disk_usage(root).free<10*1024**3+64*1024**2:
                    raise RuntimeError('Time or disk headroom reached before next state')
                if attempted>=maximum:
                    raise RuntimeError('Bounded passive authorization exhausted')
                pressure=config['passive_loads'][index]; label=f'passive_{index}'
                attempted+=1
                write_json(root/'progress.json',{'status':'unknown','mesh':name,'state':label,'attempted_states':attempted,'accepted_states':accepted})
                initial=current.solve(label,pressure,0.,initial)
                path=child/'raw'/f'{name}_state_{label}.npz'; state=load_arrays(path)
                meta=json.loads(path.with_suffix('.json').read_text())
                old_path=root/'comparison'/f'{name}_state_{label}.npz'
                old=state_audit(old_mesh,load_arrays(old_path),json.loads(old_path.with_suffix('.json').read_text()),original)
                report=passive_state_audit(current.mesh_data,state,meta,config,name,old)
                report['checks']['CG1_control']=old['status']=='passed'
                iterates=saved_iterates_audit(child/f'iterates/{name}_{label}',current.mesh_data,state,meta,config)
                report['checks']['saved_iterates']=iterates['status']=='passed'
                report['status']='passed' if all(report['checks'].values()) else 'failed'
                write_json(path.with_name(path.stem+'_audit.json'),report)
                if report['status']!='passed':
                    raise ValueError('Independent gate failed: '+str([key for key,value in report['checks'].items() if not value]))
                accepted+=1
                write_json(root/'last_valid.json',{'mesh':name,'label':label,'accepted_states':accepted})
                write_json(root/'progress.json',{'status':'unknown','attempted_states':attempted,'accepted_states':accepted})
        report=verify_pressure(root); write_json(root/'verification.json',report)
        write_json(root/'progress.json',{'status':report['status'],'attempted_states':attempted,'accepted_states':accepted})
        return 0 if report['status']=='passed' else 2
    except Exception as error:
        write_json(root/'failure.json',{'status':'failed','error':str(error),'traceback':traceback.format_exc(),
                   'mesh':current.name if current else None,'label':label,'attempted_states':attempted,'accepted_states':accepted})
        if current is not None:
            np.savez_compressed(root/'last_attempt.npz',mixed_state=current.w.x.array,mesh_name=np.array(current.name),
                                load=float(current.load.value),activation=float(current.activation.value))
        traceback.print_exc()
        return 2


def runtime_interface_probe(root,config):
    """One explicit six-DOF interface fixture, not a FEM/scientific equilibrium.

    Run the production observer and factor-option binder in a real SNES callback
    before any expensive geometry or mechanical assembly is created.
    """
    from types import SimpleNamespace
    from petsc4py import PETSc
    from prl.verification.fenicsx_pressure import verify_interface_probe
    target=root/'runtime_interface'; target.mkdir(exist_ok=False)
    diagonal=np.arange(2.,8.); right=np.arange(1.,7.)
    matrix=PETSc.Mat().createAIJ(size=(6,6),csr=(np.arange(7,dtype=PETSc.IntType),
        np.arange(6,dtype=PETSc.IntType),diagonal),comm=PETSc.COMM_SELF)
    matrix.assemble()
    solution=PETSc.Vec().createSeq(6,comm=PETSc.COMM_SELF); solution.set(0.)
    residual=solution.duplicate(); rhs=PETSc.Vec().createWithArray(right,comm=PETSc.COMM_SELF)
    solver=PETSc.SNES().create(comm=PETSc.COMM_SELF)
    prefix='prl_interface_'; solver.setOptionsPrefix(prefix); matrix.setOptionsPrefix(prefix+'A_')
    def function(snes,vector,value):
        matrix.mult(vector,value); value.axpy(-1.,rhs)
    def jacobian(snes,vector,jac,preconditioner):
        pass  # The already assembled constant diagonal is the exact Jacobian.
    solver.setFunction(function,residual); solver.setJacobian(jacobian,matrix,matrix)
    options=PETSc.Options()
    temporary={key:value for key,value in config['solver'].items() if key!='mat_mumps_icntl_14'}
    for key,value in temporary.items():
        options[prefix+key]=value
    solver.setFromOptions()
    for key in temporary:
        options.delValue(prefix+key)  # PETSc options database only; no filesystem deletion.
    observer=object.__new__(Ring)
    observer.config=config; observer.problem=SimpleNamespace(solver=solver)
    observer.history=[]; observer.vmap=np.arange(4); observer.pmap=np.arange(4,6)
    observer.load=SimpleNamespace(value=0.); observer.activation=SimpleNamespace(value=0.)
    observer.iterate_root=target/'iterates'; observer.iterate_root.mkdir()
    binding=observer.bind_factor_options(); solver.setMonitor(observer.monitor)
    write_json(target/'started.json',{'fixture_snes_solves':1,'fixture_dofs':6,'fem_equilibria':0,'binding':binding})
    solver.solve(None,solution)
    np.savez_compressed(target/'fixture.npz',diagonal=diagonal,rhs=right,initial=np.zeros(6),
                        solution=solution.getArray(readonly=True).copy())
    ksp=solver.getKSP(); pc=ksp.getPC(); factor=pc.getFactorMatrix()
    write_json(target/'solver.json',{'snes_reason':int(solver.getConvergedReason()),
        'iterations':int(solver.getIterationNumber()),'ksp_reason':int(ksp.getConvergedReason()),
        'pc_failed_reason':int(pc.getFailedReason()),'mumps_infog_1':int(factor.getMumpsInfog(1)),
        'mumps_icntl_14':int(factor.getMumpsIcntl(14)),
        'ksp_prefix':ksp.getOptionsPrefix(),'factor_prefix':factor.getOptionsPrefix()})
    report=verify_interface_probe(target); write_json(target/'verification.json',report)
    solver.destroy(); rhs.destroy(); residual.destroy(); solution.destroy(); matrix.destroy()
    if report['status']!='passed':
        raise ValueError('Real PETSc interface preflight failed: '+str(report))
    print('Runtime interface gate passed; now permit the one approved FEM equilibrium.',flush=True)
    return report


def main():
    root=Path('/out'); config=json.loads((root/'configuration.json').read_text())
    if config.get('complete_passive_ring',False):
        return complete_passive_ring(root,config)
    started=time.monotonic(); attempted=0; accepted=0; current=None
    try:
        resumed=config.get('resume_first_ring',False)
        if config.get('runtime_interface_gate',False):
            runtime_interface_probe(root,config)
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
