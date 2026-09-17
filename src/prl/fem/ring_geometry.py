"""Deterministic straight-sided three-layer annulus geometry, without a solver."""

import numpy as np


def configuration():
    return {
        'schema_version':'prl.fenicsx_ring.v1',
        'radii':[20/27,21/27,22/27,1.0],
        'meshes':[{'name':'M0','segments':64,'radial':[1,1,5]},
                  {'name':'M1','segments':128,'radial':[2,2,10]}],
        'mu':1.0,'kappa':1000.0,'quadrature_degree':6,
        'passive_loads':[0.0,.02,.04,.06,.08],
        'activation_steps':[0.0,.25,.5,.75,1.0],
        'active_peak':.10,'combined_pressure':.04,
        'solver':{'snes_type':'newtonls','snes_linesearch_type':'bt',
                  'snes_atol':1e-11,'snes_rtol':1e-10,'snes_stol':0.,'snes_max_it':30,
                  'ksp_type':'preonly','pc_type':'lu','pc_factor_mat_solver_type':'mumps'},
        'scope':'dimensionless plane-strain ring; uncalibrated; load continuation is not physiological time',
    }


def annulus(segments, radial, radii):
    levels = np.concatenate([np.linspace(radii[i],radii[i+1],radial[i]+1)[:-1]
                             for i in range(3)]+[np.array([radii[-1]])])
    angles = np.arange(segments)*2*np.pi/segments
    xy = (levels[:,None,None]*np.stack((np.cos(angles),np.sin(angles)),axis=-1)[None]).reshape(-1,2)
    triangles, labels = [], []
    layer_indices = np.repeat(np.arange(1,4), radial)
    for level, label in enumerate(layer_indices):
        for j in range(segments):
            k=(j+1)%segments
            a,b,c,d=level*segments+j,(level+1)*segments+j,(level+1)*segments+k,level*segments+k
            pair = [(a,b,c),(a,c,d)] if (j+level)%2==0 else [(a,b,d),(b,c,d)]
            triangles.extend(pair)
            labels.extend([label,label])
    return xy, np.array(triangles,dtype=np.int64), np.array(labels,dtype=np.int32)


def geometry_metrics(xy,cells,labels,segments,radii):
    points=xy[cells]
    sides=np.stack([points[:,1]-points[:,0],points[:,2]-points[:,1],points[:,0]-points[:,2]],axis=1)
    lengths=np.linalg.norm(sides,axis=-1)
    angles=[]
    for i in range(3):
        a,b,c=lengths[:,i],lengths[:,(i+1)%3],lengths[:,(i+2)%3]
        angles.append(np.arccos(np.clip((a*a+b*b-c*c)/(2*a*b),-1,1)))
    determinant=(points[:,1,0]-points[:,0,0])*(points[:,2,1]-points[:,0,1])-(points[:,1,1]-points[:,0,1])*(points[:,2,0]-points[:,0,0])
    area=determinant.sum()/2
    exact=np.pi*(radii[-1]**2-radii[0]**2)
    edges=np.sort(np.concatenate([cells[:,[0,1]],cells[:,[1,2]],cells[:,[2,0]]]),axis=1)
    _,counts=np.unique(edges,axis=0,return_counts=True)
    return {'cells':len(cells),'vertices':len(xy),'minimum_signed_area':float(determinant.min()/2),
            'minimum_angle_degrees':float(np.rad2deg(np.min(angles))),
            'ring_area':float(area),'circle_area_relative_error':float(abs(area/exact-1)),
            'boundary_edges':int(np.count_nonzero(counts==1)),
            'edge_manifold':bool(np.all(counts<=2)),
            'layer_counts':{str(i):int(np.count_nonzero(labels==i)) for i in [1,2,3]},
            'boundary_count_correct':bool(np.count_nonzero(counts==1)==2*segments)}
