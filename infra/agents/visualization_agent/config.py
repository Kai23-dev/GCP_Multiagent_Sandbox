"""
Visualization agent configuration.

All style, palette, and resolution settings live here.
Generated charts automatically inherit these values — change them here once
to propagate consistently across every visualization the agent produces.
"""
import os

# ── Output ────────────────────────────────────────────────────────────────────
OUTPUT_DIR: str = os.environ.get("VISUALIZATION_OUTPUT_DIR", "visualizations")
DEFAULT_FORMAT: str = "png"

# ── Resolution — maximum / default ───────────────────────────────────────────
# Override per chart by passing custom_dpi / custom_width_inches /
# custom_height_inches to generate_visualization_code.
DEFAULT_DPI: int = 300            # dots-per-inch (max print quality)
DEFAULT_WIDTH_INCHES: float = 16.0
DEFAULT_HEIGHT_INCHES: float = 9.0

# ── Seaborn global theme (passed verbatim to sns.set_theme) ──────────────────
SNS_THEME: dict = {
    "style": "whitegrid",        # whitegrid | darkgrid | white | dark | ticks
    "palette": "muted",
    "context": "talk",           # paper | notebook | talk | poster
    "font": "DejaVu Sans",
    "font_scale": 1.0,
    "rc": {
        "figure.facecolor": "white",
        "axes.facecolor": "#f8f9fa",
        "axes.edgecolor": "#dee2e6",
        "axes.spines.top": False,
        "axes.spines.right": False,
        "grid.alpha": 0.4,
        "grid.linestyle": "--",
        "axes.titlesize": 16,
        "axes.titleweight": "bold",
        "axes.labelsize": 13,
        "xtick.labelsize": 11,
        "ytick.labelsize": 11,
        "legend.fontsize": 11,
        "legend.framealpha": 0.8,
    },
}

# ── Label / annotation density limits ─────────────────────────────────────────
# When a chart has more ticks or data-points than these thresholds, the
# generated code will show only every N-th label to prevent overlapping.
MAX_XTICK_LABELS: int = 15
MAX_DATA_LABELS: int = 15

# ── Deterministic colour palette ──────────────────────────────────────────────
COLOR_PALETTE: list = [
    "#003366",  # Navy
    "#0066CC",  # Blue
    "#3399FF",  # Sky
    "#66B2FF",  # Light blue
    "#FF6600",  # Orange
    "#FF9900",  # Amber
    "#FFCC00",  # Yellow
    "#66CC66",  # Green
]
