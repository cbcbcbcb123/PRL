"""Image polygon meshing and passive FEniCSx adaptation in the pinned image."""

from pathlib import Path
import json
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


def generate(source):
    import gmsh
    from scipy.spatial import cKDTree

    boundary,rotation=outline(source)
    gmsh.initialize()
    try:
        for key,value in [('General.NumThreads',1),('General.Terminal',1),('Mesh.Algorithm',6),
                          ('Mesh.MeshSizeMin',.015),('Mesh.MeshSizeMax',.09),('Mesh.RandomSeed',7301)]:
            gmsh.option.setNumber(key,value)
        gmsh.model.add('f6s1_retained_outline')
        loops=[]
        curve_tags=[]
        for radius in [20/27,21/27,22/27,1.]:
            points=[gmsh.model.geo.addPoint(float(x),float(y),0.,.09) for x,y in boundary*radius]
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
        return result,{'gmsh_version':gmsh.__version__,'algorithm':6,'target_size':.09}
    finally:
        gmsh.finalize()


def main():
    from prl.fem.fenicsx_ring import Ring,write_json
    from prl.verification.fenicsx_ring import load_arrays,state_audit
    from prl.verification.fenicsx_contour import geometry_audit,verify_contour

    root=Path('/out')
    config=json.loads((root/'configuration.json').read_text())
    started=time.monotonic()
    completed=0
    attempted=0
    current=None
    (root/'raw').mkdir(exist_ok=False)
    try:
        source=load_arrays(root/'geometry_source.npz')
        coarse,metadata=generate(source)
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
        # Conservative uncompressed storage bound: all quadrature fields, maps and states.
        predicted=sum(len(data['triangles'])*5*16*32*8 for data in geometries)+48*1024**2
        write_json(root/'raw_storage_bound.json',{'maximum_planned_bytes':predicted,'limit_bytes':256*1024**2})
        if predicted>256*1024**2:
            raise ValueError('Predicted complete-state output cannot fit phase budget')
        for name,data in zip(['M0','M1'],geometries):
            current=Ring({'name':name},config,root,geometry_input=data)
            current.tangent_checks()
            initial=np.zeros_like(current.w.x.array)
            for i,pressure in enumerate(config['passive_loads']):
                if time.monotonic()-started>1140 or sum(p.stat().st_size for p in root.rglob('*') if p.is_file())>224*1024**2:
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
