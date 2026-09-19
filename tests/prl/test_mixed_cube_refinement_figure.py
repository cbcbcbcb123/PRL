import ast

from prl.runs.mixed_cube_refinement_figure import _notebook_payload


def test_portable_notebook_uses_only_copied_inputs_and_keeps_required_export_parameters():
    notebook = _notebook_payload("FigR3_mixed_cube_refinement_v01_20260919",
                                 {role: "a" * 64 for role in ("report", "states", "renderer", "style")})
    code = "\n".join(cell["source"] for cell in notebook["cells"] if cell["cell_type"] == "code")
    ast.parse(code)
    for name in ("PRIMARY_DATA", "STATE_DATA", "RENDERER_SOURCE", "STYLE_SOURCE_FILE"):
        assert f"{name} = REVISION_DIR /" in code
    assert "DPI = export_dpi" in code
    assert "FIGURE_SIZE_IN =" in code
    assert "axis_box_size_in = (4.0, 4.0)" in code
    assert "deformation_scale = 30.0" in code
    assert "export_dpi = 160" in code
    assert "allow_pickle=False" in code
    assert "subprocess" not in code and "prl." not in code
    assert all(cell.get("execution_count") is None for cell in notebook["cells"])
    assert all(not cell.get("outputs") for cell in notebook["cells"])
    assert notebook["cells"][-1]["source"].rstrip().endswith("display(Image(filename=str(OUTPUT_PNG)))")


def test_notebook_describes_the_frozen_scope_and_does_not_rewrite_report():
    notebook = _notebook_payload("FigR3_mixed_cube_refinement_v01_20260919", {})
    markdown = "\n".join(cell["source"] for cell in notebook["cells"] if cell["cell_type"] == "markdown")
    assert "8→12" in markdown and "ln(12/8)" in markdown and "3.5/2.5/2.5" in markdown
    assert "不是生理时间" in markdown
    read = next(cell["source"] for cell in notebook["cells"] if cell["id"] == "read-data")
    assert "write_text" not in read
    assert "candidate_k100_qualification" not in read
