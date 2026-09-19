"""In-memory evidence-selection checks; these tests do not render or save files."""

import numpy as np
import pytest

from prl.rendering.mixed_cube_representation import FINE_CASE, _prepare_plot_data


def saved_inputs(iterations=(0, 1, 2, 3, 4)):
    coordinates = np.array([[0., 0., .5], [1., 0., .5], [0., 1., .5], [1., 1., .5]])
    arrays = {FINE_CASE + "_coordinates": coordinates,
              FINE_CASE + "_iterations": np.asarray(iterations, dtype=int)}
    history = []
    for index in iterations:
        # Test-only values are deliberately distinct from any production result.
        arrays[FINE_CASE + f"_u_{index}"] = np.full_like(coordinates, index * 1e-4)
        history.append({"iteration": index, "residual": float(5 - index)})
    report = {"cases": [], "iterate_diagnostics": {FINE_CASE: history}}
    return report, arrays


def test_selection_uses_real_first_middle_last_states_without_scaling_fields():
    report, arrays = saved_inputs()
    prepared = _prepare_plot_data(report, arrays)
    assert [state["iteration"] for state in prepared["states"]] == [0, 2, 4]
    np.testing.assert_array_equal(prepared["states"][1]["u"], arrays[FINE_CASE + "_u_2"])
    np.testing.assert_array_equal(prepared["slice"], arrays[FINE_CASE + "_coordinates"][:, :2])


def test_fewer_states_and_not_run_cases_are_not_fabricated():
    report, arrays = saved_inputs((0, 4))
    report["cases"] = [{"kind": "mms", "u_degree": 3, "p_degree": 2,
                        "n": 8, "equilibrium": "not_run", "DOF": 1,
                        "metrics": {"relative_u_H1": .1, "relative_pressure_L2": .2}}]
    prepared = _prepare_plot_data(report, arrays)
    assert [state["iteration"] for state in prepared["states"]] == [0, 4]
    assert prepared["curves"][2] == []
    assert _prepare_plot_data({"cases": []}, {})["states"] == []


def test_missing_persisted_state_cannot_be_replaced_by_interpolation():
    report, arrays = saved_inputs()
    arrays.pop(FINE_CASE + "_u_2")
    with pytest.raises(KeyError):
        _prepare_plot_data(report, arrays)


def test_saved_history_disagreement_is_an_error():
    report, arrays = saved_inputs()
    report["iterate_diagnostics"][FINE_CASE].pop()
    with pytest.raises(ValueError, match="agree exactly"):
        _prepare_plot_data(report, arrays)


def test_absent_real_midplane_is_not_interpolated_into_existence():
    report, arrays = saved_inputs()
    arrays[FINE_CASE + "_coordinates"][:, 2] = .25
    with pytest.raises(ValueError, match="saved-node slice"):
        _prepare_plot_data(report, arrays)


def test_failed_qualification_errors_are_retained_with_actual_cost():
    report = {"cases": [{"kind": "mms", "u_degree": 3, "p_degree": 1, "n": 8,
                         "equilibrium": "passed", "qualification": "failed", "DOF": 12345,
                         "metrics": {"relative_u_H1": .4, "relative_pressure_L2": .2}}]}
    prepared = _prepare_plot_data(report, {})
    assert prepared["curves"][1] == [{"n": 8, "DOF": 12345.,
                                    "errors": {"relative_u_H1": .4, "relative_pressure_L2": .2}}]


@pytest.mark.parametrize("value", [float("nan"), float("inf"), -.1])
def test_invalid_errors_fail_instead_of_being_silently_dropped(value):
    report = {"cases": [{"kind": "mms", "u_degree": 3, "p_degree": 2, "n": 2,
                         "equilibrium": "passed", "DOF": 100,
                         "metrics": {"relative_u_H1": value}}]}
    with pytest.raises(ValueError, match="finite and nonnegative"):
        _prepare_plot_data(report, {})
