"""
Visualization agent tools.

Three tools form the chart-creation pipeline:

  1. generate_visualization_code  — builds deterministic seaborn code from
                                    chart parameters and config-defined style.
  2. validate_visualization_code  — AST syntax parse + security scan.
  3. save_visualization           — runs validated code in a subprocess and
                                    persists the image to disk.
"""
from __future__ import annotations

import ast
import json
import os
import re
import subprocess
import sys
import tempfile
from typing import Any
from google.adk.tools.tool_context import ToolContext

try:
    from .config import (
        COLOR_PALETTE,
        DEFAULT_DPI,
        DEFAULT_FORMAT,
        DEFAULT_HEIGHT_INCHES,
        DEFAULT_WIDTH_INCHES,
        MAX_DATA_LABELS,
        MAX_XTICK_LABELS,
        OUTPUT_DIR,
        SNS_THEME,
    )
except ImportError:
    from config import (
        COLOR_PALETTE,
        DEFAULT_DPI,
        DEFAULT_FORMAT,
        DEFAULT_HEIGHT_INCHES,
        DEFAULT_WIDTH_INCHES,
        MAX_DATA_LABELS,
        MAX_XTICK_LABELS,
        OUTPUT_DIR,
        SNS_THEME,
    )

# ─── Security: modules / builtins blocked inside generated code ───────────────
_BLOCKED_MODULES: frozenset = frozenset(
    {
        "os",
        "sys",
        "subprocess",
        "socket",
        "shutil",
        "importlib",
        "ctypes",
        "pickle",
        "marshal",
        "pty",
        "pexpect",
        "signal",
        "multiprocessing",
        "threading",
        "http",
        "urllib",
        "requests",
    }
)
_BLOCKED_BUILTINS: frozenset = frozenset(
    {"eval", "exec", "__import__", "compile", "open", "input", "breakpoint"}
)

# Column / filename characters that are safe to embed in generated code
_SAFE_IDENTIFIER_RE = re.compile(r"^[\w\s\-\.]+$")

# Environment detection: GOOGLE_CLOUD_AGENT_ENGINE_ENABLE_TELEMETRY set by Terraform deployment
# Present when deployed → remote mode | Absent locally → local mode
USE_LOCAL_SAVING = not bool(os.environ.get("GOOGLE_CLOUD_AGENT_ENGINE_ENABLE_TELEMETRY"))
print(f"vi=====Running in {'LOCAL' if USE_LOCAL_SAVING else 'CLOUD'} mode (GOOGLE_CLOUD_AGENT_ENGINE_ENABLE_TELEMETRY={'not set' if USE_LOCAL_SAVING else 'set'})")

VISUALIZATION_BUCKET: str = os.environ.get("VISUALIZATION_BUCKET", "")
print(f"vi=====Visualization bucket: {VISUALIZATION_BUCKET or 'not set (local mode)'}")

class _SecurityVisitor(ast.NodeVisitor):
    """Rejects code that contains dangerous constructs."""

    def __init__(self) -> None:
        self.violations: list[str] = []

    def visit_Import(self, node: ast.Import) -> None:  # noqa: N802
        for alias in node.names:
            root = alias.name.split(".")[0]
            if root in _BLOCKED_MODULES:
                self.violations.append(f"Blocked import: {alias.name}")
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:  # noqa: N802
        root = (node.module or "").split(".")[0]
        if root in _BLOCKED_MODULES:
            self.violations.append(f"Blocked from-import: {node.module}")
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:  # noqa: N802
        if isinstance(node.func, ast.Name) and node.func.id in _BLOCKED_BUILTINS:
            self.violations.append(f"Blocked builtin call: {node.func.id}()")
        if isinstance(node.func, ast.Attribute) and isinstance(
            node.func.value, ast.Name
        ):
            if node.func.value.id in _BLOCKED_MODULES:
                self.violations.append(
                    f"Blocked attribute call: {node.func.value.id}.{node.func.attr}()"
                )
        self.generic_visit(node)


# ─── Supported chart types ────────────────────────────────────────────────────
_SUPPORTED_CHARTS: tuple = (
    "bar",
    "line",
    "scatter",
    "box",
    "violin",
    "hist",
    "count",
    "strip",
    "heatmap",
    "pie",
)


def _build_chart_call(
    chart_type: str,
    x_column: str,
    y_column: str,
    hue_column: str,
    data_var: str = "df",
) -> str:
    """Return the seaborn plotting statement(s) for the requested chart type."""
    hue_arg = f", hue={repr(hue_column)}" if hue_column else ""
    ct = chart_type.lower().strip()

    if ct == "bar":
        return (
            f"sns.barplot(data={data_var}, x={repr(x_column)}, y={repr(y_column)}"
            f"{hue_arg}, palette=PALETTE, ax=ax)"
        )
    if ct == "line":
        return (
            f"sns.lineplot(data={data_var}, x={repr(x_column)}, y={repr(y_column)}"
            f"{hue_arg}, palette=PALETTE, ax=ax)"
        )
    if ct == "scatter":
        return (
            f"sns.scatterplot(data={data_var}, x={repr(x_column)}, y={repr(y_column)}"
            f"{hue_arg}, palette=PALETTE, ax=ax)"
        )
    if ct == "box":
        return (
            f"sns.boxplot(data={data_var}, x={repr(x_column)}, y={repr(y_column)}"
            f"{hue_arg}, palette=PALETTE, ax=ax)"
        )
    if ct == "violin":
        return (
            f"sns.violinplot(data={data_var}, x={repr(x_column)}, y={repr(y_column)}"
            f"{hue_arg}, palette=PALETTE, ax=ax)"
        )
    if ct == "hist":
        return (
            f"sns.histplot(data={data_var}, x={repr(x_column)}"
            f"{hue_arg}, palette=PALETTE, ax=ax)"
        )
    if ct == "count":
        return (
            f"sns.countplot(data={data_var}, x={repr(x_column)}"
            f"{hue_arg}, palette=PALETTE, ax=ax)"
        )
    if ct == "strip":
        return (
            f"sns.stripplot(data={data_var}, x={repr(x_column)}, y={repr(y_column)}"
            f"{hue_arg}, palette=PALETTE, ax=ax)"
        )
    if ct == "heatmap":
        pivot_col = repr(hue_column if hue_column else y_column)
        return (
            f"_pivot = {data_var}.pivot_table(\n"
            f"    index={repr(x_column)}, columns={pivot_col},\n"
            f"    values={repr(y_column)}, aggfunc='mean'\n"
            f")\n"
            f"sns.heatmap(_pivot, cmap='Blues', ax=ax, annot=True, fmt='.1f')"
        )
    if ct == "pie":
        return (
            f"_pie_data = {data_var}.groupby({repr(x_column)})[{repr(y_column)}].sum()\n"
            f"_wedges, _texts = ax.pie(\n"
            f"    _pie_data.values, labels=_pie_data.index,\n"
            f"    colors=PALETTE[:len(_pie_data)], startangle=90\n"
            f")\n"
            f"ax.set_aspect('equal')"
        )
    return ""


def _build_data_labels_code(chart_type: str, x_column: str, y_column: str, data_var: str = "df") -> list[str]:
    """Return lines of code that annotate data points with their numerical values."""
    ct = chart_type.lower().strip()

    if ct in ("bar", "hist", "count"):
        return [
            "_patches = ax.patches",
            "_n_patches = len(_patches)",
            f"_step = max(1, _n_patches // {MAX_DATA_LABELS}) if _n_patches > {MAX_DATA_LABELS} else 1",
            "for _i, _p in enumerate(_patches):",
            "    _h = _p.get_height()",
            "    if _h and _h != 0 and _i % _step == 0:",
            "        ax.annotate(",
            "            f'{_h:,.2f}'.rstrip('0').rstrip('.'),",
            "            (_p.get_x() + _p.get_width() / 2., _h),",
            "            ha='center', va='bottom', fontsize=9, fontweight='bold',",
            "        )",
        ]

    if ct == "line":
        return [
            "for _line in ax.get_lines():",
            "    _xd, _yd = _line.get_xdata(), _line.get_ydata()",
            "    _n = len(_xd)",
            f"    _step = max(1, _n // {MAX_DATA_LABELS}) if _n > {MAX_DATA_LABELS} else 1",
            "    for _i, (_xi, _yi) in enumerate(zip(_xd, _yd)):",
            "        if _i % _step == 0:",
            "            ax.annotate(",
            "                f'{_yi:,.2f}'.rstrip('0').rstrip('.'),",
            "                (_xi, _yi), textcoords='offset points', xytext=(0, 6),",
            "                ha='center', va='bottom', fontsize=9, fontweight='bold',",
            "            )",
        ]

    if ct == "scatter":
        return [
            f"_scatter_df = {data_var}.reset_index(drop=True)",
            "_n_pts = len(_scatter_df)",
            f"_step = max(1, _n_pts // {MAX_DATA_LABELS}) if _n_pts > {MAX_DATA_LABELS} else 1",
            "for _i, _row in _scatter_df.iterrows():",
            "    if _i % _step == 0:",
            "        ax.annotate(",
            f"            f'{{_row[{repr(y_column)}]:,.2f}}'.rstrip('0').rstrip('.'),",
            f"            (_row[{repr(x_column)}], _row[{repr(y_column)}]),",
            "            textcoords='offset points', xytext=(0, 6),",
            "            ha='center', va='bottom', fontsize=9, fontweight='bold',",
            "        )",
        ]

    if ct == "pie":
        return [
            "_total = _pie_data.values.sum()",
            "for _text, _val in zip(_texts, _pie_data.values):",
            "    _pct = _val / _total * 100",
            "    _label = _text.get_text()",
            "    _fmt_val = f'{_val:,.2f}'.rstrip('0').rstrip('.')",
            "    _text.set_text(f'{_label}\\n{_pct:.1f}% ({_fmt_val})')",
            "    _text.set_fontsize(9)",
            "    _text.set_fontweight('bold')",
        ]

    # box, violin, strip, heatmap — labels are not applicable or already present
    return []


def _build_xtick_thinning_code() -> list[str]:
    """Return lines of generated code that thin and wrap x-axis tick labels."""
    return [
        "# ── Thin x-axis tick labels if too crowded ─────────────────────────────",
        "_xtick_labels = ax.get_xticklabels()",
        f"if len(_xtick_labels) > {MAX_XTICK_LABELS}:",
        f"    _step = max(1, len(_xtick_labels) // {MAX_XTICK_LABELS})",
        "    _new_labels = [textwrap.fill(_l.get_text(), 18) if _i % _step == 0 else '' for _i, _l in enumerate(_xtick_labels)]",
        "    ax.set_xticklabels(_new_labels, rotation=45, ha='right')",
        "else:",
        "    ax.set_xticklabels([textwrap.fill(_l.get_text(), 18) for _l in _xtick_labels])",
    ]


# ─── Tool 1: Code Generation ──────────────────────────────────────────────────

def generate_visualization_code(
    chart_type: str,
    data_json: str,
    title: str,
    x_column: str,
    y_column: str,
    x_label: str = "",
    y_label: str = "",
    hue_column: str = "",
    custom_dpi: int = 0,
    custom_width_inches: float = 0.0,
    custom_height_inches: float = 0.0,
    show_data_labels: bool = False,
    tool_context: ToolContext = None,
) -> dict[str, Any]:
    """Generate deterministic seaborn visualization code from chart parameters.

    The style, colour palette, and default resolution are read from
    visualization_agent/config.py so every chart produced by this agent
    shares a consistent look. Pass custom_dpi / custom_width_inches /
    custom_height_inches to override the defaults for a single chart.

    Args:
        chart_type: Chart kind. Supported values: bar, line, scatter, box,
            violin, hist, count, strip, heatmap, pie.
        data_json: JSON string encoding the dataset — either a list of
            row-dicts (``[{"col": val, ...}, ...]``) or a column-dict
            (``{"col": [val, ...], ...}``).
        title: Chart title shown above the figure.
        x_column: Column name mapped to the x-axis. For ``pie`` charts
            this is the category / label column.
        y_column: Column name mapped to the y-axis (not required for
            ``hist`` / ``count``; used as the value column for ``heatmap``
            and ``pie``).
        x_label: Human-readable x-axis label. Defaults to x_column.
        y_label: Human-readable y-axis label. Defaults to y_column.
        hue_column: Optional column for colour-encoding a third dimension.
            For ``heatmap`` this becomes the pivot column.
        custom_dpi: DPI override (0 = use DEFAULT_DPI from config).
        custom_width_inches: Figure width override in inches (0 = default).
        custom_height_inches: Figure height override in inches (0 = default).
        show_data_labels: When True, add direct numerical labels on each
            data point / bar. Supported for bar, line, scatter, hist, count,
            and pie charts. For pie, labels show percentage and absolute
            value next to each slice. Ignored for box, violin, strip
            (no single values) and heatmap (already annotated).

    Returns:
        dict with keys:
            - ``status_message`` (str): status message (the actual code is stored
              in session state for ``validate_visualization_code`` and
              ``save_visualization`` to retrieve automatically).
            - ``filename_hint`` (str): suggested output file stem.
            - ``dpi`` (int): resolved DPI value used.
            - ``width_inches`` (float): resolved figure width.
            - ``height_inches`` (float): resolved figure height.
            - ``error`` (str): non-empty only when generation failed.
    """
    # ── Validate chart_type ───────────────────────────────────────────────────
    if chart_type.lower().strip() not in _SUPPORTED_CHARTS:
        return {
            "error": (
                f"Unsupported chart_type '{chart_type}'. "
                f"Supported: {', '.join(_SUPPORTED_CHARTS)}"
            )
        }

    # ── Sanitise column / title strings passed into the generated code ────────
    for name, value in (
        ("x_column", x_column),
        ("y_column", y_column),
        ("hue_column", hue_column),
    ):
        if value and not _SAFE_IDENTIFIER_RE.match(value):
            return {"error": f"Unsafe characters in {name}: {repr(value)}"}

    # ── Validate & normalize data_json ─────────────────────────────────────────
    try:
        _parsed_data = json.loads(data_json)
    except (json.JSONDecodeError, TypeError) as exc:
        return {"error": f"Invalid data_json: {exc}"}
    # Re-serialize to compact single-line JSON to avoid quoting issues in
    # the generated code (the LLM may pass pretty-printed / multi-line JSON).
    data_json = json.dumps(_parsed_data, ensure_ascii=True)

    # ── Resolve resolution ────────────────────────────────────────────────────
    dpi = int(custom_dpi) if custom_dpi and custom_dpi > 0 else DEFAULT_DPI
    width = (
        float(custom_width_inches)
        if custom_width_inches and custom_width_inches > 0
        else DEFAULT_WIDTH_INCHES
    )
    height = (
        float(custom_height_inches)
        if custom_height_inches and custom_height_inches > 0
        else DEFAULT_HEIGHT_INCHES
    )

    xl = x_label or x_column
    yl = y_label or y_column
    filename_hint = (
        re.sub(r"[^\w\-]", "_", title.strip()).lower() or "chart"
    )
    output_filename = filename_hint + "." + DEFAULT_FORMAT
    chart_call = _build_chart_call(chart_type, x_column, y_column, hue_column)

    # ── Assemble code ─────────────────────────────────────────────────────────
    lines: list[str] = [
        "# Auto-generated visualization — do not edit manually.",
        "# Style and resolution are controlled by visualization_agent/config.py.",
        "",
        "import json",
        "import textwrap",
        "from pathlib import Path",
        "",
        "import matplotlib",
        'matplotlib.use("Agg")  # non-interactive backend; must be set before pyplot',
        "import matplotlib.pyplot as plt",
        "import pandas as pd",
        "import seaborn as sns",
        "",
        "# ── Style (from config) ───────────────────────────────────────────────",
        f"_THEME = {repr(SNS_THEME)}",
        f"PALETTE = {repr(COLOR_PALETTE)}",
        "sns.set_theme(**_THEME)",
        "",
        "# ── Data ─────────────────────────────────────────────────────────────",
        f"_raw = json.loads({repr(data_json)})",
        "df = pd.DataFrame(_raw)",
        "",
        "# ── Figure ───────────────────────────────────────────────────────────",
        f"fig, ax = plt.subplots(figsize=({width}, {height}))",
        "",
        "# ── Chart ────────────────────────────────────────────────────────────",
    ]
    lines.extend(chart_call.splitlines())
    lines += [
        "",
        "# ── Data labels ─────────────────────────────────────────────────────",
    ]
    if show_data_labels:
        label_lines = _build_data_labels_code(chart_type, x_column, y_column)
        if label_lines:
            lines.extend(label_lines)
        else:
            lines.append("# (data labels not applicable for this chart type)")
    lines += [
        "",
        "# ── Labels & title ──────────────────────────────────────────────────",
        f"ax.set_title({repr(title)})",
    ]
    if chart_type.lower().strip() != "pie":
        lines += [
            f"ax.set_xlabel({repr(xl)})",
            f"ax.set_ylabel({repr(yl)})",
        ]
    if chart_type.lower().strip() != "pie":
        lines += [""]
        lines += _build_xtick_thinning_code()
    lines += [
        "plt.tight_layout()",
        "",
        "# ── Save ─────────────────────────────────────────────────────────────",
        f"_output_dir = Path({repr(OUTPUT_DIR)})",
        "_output_dir.mkdir(parents=True, exist_ok=True)",
        f"_output_path = _output_dir / {repr(output_filename)}",
        f"fig.savefig(_output_path, dpi={dpi}, bbox_inches='tight', facecolor=fig.get_facecolor())",
        "plt.close(fig)",
        'print(f"Saved: {_output_path.resolve()}")',
    ]

    _code = "\n".join(lines) + "\n"

    # Store in session state so validate / save can retrieve it without the
    # LLM having to pass the large code string (avoids malformed-call errors).
    if tool_context is not None:
        tool_context.state["_last_generated_code"] = _code

    return {
        "status_message": "Code generated and stored in session state. Proceed to validate_visualization_code (no need to pass code).",
        "filename_hint": filename_hint,
        "dpi": dpi,
        "width_inches": width,
        "height_inches": height,
        "error": "",
    }


# ─── Tool 1b: Subplot Code Generation ─────────────────────────────────────────

def generate_subplot_visualization_code(
    subplots_json: str,
    data_json: str,
    title: str,
    layout: str = "vertical",
    custom_dpi: int = 0,
    custom_width_inches: float = 0.0,
    custom_height_inches: float = 0.0,
    tool_context: ToolContext = None,
) -> dict[str, Any]:
    """Generate seaborn code that renders multiple subplots on a single figure.

    Each element of ``subplots_json`` describes one subplot (its chart type,
    columns, title, labels, hue, and whether to show data labels). All
    subplots share the same underlying ``data_json`` dataset.

    Args:
        subplots_json: JSON **array** of subplot specification objects.
            Each object supports the following keys:
                - ``chart_type`` (str, required): one of bar, line, scatter,
                  box, violin, hist, count, strip, heatmap, pie.
                - ``x_column`` (str, required): column for x-axis.
                - ``y_column`` (str, required): column for y-axis.
                - ``title`` (str, optional): subplot title.
                - ``x_label`` (str, optional): x-axis label.
                - ``y_label`` (str, optional): y-axis label.
                - ``hue_column`` (str, optional): colour-encoding column.
                - ``show_data_labels`` (bool, optional): annotate values.
                - ``filter_column`` (str, optional): column used to filter
                  ``data_json`` for this subplot. Must be paired with
                  ``filter_value``.
                - ``filter_value`` (str, optional): value to match in
                  ``filter_column``. Only rows where
                  ``df[filter_column] == filter_value`` are plotted.
        data_json: JSON string encoding the dataset — same format accepted
            by ``generate_visualization_code``.
        title: Overall figure super-title displayed above all subplots.
        layout: Arrangement of subplots. ``"vertical"`` (default) stacks
            them in a single column; ``"horizontal"`` places them in a
            single row; ``"grid"`` uses a roughly square grid.
        custom_dpi: DPI override (0 = use DEFAULT_DPI from config).
        custom_width_inches: Figure width override in inches (0 = default).
        custom_height_inches: Figure height override in inches (0 = default).

    Returns:
        dict with keys:
            - ``status_message`` (str): status message (the actual code is stored
              in session state for ``validate_visualization_code`` and
              ``save_visualization`` to retrieve automatically).
            - ``filename_hint`` (str): suggested output file stem.
            - ``dpi`` (int): resolved DPI value used.
            - ``width_inches`` (float): resolved figure width.
            - ``height_inches`` (float): resolved figure height.
            - ``error`` (str): non-empty only when generation failed.
    """
    # ── Parse & validate subplots spec ───────────────────────────────────────
    try:
        specs: list[dict] = json.loads(subplots_json)
    except (json.JSONDecodeError, TypeError) as exc:
        return {"error": f"Invalid subplots_json: {exc}"}

    if not isinstance(specs, list) or len(specs) == 0:
        return {"error": "subplots_json must be a non-empty JSON array."}
    if len(specs) > 16:
        return {"error": "Too many subplots (max 16)."}

    for idx, spec in enumerate(specs):
        ct = spec.get("chart_type", "")
        if ct.lower().strip() not in _SUPPORTED_CHARTS:
            return {
                "error": (
                    f"Subplot {idx}: unsupported chart_type '{ct}'. "
                    f"Supported: {', '.join(_SUPPORTED_CHARTS)}"
                )
            }
        for key in ("x_column", "y_column", "hue_column", "filter_column"):
            val = spec.get(key, "")
            if val and not _SAFE_IDENTIFIER_RE.match(val):
                return {"error": f"Subplot {idx}: unsafe characters in {key}: {repr(val)}"}

    # ── Validate & normalize data_json ────────────────────────────────────────
    try:
        _parsed_data = json.loads(data_json)
    except (json.JSONDecodeError, TypeError) as exc:
        return {"error": f"Invalid data_json: {exc}"}
    # Re-serialize to compact single-line JSON to avoid quoting issues in
    # the generated code (the LLM may pass pretty-printed / multi-line JSON).
    data_json = json.dumps(_parsed_data, ensure_ascii=True)

    # ── Resolve resolution ───────────────────────────────────────────────────
    n = len(specs)
    dpi = int(custom_dpi) if custom_dpi and custom_dpi > 0 else DEFAULT_DPI

    layout = layout.lower().strip()
    if layout == "horizontal":
        nrows, ncols = 1, n
    elif layout == "grid":
        import math
        ncols = math.ceil(math.sqrt(n))
        nrows = math.ceil(n / ncols)
    else:  # vertical (default)
        nrows, ncols = n, 1

    # Scale default height per row so subplots don't get squished
    default_w = DEFAULT_WIDTH_INCHES
    default_h = DEFAULT_HEIGHT_INCHES * nrows / max(nrows, 1) if layout != "horizontal" else DEFAULT_HEIGHT_INCHES
    # Ensure minimum useful height per subplot
    default_h = max(default_h, 5.0 * nrows) if layout != "horizontal" else default_h

    width = float(custom_width_inches) if custom_width_inches and custom_width_inches > 0 else default_w
    height = float(custom_height_inches) if custom_height_inches and custom_height_inches > 0 else default_h

    filename_hint = re.sub(r"[^\w\-]", "_", title.strip()).lower() or "subplot_chart"
    output_filename = filename_hint + "." + DEFAULT_FORMAT

    # ── Assemble code ────────────────────────────────────────────────────────
    lines: list[str] = [
        "# Auto-generated subplot visualization — do not edit manually.",
        "# Style and resolution are controlled by visualization_agent/config.py.",
        "",
        "import json",
        "import textwrap",
        "from pathlib import Path",
        "",
        "import matplotlib",
        'matplotlib.use("Agg")  # non-interactive backend; must be set before pyplot',
        "import matplotlib.pyplot as plt",
        "import pandas as pd",
        "import seaborn as sns",
        "",
        "# ── Style (from config) ───────────────────────────────────────────────",
        f"_THEME = {repr(SNS_THEME)}",
        f"PALETTE = {repr(COLOR_PALETTE)}",
        "sns.set_theme(**_THEME)",
        "",
        "# ── Data ─────────────────────────────────────────────────────────────",
        f"_raw = json.loads({repr(data_json)})",
        "df = pd.DataFrame(_raw)",
        "",
        "# ── Figure ───────────────────────────────────────────────────────────",
        f"fig, axes = plt.subplots(nrows={nrows}, ncols={ncols}, figsize=({width}, {height}))",
        "import numpy as np",
        "axes = np.atleast_1d(axes).flatten()  # always a flat array",
        "",
    ]

    for idx, spec in enumerate(specs):
        ct = spec.get("chart_type", "line").lower().strip()
        x_col = spec.get("x_column", "")
        y_col = spec.get("y_column", "")
        hue_col = spec.get("hue_column", "")
        sp_title = spec.get("title", "")
        sp_xl = spec.get("x_label", "") or x_col
        sp_yl = spec.get("y_label", "") or y_col
        sp_labels = spec.get("show_data_labels", True)
        filter_col = spec.get("filter_column", "")
        filter_val = spec.get("filter_value", "")

        lines.append(f"# ── Subplot {idx} ─────────────────────────────────────────────────")
        lines.append(f"ax = axes[{idx}]")

        # If a filter is specified, create a filtered dataframe for this subplot
        if filter_col and filter_val is not None and filter_val != "":
            data_var = f"_sub_df_{idx}"
            lines.append(f"{data_var} = df[df[{repr(filter_col)}] == {repr(filter_val)}]")
        else:
            data_var = "df"

        chart_call = _build_chart_call(ct, x_col, y_col, hue_col, data_var=data_var)
        if chart_call:
            lines.extend(chart_call.splitlines())

        if sp_labels:
            label_lines = _build_data_labels_code(ct, x_col, y_col, data_var=data_var)
            if label_lines:
                lines.extend(label_lines)

        if sp_title:
            lines.append(f"ax.set_title({repr(sp_title)})")
        if ct != "pie":
            lines.append(f"ax.set_xlabel({repr(sp_xl)})")
            lines.append(f"ax.set_ylabel({repr(sp_yl)})")
            lines += _build_xtick_thinning_code()
        lines.append("")

    # Hide unused axes when grid layout has leftover cells
    lines += [
        "# ── Hide unused subplot axes ────────────────────────────────────────",
        f"for _unused_ax in axes[{n}:]:",
        "    _unused_ax.set_visible(False)",
        "",
        "# ── Super-title & layout ────────────────────────────────────────────",
        f"fig.suptitle({repr(title)}, fontsize=18, fontweight='bold', y=1.02)",
        "plt.tight_layout()",
        "",
        "# ── Save ─────────────────────────────────────────────────────────────",
        f"_output_dir = Path({repr(OUTPUT_DIR)})",
        "_output_dir.mkdir(parents=True, exist_ok=True)",
        f"_output_path = _output_dir / {repr(output_filename)}",
        f"fig.savefig(_output_path, dpi={dpi}, bbox_inches='tight', facecolor=fig.get_facecolor())",
        "plt.close(fig)",
        'print(f"Saved: {_output_path.resolve()}")',
    ]

    _code = "\n".join(lines) + "\n"

    # Store in session state so validate / save can retrieve it without the
    # LLM having to pass the large code string (avoids malformed-call errors).
    if tool_context is not None:
        tool_context.state["_last_generated_code"] = _code

    return {
        "status_message": "Code generated and stored in session state. Proceed to validate_visualization_code (no need to pass code).",
        "filename_hint": filename_hint,
        "dpi": dpi,
        "width_inches": width,
        "height_inches": height,
        "error": "",
    }


# ─── Tool 2: Validation ───────────────────────────────────────────────────────

def validate_visualization_code(
    tool_context: ToolContext = None,
) -> dict[str, Any]:
    """Validate generated visualization code for syntax correctness and security.

    Performs three checks in order:
      1. AST syntax parse — catches syntax errors before execution.
      2. Security scan — blocks dangerous module imports (os, sys, subprocess,
         socket, …) and dangerous builtins (eval, exec, __import__, open, …).
      3. Seaborn presence check — confirms ``seaborn`` / ``sns`` is imported,
         since the agent is designed exclusively for seaborn charts.

    The code is read automatically from session state where it was stored
    by the most recent call to ``generate_visualization_code`` or
    ``generate_subplot_visualization_code``.

    Args:
        tool_context: ADK tool context injected automatically; not exposed to
            the LLM.

    Returns:
        dict with keys:
            - ``valid`` (bool): True only when all checks pass.
            - ``errors`` (list[str]): Descriptions of every problem found.
              Empty when ``valid`` is True.
    """
    # Read code from session state (stored by the generate step)
    code = ""
    if tool_context is not None:
        code = tool_context.state.get("_last_generated_code", "")
    if not code:
        return {"valid": False, "errors": ["No code found in session state. Call generate_visualization_code first."]}

    errors: list[str] = []

    # 1. Syntax ────────────────────────────────────────────────────────────────
    try:
        tree = ast.parse(code)
    except SyntaxError as exc:
        return {"valid": False, "errors": [f"SyntaxError at line {exc.lineno}: {exc.msg}"]}

    # 2. Security ──────────────────────────────────────────────────────────────
    visitor = _SecurityVisitor()
    visitor.visit(tree)
    errors.extend(visitor.violations)

    # 3. Seaborn presence ──────────────────────────────────────────────────────
    imported_names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imported_names.add(alias.asname or alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            for alias in node.names:
                imported_names.add(alias.asname or alias.name or "")
    if "sns" not in imported_names and "seaborn" not in imported_names:
        errors.append(
            "Code does not import seaborn — only seaborn-based visualizations are supported."
        )

    return {"valid": len(errors) == 0, "errors": errors}


# ─── Tool 3: Save ─────────────────────────────────────────────────────────────

def save_visualization(tool_context: ToolContext = None) -> dict[str, Any]:
    """Execute validated visualization code and confirm the saved file path.

    The code is written to a temporary file and executed in a fresh subprocess
    that inherits the current Python interpreter, so all installed packages
    (seaborn, matplotlib, pandas) are available. Execution is capped at
    60 seconds to prevent hangs.

    Always call ``validate_visualization_code`` **before** calling this tool
    to ensure the code is safe to run.

    The code is read automatically from session state where it was stored
    by the most recent call to ``generate_visualization_code`` or
    ``generate_subplot_visualization_code``.

    In cloud mode (USE_LOCAL_SAVING is False) the chart is uploaded to the
    GCS bucket specified by the VISUALIZATION_BUCKET environment variable
    under a path scoped to the current session: ``{session_id}/{filename}``.
    The local file is removed after a successful upload.

    Args:
        tool_context: ADK tool context injected automatically; not exposed to
            the LLM. Provides the session ID used as the GCS path prefix.

    Returns:
        dict with keys:
            - ``success`` (bool): True when the subprocess exits with code 0.
            - ``output`` (str): Captured stdout or GCS URI on success.
            - ``error`` (str): Captured stderr or timeout message; empty on success.
    """
    # Read code from session state (stored by the generate step)
    code = ""
    if tool_context is not None:
        code = tool_context.state.get("_last_generated_code", "")
    if not code:
        return {"success": False, "output": "", "error": "No code found in session state. Call generate_visualization_code first."}

    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".py", delete=False, encoding="utf-8"
    ) as tmp:
        tmp.write(code)
        tmp_path = tmp.name

    try:
        result = subprocess.run(
            [sys.executable, tmp_path],
            capture_output=True,
            text=True,
            timeout=60,
        )
        if result.returncode != 0:
            return {
                "success": False,
                "output": result.stdout.strip(),
                "error": result.stderr.strip(),
            }

        stdout = result.stdout.strip()

        if USE_LOCAL_SAVING:
            return {"success": True, "output": stdout, "error": ""}

        # ── Cloud mode: upload to GCS ─────────────────────────────────────────
        if not VISUALIZATION_BUCKET:
            return {
                "success": False,
                "output": stdout,
                "error": "VISUALIZATION_BUCKET environment variable is not set.",
            }

        # Parse local file path from subprocess stdout: "Saved: /abs/path/file.png"
        saved_path: str | None = None
        for line in stdout.splitlines():
            if line.startswith("Saved: "):
                saved_path = line[len("Saved: "):].strip()
                break

        if not saved_path or not os.path.exists(saved_path):
            return {
                "success": False,
                "output": stdout,
                "error": f"Could not locate saved file from subprocess output: {stdout!r}",
            }

        session_id = tool_context.session.id
        filename = os.path.basename(saved_path)
        blob_name = f"{session_id}/{filename}"

        try:
            from google.cloud import storage  # lazy import — only needed in cloud mode

            gcs_client = storage.Client()
            bucket_obj = gcs_client.bucket(VISUALIZATION_BUCKET)
            blob = bucket_obj.blob(blob_name)
            blob.upload_from_filename(saved_path)
            gcs_uri = f"gs://{VISUALIZATION_BUCKET}/{blob_name}"
            https_url = f"https://storage.cloud.google.com/{VISUALIZATION_BUCKET}/{blob_name}"
            print(f"vi=====Uploaded visualization to {gcs_uri}")
            return {"success": True, "output": f"Saved to GCS: [{https_url}]({https_url})", "error": ""}
        except Exception as gcs_exc:  # noqa: BLE001
            return {"success": False, "output": stdout, "error": str(gcs_exc)}
        finally:
            try:
                os.unlink(saved_path)
            except OSError:
                pass

    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "output": "",
            "error": "Visualization timed out after 60 seconds.",
        }
    except Exception as exc:  # noqa: BLE001
        return {"success": False, "output": "", "error": str(exc)}
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
