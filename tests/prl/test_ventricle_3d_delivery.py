"""Delivery comparisons must not disguise scientific failure or widen tolerances."""
from prl.rendering.ventricle_3d_resume import report_agreement


def test_cross_platform_roundoff_only_for_two_virtual_work_error_fields():
    assert not report_agreement({'active_virtual_work_error':1e-12},{'active_virtual_work_error':2e-10})
    assert report_agreement({'max_abs_J_minus_one':.01},{'max_abs_J_minus_one':.0100000002})
    assert report_agreement({'pressure_virtual_work_error':0.},{'pressure_virtual_work_error':2e-9})


def test_categorical_failures_cannot_be_hidden_by_numeric_comparison():
    assert report_agreement({'status':'failed','checks':{'local_volume':False}},
                            {'status':'passed','checks':{'local_volume':True}})
    assert report_agreement({'a':[1,2]},{'a':[1]})
    assert report_agreement({'a':1},{'b':1})
