"""Read-only external result policy tests; no Docker or scientific solves."""
from collections import namedtuple
from pathlib import Path
import pytest
from prl.result_store import disk_admission,policy,result_path

ROOT=Path(__file__).parents[2]
MIB=1024**2
GIB=1024**3


def test_external_results_have_no_fixed_stage_limit(monkeypatch):
    import prl.result_store as store
    usage=namedtuple('usage','total used free')
    monkeypatch.setattr(store.shutil,'disk_usage',lambda path:usage(200*GIB,40*GIB,160*GIB))
    report=disk_admission(ROOT,5*GIB)
    assert report['can_start'] and report['fixed_stage_limit_bytes'] is None


def test_free_disk_floor_includes_forecast_and_failure_reserve(monkeypatch):
    import prl.result_store as store
    usage=namedtuple('usage','total used free')
    required=10*GIB+64*MIB+900*MIB
    monkeypatch.setattr(store.shutil,'disk_usage',lambda path:usage(20*GIB,0,required-1))
    assert not disk_admission(ROOT,900*MIB)['can_start']
    monkeypatch.setattr(store.shutil,'disk_usage',lambda path:usage(20*GIB,0,required))
    assert disk_admission(ROOT,900*MIB)['can_start']


@pytest.mark.parametrize('bad',['../outside','results/../../outside','src/not_a_result'])
def test_escape_and_non_result_paths_rejected(bad):
    with pytest.raises(ValueError):
        result_path(ROOT,bad,new=True)


def test_legacy_result_is_read_in_place_and_cannot_be_rerun():
    identifier='results/ventricle_fem/f6s1p_retained_passive_v01_20260917'
    if not (ROOT/identifier).exists():
        pytest.skip('Local scientific evidence is outside Git')
    assert result_path(ROOT,identifier)==ROOT/identifier
    with pytest.raises(FileExistsError):
        result_path(ROOT,identifier,new=True)


def test_new_result_is_only_allocated_inside_approved_root():
    try:
        _,base=policy(ROOT)
    except FileNotFoundError:
        pytest.skip('External store needs explicit local authorization/setup')
    path=result_path(ROOT,'results/ventricle_fem/_uncreated_unit_test_path',new=True)
    assert path.is_relative_to(base) and not path.exists()


def test_solver_storage_seam_uses_disk_not_800_mib(monkeypatch):
    import prl.result_store as store
    from prl.fem.fenicsx_contour import output_fits
    usage=namedtuple('usage','total used free')
    monkeypatch.setattr(store.shutil,'disk_usage',lambda path:usage(200*GIB,0,100*GIB))
    cfg={'resources':{'stage_bytes':None},'output_storage':{'mode':'external_disk_free',
         'stop_reserve_bytes':64*MIB,'disk_free_floor_bytes':10*GIB}}
    assert output_fits(ROOT,cfg,2*GIB)
    monkeypatch.setattr(store.shutil,'disk_usage',lambda path:usage(200*GIB,0,10*GIB))
    assert not output_fits(ROOT,cfg,2*GIB)


def test_completed_contour_run_refuses_before_any_docker_call(monkeypatch):
    import prl.runs.fenicsx_contour as runner
    if not (ROOT/runner.PASSIVE_RESULT).exists():
        pytest.skip('Local scientific evidence is outside Git')
    def unexpected_docker(*args):
        pytest.fail('A completed stage must be refused before touching Docker')
    monkeypatch.setattr(runner,'read_docker',unexpected_docker)
    with pytest.raises(FileExistsError):
        runner.run_contour(ROOT,retained=True)


def test_result_index_rejects_nonstandard_status_without_writing():
    from prl.result_store import register_result
    with pytest.raises(ValueError,match='project execution status'):
        register_result(ROOT,ROOT,'passed_science_implicitly','unused')
