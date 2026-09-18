"""Read saved P2 states: sampled boundary safety and localized volume observations.

This module never changes a state, runs FEM, or changes mechanical acceptance.
Sampled simple boundaries are not a proof of exact-curve global injectivity.
"""
import hashlib
import json
from pathlib import Path

import numpy as np
import shapely
from shapely.geometry import LinearRing, Polygon, Point
from shapely.validation import explain_validity

from .fenicsx_ring import load_arrays, fields, shape


def ordered_outer(mesh):
    edges=mesh['cells'][:,[[0,5,1],[1,3,2],[2,4,0]]].reshape(-1,3)
    _,indices,counts=np.unique(np.sort(edges[:,[0,2]],axis=1),axis=0,return_inverse=True,return_counts=True)
    boundary=edges[counts[indices]==1]
    inner={tuple(sorted(pair)) for pair in mesh['inner_edges'][:,[0,2]]}
    outer=[edge for edge in boundary if tuple(sorted(edge[[0,2]])) not in inner]
    adjacency={}
    for a,mid,b in outer:
        adjacency.setdefault(int(a),[]).append((int(b),int(mid)))
        adjacency.setdefault(int(b),[]).append((int(a),int(mid)))
    if not adjacency or not all(len(neighbors)==2 for neighbors in adjacency.values()):
        raise ValueError('Outer boundary is not a two-neighbor cycle')
    start=min(adjacency); current=start; previous=None; result=[]
    while True:
        node,mid=next(pair for pair in adjacency[current] if pair[0]!=previous)
        result.append((current,mid,node)); previous,current=current,node
        if current==start:
            break
        if len(result)>len(outer):
            raise ValueError('Boundary walk did not close')
    if len(result)!=len(outer):
        raise ValueError('Additional outer boundary components')
    return np.asarray(result)


def curve(nodes,edges,subdivisions):
    parameter=np.arange(subdivisions)/subdivisions
    basis=np.column_stack((2*parameter**2-3*parameter+1,4*parameter-4*parameter**2,2*parameter**2-parameter))
    return LinearRing(np.einsum('qa,eai->eqi',basis,nodes[edges]).reshape(-1,2))


def passive_observations(root):
    root=Path(root); config=json.loads((root/'configuration.json').read_text())
    report=json.loads((root/'post_verification.json').read_text())
    records={}; inputs={}
    for name in ['M0','M1']:
        meshpath=root/'raw'/f'{name}_mesh.npz'
        if not meshpath.exists():
            meshpath=root/'retained'/f'{name}_mesh.npz'
        mesh=load_arrays(meshpath); outer=ordered_outer(mesh); inner=mesh['inner_edges']
        inputs[meshpath.relative_to(root).as_posix()]=hashlib.sha256(meshpath.read_bytes()).hexdigest()
        anchors=load_arrays(root/'input'/f'{name}_input_mesh.npz')['anchors']
        reference_inner=curve(mesh['coordinates'],inner,48)
        reference_outer=curve(mesh['coordinates'],outer,48)
        basis=shape(mesh['qpoints'])[0]
        coordinates=np.einsum('qa,cai->cqi',basis,mesh['coordinates'][mesh['cells']])
        for label,audit in report['cases'][name].items():
            index=int(label.split('_')[-1]); path=root/('retained' if index<2 else 'raw')/f'{name}_state_{label}.npz'
            state=load_arrays(path); values=fields(mesh,state,config['mu'],config['kappa'])
            inputs[path.relative_to(root).as_posix()]=hashlib.sha256(path.read_bytes()).hexdigest()
            nodes=mesh['coordinates']+state['u']; samples={}
            for subdivisions in [24,48]:
                rings=[curve(nodes,edges,subdivisions) for edges in [outer,inner]]
                wall=Polygon(rings[0],holes=[rings[1]])
                checks={'outer_simple':bool(rings[0].is_simple),'inner_simple':bool(rings[1].is_simple),
                    'outer_contains_cavity':bool(Polygon(rings[0]).contains(Polygon(rings[1]))),
                    'wall_valid':bool(wall.is_valid),'wall_positive_area':bool(wall.area>0)}
                samples[str(subdivisions)]={'status':'passed' if all(checks.values()) else 'failed','checks':checks,
                    'validity':explain_validity(wall),'minimum_sampled_boundary_distance_L':float(rings[0].distance(rings[1]))}
            deviations=np.abs(values['J']-1); cell,quadrature=np.unravel_index(np.argmax(deviations),deviations.shape)
            location=coordinates[cell,quadrature]; bad=deviations>.01; weights=values['weights']
            pressure_basis=shape(mesh['qpoints'])[0]
            local_pressure=np.einsum('qa,ca->cq',pressure_basis,state['pressure'].reshape(-1)[mesh['pressure_cells']])
            records[f'{name}_{label}']={'mechanical_status':audit['status'],'load':float(state['load']),
                'samples':samples,'J_at_extreme':float(values['J'][cell,quadrature]),
                'pressure_at_extreme_over_mu':float(local_pressure[cell,quadrature]/config['mu']),
                'cell_index':int(cell),'quadrature_index':int(quadrature),'layer':int(mesh['layers'][cell]),
                'reference_location_L':location.tolist(),
                'reference_distance_to_inner_L':float(reference_inner.distance(Point(location))),
                'reference_distance_to_outer_L':float(reference_outer.distance(Point(location))),
                'reference_distance_to_gauges_L':np.linalg.norm(anchors-location,axis=1).tolist(),
                'cells_exceeding_one_percent':int(np.count_nonzero(np.any(bad,axis=1))),
                'total_cells':len(mesh['cells']),'quadrature_points_exceeding_one_percent':int(np.count_nonzero(bad)),
                'exceeding_reference_weight_fraction':float(weights[bad].sum()/weights.sum()),
                'weighted_mean_J':float(np.sum(weights*values['J'])/weights.sum())}
    return {'status':'passed' if all(item['status']=='passed' for case in records.values() for item in case['samples'].values()) else 'failed',
        'scope':'saved-state observations only; 24/48 straight subsegments per quadratic boundary edge, not exact global injectivity',
        'volume_fraction_note':'quadrature-weighted reference measure of points above original 1% gate, not an exact resolved defect volume',
        'shapely_version':shapely.__version__,'inputs_sha256':inputs,'cases':records,'new_equilibria':0,'physical_gates_changed':False}
