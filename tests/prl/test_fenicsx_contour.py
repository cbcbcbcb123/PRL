"""No solver/container calls: mesh seam, independent geometry and routing checks."""

from pathlib import Path
import ast

import numpy as np

from prl.fem.fenicsx_contour import outline,refine
from prl.fem.ring_geometry import annulus
from prl.runs.fenicsx_contour import configuration
from prl.verification.fenicsx_contour import inside,polygon_area
from prl.verification.fenicsx_ring import state_audit
from test_fenicsx_ring import triangle_mesh


def test_midpoint_refinement_keeps_domain_and_shared_edges():
    xy,tri,labels=annulus(64,[1,1,5],[20/27,21/27,22/27,1.])
    data={'xy':xy,'triangles':tri,'labels':labels,
          **{key:level*64+np.arange(64) for key,level in [('inner_nodes',0),('interface1_nodes',1),('interface2_nodes',2),('outer_nodes',7)]}}
    refined=refine(data)
    assert len(refined['triangles'])==4*len(tri)
    for key in ['inner_nodes','interface1_nodes','interface2_nodes','outer_nodes']:
        assert abs(polygon_area(xy[data[key]])-polygon_area(refined['xy'][refined[key]]))<1e-13
        assert np.array_equal(refined[key][::2],data[key])
    counts=np.unique(np.sort(np.concatenate([refined['triangles'][:,[0,1]],refined['triangles'][:,[1,2]],refined['triangles'][:,[2,0]]]),axis=1),axis=0,return_counts=True)[1]
    assert set(counts)=={1,2}
    assert np.count_nonzero(counts==1)==256


def test_source_frame_anchor_line_horizontal_and_no_mutation():
    angles=np.arange(256)*2*np.pi/256
    source={'smooth_contour_um':np.column_stack((2*np.cos(angles),np.sin(angles)))+[4,6],
            'center_um':np.array([4,6]),'length_scale_um':np.array(2.)}
    before=source['smooth_contour_um'].copy()
    poly,rotation=outline(source)
    assert poly.shape==(128,2) and polygon_area(poly)>0
    assert abs(poly[64,1]-poly[0,1])<1e-14
    assert np.allclose(rotation@rotation.T,np.eye(2))
    assert np.array_equal(source['smooth_contour_um'],before)


def test_independent_inside_and_area():
    polygon=np.array([[0.,0.],[2,0],[2,1],[0,1]])
    assert polygon_area(polygon)==2.
    assert inside(np.array([[1,.5],[3,.5],[-1,0.]]),polygon).tolist()==[True,False,False]


def test_contour_not_given_false_circular_analytic_reference():
    data=triangle_mesh()
    data['inner_edges']=np.array([[0,5,1],[1,3,2],[2,4,0]])
    data['fixed']=np.zeros((6,2),dtype=bool); data['fixed'][0]=True
    state={'u':np.zeros((6,2)),'pressure':np.zeros(3),'activation':0.,'load':.02,
           'F':np.broadcast_to(np.eye(3),(1,3,3,3)).copy(),'J':np.ones((1,3)),
           'stress':np.zeros((1,3,3,3)),'active_stress':np.zeros((1,3,3,3)),
           'force_residual':np.zeros((6,2))}
    report=state_audit(data,state,{'snes_reason':2,'iterations':0,'free_residual_norm':0.,'active_energy':0.},configuration())
    assert 'analytic_relative_error' not in report
    assert report['status']=='failed'  # nonzero pressure but zero internal force


def test_public_cli_and_no_mechanics_import_in_verifier():
    from prl.cli import _parser,FEM_RUN_COMMANDS
    for command in ['run','verify','render']:
        assert _parser().parse_args([command,'fem-fenicsx-contour']).command==command
    assert 'fem-fenicsx-contour' in FEM_RUN_COMMANDS
    path=Path(__file__).parents[2]/'src/prl/verification/fenicsx_contour.py'
    tree=ast.parse(path.read_text())
    for node in ast.walk(tree):
        if isinstance(node,ast.ImportFrom):
            assert not (node.module or '').startswith(('prl.fem','prl.runs','dolfinx','ufl'))


def test_contract_parameters_unchanged():
    cfg=configuration()
    assert (cfg['mu'],cfg['kappa'])==(1.,1000.)
    assert cfg['passive_loads']==[0.,.02,.04,.06,.08]
    assert cfg['resources']['threads']==1 and cfg['resources']['gpu']==0
    assert cfg['solver']['snes_max_it']==30


def test_mesh_diagnostic_counts_true_angles_without_mechanical_fields():
    from prl.rendering.fenicsx_contour import diagnose
    xy,tri,labels=annulus(64,[1,1,5],[20/27,21/27,22/27,1.])
    minimum,report=diagnose({'xy':xy,'triangles':tri,'labels':labels})
    assert minimum.min()>=20 and report['below_20_degrees']==0
    assert report['mechanical_equilibria']==0
    assert sum(item['cells'] for item in report['layers'].values())==len(tri)
