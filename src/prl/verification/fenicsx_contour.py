"""Independent polygon/triangle and saved-state audit; no production FEM imports."""

import hashlib
import json
from pathlib import Path

import numpy as np
from scipy.spatial import cKDTree

from .fenicsx_ring import load_arrays,state_audit

SOURCE_SHA='e2f3ac0f68b523bddcc8e33e8a0ab057cf06116a43120653b90139894d06fa21'


def polygon_area(points):
    return float(np.sum(points[:,0]*np.roll(points[:,1],-1)-points[:,1]*np.roll(points[:,0],-1))/2)


def inside(points,polygon):
    result=np.zeros(len(points),dtype=bool)
    for a,b in zip(polygon,np.roll(polygon,-1,axis=0)):
        if b[1]==a[1]:
            continue
        result^=((a[1]>points[:,1])!=(b[1]>points[:,1])) & (points[:,0]<(b[0]-a[0])*(points[:,1]-a[1])/(b[1]-a[1])+a[0])
    return result


def geometry_audit(data,source):
    xy,tri,labels=[data[k] for k in ['xy','triangles','labels']]
    p=xy[tri]
    det=(p[:,1,0]-p[:,0,0])*(p[:,2,1]-p[:,0,1])-(p[:,1,1]-p[:,0,1])*(p[:,2,0]-p[:,0,0])
    angles=[]
    for i in range(3):
        a=p[:,(i+1)%3]-p[:,i]
        b=p[:,(i+2)%3]-p[:,i]
        angles.append(np.degrees(np.arccos(np.clip(np.sum(a*b,axis=1)/(np.linalg.norm(a,axis=1)*np.linalg.norm(b,axis=1)),-1,1))))
    edge_arrays=np.sort(np.concatenate([tri[:,[0,1]],tri[:,[1,2]],tri[:,[2,0]]]),axis=1)
    edges,counts=np.unique(edge_arrays,axis=0,return_counts=True)
    edge_count={tuple(e):int(c) for e,c in zip(edges,counts)}
    edge_layers={}
    for cell,label in zip(tri,labels):
        for a,b in zip(cell,np.roll(cell,-1)):
            edge_layers.setdefault(tuple(sorted((int(a),int(b)))),[]).append(int(label))
    checks={'positive_reference':bool(np.min(det)>0),'minimum_angle':bool(np.min(angles)>=20),
            'edge_manifold':bool(np.all(counts<=2)), 'all_vertices_used':len(np.unique(tri))==len(xy),
            'labels':set(labels.tolist())=={1,2,3}}
    loop_areas=[]
    declared_boundary=set()
    for key,expected in [('inner_nodes',[1]),('interface1_nodes',[1,2]),('interface2_nodes',[2,3]),('outer_nodes',[3])]:
        nodes=data[key]
        loop=xy[nodes]
        loop_areas.append(polygon_area(loop))
        loop_edges={tuple(sorted((int(a),int(b)))) for a,b in zip(nodes,np.roll(nodes,-1))}
        checks[key+'_connectivity']=len(np.unique(nodes))==len(nodes) and all(sorted(edge_layers.get(e,[]))==expected for e in loop_edges)
        if len(expected)==1:
            declared_boundary|=loop_edges
        checks[key+'_star_oriented']=bool(np.all(loop[:,0]*np.roll(loop[:,1],-1)-loop[:,1]*np.roll(loop[:,0],-1)>0))
    checks['boundary_complete']={e for e,c in edge_count.items() if c==1}==declared_boundary
    loop_areas=np.asarray(loop_areas)
    layer_areas=np.array([det[labels==i].sum()/2 for i in [1,2,3]])
    checks['layer_area']=bool(np.max(np.abs(layer_areas/np.diff(loop_areas)-1))<=1e-12)
    checks['homothetic_areas']=bool(np.max(np.abs(loop_areas/loop_areas[-1]-np.array([20/27,21/27,22/27,1.])**2))<1e-12)
    # Reconstruct the source resampling and the coordinate frame independently.
    curve=source['smooth_contour_um']
    closed=np.vstack((curve,curve[0]))
    distance=np.r_[0.,np.cumsum(np.linalg.norm(np.diff(closed,axis=0),axis=1))]
    samples=np.column_stack([np.interp(np.arange(128)*distance[-1]/128,distance,closed[:,i]) for i in range(2)])
    vector=samples[64]-samples[0]
    vector/=np.linalg.norm(vector)
    rotation=np.array([[vector[0],vector[1]],[-vector[1],vector[0]]])
    expected=(samples-source['center_um'])@rotation.T/float(source['length_scale_um'])
    checks['source_polygon']=bool(np.max(np.abs(data['polygon']-expected))<1e-12)
    checks['gauge_points']=bool(np.max(np.abs(data['anchors']-expected[[0,64]]))<1e-12)
    outer=xy[data['outer_nodes']]@rotation*float(source['length_scale_um'])+source['center_um']
    # Require every actual straight boundary node on the frozen polygon, not just area agreement.
    maximum=0.
    for point in outer:
        a=samples
        d=np.roll(samples,-1,axis=0)-samples
        t=np.clip(np.sum((point-a)*d,axis=1)/np.sum(d*d,axis=1),0,1)
        maximum=max(maximum,float(np.min(np.linalg.norm(point-a-t[:,None]*d,axis=1))))
    checks['boundary_on_frozen_polygon']=maximum<=1e-9
    mask=source['slice_mask'].astype(bool)
    row,col=np.indices(mask.shape)
    raster=inside(np.column_stack((col.ravel(),row.ravel()))*source['voxel_um'][0],outer).reshape(mask.shape)
    iou=float(np.count_nonzero(raster&mask)/np.count_nonzero(raster|mask))
    dense=[]
    for a,b in zip(outer,np.roll(outer,-1,axis=0)):
        dense.extend(a+(b-a)*np.arange(max(1,int(np.ceil(np.linalg.norm(b-a)/.1))))[:,None]/max(1,int(np.ceil(np.linalg.norm(b-a)/.1))))
    dense=np.asarray(dense)
    raw=source['raw_contour_um']
    hausdorff=float(max(cKDTree(raw).query(dense)[0].max(),cKDTree(dense).query(raw)[0].max()))
    checks['source_fidelity']=iou>=.98 and hausdorff<=2.
    return {'status':'passed' if all(checks.values()) else 'failed','checks':checks,
            'failed_checks':[k for k,v in checks.items() if not v],'cells':len(tri),'vertices':len(xy),
            'minimum_angle_degrees':float(np.min(angles)),'minimum_signed_area':float(det.min()/2),
            'source_mask_iou':iou,'raw_contour_hausdorff_um':hausdorff,
            'reference_cavity_area':float(loop_areas[0]),'reference_wall_area':float(layer_areas.sum()),
            'layer_areas':layer_areas.tolist()}


def verify_contour(root,save=False):
    root=Path(root)
    cfg=json.loads((root/'configuration.json').read_text())
    source=load_arrays(root/'geometry_source.npz')
    checks={'source_hash':hashlib.sha256((root/'geometry_source.npz').read_bytes()).hexdigest()==SOURCE_SHA,
            'frozen_physics':cfg['mu']==1. and cfg['kappa']==1000. and cfg['passive_loads']==[0.,.02,.04,.06,.08] and cfg['geometry_kind']=='image_polygon'}
    if 'retained_mesh' in cfg:
        checks['retained_mesh_identity']=hashlib.sha256((root/'retained_mesh.npz').read_bytes()).hexdigest()=='157265c350367a95f36c40c5951117272ceeccac9f273ec65e5000eb81627f65'
        original=load_arrays(root/'retained_mesh.npz')
        actual=load_arrays(root/'raw/M0_input_mesh.npz')
        checks['retained_mesh_arrays']=set(original)==set(actual) and all(np.array_equal(original[k],actual[k]) for k in original)
    cases={}
    geometry={}
    for name in ['M0','M1']:
        path=root/'raw'/f'{name}_input_mesh.npz'
        if not path.exists():
            checks[name+'_geometry']=False
            continue
        geom=geometry_audit(load_arrays(path),source)
        geometry[name]=geom
        checks[name+'_geometry']=geom['status']=='passed'
        mesh_path=root/'raw'/f'{name}_mesh.npz'
        if not mesh_path.exists():
            checks[name+'_states_complete']=False
            continue
        mesh=load_arrays(mesh_path)
        positions=mesh['coordinates'][mesh['cells']]
        mids=np.stack(((positions[:,1]+positions[:,2])/2,(positions[:,0]+positions[:,2])/2,(positions[:,0]+positions[:,1])/2),axis=1)
        checks[name+'_P2P1_mapping']=bool(np.max(np.abs(positions[:,3:]-mids))<1e-12 and np.max(np.abs(mesh['pressure_coordinates'][mesh['pressure_cells']]-positions[:,:3]))<1e-12)
        tangent=json.loads((root/'raw'/f'{name}_tangent.json').read_text())
        checks[name+'_tangent']=all(tangent[k]<=v for k,v in [('pressure',2e-6),('active',2e-6),('total',2e-5)])
        previous=None
        records={}
        for i,p in enumerate([0.,.02,.04,.06,.08]):
            path=root/'raw'/f'{name}_state_passive_{i}.npz'
            if not path.exists():
                break
            state=load_arrays(path)
            metadata=json.loads(path.with_suffix('.json').read_text())
            record=state_audit(mesh,state,metadata,cfg)
            records[f'passive_{i}']=record
            checks[f'{name}_state_{i}']=record['status']=='passed'
            checks[f'{name}_load_{i}']=float(state['load'])==p and float(state['activation'])==0.
            expected=np.zeros_like(state['mixed_state']) if previous is None else previous
            checks[f'{name}_chain_{i}']=bool(np.array_equal(state['initial_mixed'],expected))
            previous=state['mixed_state']
            if i==0:
                checks[name+'_zero_stress']=bool(np.max(np.abs(state['stress']))<=2e-7)
        cases[name]=records
        checks[name+'_states_complete']=len(records)==5
        checks[name+'_monotone']=len(records)==5 and bool(np.all(np.diff([r['cavity_area'] for r in records.values()])>0))
        checks[name+'_response']=records.get('passive_4',{}).get('cavity_area_change',0)>=.01
    comparison={}
    if len(geometry)==2:
        checks['same_reference_domain']=abs(geometry['M0']['reference_wall_area']/geometry['M1']['reference_wall_area']-1)<1e-12
    if all('passive_4' in cases.get(n,{}) for n in ['M0','M1']):
        a,b=[cases[n]['passive_4']['cavity_area_change'] for n in ['M0','M1']]
        comparison={'absolute':abs(a-b),'relative':abs(a-b)/max(abs(a),abs(b),1e-15)}
    checks['mesh_response']=bool(comparison and comparison['absolute']<=.002 and comparison['relative']<=.05)
    report={'status':'passed' if all(checks.values()) else 'failed','checks':checks,'failed_checks':[k for k,v in checks.items() if not v],
            'cases':cases,'geometry':geometry,'mesh_comparison':comparison,'active_contraction':'not_run','biological_validation':'not_run'}
    if save:
        (root/'verification.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    return report


def diagnose_local_volume(root,save=False):
    """Saved-state localization only; weak constraint is not a pointwise bound."""
    from .fenicsx_ring import fields
    root=Path(root)
    mesh=load_arrays(root/'raw/M0_mesh.npz')
    state=load_arrays(root/'raw/M0_state_passive_1.npz')
    values=fields(mesh,state)
    deviation=np.abs(values['J']-1)
    worst=np.unravel_index(np.argmax(deviation),deviation.shape)
    bary=np.column_stack((1-mesh['qpoints'].sum(axis=1),mesh['qpoints']))
    pressure=np.einsum('qa,ca->cq',bary,state['pressure'][mesh['pressure_cells']])
    position=np.einsum('qa,cai->cqi',bary,mesh['coordinates'][mesh['cells'][:,:3]])
    report={'status':'passed','scientific_gate':'failed','scientific_solves':0,
            'max_abs_J_minus_one':float(deviation.max()),'worst_cell':int(worst[0]),'worst_quadrature_point':int(worst[1]),
            'worst_reference_xy':position[worst].tolist(),'worst_layer':int(mesh['layers'][worst[0]]),
            'reference_volume_fraction_above_one_percent':float(np.sum(values['weights']*(deviation>.01))/values['weights'].sum()),
            'pointwise_mixed_constraint_max':float(np.max(np.abs(values['J']-1-pressure/1000))),
            'max_abs_pressure_over_kappa':float(np.max(np.abs(pressure/1000))),
            'max_displacement_over_L':float(np.linalg.norm(state['u'],axis=1).max()),
            'layers':{str(i):{'cells':int(np.sum(mesh['layers']==i)),
               'failed_cells':int(np.sum(np.max(deviation[mesh['layers']==i],axis=1)>.01)),
               'max_abs_J_minus_one':float(deviation[mesh['layers']==i].max())} for i in [1,2,3]},
            'interpretation':'Weak P1 pressure residual can vanish while pointwise volume constraint is unresolved. Spatial discretization sensitivity is a hypothesis; fine-mesh mechanics is not_run.'}
    if save:
        (root/'local_volume_diagnosis.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    return report


def verify_mesh_repair(root,save=False):
    """Independently re-read the bounded pre-solve mesh experiment."""
    root=Path(root)
    source=load_arrays(root/'geometry_source.npz')
    cfg=json.loads((root/'configuration.json').read_text())
    records=json.loads((root/'mesh_candidates.json').read_text())
    failure=json.loads((root/'failure.json').read_text())
    checks={'source_hash':hashlib.sha256((root/'geometry_source.npz').read_bytes()).hexdigest()==SOURCE_SHA,
            'declared_candidates':cfg['mesh_size_candidates']==[1.2,.9,.7],
            'all_candidates_retained':len(records)==3,
            'no_equilibrium_attempt':failure['attempted_states']==0 and failure['completed_states']==0,
            'no_state_files':not any((root/'raw').glob('*state*.npz')),
            'frozen_physics':cfg['mu']==1. and cfg['kappa']==1000. and cfg['passive_loads']==[0.,.02,.04,.06,.08]}
    results=[]
    for i,record in enumerate(records):
        mesh=load_arrays(root/'raw'/f'candidate_{i}_mesh.npz')
        audit=geometry_audit(mesh,source)
        prediction=76800*len(mesh['triangles'])+50331648
        checks[f'candidate_{i}_geometry']=audit['status']=='passed'
        checks[f'candidate_{i}_record']=audit==record['geometry'] and record['factor']==[1.2,.9,.7][i]
        checks[f'candidate_{i}_budget']=prediction==record['predicted_bytes'] and prediction>256*1024**2 and not record['storage_passed']
        results.append({'factor':record['factor'],'geometry':audit,'predicted_bytes':prediction})
    report={'status':'passed' if all(checks.values()) else 'failed','checks':checks,
            'geometry_status':'passed' if all(r['geometry']['status']=='passed' for r in results) else 'failed',
            'storage_admission':'blocked','passive_mechanics':'not_run','active_mechanics':'not_run',
            'biological_validation':'not_run','equilibrium_solves':0,'candidates':results}
    if save:
        (root/'verification.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    return report
