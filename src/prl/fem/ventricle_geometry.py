"""Deterministic, conforming tetrahedra for an idealized half-ellipsoidal wall."""
from collections import Counter
import numpy as np


def configuration():
    return {
        'schema_version':'prl.idealized_3d.v1', 'mu':1., 'kappa':1000.,
        'axes':[1.,1.,1.5], 'radii':[20/27,21/27,22/27,1.],
        'meshes':[{'name':'M0','segments':16,'bands':4,'radial':[1,1,2]},
                  {'name':'M1','segments':24,'bands':6,'radial':[1,1,3]}],
        'states':[{'label':'zero','p':0.,'Ta':0.,'initial':None},
                  {'label':'pressure_1','p':.01,'Ta':0.,'initial':'zero'},
                  {'label':'pressure_2','p':.02,'Ta':0.,'initial':'pressure_1'},
                  {'label':'active_1','p':0.,'Ta':.05,'initial':'zero'},
                  {'label':'active_2','p':0.,'Ta':.1,'initial':'active_1'},
                  {'label':'combined_1','p':.02,'Ta':.05,'initial':'pressure_2'},
                  {'label':'combined_2','p':.02,'Ta':.1,'initial':'combined_1'}],
        'solver':{'snes_type':'newtonls','snes_linesearch_type':'bt','snes_atol':1e-11,
                  'snes_rtol':1e-10,'snes_stol':0.,'snes_max_it':30,'ksp_type':'preonly',
                  'pc_type':'lu','pc_factor_mat_solver_type':'mumps','mat_mumps_icntl_14':100},
        'quadrature_degree':6, 'retain_solver_iterates':True, 'diagnostic_trace':True,
        'maximum_equilibrium_solves':14,'resources':{'seconds':1800,'threads':1,'gpu':0,'automatic_retries':0},
        'active_rule':'A=(I-n0*n0)/2; equal tangent-plane dispersion, not measured fibers',
        'scope':'idealized 3D solid; uncalibrated; no flow/growth/physiological clock',
    }


def half_ellipsoid(case, config):
    segments,bands=case['segments'],case['bands']
    theta=np.arange(segments)*2*np.pi/segments
    surface=[]
    for band in range(bands):
        phi=np.pi/2+band*np.pi/(2*bands)
        surface.extend(np.column_stack((np.sin(phi)*np.cos(theta),
                                        np.sin(phi)*np.sin(theta),
                                        np.full(segments,np.cos(phi)))))
    surface.append([0.,0.,-1.])
    surface=np.asarray(surface)*np.asarray(config['axes'])
    surface[:segments,2]=0.
    triangles=[]
    for band in range(bands-1):
        for i in range(segments):
            a=band*segments+i; b=band*segments+(i+1)%segments
            c=a+segments; d=b+segments
            triangles.extend([[a,c,d],[a,d,b]])
    apex=len(surface)-1
    for i in range(segments):
        triangles.append([(bands-1)*segments+i,apex,(bands-1)*segments+(i+1)%segments])
    triangles=np.asarray(triangles,dtype=np.int32)
    scales=[config['radii'][0]]; interval_labels=[]
    for layer,count in enumerate(case['radial']):
        scales.extend(np.linspace(config['radii'][layer],config['radii'][layer+1],count+1)[1:])
        interval_labels.extend([layer+1]*count)
    size=len(surface); xyz=np.concatenate([s*surface for s in scales])
    tetra=[]; labels=[]
    for interval,layer in enumerate(interval_labels):
        for face in triangles:
            a,b,c=np.sort(face)+interval*size
            tetra.extend([[a,b,c,c+size],[a,b,b+size,c+size],[a,a+size,b+size,c+size]])
            labels.extend([layer]*3)
    tetra=np.asarray(tetra,dtype=np.int64)
    local=xyz[tetra]
    signed=np.linalg.det(np.stack((local[:,1]-local[:,0],local[:,2]-local[:,0],local[:,3]-local[:,0]),axis=-1))
    flipped=signed<0
    tetra[flipped,1],tetra[flipped,2]=tetra[flipped,2].copy(),tetra[flipped,1].copy()
    inner=triangles.copy()
    # Orient inner faces away from the cavity (towards solid), for dVc/du.
    v=xyz[inner]
    inward=np.einsum('fi,fi->f',np.cross(v[:,1]-v[:,0],v[:,2]-v[:,0]),v.mean(axis=1))<0
    inner[inward,1],inner[inward,2]=inner[inward,2].copy(),inner[inward,1].copy()
    return {'xyz':xyz,'tetrahedra':tetra,'layers':np.asarray(labels,dtype=np.int32),
            'inner_faces':inner,'outer_faces':inner+(len(scales)-1)*size}


def geometry_metrics(data,config,name):
    xyz,tet=data['xyz'],data['tetrahedra']; v=xyz[tet]
    determinant=np.linalg.det(np.stack((v[:,1]-v[:,0],v[:,2]-v[:,0],v[:,3]-v[:,0]),axis=-1))
    faces=Counter(tuple(sorted(face)) for cell in tet for face in
                  [cell[[1,2,3]],cell[[0,2,3]],cell[[0,1,3]],cell[[0,1,2]]])
    exterior={face for face,count in faces.items() if count==1}
    prescribed={tuple(sorted(f)) for key in ['inner_faces','outer_faces'] for f in data[key]}
    base={face for face in exterior if np.all(np.abs(xyz[list(face),2])<1e-12)}
    inner=xyz[data['inner_faces']]
    cavity=float(np.einsum('fi,fi->',inner[:,0],np.cross(inner[:,1],inner[:,2]))/6)
    exact=2*np.pi/3*np.prod(config['axes'])*config['radii'][0]**3
    checks={'positive_tetrahedra':bool(determinant.min()>0),
            'no_duplicate_cells':len({tuple(sorted(t)) for t in tet})==len(tet),
            'manifold_faces':max(faces.values())==2,
            'all_boundaries_identified':exterior==prescribed|base,
            'three_layers_positive':all(float(determinant[data['layers']==k].sum())>0 for k in [1,2,3]),
            'cavity_geometry_error':bool(abs(cavity/exact-1)<=(.08 if name=='M0' else .04))}
    return {'status':'passed' if all(checks.values()) else 'failed','checks':checks,
            'vertices':len(xyz),'tetrahedra':len(tet),'inner_facets':len(data['inner_faces']),
            'outer_facets':len(data['outer_faces']),'base_facets':len(base),
            'minimum_reference_volume':float(determinant.min()/6),'cavity_reference_volume':cavity,
            'analytic_reference_volume':float(exact),'relative_cavity_geometry_error':float(abs(cavity/exact-1))}
