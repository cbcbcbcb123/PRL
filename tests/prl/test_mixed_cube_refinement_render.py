"""No-file tests of retained-state selection and frozen non-dyadic orders."""

import numpy as np
import pytest

from prl.rendering.mixed_cube_refinement import FINE_CASE, _prepare_plot_data


def report_fixture():
    return {"cases": [{"n": n, "equilibrium": "passed", "kind": "mms", "u_degree": 3, "p_degree": 2,
                        "metrics": {"relative_u_L2": n ** -3.6, "relative_u_H1": n ** -2.8,
                                    "relative_pressure_L2": n ** -3.1}}
                       for n in (4, 8, 12)],
            "convergence": {"status": "passed", "primary_pair": [8, 12], "grid_levels": [4, 8, 12],
                            "primary_EOC": {"u_L2": 3.6, "u_H1": 2.8, "pressure_L2": 3.1}}}


def state_fixture(report, iterations=(0, 1, 2, 3)):
    coordinates = np.array([[0., 0., .5], [1., 0., .5], [0., 1., .5], [1., 1., .5]])
    arrays = {FINE_CASE + "_coordinates": coordinates,
              FINE_CASE + "_boundary_faces": np.array([[0, 1, 2], [1, 2, 3]]),
              FINE_CASE + "_boundary_tags": np.array([1, 2]),
              FINE_CASE + "_iterations": np.array(iterations, dtype=int)}
    report["iterate_diagnostics"] = {FINE_CASE: [{"iteration": index, "residual": 1. / (index + 1)}
                                               for index in iterations]}
    for index in iterations:
        arrays[FINE_CASE + f"_u_{index}"] = np.full_like(coordinates, index * 1e-4)
    return arrays


def test_primary_order_uses_ln_one_point_five_and_retains_historical_order():
    data = _prepare_plot_data(report_fixture(), {})
    assert data["primary_EOC"] == pytest.approx({"u_L2": 3.6, "u_H1": 2.8, "pressure_L2": 3.1})
    assert data["historical_EOC"] == pytest.approx(data["primary_EOC"])


def test_wrong_dyadic_report_order_is_rejected():
    report = report_fixture()
    report["convergence"]["primary_EOC"]["u_L2"] = 3.6 * np.log(1.5) / np.log(2)
    with pytest.raises(ValueError, match="ln"):
        _prepare_plot_data(report, {})


def test_only_actual_first_middle_last_states_are_selected_and_fields_are_unscaled():
    report = report_fixture()
    arrays = state_fixture(report)
    data = _prepare_plot_data(report, arrays)
    assert [state["iteration"] for state in data["states"]] == [0, 2, 3]
    np.testing.assert_array_equal(data["states"][1]["u"], arrays[FINE_CASE + "_u_2"])


def test_missing_primary_grid_is_not_synthesized():
    report = report_fixture()
    report["cases"][-1]["equilibrium"] = "not_run"
    report["convergence"]["primary_EOC"] = {}
    data = _prepare_plot_data(report, {})
    assert data["primary_EOC"] == dict.fromkeys(("u_L2", "u_H1", "pressure_L2"))
    assert data["states"] == []
    assert 12 not in data["curves"]["u_L2"]


def test_failed_scientific_qualification_does_not_hide_retained_errors():
    report = report_fixture()
    report["convergence"]["status"] = "failed"
    assert len(_prepare_plot_data(report, {})["curves"]["u_L2"]) == 3


@pytest.mark.parametrize("replacement", [{"primary_pair": [12, 16]}, {"grid_levels": [8, 12, 16]}])
def test_rejected_old_window_cannot_be_plotted(replacement):
    report = report_fixture()
    report["convergence"].update(replacement)
    with pytest.raises(ValueError, match="frozen"):
        _prepare_plot_data(report, {})


def test_missing_saved_state_is_an_error_not_an_interpolation_request():
    report = report_fixture()
    arrays = state_fixture(report)
    arrays.pop(FINE_CASE + "_u_2")
    with pytest.raises(KeyError):
        _prepare_plot_data(report, arrays)
