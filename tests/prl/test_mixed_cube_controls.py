"""Control-field identities and approval gates; no native/FEM execution."""
import ast
from pathlib import Path
from unittest.mock import patch
import numpy as np
import pytest
from prl.fem.mixed_cube_spec import configuration,guarded_configuration,control_configuration,disposition
from prl.verification.mixed_cube import exact_fields,exact_kinematics,convergence


def test_control_scope_preserves_original_physics_gates_and_guard():
    original=guarded_configuration(); control=control_configuration()
    for key in ['mu','solver','quadrature_degree','patch_gates','mms_gates','resources','trial_guard']:
        assert control[key]==original[key]
    assert len(control['cases'])==control['maximum_equilibrium_solves']==4
    assert [(x['kind'],x['n'],x['kappa']) for x in control['cases']]==[
        ('quadratic_volume',2,1000.),('isochoric_mms',2,1000.),
        ('isochoric_mms',4,1000.),('isochoric_mms',8,1000.)]
    assert len(configuration()['cases'])==8


def test_exact_controls_have_registered_volume_and_compatible_pressure():
    points=np.random.default_rng(1909).random((17,3))
    volume=exact_fields(points,'quadratic_volume',1000.)
    np.testing.assert_allclose(volume['J'],1+.004*points[:,0],rtol=0,atol=1e-15)
    np.testing.assert_allclose(volume['pressure'],4*points[:,0],rtol=0,atol=3e-13)
    assert np.linalg.norm(volume['body'])>1
    shear=exact_fields(points,'isochoric_mms',1000.)
    np.testing.assert_array_equal(shear['J'],np.ones(17))
    np.testing.assert_array_equal(shear['pressure'],np.zeros(17))
    np.testing.assert_array_equal(shear['grad'][:,:,0],np.zeros((17,3)))
    assert np.linalg.norm(shear['body'])>0


@pytest.mark.parametrize('kind',['quadratic_volume','isochoric_mms'])
def test_independent_hessian_against_gradient_difference(kind):
    points=np.random.default_rng(9).random((11,3)); h=1e-5
    _,_,hessian=exact_kinematics(points,kind)
    for axis in range(3):
        step=np.zeros(3); step[axis]=h
        high=exact_kinematics(points+step,kind)[1]; low=exact_kinematics(points-step,kind)[1]
        np.testing.assert_allclose((high-low)/(2*h),hessian[...,axis],rtol=1e-8,atol=1e-11)


def test_production_boundary_expression_without_loading_native_runtime():
    # Evaluate the actual production NumPy function, not a second copied expression.
    source=Path(__file__).resolve().parents[2]/'src/prl/fem/fenicsx_mixed_cube.py'
    parsed=ast.parse(source.read_text(encoding='utf-8'))
    definition=next(node for node in parsed.body if isinstance(node,ast.FunctionDef)
                    and node.name=='exact_displacement_numpy')
    namespace={'np':np}
    exec(compile(ast.Module(body=[definition],type_ignores=[]),str(source),'exec'),namespace)
    points=np.random.default_rng(91).random((13,3))
    for kind in ['affine','shear','mms','quadratic_volume','isochoric_mms']:
        np.testing.assert_allclose(namespace['exact_displacement_numpy'](points.T,kind).T,
            exact_kinematics(points,kind)[0],rtol=1e-14,atol=1e-16)


def synthetic_reports():
    # Test data only, never scientific evidence.
    reports={'patch_quadratic_volume':{'status':'passed'}}
    for n in [2,4,8]:
        reports[f'isochoric_k1000_n{n}']={'status':'passed','metrics':{
            'relative_u_L2':1/n**3,'relative_u_H1':1/n**2,
            'relative_pressure_L2':None,'scaled_pressure_L2':.01/n,'J_error_RMS':.001/n}}
    return reports


def test_defined_gates_pass_does_not_assert_zero_pressure_relative_accuracy():
    result=convergence(synthetic_reports(),control_configuration())
    assert result['status']=='passed'
    assert result['groups']['isochoric']['relative_pressure_qualification']=='unknown'
    assert result['groups']['isochoric']['relative_pressure_error'] is None
    assert result['original_eight_case_qualification']=='failed_unchanged'
    assert result['does_not_qualify_original_ventricle']


def test_control_gate_failures_missing_states_and_stop_policy():
    cfg=control_configuration(); reports=synthetic_reports()
    assert convergence({},cfg)['status']=='not_run'
    assert convergence({'patch_quadratic_volume':{'status':'passed'}},cfg)['status']=='blocked'
    reports['isochoric_k1000_n8']['metrics']['relative_u_H1']=.16
    assert convergence(reports,cfg)['status']=='failed'
    soft={'status':'failed','hard_failures':[]}
    assert disposition('quadratic_volume',soft)=='stop_batch'
    assert disposition('isochoric_mms',soft)=='continue_registered_cases'
    assert disposition('isochoric_mms',{'status':'failed','hard_failures':['positive_J']})=='stop_batch'


def test_explicit_control_entry_is_create_only():
    from prl.runs.mixed_cube import run,batch_spec
    from prl.cli import _parser
    selected=batch_spec('controls_v01')
    assert selected['container']!=batch_spec('v03')['container']
    assert selected['result']!=batch_spec('v03')['result']
    assert _parser().parse_args(['run','fem-mixed-cube','--batch','controls_v01']).batch=='controls_v01'
    with patch('prl.runs.mixed_cube.result_path',side_effect=FileExistsError),patch('prl.runs.mixed_cube.read_docker') as runtime:
        with pytest.raises(FileExistsError):
            run(Path.cwd(),'controls_v01')
        runtime.assert_not_called()
