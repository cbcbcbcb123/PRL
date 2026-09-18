"""Bounded M1 diagnostic selection and non-masking diagnostic comparisons."""
import json
from pathlib import Path
from unittest.mock import patch
import pytest
from prl.fem.ventricle_geometry import configuration
from prl.fem.ventricle_protocol import remaining_states
from prl.runs.ventricle_3d import fine_pressure_configuration,run
from prl.verification.ventricle_mesh_probe import compare_response


def test_exact_existing_M1_and_two_original_states(tmp_path):
    original=configuration(); parent={**original,'reuse_m0_zero':True,'maximum_equilibrium_solves':13}
    (tmp_path/'configuration.json').write_text(json.dumps(parent))
    actual=fine_pressure_configuration(tmp_path)
    assert actual['meshes']==[original['meshes'][1]] and actual['states']==original['states'][:2]
    assert actual['maximum_equilibrium_solves']==2 and len(remaining_states(actual,'M1'))==2
    for key in set(original)-{'meshes','states','maximum_equilibrium_solves'}:
        assert actual[key]==original[key]
    parent['kappa']=1001; (tmp_path/'configuration.json').write_text(json.dumps(parent))
    with pytest.raises(ValueError,match='configuration changed'):
        fine_pressure_configuration(tmp_path)


def test_mesh_response_agreement_never_relabels_coarse_failure():
    coarse={'status':'failed','volume_change':.011,'max_abs_J_minus_one':.015}
    fine={'status':'passed','volume_change':.0111,'max_abs_J_minus_one':.009}
    result=compare_response(coarse,fine)
    assert result['response_reference_gate'] and not result['pointwise_qualification_both_meshes']
    assert result['local_distortion_ratio_M1_over_M0']==.6
    assert not compare_response(coarse,{**fine,'volume_change':.012})['response_reference_gate']


def test_fine_create_only_before_runtime():
    with patch('prl.runs.ventricle_3d.result_path',side_effect=FileExistsError),patch('prl.runs.ventricle_3d.read_docker') as docker:
        with pytest.raises(FileExistsError):
            run(Path(__file__).resolve().parents[2],fine_pressure=True)
        docker.assert_not_called()


def test_fine_cli_modes_are_exclusive():
    from prl.cli import _parser
    for command in ['run','verify']:
        assert _parser().parse_args([command,'fem-idealized-3d','--fine-first-pressure']).fine_first_pressure
        with pytest.raises(SystemExit):
            _parser().parse_args([command,'fem-idealized-3d','--fine-first-pressure','--resume-qualified-zero'])
    with pytest.raises(ValueError,match='one explicitly authorized slice'):
        run(Path('.'),resume=True,fine_pressure=True)
