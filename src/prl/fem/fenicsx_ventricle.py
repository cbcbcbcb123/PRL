"""Idealized 3D solid in the pinned FEniCSx runtime, with first-failure stop."""
import json
from pathlib import Path
import time
import traceback
import basix
import basix.ufl
import dolfinx
from dolfinx import fem,mesh
from dolfinx.fem import petsc
from mpi4py import MPI
from petsc4py import PETSc
import numpy as np
from scipy.spatial import cKDTree
import ufl

from prl.fem.fenicsx_ring import Ring,write_json
from prl.verification.ventricle_3d import load_arrays,state_audit,mapping_checks,verify
from prl.fem.ventricle_protocol import advance_case,restart_identity
from prl.fem.mixed_material import passive_energy


class VentricularSolid(Ring):
    """Reuse qualified SNES bookkeeping only; geometry/forms/states are truly 3D.

    Inherited vector, tangent_checks, trace, factor binding/readback are dimension
    independent. Neither the 2D constructor, solve nor monitor is called.
    """
    def __init__(self,case,config,root):
        self.name=case['name']; self.config=config; self.root=root
        data=load_arrays(root/'input'/f'{self.name}_geometry.npz')
        geometry=json.loads((root/'input'/f'{self.name}_geometry.json').read_text())
        write_json(root/'raw'/f'{self.name}_geometry.json',geometry)
        if geometry['status']!='passed':
            raise ValueError('Reference geometry rejected')
        coordinate=basix.ufl.element('Lagrange','tetrahedron',1,shape=(3,))
        self.domain=domain=mesh.create_mesh(MPI.COMM_WORLD,data['tetrahedra'],coordinate,data['xyz'])
        count=domain.topology.index_map(3).size_local
        if MPI.COMM_WORLD.size!=1 or count!=len(data['tetrahedra']):
            raise ValueError('Single-rank complete mesh required')
        self.cell_ids=np.arange(count,dtype=np.int32)
        self.layers=data['layers'][domain.topology.original_cell_index]
        cell_tags=mesh.meshtags(domain,3,self.cell_ids,self.layers)
        domain.topology.create_connectivity(2,3)
        exterior=mesh.exterior_facet_indices(domain.topology)
        midpoints=mesh.compute_midpoints(domain,2,exterior)
        centers=data['xyz'][data['inner_faces']].mean(axis=1)
        distance,_=cKDTree(centers).query(midpoints)
        inner=np.sort(exterior[distance<1e-12])
        if len(inner)!=len(centers):
            raise ValueError('Inner pressure facet mapping failed')
        facet_tags=mesh.meshtags(domain,2,inner,np.ones(len(inner),dtype=np.int32))
        ue=basix.ufl.element('Lagrange','tetrahedron',2,shape=(3,))
        pe=basix.ufl.element('Lagrange','tetrahedron',1)
        self.space=fem.functionspace(domain,basix.ufl.mixed_element([ue,pe]))
        self.w=fem.Function(self.space)
        self.vspace,self.vmap=self.space.sub(0).collapse()
        self.pspace,self.pmap=self.space.sub(1).collapse()
        self.vmap=np.asarray(self.vmap,dtype=np.int32).reshape(-1)
        self.pmap=np.asarray(self.pmap,dtype=np.int32).reshape(-1)
        self.coords=self.vspace.tabulate_dof_coordinates()
        self.cells=np.array([self.vspace.dofmap.cell_dofs(c) for c in self.cell_ids])
        self.pcells=np.array([self.pspace.dofmap.cell_dofs(c) for c in self.cell_ids])
        self.fixed=np.repeat((np.abs(self.coords[:,2])<1e-12)[:,None],3,axis=1)
        mapped=self.vmap.reshape(-1,3)
        bcs=[fem.dirichletbc(PETSc.ScalarType(0),mapped[self.fixed[:,k],k],self.space.sub(0).sub(k)) for k in range(3)]
        self.fixed_mixed=mapped[self.fixed]
        self.free_mixed=np.ones(len(self.w.x.array),dtype=bool); self.free_mixed[self.fixed_mixed]=False
        u,pressure=ufl.split(self.w)
        self.load=fem.Constant(domain,PETSc.ScalarType(0))
        self.activation=fem.Constant(domain,PETSc.ScalarType(0))
        F=ufl.variable(ufl.Identity(3)+ufl.grad(u)); J=ufl.det(F)
        x=ufl.SpatialCoordinate(domain)
        normal=ufl.as_vector([x[k]/config['axes'][k]**2 for k in range(3)])
        normal=normal/ufl.sqrt(ufl.inner(normal,normal))
        active_tensor=(ufl.Identity(3)-ufl.outer(normal,normal))/2
        passive=passive_energy(F,J,pressure,config['mu'],config['kappa'],ufl.inner)
        active=self.activation/2*(ufl.inner(F*active_tensor,F)-ufl.tr(active_tensor))
        dx=ufl.Measure('dx',domain=domain,subdomain_data=cell_tags,metadata={'quadrature_degree':6})
        ds=ufl.Measure('ds',domain=domain,subdomain_data=facet_tags,metadata={'quadrature_degree':6})
        cavity=-ufl.dot(x+u,ufl.cofac(F)*ufl.FacetNormal(domain))/3*ds(1)
        active_energy=active*dx(3); pressure_energy=-self.load*cavity
        test=ufl.TestFunction(self.space)
        residual=ufl.derivative(passive*dx+active_energy+pressure_energy,self.w,test)
        self.parts={'pressure':ufl.derivative(pressure_energy,self.w,test),
                    'active':ufl.derivative(active_energy,self.w,test),'total':residual}
        self.residual_form=fem.form(residual); self.volume_form=fem.form(cavity)
        self.active_energy_form=fem.form(active_energy)
        self.problem=petsc.NonlinearProblem(residual,self.w,bcs=bcs,petsc_options_prefix='V3D_'+self.name+'_',
            petsc_options={k:v for k,v in config['solver'].items() if k!='mat_mumps_icntl_14'})
        self.factor_options=self.bind_factor_options()
        chi=fem.Function(fem.functionspace(domain,('DG',0)))
        for c in self.cell_ids:
            chi.x.array[chi.function_space.dofmap.cell_dofs(c)]=float(self.layers[c]==3)
        pa=chi*ufl.diff(active,F); piola=ufl.diff(passive,F)+pa
        self.qpoints,self.qweights=basix.make_quadrature(basix.CellType.tetrahedron,6)
        fq,fw=basix.make_quadrature(basix.CellType.triangle,6)
        self.expressions={k:fem.Expression(value,self.qpoints) for k,value in
                          {'F':F,'J':J,'stress':piola*F.T/J,'active_stress':pa*F.T/J}.items()}
        tree=cKDTree(self.coords)
        surface_maps={}
        for key in ['inner_faces','outer_faces']:
            vertices=data['xyz'][data[key]]
            targets=np.concatenate([vertices,np.stack([(vertices[:,1]+vertices[:,2])/2,
                (vertices[:,0]+vertices[:,2])/2,(vertices[:,0]+vertices[:,1])/2],axis=1)],axis=1)
            distance,indices=tree.query(targets.reshape(-1,3))
            if np.max(distance)>1e-12:
                raise ValueError('P2 surface DOF mapping failed')
            surface_maps[key]=indices.reshape(-1,6)
        self.mesh_data={'coordinates':self.coords,'cells':self.cells,'layers':self.layers,
            'pressure_coordinates':self.pspace.tabulate_dof_coordinates(),'pressure_cells':self.pcells,
            'fixed':self.fixed,'qpoints':self.qpoints,'qweights':self.qweights,
            'facet_qpoints':fq,'facet_qweights':fw,'mixed_u_map':self.vmap,'mixed_p_map':self.pmap,**surface_maps}
        np.savez_compressed(root/'raw'/f'{self.name}_mesh.npz',**self.mesh_data)
        if not all(mapping_checks(self.mesh_data).values()):
            raise ValueError('Independent basis ordering check failed')
        self.history=[]; self.problem.solver.setMonitor(self.monitor)

    def monitor(self,solver,iteration,norm):
        self.history.append({'iteration':int(iteration),'residual':float(norm)})
        write_json(self.iterate_root/'history.json',self.history)
        mixed=solver.getSolution().getArray(readonly=True).copy()
        target=self.iterate_root/f'iterate_{iteration:03d}.npz'
        if target.exists():
            raise FileExistsError('Retained iteration already exists')
        np.savez_compressed(target,mixed_state=mixed,u=mixed[self.vmap].reshape(-1,3),
            pressure=mixed[self.pmap],load=float(self.load.value),activation=float(self.activation.value),
            iteration=iteration,residual=norm)

    def solve(self,spec,initial):
        label=spec['label']; self.w.x.array[:]=initial; self.w.x.scatter_forward()
        self.load.value=spec['p']; self.activation.value=spec['Ta']; self.history=[]
        self.iterate_root=self.root/'iterates'/f'{self.name}_{label}'
        self.iterate_root.mkdir(parents=True,exist_ok=False)
        write_json(self.iterate_root/'factor_option_binding.json',self.factor_options)
        np.savez_compressed(self.iterate_root/'initial.npz',mixed_state=initial,load=spec['p'],activation=spec['Ta'])
        write_json(self.root/'progress.json',{'status':'unknown','mesh':self.name,**spec})
        print(f'{self.name} {label}: p={spec["p"]}, Ta={spec["Ta"]}',flush=True)
        started=time.monotonic(); self.problem.solve(); self.w.x.scatter_forward()
        residual=self.vector(self.residual_form)
        iterations=int(self.problem.solver.getIterationNumber())
        meta={'snes_reason':int(self.problem.solver.getConvergedReason()),'iterations':iterations,
            'history':self.history,'free_residual_norm':float(np.linalg.norm(residual[self.free_mixed])),
            'cavity_volume':float(fem.assemble_scalar(self.volume_form)),
            'active_energy':float(fem.assemble_scalar(self.active_energy_form)),
            'linear_solver':self.linear_solver_report(iterations),'elapsed_seconds':time.monotonic()-started}
        state={'u':self.w.x.array[self.vmap].reshape(-1,3).copy(),'pressure':self.w.x.array[self.pmap].copy(),
            'mixed_state':self.w.x.array.copy(),'initial_mixed':initial.copy(),
            'load':spec['p'],'activation':spec['Ta'],'force_residual':residual[self.vmap].reshape(-1,3),
            'weak_residual':residual[self.pmap]}
        state.update({k:np.asarray(expression.eval(self.domain,self.cell_ids)) for k,expression in self.expressions.items()})
        path=self.root/'raw'/f'{self.name}_state_{label}'
        np.savez_compressed(path.with_suffix('.npz'),**state); write_json(path.with_suffix('.json'),meta)
        audit=state_audit(self.mesh_data,state,meta,self.config)
        write_json(self.root/'raw'/f'{self.name}_audit_{label}.json',audit)
        print(f'  {audit["status"]}: dV={audit["volume_change"]:.7g}; max|J-1|={audit["max_abs_J_minus_one"]:.7g}',flush=True)
        if audit['status']!='passed':
            raise ValueError('Independent state gate failed: '+str(audit['failed_checks']))
        return self.w.x.array.copy()


def reuse_zero(solid,config,root):
    """Exercise the fixed real adapter without calling SNES or updating a state."""
    retained_mesh=load_arrays(root/'retained/M0_mesh.npz')
    retained=load_arrays(root/'retained/M0_state_zero.npz')
    metadata=json.loads((root/'retained/M0_state_zero.json').read_text())
    checks=restart_identity(solid.mesh_data,retained_mesh,retained,len(solid.w.x.array))
    report={'status':'failed','checks':checks,'new_equilibrium_solves':0,'newton_updates':0}
    write_json(root/'restart_interface.json',report)
    if not all(checks.values()):
        raise ValueError('Retained restart identity mismatch')
    solid.w.x.array[:]=retained['mixed_state']; solid.w.x.scatter_forward()
    solid.load.value=0.; solid.activation.value=0.
    residual=solid.vector(solid.residual_form)
    current={**retained,'u':solid.w.x.array[solid.vmap].reshape(-1,3).copy(),
        'pressure':solid.w.x.array[solid.pmap].copy(),
        'force_residual':residual[solid.vmap].reshape(-1,3),'weak_residual':residual[solid.pmap]}
    current.update({key:np.asarray(expression.eval(solid.domain,solid.cell_ids)) for key,expression in solid.expressions.items()})
    np.savez_compressed(root/'restart_interface_state.npz',**current)
    for key in ['u','pressure','F','J','stress','active_stress','force_residual','weak_residual']:
        checks['retained_'+key]=bool(np.allclose(current[key].ravel(),retained[key].ravel(),rtol=0,atol=1e-12))
    checks['native_pressure_flat']=current['pressure'].shape==(len(solid.mesh_data['pressure_coordinates']),)
    checks['mixed_vector_unchanged']=bool(np.array_equal(solid.w.x.array,retained['mixed_state']))
    audit=state_audit(solid.mesh_data,current,metadata,config)
    checks['independent_zero']=audit['status']=='passed'
    report.update(status='passed' if all(checks.values()) else 'failed',checks=checks,audit=audit)
    write_json(root/'restart_interface.json',report)
    if report['status']!='passed':
        raise ValueError('Native zero-state interface check failed')
    print('M0 retained-zero interface passed; zero SNES calls, no state update',flush=True)
    return retained['mixed_state'].copy()


def main():
    root=Path('/out'); config=json.loads((root/'configuration.json').read_text())
    (root/'raw').mkdir(exist_ok=False)
    start=time.monotonic(); current=None; attempted=0; accepted=0; spec=None
    try:
        for case in config['meshes']:
            current=VentricularSolid(case,config,root); current.tangent_checks(); states={}
            if config.get('reuse_m0_zero',False) and case['name']=='M0':
                states['zero']=reuse_zero(current,config,root)
            def before_solve(next_spec):
                nonlocal spec,attempted
                spec=next_spec
                if time.monotonic()-start>1680:
                    raise TimeoutError('Stop with 120 seconds state preservation reserve')
                attempted+=1
            def after_solve(accepted_spec):
                nonlocal accepted
                accepted+=1
            advance_case(current,config,states,before_solve,after_solve)
        report=verify(root); write_json(root/'verification.json',report)
        write_json(root/'solver_execution.json',{'status':report['status'],'attempted_states':attempted,
            'accepted_states':accepted,'elapsed_seconds':time.monotonic()-start,'dolfinx_version':dolfinx.__version__,
            'scientific_invocations':1,'automatic_retries':0})
        return 0 if report['status']=='passed' else 2
    except Exception as error:
        if current is not None:
            np.savez_compressed(root/'failure_state.npz',mixed_state=current.w.x.array.copy(),
                u=current.w.x.array[current.vmap].reshape(-1,3),pressure=current.w.x.array[current.pmap])
            write_json(root/'failure_history.json',current.history)
        write_json(root/'failure.json',{'status':'failed','reason':repr(error),'traceback':traceback.format_exc(),
            'mesh':current.name if current else None,'state':spec,'attempted_states':attempted,'accepted_states':accepted,
            'elapsed_seconds':time.monotonic()-start,'automatic_retries':0})
        traceback.print_exc()
        try:
            write_json(root/'verification.json',verify(root))
        except Exception as audit_error:
            write_json(root/'verification_failure.json',{'status':'failed','reason':repr(audit_error)})
        return 2


if __name__=='__main__':
    raise SystemExit(main())
