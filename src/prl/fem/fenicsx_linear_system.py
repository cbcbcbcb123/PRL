"""One retained-initial-state matrix diagnosis; no nonlinear equilibrium solve."""
from __future__ import annotations

import json
from pathlib import Path
import platform
import time
import traceback

import numpy as np
from scipy import sparse
from scipy.sparse.linalg import LinearOperator,onenormest,splu
import scipy
import dolfinx
from petsc4py import PETSc

from prl.fem.fenicsx_ring import Ring,write_json
from prl.verification.fenicsx_pressure import same_displacement_mesh
from prl.verification.fenicsx_ring import load_arrays
from prl.verification.fenicsx_linear_system import sparse_metrics,classify,finite_json


def _json_error(error):
    return {'type':type(error).__name__,'message':str(error)}


def _mumps_values(factor):
    indices=[1,2,3,7,8,12,13,14,15,16,20,21,22,28,29,30,31,32,33,34,35,36]
    result={'infog':{},'rinfog':{}}
    for index in indices:
        try:
            result['infog'][str(index)]=int(factor.getMumpsInfog(index))
        except Exception as error:
            result['infog'][str(index)]='unavailable:'+type(error).__name__
    for index in [1,2,3,4,5,6,7,8,9,10,11,12]:
        try:
            result['rinfog'][str(index)]=float(factor.getMumpsRinfog(index))
        except Exception as error:
            result['rinfog'][str(index)]='unavailable:'+type(error).__name__
    for label,method,entries,cast in [
        ('icntl','getMumpsIcntl',[6,7,8,10,14,18,22,24,28,29],int),
        ('cntl','getMumpsCntl',[1,2,3,4,5],float),
    ]:
        result[label]={}
        for index in entries:
            try:
                result[label][str(index)]=cast(getattr(factor,method)(index))
            except Exception as error:
                result[label][str(index)]='unavailable:'+type(error).__name__
    try:
        result['inertia']=[int(x) for x in factor.getInertia()]
    except Exception as error:
        result['inertia']='unavailable:'+type(error).__name__
    return result


def _mumps_attempt(ksp,matrix,rhs,output=None):
    pc=ksp.getPC()
    try:
        factor_solver_type=pc.getFactorSolverType()
    except Exception as error:
        factor_solver_type='unavailable:'+type(error).__name__
    report={'ksp_type':ksp.getType(),'pc_type':pc.getType(),
            'factor_solver_type':factor_solver_type,'attempts':1,
            'ksp_options_prefix':ksp.getOptionsPrefix(),'matrix_type':matrix.getType()}
    solution=matrix.createVecRight(); solution.set(0)
    right=matrix.createVecLeft(); right.array[:]=rhs
    error=None
    try:
        ksp.setOperators(matrix)
        ksp.setErrorIfNotConverged(False)
        ksp.solve(right,solution)
    except Exception as caught:
        error=_json_error(caught)
    report.update(converged_reason=int(ksp.getConvergedReason()),iterations=int(ksp.getIterationNumber()),
                  pc_failed_reason=int(pc.getFailedReason()),exception=error)
    try:
        report['mumps']=_mumps_values(pc.getFactorMatrix())
    except Exception as caught:
        report['mumps']={'factor_matrix_error':_json_error(caught)}
    if output is not None:
        write_json(output/'mumps_factorization.json',finite_json(report))
        np.savez_compressed(output/'mumps_linear_solution.npz',solution=solution.array.copy())
    report.update(solution_finite=bool(np.all(np.isfinite(solution.array))),
                  solution_norm=float(solution.norm()))
    residual=matrix.createVecLeft(); matrix.mult(solution,residual); residual.axpy(-1,right)
    report['relative_residual']=float(residual.norm()/max(right.norm(),1e-300))
    residual.destroy(); right.destroy(); solution.destroy()
    return report


def _superlu_attempt(matrix,rhs,output=None):
    started=time.monotonic()
    try:
        factor=splu(matrix.tocsc())
        solution=factor.solve(rhs)
        if output is not None:
            np.savez_compressed(output/'superlu_linear_solution.npz',solution=solution)
        relative=float(np.linalg.norm(matrix@solution-rhs)/max(np.linalg.norm(rhs),1e-300))
        pivots=np.abs(factor.U.diagonal())
    except Exception as error:
        return {'status':'failed','attempts':1,'error':_json_error(error),
                'elapsed_seconds':time.monotonic()-started}
    condition=None; condition_error=None
    try:
        inverse=LinearOperator(matrix.shape,matvec=factor.solve,
                               rmatvec=lambda value:factor.solve(value,trans='T'),dtype=float)
        estimate=float(onenormest(matrix)*onenormest(inverse))
        if np.isfinite(estimate):
            condition=estimate
        else:
            condition_error={'type':'NonFiniteEstimate','message':str(estimate)}
    except Exception as error:
        condition_error=_json_error(error)
    return {'status':'passed','attempts':1,'relative_residual':relative,
            'solution_norm':float(np.linalg.norm(solution)),
            'minimum_abs_U_diagonal':float(pivots.min()),
            'maximum_abs_U_diagonal':float(pivots.max()),
            'estimated_condition_1':condition,'condition_estimate_error':condition_error,
            'elapsed_seconds':time.monotonic()-started}


def _workspace_margin_attempt(root,config):
    """Import the retained matrix verbatim; never assemble or update FEM fields."""
    started=time.monotonic()
    with np.load(root/'previous_matrix_csr.npz',allow_pickle=False) as archive:
        arrays={key:archive[key].copy() for key in archive.files}
    previous=json.loads((root/'previous_mumps_diagnosis.json').read_text())
    old_config=json.loads((root/'previous_configuration.json').read_text())
    expected_options={**old_config['solver'],'mat_mumps_icntl_14':100}
    if config['solver']!=expected_options or previous['mumps']['icntl']['14']!=20:
        raise ValueError('Only the approved 20-to-100 workspace change is permitted')
    size=len(arrays['rhs'])
    matrix=PETSc.Mat().createAIJ(size=(size,size),comm=PETSc.COMM_SELF,
        csr=(np.asarray(arrays['indptr'],dtype=PETSc.IntType),
             np.asarray(arrays['indices'],dtype=PETSc.IntType),
             np.asarray(arrays['data'],dtype=PETSc.ScalarType)))
    matrix.assemble()
    native_before=tuple(value.copy() for value in matrix.getValuesCSR())
    identity={key:bool(np.array_equal(value,arrays[key]))
              for key,value in zip(('indptr','indices','data'),native_before)}
    write_json(root/'matrix_identity.json',identity)
    if not all(identity.values()) or matrix.getType()!=previous['matrix_type']:
        raise ValueError('PETSc CSR import changed the retained matrix')
    np.savez_compressed(root/'matrix_csr.npz',**arrays)
    state_before=arrays['initial'].copy()
    ksp=PETSc.KSP().create(comm=PETSc.COMM_SELF)
    prefix=previous['ksp_options_prefix']; ksp.setOptionsPrefix(prefix)
    options=PETSc.Options()
    for name,value in config['solver'].items():
        if name.startswith(('ksp_','pc_','mat_')):
            options[prefix+name]=value
    ksp.setFromOptions()
    mumps=_mumps_attempt(ksp,matrix,arrays['rhs'],root)
    write_json(root/'mumps_diagnosis.json',finite_json(mumps))
    native_after=matrix.getValuesCSR()
    np.savez_compressed(root/'matrix_after.npz',indptr=native_after[0],indices=native_after[1],data=native_after[2])
    np.savez_compressed(root/'state_identity.npz',before=state_before,after=arrays['initial'])
    with np.load(root/'mumps_linear_solution.npz',allow_pickle=False) as actual, np.load(root/'reference_superlu_solution.npz',allow_pickle=False) as reference:
        difference=float(np.linalg.norm(actual['solution']-reference['solution'])/np.linalg.norm(reference['solution']))
    controls=mumps.get('mumps',{})
    unchanged_controls={f'{group}_{key}':value==previous['mumps'][group].get(key)
                        for group in ('icntl','cntl') for key,value in controls.get(group,{}).items()
                        if not (group=='icntl' and key=='14')}
    unchanged_matrix=all(np.array_equal(a,b) for a,b in zip(native_before,native_after))
    checks={'infog_zero':controls.get('infog',{}).get('1')==0,
            'ksp_converged':mumps['converged_reason']>0,'pc_ok':mumps['pc_failed_reason']==0,
            'solution_finite':mumps['solution_finite'],
            'relative_residual':mumps['relative_residual']<=config['relative_residual_limit'],
            'reference_solution':difference<=config['relative_solution_difference_limit'],
            'margin_100':controls.get('icntl',{}).get('14')==100,
            'other_controls_unchanged':bool(unchanged_controls) and all(unchanged_controls.values()),
            'matrix_unchanged':unchanged_matrix,
            'state_unchanged':state_before.tobytes()==arrays['initial'].tobytes()}
    report={'status':'passed' if all(checks.values()) else 'failed','checks':checks,
            'mumps':mumps,'unchanged_controls':unchanged_controls,'relative_solution_difference':difference,
            'matrix_assemblies':0,'mumps_factorizations':1,'superlu_factorizations':0,
            'nonlinear_equilibrium_solves':0,'newton_updates':0,'automatic_retries':0,'gpu':0,
            'scientific_pressure_space_status':'failed','contour':'not_run',
            'versions':{'petsc':PETSc.Sys.getVersion(),'scipy':scipy.__version__,'python':platform.python_version()},
            'elapsed_seconds':time.monotonic()-started}
    write_json(root/'diagnosis.json',finite_json(report))
    print('PRL_F6S1S3_JSON='+json.dumps(finite_json(report),allow_nan=False),flush=True)
    ksp.destroy(); matrix.destroy()
    return 0 if report['status']=='passed' else 2


def main():
    root=Path('/out'); started=time.monotonic()
    config=json.loads((root/'configuration.json').read_text())
    try:
        if config.get('workspace_margin'):
            return _workspace_margin_attempt(root,config)
        source=root/'source_f6s1r'; assembly=root/'assembly'; (assembly/'raw').mkdir(parents=True,exist_ok=False)
        previous_mesh=load_arrays(source/'M0_mesh.npz')
        zero=load_arrays(source/'M0_state_passive_0.npz')
        failed=load_arrays(source/'M0_state_passive_1.npz')
        failed_metadata=json.loads((source/'M0_state_passive_1.json').read_text())
        initial=np.asarray(failed['initial_mixed'])
        state_chain=bool(np.array_equal(initial,zero['mixed_state']))
        case={'name':'M0','segments':64,'radial':[1,1,5]}
        ring=Ring(case,config,assembly)
        same_mesh=same_displacement_mesh(ring.mesh_data,previous_mesh)
        if not same_mesh or not state_chain or failed_metadata['snes_reason']!=-3 or failed_metadata['iterations']!=0:
            raise ValueError('Retained failed initial state or same-mesh identity check failed')
        if initial.shape!=ring.w.x.array.shape:
            raise ValueError('Retained mixed-state layout changed')
        ring.w.x.array[:]=initial; ring.w.x.scatter_forward()
        ring.load.value=.02; ring.activation.value=0.
        problem=ring.problem; snes=problem.solver
        problem.x.array[:]=initial
        before=ring.w.x.array.copy()
        snes.computeFunction(problem.x,problem.b)
        preconditioner=problem.P_mat if problem.P_mat is not None else problem.A
        snes.computeJacobian(problem.x,problem.A,preconditioner)
        after_assembly=ring.w.x.array.copy()
        indptr,indices,values=problem.A.getValuesCSR()
        matrix=sparse.csr_matrix((np.asarray(values).copy(),np.asarray(indices).copy(),np.asarray(indptr).copy()),
                                 shape=problem.A.getSize())
        residual=np.asarray(problem.b.array).copy(); rhs=-residual
        map2=ring.vmap.reshape(-1,2)
        displacement_cells=map2[ring.cells].reshape(len(ring.cells),-1)
        pressure_cells=ring.pmap[ring.pcells]
        metrics=sparse_metrics(matrix,residual,ring.vmap,ring.pmap,displacement_cells,pressure_cells,ring.fixed_mixed)
        np.savez_compressed(root/'matrix_csr.npz',indptr=matrix.indptr,indices=matrix.indices,data=matrix.data,
                            rhs=rhs,residual=residual,displacement=ring.vmap,pressure=ring.pmap,
                            displacement_cells=displacement_cells,pressure_cells=pressure_cells,
                            fixed=ring.fixed_mixed,initial=initial)
        same_matrix=None
        if config.get('report_replay'):
            with np.load(root/'previous_matrix_csr.npz',allow_pickle=False) as previous, np.load(root/'matrix_csr.npz',allow_pickle=False) as current:
                same_matrix={key:bool(np.array_equal(previous[key],current[key])) for key in previous.files}
            write_json(root/'matrix_identity.json',same_matrix)
            if not all(same_matrix.values()):
                raise ValueError('Matrix replay differs from retained F6-S1-S CSR or maps')
        write_json(root/'matrix_metrics.json',finite_json(metrics))
        superlu=_superlu_attempt(matrix,rhs,root)
        write_json(root/'superlu_diagnosis.json',finite_json(superlu))
        print('PRL_SUPERLU_JSON='+json.dumps(finite_json(superlu),allow_nan=False),flush=True)
        mumps=_mumps_attempt(snes.getKSP(),problem.A,rhs,root)
        write_json(root/'mumps_diagnosis.json',finite_json(mumps))
        print('PRL_MUMPS_JSON='+json.dumps(finite_json(mumps),allow_nan=False),flush=True)
        np.savez_compressed(root/'state_identity.npz',initial=initial,before=before,
                            after_assembly=after_assembly,after_factorization=ring.w.x.array.copy(),
                            problem_after=problem.x.array.copy())
        state_unchanged=bool(np.array_equal(before,ring.w.x.array) and np.array_equal(before,after_assembly)
                             and np.array_equal(initial,problem.x.array))
        verdict=classify(metrics,mumps,superlu)
        report={'status':'passed','diagnostic_delivery':'passed','scientific_pressure_space_status':'failed',
                'cause_class':verdict,'same_displacement_mesh':same_mesh,'retained_state_chain':state_chain,
                'same_saved_matrix':same_matrix,
                'original_failure':failed_metadata,'matrix':metrics,'mumps':mumps,'superlu':superlu,
                'state_unchanged':state_unchanged,'nonlinear_equilibrium_solves':0,'newton_updates':0,
                'matrix_assemblies':1,'mumps_factorizations':1,'superlu_factorizations':1,
                'contour':'not_run','automatic_retries':0,'gpu':0,
                'versions':{'dolfinx':dolfinx.__version__,'petsc':PETSc.Sys.getVersion(),
                            'scipy':scipy.__version__,'python':platform.python_version()},
                'elapsed_seconds':time.monotonic()-started}
        if not state_unchanged:
            report.update(status='failed',diagnostic_delivery='failed')
        report=finite_json(report)
        write_json(root/'diagnosis.json',report)
        print('PRL_F6S1S_JSON='+json.dumps(report,allow_nan=False),flush=True)
        return 0 if report['status']=='passed' else 2
    except Exception as error:
        write_json(root/'failure.json',{'status':'failed','error':_json_error(error),
                  'traceback':traceback.format_exc(),'nonlinear_equilibrium_solves':0,
                  'automatic_retries':0,'elapsed_seconds':time.monotonic()-started})
        traceback.print_exc()
        return 2


if __name__=='__main__':
    raise SystemExit(main())
