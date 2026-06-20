import sys
if sys.platform == "win32":
    try:
        import ctypes
        ctypes.windll.shcore.SetProcessDpiAwareness(2)  # Per-Monitor DPI Aware V2
    except Exception:
        pass

import os
os.environ["QT_LOGGING_RULES"] = "qt.qpa.window=false"

# pyrefly: ignore [missing-import]
import multiprocess
import threading
import time
import tkinter as tk
from tkinter import filedialog, messagebox
import customtkinter as ctk
from selenium import webdriver
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.edge.options import Options as EdgeOptions
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.edge.service import Service as EdgeService
try:
    from webdriver_manager.chrome import ChromeDriverManager
    from webdriver_manager.microsoft import EdgeChromiumDriverManager
except ImportError:
    ChromeDriverManager = None
    EdgeChromiumDriverManager = None
from overlay import run
from stockfish_bot import StockfishBot
from selenium.common.exceptions import WebDriverException
import keyboard
try:
    import requests
except ImportError:
    requests = None
try:
    import winreg
except ImportError:
    winreg = None


# ─────────────────────────────────────────────────────────────
#  Design tokens
# ─────────────────────────────────────────────────────────────
FONT_FAMILY   = "Segoe UI"
ACCENT        = "#2563EB"          # Blue-600
ACCENT_HOVER  = "#1D4ED8"          # Blue-700
DANGER        = "#DC2626"          # Red-600
DANGER_HOVER  = "#B91C1C"
SUCCESS       = "#16A34A"          # Green-600
WARNING       = "#D97706"          # Amber-600
CARD_BG       = "#FFFFFF"
PANEL_BG      = "#F1F5F9"          # Slate-100
BORDER        = "#E2E8F0"          # Slate-200
TEXT_PRIMARY  = "#0F172A"          # Slate-900
TEXT_SECONDARY = "#64748B"         # Slate-500
TEXT_MUTED    = "#94A3B8"          # Slate-400
HEADER_BG     = "#F8FAFC"          # Slate-50
ROW_ALT       = "#F8FAFC"

FONT_H1   = (FONT_FAMILY, 13, "bold")
FONT_H2   = (FONT_FAMILY, 11, "bold")
FONT_BODY = (FONT_FAMILY, 10)
FONT_SMALL = (FONT_FAMILY, 9)
FONT_MONO = ("Consolas", 10)

CTK_CORNER = 8


# ─────────────────────────────────────────────────────────────
#  Helper: section card
# ─────────────────────────────────────────────────────────────
def make_card(parent, title: str = "", pady_top: int = 0):
    """Returns a styled CTkFrame card with an optional bold title label."""
    wrapper = ctk.CTkFrame(parent, fg_color="transparent")
    wrapper.pack(fill="x", padx=0, pady=(pady_top, 6))

    if title:
        ctk.CTkLabel(
            wrapper,
            text=title,
            font=ctk.CTkFont(family=FONT_FAMILY, size=10, weight="bold"),
            text_color=TEXT_SECONDARY,
            anchor="w",
        ).pack(fill="x", padx=2, pady=(0, 3))

    card = ctk.CTkFrame(
        wrapper,
        fg_color=CARD_BG,
        corner_radius=CTK_CORNER,
        border_width=1,
        border_color=BORDER,
    )
    card.pack(fill="x")
    return card


def make_divider(parent):
    ctk.CTkFrame(parent, height=1, fg_color=BORDER).pack(fill="x", padx=10, pady=4)


# ─────────────────────────────────────────────────────────────
#  Custom move-log table (pure CTk, no ttk)
# ─────────────────────────────────────────────────────────────
class MoveLogTable(ctk.CTkScrollableFrame):
    COL_WIDTHS = (30, 68, 68)
    HEADERS    = ("#", "White", "Black")

    def __init__(self, parent, **kwargs):
        super().__init__(
            parent,
            fg_color=CARD_BG,
            scrollbar_button_color=BORDER,
            scrollbar_button_hover_color=TEXT_MUTED,
            **kwargs,
        )
        self._rows: list[tuple] = []   # (num_lbl, white_lbl, black_lbl)
        self._build_header()

    # ── header ────────────────────────────────────────────────
    def _build_header(self):
        hdr = ctk.CTkFrame(self, fg_color=HEADER_BG, corner_radius=0)
        hdr.pack(fill="x", pady=(0, 1))
        for i, (text, w) in enumerate(zip(self.HEADERS, self.COL_WIDTHS)):
            ctk.CTkLabel(
                hdr,
                text=text,
                font=ctk.CTkFont(family=FONT_FAMILY, size=10, weight="bold"),
                text_color=TEXT_SECONDARY,
                width=w,
                anchor="center",
            ).grid(row=0, column=i, padx=(4 if i == 0 else 0), pady=5, sticky="ew")

    # ── public API ────────────────────────────────────────────
    def clear(self):
        for row in self._rows:
            for lbl in row:
                lbl.destroy()
        self._rows.clear()

    def insert_move(self, move: str):
        """Append a single move (alternates White / Black)."""
        total_moves = sum(2 if r[2].cget("text") else 1 for r in self._rows)
        if total_moves % 2 == 0:
            # New row
            row_num = len(self._rows) + 1
            self._add_row(row_num, move, "")
        else:
            # Fill Black cell
            num_lbl, white_lbl, black_lbl = self._rows[-1]
            black_lbl.configure(text=move)

    def set_moves(self, moves: list):
        self.clear()
        for i in range(0, len(moves), 2):
            white = moves[i]
            black = moves[i + 1] if i + 1 < len(moves) else ""
            self._add_row(i // 2 + 1, white, black)

    # ── internals ─────────────────────────────────────────────
    def _add_row(self, num: int, white: str, black: str):
        row_bg = ROW_ALT if (num % 2 == 0) else CARD_BG
        row_frame = ctk.CTkFrame(self, fg_color=row_bg, corner_radius=0)
        row_frame.pack(fill="x")

        num_lbl = ctk.CTkLabel(
            row_frame, text=str(num),
            font=ctk.CTkFont(family=FONT_FAMILY, size=10),
            text_color=TEXT_MUTED,
            width=self.COL_WIDTHS[0], anchor="center",
        )
        num_lbl.grid(row=0, column=0, padx=(4, 0), pady=3, sticky="ew")

        white_lbl = ctk.CTkLabel(
            row_frame, text=white,
            font=ctk.CTkFont(family="Consolas", size=10, weight="bold"),
            text_color=TEXT_PRIMARY,
            width=self.COL_WIDTHS[1], anchor="center",
        )
        white_lbl.grid(row=0, column=1, pady=3, sticky="ew")

        black_lbl = ctk.CTkLabel(
            row_frame, text=black,
            font=ctk.CTkFont(family="Consolas", size=10, weight="bold"),
            text_color=TEXT_PRIMARY,
            width=self.COL_WIDTHS[2], anchor="center",
        )
        black_lbl.grid(row=0, column=2, pady=3, sticky="ew")

        self._rows.append((num_lbl, white_lbl, black_lbl))


# ─────────────────────────────────────────────────────────────
#  Stat row helper (label + value side-by-side)
# ─────────────────────────────────────────────────────────────
def stat_row(parent, label: str, default: str = "—") -> ctk.CTkLabel:
    """Packs a label+value pair and returns the *value* label for later updates."""
    row = ctk.CTkFrame(parent, fg_color="transparent")
    row.pack(fill="x", padx=14, pady=2)
    ctk.CTkLabel(
        row, text=label,
        font=ctk.CTkFont(family=FONT_FAMILY, size=10),
        text_color=TEXT_SECONDARY,
        anchor="w", width=110,
    ).pack(side="left")
    val = ctk.CTkLabel(
        row, text=default,
        font=ctk.CTkFont(family=FONT_FAMILY, size=10, weight="bold"),
        text_color=TEXT_PRIMARY,
        anchor="w",
    )
    val.pack(side="left")
    return val


# ─────────────────────────────────────────────────────────────
#  Labelled slider
# ─────────────────────────────────────────────────────────────
def make_slider(parent, label: str, from_: float, to: float,
                resolution: float, default: float,
                variable: tk.Variable) -> ctk.CTkSlider:
    outer = ctk.CTkFrame(parent, fg_color="transparent")
    outer.pack(fill="x", padx=14, pady=(4, 2))

    header = ctk.CTkFrame(outer, fg_color="transparent")
    header.pack(fill="x")
    ctk.CTkLabel(
        header, text=label,
        font=ctk.CTkFont(family=FONT_FAMILY, size=10),
        text_color=TEXT_SECONDARY, anchor="w",
    ).pack(side="left")

    val_lbl = ctk.CTkLabel(
        header, text=str(default),
        font=ctk.CTkFont(family=FONT_FAMILY, size=10, weight="bold"),
        text_color=ACCENT, anchor="e",
    )
    val_lbl.pack(side="right")

    steps = max(1, int(round((to - from_) / resolution)))

    def _on_change(v):
        formatted = (
            str(int(float(v))) if resolution >= 1.0
            else f"{float(v):.1f}"
        )
        val_lbl.configure(text=formatted)
        variable.set(float(v))

    slider = ctk.CTkSlider(
        outer,
        from_=from_, to=to,
        number_of_steps=steps,
        command=_on_change,
        button_color=ACCENT,
        button_hover_color=ACCENT_HOVER,
        progress_color=ACCENT,
        fg_color=BORDER,
        height=16,
    )
    slider.set(default)
    slider.pack(fill="x", pady=(2, 0))
    return slider


# ─────────────────────────────────────────────────────────────
#  Compact numeric entry
# ─────────────────────────────────────────────────────────────
def make_entry_row(parent, label: str, variable: tk.Variable, width: int = 80):
    row = ctk.CTkFrame(parent, fg_color="transparent")
    row.pack(fill="x", padx=14, pady=3)
    ctk.CTkLabel(
        row, text=label,
        font=ctk.CTkFont(family=FONT_FAMILY, size=10),
        text_color=TEXT_SECONDARY, anchor="w", width=110,
    ).pack(side="left")
    entry = ctk.CTkEntry(
        row,
        textvariable=variable,
        width=width,
        justify="center",
        font=ctk.CTkFont(family=FONT_FAMILY, size=10),
        fg_color=PANEL_BG,
        border_color=BORDER,
        text_color=TEXT_PRIMARY,
        corner_radius=6,
        height=28,
    )
    entry.pack(side="left")
    return entry


# ─────────────────────────────────────────────────────────────
#  Main GUI class
# ─────────────────────────────────────────────────────────────
class GUI:
    def __init__(self, master: ctk.CTk):
        self.master = master

        # ── state ────────────────────────────────────────────
        self.exit = False
        self.chrome = None
        self.chrome_url = None
        self.chrome_session_id = None
        self.stockfish_bot_pipe = None
        self.overlay_screen_pipe = None
        self.stockfish_bot_process = None
        self.overlay_screen_process = None
        self.restart_after_stopping = False
        self.match_moves: list[str] = []
        self.running = False
        self.stockfish_path = ""

        # ── window setup ─────────────────────────────────────
        master.title("PawnBit")
        master.geometry("780x680")
        master.minsize(700, 560)
        master.resizable(True, True)
        master.attributes("-topmost", True)
        master.protocol("WM_DELETE_WINDOW", self.on_close_listener)
        try:
            master.iconphoto(True, tk.PhotoImage(file="src/assets/pawn_32x32.png"))
        except Exception:
            pass

        # ── root layout ──────────────────────────────────────
        master.configure(fg_color=PANEL_BG)
        master.grid_columnconfigure(0, weight=0)
        master.grid_columnconfigure(1, weight=1)
        master.grid_rowconfigure(1, weight=1)

        # ── title bar ────────────────────────────────────────
        self._build_titlebar()

        # ── columns ──────────────────────────────────────────
        left_scroll = ctk.CTkScrollableFrame(
            master,
            fg_color="transparent",
            scrollbar_button_color=BORDER,
            scrollbar_button_hover_color=TEXT_MUTED,
            width=310,
        )
        left_scroll.grid(row=1, column=0, sticky="nsew", padx=(10, 4), pady=(0, 10))

        right_col = ctk.CTkFrame(master, fg_color="transparent")
        right_col.grid(row=1, column=1, sticky="nsew", padx=(4, 10), pady=(0, 10))
        right_col.grid_rowconfigure(0, weight=1)
        right_col.grid_columnconfigure(0, weight=1)

        # ── left panels ──────────────────────────────────────
        self._build_metrics_card(left_scroll)
        self._build_connection_card(left_scroll)
        self._build_modes_card(left_scroll)
        self._build_engine_card(left_scroll)
        self._build_misc_card(left_scroll)

        # ── right panel ──────────────────────────────────────
        self._build_move_log(right_col)

        # ── config + threads ─────────────────────────────────
        self.config_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "config.json"
        )
        self.load_config()

        threading.Thread(target=self.process_checker_thread, daemon=True).start()
        threading.Thread(target=self.process_communicator_thread, daemon=True).start()
        threading.Thread(target=self.keypress_listener_thread, daemon=True).start()

    # ═══════════════════════════════════════════════════════════
    #  UI BUILDERS
    # ═══════════════════════════════════════════════════════════

    def _build_titlebar(self):
        bar = ctk.CTkFrame(self.master, fg_color=CARD_BG, corner_radius=0,
                           border_width=0, height=48)
        bar.grid(row=0, column=0, columnspan=2, sticky="ew")
        bar.grid_propagate(False)
        bar.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            bar,
            text="  ♟  PawnBit",
            font=ctk.CTkFont(family=FONT_FAMILY, size=15, weight="bold"),
            text_color=TEXT_PRIMARY,
            anchor="w",
        ).grid(row=0, column=0, padx=14, sticky="w")

        # Status badge in title bar
        self.status_badge = ctk.CTkLabel(
            bar,
            text="  ●  Inactive",
            font=ctk.CTkFont(family=FONT_FAMILY, size=10, weight="bold"),
            text_color="#FFFFFF",
            fg_color="#94A3B8",
            corner_radius=20,
            padx=10, pady=4,
        )
        self.status_badge.grid(row=0, column=1, padx=8, sticky="w")

        ctk.CTkFrame(bar, height=1, fg_color=BORDER).grid(
            row=1, column=0, columnspan=3, sticky="ew"
        )

    # ── Metrics card ─────────────────────────────────────────
    def _build_metrics_card(self, parent):
        card = make_card(parent, "ENGINE STATS")
        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.pack(fill="x", pady=(6, 8))

        self.eval_val   = stat_row(inner, "Evaluation")
        self.wdl_val    = stat_row(inner, "WDL")
        self.mat_val    = stat_row(inner, "Material")
        self.bot_acc    = stat_row(inner, "Bot Accuracy")
        self.opp_acc    = stat_row(inner, "Opponent Acc")

    # ── Connection card ──────────────────────────────────────
    def _build_connection_card(self, parent):
        card = make_card(parent, "CONNECTION", pady_top=4)

        # Platform
        plat_lbl = ctk.CTkLabel(
            card, text="Platform",
            font=ctk.CTkFont(family=FONT_FAMILY, size=10, weight="bold"),
            text_color=TEXT_SECONDARY, anchor="w",
        )
        plat_lbl.pack(fill="x", padx=14, pady=(10, 2))

        self.website = tk.StringVar(value="chesscom")
        plat_row = ctk.CTkFrame(card, fg_color="transparent")
        plat_row.pack(fill="x", padx=14, pady=(0, 6))

        ctk.CTkRadioButton(
            plat_row, text="Chess.com",
            variable=self.website, value="chesscom",
            font=ctk.CTkFont(family=FONT_FAMILY, size=10),
            text_color=TEXT_PRIMARY,
            fg_color=ACCENT, hover_color=ACCENT_HOVER,
        ).pack(side="left", padx=(0, 14))
        ctk.CTkRadioButton(
            plat_row, text="Lichess.org",
            variable=self.website, value="lichess",
            font=ctk.CTkFont(family=FONT_FAMILY, size=10),
            text_color=TEXT_PRIMARY,
            fg_color=ACCENT, hover_color=ACCENT_HOVER,
        ).pack(side="left")

        make_divider(card)

        # Browser
        ctk.CTkLabel(
            card, text="Browser",
            font=ctk.CTkFont(family=FONT_FAMILY, size=10, weight="bold"),
            text_color=TEXT_SECONDARY, anchor="w",
        ).pack(fill="x", padx=14, pady=(4, 2))

        self.available_browsers = self.detect_browsers()
        if not self.available_browsers:
            self.available_browsers["Chrome"] = "default"

        self.selected_browser = tk.StringVar()
        browser_list = list(self.available_browsers.keys())
        default_browser = "Chrome" if "Chrome" in browser_list else browser_list[0]
        self.selected_browser.set(default_browser)

        browser_row = ctk.CTkFrame(card, fg_color="transparent")
        browser_row.pack(fill="x", padx=14, pady=(0, 10))
        for b in browser_list:
            ctk.CTkRadioButton(
                browser_row, text=b,
                variable=self.selected_browser, value=b,
                font=ctk.CTkFont(family=FONT_FAMILY, size=10),
                text_color=TEXT_PRIMARY,
                fg_color=ACCENT, hover_color=ACCENT_HOVER,
            ).pack(side="left", padx=(0, 12))

        make_divider(card)

        # Start / Stop button
        self.start_button = ctk.CTkButton(
            card,
            text="▶  Start",
            command=self.on_start_button_listener,
            font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"),
            fg_color=ACCENT,
            hover_color=ACCENT_HOVER,
            corner_radius=CTK_CORNER,
            height=36,
        )
        self.start_button.pack(fill="x", padx=14, pady=(6, 12))

    # ── Modes card ───────────────────────────────────────────
    def _build_modes_card(self, parent):
        card = make_card(parent, "MODES", pady_top=4)

        self.enable_manual_mode     = tk.BooleanVar(value=False)
        self.enable_mouseless_mode  = tk.BooleanVar(value=False)
        self.enable_non_stop_puzzles  = tk.IntVar(value=0)
        self.enable_non_stop_matches  = tk.IntVar(value=0)
        self.enable_bongcloud       = tk.IntVar(value=0)

        def _checkbox(parent, text, variable, command=None):
            kw = dict(
                text=text,
                variable=variable,
                font=ctk.CTkFont(family=FONT_FAMILY, size=10),
                text_color=TEXT_PRIMARY,
                fg_color=ACCENT,
                hover_color=ACCENT_HOVER,
                checkmark_color="#FFFFFF",
                corner_radius=4,
                border_width=2,
                border_color=BORDER,
            )
            if command:
                kw["command"] = command
            cb = ctk.CTkCheckBox(parent, **kw)
            cb.pack(anchor="w", padx=14, pady=3)
            return cb

        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.pack(fill="x", pady=(8, 4))

        self.manual_mode_checkbox = _checkbox(
            inner, "Manual Mode",
            self.enable_manual_mode,
            command=self.on_manual_mode_checkbox_listener,
        )
        # Sub-label for manual mode
        self.manual_mode_frame = ctk.CTkFrame(inner, fg_color="transparent")
        self.manual_mode_label = ctk.CTkLabel(
            self.manual_mode_frame,
            text="   ↳  Press 3 to make a move",
            font=ctk.CTkFont(family=FONT_FAMILY, size=9),
            text_color=TEXT_MUTED, anchor="w",
        )
        self.manual_mode_label.pack(anchor="w")

        _checkbox(inner, "Mouseless Mode", self.enable_mouseless_mode)
        _checkbox(inner, "Non-stop Puzzles", self.enable_non_stop_puzzles)
        _checkbox(inner, "Non-stop Online Matches", self.enable_non_stop_matches)
        _checkbox(inner, "Bongcloud  ♟", self.enable_bongcloud)

        make_divider(card)

        # Mouse latency slider
        self.mouse_latency = tk.DoubleVar(value=0.0)
        make_slider(card, "Mouse Latency (s)",
                    from_=0.0, to=15.0, resolution=0.2,
                    default=0.0, variable=self.mouse_latency)
        ctk.CTkFrame(card, height=6, fg_color="transparent").pack()

    # ── Engine params card ───────────────────────────────────
    def _build_engine_card(self, parent):
        card = make_card(parent, "ENGINE PARAMETERS", pady_top=4)
        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.pack(fill="x", pady=(8, 4))

        self.slow_mover   = tk.IntVar(value=100)
        self.skill_level  = tk.IntVar(value=20)
        self.stockfish_depth = tk.IntVar(value=15)
        self.memory       = tk.IntVar(value=512)
        self.cpu_threads  = tk.IntVar(value=1)

        make_entry_row(inner, "Slow Mover", self.slow_mover, width=80)

        make_slider(inner, "Skill Level",
                    from_=0, to=20, resolution=1,
                    default=20, variable=self.skill_level)

        make_slider(inner, "Depth",
                    from_=1, to=20, resolution=1,
                    default=15, variable=self.stockfish_depth)

        make_divider(inner)

        make_entry_row(inner, "Memory (MB)", self.memory, width=80)
        make_entry_row(inner, "CPU Threads", self.cpu_threads, width=80)
        ctk.CTkFrame(inner, height=4, fg_color="transparent").pack()

    # ── Misc card ────────────────────────────────────────────
    def _build_misc_card(self, parent):
        card = make_card(parent, "MISC", pady_top=4)
        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.pack(fill="x", pady=(8, 10))

        self.enable_topmost = tk.IntVar(value=1)
        ctk.CTkCheckBox(
            inner,
            text="Window stays on top",
            variable=self.enable_topmost,
            onvalue=1, offvalue=0,
            command=self.on_topmost_check_button_listener,
            font=ctk.CTkFont(family=FONT_FAMILY, size=10),
            text_color=TEXT_PRIMARY,
            fg_color=ACCENT, hover_color=ACCENT_HOVER,
            checkmark_color="#FFFFFF",
            corner_radius=4,
            border_width=2,
            border_color=BORDER,
        ).pack(anchor="w", padx=14, pady=(0, 6))

        make_divider(inner)

        # Stockfish browser button + path display
        ctk.CTkButton(
            inner,
            text="📂  Select Stockfish",
            command=self.on_select_stockfish_button_listener,
            font=ctk.CTkFont(family=FONT_FAMILY, size=10),
            fg_color=PANEL_BG,
            hover_color=BORDER,
            text_color=TEXT_PRIMARY,
            border_width=1,
            border_color=BORDER,
            corner_radius=CTK_CORNER,
            height=32,
        ).pack(fill="x", padx=14, pady=(6, 4))

        self.stockfish_path_label = ctk.CTkLabel(
            inner,
            text="No executable selected",
            font=ctk.CTkFont(family="Consolas", size=9),
            text_color=TEXT_MUTED,
            anchor="w",
            wraplength=260,
        )
        self.stockfish_path_label.pack(fill="x", padx=14, pady=(0, 4))

    # ── Move log (right column) ───────────────────────────────
    def _build_move_log(self, parent):
        # Header
        log_header = ctk.CTkFrame(parent, fg_color="transparent")
        log_header.grid(row=0, column=0, sticky="new", padx=0, pady=(0, 4))
        log_header.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            log_header,
            text="MOVE LOG",
            font=ctk.CTkFont(family=FONT_FAMILY, size=10, weight="bold"),
            text_color=TEXT_SECONDARY,
            anchor="w",
        ).grid(row=0, column=0, sticky="w", pady=(0, 3))

        # Table card wrapper
        table_card = ctk.CTkFrame(
            parent,
            fg_color=CARD_BG,
            corner_radius=CTK_CORNER,
            border_width=1,
            border_color=BORDER,
        )
        table_card.grid(row=1, column=0, sticky="nsew", padx=0, pady=0)
        parent.grid_rowconfigure(1, weight=1)

        self.move_log = MoveLogTable(table_card)
        self.move_log.pack(fill="both", expand=True, padx=4, pady=4)

        # Export button
        self.export_pgn_button = ctk.CTkButton(
            parent,
            text="⬇  Export PGN",
            command=self.on_export_pgn_button_listener,
            font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"),
            fg_color=PANEL_BG,
            hover_color=BORDER,
            text_color=TEXT_PRIMARY,
            border_width=1,
            border_color=BORDER,
            corner_radius=CTK_CORNER,
            height=38,
        )
        self.export_pgn_button.grid(row=2, column=0, sticky="ew", pady=(8, 0))

    # ═══════════════════════════════════════════════════════════
    #  STATUS BADGE HELPER
    # ═══════════════════════════════════════════════════════════

    def _set_status(self, text: str, color: str):
        self.status_badge.configure(
            text=f"  ●  {text}",
            fg_color=color,
        )
        self.status_badge.update()

    # ═══════════════════════════════════════════════════════════
    #  BROWSER DETECTION (unchanged logic)
    # ═══════════════════════════════════════════════════════════

    def detect_browsers(self):
        available = {}

        def check_registry(name):
            if winreg is None:
                return None
            for hkey in (winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER):
                try:
                    key = winreg.OpenKey(
                        hkey,
                        f"SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\App Paths\\{name}"
                    )
                    val, _ = winreg.QueryValueEx(key, "")
                    winreg.CloseKey(key)
                    if val:
                        val = val.strip('"')
                        if os.path.exists(val):
                            return val
                except Exception:
                    pass
            return None

        # Chrome
        chrome_path = check_registry("chrome.exe")
        if not chrome_path:
            for p in [
                os.path.expandvars(r"%ProgramFiles%\Google\Chrome\Application\chrome.exe"),
                os.path.expandvars(r"%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe"),
                os.path.expandvars(r"%LocalAppData%\Google\Chrome\Application\chrome.exe"),
            ]:
                if os.path.exists(p):
                    chrome_path = p
                    break
        if chrome_path:
            available["Chrome"] = chrome_path

        # Edge
        edge_path = check_registry("msedge.exe")
        if not edge_path:
            for p in [
                os.path.expandvars(r"%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe"),
                os.path.expandvars(r"%ProgramFiles%\Microsoft\Edge\Application\msedge.exe"),
                os.path.expandvars(r"%LocalAppData%\Microsoft\Edge\Application\msedge.exe"),
            ]:
                if os.path.exists(p):
                    edge_path = p
                    break
        if edge_path:
            available["Edge"] = edge_path

        # Brave
        brave_path = check_registry("brave.exe")
        if not brave_path:
            for p in [
                os.path.expandvars(r"%ProgramFiles%\BraveSoftware\Brave-Browser\Application\brave.exe"),
                os.path.expandvars(r"%ProgramFiles(x86)%\BraveSoftware\Brave-Browser\Application\brave.exe"),
                os.path.expandvars(r"%LocalAppData%\BraveSoftware\Brave-Browser\Application\brave.exe"),
            ]:
                if os.path.exists(p):
                    brave_path = p
                    break
        if brave_path:
            available["Brave"] = brave_path

        return available

    # ═══════════════════════════════════════════════════════════
    #  EVENT LISTENERS  (all original logic preserved)
    # ═══════════════════════════════════════════════════════════

    def on_close_listener(self):
        self.exit = True
        self.master.destroy()

    def on_topmost_check_button_listener(self):
        self.master.attributes("-topmost", bool(self.enable_topmost.get()))

    def on_manual_mode_checkbox_listener(self):
        if self.enable_manual_mode.get():
            self.manual_mode_frame.pack(after=self.manual_mode_checkbox,
                                        anchor="w", padx=14, pady=(0, 2))
        else:
            self.manual_mode_frame.pack_forget()

    def on_select_stockfish_button_listener(self):
        f = filedialog.askopenfilename(
            title="Select Stockfish Executable",
            filetypes=[("Executable", "*.exe"), ("All Files", "*.*")],
        )
        if not f:
            return
        self.stockfish_path = f
        # Truncate display: show last two path components
        parts = f.replace("\\", "/").split("/")
        display = "…/" + "/".join(parts[-2:]) if len(parts) > 2 else f
        self.stockfish_path_label.configure(text=display, text_color=TEXT_PRIMARY)
        self.save_config()

    def on_export_pgn_button_listener(self):
        f = filedialog.asksaveasfile(
            initialfile="match.pgn",
            defaultextension=".pgn",
            filetypes=[("Portable Game Notation", "*.pgn"), ("All Files", "*.*")],
        )
        if f is None:
            return
        data = ""
        for i in range(len(self.match_moves) // 2 + 1):
            if len(self.match_moves) % 2 == 0 and i == len(self.match_moves) // 2:
                continue
            data += str(i + 1) + ". "
            data += self.match_moves[i * 2] + " "
            if (i * 2) + 1 < len(self.match_moves):
                data += self.match_moves[i * 2 + 1] + " "
        f.write(data)
        f.close()

    # ── Start ─────────────────────────────────────────────────
    def on_start_button_listener(self):
        slow_mover = self.slow_mover.get()
        if slow_mover < 10 or slow_mover > 1000:
            messagebox.showerror("Error", "Slow Mover must be between 10 and 1000")
            return
        if not self.stockfish_path:
            messagebox.showerror("Error", "Stockfish path is empty")
            return
        if not self.check_browser_and_attach():
            return
        if self.enable_mouseless_mode.get() and self.website.get() == "chesscom":
            messagebox.showerror("Error", "Mouseless mode is only supported on Lichess.org")
            return

        parent_conn, child_conn = multiprocess.Pipe()
        self.stockfish_bot_pipe = parent_conn
        st_ov_queue = multiprocess.Queue()

        self.stockfish_bot_process = StockfishBot(
            self.chrome_url,
            self.chrome_session_id,
            self.website.get(),
            child_conn,
            st_ov_queue,
            self.stockfish_path,
            self.enable_manual_mode.get() == 1,
            self.enable_mouseless_mode.get() == 1,
            self.enable_non_stop_puzzles.get() == 1,
            self.enable_non_stop_matches.get() == 1,
            self.mouse_latency.get(),
            self.enable_bongcloud.get() == 1,
            self.slow_mover.get(),
            self.skill_level.get(),
            self.stockfish_depth.get(),
            self.memory.get(),
            self.cpu_threads.get(),
        )
        self.stockfish_bot_process.start()

        self.overlay_screen_process = multiprocess.Process(target=run, args=(st_ov_queue,))
        self.overlay_screen_process.start()

        self.running = True
        self.start_button.configure(
            text="Starting…",
            state="disabled",
            fg_color=TEXT_MUTED,
            hover_color=TEXT_MUTED,
        )

    # ── Stop ──────────────────────────────────────────────────
    def on_stop_button_listener(self):
        if self.stockfish_bot_process is not None:
            if self.overlay_screen_process is not None:
                self.overlay_screen_process.kill()
                self.overlay_screen_process = None
            if self.stockfish_bot_process.is_alive():
                self.stockfish_bot_process.kill()
            self.stockfish_bot_process = None

        if self.stockfish_bot_pipe is not None:
            self.stockfish_bot_pipe.close()
            self.stockfish_bot_pipe = None

        self.running = False
        self._set_status("Inactive", "#94A3B8")

        # Reset eval displays
        for lbl, text in [
            (self.eval_val, "—"), (self.wdl_val, "—"),
            (self.mat_val, "—"), (self.bot_acc, "—"),
            (self.opp_acc, "—"),
        ]:
            lbl.configure(text=text, text_color=TEXT_PRIMARY)

        if not self.restart_after_stopping:
            self.start_button.configure(
                text="▶  Start",
                state="normal",
                fg_color=ACCENT,
                hover_color=ACCENT_HOVER,
                command=self.on_start_button_listener,
            )
        else:
            self.restart_after_stopping = False
            self.on_start_button_listener()

    # ═══════════════════════════════════════════════════════════
    #  BACKGROUND THREADS
    # ═══════════════════════════════════════════════════════════

    def process_checker_thread(self):
        while not self.exit:
            if (
                self.running
                and self.stockfish_bot_process is not None
                and not self.stockfish_bot_process.is_alive()
            ):
                self.on_stop_button_listener()
                if self.restart_after_stopping:
                    self.restart_after_stopping = False
                    self.on_start_button_listener()
            time.sleep(0.1)

    def process_communicator_thread(self):
        while not self.exit:
            try:
                if self.stockfish_bot_pipe is not None and self.stockfish_bot_pipe.poll():
                    data = self.stockfish_bot_pipe.recv()

                    if data == "START":
                        self.move_log.clear()
                        self.match_moves = []
                        self._set_status("Running", SUCCESS)
                        self.start_button.configure(
                            text="⏹  Stop",
                            state="normal",
                            fg_color=DANGER,
                            hover_color=DANGER_HOVER,
                            command=self.on_stop_button_listener,
                        )
                    elif data[:7] == "RESTART":
                        self.restart_after_stopping = True
                        self.stockfish_bot_pipe.send("DELETE")
                    elif data[:6] == "S_MOVE":
                        move = data[6:]
                        self.match_moves.append(move)
                        self.move_log.insert_move(move)
                        self.move_log._parent_canvas.yview_moveto(1)  # scroll to bottom
                    elif data[:6] == "M_MOVE":
                        moves = data[6:].split(",")
                        self.match_moves += moves
                        self.move_log.set_moves(moves)
                    elif data[:5] == "EVAL|":
                        parts = data.split("|")
                        if len(parts) >= 5:
                            eval_str, wdl_str, material_str, bot_acc_str, opp_acc_str = parts[1:]
                            self.update_evaluation_display(
                                eval_str, wdl_str, material_str, bot_acc_str, opp_acc_str
                            )
                    elif data[:7] == "ERR_EXE":
                        messagebox.showerror("Error", "Stockfish path provided is not valid!")
                    elif data[:8] == "ERR_PERM":
                        messagebox.showerror("Error", "Stockfish path provided is not executable!")
                    elif data[:9] == "ERR_BOARD":
                        messagebox.showerror("Error", "Can't find board!")
                    elif data[:9] == "ERR_COLOR":
                        messagebox.showerror("Error", "Can't find player color!")
                    elif data[:9] == "ERR_MOVES":
                        messagebox.showerror("Error", "Can't find moves list!")
                    elif data[:12] == "ERR_GAMEOVER":
                        messagebox.showerror("Error", "Game has already finished!")
            except (BrokenPipeError, OSError):
                self.stockfish_bot_pipe = None
            time.sleep(0.1)

    def keypress_listener_thread(self):
        while not self.exit:
            time.sleep(0.1)
            if keyboard.is_pressed("1"):
                self.on_start_button_listener()
            elif keyboard.is_pressed("2"):
                self.on_stop_button_listener()

    # ═══════════════════════════════════════════════════════════
    #  EVALUATION DISPLAY
    # ═══════════════════════════════════════════════════════════

    def update_evaluation_display(self, eval_str, wdl_str, material_str,
                                   bot_acc, opponent_acc):
        # Eval color
        try:
            if eval_str.startswith("M"):
                color = SUCCESS if int(eval_str[1:]) > 0 else DANGER
            else:
                v = float(eval_str)
                color = SUCCESS if v > 0 else (TEXT_PRIMARY if v == 0 else DANGER)
        except ValueError:
            color = TEXT_PRIMARY
        self.eval_val.configure(text=eval_str, text_color=color)

        self.wdl_val.configure(text=wdl_str, text_color=TEXT_PRIMARY)

        # Material color
        try:
            if material_str.startswith("+"):
                mat_color = SUCCESS
            elif material_str.startswith("-"):
                mat_color = DANGER
            else:
                mat_color = TEXT_PRIMARY
        except Exception:
            mat_color = TEXT_PRIMARY
        self.mat_val.configure(text=material_str, text_color=mat_color)

        self.bot_acc.configure(text=bot_acc, text_color=TEXT_PRIMARY)
        self.opp_acc.configure(text=opponent_acc, text_color=TEXT_PRIMARY)

    # ═══════════════════════════════════════════════════════════
    #  CONFIG
    # ═══════════════════════════════════════════════════════════

    def load_config(self):
        import json
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path) as f:
                    config = json.load(f)
                    path = config.get("stockfish_path", "")
                    if path and os.path.exists(path):
                        self.stockfish_path = path
                        parts = path.replace("\\", "/").split("/")
                        display = "…/" + "/".join(parts[-2:]) if len(parts) > 2 else path
                        self.stockfish_path_label.configure(
                            text=display, text_color=TEXT_PRIMARY
                        )
            except Exception as e:
                print(f"Error loading config: {e}")

    def save_config(self):
        import json
        try:
            config = {}
            if os.path.exists(self.config_path):
                try:
                    with open(self.config_path) as f:
                        config = json.load(f)
                except Exception:
                    pass
            config["stockfish_path"] = self.stockfish_path
            with open(self.config_path, "w") as f:
                json.dump(config, f, indent=4)
        except Exception as e:
            print(f"Error saving config: {e}")

    # ═══════════════════════════════════════════════════════════
    #  BROWSER ATTACH (unchanged logic)
    # ═══════════════════════════════════════════════════════════

    def _probe_cdp_tabs(self, port=9222):
        if requests is None:
            return []
        try:
            resp = requests.get(f"http://localhost:{port}/json", timeout=1)
            if resp.status_code == 200:
                return resp.json()
        except Exception:
            pass
        return []

    def _find_browser_debug_port(self):
        for port in range(9222, 9232):
            tabs = self._probe_cdp_tabs(port)
            if tabs:
                return port, tabs
        return None, []

    def check_browser_and_attach(self):
        site = self.website.get()
        browser_choice = self.selected_browser.get()
        target_url = "chess.com" if site == "chesscom" else "lichess.org"
        site_name = "Chess.com" if site == "chesscom" else "Lichess.org"

        port, tabs = self._find_browser_debug_port()
        if not tabs:
            messagebox.showinfo(
                "Browser Not Detected",
                f"Could not detect {browser_choice} with remote debugging enabled.\n\n"
                f"Please open {browser_choice} with the following flag:\n"
                f"  --remote-debugging-port=9222\n\n"
                f"Then navigate to {site_name} and click Start again."
            )
            return False

        matching_tab = next(
            (t for t in tabs if target_url in t.get("url", "")), None
        )
        if matching_tab is None:
            messagebox.showinfo(
                "Site Not Open",
                f"{site_name} is not open in {browser_choice}.\n\n"
                f"Please navigate to {site_name} in {browser_choice} and click Start again."
            )
            return False

        try:
            browser_path = self.available_browsers.get(browser_choice)
            if browser_choice == "Edge":
                options = EdgeOptions()
                options.add_experimental_option("debuggerAddress", f"localhost:{port}")
                if browser_path and browser_path != "default":
                    options.binary_location = browser_path
                try:
                    if EdgeChromiumDriverManager is not None:
                        edge_install = EdgeChromiumDriverManager().install()
                        folder = os.path.dirname(edge_install)
                        edgedriver_path = os.path.join(folder, "msedgedriver.exe")
                        service = EdgeService(edgedriver_path)
                        driver = webdriver.Edge(service=service, options=options)
                    else:
                        driver = webdriver.Edge(options=options)
                except Exception:
                    driver = webdriver.Edge(options=options)
            else:
                options = ChromeOptions()
                options.add_experimental_option("debuggerAddress", f"localhost:{port}")
                if browser_path and browser_path != "default":
                    options.binary_location = browser_path
                try:
                    if ChromeDriverManager is not None:
                        chrome_install = ChromeDriverManager().install()
                        folder = os.path.dirname(chrome_install)
                        chromedriver_path = os.path.join(folder, "chromedriver.exe")
                        service = ChromeService(chromedriver_path)
                        driver = webdriver.Chrome(service=service, options=options)
                    else:
                        driver = webdriver.Chrome(options=options)
                except Exception:
                    driver = webdriver.Chrome(options=options)

            self.chrome = driver
            self.chrome_url = driver.command_executor._url
            self.chrome_session_id = driver.session_id

            for handle in driver.window_handles:
                driver.switch_to.window(handle)
                if target_url in driver.current_url:
                    break
            return True

        except Exception as e:
            messagebox.showerror("Attach Failed",
                                 f"Could not attach to {browser_choice}.\n\nError: {e}")
            return False


# ─────────────────────────────────────────────────────────────
#  Entry point
# ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    ctk.set_appearance_mode("light")
    ctk.set_default_color_theme("blue")

    window = ctk.CTk()
    my_gui = GUI(window)
    window.mainloop()
