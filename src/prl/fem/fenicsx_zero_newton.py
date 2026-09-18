"""Bounded six-DOF native diagnostic; never a tissue/FEM equilibrium."""
import faulthandler
import json
from pathlib import Path
from types import SimpleNamespace
import traceback

import numpy as np
from petsc4py import PETSc
from prl.fem.fenicsx_ring import Ring,write_json


def checkpoint(root,event,**details):
    record={'event':event,**details}
    with (root/'calls.jsonl').open('a',encoding='utf-8') as handle:
        handle.write(json.dumps(record,allow_nan=False)+'\n'); handle.flush()
    print('PRL_ZERO_NEWTON '+json.dumps(record),flush=True)


def fixture(root,config,legacy=False):
    root=Path(root); root.mkdir(exist_ok=False)
    diagonal=np.arange(2.,8.); right=np.zeros(6)
    matrix=PETSc.Mat().createAIJ(size=(6,6),csr=(np.arange(7,dtype=PETSc.IntType),
        np.arange(6,dtype=PETSc.IntType),diagonal),comm=PETSc.COMM_SELF)
    matrix.assemble()
    solution=PETSc.Vec().createSeq(6,comm=PETSc.COMM_SELF); solution.set(0.)
    residual=solution.duplicate(); rhs=PETSc.Vec().createWithArray(right,comm=PETSc.COMM_SELF)
    solver=PETSc.SNES().create(comm=PETSc.COMM_SELF); prefix='prl_zero_native_'
    solver.setOptionsPrefix(prefix); matrix.setOptionsPrefix(prefix+'A_')
    def function(snes,vector,value):
        matrix.mult(vector,value); value.axpy(-1.,rhs)
    def jacobian(snes,vector,jac,preconditioner):
        pass
    solver.setFunction(function,residual); solver.setJacobian(jacobian,matrix,matrix)
    options=PETSc.Options()
    temporary={key:value for key,value in config['solver'].items() if key!='mat_mumps_icntl_14'}
    for key,value in temporary.items():
        options[prefix+key]=value
    solver.setFromOptions()
    for key in temporary:
        options.delValue(prefix+key)  # PETSc options only, not files.
    observer=object.__new__(Ring)
    observer.config=config; observer.problem=SimpleNamespace(solver=solver)
    observer.vmap=np.arange(4); observer.pmap=np.arange(4,6)
    observer.load=SimpleNamespace(value=0.); observer.activation=SimpleNamespace(value=0.)
    binding=observer.bind_factor_options(); solver.setMonitor(observer.monitor)
    write_json(root/'identity.json',{'PETSc':PETSc.Sys.getVersion(),'binding':binding,
        'fixture_dofs':6,'scientific_equilibria':0,'legacy':legacy})
    reports=[]
    for index,label in enumerate(['zero'] if legacy else ['zero','loaded','already_converged']):
        observer.history=[]; observer.iterate_root=root/label; observer.iterate_root.mkdir()
        if index==1:
            rhs.setValues(np.arange(6,dtype=PETSc.IntType),np.arange(1.,7.)); rhs.assemble()
        before=solution.getArray(readonly=True).copy()
        checkpoint(root,'solve_enter',case=label)
        solver.solve(None,solution)
        iterations=int(solver.getIterationNumber()); reason=int(solver.getConvergedReason())
        checkpoint(root,'solve_return',case=label,iterations=iterations,snes_reason=reason,
                   residual=float(solver.getFunctionNorm()))
        np.savez_compressed(root/f'{label}.npz',diagonal=diagonal,rhs=rhs.getArray(readonly=True).copy(),
                            initial=before,solution=solution.getArray(readonly=True).copy())
        if legacy:
            checkpoint(root,'get_ksp_enter'); ksp=solver.getKSP()
            checkpoint(root,'get_pc_enter'); pc=ksp.getPC()
            checkpoint(root,'get_reasons_enter')
            checkpoint(root,'get_reasons_return',ksp_reason=int(ksp.getConvergedReason()),pc_reason=int(pc.getFailedReason()))
            checkpoint(root,'get_factor_enter'); factor=pc.getFactorMatrix()
            checkpoint(root,'get_factor_return',factor_exists=bool(factor),handle=int(factor.handle))
            checkpoint(root,'get_infog_enter')
            info=int(factor.getMumpsInfog(1))
            checkpoint(root,'get_infog_return',infog_1=info)
            raise RuntimeError('Legacy hazard did not reproduce; no permission to assume its cause')
        report=observer.linear_solver_report(iterations)
        expected=np.arange(1.,7.)/diagonal if index else np.zeros(6)
        checks={'snes':reason>0,'solution':bool(np.linalg.norm(solution.getArray(readonly=True)-expected)<1e-12),
                'iterations':iterations==(1 if index==1 else 0),'saved_iterates':len(observer.history)==iterations+1}
        if index==1:
            checks['factor']=report.get('status')=='passed' and report.get('mumps_icntl_14')==100 and report.get('mumps_infog_1')==0
        else:
            checks['no_factor_read']=report.get('status')=='not_run' and all(report.get(key) is None for key in ['ksp_reason','pc_failed_reason','mumps_infog_1','mumps_infog_2','mumps_icntl_14'])
            checks['no_update']=np.array_equal(before,solution.getArray(readonly=True))
        record={'case':label,'checks':checks,'status':'passed' if all(checks.values()) else 'failed',
                'iterations':iterations,'snes_reason':reason,'linear_solver':report}
        reports.append(record); write_json(root/'verification.json',{'status':'passed' if all(r['status']=='passed' for r in reports) else 'failed','cases':reports})
        if record['status']!='passed':
            raise ValueError('Zero-Newton runtime interface failed: '+str(record))
    solver.destroy(); rhs.destroy(); residual.destroy(); solution.destroy(); matrix.destroy()
    return reports


def main():
    faulthandler.enable(all_threads=True)
    root=Path('/out'); config=json.loads((root/'configuration.json').read_text())
    try:
        fixture(root/'legacy',config,legacy=True)
    except Exception as error:
        write_json(root/'python_failure.json',{'status':'failed','error':repr(error),'traceback':traceback.format_exc()})
        traceback.print_exc(); return 2
    return 0


if __name__=='__main__':
    raise SystemExit(main())
