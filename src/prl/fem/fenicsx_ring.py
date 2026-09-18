"""FEniCSx adapter for the frozen F6-S0 model; only executed in the pinned image."""

from __future__ import annotations

import json
from pathlib import Path
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

from prl.fem.ring_geometry import annulus, geometry_metrics
from prl.verification.fenicsx_ring import verify_fenicsx_ring


def write_json(path,data):
    Path(path).write_text(json.dumps(data,indent=2,allow_nan=False)+'\n',encoding='utf-8')


def budget(root,started):
    size=sum(p.stat().st_size for p in root.rglob('*') if p.is_file())
    if size>120*1024**2:
        raise RuntimeError('128 MiB stage cap: stop with 8 MiB control headroom')
    if time.monotonic()-started>1140:
        raise RuntimeError('1200 second deadline: stop with 60 second state retention headroom')


class Ring:
    def __init__(self,case,config,root,geometry_input=None):
        self.name=case['name']
        self.config=config
        self.root=root
        if geometry_input is None:
            xy,cells,labels=annulus(case['segments'],case['radial'],config['radii'])
            gm=geometry_metrics(xy,cells,labels,case['segments'],config['radii'])
            geometry_ok=(gm['minimum_signed_area']>0 and gm['minimum_angle_degrees']>=20 and gm['edge_manifold'] and gm['boundary_count_correct'] and gm['circle_area_relative_error']<=(.002 if self.name=='M0' else .0005))
            angles=np.arange(case['segments'])*2*np.pi/case['segments']
            inner_vertices=config['radii'][0]*np.column_stack((np.cos(angles),np.sin(angles)))
            anchors=np.array([[1.,0.],[-1.,0.]])
        else:
            xy,cells,labels=[geometry_input[k] for k in ['xy','triangles','labels']]
            gm=geometry_input['metrics']
            geometry_ok=gm['status']=='passed'
            inner_vertices=xy[geometry_input['inner_nodes']]
            anchors=geometry_input['anchors']
        write_json(root/'raw'/f'{self.name}_geometry.json',gm)
        if not geometry_ok:
            raise ValueError('Frozen reference geometry gate failed')
        coordinate_element=basix.ufl.element('Lagrange','triangle',1,shape=(2,))
        self.domain=domain=mesh.create_mesh(MPI.COMM_WORLD,cells,coordinate_element,xy)
        self.count=domain.topology.index_map(2).size_local
        assert MPI.COMM_WORLD.size==1 and self.count==len(cells)
        self.cell_ids=np.arange(self.count,dtype=np.int32)
        self.layers=labels[domain.topology.original_cell_index]
        cell_tags=mesh.meshtags(domain,2,self.cell_ids,self.layers)
        domain.topology.create_connectivity(1,2)
        exterior=mesh.exterior_facet_indices(domain.topology)
        midpoints=mesh.compute_midpoints(domain,1,exterior)
        from scipy.spatial import cKDTree
        inner_midpoints=(inner_vertices+np.roll(inner_vertices,-1,axis=0))/2
        distance,_=cKDTree(inner_midpoints).query(midpoints[:,:2])
        inner=exterior[distance<1e-12]
        assert len(inner)==len(inner_vertices)
        facet_tags=mesh.meshtags(domain,1,np.sort(inner),np.ones(len(inner),dtype=np.int32))
        displacement_element=basix.ufl.element('Lagrange','triangle',2,shape=(2,))
        pressure_space=config.get('pressure_space','CG1')
        if pressure_space not in {'CG1','DG2'}:
            raise ValueError('Only frozen CG1 or explicitly selected finite-bulk DG2 pressure is supported')
        if pressure_space=='DG2' and (not np.isfinite(config['kappa']) or config['kappa']<=0):
            raise ValueError('DG2 diagnostic requires positive finite bulk modulus; not an incompressible-limit pair')
        pressure_element=basix.ufl.element('Lagrange','triangle',2,discontinuous=True) if pressure_space=='DG2' else basix.ufl.element('Lagrange','triangle',1)
        self.space=fem.functionspace(domain,basix.ufl.mixed_element([displacement_element,pressure_element]))
        self.w=fem.Function(self.space)
        self.vspace,self.vmap=self.space.sub(0).collapse()
        self.pspace,self.pmap=self.space.sub(1).collapse()
        self.coords=self.vspace.tabulate_dof_coordinates()[:,:2]
        self.cells=np.array([self.vspace.dofmap.cell_dofs(c) for c in self.cell_ids])
        self.pcells=np.array([self.pspace.dofmap.cell_dofs(c) for c in self.cell_ids])
        self.vmap=np.asarray(self.vmap,dtype=np.int32).reshape(-1)
        self.pmap=np.asarray(self.pmap,dtype=np.int32).reshape(-1)
        self.fixed=np.zeros(self.coords.shape,dtype=bool)
        node_a=int(np.argmin(np.linalg.norm(self.coords-anchors[0],axis=1)))
        node_b=int(np.argmin(np.linalg.norm(self.coords-anchors[1],axis=1)))
        assert np.linalg.norm(self.coords[node_a]-anchors[0])<1e-12
        assert np.linalg.norm(self.coords[node_b]-anchors[1])<1e-12
        self.fixed[node_a,:]=True
        self.fixed[node_b,1]=True
        map2=self.vmap.reshape(-1,2)
        bcs=[fem.dirichletbc(PETSc.ScalarType(0),np.array([map2[node_a,0]],dtype=np.int32),self.space.sub(0).sub(0)),
             fem.dirichletbc(PETSc.ScalarType(0),np.array([map2[node_a,1],map2[node_b,1]],dtype=np.int32),self.space.sub(0).sub(1))]
        self.fixed_mixed=map2[self.fixed]
        self.free_mixed=np.ones(len(self.w.x.array),dtype=bool)
        self.free_mixed[self.fixed_mixed]=False
        u,pm=ufl.split(self.w)
        self.load=fem.Constant(domain,PETSc.ScalarType(0))
        self.activation=fem.Constant(domain,PETSc.ScalarType(0))
        f2=ufl.Identity(2)+ufl.grad(u)
        f=ufl.variable(ufl.as_tensor(((f2[0,0],f2[0,1],0.),(f2[1,0],f2[1,1],0.),(0.,0.,1.))))
        j=ufl.det(f)
        x=ufl.SpatialCoordinate(domain)
        fiber=ufl.as_vector((-x[1],x[0],0))/ufl.sqrt(x[0]**2+x[1]**2)
        mu,kappa=config['mu'],config['kappa']
        passive=mu/2*(j**(-2/3)*ufl.inner(f,f)-3)+pm*(j-1)-pm**2/(2*kappa)
        active=self.activation/2*(ufl.inner(f*fiber,f*fiber)-1)
        dx=ufl.Measure('dx',domain=domain,subdomain_data=cell_tags,metadata={'quadrature_degree':6})
        ds=ufl.Measure('ds',domain=domain,subdomain_data=facet_tags,metadata={'quadrature_degree':6})
        normal=ufl.FacetNormal(domain)
        cavity_area=-.5*ufl.dot(x+u,ufl.cofac(f2)*normal)*ds(1)
        passive_energy=passive*dx
        active_energy=active*dx(3)
        pressure_energy=-self.load*cavity_area
        test=ufl.TestFunction(self.space)
        residual=ufl.derivative(passive_energy+active_energy+pressure_energy,self.w,test)
        self.residual_form=fem.form(residual)
        self.parts={'pressure':ufl.derivative(pressure_energy,self.w,test),
                    'active':ufl.derivative(active_energy,self.w,test),'total':residual}
        self.area_form=fem.form(cavity_area)
        self.active_energy_form=fem.form(active_energy)
        self.problem=petsc.NonlinearProblem(residual,self.w,bcs=bcs,petsc_options_prefix=self.name+'_',
                        petsc_options=config['solver'])
        chi_space=fem.functionspace(domain,('DG',0))
        chi=fem.Function(chi_space)
        for c in self.cell_ids:
            chi.x.array[chi_space.dofmap.cell_dofs(c)]=float(self.layers[c]==3)
        passive_piola=ufl.diff(passive,f)
        active_piola=chi*ufl.diff(active,f)
        sigma=(passive_piola+active_piola)*f.T/j
        active_sigma=active_piola*f.T/j
        self.qpoints,self.qweights=basix.make_quadrature(basix.CellType.triangle,6)
        self.expressions={k:fem.Expression(value,self.qpoints) for k,value in
                          {'F':f,'J':j,'stress':sigma,'active_stress':active_sigma}.items()}
        self.inner_edges=[]
        for n in range(len(inner_vertices)):
            endpoints=inner_vertices[[n,(n+1)%len(inner_vertices)]]
            targets=[endpoints[0],endpoints.mean(axis=0),endpoints[1]]
            indices=[]
            for target in targets:
                index=int(np.argmin(np.linalg.norm(self.coords-target,axis=1)))
                assert np.linalg.norm(self.coords[index]-target)<1e-12
                indices.append(index)
            self.inner_edges.append(indices)
        self.mesh_data={'coordinates':self.coords,'cells':self.cells,'layers':self.layers,
                       'pressure_coordinates':self.pspace.tabulate_dof_coordinates()[:,:2],
                       'pressure_cells':self.pcells,'inner_edges':np.array(self.inner_edges),
                       'fixed':self.fixed,'qpoints':self.qpoints,'qweights':self.qweights,
                       'mixed_u_map':self.vmap,'mixed_p_map':self.pmap}
        if pressure_space=='DG2':
            self.mesh_data['pressure_space']=np.array('DG2')
        np.savez_compressed(root/'raw'/f'{self.name}_mesh.npz',**self.mesh_data)
        self.history=[]
        self.problem.solver.setMonitor(lambda solver,iteration,norm:self.history.append({'iteration':int(iteration),'residual':float(norm)}))

    def vector(self,form):
        vector=petsc.assemble_vector(form)
        vector.ghostUpdate(addv=PETSc.InsertMode.ADD,mode=PETSc.ScatterMode.REVERSE)
        result=vector.array.copy()
        vector.destroy()
        return result

    def tangent_checks(self):
        saved=self.w.x.array.copy()
        self.load.value=.04
        self.activation.value=.10
        rng=np.random.default_rng(7301)
        direction=rng.normal(size=saved.size)*.01
        direction[self.fixed_mixed]=0
        trial=ufl.TrialFunction(self.space)
        results={}
        for key,part in self.parts.items():
            form=fem.form(part)
            tangent=petsc.assemble_matrix(fem.form(ufl.derivative(part,self.w,trial)))
            tangent.assemble()
            vector=PETSc.Vec().createWithArray(direction,comm=MPI.COMM_WORLD)
            product=tangent.createVecLeft()
            tangent.mult(vector,product)
            exact=product.array.copy()
            h=1e-6
            self.w.x.array[:]=saved+h*direction
            forward=self.vector(form)
            self.w.x.array[:]=saved-h*direction
            backward=self.vector(form)
            self.w.x.array[:]=saved
            difference=(forward-backward)/(2*h)
            results[key]=float(np.linalg.norm(difference-exact)/max(np.linalg.norm(exact),np.linalg.norm(difference),1e-12))
            vector.destroy()
            product.destroy()
            tangent.destroy()
        self.load.value=0.
        self.activation.value=0.
        write_json(self.root/'raw'/f'{self.name}_tangent.json',results)
        if not all(results[k]<=v for k,v in [('pressure',2e-6),('active',2e-6),('total',2e-5)]):
            raise ValueError('Jacobian directional check failed: '+str(results))

    def solve(self,label,pressure,activation,initial):
        self.w.x.array[:]=initial
        self.w.x.scatter_forward()
        self.load.value=pressure
        self.activation.value=activation
        self.history=[]
        np.savez_compressed(self.root/'raw'/f'{self.name}_attempt.npz',initial=initial,load=pressure,activation=activation)
        write_json(self.root/'progress.json',{'status':'unknown','mesh':self.name,'state':label,'load':pressure,'activation':activation})
        print(f'{self.name} {label}: p={pressure:.3f} Ta={activation:.3f}',flush=True)
        started=time.monotonic()
        self.problem.solve()
        self.w.x.scatter_forward()
        reason=int(self.problem.solver.getConvergedReason())
        residual=self.vector(self.residual_form)
        metadata={'snes_reason':reason,'iterations':int(self.problem.solver.getIterationNumber()),
                  'history':self.history,'free_residual_norm':float(np.linalg.norm(residual[self.free_mixed])),
                  'cavity_area':float(fem.assemble_scalar(self.area_form)),
                  'active_energy':float(fem.assemble_scalar(self.active_energy_form)),
                  'elapsed_seconds':time.monotonic()-started}
        state={'u':self.w.x.array[self.vmap].reshape(-1,2).copy(),
               'pressure':self.w.x.array[self.pmap].copy(),
               'mixed_state':self.w.x.array.copy(),'initial_mixed':initial.copy(),
               'load':pressure,'activation':activation,
               'force_residual':residual[self.vmap].reshape(-1,2),
               'weak_residual':residual[self.pmap]}
        for key,expression in self.expressions.items():
            state[key]=np.asarray(expression.eval(self.domain,self.cell_ids))
        path=self.root/'raw'/f'{self.name}_state_{label}'
        np.savez_compressed(path.with_suffix('.npz'),**state)
        write_json(path.with_suffix('.json'),metadata)
        if reason<=0 or metadata['free_residual_norm']>1e-9 or not all(np.all(np.isfinite(v)) for v in state.values()):
            raise ValueError('SNES failed or invalid state: '+str(metadata))
        if np.min(state['J'])<=0:
            raise ValueError('Nonpositive J in saved state')
        return self.w.x.array.copy()


def main():
    root=Path('/out')
    config=json.loads((root/'configuration.json').read_text())
    started=time.monotonic()
    count=0
    current=None
    (root/'raw').mkdir(exist_ok=False)
    try:
        rings=[]
        for case in config['meshes']:
            budget(root,started)
            current=Ring(case,config,root)
            current.tangent_checks()
            rings.append(current)
        parent_root=Path('/workspace')/config['parent_result'] if config.get('parent_result') else root
        if parent_root==root:
            for ring in rings:
                current=ring
                initial=np.zeros_like(ring.w.x.array)
                for i,p in enumerate(config['passive_loads']):
                    budget(root,started)
                    count+=1
                    initial=ring.solve(f'passive_{i}',p,0.,initial)
        gate=verify_fenicsx_ring(root,stage='passive',save=True,parent_root=parent_root)
        print('G1: '+gate['status']+' '+str(gate['failed_checks']),flush=True)
        if gate['status']!='passed':
            write_json(root/'solver_execution.json',{'status':'failed','G1':'failed','G2':'not_run','completed_states':count,'reason':'independent passive gate','elapsed_seconds':time.monotonic()-started})
            return 2
        for ring in rings:
            current=ring
            for label,pmax in [('active',0.),('combined',config['combined_pressure'])]:
                with np.load(parent_root/'raw'/f'{ring.name}_state_passive_0.npz',allow_pickle=False) as saved:
                    initial=saved['mixed_state'].copy()
                for i,step in enumerate(config['activation_steps'][1:],1):
                    budget(root,started)
                    count+=1
                    initial=ring.solve(f'{label}_{i}',pmax*step,config['active_peak']*step,initial)
        verification=verify_fenicsx_ring(root,save=True,parent_root=parent_root)
        write_json(root/'solver_execution.json',{'status':verification['status'],'G1':'passed','G2':verification['status'],
                    'completed_states':count,'scientific_invocations':1,'automatic_retries':0,
                    'elapsed_seconds':time.monotonic()-started,'dolfinx_version':dolfinx.__version__})
        return 0 if verification['status']=='passed' else 2
    except Exception as error:
        if current is not None:
            np.savez_compressed(root/'failure_state.npz',mixed_state=current.w.x.array,
                                displacement=current.w.x.array[current.vmap].reshape(-1,2),
                                pressure=current.w.x.array[current.pmap])
            write_json(root/'failure_history.json',current.history)
        write_json(root/'failure.json',{'status':'failed','reason':repr(error),'traceback':traceback.format_exc(),
                    'attempted_states':count,'elapsed_seconds':time.monotonic()-started,'automatic_retries':0})
        traceback.print_exc()
        return 2


if __name__=='__main__':
    raise SystemExit(main())
