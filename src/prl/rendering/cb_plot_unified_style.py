"""Reusable Matplotlib helpers for the CB unified quantitative-figure style.

Copy this module into a figure project, then retain the StyleSpec and any
StyleOverride records in the notebook's Chinese "作图调整参数" cell.
"""

from __future__ import annotations

import json
import math
import re
from dataclasses import asdict, dataclass, fields
from pathlib import Path
from typing import Iterable, Sequence

import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib import colors as mcolors
from matplotlib import font_manager
from matplotlib.axes import Axes
from matplotlib.figure import Figure
from matplotlib.transforms import Bbox


DEFAULT_AXIS_BOX_SIZE_IN = (6.0, 5.0)
STANDARD_AXIS_BOX_SIZE_OPTIONS_IN = (
    (5.0, 5.0),
    (6.0, 5.0),
    (10.0, 5.0),
)
FONT_CANDIDATES = ("Calibri", "Arial", "Helvetica", "DejaVu Sans")
DEFAULT_EXPORT_DPI = 600
TOP_INFORMATION_MIN_MARGIN_IN = 0.35
LEGEND_INSIDE_LOCATIONS = (
    "upper right",
    "upper left",
    "lower right",
    "lower left",
    "center right",
    "center left",
    "upper center",
    "lower center",
)
LEGEND_OVERLAP_PADDING_PT = 2.0
CANVAS_CONTENT_MIN_CLEARANCE_PT = 12.0
STATISTICAL_TEXT_TOP_SPINE_MIN_CLEARANCE_PT = 8.0


@dataclass(frozen=True)
class StyleSpec:
    """Visual defaults for one or more quantitative axes."""

    axis_box_size_in: tuple[float, float] = DEFAULT_AXIS_BOX_SIZE_IN
    tick_label_size: float = 34.0
    axis_label_size: float = 38.0
    annotation_font_size: float = 32.0
    sample_size_and_stat_font_size: float = 30.0
    in_axes_title_size: float = 32.0
    legend_font_size: float = 30.0
    axes_line_width: float = 4.0
    major_tick_length_pt: float = 10.5
    major_tick_width_pt: float = 2.0
    minor_tick_length_pt: float = 7.0
    minor_tick_width_pt: float = 2.0
    data_line_width: float = 3.0
    significance_bracket_line_width: float = 3.0
    tick_label_pad_pt: float = 6.0
    axis_label_pad_pt: float = 18.0
    export_dpi: int = DEFAULT_EXPORT_DPI
    axis_box_tolerance_in: float = 0.02
    font_candidates: tuple[str, ...] = FONT_CANDIDATES
    show_minor_ticks: bool = True
    use_in_axes_title: bool = False


@dataclass(frozen=True)
class StyleOverride:
    """Document one non-default visual field and its scientific/layout reason."""

    field: str
    reason: str


@dataclass(frozen=True)
class ValidationResult:
    """A serializable result from validate_figure."""

    passed: bool
    issues: tuple[str, ...]
    warnings: tuple[str, ...]
    measured_axes_in: tuple[dict[str, float], ...]
    selected_font: str
    required_canvas_clearance_pt: float
    measured_minimum_canvas_clearance_pt: float | None

    def as_dict(self) -> dict[str, object]:
        return {
            "passed": self.passed,
            "issues": list(self.issues),
            "warnings": list(self.warnings),
            "measured_axes_in": list(self.measured_axes_in),
            "selected_font": self.selected_font,
            "required_canvas_clearance_pt": self.required_canvas_clearance_pt,
            "measured_minimum_canvas_clearance_pt": self.measured_minimum_canvas_clearance_pt,
        }


@dataclass(frozen=True)
class ExportPaths:
    png: Path
    svg: Path
    manifest: Path
    validation: ValidationResult


class StyleValidationError(ValueError):
    """Raise when a figure cannot be exported as a compliant style artifact."""


DEFAULT_STYLE = StyleSpec()


def is_standard_axis_box_size(axis_box_size_in: Sequence[float]) -> bool:
    """Return whether the axis box matches one of the confirmed standard choices."""

    if len(axis_box_size_in) != 2:
        return False
    return any(
        _is_close(axis_box_size_in[0], option[0])
        and _is_close(axis_box_size_in[1], option[1])
        for option in STANDARD_AXIS_BOX_SIZE_OPTIONS_IN
    )


VISUAL_STYLE_FIELDS = frozenset(
    {
        "axis_box_size_in",
        "tick_label_size",
        "axis_label_size",
        "annotation_font_size",
        "sample_size_and_stat_font_size",
        "in_axes_title_size",
        "legend_font_size",
        "axes_line_width",
        "major_tick_length_pt",
        "major_tick_width_pt",
        "minor_tick_length_pt",
        "minor_tick_width_pt",
        "data_line_width",
        "significance_bracket_line_width",
        "tick_label_pad_pt",
        "axis_label_pad_pt",
        "export_dpi",
        "show_minor_ticks",
        "use_in_axes_title",
    }
)


def resolve_font_family(candidates: Sequence[str] = FONT_CANDIDATES) -> str:
    """Return the first installed font from the ordered fallback list."""

    for candidate in candidates:
        try:
            font_manager.findfont(
                font_manager.FontProperties(family=candidate),
                fallback_to_default=False,
            )
        except ValueError:
            continue
        return candidate
    return "DejaVu Sans"


_STATISTICAL_TEXT_PATTERN = re.compile(
    r"^(?:n\s*[=:]|[pq]\s*(?:[=<>]|value)|\*{1,4}|n\.?s\.?$)",
    flags=re.IGNORECASE,
)


def _configure_typography_rcparams(style: StyleSpec) -> str:
    """Configure global Matplotlib defaults and return the selected font."""

    selected_font = resolve_font_family(style.font_candidates)
    fallback_fonts = [selected_font] + [
        candidate for candidate in style.font_candidates if candidate != selected_font
    ]
    mpl.rcParams.update(
        {
            "font.family": "sans-serif",
            "font.sans-serif": fallback_fonts,
            "mathtext.fontset": "dejavusans",
            "font.size": style.tick_label_size,
            "axes.labelsize": style.axis_label_size,
            "xtick.labelsize": style.tick_label_size,
            "ytick.labelsize": style.tick_label_size,
            "legend.fontsize": style.legend_font_size,
            "legend.title_fontsize": style.legend_font_size,
            "svg.fonttype": "none",
        }
    )
    return selected_font


def _set_text_typography(
    text: object,
    *,
    selected_font: str,
    font_size: float,
    font_weight: str = "normal",
) -> None:
    """Set a Matplotlib Text artist's final font properties."""

    text.set_fontfamily(selected_font)
    text.set_fontsize(font_size)
    text.set_fontweight(font_weight)


def _is_top_information_text(axis: Axes, text: object) -> bool:
    return (
        text.get_transform() == axis.transAxes
        and float(text.get_position()[1]) > 1.0
    )


def _expected_axes_text_size(axis: Axes, text: object, style: StyleSpec) -> float:
    if _is_top_information_text(axis, text):
        return style.sample_size_and_stat_font_size
    if _STATISTICAL_TEXT_PATTERN.match(text.get_text().strip()):
        return style.sample_size_and_stat_font_size
    return style.annotation_font_size


def _apply_legend_typography(legend: object, style: StyleSpec, selected_font: str) -> None:
    if legend is None:
        return
    for text in [*legend.get_texts(), legend.get_title()]:
        _set_text_typography(
            text,
            selected_font=selected_font,
            font_size=style.legend_font_size,
        )


def _normalize_axes(axes: Axes | Iterable[Axes]) -> list[Axes]:
    if isinstance(axes, Axes):
        return [axes]
    normalized = list(axes)
    if not normalized or any(not isinstance(axis, Axes) for axis in normalized):
        raise TypeError("axes must be a Matplotlib Axes or a non-empty iterable of Axes.")
    return normalized


def _normalize_overrides(overrides: Iterable[StyleOverride]) -> list[StyleOverride]:
    normalized = list(overrides)
    if any(not isinstance(item, StyleOverride) for item in normalized):
        raise TypeError("overrides must contain only StyleOverride instances.")
    return normalized


def _is_close(left: float, right: float, tolerance: float = 0.01) -> bool:
    return math.isclose(float(left), float(right), abs_tol=tolerance, rel_tol=0.0)


def _expanded_display_bbox(bbox: Bbox, padding_px: float) -> Bbox:
    return Bbox.from_extents(
        bbox.x0 - padding_px,
        bbox.y0 - padding_px,
        bbox.x1 + padding_px,
        bbox.y1 + padding_px,
    )


def _bbox_has_area(bbox: Bbox) -> bool:
    return (
        all(math.isfinite(float(value)) for value in bbox.extents)
        and bbox.width > 0
        and bbox.height > 0
    )


def _bbox_inside(inner: Bbox, outer: Bbox, tolerance_px: float = 0.5) -> bool:
    return (
        inner.x0 >= outer.x0 - tolerance_px
        and inner.y0 >= outer.y0 - tolerance_px
        and inner.x1 <= outer.x1 + tolerance_px
        and inner.y1 <= outer.y1 + tolerance_px
    )


def _point_in_bbox(point: tuple[float, float], bbox: Bbox) -> bool:
    return bbox.x0 <= point[0] <= bbox.x1 and bbox.y0 <= point[1] <= bbox.y1


def _point_on_segment(
    point: tuple[float, float],
    start: tuple[float, float],
    end: tuple[float, float],
) -> bool:
    return (
        min(start[0], end[0]) - 1e-9 <= point[0] <= max(start[0], end[0]) + 1e-9
        and min(start[1], end[1]) - 1e-9 <= point[1] <= max(start[1], end[1]) + 1e-9
    )


def _segment_direction(
    start: tuple[float, float],
    end: tuple[float, float],
    point: tuple[float, float],
) -> float:
    return (end[0] - start[0]) * (point[1] - start[1]) - (
        end[1] - start[1]
    ) * (point[0] - start[0])


def _segments_intersect(
    first_start: tuple[float, float],
    first_end: tuple[float, float],
    second_start: tuple[float, float],
    second_end: tuple[float, float],
) -> bool:
    first_direction = _segment_direction(first_start, first_end, second_start)
    second_direction = _segment_direction(first_start, first_end, second_end)
    third_direction = _segment_direction(second_start, second_end, first_start)
    fourth_direction = _segment_direction(second_start, second_end, first_end)

    if (
        (first_direction > 0 > second_direction or first_direction < 0 < second_direction)
        and (third_direction > 0 > fourth_direction or third_direction < 0 < fourth_direction)
    ):
        return True
    if abs(first_direction) <= 1e-9 and _point_on_segment(
        second_start, first_start, first_end
    ):
        return True
    if abs(second_direction) <= 1e-9 and _point_on_segment(
        second_end, first_start, first_end
    ):
        return True
    if abs(third_direction) <= 1e-9 and _point_on_segment(
        first_start, second_start, second_end
    ):
        return True
    if abs(fourth_direction) <= 1e-9 and _point_on_segment(
        first_end, second_start, second_end
    ):
        return True
    return False


def _line_segment_intersects_bbox(
    start: tuple[float, float],
    end: tuple[float, float],
    bbox: Bbox,
) -> bool:
    if _point_in_bbox(start, bbox) or _point_in_bbox(end, bbox):
        return True
    corners = (
        (bbox.x0, bbox.y0),
        (bbox.x1, bbox.y0),
        (bbox.x1, bbox.y1),
        (bbox.x0, bbox.y1),
    )
    edges = zip(corners, (*corners[1:], corners[0]))
    return any(
        _segments_intersect(start, end, edge_start, edge_end)
        for edge_start, edge_end in edges
    )


def _line_overlaps_bbox(line: object, bbox: Bbox) -> bool:
    if not line.get_visible():
        return False
    try:
        path = line.get_path().transformed(line.get_transform())
    except (AttributeError, RuntimeError, TypeError, ValueError):
        return False

    previous_point: tuple[float, float] | None = None
    for vertex in path.vertices:
        point = (float(vertex[0]), float(vertex[1]))
        if not all(math.isfinite(value) for value in point):
            previous_point = None
            continue
        if _point_in_bbox(point, bbox):
            return True
        if previous_point is not None and _line_segment_intersects_bbox(
            previous_point, point, bbox
        ):
            return True
        previous_point = point
    return False


def _artist_bbox_overlaps(artist: object, bbox: Bbox, renderer: object) -> bool:
    if not artist.get_visible():
        return False
    try:
        artist_bbox = artist.get_window_extent(renderer=renderer)
    except (AttributeError, RuntimeError, TypeError, ValueError):
        return False
    return _bbox_has_area(artist_bbox) and artist_bbox.overlaps(bbox)


def _collection_offsets_overlap_bbox(collection: object, bbox: Bbox, renderer: object) -> bool:
    if not collection.get_visible():
        return False
    try:
        offsets = collection.get_offsets()
        if len(offsets) == 0:
            return _artist_bbox_overlaps(collection, bbox, renderer)
        points = collection.get_offset_transform().transform(offsets)
    except (AttributeError, RuntimeError, TypeError, ValueError):
        return _artist_bbox_overlaps(collection, bbox, renderer)

    for raw_point in points:
        try:
            point = (float(raw_point[0]), float(raw_point[1]))
        except (TypeError, ValueError):
            continue
        if all(math.isfinite(value) for value in point) and _point_in_bbox(point, bbox):
            return True
    return False


def _legend_overlaps_data(
    axis: Axes,
    legend: object,
    renderer: object,
    *,
    padding_px: float,
) -> bool:
    legend_bbox = _expanded_display_bbox(
        legend.get_window_extent(renderer=renderer),
        padding_px,
    )
    for line in axis.get_lines():
        if _line_overlaps_bbox(line, legend_bbox):
            return True
    for collection in axis.collections:
        if _collection_offsets_overlap_bbox(collection, legend_bbox, renderer):
            return True
    for patch in axis.patches:
        if _artist_bbox_overlaps(patch, legend_bbox, renderer):
            return True
    for image in axis.images:
        if _artist_bbox_overlaps(image, legend_bbox, renderer):
            return True
    return False


def relocate_legend_inside_if_clear(
    axis: Axes,
    *,
    style: StyleSpec = DEFAULT_STYLE,
    candidate_locations: Sequence[str] = LEGEND_INSIDE_LOCATIONS,
) -> bool:
    """Move an axes legend inside the frame when it does not overlap data."""

    legend = axis.get_legend()
    if legend is None:
        return False

    figure = axis.figure
    original_location = getattr(legend, "_loc", None)
    original_bbox_to_anchor = getattr(legend, "_bbox_to_anchor", None)
    padding_px = LEGEND_OVERLAP_PADDING_PT * figure.dpi / 72.0

    for location in candidate_locations:
        legend.set_bbox_to_anchor((0.0, 0.0, 1.0, 1.0), transform=axis.transAxes)
        legend.set_loc(location)
        figure.canvas.draw()
        renderer = figure.canvas.get_renderer()
        legend_bbox = legend.get_window_extent(renderer=renderer)
        axis_bbox = axis.get_window_extent(renderer=renderer)
        if not _bbox_inside(legend_bbox, axis_bbox):
            continue
        if not _legend_overlaps_data(axis, legend, renderer, padding_px=padding_px):
            return True

    if original_location is not None:
        legend.set_loc(original_location)
    setattr(legend, "_bbox_to_anchor", original_bbox_to_anchor)
    figure.canvas.draw()
    return False


def _axis_top_margin_in(axis: Axes) -> float:
    position = axis.get_position()
    return (1.0 - position.y1) * axis.figure.get_figheight()


def create_figure_with_axis_box(
    *,
    style: StyleSpec = DEFAULT_STYLE,
    margins_in: tuple[float, float, float, float] = (1.35, 0.35, 1.15, 0.95),
) -> tuple[Figure, Axes]:
    """Create one axes whose rendered box is explicitly sized in inches.

    margins_in is ordered as left, right, bottom, top. Increase margins before
    adding labels, legends, or top information; do not allow an auto-layout
    engine to shrink the requested axis box.
    """

    if len(margins_in) != 4 or any(value < 0 for value in margins_in):
        raise ValueError("margins_in must contain four non-negative values.")
    axis_width, axis_height = style.axis_box_size_in
    if axis_width <= 0 or axis_height <= 0:
        raise ValueError("axis_box_size_in values must be positive.")

    left, right, bottom, top = margins_in
    figure_width = left + axis_width + right
    figure_height = bottom + axis_height + top
    figure = plt.figure(figsize=(figure_width, figure_height), constrained_layout=False)
    axis = figure.add_axes(
        (
            left / figure_width,
            bottom / figure_height,
            axis_width / figure_width,
            axis_height / figure_height,
        )
    )
    apply_axes_style(axis, style=style)
    return figure, axis


def apply_axes_style(
    axis: Axes,
    *,
    style: StyleSpec = DEFAULT_STYLE,
    xlabel: str | None = None,
    ylabel: str | None = None,
    show_grid: bool = False,
) -> str:
    """Apply the unified style to one axes and return the selected font family."""

    selected_font = _configure_typography_rcparams(style)
    mpl.rcParams.update(
        {
            "axes.linewidth": style.axes_line_width,
            "axes.spines.top": True,
            "axes.spines.right": True,
            "axes.grid": False,
            "xtick.direction": "out",
            "ytick.direction": "out",
            "xtick.minor.visible": style.show_minor_ticks,
            "ytick.minor.visible": style.show_minor_ticks,
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
            "figure.facecolor": "#FFFFFF",
            "axes.facecolor": "#FFFFFF",
            "savefig.facecolor": "#FFFFFF",
            "savefig.edgecolor": "#FFFFFF",
            "savefig.dpi": style.export_dpi,
        }
    )
    if xlabel is not None:
        axis.set_xlabel(xlabel)
    if ylabel is not None:
        axis.set_ylabel(ylabel)

    axis.set_box_aspect(style.axis_box_size_in[1] / style.axis_box_size_in[0])
    for spine in axis.spines.values():
        spine.set_visible(True)
        spine.set_color("#000000")
        spine.set_linewidth(style.axes_line_width)

    if style.show_minor_ticks:
        axis.minorticks_on()
    else:
        axis.minorticks_off()
    axis.tick_params(
        axis="both",
        which="major",
        direction="out",
        width=style.major_tick_width_pt,
        length=style.major_tick_length_pt,
        pad=style.tick_label_pad_pt,
        top=True,
        right=True,
        labeltop=False,
        labelright=False,
        labelsize=style.tick_label_size,
    )
    axis.tick_params(
        axis="both",
        which="minor",
        direction="out",
        width=style.minor_tick_width_pt,
        length=style.minor_tick_length_pt,
        top=True,
        right=True,
        bottom=True,
        left=True,
    )
    if show_grid:
        axis.grid(
            True,
            color="#D0D0D0",
            linewidth=0.7,
            alpha=0.75,
        )
    else:
        axis.grid(False)
    for label in (axis.xaxis.label, axis.yaxis.label):
        label.set_fontsize(style.axis_label_size)
        label.set_fontfamily(selected_font)
        label.set_fontweight("normal")
    axis.xaxis.labelpad = style.axis_label_pad_pt
    axis.yaxis.labelpad = style.axis_label_pad_pt
    if axis.title.get_text():
        _set_text_typography(
            axis.title,
            selected_font=selected_font,
            font_size=style.in_axes_title_size,
        )
    for tick_label in [*axis.get_xticklabels(), *axis.get_yticklabels()]:
        tick_label.set_fontsize(style.tick_label_size)
        tick_label.set_fontfamily(selected_font)
        tick_label.set_fontweight("normal")

    axis.figure._cb_plot_unified_style_font = selected_font
    return selected_font


def enforce_figure_typography(
    figure: Figure,
    axes: Axes | Iterable[Axes],
    *,
    style: StyleSpec = DEFAULT_STYLE,
) -> str:
    """Normalize final visible text before validation and export.

    Apply this automatically from export_figure. It deliberately overwrites
    manual font sizes so final SVG and PNG exports follow StyleSpec.
    """

    normalized_axes = _normalize_axes(axes)
    selected_font = _configure_typography_rcparams(style)
    for axis in normalized_axes:
        for label in (axis.xaxis.label, axis.yaxis.label):
            _set_text_typography(
                label,
                selected_font=selected_font,
                font_size=style.axis_label_size,
            )
        axis.xaxis.labelpad = style.axis_label_pad_pt
        axis.yaxis.labelpad = style.axis_label_pad_pt
        for tick_label in [*axis.get_xticklabels(), *axis.get_yticklabels()]:
            _set_text_typography(
                tick_label,
                selected_font=selected_font,
                font_size=style.tick_label_size,
            )
        if axis.title.get_text():
            _set_text_typography(
                axis.title,
                selected_font=selected_font,
                font_size=style.in_axes_title_size,
            )
        for text in axis.texts:
            _set_text_typography(
                text,
                selected_font=selected_font,
                font_size=_expected_axes_text_size(axis, text, style),
            )
        legend = axis.get_legend()
        _apply_legend_typography(legend, style, selected_font)
        relocate_legend_inside_if_clear(axis, style=style)

    for legend in figure.legends:
        _apply_legend_typography(legend, style, selected_font)
    for text in figure.texts:
        _set_text_typography(
            text,
            selected_font=selected_font,
            font_size=style.annotation_font_size,
        )

    figure._cb_plot_unified_style_font = selected_font
    return selected_font


def add_top_information(
    axis: Axes,
    text: str,
    *,
    style: StyleSpec = DEFAULT_STYLE,
    x: float = 0.0,
    y: float = 1.03,
    ha: str = "left",
) -> object:
    """Add text above the data region after confirming adequate top margin."""

    if y <= 1.0:
        raise ValueError("Top information must use an axes-coordinate y value above 1.0.")
    if _axis_top_margin_in(axis) < TOP_INFORMATION_MIN_MARGIN_IN:
        raise ValueError(
            "Reserve more top canvas margin before adding a top information band."
        )
    return axis.text(
        x,
        y,
        text,
        transform=axis.transAxes,
        clip_on=False,
        ha=ha,
        va="bottom",
        fontsize=style.sample_size_and_stat_font_size,
        fontweight="normal",
    )


def set_in_axes_title(
    axis: Axes,
    text: str,
    *,
    style: StyleSpec,
) -> object:
    """Set the allowed 32 pt regular in-axes title for an explicit exception."""

    if not style.use_in_axes_title:
        raise StyleValidationError(
            "Set StyleSpec(use_in_axes_title=True) and record its override reason "
            "before adding an in-axes title."
        )
    return axis.set_title(
        text,
        fontsize=style.in_axes_title_size,
        fontweight="normal",
    )


def data_line_kwargs(style: StyleSpec = DEFAULT_STYLE) -> dict[str, float]:
    """Return the default line-width keyword for quantitative data marks."""

    return {"linewidth": style.data_line_width}


def significance_bracket_kwargs(style: StyleSpec = DEFAULT_STYLE) -> dict[str, float]:
    """Return the default line-width keyword for significance brackets."""

    return {"linewidth": style.significance_bracket_line_width}


def measure_axes_box_inches(axis: Axes) -> tuple[float, float]:
    """Render and return the physical width and height of an axes box."""

    figure = axis.figure
    figure.canvas.draw()
    renderer = figure.canvas.get_renderer()
    bounds = axis.get_window_extent(renderer=renderer)
    return bounds.width / figure.dpi, bounds.height / figure.dpi


def _override_issues(
    style: StyleSpec,
    overrides: Sequence[StyleOverride],
) -> list[str]:
    issues: list[str] = []
    override_fields: set[str] = set()
    for record in overrides:
        if not record.field.strip():
            issues.append("A StyleOverride field must be non-empty.")
        if not record.reason.strip():
            issues.append(f"StyleOverride {record.field!r} is missing a reason.")
        override_fields.add(record.field)

    for descriptor in fields(StyleSpec):
        field_name = descriptor.name
        if field_name not in VISUAL_STYLE_FIELDS:
            continue
        if field_name == "axis_box_size_in" and is_standard_axis_box_size(
            getattr(style, field_name)
        ):
            continue
        if getattr(style, field_name) != getattr(DEFAULT_STYLE, field_name):
            if field_name not in override_fields:
                issues.append(
                    f"Non-default StyleSpec.{field_name} requires a StyleOverride reason."
                )
    return issues


def _color_matches_black(color: object) -> bool:
    actual = mcolors.to_rgba(color)
    expected = mcolors.to_rgba("#000000")
    return all(
        _is_close(current, target, tolerance=0.02)
        for current, target in zip(actual, expected)
    )


def _visible_layout_texts(
    figure: Figure,
    axes: Sequence[Axes],
) -> list[tuple[str, object]]:
    """Return unique visible text artists that must fit inside the canvas."""

    collected: list[tuple[str, object]] = []
    seen: set[int] = set()

    def collect(owner: str, text: object) -> None:
        if id(text) in seen:
            return
        if not text.get_visible() or not text.get_text().strip():
            return
        seen.add(id(text))
        collected.append((owner, text))

    for index, axis in enumerate(axes, start=1):
        collect(f"Axes {index} x-axis label", axis.xaxis.label)
        collect(f"Axes {index} y-axis label", axis.yaxis.label)
        collect(f"Axes {index} title", axis.title)
        collect(f"Axes {index} x-axis offset", axis.xaxis.get_offset_text())
        collect(f"Axes {index} y-axis offset", axis.yaxis.get_offset_text())
        for tick_label in [*axis.get_xticklabels(), *axis.get_yticklabels()]:
            collect(f"Axes {index} tick label", tick_label)
        for text in axis.texts:
            collect(f"Axes {index} annotation", text)
        legend = axis.get_legend()
        if legend is not None:
            for text in [*legend.get_texts(), legend.get_title()]:
                collect(f"Axes {index} legend", text)

    for text in figure.texts:
        collect("Figure annotation", text)
    for legend in figure.legends:
        for text in [*legend.get_texts(), legend.get_title()]:
            collect("Figure legend", text)
    return collected


def _all_layout_axes(figure: Figure, primary_axes: Sequence[Axes]) -> list[Axes]:
    """Return primary and auxiliary axes, including colorbar axes, once each."""

    collected: list[Axes] = []
    seen: set[int] = set()
    for axis in [*primary_axes, *figure.axes]:
        if id(axis) in seen:
            continue
        seen.add(id(axis))
        collected.append(axis)
    return collected


def _rendered_layout_issues(
    figure: Figure,
    axes: Sequence[Axes],
) -> tuple[list[str], float | None]:
    """Check all rendered layout content against canvas edges and top spines."""

    figure.canvas.draw()
    renderer = figure.canvas.get_renderer()
    figure_bounds = figure.bbox
    canvas_clearance_px = (
        CANVAS_CONTENT_MIN_CLEARANCE_PT * figure.dpi / 72.0
    )
    top_spine_clearance_px = (
        STATISTICAL_TEXT_TOP_SPINE_MIN_CLEARANCE_PT
        * figure.dpi
        / 72.0
    )
    issues: list[str] = []
    measured_minimum_clearance_pt: float | None = None
    layout_axes = _all_layout_axes(figure, axes)

    def check_bounds(owner: str, bounds: Bbox) -> None:
        nonlocal measured_minimum_clearance_pt
        if not all(math.isfinite(value) for value in bounds.extents):
            issues.append(f"{owner} has invalid bounds.")
            return
        clearances_px = (
            bounds.x0 - figure_bounds.x0,
            figure_bounds.x1 - bounds.x1,
            bounds.y0 - figure_bounds.y0,
            figure_bounds.y1 - bounds.y1,
        )
        minimum_clearance_pt = min(clearances_px) * 72.0 / figure.dpi
        if (
            measured_minimum_clearance_pt is None
            or minimum_clearance_pt < measured_minimum_clearance_pt
        ):
            measured_minimum_clearance_pt = minimum_clearance_pt
        if min(clearances_px) < canvas_clearance_px:
            issues.append(
                f"{owner} is clipped or only {minimum_clearance_pt:.1f} pt "
                "from the canvas edge; require at least "
                f"{CANVAS_CONTENT_MIN_CLEARANCE_PT:g} pt. Expand the total "
                "canvas margin without shrinking the confirmed main axis box."
            )

    for index, axis in enumerate(layout_axes, start=1):
        check_bounds(
            f"Figure axes {index} frame",
            axis.get_window_extent(renderer=renderer),
        )

    for owner, text in _visible_layout_texts(figure, layout_axes):
        bounds = text.get_window_extent(renderer=renderer)
        check_bounds(f"{owner} {text.get_text()!r}", bounds)

    for index, axis in enumerate(layout_axes, start=1):
        legend = axis.get_legend()
        if legend is not None and legend.get_visible():
            check_bounds(
                f"Figure axes {index} legend",
                legend.get_window_extent(renderer=renderer),
            )
        for artist in [
            *axis.lines,
            *axis.patches,
            *axis.collections,
            *axis.images,
            *axis.artists,
        ]:
            if not artist.get_visible() or artist.get_clip_on():
                continue
            try:
                bounds = artist.get_window_extent(renderer=renderer)
            except (AttributeError, RuntimeError, TypeError, ValueError):
                continue
            if _bbox_has_area(bounds):
                check_bounds(f"Figure axes {index} unclipped artist", bounds)

    for index, legend in enumerate(figure.legends, start=1):
        if legend.get_visible():
            check_bounds(
                f"Figure-level legend {index}",
                legend.get_window_extent(renderer=renderer),
            )
    for index, artist in enumerate(
        [*figure.lines, *figure.patches, *figure.artists], start=1
    ):
        if not artist.get_visible():
            continue
        try:
            bounds = artist.get_window_extent(renderer=renderer)
        except (AttributeError, RuntimeError, TypeError, ValueError):
            continue
        if _bbox_has_area(bounds):
            check_bounds(f"Figure-level artist {index}", bounds)

    for index, axis in enumerate(axes, start=1):
        axis_bounds = axis.get_window_extent(renderer=renderer)
        for text in axis.texts:
            label = text.get_text().strip()
            if (
                not text.get_visible()
                or not label
                or not _STATISTICAL_TEXT_PATTERN.match(label)
            ):
                continue
            bounds = text.get_window_extent(renderer=renderer)
            overlaps_axis_horizontally = (
                bounds.x1 > axis_bounds.x0 and bounds.x0 < axis_bounds.x1
            )
            overlaps_axis_vertically = (
                bounds.y1 > axis_bounds.y0 and bounds.y0 < axis_bounds.y1
            )
            if not overlaps_axis_horizontally or not overlaps_axis_vertically:
                continue
            top_clearance_px = axis_bounds.y1 - bounds.y1
            if top_clearance_px < top_spine_clearance_px:
                top_clearance_pt = top_clearance_px * 72.0 / figure.dpi
                issues.append(
                    f"Axes {index} statistical annotation {label!r} is only "
                    f"{top_clearance_pt:.1f} pt below the top spine; "
                    "move it downward or add y-range headroom to provide at "
                    f"least {STATISTICAL_TEXT_TOP_SPINE_MIN_CLEARANCE_PT:g} pt."
                )
    return issues, measured_minimum_clearance_pt


def validate_figure(
    figure: Figure,
    axes: Axes | Iterable[Axes],
    *,
    style: StyleSpec = DEFAULT_STYLE,
    overrides: Iterable[StyleOverride] = (),
) -> ValidationResult:
    """Validate geometry and core style settings without writing files."""

    normalized_axes = _normalize_axes(axes)
    normalized_overrides = _normalize_overrides(overrides)
    issues = _override_issues(style, normalized_overrides)
    warnings: list[str] = []
    measurements: list[dict[str, float]] = []
    selected_font = getattr(
        figure,
        "_cb_plot_unified_style_font",
        resolve_font_family(style.font_candidates),
    )

    for index, axis in enumerate(normalized_axes, start=1):
        width, height = measure_axes_box_inches(axis)
        measurements.append(
            {
                "axis_index": float(index),
                "width_in": round(width, 4),
                "height_in": round(height, 4),
                "expected_width_in": style.axis_box_size_in[0],
                "expected_height_in": style.axis_box_size_in[1],
            }
        )
        if not _is_close(width, style.axis_box_size_in[0], style.axis_box_tolerance_in):
            issues.append(
                f"Axes {index} width is {width:.3f} in, expected "
                f"{style.axis_box_size_in[0]:.3f} in."
            )
        if not _is_close(height, style.axis_box_size_in[1], style.axis_box_tolerance_in):
            issues.append(
                f"Axes {index} height is {height:.3f} in, expected "
                f"{style.axis_box_size_in[1]:.3f} in."
            )

        for side, spine in axis.spines.items():
            if not spine.get_visible():
                issues.append(f"Axes {index} {side} spine is hidden.")
            if not _is_close(spine.get_linewidth(), style.axes_line_width):
                issues.append(
                    f"Axes {index} {side} spine width is not "
                    f"{style.axes_line_width:g} pt."
                )
            if not _color_matches_black(spine.get_edgecolor()):
                issues.append(f"Axes {index} {side} spine is not black.")

        for axis_object, name in ((axis.xaxis, "x"), (axis.yaxis, "y")):
            major = getattr(axis_object, "_major_tick_kw", {})
            if major.get("tickdir") != "out":
                issues.append(f"Axes {index} {name} major ticks are not outward.")
            if not _is_close(major.get("size", -1), style.major_tick_length_pt):
                issues.append(
                    f"Axes {index} {name} major tick length is not "
                    f"{style.major_tick_length_pt:g} pt."
                )
            if not _is_close(major.get("width", -1), style.major_tick_width_pt):
                issues.append(
                    f"Axes {index} {name} major tick width is not "
                    f"{style.major_tick_width_pt:g} pt."
                )
            minor = getattr(axis_object, "_minor_tick_kw", {})
            if minor.get("tickdir") != "out":
                issues.append(f"Axes {index} {name} minor ticks are not outward.")
            if not _is_close(minor.get("size", -1), style.minor_tick_length_pt):
                issues.append(
                    f"Axes {index} {name} minor tick length is not "
                    f"{style.minor_tick_length_pt:g} pt."
                )
            if not _is_close(minor.get("width", -1), style.minor_tick_width_pt):
                issues.append(
                    f"Axes {index} {name} minor tick width is not "
                    f"{style.minor_tick_width_pt:g} pt."
                )
            if style.show_minor_ticks:
                minor_tick_lines = axis_object.get_minorticklines()
                if not any(line.get_visible() for line in minor_tick_lines):
                    issues.append(f"Axes {index} {name} minor ticks are not visible.")

        for axis_object, label in (
            (axis.xaxis, axis.xaxis.label),
            (axis.yaxis, axis.yaxis.label),
        ):
            if label.get_text():
                if not _is_close(label.get_fontsize(), style.axis_label_size):
                    issues.append(
                        f"Axes {index} axis-label font size is not "
                        f"{style.axis_label_size:g} pt."
                    )
                if float(axis_object.labelpad) < style.axis_label_pad_pt:
                    issues.append(
                        f"Axes {index} axis-label pad is less than "
                        f"{style.axis_label_pad_pt:g} pt."
                    )
                if str(label.get_fontweight()).lower() != "normal":
                    issues.append(f"Axes {index} axis-label font weight is not normal.")
        for tick_label in [*axis.get_xticklabels(), *axis.get_yticklabels()]:
            if tick_label.get_visible() and tick_label.get_text():
                if not _is_close(tick_label.get_fontsize(), style.tick_label_size):
                    issues.append(
                        f"Axes {index} tick-label font size is not "
                        f"{style.tick_label_size:g} pt."
                    )
                if str(tick_label.get_fontweight()).lower() != "normal":
                    issues.append(
                        f"Axes {index} tick-label font weight is not normal."
                    )

        if axis.get_title().strip():
            if not style.use_in_axes_title:
                issues.append(f"Axes {index} has an in-axes title without an override.")
            elif not _is_close(axis.title.get_fontsize(), style.in_axes_title_size):
                issues.append(
                    f"Axes {index} in-axes title size is not "
                    f"{style.in_axes_title_size:g} pt."
                )
            elif str(axis.title.get_fontweight()).lower() != "normal":
                issues.append(f"Axes {index} in-axes title font weight is not normal.")

        for text in axis.texts:
            if not text.get_text():
                continue
            expected_size = _expected_axes_text_size(axis, text, style)
            if not _is_close(text.get_fontsize(), expected_size):
                issues.append(
                    f"Axes {index} annotation {text.get_text()!r} is not "
                    f"{expected_size:g} pt."
                )
            if str(text.get_fontweight()).lower() != "normal":
                issues.append(
                    f"Axes {index} annotation {text.get_text()!r} font weight is not normal."
                )

        legend = axis.get_legend()
        if legend is not None:
            for text in [*legend.get_texts(), legend.get_title()]:
                if not text.get_text():
                    continue
                if not _is_close(text.get_fontsize(), style.legend_font_size):
                    issues.append(
                        f"Axes {index} legend text is not "
                        f"{style.legend_font_size:g} pt."
                    )
                if str(text.get_fontweight()).lower() != "normal":
                    issues.append(f"Axes {index} legend text font weight is not normal.")
            renderer = figure.canvas.get_renderer()
            padding_px = LEGEND_OVERLAP_PADDING_PT * figure.dpi / 72.0
            if _legend_overlaps_data(axis, legend, renderer, padding_px=padding_px):
                warnings.append(
                    f"Axes {index} legend overlaps data marks; keep it outside "
                    "or use direct labels if no clear inside position exists."
                )

        for line in axis.get_lines():
            if not _is_close(line.get_linewidth(), style.data_line_width):
                warnings.append(
                    f"Axes {index} contains a data line not using the default "
                    f"{style.data_line_width:g} pt width."
                )

        visible_grid = any(
            line.get_visible()
            for line in [*axis.get_xgridlines(), *axis.get_ygridlines()]
        )
        if visible_grid and "show_grid" not in {
            record.field for record in normalized_overrides
        }:
            issues.append(
                f"Axes {index} shows grid lines without a StyleOverride reason."
            )

        has_top_band = any(
            text.get_transform() == axis.transAxes
            and float(text.get_position()[1]) > 1.0
            for text in axis.texts
        )
        if has_top_band and _axis_top_margin_in(axis) < TOP_INFORMATION_MIN_MARGIN_IN:
            issues.append(
                f"Axes {index} top information band has insufficient reserved margin."
            )

    for legend in figure.legends:
        for text in [*legend.get_texts(), legend.get_title()]:
            if not text.get_text():
                continue
            if not _is_close(text.get_fontsize(), style.legend_font_size):
                issues.append(
                    f"Figure legend text is not {style.legend_font_size:g} pt."
                )
            if str(text.get_fontweight()).lower() != "normal":
                issues.append("Figure legend text font weight is not normal.")

    for text in figure.texts:
        if not text.get_text():
            continue
        if not _is_close(text.get_fontsize(), style.annotation_font_size):
            issues.append(
                f"Figure text {text.get_text()!r} is not "
                f"{style.annotation_font_size:g} pt."
            )
        if str(text.get_fontweight()).lower() != "normal":
            issues.append(f"Figure text {text.get_text()!r} font weight is not normal.")

    layout_issues, measured_canvas_clearance_pt = _rendered_layout_issues(
        figure, normalized_axes
    )
    issues.extend(layout_issues)

    return ValidationResult(
        passed=not issues,
        issues=tuple(issues),
        warnings=tuple(warnings),
        measured_axes_in=tuple(measurements),
        selected_font=selected_font,
        required_canvas_clearance_pt=CANVAS_CONTENT_MIN_CLEARANCE_PT,
        measured_minimum_canvas_clearance_pt=(
            None
            if measured_canvas_clearance_pt is None
            else round(measured_canvas_clearance_pt, 3)
        ),
    )


def export_figure(
    figure: Figure,
    axes: Axes | Iterable[Axes],
    output_prefix: str | Path,
    *,
    style: StyleSpec = DEFAULT_STYLE,
    overrides: Iterable[StyleOverride] = (),
) -> ExportPaths:
    """Validate and export a 600 dpi PNG, editable-text SVG, and manifest."""

    normalized_axes = _normalize_axes(axes)
    normalized_overrides = _normalize_overrides(overrides)
    enforce_figure_typography(figure, normalized_axes, style=style)
    validation = validate_figure(
        figure,
        normalized_axes,
        style=style,
        overrides=normalized_overrides,
    )
    if not validation.passed:
        joined_issues = "\n- ".join(validation.issues)
        raise StyleValidationError(f"CB unified-style validation failed:\n- {joined_issues}")

    prefix = Path(output_prefix)
    if prefix.suffix:
        prefix = prefix.with_suffix("")
    prefix.parent.mkdir(parents=True, exist_ok=True)
    png_path = prefix.with_suffix(".png")
    svg_path = prefix.with_suffix(".svg")
    manifest_path = prefix.with_name(f"{prefix.name}_style_manifest.json")

    figure.savefig(
        png_path,
        dpi=style.export_dpi,
        facecolor="#FFFFFF",
        edgecolor="#FFFFFF",
        bbox_inches=None,
    )
    figure.savefig(
        svg_path,
        format="svg",
        facecolor="#FFFFFF",
        edgecolor="#FFFFFF",
        bbox_inches=None,
    )
    manifest = {
        "schema_version": 1,
        "style": asdict(style),
        "overrides": [asdict(record) for record in normalized_overrides],
        "validation": validation.as_dict(),
        "exports": {
            "png": str(png_path.resolve()),
            "svg": str(svg_path.resolve()),
            "png_dpi": style.export_dpi,
            "svg_fonttype": mpl.rcParams["svg.fonttype"],
            "bbox_inches": None,
        },
    }
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return ExportPaths(
        png=png_path,
        svg=svg_path,
        manifest=manifest_path,
        validation=validation,
    )


