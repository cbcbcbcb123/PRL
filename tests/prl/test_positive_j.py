"""Candidate-path regression tests, without a native FEM solve."""
import numpy as np
import pytest


def test_cubic_coefficients_match_direct_determinants():
    from prl.fem.positive_j import determinant_coefficients
    rng=np.random.default_rng(912)
    base=np.eye(3)+rng.normal(size=(7,11,3,3))*.1
    increment=rng.normal(size=base.shape)
    coefficients=determinant_coefficients(base,increment)
    for scale in [0.,.05,.5,1.]:
        value=sum(coefficients[...,power]*scale**power for power in range(4))
        np.testing.assert_allclose(value,np.linalg.det(base+scale*increment),rtol=3e-13,atol=3e-14)


def test_positive_endpoints_do_not_admit_an_inverted_interior():
    from prl.fem.positive_j import admissible_scale
    base=np.eye(3)[None]
    increment=np.diag([-3.,-2.,0.])[None]
    assert np.linalg.det(base)[0]>0 and np.linalg.det(base+increment)[0]>0
    assert np.linalg.det(base+.4*increment)[0]<0
    result=admissible_scale(base,increment)
    assert result['scale']==.25
    assert result['halvings']==2
    for scale in np.linspace(0,result['scale'],101):
        assert np.linalg.det(base+scale*increment).min()>0


def test_unmodified_safe_direction_and_nonfinite_rejection():
    from prl.fem.positive_j import admissible_scale
    base=np.eye(3)[None]
    assert admissible_scale(base,base*.001)['scale']==1.
    with pytest.raises(ValueError,match='current'):
        admissible_scale(-base,base)
    with pytest.raises(ValueError,match='finite'):
        admissible_scale(base,base*np.nan)
    with pytest.raises(ValueError,match='halving'):
        admissible_scale(base,-base*3,max_halvings=0)


def test_independent_stationary_point_audit_finds_interior_inversion():
    from prl.verification.positive_j import path_minimum
    base=np.eye(3)[None]; increment=np.diag([-3.,-2.,0.])[None]
    minimum,error=path_minimum(base,increment)
    assert minimum==pytest.approx(-1/24)
    assert error<1e-14
    assert path_minimum(base,increment*.25)[0]>0


def test_guarded_configuration_changes_only_candidate_admission():
    from prl.fem.mixed_cube_spec import configuration,guarded_configuration
    from prl.runs.mixed_cube import batch_spec,run
    from pathlib import Path
    from unittest.mock import patch
    guarded=guarded_configuration()
    assert guarded.pop('trial_guard')['max_halvings']==20
    assert guarded==configuration()
    assert batch_spec('v03')['container']=='prl-mixed-cube-benchmark-v03-20260919'
    with patch('prl.runs.mixed_cube.result_path',side_effect=FileExistsError),patch('prl.runs.mixed_cube.read_docker') as runtime:
        with pytest.raises(FileExistsError):
            run(Path(__file__).resolve().parents[2],'v03')
        runtime.assert_not_called()
