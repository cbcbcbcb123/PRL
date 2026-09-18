"""Explicit saved-field protocol fixtures; no scientific result fabrication."""
import json
from types import SimpleNamespace
import numpy as np
import pytest

from prl.rendering.fenicsx_contour_pressure import plot_data


def plotting_fixture():
    report={'cases':{},'retained_failed_CG1':{}}
    data={'mu':np.array(1.),'kappa':np.array(1000.)}
    for name in ['M0','M1']:
        report['cases'][name]={'passive_0':{'cavity_area':2.,'max_abs_J_minus_one':0.,'status':'passed','cavity_area_change':0.}}
        report['retained_failed_CG1'][name]={'audit':{'max_abs_J_minus_one':0.}}
        data[name+'_mesh_cells']=np.array([[0,1,2]])
        data[name+'_indices']=np.array([0])
        for key,value in {'u':np.zeros((3,2)),'pressure':np.zeros(3),'load':np.array(0.),'activation':np.array(0.)}.items():
            data[name+'_0_'+key]=value
            data[name+'_CG1_state_'+key]=value
        data[name+'_CG1_mesh_cells']=np.array([[0,1,2]])
    data['verification']=np.array(json.dumps(report))
    mechanics=SimpleNamespace(load_arrays=lambda path:data,
        fields=lambda *args:{'J':np.ones((1,2)),'stress':np.zeros((1,2,3,3))},
        cavity=lambda *args:(2.,None,None))
    return data,mechanics


def test_no_fabricated_pressure_frames():
    _,mechanics=plotting_fixture()
    _,_,cases,_,_=plot_data(None,mechanics)
    assert sum(len(rows) for rows in cases.values())==2
    assert all(rows[0]['index']==0 for rows in cases.values())


def test_raw_field_disagreement_refuses_plot():
    _,mechanics=plotting_fixture()
    mechanics.cavity=lambda *args:(2.01,None,None)
    with pytest.raises(ValueError,match='disagree'):
        plot_data(None,mechanics)


def test_failure_status_remains_failure_in_plot():
    data,mechanics=plotting_fixture()
    report=json.loads(str(data['verification']))
    report['cases']['M1']['passive_0']['status']='failed'
    data['verification']=np.array(json.dumps(report))
    _,_,cases,_,_=plot_data(None,mechanics)
    assert cases['M1'][0]['status']=='failed'


def test_delivery_accepts_observed_finite_difference_cancellation_only():
    from prl.rendering.fenicsx_contour_pressure import audit_agreement
    native={'pressure':.02,'cavity_area':3.7694874817876047,'pressure_area_difference_work':.0007491571274442776,
            'checks':{'local_volume':True,'pressure_virtual_work':True}}
    host={**native,'pressure_area_difference_work':.0007491571287765453}
    assert audit_agreement({'cases':{'M0':{'passive_1':host}}},{'cases':{'M0':{'passive_1':native}}})['status']=='passed'


@pytest.mark.parametrize('changed',[
    {'pressure_area_difference_work':.00075}, {'checks':{'local_volume':False,'pressure_virtual_work':True}},
    {'unrelated_error':1.3e-12}])
def test_delivery_rejects_nonroundoff_or_categorical_change(changed):
    from prl.rendering.fenicsx_contour_pressure import audit_agreement
    native={'pressure':.02,'cavity_area':3.7694874817876047,'pressure_area_difference_work':.0007491571274442776,
            'checks':{'local_volume':True,'pressure_virtual_work':True}}
    if 'unrelated_error' in changed:
        # Non-finite-difference quantities keep the strict base floor.
        native={**native,'unrelated_error':0.}
    assert audit_agreement({'cases':{'M0':{'passive_1':{**native,**changed}}}},
        {'cases':{'M0':{'passive_1':native}}})['status']=='failed'
