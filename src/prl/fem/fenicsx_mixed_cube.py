"""One registered FEniCSx cube batch; no retry, continuation, or ventricular solve."""
import gc
import json
from pathlib import Path
import signal
import time
import traceback
import basix
import basix.ufl
import dolfinx
from dolfinx import fem, mesh
from dolfinx.fem import petsc
from mpi4py import MPI
from petsc4py import PETSc
import numpy as np
import ufl
from prl.fem.fenicsx_ring import Ring, write_json
from prl.fem.mixed_material import passive_energy
from prl.fem.mixed_cube_spec import disposition
from prl.fem.positive_j import admissible_scale
from prl.verification.ventricle_3d import load_arrays, mapping_checks, kinematics, extra_points
from prl.verification.mixed_cube import boundary_data, assembled, audit, convergence


def exact_displacement_numpy(x,kind):
    values=np.zeros_like(x)
    if kind=='affine':
        values=x*np.array([.001,-.0004,-.0003])[:,None]
    elif kind=='shear':
        values[0]=.1*x[1]
    elif kind=='mms':
        values[0]=.002*np.sin(np.pi*x[0])*np.sin(np.pi*x[1])*np.sin(np.pi*x[2])
    elif kind=='quadratic_volume':
        values[0]=.002*x[0]**2
    elif kind=='isochoric_mms':
        values[0]=.002*np.sin(np.pi*x[1])*np.sin(np.pi*x[2])
    else:
        raise ValueError('Unknown registered case')
    return values


def exact_displacement_ufl(x,kind):
    if kind=='affine':
        return ufl.as_vector((.001*x[0],-.0004*x[1],-.0003*x[2]))
    if kind=='shear':
        return ufl.as_vector((.1*x[1],0.,0.))
    if kind=='mms':
        return ufl.as_vector((.002*ufl.sin(np.pi*x[0])*ufl.sin(np.pi*x[1])*ufl.sin(np.pi*x[2]),0.,0.))
    if kind=='quadratic_volume':
        return ufl.as_vector((.002*x[0]**2,0.,0.))
    if kind=='isochoric_mms':
        return ufl.as_vector((.002*ufl.sin(np.pi*x[1])*ufl.sin(np.pi*x[2]),0.,0.))
    raise ValueError('Unknown registered case')


class Cube(Ring):
    """Only reuse dimension-independent PETSc vector/factor bookkeeping."""
    def __init__(self,case,config,root,deadline):
        self.name=case['name']; self.case=case; self.config=config; self.root=root; self.deadline=deadline
        self.history=[]; self.iterate_root=root/'iterates'/self.name
        self.iterate_root.mkdir(parents=True,exist_ok=False)
        data=load_arrays(root/'input'/f'n{case["n"]}.npz')
        coordinate=basix.ufl.element('Lagrange','tetrahedron',1,shape=(3,))
        self.domain=domain=mesh.create_mesh(MPI.COMM_WORLD,data['tetrahedra'],coordinate,data['xyz'])
        count=domain.topology.index_map(3).size_local
        if MPI.COMM_WORLD.size!=1 or count!=6*case['n']**3:
            raise ValueError('Frozen mesh count or MPI rank mismatch')
        self.cell_ids=np.arange(count,dtype=np.int32)
        domain.topology.create_connectivity(2,3)
        exterior=mesh.exterior_facet_indices(domain.topology)
        middle=mesh.compute_midpoints(domain,2,exterior)
        labels=np.zeros(len(exterior),dtype=np.int32)
        for axis in range(3):
            for side in [0,1]:
                labels[np.abs(middle[:,axis]-side)<1e-12]=2*axis+side+1
        if np.any(labels==0):
            raise ValueError('Cube boundary tags missing')
        order=np.argsort(exterior)
        facet_tags=mesh.meshtags(domain,2,exterior[order],labels[order])
        ue=basix.ufl.element('Lagrange','tetrahedron',2,shape=(3,))
        pe=basix.ufl.element('Lagrange','tetrahedron',1)
        self.space=fem.functionspace(domain,basix.ufl.mixed_element([ue,pe]))
        self.w=fem.Function(self.space)
        self.vspace,self.vmap=self.space.sub(0).collapse(); self.pspace,self.pmap=self.space.sub(1).collapse()
        self.vmap=np.asarray(self.vmap,dtype=np.int32).reshape(-1); self.pmap=np.asarray(self.pmap,dtype=np.int32).reshape(-1)
        self.coords=self.vspace.tabulate_dof_coordinates()
        self.cells=np.array([self.vspace.dofmap.cell_dofs(c) for c in self.cell_ids])
        self.pcells=np.array([self.pspace.dofmap.cell_dofs(c) for c in self.cell_ids])
        self.fixed=np.repeat((np.abs(self.coords[:,0])<1e-12)[:,None],3,axis=1)
        self.fixed_mixed=self.vmap.reshape(-1,3)[self.fixed]
        self.free_mixed=np.ones(len(self.w.x.array),dtype=bool); self.free_mixed[self.fixed_mixed]=False
        boundary_function=fem.Function(self.vspace)
        boundary_function.interpolate(lambda x:exact_displacement_numpy(x,case['kind']))
        self.boundary_function=boundary_function
        boundary_dofs=fem.locate_dofs_topological((self.space.sub(0),self.vspace),2,exterior[labels==1])
        bcs=[fem.dirichletbc(boundary_function,boundary_dofs,self.space.sub(0))]
        if not np.array_equal(np.sort(bcs[0].dof_indices()[0]),np.sort(self.fixed_mixed)):
            raise ValueError('Nonzero Dirichlet DOF map mismatch')
        u,pressure=ufl.split(self.w)
        F=ufl.variable(ufl.Identity(3)+ufl.grad(u)); J=ufl.det(F)
        energy=passive_energy(F,J,pressure,config['mu'],case['kappa'],ufl.inner)
        P=ufl.diff(energy,F)
        x=ufl.SpatialCoordinate(domain); prescribed=exact_displacement_ufl(x,case['kind'])
        exact_F=ufl.variable(ufl.Identity(3)+ufl.grad(prescribed)); exact_J=ufl.det(exact_F)
        dummy_pressure=fem.Constant(domain,PETSc.ScalarType(0))
        exact_energy=passive_energy(exact_F,exact_J,dummy_pressure,config['mu'],case['kappa'],ufl.inner)
        # Substitute compatible pressure AFTER constitutive differentiation.
        exact_P=ufl.replace(ufl.diff(exact_energy,exact_F),{dummy_pressure:case['kappa']*(exact_J-1)})
        # Affine patches have spatially constant P*, hence exactly zero body.
        # Keep its domain: FFCx can simplify div(P*) to a domain-free zero,
        # whose coordinate hash is 0 and is rejected by this native evaluator.
        body=(fem.Constant(domain,np.zeros(3,dtype=PETSc.ScalarType))
              if case['kind'] in {'affine','shear'} else -ufl.div(exact_P))
        traction=exact_P*ufl.FacetNormal(domain)
        dx=ufl.Measure('dx',domain=domain,metadata={'quadrature_degree':6})
        ds=ufl.Measure('ds',domain=domain,subdomain_data=facet_tags,metadata={'quadrature_degree':6})
        test=ufl.TestFunction(self.space); v,_=ufl.split(test)
        residual=ufl.derivative(energy*dx,self.w,test)-ufl.dot(body,v)*dx
        for tag in range(2,7):
            residual-=ufl.dot(traction,v)*ds(tag)
        self.residual=residual; self.residual_form=fem.form(residual)
        self.problem=petsc.NonlinearProblem(residual,self.w,bcs=bcs,petsc_options_prefix='Cube_'+self.name+'_',
            petsc_options={k:value for k,value in config['solver'].items() if k!='mat_mumps_icntl_14'})
        self.factor_options=self.bind_factor_options()
        self.qpoints,self.qweights=basix.make_quadrature(basix.CellType.tetrahedron,6)
        fq,fw=basix.make_quadrature(basix.CellType.triangle,6)
        self.expressions={key:fem.Expression(value,self.qpoints) for key,value in
            {'F':F,'J':J,'P':P,'body':body}.items()}
        write_json(self.iterate_root/'expression_metadata.json',{
            'expected_ufl_coordinate_hash':int(domain.ufl_domain().ufl_coordinate_element().basix_hash()),
            'expressions':{key:{'coordinate_hash':int(expression.ufcx_expression.coordinate_element_hash)}
                for key,expression in self.expressions.items()},
            'body_representation':'mesh_bound_zero_constant' if case['kind'] in {'affine','shear'} else 'analytic_negative_divergence',
            'SNES_calls':0})
        self.mesh_data={'coordinates':self.coords,'cells':self.cells,
            'pressure_coordinates':self.pspace.tabulate_dof_coordinates(),'pressure_cells':self.pcells,
            'fixed':self.fixed,'qpoints':self.qpoints,'qweights':self.qweights,
            'facet_qpoints':fq,'facet_qweights':fw,'mixed_u_map':self.vmap,'mixed_p_map':self.pmap,
            **boundary_data(self.coords,self.cells)}
        if not all(mapping_checks(self.mesh_data).values()):
            raise ValueError('Independent ordering/weights mismatch')
        np.savez_compressed(root/'raw'/f'{self.name}_mesh.npz',**self.mesh_data)
        write_json(self.iterate_root/'factor_option_binding.json',self.factor_options)
        self.guard_history=[]
        if config.get('trial_guard'):
            self.guard_points=np.concatenate((self.qpoints,extra_points()))
            self.guard_expression=fem.Expression(F,self.guard_points)
            self.problem.solver.setLineSearchPreCheck(self.guard_direction)
            write_json(self.iterate_root/'guard_binding.json',{
                'status':'passed','petsc_version':list(PETSc.Sys.getVersion()),
                'callback':'SNES.setLineSearchPreCheck(X,Y) -> changed_direction',
                'update_sign':'X - lambda Y','spatial_points':len(self.guard_points),
                'scope':'callback bound; actual invocation and path verification still required'})
        self.problem.solver.setMonitor(self.monitor)

    def guard_direction(self,current_vector,direction_vector):
        """PETSc BT precheck: scale Y before ANY trial residual evaluation."""
        if time.monotonic()>self.deadline:
            raise TimeoutError('Reached preservation reserve before candidate check')
        current=current_vector.getArray(readonly=True).copy()
        direction=direction_vector.getArray(readonly=True).copy()
        sequence=len(self.guard_history)
        target=self.iterate_root/f'candidate_{sequence:03d}.npz'
        if target.exists():
            raise FileExistsError('Repeated precheck sequence; no overwrite')
        np.savez_compressed(target,current_mixed=current,direction_mixed=direction)
        saved=self.w.x.array.copy()
        try:
            self.w.x.array[:]=current; self.w.x.scatter_forward()
            base=np.asarray(self.guard_expression.eval(self.domain,self.cell_ids)).copy()
            self.w.x.array[:]=current-direction; self.w.x.scatter_forward()
            trial=np.asarray(self.guard_expression.eval(self.domain,self.cell_ids)).copy()
        finally:
            self.w.x.array[:]=saved; self.w.x.scatter_forward()
        settings=self.config['trial_guard']
        try:
            report=admissible_scale(base,trial-base,floor=settings['floor'],max_halvings=settings['max_halvings'])
        except Exception as error:
            write_json(self.iterate_root/'guard_failure.json',{'status':'failed','sequence':sequence,'reason':repr(error)})
            raise
        report.update(sequence=sequence,newton_iteration=int(self.problem.solver.getIterationNumber()))
        self.guard_history.append(report)
        write_json(self.iterate_root/'guard_history.json',self.guard_history)
        direction_vector.scale(report['scale'])
        return report['scale']!=1.

    def state(self):
        residual=self.vector(self.residual_form)
        values={'u':self.w.x.array[self.vmap].reshape(-1,3).copy(),
            'pressure':self.w.x.array[self.pmap].copy(),'mixed_state':self.w.x.array.copy(),
            'initial_mixed':np.zeros_like(self.w.x.array),
            'force_residual':residual[self.vmap].reshape(-1,3),'weak_residual':residual[self.pmap]}
        for key,expression in self.expressions.items():
            try:
                values[key]=np.asarray(expression.eval(self.domain,self.cell_ids))
            except Exception as error:
                write_json(self.iterate_root/'expression_failure.json',{
                    'expression':key,'reason':repr(error),
                    'coordinate_hash':int(expression.ufcx_expression.coordinate_element_hash)})
                raise RuntimeError(f'{key} expression evaluation failed: {error}') from error
        return values,residual

    def precheck(self):
        self.w.x.array[self.vmap]=self.boundary_function.x.array
        self.w.x.array[self.pmap]=0.; self.w.x.scatter_forward()
        state,_=self.state(); independent=assembled(self.mesh_data,state,self.case)
        errors={key:float(np.max(np.abs(independent[source]-state[key]))) for key,source in
                [('F','F'),('J','J'),('P','P'),('body','body'),('force_residual','force'),('weak_residual','weak')]}
        direction=np.random.default_rng(91826).normal(size=len(self.w.x.array))*.001
        direction[self.fixed_mixed]=0.
        tangent=petsc.assemble_matrix(fem.form(ufl.derivative(self.residual,self.w,ufl.TrialFunction(self.space))))
        tangent.assemble(); vector=PETSc.Vec().createWithArray(direction,comm=MPI.COMM_WORLD)
        product=tangent.createVecLeft(); tangent.mult(vector,product)
        saved=self.w.x.array.copy(); h=1e-6
        self.w.x.array[:]=saved+h*direction; forward=self.vector(self.residual_form)
        self.w.x.array[:]=saved-h*direction; backward=self.vector(self.residual_form)
        tangent_error=float(np.linalg.norm((forward-backward)/(2*h)-product.array)/max(np.linalg.norm(product.array),1e-12))
        self.w.x.array[:]=0.; self.w.x.scatter_forward()
        vector.destroy(); product.destroy(); tangent.destroy()
        report={'status':'passed' if max(errors.values())<=2e-7 and max(errors['F'],errors['J'])<=1e-10 and tangent_error<=2e-5 else 'failed',
            'errors':errors,'tangent_relative_error':tangent_error,'SNES_calls':0,
            'state':'interpolated prescribed u and zero p; restored to zero before solve'}
        write_json(self.root/'raw'/f'{self.name}_precheck.json',report)
        if report['status']!='passed':
            raise ValueError('Independent native load/assembly/tangent mismatch')

    def monitor(self,solver,iteration,norm):
        mixed=solver.getSolution().getArray(readonly=True).copy()
        u=mixed[self.vmap].reshape(-1,3)
        _,J,_,_,_,_=kinematics(self.mesh_data,u,extra_points())
        _,quadrature_J,_,_,_,_=kinematics(self.mesh_data,u,self.qpoints)
        minimum=min(float(J.min()),float(quadrature_J.min()))
        self.history.append({'iteration':int(iteration),'residual':float(norm),'minimum_sampled_J':minimum})
        target=self.iterate_root/f'iterate_{iteration:03d}.npz'
        if target.exists():
            raise FileExistsError('Repeated accepted-iterate number; no overwrite')
        np.savez_compressed(target,mixed_state=mixed,u=u,pressure=mixed[self.pmap],iteration=iteration,residual=norm)
        write_json(self.iterate_root/'history.json',self.history)
        if not np.isfinite(J).all() or not np.isfinite(quadrature_J).all() or minimum<=0:
            raise ValueError('Nonpositive/nonfinite accepted iterate J')
        if time.monotonic()>self.deadline:
            raise TimeoutError('Reached 120-second preservation reserve')

    def solve_case(self):
        self.w.x.array[:]=0.; self.w.x.scatter_forward()
        np.savez_compressed(self.iterate_root/'initial.npz',mixed_state=self.w.x.array.copy())
        started=time.monotonic()
        # Exactly one call per registered case. Ordinary negative SNES reason is recorded.
        self.problem.solve(); self.w.x.scatter_forward()
        state,residual=self.state()
        iterations=int(self.problem.solver.getIterationNumber())
        metadata={'snes_reason':int(self.problem.solver.getConvergedReason()),'iterations':iterations,
            'free_residual_norm':float(np.linalg.norm(residual[self.free_mixed])),
            'linear_solver':self.linear_solver_report(iterations),'history':self.history,
            'elapsed_seconds':time.monotonic()-started,'mixed_dofs':len(self.w.x.array),
            'tetrahedra':len(self.cells),'initial_state':'all-zero mixed vector, exact Dirichlet imposed by solver'}
        np.savez_compressed(self.root/'raw'/f'{self.name}_state.npz',**state)
        write_json(self.root/'raw'/f'{self.name}_state.json',metadata)
        report,derived=audit(self.mesh_data,state,metadata,self.case,self.config)
        report['cost']=metadata
        np.savez_compressed(self.root/'raw'/f'{self.name}_derived.npz',**derived)
        write_json(self.root/'raw'/f'{self.name}_audit.json',report)
        return report


def main():
    root=Path('/out'); config=json.loads((root/'configuration.json').read_text())
    (root/'raw').mkdir(exist_ok=False)
    start=time.monotonic(); deadline=start+config['resources']['seconds']-config['resources']['stop_reserve_seconds']
    current=None; reports={}; attempted=0; stop=None
    def interrupted(signum,frame):
        raise TimeoutError('Host stop signal '+str(signum))
    signal.signal(signal.SIGTERM,interrupted)
    try:
        for case in config['cases']:
            if time.monotonic()>deadline:
                raise TimeoutError('No new case inside preservation reserve')
            write_json(root/'progress.json',{'status':'unknown','case':case['name'],'phase':'assembly_precheck','attempted_solves':attempted})
            print(case['name']+': building and checking native forms',flush=True)
            built=time.monotonic(); current=Cube(case,config,root,deadline); current.precheck()
            preparation=time.monotonic()-built
            write_json(root/'progress.json',{'status':'unknown','case':case['name'],'phase':'single_solve','attempted_solves':attempted+1})
            attempted+=1
            report=current.solve_case(); report['preparation_seconds']=preparation
            reports[case['name']]=report
            write_json(root/'cases.json',reports)
            print(case['name']+': '+report['status']+' '+json.dumps(report['metrics']),flush=True)
            if disposition(case['kind'],report)=='stop_batch':
                stop='patch_prerequisite_or_safety_failure'; break
            current=None; gc.collect()
    except Exception as error:
        stop=repr(error)
        if current is not None:
            np.savez_compressed(root/'failure_state.npz',mixed_state=current.w.x.array.copy(),
                u=current.w.x.array[current.vmap].reshape(-1,3),pressure=current.w.x.array[current.pmap])
        write_json(root/'failure.json',{'status':'failed','reason':stop,'traceback':traceback.format_exc(),
            'case':current.name if current else None,'attempted_solves':attempted,'automatic_retries':0})
        traceback.print_exc()
    convergence_report=convergence(reports,config)
    not_run=[case['name'] for case in config['cases'] if case['name'] not in reports]
    status='passed' if stop is None and not not_run and all(item['status']=='passed' for item in reports.values()) and convergence_report['status']=='passed' else 'failed'
    summary={'status':status,'cases':reports,'convergence':convergence_report,'not_run_or_unfinished':not_run,
        'stop_reason':stop,'attempted_solves':attempted,'automatic_retries':0,'container_invocations':1,
        'elapsed_seconds':time.monotonic()-start,'dolfinx_version':dolfinx.__version__,
        'original_ventricular_gate':'failed_unchanged','biology':'not_run','growth':'not_run','fsi':'not_run'}
    write_json(root/'summary.json',summary)
    return 0 if status=='passed' else 2


if __name__=='__main__':
    raise SystemExit(main())
