"""Generate architecture diagram PNGs for the README.

Run:  python docs/generate_architecture.py
Outputs: docs/architecture.png, docs/threading_model.png

Design philosophy: minimal, flat, maximum whitespace. No curved arrows.
"""

from __future__ import annotations

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
import matplotlib.patheffects as pe

# ── Palette (Catppuccin Mocha) ──────────────────────────────────────────
BG       = "#1e1e2e"
SURFACE  = "#272739"
OVERLAY  = "#585b70"
TEXT     = "#cdd6f4"
DIM      = "#7f849c"

BLUE     = "#89b4fa"
GREEN    = "#a6e3a1"
PEACH    = "#fab387"
RED      = "#f38ba8"
MAUVE    = "#cba6f7"
TEAL     = "#94e2d5"
YELLOW   = "#f9e2af"

BLUE_DIM   = "#3b5998"
GREEN_DIM  = "#3a6d3a"
PEACH_DIM  = "#7a5533"


def _rect(ax, x, y, w, h, fc, ec="none", lw=0, alpha=0.9, zorder=2):
    r = FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.006",
                       fc=fc, ec=ec, lw=lw, alpha=alpha, zorder=zorder)
    ax.add_patch(r)
    return r


def _text(ax, x, y, s, color=TEXT, size=10, weight="normal", ha="center", va="center", zorder=5):
    ax.text(x, y, s, color=color, fontsize=size, fontweight=weight,
            ha=ha, va=va, zorder=zorder)


def _arrow_down(ax, x, y1, y2, color=DIM, lw=1.2):
    ax.annotate("", xy=(x, y2), xytext=(x, y1),
                arrowprops=dict(arrowstyle="-|>", color=color, lw=lw),
                zorder=4)


def _arrow_right(ax, x1, x2, y, color=DIM, lw=1.2):
    ax.annotate("", xy=(x2, y), xytext=(x1, y),
                arrowprops=dict(arrowstyle="-|>", color=color, lw=lw),
                zorder=4)


def _arrow_diag(ax, x1, y1, x2, y2, color=DIM, lw=1.2, ls="-"):
    ax.annotate("", xy=(x2, y2), xytext=(x1, y1),
                arrowprops=dict(arrowstyle="-|>", color=color, lw=lw, ls=ls),
                zorder=4)


# ========================================================================
#  ARCHITECTURE OVERVIEW
# ========================================================================
def generate_architecture():
    fig, ax = plt.subplots(figsize=(13, 10.5), dpi=170)
    fig.patch.set_facecolor(BG)
    ax.set_facecolor(BG)
    ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis("off")

    # Title
    _text(ax, 0.5, 0.965, "HardwareGUI Architecture", TEXT, 20, "bold")
    _text(ax, 0.5, 0.935, "Model-View-Presenter  with  Layered Services", DIM, 11)

    # ── Constants ───────────────────────────────────────────────────────
    L  = 0.08          # left
    R  = 0.92          # right
    W  = R - L         # full width
    BW = 0.175         # box width
    BH = 0.055         # box height
    PAD = 0.035        # padding inside layer bands

    # ── PRESENTATION LAYER ──────────────────────────────────────────────
    py = 0.87          # layer top
    ph = 0.165         # layer height
    _rect(ax, L, py - ph, W, ph, SURFACE, ec=BLUE, lw=1.5, alpha=0.35)
    _text(ax, L + 0.005, py - 0.005, "PRESENTATION", BLUE, 9, "bold", ha="left", va="top")

    # Row 1: MainWindow, Pages, Widgets
    r1y = py - PAD - BH
    xs_3 = [L + PAD + i * (BW + 0.04) for i in range(3)]
    for x, title, sub in [
        (xs_3[0], "MainWindow",     "QMainWindow"),
        (xs_3[1], "Hardware Pages",  "BaseHardwarePage"),
        (xs_3[2], "Widgets",         "Sidebar, LivePlot"),
    ]:
        _rect(ax, x, r1y, BW, BH, BLUE)
        _text(ax, x + BW/2, r1y + BH*0.62, title, BG, 10, "bold")
        _text(ax, x + BW/2, r1y + BH*0.25, sub, BLUE_DIM, 8)

    # Row 2: Presenter (centered)
    r2y = r1y - 0.025 - BH
    px = L + PAD + BW + 0.04  # align under Pages
    _rect(ax, px, r2y, BW, BH, BLUE)
    _text(ax, px + BW/2, r2y + BH*0.62, "ActionsPresenter", BG, 10, "bold")
    _text(ax, px + BW/2, r2y + BH*0.25, "PAGE_FACTORIES registry", BLUE_DIM, 8)

    # Pages -> Presenter
    _arrow_down(ax, xs_3[1] + BW/2, r1y, r2y + BH, BLUE, 1.5)

    # ── DOMAIN LAYER ────────────────────────────────────────────────────
    dy = 0.66
    dh = 0.30
    _rect(ax, L, dy - dh, W, dh, SURFACE, ec=GREEN, lw=1.5, alpha=0.35)
    _text(ax, L + 0.005, dy - 0.005, "DOMAIN", GREEN, 9, "bold", ha="left", va="top")

    # Services row (4 boxes)
    sy = dy - PAD - BH
    xs_4 = [L + PAD + i * (BW + 0.02) for i in range(4)]
    for x, title, sub, fc in [
        (xs_4[0], "VU Service",      "BaseHardwareService", GREEN),
        (xs_4[1], "SMU Service",     "BaseHardwareService", GREEN),
        (xs_4[2], "SU Service",      "BaseHardwareService", GREEN),
        (xs_4[3], "Simulated Svcs",  "SimulatedServiceBase", TEAL),
    ]:
        _rect(ax, x, sy, BW, BH, fc)
        _text(ax, x + BW/2, sy + BH*0.62, title, BG, 10, "bold")
        _text(ax, x + BW/2, sy + BH*0.25, sub, GREEN_DIM, 8)

    # Controllers row (3 boxes)
    cy = sy - 0.025 - BH
    for i, title in enumerate(["VU Controller", "SMU Controller", "SU Controller"]):
        x = xs_4[i]
        _rect(ax, x, cy, BW, BH, GREEN)
        _text(ax, x + BW/2, cy + BH*0.62, title, BG, 10, "bold")
        _text(ax, x + BW/2, cy + BH*0.25, "@operation decorator", GREEN_DIM, 8)

    # Shared patterns row
    spy = cy - 0.025 - 0.042
    sph = 0.042
    spw = 0.20
    sp_gap = 0.035
    sp_xs = [L + PAD + i * (spw + sp_gap) for i in range(3)]
    for x, title, sub in [
        (sp_xs[0], "OperationResult",    "frozen dataclass"),
        (sp_xs[1], "Progress Adapters",  "Template Method"),
        (sp_xs[2], "Exception Hierarchy","HardwareError tree"),
    ]:
        _rect(ax, x, spy, spw, sph, MAUVE, alpha=0.85)
        _text(ax, x + spw/2, spy + sph*0.62, title, BG, 9, "bold")
        _text(ax, x + spw/2, spy + sph*0.22, sub, "#5b4a7a", 7.5)

    # Presenter -> Services arrows
    for i in range(3):
        _arrow_down(ax, xs_4[i] + BW/2, r2y, sy + BH, BLUE, 1.2)

    # Services -> Controllers arrows
    for i in range(3):
        _arrow_down(ax, xs_4[i] + BW/2, sy, cy + BH, GREEN, 1.2)

    # Labels between layers
    _text(ax, R - 0.04, (r2y + sy + BH) / 2, "commands", BLUE, 8, va="center", ha="right")
    _text(ax, R - 0.04, (sy + cy + BH) / 2, "delegates", GREEN, 8, va="center", ha="right")

    # ── INFRASTRUCTURE LAYER ────────────────────────────────────────────
    iy = 0.305
    ih = 0.19
    _rect(ax, L, iy - ih, W, ih, SURFACE, ec=PEACH, lw=1.5, alpha=0.35)
    _text(ax, L + 0.005, iy - 0.005, "INFRASTRUCTURE", PEACH, 9, "bold", ha="left", va="top")

    # Infra row
    iry = iy - PAD - BH
    for i, (title, sub) in enumerate([
        ("FunctionTask",      "QRunnable + Signals"),
        ("Network Discovery", "ThreadPoolExecutor"),
        ("AppConfig",         "Frozen Dataclasses"),
    ]):
        x = xs_3[i]
        _rect(ax, x, iry, BW, BH, PEACH)
        _text(ax, x + BW/2, iry + BH*0.62, title, BG, 10, "bold")
        _text(ax, x + BW/2, iry + BH*0.25, sub, PEACH_DIM, 8)

    # ── EXTERNAL HARDWARE ───────────────────────────────────────────────
    ehy = iy - ih - 0.025 - BH
    for i, (title, sub) in enumerate([
        ("DPI Hardware",      "/measdata/dpi"),
        ("SCPI Instruments",  "Oscilloscopes, PSUs"),
        ("EEPROM / MCU",      "Calibration Data"),
    ]):
        x = xs_3[i]
        _rect(ax, x, ehy, BW, BH, RED, alpha=0.85)
        _text(ax, x + BW/2, ehy + BH*0.62, title, BG, 10, "bold")
        _text(ax, x + BW/2, ehy + BH*0.25, sub, "#6b3040", 8)

    # Controllers -> FunctionTask
    _arrow_down(ax, xs_3[0] + BW/2, cy, iry + BH, PEACH, 1.2)
    _text(ax, xs_3[0] + BW/2 + 0.08, (cy + iry + BH) / 2, "spawns", PEACH, 8)

    # Infra -> Hardware
    _arrow_down(ax, xs_3[0] + BW/2, iry, ehy + BH, RED, 1.2)
    _arrow_down(ax, xs_3[1] + BW/2, iry, ehy + BH, RED, 1.2)

    # ── SIGNAL RETURN PATH ──────────────────────────────────────────────
    # Badge on the right margin, outside all content
    badge_x = R + 0.02
    badge_y = (r1y + iry + BH) / 2
    _rect(ax, badge_x - 0.01, badge_y - 0.05, 0.075, 0.10, SURFACE, alpha=0.9, zorder=5)
    for i, line in enumerate(["TaskSignals", "log", "progress", "artifact", "finished"]):
        yy = badge_y + 0.035 - i * 0.018
        sz = 8.5 if i == 0 else 7.5
        wt = "bold" if i == 0 else "normal"
        _text(ax, badge_x + 0.027, yy, line, YELLOW, sz, wt, zorder=6)

    # Arrow: from infra level to presentation, hugging the right edge
    sig_x = R + 0.005
    ax.annotate("", xy=(sig_x, r1y + BH/2), xytext=(sig_x, iry + BH/2),
                arrowprops=dict(arrowstyle="-|>", color=YELLOW, lw=2.5),
                zorder=4)

    # ── Thread boundary ─────────────────────────────────────────────────
    tby = (dy - dh + iy) / 2
    ax.axhline(tby, xmin=0.08, xmax=0.92, color=YELLOW, lw=1, ls=":", alpha=0.4, zorder=1)
    _text(ax, R - 0.065, tby + 0.01, "thread boundary", YELLOW, 7)

    fig.savefig("docs/architecture.png", bbox_inches="tight", facecolor=BG, pad_inches=0.15)
    plt.close(fig)
    print("Saved docs/architecture.png")


# ========================================================================
#  THREADING DIAGRAM
# ========================================================================
def generate_threading():
    fig, ax = plt.subplots(figsize=(14, 7.5), dpi=170)
    fig.patch.set_facecolor(BG)
    ax.set_facecolor(BG)
    ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis("off")

    _text(ax, 0.5, 0.96, "Threading & Signal Flow", TEXT, 18, "bold")
    _text(ax, 0.5, 0.93, "How hardware operations run without blocking the UI", DIM, 10)

    # ── Constants ───────────────────────────────────────────────────────
    L = 0.04
    R = 0.96
    W = R - L
    BW = 0.19
    BH = 0.085

    # Numbered step badge
    def _step(ax, x, y, num, color):
        ax.text(x, y, str(num), color=BG, fontsize=9, fontweight="bold",
                ha="center", va="center", zorder=7,
                bbox=dict(boxstyle="circle,pad=0.15", fc=color, ec="none"))

    # ── GUI THREAD SECTION ──────────────────────────────────────────────
    gui_top = 0.87
    gui_bot = 0.54
    _rect(ax, L, gui_bot, W, gui_top - gui_bot, SURFACE, ec=BLUE, lw=1.8, alpha=0.3)
    _text(ax, L + 0.04, (gui_top + gui_bot) / 2, "GUI\nThread", BLUE, 11, "bold")

    # Step boxes - single row, well spaced
    gx = [0.12, 0.34, 0.56, 0.78]
    gy = gui_top - 0.06 - BH

    boxes_gui = [
        ("User Click",       "Page button\npressed",    BLUE),
        ("Service._run_task", "Create\nFunctionTask",   GREEN),
        ("Connect Signals",   "log, progress,\nartifact, finished", BLUE),
        ("on_finished()",    "Update UI with\nTaskResult", BLUE),
    ]
    for i, (title, sub, fc) in enumerate(boxes_gui):
        _rect(ax, gx[i], gy, BW, BH, fc)
        _text(ax, gx[i] + BW/2, gy + BH*0.68, title, BG, 10, "bold")
        _text(ax, gx[i] + BW/2, gy + BH*0.28, sub, BLUE_DIM if fc == BLUE else GREEN_DIM, 8)
        _step(ax, gx[i] + 0.015, gy + BH - 0.01, i + 1, fc)

    # Horizontal arrows between GUI boxes
    for i in range(3):
        _arrow_right(ax, gx[i] + BW + 0.005, gx[i+1] - 0.005, gy + BH/2, DIM, 1.3)

    # ── THREAD BOUNDARY ─────────────────────────────────────────────────
    tby = (gui_bot + 0.45) / 2
    ax.axhline(tby, xmin=0.04, xmax=0.96, color=YELLOW, lw=1.8, ls=(0, (6, 4)), alpha=0.6)
    _text(ax, 0.5, tby + 0.015, "THREAD  BOUNDARY  (Qt signal bridge)", YELLOW, 9, "bold")

    # ── WORKER THREAD SECTION ───────────────────────────────────────────
    wrk_top = 0.42
    wrk_bot = 0.08
    _rect(ax, L, wrk_bot, W, wrk_top - wrk_bot, SURFACE, ec=PEACH, lw=1.8, alpha=0.3)
    _text(ax, L + 0.04, (wrk_top + wrk_bot) / 2, "Worker\nThread", PEACH, 11, "bold")

    # Worker boxes
    wy = wrk_top - 0.06 - BH

    boxes_wrk = [
        ("QThreadPool",       "Picks task from\nglobal pool",       PEACH),
        ("FunctionTask.run()", "Captures stdout\nvia _EmittingStream", PEACH),
        ("Controller Op",     "@operation\ndecorator",              GREEN),
        ("DPI / SCPI",        "Hardware\nI/O calls",                RED),
    ]
    for i, (title, sub, fc) in enumerate(boxes_wrk):
        dim = PEACH_DIM if fc == PEACH else (GREEN_DIM if fc == GREEN else "#6b3040")
        _rect(ax, gx[i], wy, BW, BH, fc)
        _text(ax, gx[i] + BW/2, wy + BH*0.68, title, BG, 10, "bold")
        _text(ax, gx[i] + BW/2, wy + BH*0.28, sub, dim, 8)
        _step(ax, gx[i] + 0.015, wy + BH - 0.01, i + 5, fc)

    # Horizontal arrows between worker boxes
    for i in range(3):
        _arrow_right(ax, gx[i] + BW + 0.005, gx[i+1] - 0.005, wy + BH/2, DIM, 1.3)

    # ── CROSS-THREAD ARROWS (3 vertical lines, well separated) ─────────
    # Each arrow occupies its own horizontal position, no overlapping

    # 1. DOWN: Service -> QThreadPool (submit)
    sx = gx[0] + BW * 0.5  # left side
    _arrow_down(ax, sx, gui_bot, wrk_top, PEACH, 2.0)
    _text(ax, sx - 0.05, tby - 0.018, "submit()", PEACH, 9)

    # 2. UP: EmittingStream -> Connect Signals (streaming signals)
    ex = gx[2] + BW * 0.3  # center-left
    _arrow_down(ax, ex, wy + BH, gui_bot, YELLOW, 1.8)
    _text(ax, ex + 0.05, tby - 0.018, "emit(log,\nprogress)", YELLOW, 8)

    # 3. UP: FunctionTask -> on_finished (results)
    fx = gx[3] + BW * 0.5  # right side
    _arrow_down(ax, fx, wy + BH, gui_bot, YELLOW, 2.0)
    _text(ax, fx + 0.015, tby - 0.018, "finished()", YELLOW, 9, ha="left")

    fig.savefig("docs/threading_model.png", bbox_inches="tight", facecolor=BG, pad_inches=0.15)
    plt.close(fig)
    print("Saved docs/threading_model.png")


if __name__ == "__main__":
    generate_architecture()
    generate_threading()
