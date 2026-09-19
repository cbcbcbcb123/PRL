"""Pure in-memory notebook construction checks, without initializing a package."""

import ast

from prl.runs.mixed_cube_representation_figure import _notebook_payload


def test_notebook_uses_copied_inputs_and_editable_exploration_parameters():
    hashes = {role: "a" * 64 for role in ("report", "states", "renderer", "style")}
    notebook = _notebook_payload("FigR2_mixed_cube_representation_v01_20260919", hashes)
    code = "\n".join(cell["source"] for cell in notebook["cells"] if cell["cell_type"] == "code")
    ast.parse(code)
    assert 'axis_box_size_in = (4.0, 4.0)' in code
    assert 'deformation_scale = 30.0' in code
    assert 'export_dpi = 160' in code
    assert 'DPI = export_dpi' in code
    assert 'FIGURE_SIZE_IN =' in code
    assert 'PRIMARY_DATA = REVISION_DIR /' in code
    assert 'STATE_DATA = REVISION_DIR /' in code
    assert 'RENDERER_SOURCE = REVISION_DIR /' in code
    assert 'STYLE_SOURCE_FILE = REVISION_DIR /' in code
    assert 'allow_pickle=False' in code
    assert 'subprocess' not in code
    assert 'prl.' not in code
    assert all(cell.get("execution_count") is None for cell in notebook["cells"])
    assert all(not cell.get("outputs") for cell in notebook["cells"])
    assert notebook["cells"][-1]["source"].rstrip().endswith('display(Image(filename=str(OUTPUT_PNG)))')


def test_stronger_safety_qualification_is_displayed_without_changing_original_report():
    notebook = _notebook_payload("FigR2_mixed_cube_representation_v01_20260919", {})
    source = next(cell["source"] for cell in notebook["cells"] if cell["id"] == "read-data")
    assert "PLOT_REPORT = deepcopy(REPORT)" in source
    assert 'REPORT.get("candidate_k100_qualification", {})' in source
    assert '["status"] = qualified["status"]' in source
    assert "write_text" not in source
