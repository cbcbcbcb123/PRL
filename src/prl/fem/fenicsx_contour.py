"""Image polygon meshing and passive FEniCSx adaptation in the pinned image."""

from pathlib import Path
import json
import hashlib
import time
import traceback

import numpy as np


def outline(source, count=128):
    points=source['smooth_contour_um']
    closed=np.vstack((points,points[0]))
    arclength=np.r_[0.,np.cumsum(np.linalg.norm(np.diff(closed,axis=0),axis=1))]
    query=np.arange(count)*arclength[-1]/count
    sampled=np.column_stack([np.interp(query,arclength,closed[:,i]) for i in range(2)])
    normalized=(sampled-source['center_um'])/float(source['length_scale_um'])
    direction=normalized[count//2]-normalized[0]
    direction/=np.linalg.norm(direction)
    rotation=np.array([[direction[0],direction[1]],[-direction[1],direction[0]]])
    return normalized@rotation.T,rotation


def refine(data):
    """Conforming midpoint four-way subdivision with identical polygonal domain."""
    triangles=data['triangles']
    edges,inverse=np.unique(np.sort(np.concatenate([triangles[:,[0,1]],triangles[:,[1,2]],triangles[:,[2,0]]]),axis=1),axis=0,return_inverse=True)
    midpoint=inverse.reshape(3,-1).T+len(data['xy'])
    a,b,c=triangles.T
    ab,bc,ca=midpoint.T
    output={**data,'xy':np.vstack((data['xy'],data['xy'][edges].mean(axis=1))),
            'triangles':np.stack([np.column_stack((a,ab,ca)),np.column_stack((ab,b,bc)),
                                  np.column_stack((ca,bc,c)),np.column_stack((ab,bc,ca))],axis=1).reshape(-1,3),
            'labels':np.repeat(data['labels'],4)}
    lookup={tuple(edge):i+len(data['xy']) for i,edge in enumerate(edges)}
    for key in ['inner_nodes','interface1_nodes','interface2_nodes','outer_nodes']:
        loop=data[key]
        half=[lookup[tuple(sorted((int(a),int(b))))] for a,b in zip(loop,np.roll(loop,-1))]
        output[key]=np.column_stack((loop,half)).ravel()
    return output


def adaptive_boundary_sizes(polygon,factor):
    """Resolve distance to adjacent fixed polygonal layer interfaces."""
    if not np.isfinite(factor) or factor<=0:
        raise ValueError('Positive finite mesh-size factor required')
    curves=[np.asarray(polygon)*radius for radius in [20/27,21/27,22/27,1.]]
    gaps=[]
    for i,curve in enumerate(curves):
        neighboring=[]
        for j in [i-1,i+1]:
            if 0<=j<len(curves):
                start=curves[j]
                direction=np.roll(start,-1,axis=0)-start
                squared=np.sum(direction*direction,axis=1)
                if np.any(squared<=0):
                    raise ValueError('Zero-length polygon edge')
                offset=curve[:,None,:]-start[None]
                fraction=np.clip(np.sum(offset*direction,axis=2)/squared,0.,1.)
                neighboring.append(np.min(np.linalg.norm(offset-fraction[:,:,None]*direction,axis=2),axis=1))
        gaps.append(np.min(neighboring,axis=0))
    gaps=np.asarray(gaps)
    if np.any(gaps<=0):
        raise ValueError('Intersecting adjacent layers')
    return np.minimum(.09,factor*gaps),gaps


def generate(source,size_factor=None):
    import gmsh
    from scipy.spatial import cKDTree

    boundary,rotation=outline(source)
    sizes,gaps=adaptive_boundary_sizes(boundary,size_factor) if size_factor is not None else (np.full((4,len(boundary)),.09),None)
    gmsh.initialize()
    try:
        for key,value in [('General.NumThreads',1),('General.Terminal',1),('Mesh.Algorithm',6),
                          ('Mesh.MeshSizeMin',.015 if size_factor is None else 0.),('Mesh.MeshSizeMax',.09),('Mesh.RandomSeed',7301)]:
            gmsh.option.setNumber(key,value)
        gmsh.model.add('f6s1_retained_outline')
        loops=[]
        curve_tags=[]
        for layer,radius in enumerate([20/27,21/27,22/27,1.]):
            points=[gmsh.model.geo.addPoint(float(x),float(y),0.,float(h)) for (x,y),h in zip(boundary*radius,sizes[layer])]
            curves=[gmsh.model.geo.addLine(points[i],points[(i+1)%len(points)]) for i in range(len(points))]
            curve_tags.append(curves)
            loops.append(gmsh.model.geo.addCurveLoop(curves))
        surfaces=[gmsh.model.geo.addPlaneSurface([loops[i+1],loops[i]]) for i in range(3)]
        gmsh.model.geo.synchronize()
        gmsh.model.mesh.generate(2)
        tags,coordinates,_=gmsh.model.mesh.getNodes()
        xy=np.asarray(coordinates).reshape(-1,3)[:,:2]
        index={int(tag):i for i,tag in enumerate(tags)}
        triangles=[]
        labels=[]
        for label,surface in enumerate(surfaces,1):
            kinds,_,connectivity=gmsh.model.mesh.getElements(2,surface)
            for kind,values in zip(kinds,connectivity):
                if kind!=2:
                    raise ValueError('Only affine triangles are authorized')
                entries=np.array([index[int(v)] for v in values]).reshape(-1,3)
                triangles.extend(entries)
                labels.extend([label]*len(entries))
        result={'xy':xy,'triangles':np.asarray(triangles,dtype=np.int64),'labels':np.asarray(labels,dtype=np.int32),
                'anchors':boundary[[0,len(boundary)//2]],'source_to_solver_rotation':rotation,
                'polygon':boundary,'length_scale_um':source['length_scale_um'],'center_um':source['center_um']}
        for key,curves in zip(['inner_nodes','interface1_nodes','interface2_nodes','outer_nodes'],curve_tags):
            ordered=[]
            for curve in curves:
                _,_,entries=gmsh.model.mesh.getElements(1,curve)
                pairs=np.asarray(entries[0]).reshape(-1,2)
                # Gmsh segment connectivity follows the explicitly oriented CAD line.
                adjacency={int(a):int(b) for a,b in pairs}
                starts=set(adjacency)-set(adjacency.values())
                if len(starts)!=1:
                    raise ValueError('Unrecognized Gmsh line connectivity')
                node=starts.pop()
                while node in adjacency:
                    ordered.append(index[node])
                    node=adjacency[node]
            result[key]=np.asarray(ordered,dtype=np.int64)
        if cKDTree(xy).query(result['anchors'])[0].max()>1e-12:
            raise ValueError('Gauge point absent from mesh')
        return result,{'gmsh_version':gmsh.__version__,'algorithm':6,'target_size':.09,
                       'size_factor':size_factor,'minimum_prescribed_size':float(sizes.min()),
                       'minimum_adjacent_gap':None if gaps is None else float(gaps.min())}
    finally:
        gmsh.finalize()


def retained_geometry(root,config):
    """Byte-verified geometry reuse; no mesher import or invocation."""
    path=Path(root)/'retained_mesh.npz'
    if hashlib.sha256(path.read_bytes()).hexdigest()!=config['retained_mesh']['sha256']:
        raise ValueError('Retained geometry hash mismatch')
    with np.load(path,allow_pickle=False) as archive:
        return {key:archive[key] for key in archive.files}


def output_fits(root,config,planned_bytes):
    """Historical caps stay frozen; new external outputs use actual free space."""
    if config.get('output_storage',{}).get('mode')=='external_disk_free':
        from prl.result_store import disk_admission
        store=config['output_storage']
        return disk_admission(root,planned_bytes,store['stop_reserve_bytes'],store['disk_free_floor_bytes'])['can_start']
    return planned_bytes<=config['resources']['stage_bytes']


def execution_meshes(config):
    """No arbitrary partial-run escape; only the frozen two-state diagnostic."""
    if config.get('diagnostic')=='fine_two_state':
        if config.get('execution_meshes')!=['M1'] or config['passive_loads']!=[0.,.02] or config['active_peak']!=0.:
            raise ValueError('Fine diagnostic is exactly M1 at p=0 and 0.02, passive only')
        return ['M1']
    if 'execution_meshes' in config or 'diagnostic' in config:
        raise ValueError('Unknown partial execution scope')
    return ['M0','M1']


def main():
    from prl.fem.fenicsx_ring import Ring,write_json
    from prl.verification.fenicsx_ring import load_arrays,state_audit
    from prl.verification.fenicsx_contour import geometry_audit,verify_contour

    root=Path('/out')
    config=json.loads((root/'configuration.json').read_text())
    selected=execution_meshes(config)
    stage_cap=config['resources']['stage_bytes']
    started=time.monotonic()
    completed=0
    attempted=0
    current=None
    (root/'raw').mkdir(exist_ok=False)
    try:
        source=load_arrays(root/'geometry_source.npz')
        candidates=[]
        for candidate,factor in enumerate(config.get('mesh_size_candidates',[None])):
            if 'retained_mesh' in config:
                coarse=retained_geometry(root,config)
                metadata={'mode':'retained','source':config['retained_mesh'],'gmsh_calls':0}
            else:
                coarse,metadata=generate(source,factor)
            candidate_report=geometry_audit(coarse,source)
            # 12 points for the frozen degree-six triangle quadrature; 32 scalars
            # conservatively cover all saved fields/maps, plus 48 MiB for figures/control.
            predicted=len(coarse['triangles'])*5*5*12*32*8+48*1024**2
            candidates.append({'candidate':candidate,'factor':factor,'geometry':candidate_report,
                               'predicted_bytes':predicted,'storage_passed':output_fits(root,config,predicted)})
            if factor is not None:
                np.savez_compressed(root/'raw'/f'candidate_{candidate}_mesh.npz',**coarse)
                write_json(root/'mesh_candidates.json',candidates)
            if candidate_report['status']=='passed' and output_fits(root,config,predicted):
                break
            if factor is None or candidate+1==len(config.get('mesh_size_candidates',[])):
                np.savez_compressed(root/'raw'/'M0_input_mesh.npz',**coarse)
                write_json(root/'raw'/'M0_geometry_preflight.json',candidate_report)
                raise ValueError('Bounded geometry candidates exhausted; no equilibrium solves')
        write_json(root/'mesher.json',metadata)
        fine=refine(coarse)
        geometries=[coarse,fine]
        for name,data in zip(['M0','M1'],geometries):
            np.savez_compressed(root/'raw'/f'{name}_input_mesh.npz',**data)
            report=geometry_audit(data,source)
            write_json(root/'raw'/f'{name}_geometry_preflight.json',report)
            data['metrics']=report
            if report['status']!='passed':
                raise ValueError('Independent geometry gate: '+str(report['failed_checks']))
        if config.get('diagnostic')=='fine_two_state':
            prior=load_arrays(root/'comparison/M1_input_mesh.npz')
            if set(prior)!=set(fine)-{'metrics'} or not all(np.array_equal(prior[k],fine[k]) for k in prior):
                raise ValueError('Fine geometry differs from the already retained M1')
        # Conservative uncompressed storage bound: all quadrature fields, maps and states.
        predicted=sum(len(data['triangles'])*len(config['passive_loads'])*12*32*8 for name,data in zip(['M0','M1'],geometries) if name in selected)+48*1024**2
        write_json(root/'raw_storage_bound.json',{'maximum_planned_bytes':predicted,'limit_bytes':stage_cap})
        if not output_fits(root,config,predicted):
            raise ValueError('Predicted complete-state output cannot fit phase budget')
        for name,data in zip(['M0','M1'],geometries):
            if name not in selected:
                continue
            current=Ring({'name':name},config,root,geometry_input=data)
            current.tangent_checks()
            initial=np.zeros_like(current.w.x.array)
            for i,pressure in enumerate(config['passive_loads']):
                low_space=(not output_fits(root,config,32*1024**2) if stage_cap is None else
                           sum(p.stat().st_size for p in root.rglob('*') if p.is_file())>stage_cap-32*1024**2)
                if time.monotonic()-started>1140 or low_space:
                    raise RuntimeError('Stop with reserved time/storage headroom')
                attempted+=1
                initial=current.solve(f'passive_{i}',pressure,0.,initial)
                path=root/'raw'/f'{name}_state_passive_{i}.npz'
                report=state_audit(current.mesh_data,load_arrays(path),json.loads(path.with_suffix('.json').read_text()),config)
                write_json(path.with_name(path.stem+'_audit.json'),report)
                if report['status']!='passed':
                    raise ValueError('Independent state gate: '+str([k for k,v in report['checks'].items() if not v]))
                completed+=1
                write_json(root/'last_valid.json',{'mesh':name,'label':f'passive_{i}','completed_states':completed})
        if config.get('diagnostic')=='fine_two_state':
            from prl.verification.fenicsx_fine import verify_fine
            report=verify_fine(root,save=True)
        else:
            report=verify_contour(root,save=True)
        write_json(root/'solver_execution.json',{'status':report['status'],'attempted_states':attempted,
                    'completed_states':completed,'automatic_retries':0,'elapsed_seconds':time.monotonic()-started})
        return 0 if report['status']=='passed' else 2
    except Exception as error:
        if current is not None:
            np.savez_compressed(root/'failure_state.npz',mixed_state=current.w.x.array)
            write_json(root/'failure_history.json',current.history)
        write_json(root/'failure.json',{'status':'failed','reason':repr(error),'traceback':traceback.format_exc(),
                    'attempted_states':attempted,'completed_states':completed,'elapsed_seconds':time.monotonic()-started,'automatic_retries':0})
        traceback.print_exc()
        return 2


if __name__=='__main__':
    raise SystemExit(main())
