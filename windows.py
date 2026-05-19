import os
import re
import sys
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from roboflow import Roboflow
import json
import base64
from io import BytesIO
from PIL import Image, ImageTk, ImageDraw
import numpy as np
import threading
from datetime import datetime
import urllib.request
import urllib.error
import pickle
from pathlib import Path
import socket
from contextlib import contextmanager, redirect_stdout
try:
    from scipy import ndimage
    SCIPY_AVAILABLE = True
except ImportError:
    SCIPY_AVAILABLE = False
try:
    import cv2
    OPENCV_AVAILABLE = True
except ImportError:
    OPENCV_AVAILABLE = False
try:
    import matplotlib
    matplotlib.use('TkAgg')
    import matplotlib.pyplot as plt
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
    import matplotlib.patches as patches
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False
try:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import letter, A4
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image as RLImage, PageBreak, HRFlowable
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False
try:
    import pillow_heif
    PILLOW_HEIF_AVAILABLE = True
except ImportError:
    PILLOW_HEIF_AVAILABLE = False

ROBOFLOW_API_KEY = "Ixdl8OkpfEuJSBr6DV55"
DISH_MODEL_ID = "moldez_dish_finder"
DISH_MODEL_VERSION = 4
Culture_MODEL_ID = "moldez_segmentation"
Culture_MODEL_VERSION = 6
def resource_path(relative_path):
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)

def set_window_icon(window):
    """Apply the app icon with macOS-friendly asset selection."""
    icns_path = resource_path("icon.icns")
    png_path = resource_path("banner.png")
    ico_path = resource_path("icon.ico")
    if sys.platform.startswith("win") and os.path.exists(ico_path):
        try:
            window.iconbitmap(default=ico_path)
        except Exception:
            pass
    icon_path = None
    for candidate in (icns_path, png_path, ico_path):
        if os.path.exists(candidate):
            icon_path = candidate
            break
    if not icon_path:
        return
    try:
        with Image.open(icon_path) as icon_image:
            icon_photo = ImageTk.PhotoImage(icon_image)
        window._icon_photo = icon_photo
        window.iconphoto(True, icon_photo)
    except Exception:
        try:
            icon_photo = tk.PhotoImage(file=icon_path)
            window._icon_photo = icon_photo
            window.iconphoto(True, icon_photo)
        except Exception:
            pass

def get_app_dir():
    """Return a stable writable directory for the current platform."""
    if sys.platform == "darwin":
        app_support_dir = os.path.join(
            os.path.expanduser("~/Library/Application Support"),
            "MoldEZ")
        os.makedirs(app_support_dir, exist_ok=True)
        return app_support_dir
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.abspath(".")

@contextmanager
def suppress_stdout():
    with open(os.devnull, 'w') as devnull:
        with redirect_stdout(devnull):
            try:
                yield
            finally:
                pass

# Rounded buttons are rendered.
class RoundedButton(tk.Canvas):
    """A pill-shaped button with smooth hover transition."""
    def __init__(self, parent, text, command, bg_color="#2c3e50",
                 fg_color="white", hover_color=None,
                 radius=18, font=("Segoe UI Semibold", 10),
                 padx=20, pady=8, state=tk.NORMAL, **kwargs):
        self._state = state
        self._bg = bg_color
        self._fg = fg_color
        self._hover = hover_color or self._lighten(bg_color)
        self._radius = radius
        self._text = text.upper()
        self._font = font
        self._command = command
        self._padx = padx
        self._pady = pady

        # Text size is measured safely.
        _measure_top = tk.Toplevel(parent)
        _measure_top.withdraw()
        tmp = tk.Label(_measure_top, text=self._text, font=self._font)
        tmp.update_idletasks()
        w = tmp.winfo_reqwidth() + padx * 2
        h = tmp.winfo_reqheight() + pady * 2

        # Parent background is retrieved.
        try:
            parent_bg = parent.cget("bg")
        except Exception:
            parent_bg = "#f8f9fa"

        super().__init__(parent, width=w, height=h,
                         highlightthickness=0, bd=0,
                         bg=parent_bg, **kwargs)

        # Pending Tk work is flushed.
        self.update_idletasks()
        _measure_top.destroy()

        self._w = w
        self._h = h
        self._current_color = bg_color

        # Initial draw is scheduled.
        self.after_idle(self._perform_initial_draw)

        if state == tk.NORMAL:
            self.bind("<Enter>", self._on_enter)
            self.bind("<Leave>", self._on_leave)
            self.bind("<Button-1>", self._on_click)
            self.bind("<ButtonRelease-1>", self._on_release)
            self.config_canvas(cursor="hand2")

    def _perform_initial_draw(self):
        """Safely draw after Tk has registered the canvas command."""
        self._draw(self._bg)

    # Drawing is performed.
    def _draw(self, fill_color):
        self.delete("all")
        r = self._radius
        w, h = self._w, self._h
        self.create_arc(0, 0, 2*r, 2*r, start=90, extent=90, fill=fill_color, outline=fill_color)
        self.create_arc(w-2*r, 0, w, 2*r, start=0, extent=90, fill=fill_color, outline=fill_color)
        self.create_arc(0, h-2*r, 2*r, h, start=180, extent=90, fill=fill_color, outline=fill_color)
        self.create_arc(w-2*r, h-2*r, w, h, start=270, extent=90, fill=fill_color, outline=fill_color)
        self.create_rectangle(r, 0, w-r, h, fill=fill_color, outline=fill_color)
        self.create_rectangle(0, r, w, h-r, fill=fill_color, outline=fill_color)
        self.create_text(w//2, h//2, text=self._text, font=self._font,
                         fill=self._fg if self._state == tk.NORMAL else "#aaaaaa")
        self._current_color = fill_color

    def set_text(self, text):
        """Update the button label and redraw cleanly."""
        self._text = text.upper()
        self._draw(self._current_color)

    def _lighten(self, hex_color):
        table = {
            '#2c3e50': '#34495e', '#27ae60': '#2ecc71', '#f39c12': '#f1c40f',
            '#e74c3c': '#ec7063', '#3498db': '#5dade2', '#2ca24c': '#36d162',
            '#f0ad4e': '#f8c471', '#2596be': '#3ab4d9', '#842aa2': '#9b32bb',
        }
        return table.get(hex_color, hex_color)

    # Interactions are handled.
    def _on_enter(self, e):
        self._draw(self._hover)

    def _on_leave(self, e):
        self._draw(self._bg)

    def _on_click(self, e):
        self._draw(self._bg)

    def _on_release(self, e):
        self._draw(self._hover)
        if self._command:
            self._command()

    # State is controlled.
    def config(self, **kwargs):
        if "state" in kwargs:
            self._state = kwargs.pop("state")
            if self._state == tk.DISABLED:
                self.unbind("<Enter>")
                self.unbind("<Leave>")
                self.unbind("<Button-1>")
                self.unbind("<ButtonRelease-1>")
                self.config_canvas(cursor="")
            else:
                self.bind("<Enter>", self._on_enter)
                self.bind("<Leave>", self._on_leave)
                self.bind("<Button-1>", self._on_click)
                self.bind("<ButtonRelease-1>", self._on_release)
                self.config_canvas(cursor="hand2")
            self._draw(self._bg)
        if kwargs:
            super().config(**kwargs)

    def config_canvas(self, **kw):
        super().config(**kw)

    def pack(self, **kw):
        super().pack(**kw)
    def grid(self, **kw):
        super().grid(**kw)
    def place(self, **kw):
        super().place(**kw)

    def update_bg(self, new_bg):
        super().config(bg=new_bg)

class AppButton(tk.Button):
    """Standard rectangular button with hover and disabled styling."""
    def __init__(self, parent, text, command, bg_color="#2c3e50",
                 fg_color="white", hover_color=None,
                 font=("Segoe UI", 10, "bold"),
                 padx=15, pady=5, state=tk.NORMAL, palette_key=None, **kwargs):
        self._bg = bg_color
        self._fg = fg_color
        self._hover = hover_color or self._lighten(bg_color)
        self._disabled_bg = "#c8ced6"
        self._disabled_fg = "#6c757d"
        self._palette_key = palette_key

        super().__init__(
            parent,
            text=text.upper(),
            command=command,
            font=font,
            bg=bg_color,
            fg=fg_color,
            activebackground=self._hover,
            activeforeground=fg_color,
            disabledforeground=self._disabled_fg,
            relief=tk.RAISED,
            bd=3,
            padx=padx,
            pady=pady,
            cursor="hand2" if state == tk.NORMAL else "",
            highlightthickness=0,
            state=state,
            **kwargs
        )
        self._apply_state_style()
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)

    def _lighten(self, hex_color):
        table = {
            '#2c3e50': '#34495e', '#27ae60': '#2ecc71', '#f39c12': '#f1c40f',
            '#e74c3c': '#ec7063', '#3498db': '#5dade2', '#2ca24c': '#36d162',
            '#f0ad4e': '#f8c471', '#2596be': '#3ab4d9', '#842aa2': '#9b32bb',
            '#e0e6ed': '#f5f7fa', '#4fa3e0': '#76baea', '#bb55d4': '#ca79de',
        }
        return table.get(hex_color, hex_color)

    def _darken(self, hex_color):
        table = {
            '#e0e6ed': '#c5ced8', '#4fa3e0': '#3b92d1', '#2ecc71': '#25b864',
            '#f8c471': '#efb04a', '#3ab4d9': '#259bc0', '#bb55d4': '#a440c0',
            '#e74c3c': '#d44334', '#f39c12': '#db8907',
        }
        return table.get(hex_color, hex_color)

    def _compute_fg(self, bg_color):
        color = bg_color.lstrip('#')
        if len(color) != 6:
            return "white"
        red = int(color[0:2], 16)
        green = int(color[2:4], 16)
        blue = int(color[4:6], 16)
        luminance = (0.299 * red) + (0.587 * green) + (0.114 * blue)
        return "#18202d" if luminance >= 170 else "white"

    def _apply_state_style(self):
        is_disabled = str(self.cget("state")) == tk.DISABLED
        self.configure(
            bg=self._disabled_bg if is_disabled else self._bg,
            activebackground=self._disabled_bg if is_disabled else self._hover,
            fg=self._disabled_fg if is_disabled else self._fg,
            activeforeground=self._disabled_fg if is_disabled else self._fg,
            cursor="" if is_disabled else "hand2",
        )

    def _on_enter(self, _event):
        if str(self.cget("state")) != tk.DISABLED:
            self.configure(bg=self._hover, bd=4)

    def _on_leave(self, _event):
        if str(self.cget("state")) != tk.DISABLED:
            self.configure(bg=self._bg, bd=3)

    def configure(self, cnf=None, **kwargs):
        if "state" in kwargs:
            state = kwargs["state"]
            result = super().configure(cnf, **kwargs)
            if state in (tk.NORMAL, tk.DISABLED, "normal", "disabled"):
                self._apply_state_style()
            return result
        return super().configure(cnf, **kwargs)

    config = configure

    def set_text(self, text):
        self.configure(text=text.upper())

    def update_theme(self, colors):
        if self._palette_key and self._palette_key in colors:
            self._bg = colors[self._palette_key]
        self._fg = self._compute_fg(self._bg)
        if self._palette_key == 'primary' and self._bg == colors.get('primary'):
            self._hover = self._darken(self._bg) if self._fg != "white" else self._lighten(self._bg)
        else:
            self._hover = self._lighten(self._bg)
        is_dark = colors.get('background', '').lower() == DARK_COLORS['background']
        self._disabled_bg = '#4b556b' if is_dark else '#c8ced6'
        self._disabled_fg = '#a7b4c6' if is_dark else '#6c757d'
        self._apply_state_style()

class ToggleSwitch(tk.Canvas):
    """Animated on/off switch for the top bar."""
    def __init__(self, parent, variable, command=None, width=46, height=24,
                 bg_color="#2c3e50", on_color="#4fa3e0", off_color="#5b6474",
                 thumb_color="#ffffff", **kwargs):
        super().__init__(
            parent,
            width=width,
            height=height,
            highlightthickness=0,
            bd=0,
            bg=bg_color,
            cursor="hand2",
            **kwargs
        )
        self.variable = variable
        self.command = command
        self._width = width
        self._height = height
        self._bg = bg_color
        self._on = on_color
        self._off = off_color
        self._thumb = thumb_color
        self._position = 1.0 if self.variable.get() else 0.0
        self.bind("<Button-1>", self._toggle)
        self._draw()

    def _draw(self):
        self.delete("all")
        pad = 2
        track_h = self._height - pad * 2
        track_w = self._width - pad * 2
        radius = track_h / 2
        x0 = pad
        y0 = pad
        x1 = x0 + track_w
        y1 = y0 + track_h
        fill = self._blend(self._off, self._on, self._position)

        self.create_arc(x0, y0, x0 + track_h, y1, start=90, extent=180,
                        fill=fill, outline=fill)
        self.create_arc(x1 - track_h, y0, x1, y1, start=270, extent=180,
                        fill=fill, outline=fill)
        self.create_rectangle(x0 + radius, y0, x1 - radius, y1,
                              fill=fill, outline=fill)

        thumb_d = track_h - 4
        thumb_x = x0 + 2 + (track_w - thumb_d - 4) * self._position
        thumb_y = y0 + 2
        self.create_oval(thumb_x, thumb_y, thumb_x + thumb_d, thumb_y + thumb_d,
                         fill=self._thumb, outline="")

    def _hex_to_rgb(self, value):
        value = value.lstrip('#')
        return tuple(int(value[i:i+2], 16) for i in (0, 2, 4))

    def _rgb_to_hex(self, rgb):
        return '#%02x%02x%02x' % rgb

    def _blend(self, start, end, progress):
        sr, sg, sb = self._hex_to_rgb(start)
        er, eg, eb = self._hex_to_rgb(end)
        mixed = (
            int(sr + (er - sr) * progress),
            int(sg + (eg - sg) * progress),
            int(sb + (eb - sb) * progress),
        )
        return self._rgb_to_hex(mixed)

    def _set_position(self, target):
        self._position = target
        self._draw()

    def _toggle(self, _event=None):
        self.variable.set(not self.variable.get())
        self._set_position(1.0 if self.variable.get() else 0.0)
        if self.command:
            self.command()

    def sync(self):
        self._set_position(1.0 if self.variable.get() else 0.0)

    def update_colors(self, bg_color=None, on_color=None, off_color=None,
                      thumb_color=None):
        if bg_color is not None:
            self._bg = bg_color
            super().configure(bg=bg_color)
        if on_color is not None:
            self._on = on_color
        if off_color is not None:
            self._off = off_color
        if thumb_color is not None:
            self._thumb = thumb_color
        self._draw()


class AnimatedProgressBar(tk.Canvas):
    def __init__(self, parent, width=320, height=14, mode='indeterminate',
                 maximum=100, bg_color='#edf3fb', fill_color='#18a558',
                 accent_color='#32c06b', border_color='#18a558', **kwargs):
        super().__init__(
            parent,
            width=width,
            height=height,
            highlightthickness=0,
            bd=0,
            bg=parent.cget('bg') if 'bg' in parent.keys() else '#ffffff',
            **kwargs
        )
        self._width = width
        self._height = height
        self.mode = mode
        self.maximum = max(1, maximum)
        self.value = 0
        self._running = False
        self._after_id = None
        self._offset = 0
        self._indeterminate_span = 0.34
        self._bg_color = bg_color
        self._fill_color = fill_color
        self._accent_color = accent_color
        self._border_color = border_color
        self.bind("<Configure>", self._on_resize)
        self._draw()

    def _on_resize(self, event):
        self._width = max(20, event.width)
        self._height = max(10, event.height)
        self._draw()

    def configure_colors(self, bg_color=None, fill_color=None,
                         accent_color=None, border_color=None):
        if bg_color is not None:
            self._bg_color = bg_color
        if fill_color is not None:
            self._fill_color = fill_color
        if accent_color is not None:
            self._accent_color = accent_color
        if border_color is not None:
            self._border_color = border_color
        self._draw()

    config_colors = configure_colors

    def _rounded_rect(self, x0, y0, x1, y1, radius, fill, outline):
        r = min(radius, (x1 - x0) / 2, (y1 - y0) / 2)
        self.create_arc(x0, y0, x0 + 2*r, y0 + 2*r,
                        start=90, extent=90, fill=fill, outline=outline)
        self.create_arc(x1 - 2*r, y0, x1, y0 + 2*r,
                        start=0, extent=90, fill=fill, outline=outline)
        self.create_arc(x0, y1 - 2*r, x0 + 2*r, y1,
                        start=180, extent=90, fill=fill, outline=outline)
        self.create_arc(x1 - 2*r, y1 - 2*r, x1, y1,
                        start=270, extent=90, fill=fill, outline=outline)
        self.create_rectangle(x0 + r, y0, x1 - r, y1,
                              fill=fill, outline=outline)
        self.create_rectangle(x0, y0 + r, x1, y1 - r,
                              fill=fill, outline=outline)

    def _draw_stripes(self, x0, y0, x1, y1):
        stripe_step = 18
        stripe_width = 10
        slant = max(8, int((y1 - y0) * 0.9))
        start = int(x0 - slant + self._offset)
        end = int(x1 + slant)
        for sx in range(start, end, stripe_step):
            self.create_polygon(
                sx, y1,
                sx + stripe_width, y1,
                sx + stripe_width + slant, y0,
                sx + slant, y0,
                fill=self._accent_color,
                outline=""
            )

    def _draw(self):
        self.delete("all")
        pad = 1
        x0, y0 = pad, pad
        x1, y1 = self._width - pad, self._height - pad
        self.create_rectangle(
            x0, y0, x1, y1,
            fill=self._bg_color,
            outline=self._border_color,
            width=1
        )

        inner_pad = 2
        ix0, iy0 = x0 + inner_pad, y0 + inner_pad
        ix1, iy1 = x1 - inner_pad, y1 - inner_pad
        inner_w = max(0, ix1 - ix0)
        if inner_w <= 0:
            return

        if self.mode == 'indeterminate':
            start = ix0
            end = ix1
        else:
            fraction = max(0.0, min(1.0, self.value / float(self.maximum)))
            start = ix0
            end = ix0 + (inner_w * fraction)

        if end > start:
            self.create_rectangle(
                start, iy0, end, iy1,
                fill=self._fill_color,
                outline=self._fill_color,
                width=0
            )
            self._draw_stripes(start, iy0, end, iy1)

    def _animate(self):
        if not self._running:
            return
        self._offset = (self._offset + 4) % 18
        self._draw()
        self._after_id = self.after(40, self._animate)

    def start(self, _interval=None):
        if self.mode != 'indeterminate':
            return
        self.stop()
        self._running = True
        self._animate()

    def stop(self):
        self._running = False
        if self._after_id is not None:
            try:
                self.after_cancel(self._after_id)
            except Exception:
                pass
            self._after_id = None
        self._offset = 0
        self._draw()

    def set_value(self, value):
        self.value = max(0, min(self.maximum, value))
        self._draw()

# Theme palettes are defined.
LIGHT_COLORS = {
    'primary': '#2c3e50',
    'secondary': '#3498db',
    'tertiary': '#2ca24c',
    'quaternary': '#f0ad4e',
    'quinary': '#2596be',
    'senary': '#842aa2',
    'success': '#27ae60',
    'warning': '#f39c12',
    'danger': '#e74c3c',
    'light': '#ecf0f1',
    'background': '#f8f9fa',
    'card': '#ffffff',
    'border': '#dee2e6',
    'text': '#2c3e50',
    'subtext': '#6c757d',
    'results_bg': '#f8f9fa',
    'input_bg': '#ffffff',
    'input_fg': '#2c3e50',
}
DARK_COLORS = {
    'primary': '#e0e6ed',
    'secondary': '#4fa3e0',
    'tertiary': '#2ecc71',
    'quaternary': '#f8c471',
    'quinary': '#3ab4d9',
    'senary': '#bb55d4',
    'success': '#2ecc71',
    'warning': '#f39c12',
    'danger': '#e74c3c',
    'light': '#2c3e50',
    'background': '#1a1f2e',
    'card': '#242b3d',
    'border': '#3a4460',
    'text': '#e0e6ed',
    'subtext': '#8899aa',
    'results_bg': '#242b3d',
    'input_bg': '#242b3d',
    'input_fg': '#e0e6ed',
}
_BG_REMAP_ORDER = [
    ('#2c3551', 'input_bg'),
    ('#1e2536', 'results_bg'),
    ('#242b3d', 'card'),
    ('#1a1f2e', 'background'),
    ('#2d3748', 'input_bg'),
    ('#ffffff', 'card'),
    ('#f8f9fa', 'background'),
]

class MoldEZAnalyzer:
    def __init__(self, root):
        if PILLOW_HEIF_AVAILABLE:
            pillow_heif.register_heif_opener()
        self.root = root
        self.root.title("MoldEZ (Mark IV)")
        self.root.geometry("1600x920")
        self.dark_mode = tk.BooleanVar(value=False)
        self.colors = dict(LIGHT_COLORS)
        self.root.configure(bg=self.colors['background'])
        self.dish_model = None
        self.Culture_model = None
        self.current_image_path = None
        self.processed_image = None
        self._image_lock = threading.Lock()
        self.preprocessed_image_path = None
        self.detected_plate_pixels = 0
        self.detected_Culture_pixels = 0
        self.plate_mask = None
        self.Culture_mask = None
        self.use_clahe = tk.BooleanVar(value=False)
        self.clahe_clip_limit = tk.DoubleVar(value=2.0)
        self.clahe_tile_size = tk.IntVar(value=8)
        self.show_advanced = tk.BooleanVar(value=False)
        self.dish_confidence = tk.IntVar(value=30)
        self.Culture_confidence = tk.IntVar(value=40)
        self.analysis_history = []
        self.sessions = []
        self.current_session_name = "Session(1)"
        self.session_files = {}
        self.results_dir = os.path.join(get_app_dir(), "results")
        self.compare_time_source_var = tk.StringVar(value="timestamps")
        self.manual_time_hours_var = tk.IntVar(value=0)
        self.manual_time_minutes_var = tk.IntVar(value=0)
        if not os.path.exists(self.results_dir):
            os.makedirs(self.results_dir)
        self.timer_id = None
        self.remaining_seconds = 0
        self.automation_running = False
        self.auto_hours_var = tk.IntVar(value=0)
        self.auto_minutes_var = tk.IntVar(value=10)
        self.batch_cancelled = False
        self._reprocess_after_id = None
        self._detection_generation = 0
        self._themed_widgets = []
        self.setup_gui()
        self._bind_realtime_pipeline_callbacks()
        self.root.update_idletasks()
        threading.Thread(target=self._background_startup, daemon=True).start()

    # Mousewheel support is provided.
    def _bind_mousewheel(self, canvas):
        def _on_wheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        def _on_enter(_event):
            canvas.bind_all("<MouseWheel>", _on_wheel)
            canvas.bind_all("<Button-4>",
                            lambda e: canvas.yview_scroll(-1, "units"))
            canvas.bind_all("<Button-5>",
                            lambda e: canvas.yview_scroll(1, "units"))
        def _on_leave(_event):
            canvas.unbind_all("<MouseWheel>")
            canvas.unbind_all("<Button-4>")
            canvas.unbind_all("<Button-5>")
        canvas.bind("<Enter>", _on_enter)
        canvas.bind("<Leave>", _on_leave)

    def _setup_drop_target(self, widget):
        try:
            widget.tk.call('package', 'require', 'tkdnd')
            widget.tk.call('tkdnd::drop_target', 'register', widget._w, 'DND_Files')
            widget.bind('<<Drop>>', self._on_drop_image)
            if hasattr(self, 'drop_zone'):
                self.drop_zone.config(text="Drag and drop an image here\nor click to browse")
        except Exception:
            if hasattr(self, 'drop_zone'):
                self.drop_zone.config(text="Click to browse for an image")

    def _extract_dropped_file(self, raw_data):
        if not raw_data:
            return None
        try:
            candidates = list(self.root.tk.splitlist(raw_data))
        except Exception:
            candidates = [raw_data]
        for item in candidates:
            path = item.strip().strip('{}')
            if os.path.isfile(path):
                return path
        return None

    def _on_drop_image(self, event):
        path = self._extract_dropped_file(getattr(event, 'data', ''))
        if not path:
            return
        self.load_selected_image(path)

    def load_selected_image(self, path):
        self.current_image_path = path
        self.image_status.config(
            text=os.path.basename(path), fg=self.colors['success'])
        self.run_detection_btn.config(state=tk.NORMAL)
        self.update_status("Ready to run detection")
        self.reset_detection_data()
        self.show_image_preview()

    def _save_pil_image(self, image, path):
        """Save PIL images safely, converting alpha modes for JPEG output."""
        save_image = image
        if path.lower().endswith(('.jpg', '.jpeg')):
            if getattr(save_image, 'mode', '') in ('RGBA', 'LA'):
                save_image = save_image.convert('RGB')
            elif getattr(save_image, 'mode', '') == 'P':
                save_image = save_image.convert('RGBA').convert('RGB')
        save_image.save(path)

    # Dark mode is handled.
    def toggle_dark_mode(self):
        if self.dark_mode.get():
            self.colors = dict(DARK_COLORS)
        else:
            self.colors = dict(LIGHT_COLORS)
        self._update_header_theme()
        self._update_dark_mode_toggle()
        self.update_banner()
        style = ttk.Style()
        self._configure_scrollbar_style()
        self._configure_session_tree_style()
        self._configure_progressbar_style()
        style.configure("Modern.TNotebook",
                        background=self.colors['background'])
        self.update_banner()
        self._apply_theme_recursive(self.root)
        self._update_session_section_theme()
        if MATPLOTLIB_AVAILABLE and hasattr(self, 'fig'):
            self.fig.patch.set_facecolor(self.colors['background'])
            for ax in [self.ax1, self.ax2]:
                ax.set_facecolor(self.colors['results_bg'])
            self.refresh_visualization()
        if MATPLOTLIB_AVAILABLE and hasattr(self, 'colony_fig'):
            self.colony_fig.patch.set_facecolor(self.colors['background'])
            for ax in [self.colony_ax1, self.colony_ax2]:
                ax.set_facecolor(self.colors['results_bg'])
            self.refresh_colony_visualization()

    def _apply_theme_recursive(self, widget):
        """Walk every widget and re-colour it."""
        cls = widget.__class__.__name__
        if isinstance(widget, RoundedButton):
            widget.update_bg(self.colors['background'])
            return
        if isinstance(widget, AppButton):
            try:
                widget.update_theme(self.colors)
            except Exception:
                pass
            return
        if isinstance(widget, ToggleSwitch):
            try:
                widget.update_colors(bg_color=self._header_bg())
            except Exception:
                pass
            return
        try:
            bg = widget.cget("bg")
            for old_hex, key in _BG_REMAP_ORDER:
                if bg == old_hex:
                    widget.config(bg=self.colors[key])
                    break
        except Exception:
            pass
        try:
            fg = widget.cget("fg")
            fg_map = {
                '#2c3e50': self.colors['text'],
                '#e0e6ed': self.colors['text'],
                '#6c757d': self.colors['subtext'],
                '#8899aa': self.colors['subtext'],
                'black': self.colors['text'],
            }
            if fg in fg_map:
                widget.config(fg=fg_map[fg])
        except Exception:
            pass
        if cls == 'Text':
            try:
                widget.config(bg=self.colors['results_bg'],
                              fg=self.colors['text'],
                              insertbackground=self.colors['text'])
            except Exception:
                pass
        if cls == 'Entry':
            try:
                widget.config(bg=self.colors['input_bg'],
                              fg=self.colors['input_fg'],
                              insertbackground=self.colors['input_fg'],
                              highlightbackground=self.colors['border'])
            except Exception:
                pass
        if cls == 'Scale':
            try:
                widget.config(bg=self.colors['card'],
                              fg=self.colors['text'],
                              troughcolor=self.colors['border'])
            except Exception:
                pass
        if cls == 'Checkbutton':
            try:
                widget.config(bg=self.colors['card'],
                              fg=self.colors['text'],
                              selectcolor=self.colors['card'],
                              activebackground=self.colors['card'],
                              activeforeground=self.colors['text'])
            except Exception:
                pass
        if cls == 'Spinbox':
            try:
                widget.config(bg=self.colors['input_bg'],
                              fg=self.colors['input_fg'],
                              buttonbackground=self.colors['card'])
            except Exception:
                pass
        if cls == 'Canvas':
            try:
                if widget.cget("bg") not in self.colors.values():
                    widget.config(bg=self.colors['background'])
            except Exception:
                pass
        if cls == 'LabelFrame':
            try:
                widget.config(bg=self.colors['card'],
                              fg=self.colors['text'])
            except Exception:
                pass
        for child in widget.winfo_children():
            self._apply_theme_recursive(child)

    # Startup is processed.
    def _background_startup(self):
        if not self.is_internet_available():
            def _no_internet():
                self.show_message(
                    "warning", "Internet Required",
                    "MoldEZ requires an active internet connection to "
                    "initialize Roboflow models.\n\n"
                    "Please connect and try again.")
                self.root.after(1000, self.root.destroy)
            self.root.after(0, _no_internet)
            return
        self.initialize_models()

    # Internet is checked.
    def is_internet_available(self, host="8.8.8.8", port=53, timeout=3):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(timeout)
            s.connect((host, port))
            s.close()
            return True
        except socket.error:
            return False

    # GUI is set up.
    def setup_gui(self):
        # Top bar is configured.
        topbar = tk.Frame(self.root, bg=self.colors['primary'], height=42,
                          highlightbackground=self.colors['border'],
                          highlightthickness=1)
        topbar.pack(fill=tk.X, side=tk.TOP)
        topbar.pack_propagate(False)
        self.topbar = topbar
        self.topbar.configure(bg=self._header_bg())
        app_title = tk.Label(topbar,
                             text="MoldEZ · Professional Culture Analysis",
                             font=("Segoe UI", 11, "bold"),
                             fg="white", bg=self.colors['primary'])
        app_title.destroy()
        dm_frame = tk.Frame(topbar, bg=self._header_bg())
        dm_frame.pack(side=tk.RIGHT, padx=16, pady=6)
        self.dm_frame = dm_frame
        dm_label = tk.Label(dm_frame, text="🌙 Dark Mode",
                            font=("Segoe UI", 9), fg="white",
                            bg=self._header_bg())
        dm_label.config(text="🌙 Dark Mode", font=("Segoe UI", 10, "bold"),
                        cursor="hand2")
        dm_label.pack(side=tk.LEFT, padx=(0, 8))
        self.dm_label = dm_label
        self.dm_toggle_btn = ToggleSwitch(
            dm_frame,
            variable=self.dark_mode,
            command=self.toggle_dark_mode,
            bg_color=self._header_bg()
        )
        self._update_dark_mode_toggle()
        self.dm_toggle_btn.pack(side=tk.LEFT)
        dm_label.bind("<Button-1>", self.dm_toggle_btn._toggle)
        # Footer is configured.
        footer_frame = tk.Frame(self.root, bg=self.colors['background'])
        footer_frame.pack(fill=tk.X, side=tk.BOTTOM, pady=4)
        footer_label = tk.Label(
            footer_frame,
            text="Powered by Truman State University · "
                 "Developed by Mohammed Ayan Mahmood · 2025",
            font=("Segoe UI", 8, "italic"),
            fg=self.colors['subtext'], bg=self.colors['background'])
        footer_label.pack()
        footer_label.config(
            text="Powered by Truman State University · "
                 "Developed by Mohammed Ayan Mahmood · 2026")
        # Main container is configured.
        main_container = tk.Frame(self.root, bg=self.colors['background'])
        main_container.pack(expand=True, fill=tk.BOTH, padx=18,
                            pady=(10, 6))
        banner_frame = tk.Frame(main_container, bg=self.colors['background'])
        banner_frame.pack(fill=tk.X, pady=(0, 8))
        banner_photo = None
        try:
            banner_path = resource_path("banner.png")
            if os.path.exists(banner_path):
                pil_image = Image.open(banner_path)
                if pil_image.mode != 'RGBA':
                    pil_image = pil_image.convert('RGBA')
                pil_image.thumbnail((440, 96), Image.Resampling.LANCZOS)
                bio = BytesIO()
                pil_image.save(bio, format='PNG')
                bio.seek(0)
                banner_photo = tk.PhotoImage(data=bio.getvalue())
        except Exception:
            pass
        inner_frame = tk.Frame(banner_frame, bg=self.colors['background'])
        inner_frame.pack(expand=True)
        if banner_photo:
            banner_label = tk.Label(inner_frame, image=banner_photo,
                                    bg=self.colors['background'])
            banner_label.image = banner_photo
            banner_label.pack(pady=4)
        else:
            fallback_label = tk.Label(inner_frame, text="MoldEZ",
                                      font=("Helvetica", 46, "bold"),
                                      fg=self.colors['primary'],
                                      bg=self.colors['background'])
            fallback_label.pack()
        subtitle_label = tk.Label(
            inner_frame, text="Professional Culture Analysis Solution",
            font=("Segoe UI", 11, "italic"),
            fg=self.colors['subtext'], bg=self.colors['background'])
        subtitle_label.pack(pady=3)
        self.banner_container = inner_frame
        self.banner_image_label = banner_label if banner_photo else None
        self.banner_fallback_label = fallback_label if not banner_photo else None
        self.banner_subtitle_label = subtitle_label
        self.update_banner()
        # Notebook is configured.
        style = ttk.Style()
        self._configure_scrollbar_style()
        style.configure("Modern.TNotebook",
                        background=self.colors['background'], borderwidth=0)
        style.configure("Modern.TNotebook.Tab",
                        font=("Segoe UI", 10, "bold"), padding=[14, 6])
        self.notebook = ttk.Notebook(main_container, style="Modern.TNotebook")
        self.notebook.pack(expand=True, fill=tk.BOTH)
        self.main_tab = tk.Frame(self.notebook, bg=self.colors['background'])
        self.notebook.add(self.main_tab, text="🔬 Data Processing")
        self.sessions_tab = tk.Frame(self.notebook,
                                     bg=self.colors['background'])
        self.notebook.add(self.sessions_tab, text="📊 Sessions")
        self.automation_tab = tk.Frame(self.notebook,
                                       bg=self.colors['background'])
        self.notebook.add(self.automation_tab, text="🤖 Automation")
        self.setup_main_tab()
        self.setup_sessions_tab()
        self.setup_automation_tab()

    # UI helpers are provided.
    def create_card(self, parent, title, height=None):
        outer = tk.Frame(parent, bg=self.colors['background'])
        outer.pack(fill=tk.X, pady=(0, 14))
        card = tk.Frame(outer, bg=self.colors['card'],
                        highlightbackground=self.colors['border'],
                        highlightthickness=1)
        card.pack(fill=tk.X, padx=1, pady=1)
        if height:
            card.configure(height=height)
            card.pack_propagate(False)
        if title:
            hdr = tk.Frame(card, bg=self.colors['card'])
            hdr.pack(fill=tk.X, padx=18, pady=(12, 2))
            tk.Label(hdr, text=title, font=("Segoe UI", 11, "bold"),
                     fg=self.colors['primary'],
                     bg=self.colors['card']).pack(side=tk.LEFT)
        content = tk.Frame(card, bg=self.colors['card'])
        content.pack(fill=tk.BOTH, expand=True, padx=18, pady=(4, 16))
        return content

    _COLOR_MAP = {
        'tertiary': '#2ca24c',
        'quaternary':'#f0ad4e',
        'quinary': '#2596be',
        'senary': '#842aa2',
        'primary': '#2c3e50',
        'success': '#27ae60',
        'warning': '#f39c12',
        'danger': '#e74c3c',
        'secondary': '#3498db',
    }

    def create_button(self, parent, text, command, style="primary",
                      state=tk.NORMAL, **kwargs):
        bg = self._COLOR_MAP.get(style, '#2c3e50')
        btn = AppButton(parent, text=text, command=command,
                        bg_color=bg, state=state, palette_key=style, **kwargs)
        return btn

    def _configure_session_tree_style(self):
        style = ttk.Style()
        tree_bg = '#ffffff'
        tree_alt = '#edf2f7'
        heading_bg = '#f4f7fb'
        tree_fg = LIGHT_COLORS['text']
        selected_bg = LIGHT_COLORS['secondary']
        border = '#cbd5e1'

        style.configure(
            "Sess.Treeview",
            background=tree_bg,
            foreground=tree_fg,
            fieldbackground=tree_bg,
            rowheight=28,
            bordercolor=border,
            lightcolor=border,
            darkcolor=border
        )
        style.configure(
            "Sess.Treeview.Heading",
            font=("Segoe UI", 9, "bold"),
            background=heading_bg,
            foreground=tree_fg,
            bordercolor=border,
            lightcolor=border,
            darkcolor=border,
            relief=tk.FLAT
        )
        style.map(
            "Sess.Treeview",
            foreground=[('selected', tree_fg)],
            background=[('selected', selected_bg)]
        )
        style.map(
            "Sess.Treeview.Heading",
            background=[('active', heading_bg)],
            foreground=[('active', tree_fg)]
        )

        if hasattr(self, 'analyses_tree'):
            self.analyses_tree.configure(style="Sess.Treeview")
            self.analyses_tree.tag_configure('row_even', background=tree_bg,
                                             foreground=tree_fg)
            self.analyses_tree.tag_configure('row_odd', background=tree_alt,
                                             foreground=tree_fg)
            self._update_session_tree_columns()

    def _update_session_tree_columns(self, _event=None):
        if not hasattr(self, 'analyses_tree'):
            return
        try:
            total_width = self.analyses_tree.winfo_width()
            if total_width <= 40:
                total_width = self.session_tree_frame.winfo_width() - 18
            if total_width <= 40:
                return
            weights = {
                "sel": 6,
                "num": 7,
                "ts": 20,
                "file": 25,
                "diam": 11,
                "area": 12,
                "cov": 10,
                "pre": 13,
            }
            order = ("sel", "num", "ts", "file", "diam", "area", "cov", "pre")
            unit = total_width / float(sum(weights.values()))
            widths = {col: max(42, int(unit * weights[col])) for col in order}
            widths["sel"] = max(42, widths["sel"])
            widths["num"] = max(48, widths["num"])
            widths["diam"] = max(88, widths["diam"])
            widths["area"] = max(96, widths["area"])
            widths["cov"] = max(96, widths["cov"])
            widths["pre"] = max(110, widths["pre"])
            widths["ts"] = max(150, widths["ts"])
            widths["file"] = max(170, widths["file"])
            for col in order:
                anchor = tk.W if col in ("file", "pre") else tk.CENTER
                self.analyses_tree.column(col, width=widths[col],
                                          minwidth=max(40, widths[col] // 2),
                                          stretch=True, anchor=anchor)
        except Exception:
            pass

    def _configure_progressbar_style(self):
        self._ensure_ttk_theme()
        style = ttk.Style()
        style_specs = {
            "MoldEZ.Dark.Horizontal.TProgressbar": {
                "trough": '#1a2333',
                "bar": '#3fbf7f',
                "bar_active": '#6dd9a0',
                "border": '#3fbf7f',
            },
            "MoldEZ.Light.Horizontal.TProgressbar": {
                "trough": '#effaf2',
                "bar": '#18a558',
                "bar_active": '#32c06b',
                "border": '#18a558',
            },
            "MoldEZ.Dark.Batch.Horizontal.TProgressbar": {
                "trough": '#1a2333',
                "bar": '#3fbf7f',
                "bar_active": '#6dd9a0',
                "border": '#3fbf7f',
            },
            "MoldEZ.Light.Batch.Horizontal.TProgressbar": {
                "trough": '#effaf2',
                "bar": '#18a558',
                "bar_active": '#32c06b',
                "border": '#18a558',
            },
        }
        for style_name, colors in style_specs.items():
            style.configure(
                style_name,
                troughcolor=colors["trough"],
                background=colors["bar"],
                darkcolor=colors["bar"],
                lightcolor=colors["bar_active"],
                bordercolor=colors["border"],
                framecolor=colors["border"],
                relief='flat',
                thickness=12
            )
            style.map(
                style_name,
                background=[('active', colors["bar_active"])],
                lightcolor=[('active', colors["bar_active"])],
                darkcolor=[('active', colors["bar"])]
            )
        self._update_progressbar_widgets()

    def _update_progressbar_widgets(self):
        if self.dark_mode.get():
            trough = '#1a2333'
            fill = '#3fbf7f'
            accent = '#6dd9a0'
            border = '#3fbf7f'
        else:
            trough = '#effaf2'
            fill = '#18a558'
            accent = '#32c06b'
            border = '#18a558'
        if hasattr(self, 'progress'):
            try:
                self.progress.configure_colors(
                    bg_color=trough, fill_color=fill,
                    accent_color=accent, border_color=border)
            except Exception:
                pass
        if hasattr(self, 'batch_progress'):
            try:
                self.batch_progress.configure_colors(
                    bg_color=trough, fill_color=fill,
                    accent_color=accent, border_color=border)
            except Exception:
                pass

    def _show_detection_progress(self):
        if not hasattr(self, 'progress'):
            return
        if not self.progress.winfo_manager():
            self.progress.pack(fill=tk.X, pady=8)
        self.progress.start(10)

    def _hide_detection_progress(self):
        if not hasattr(self, 'progress'):
            return
        self.progress.stop()
        if self.progress.winfo_manager():
            self.progress.pack_forget()

    def _configure_scrollbar_style(self):
        self._ensure_ttk_theme()
        style = ttk.Style()

        if self.dark_mode.get():
            trough = '#1f2738'
            thumb = '#58667f'
            thumb_active = '#70819d'
        else:
            trough = '#eef2f7'
            thumb = '#bcc7d6'
            thumb_active = '#97a8be'

        for orient, sticky in (("Vertical", "ns"), ("Horizontal", "ew")):
            style_name = f"Modern.{orient}.TScrollbar"
            element = f"{orient}.Scrollbar"
            style.layout(
                style_name,
                [(f"{element}.trough", {
                    'sticky': sticky,
                    'children': [
                        (f"{element}.thumb", {'expand': '1', 'sticky': 'nswe'})
                    ]
                })]
            )
            style.configure(
                style_name,
                troughcolor=trough,
                background=thumb,
                bordercolor=trough,
                darkcolor=thumb,
                lightcolor=thumb,
                arrowcolor=thumb,
                gripcount=0,
                relief='flat',
                borderwidth=0,
                arrowsize=10,
                width=10
            )
            style.map(
                style_name,
                background=[('active', thumb_active), ('pressed', thumb_active)],
                darkcolor=[('active', thumb_active), ('pressed', thumb_active)],
                lightcolor=[('active', thumb_active), ('pressed', thumb_active)]
            )

        tab_bg = self.colors['card']
        tab_fg = self.colors['primary']
        selected_bg = self.colors['background']
        selected_fg = self.colors['text']
        border = self.colors['border']

        style.configure(
            "Modern.TNotebook",
            background=self.colors['background'],
            borderwidth=0,
            tabmargins=(0, 0, 0, 0)
        )
        style.configure(
            "Modern.TNotebook.Tab",
            font=("Segoe UI", 10, "bold"),
            padding=[14, 6],
            background=tab_bg,
            foreground=tab_fg,
            borderwidth=1,
            lightcolor=border,
            darkcolor=border,
            focuscolor=tab_bg
        )
        style.map(
            "Modern.TNotebook.Tab",
            background=[('selected', selected_bg), ('active', tab_bg)],
            foreground=[('selected', selected_fg), ('active', tab_fg)],
            lightcolor=[('selected', border)],
            darkcolor=[('selected', border)]
        )

    def _create_scrollbar(self, parent, orient="vertical", command=None):
        orient_name = "Vertical" if orient == "vertical" else "Horizontal"
        scrollbar = ttk.Scrollbar(
            parent,
            orient=orient,
            command=command,
            style=f"Modern.{orient_name}.TScrollbar"
        )
        return scrollbar

    def _ensure_ttk_theme(self):
        style = ttk.Style()
        theme_name = "MoldEZTheme"
        if theme_name not in style.theme_names():
            try:
                style.theme_create(theme_name, parent="clam")
            except Exception:
                pass
        try:
            if style.theme_use() != theme_name:
                style.theme_use(theme_name)
        except Exception:
            pass

    def _header_bg(self):
        return '#161d2b' if self.dark_mode.get() else LIGHT_COLORS['primary']

    def _update_header_theme(self):
        if hasattr(self, 'topbar'):
            self.topbar.configure(bg=self._header_bg())
        if hasattr(self, 'dm_frame'):
            self.dm_frame.configure(bg=self._header_bg())
        if hasattr(self, 'dm_label'):
            self.dm_label.configure(bg=self._header_bg(), fg='white')

    def _update_dark_mode_toggle(self):
        if not hasattr(self, 'dm_toggle_btn'):
            return
        self.dm_toggle_btn.update_colors(
            bg_color=self._header_bg(),
            on_color=self.colors['secondary'] if self.dark_mode.get() else '#3f6fa1',
            off_color='#7b8798' if not self.dark_mode.get() else '#4a5568',
            thumb_color='#ffffff'
        )
        self.dm_toggle_btn.sync()

    def _roboflow_confidence(self, value):
        try:
            return max(0, min(100, int(value)))
        except Exception:
            return 40

    def _predict_with_confidence(self, model, image_path, confidence_value):
        """
        Support both Roboflow confidence conventions.
        Official docs use 0-100, but some runtimes behave like 0-1.
        """
        confidence_percent = self._roboflow_confidence(confidence_value)
        attempts = [confidence_percent]
        confidence_fraction = round(confidence_percent / 100.0, 4)
        if confidence_fraction not in attempts:
            attempts.append(confidence_fraction)

        last_result = None
        last_error = None
        for threshold in attempts:
            try:
                result = model.predict(image_path, confidence=threshold).json()
                last_result = result
                if result.get('predictions'):
                    return result
            except Exception as e:
                last_error = e

        if last_result is not None:
            return last_result
        if last_error is not None:
            raise last_error
        return {'predictions': []}

    def _prediction_score(self, prediction):
        for key in ('score', 'confidence', 'probability'):
            value = prediction.get(key)
            if value is None:
                continue
            try:
                score = float(value)
            except (TypeError, ValueError):
                continue
            if score > 1.0:
                score /= 100.0
            return score
        return None

    def _filter_predictions_by_score(self, result, slider_value):
        threshold = max(0.0, min(1.0, float(slider_value) / 100.0))
        filtered = dict(result or {})
        predictions = filtered.get('predictions', []) or []
        filtered['predictions'] = [
            pred for pred in predictions
            if self._prediction_score(pred) is None
            or self._prediction_score(pred) >= threshold
        ]
        return filtered

    def _update_session_section_theme(self):
        fixed = dict(LIGHT_COLORS)
        if hasattr(self, 'session_tree_frame'):
            self.session_tree_frame.configure(
                bg=fixed['card'],
                fg=fixed['text'],
                highlightbackground=fixed['border']
            )
        if hasattr(self, 'session_tree_controls'):
            self.session_tree_controls.configure(bg=fixed['card'])
        if hasattr(self, 'session_time_period_frame'):
            self.session_time_period_frame.configure(bg=fixed['card'])
        if hasattr(self, 'analyses_tree'):
            self._configure_session_tree_style()

        def _apply_light_section(widget):
            cls = widget.__class__.__name__
            try:
                if cls in ('Frame', 'LabelFrame'):
                    widget.configure(bg=fixed['card'])
            except Exception:
                pass
            try:
                if cls == 'Label':
                    widget.configure(bg=fixed['card'], fg=fixed['text'])
            except Exception:
                pass
            try:
                if cls == 'Spinbox':
                    widget.configure(bg=fixed['input_bg'],
                                     fg=fixed['input_fg'],
                                     buttonbackground=fixed['card'])
            except Exception:
                pass
            try:
                if cls == 'Entry':
                    widget.configure(bg=fixed['input_bg'],
                                     fg=fixed['input_fg'],
                                     insertbackground=fixed['input_fg'],
                                     highlightbackground=fixed['border'])
            except Exception:
                pass
            for child in widget.winfo_children():
                _apply_light_section(child)

        for ref in ('session_tree_frame', 'session_tree_controls', 'session_time_period_frame'):
            if hasattr(self, ref):
                _apply_light_section(getattr(self, ref))

    def update_banner(self):
        banner_name = "banner-dark.png" if self.dark_mode.get() else "banner.png"
        banner_photo = None
        try:
            banner_path = resource_path(banner_name)
            if os.path.exists(banner_path):
                with Image.open(banner_path) as pil_image:
                    if pil_image.mode != 'RGBA':
                        pil_image = pil_image.convert('RGBA')
                    pil_image.thumbnail((440, 96), Image.Resampling.LANCZOS)
                    bio = BytesIO()
                    pil_image.save(bio, format='PNG')
                    bio.seek(0)
                    banner_photo = tk.PhotoImage(data=bio.getvalue())
        except Exception:
            banner_photo = None

        if banner_photo:
            if self.banner_image_label is None:
                self.banner_image_label = tk.Label(
                    self.banner_container, bg=self.colors['background'])
                self.banner_image_label.pack(pady=4, before=self.banner_subtitle_label)
            self.banner_image_label.configure(
                image=banner_photo, bg=self.colors['background'])
            self.banner_image_label.image = banner_photo
            if self.banner_fallback_label is not None:
                self.banner_fallback_label.pack_forget()
        elif self.banner_image_label is not None:
            self.banner_image_label.destroy()
            self.banner_image_label = None

        if self.dark_mode.get():
            if self.banner_image_label is None and self.banner_fallback_label is not None:
                self.banner_fallback_label.configure(
                    fg="white", bg=self.colors['background'])
                self.banner_fallback_label.pack(pady=4, before=self.banner_subtitle_label)
            elif self.banner_fallback_label is not None:
                self.banner_fallback_label.pack_forget()
            self.banner_subtitle_label.configure(
                fg="white", bg=self.colors['background'])
            if not self.banner_subtitle_label.winfo_manager():
                self.banner_subtitle_label.pack(pady=3)
        else:
            if self.banner_image_label is None and self.banner_fallback_label is not None:
                self.banner_fallback_label.configure(
                    fg=self.colors['primary'], bg=self.colors['background'])
                self.banner_fallback_label.pack(pady=4, before=self.banner_subtitle_label)
            self.banner_subtitle_label.configure(
                fg=self.colors['subtext'], bg=self.colors['background'])
            if not self.banner_subtitle_label.winfo_manager():
                self.banner_subtitle_label.pack(pady=3)

    def update_compare_time_mode(self):
        manual_enabled = self.compare_time_source_var.get() == "manual"
        state = "normal" if manual_enabled else "disabled"
        if hasattr(self, "compare_manual_hours_spinbox"):
            self.compare_manual_hours_spinbox.configure(state=state)
        if hasattr(self, "compare_manual_minutes_spinbox"):
            self.compare_manual_minutes_spinbox.configure(state=state)

    # Main tab is configured.
    def setup_main_tab(self):
        tab_container = tk.Frame(self.main_tab, bg=self.colors['background'])
        tab_container.pack(expand=True, fill=tk.BOTH)
        left_panel = tk.Frame(tab_container, width=520,
                              bg=self.colors['background'])
        left_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=False,
                        padx=(0, 16))
        left_panel.pack_propagate(False)
        middle_panel = tk.Frame(tab_container, width=540,
                                bg=self.colors['card'])
        middle_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        right_panel = tk.Frame(tab_container, width=430,
                               bg=self.colors['background'])
        right_panel.pack(side=tk.RIGHT, fill=tk.BOTH, expand=False,
                         padx=(16, 0))
        right_panel.pack_propagate(False)
        self.setup_left_panel(left_panel)
        self.setup_middle_panel(middle_panel)
        self.setup_right_panel(right_panel)

    def setup_left_panel(self, parent):
        scrollbar = self._create_scrollbar(parent, orient="vertical")
        scrollbar.pack(side="right", fill="y")
        canvas = tk.Canvas(parent, bg=self.colors['background'],
                           highlightthickness=0, bd=0)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.config(command=canvas.yview)
        sf = tk.Frame(canvas, bg=self.colors['background'])
        sf.bind("<Configure>",
                lambda e: canvas.configure(
                    scrollregion=canvas.bbox("all")))
        win = canvas.create_window((0, 0), window=sf, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.bind("<Configure>",
                    lambda e: canvas.itemconfigure(win, width=e.width))
        self._bind_mousewheel(canvas)
        # Step 1 is configured.
        c1 = self.create_card(sf, "Step 1 · Select Image")
        bf = tk.Frame(c1, bg=self.colors['card'])
        bf.pack(fill=tk.X, pady=(2, 6))
        bf.update_idletasks()
        self.select_image_btn = self.create_button(
            bf, "SELECT IMAGE", self.select_image, "tertiary")
        self.select_image_btn.pack(side=tk.LEFT)
        self.capture_image_btn = self.create_button(
            bf, "CAPTURE", self.capture_image, "senary")
        self.capture_image_btn.pack(side=tk.LEFT, padx=(8, 0))
        self.select_folder_btn = self.create_button(
            bf, "BATCH FOLDER", self.select_folder, "quinary")
        self.select_folder_btn.pack(side=tk.LEFT, padx=(8, 0))
        self.drop_zone = tk.Label(
            c1,
            text="Drag and drop an image here\nor click to browse",
            font=("Segoe UI", 10),
            fg=self.colors['subtext'],
            bg=self.colors['results_bg'],
            justify=tk.CENTER,
            cursor="hand2",
            highlightbackground=self.colors['border'],
            highlightthickness=1,
            padx=16, pady=14)
        self.drop_zone.pack(fill=tk.X, pady=(10, 4))
        self.drop_zone.bind("<Button-1>", lambda _e: self.select_image())
        self._setup_drop_target(self.drop_zone)
        self.image_status = tk.Label(c1, text="No image selected",
                                     fg=self.colors['subtext'],
                                     font=("Segoe UI", 10),
                                     bg=self.colors['card'])
        self.image_status.pack(anchor=tk.W, pady=(2, 0))

        # Step 1.5 is configured.
        c15 = self.create_card(sf, "Step 1.5 · Preprocessing (Optional)")
        if OPENCV_AVAILABLE:
            self.clahe_checkbox = tk.Checkbutton(
                c15,
                text="Enable CLAHE Enhancement (for poor lighting)",
                variable=self.use_clahe,
                font=("Segoe UI", 10),
                bg=self.colors['card'], fg=self.colors['primary'],
                activebackground=self.colors['card'],
                selectcolor=self.colors['card'])
            self.clahe_checkbox.pack(anchor=tk.W)
            pf = tk.Frame(c15, bg=self.colors['card'])
            pf.pack(fill=tk.X, pady=(6, 0))
            tk.Label(pf, text="Clip:", font=("Segoe UI", 9),
                     bg=self.colors['card'],
                     fg=self.colors['text']).pack(side=tk.LEFT)
            self.clip_scale = tk.Scale(pf, from_=1.0, to=4.0,
                                       resolution=0.1,
                                       variable=self.clahe_clip_limit,
                                       orient=tk.HORIZONTAL, length=110,
                                       bg=self.colors['card'],
                                       fg=self.colors['text'],
                                       troughcolor=self.colors['border'],
                                       highlightthickness=0)
            self.clip_scale.pack(side=tk.LEFT, padx=8)
            tk.Label(pf, text="Tile:", font=("Segoe UI", 9),
                     bg=self.colors['card'],
                     fg=self.colors['text']).pack(side=tk.LEFT,
                                                   padx=(14, 0))
            self.tile_scale = tk.Scale(pf, from_=4, to=16, resolution=2,
                                       variable=self.clahe_tile_size,
                                       orient=tk.HORIZONTAL, length=110,
                                       bg=self.colors['card'],
                                       fg=self.colors['text'],
                                       troughcolor=self.colors['border'],
                                       highlightthickness=0)
            self.tile_scale.pack(side=tk.LEFT, padx=8)
        else:
            tk.Label(c15,
                     text="⚠ OpenCV not available — pip install opencv-python",
                     font=("Segoe UI", 10), fg=self.colors['warning'],
                     bg=self.colors['card']).pack()

        # Advanced settings are configured.
        adv_card = self.create_card(sf, "")
        self.advanced_toggle_btn = self.create_button(
            adv_card, "▶ Advanced Detection Settings",
            self.toggle_advanced_settings, "primary")
        self.advanced_toggle_btn.pack(fill=tk.X, pady=4)
        self.advanced_content = tk.Frame(adv_card, bg=self.colors['card'])
        cf = tk.Frame(self.advanced_content, bg=self.colors['card'])
        cf.pack(fill=tk.X, pady=8)
        tk.Label(cf, text="Detection Confidence Thresholds",
                 font=("Segoe UI", 10, "bold"),
                 bg=self.colors['card'],
                 fg=self.colors['primary']).pack(anchor=tk.W)
        df = tk.Frame(cf, bg=self.colors['card'])
        df.pack(fill=tk.X, pady=4)
        tk.Label(df, text="Dish:", font=("Segoe UI", 9),
                 bg=self.colors['card'],
                 fg=self.colors['text']).pack(side=tk.LEFT)
        self.dish_scale = tk.Scale(df, from_=10, to=80, resolution=5,
                                   variable=self.dish_confidence,
                                   orient=tk.HORIZONTAL, length=140,
                                   bg=self.colors['card'],
                                   fg=self.colors['text'],
                                   troughcolor=self.colors['border'],
                                   highlightthickness=0)
        self.dish_scale.pack(side=tk.LEFT, padx=8)
        self.dish_conf_label = tk.Label(
            df, text=f"({self.dish_confidence.get()}%)",
            font=("Segoe UI", 8), bg=self.colors['card'],
            fg=self.colors['subtext'])
        self.dish_conf_label.pack(side=tk.LEFT)
        self.dish_confidence.trace("w", self.update_dish_conf_label)
        mf = tk.Frame(cf, bg=self.colors['card'])
        mf.pack(fill=tk.X, pady=4)
        tk.Label(mf, text="Culture:", font=("Segoe UI", 9),
                 bg=self.colors['card'],
                 fg=self.colors['text']).pack(side=tk.LEFT)
        self.Culture_scale = tk.Scale(mf, from_=20, to=80, resolution=5,
                                      variable=self.Culture_confidence,
                                      orient=tk.HORIZONTAL, length=140,
                                      bg=self.colors['card'],
                                      fg=self.colors['text'],
                                      troughcolor=self.colors['border'],
                                      highlightthickness=0)
        self.Culture_scale.pack(side=tk.LEFT, padx=8)
        self.Culture_conf_label = tk.Label(
            mf, text=f"({self.Culture_confidence.get()}%)",
            font=("Segoe UI", 8), bg=self.colors['card'],
            fg=self.colors['subtext'])
        self.Culture_conf_label.pack(side=tk.LEFT)
        self.Culture_confidence.trace("w", self.update_Culture_conf_label)

        # Step 2 is configured.
        c2 = self.create_card(sf, "Step 2 · Run Detection")
        det_row = tk.Frame(c2, bg=self.colors['card'])
        det_row.pack(fill=tk.X, pady=4)
        self.run_detection_btn = self.create_button(
            det_row, "RUN DETECTION",
            self.run_detection, "quinary", state=tk.DISABLED)
        self.run_detection_btn.pack(side=tk.LEFT)
        self.detection_status = tk.Label(det_row,
                                         text="Select an image first",
                                         fg=self.colors['subtext'],
                                         font=("Segoe UI", 10),
                                         bg=self.colors['card'])
        self.detection_status.pack(side=tk.LEFT, padx=12)
        self.progress = AnimatedProgressBar(
            c2, mode='indeterminate', height=14)
        self._update_progressbar_widgets()

        # Step 3 is configured.
        c3 = self.create_card(sf, "Step 3 · Plate Diameter")
        diam_row = tk.Frame(c3, bg=self.colors['card'])
        diam_row.pack(fill=tk.X, pady=4)
        tk.Label(diam_row, text="Diameter (mm):",
                 font=("Segoe UI", 10), bg=self.colors['card'],
                 fg=self.colors['text']).pack(side=tk.LEFT)
        self.diameter_var = tk.StringVar(value="100")
        tk.Entry(diam_row, textvariable=self.diameter_var, width=8,
                 font=("Segoe UI", 10),
                 bg=self.colors['input_bg'], fg=self.colors['input_fg'],
                 relief=tk.FLAT,
                 highlightbackground=self.colors['border'],
                 highlightthickness=1).pack(side=tk.LEFT, padx=8)
        self.calculate_btn = self.create_button(
            diam_row, "CALCULATE AREA",
            self.calculate_area, "quaternary", state=tk.DISABLED)
        self.calculate_btn.pack(side=tk.LEFT)

        # Results output is configured.
        c4 = self.create_card(sf, "Results", height=240)
        rc = tk.Frame(c4, bg=self.colors['card'])
        rc.pack(fill=tk.BOTH, expand=True)
        rc_sb = self._create_scrollbar(rc, orient="vertical")
        rc_sb.pack(side=tk.RIGHT, fill=tk.Y)
        rc_canvas = tk.Canvas(rc, bg=self.colors['results_bg'],
                              highlightthickness=0, bd=0)
        rc_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        rc_sb.config(command=rc_canvas.yview)
        self.results_frame = tk.Frame(rc_canvas,
                                      bg=self.colors['results_bg'])
        rc_canvas.create_window((0, 0), window=self.results_frame,
                                anchor="nw")
        self.results_text = tk.Text(self.results_frame,
                                    wrap=tk.WORD,
                                   font=("Consolas", 9),
                                    relief=tk.FLAT,
                                    bg=self.colors['results_bg'],
                                    fg=self.colors['text'],
                                    padx=12, pady=12, height=14)
        self.results_text.pack(fill=tk.BOTH, expand=True)
        rc_canvas.configure(yscrollcommand=rc_sb.set)
        self.results_frame.bind(
            "<Configure>",
            lambda e: rc_canvas.configure(
                scrollregion=rc_canvas.bbox("all")))
        self._bind_mousewheel(rc_canvas)
        self.results_text.tag_configure(
            "results", font=("Consolas", 9, "bold"),
            foreground=self.colors['secondary'])
        self.results_text.tag_configure(
            "highlight", foreground=self.colors['danger'],
            font=("Consolas", 10, "bold"))
        btn_row = tk.Frame(c4, bg=self.colors['card'])
        btn_row.pack(fill=tk.X, pady=(4, 0))
        self.save_btn = self.create_button(
            btn_row, "SAVE RESULTS", self.save_results,
            "primary", state=tk.DISABLED)
        self.save_btn.pack(side=tk.LEFT)
        self.create_button(btn_row, "CLEAR", self.clear_results,
                           "primary").pack(side=tk.LEFT, padx=(8, 0))

    def _bind_realtime_pipeline_callbacks(self):
        for var in (
                self.use_clahe, self.clahe_clip_limit, self.clahe_tile_size,
                self.dish_confidence, self.Culture_confidence):
            try:
                var.trace_add("write", self._schedule_pipeline_refresh)
            except Exception:
                var.trace("w", self._schedule_pipeline_refresh)

    def _schedule_pipeline_refresh(self, *_):
        if not self.current_image_path:
            return
        if self._reprocess_after_id is not None:
            try:
                self.root.after_cancel(self._reprocess_after_id)
            except Exception:
                pass
        self._reprocess_after_id = self.root.after(
            500, self._run_realtime_pipeline)

    def _run_realtime_pipeline(self):
        self._reprocess_after_id = None
        if not self.current_image_path:
            return
        if self.dish_model and self.Culture_model:
            self.run_detection(realtime=True)
        else:
            self.show_image_preview()

    # Middle panel is configured.
    def setup_middle_panel(self, parent):
        sb = self._create_scrollbar(parent, orient="vertical")
        sb.pack(side="right", fill="y")
        canvas = tk.Canvas(parent, bg=self.colors['card'],
                           highlightthickness=0, bd=0)
        canvas.pack(side="left", fill="both", expand=True)
        sb.config(command=canvas.yview)
        sf = tk.Frame(canvas, bg=self.colors['card'])
        sf.bind("<Configure>",
                lambda e: canvas.configure(
                    scrollregion=canvas.bbox("all")))
        win = canvas.create_window((0, 0), window=sf, anchor="nw")
        canvas.configure(yscrollcommand=sb.set)
        canvas.bind("<Configure>",
                    lambda e: canvas.itemconfigure(win, width=e.width))
        self._bind_mousewheel(canvas)
        tk.Label(sf, text="DETECTION RESULTS",
                 font=("Segoe UI", 16, "bold"),
                 fg=self.colors['primary'],
                 bg=self.colors['card']).pack(pady=(18, 8))
        img_outer = tk.Frame(sf, bg=self.colors['results_bg'],
                             highlightbackground=self.colors['border'],
                             highlightthickness=1)
        img_outer.pack(padx=28, pady=10, expand=True, fill=tk.NONE)
        self.image_display_frame = tk.Frame(
            img_outer, bg=self.colors['results_bg'], width=440, height=440)
        self.image_display_frame.pack_propagate(False)
        self.image_display_frame.pack(expand=True)
        self.image_display = tk.Label(
            self.image_display_frame,
            text="Image will appear here\nafter detection",
            font=("Segoe UI", 12), fg=self.colors['subtext'],
            bg=self.colors['results_bg'])
        self.image_display.pack(expand=True, fill=tk.BOTH, anchor='center')
        self.detection_info = tk.Label(
            sf, text="", font=("Segoe UI", 11, "bold"),
            fg=self.colors['success'], bg=self.colors['card'])
        self.detection_info.pack(pady=6)
        sum_frame = tk.Frame(sf, bg=self.colors['card'])
        sum_frame.pack(pady=6)
        ca_row = tk.Frame(sum_frame, bg=self.colors['card'])
        ca_row.pack()
        tk.Label(ca_row, text="CULTURE AREA: ",
                 font=("Segoe UI", 13, "bold"),
                 fg=self.colors['text'],
                 bg=self.colors['card']).pack(side=tk.LEFT)
        self.Culture_area_value = tk.Label(
            ca_row, text="N/A", font=("Segoe UI", 13, "bold"),
            fg=self.colors['success'], bg=self.colors['card'])
        self.Culture_area_value.pack(side=tk.LEFT)
        cov_row = tk.Frame(sum_frame, bg=self.colors['card'])
        cov_row.pack()
        tk.Label(cov_row, text="COVERAGE: ",
                 font=("Segoe UI", 13, "bold"),
                 fg=self.colors['text'],
                 bg=self.colors['card']).pack(side=tk.LEFT)
        self.coverage_value = tk.Label(
            cov_row, text="N/A", font=("Segoe UI", 13, "bold"),
            fg=self.colors['success'], bg=self.colors['card'])
        self.coverage_value.pack(side=tk.LEFT)
        self.analysis_num_label = tk.Label(
            sum_frame, text="Analysis #N/A added to history",
            font=("Segoe UI", 9), fg=self.colors['subtext'],
            bg=self.colors['card'])
        self.analysis_num_label.pack(pady=2)
        # Legend is configured.
        leg = tk.Frame(sf, bg=self.colors['card'])
        leg.pack(pady=10)
        tk.Label(leg, text="Legend", font=("Segoe UI", 10, "bold"),
                 bg=self.colors['card'],
                 fg=self.colors['primary']).pack()
        leg_items = tk.Frame(leg, bg=self.colors['card'])
        leg_items.pack(pady=6)
        for col, label in [(self.colors['success'], "Petri Dish"),
                           (self.colors['danger'], "Culture Colonies")]:
            f = tk.Frame(leg_items, bg=self.colors['card'])
            f.pack(side=tk.LEFT, padx=20)
            c = tk.Canvas(f, width=20, height=20,
                          bg=self.colors['card'], highlightthickness=0)
            c.pack(side=tk.LEFT)
            c.create_oval(2, 2, 18, 18, fill=col, outline="")
            tk.Label(f, text=label, font=("Segoe UI", 10),
                     bg=self.colors['card'],
                     fg=self.colors['text']).pack(side=tk.LEFT, padx=(6, 0))
        btn_row = tk.Frame(sf, bg=self.colors['card'])
        btn_row.pack(pady=10)
        self.save_image_btn = self.create_button(
            btn_row, "SAVE IMAGE",
            self.save_detection_image, "primary", state=tk.DISABLED)
        self.save_image_btn.pack(side=tk.LEFT)
        self.create_button(btn_row, "RESET",
                           self.reset_analysis, "danger").pack(
            side=tk.LEFT, padx=(10, 0))

    # Visualization panel is configured.
    def setup_right_panel(self, parent):
        vc = tk.Frame(parent, bg=self.colors['background'])
        vc.pack(expand=True, fill=tk.BOTH)
        v_sb = self._create_scrollbar(vc, orient="vertical")
        v_sb.pack(side=tk.RIGHT, fill=tk.Y)
        v_canvas = tk.Canvas(vc, bg=self.colors['background'],
                             highlightthickness=0, bd=0)
        v_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        v_sb.config(command=v_canvas.yview)
        v_canvas.configure(yscrollcommand=v_sb.set)
        vf = tk.Frame(v_canvas, bg=self.colors['background'])
        win = v_canvas.create_window((0, 0), window=vf, anchor="nw")
        v_canvas.bind("<Configure>",
                      lambda e: v_canvas.itemconfigure(win, width=e.width))
        vf.bind("<Configure>",
                lambda e: v_canvas.configure(
                    scrollregion=v_canvas.bbox("all")))
        self._bind_mousewheel(v_canvas)
        tk.Label(vf, text="DATA VISUALIZATION",
                 font=("Segoe UI", 16, "bold"),
                 fg=self.colors['primary'],
                 bg=self.colors['background']).pack(pady=(4, 14))
        if MATPLOTLIB_AVAILABLE:
            self.fig, (self.ax1, self.ax2) = plt.subplots(
                2, 1, figsize=(4, 6))
            self.fig.patch.set_facecolor(self.colors['background'])
            self.viz_canvas_widget = FigureCanvasTkAgg(self.fig, vf)
            self.viz_canvas_widget.get_tk_widget().config(
                bd=0, highlightthickness=0, relief='flat')
            self.viz_canvas_widget.get_tk_widget().pack(
                fill=tk.BOTH, expand=True)
            self.refresh_visualization()
        else:
            tk.Label(vf,
                     text="Matplotlib not available.\npip install matplotlib",
                     font=("Segoe UI", 11),
                     fg=self.colors['subtext'],
                     bg=self.colors['background']).pack(expand=True)

    # Visualization is handled.
    def refresh_visualization(self):
        if not MATPLOTLIB_AVAILABLE or not hasattr(self, 'fig'):
            return
        self.ax1.clear()
        self.ax2.clear()
        bg = self.colors['background']
        self.fig.patch.set_facecolor(bg)
        if not self.analysis_history:
            for ax, msg in [(self.ax1, 'No analysis data yet'),
                            (self.ax2, 'Run analyses to see trend')]:
                ax.text(0.5, 0.5, msg, ha='center', va='center',
                        fontsize=11, color=self.colors['subtext'])
                ax.set_facecolor(bg)
                ax.set_title(ax.get_title() or '', fontweight='bold')
        else:
            cur = self.analysis_history[-1]
            ca = cur['Culture_area']
            pa = cur['plate_area']
            clean = max(pa - ca, 0)
            tot = pa
            cp = (clean / tot * 97) if tot > 0 else 0
            mp = (ca / tot * 103) if tot > 0 else 0
            self.ax1.pie([cp, mp], labels=['Clean', 'Culture'],
                         colors=['#27ae60', '#e74c3c'],
                         autopct='%1.0f%%', startangle=90,
                         textprops={'color': self.colors['text']})
            self.ax1.set_title('Area Breakdown', fontweight='bold',
                               pad=12, color=self.colors['text'])
            self.ax1.set_facecolor(bg)
            areas = [i['Culture_area'] for i in self.analysis_history]
            n = len(areas)
            xr = min(10, n)
            disp_areas = areas[-xr:]
            x_vals = range(max(1, n - xr + 1), n + 1)
            self.ax2.plot(x_vals, [round(a, 2) for a in disp_areas],
                          'o-', color='#e74c3c', linewidth=2, markersize=7)
            self.ax2.set_title('Area Trend', fontweight='bold',
                               pad=12, color=self.colors['text'])
            self.ax2.set_ylabel('Culture Area (mm²)',
                                color=self.colors['subtext'])
            self.ax2.set_xlabel('Analysis #',
                                color=self.colors['subtext'])
            self.ax2.tick_params(colors=self.colors['subtext'])
            self.ax2.set_facecolor(self.colors['results_bg'])
            self.ax2.grid(True, alpha=0.2)
            if disp_areas:
                self.ax2.set_ylim(0, max(disp_areas) * 1.25)
        for ax in [self.ax1, self.ax2]:
            for spine in ax.spines.values():
                spine.set_visible(False)
        self.fig.tight_layout()
        self.viz_canvas_widget.draw()

    def refresh_colony_visualization(self):
        if not MATPLOTLIB_AVAILABLE or not hasattr(self, 'colony_fig'):
            return
        self.colony_ax1.clear()
        self.colony_ax2.clear()
        bg = self.colors['background']
        self.colony_fig.patch.set_facecolor(bg)
        if not self.colony_count_results:
            for ax, msg in [(self.colony_ax1, 'No colony count data yet'),
                            (self.colony_ax2, 'Run counting from session analyses')]:
                ax.text(0.5, 0.5, msg, ha='center', va='center',
                        fontsize=11, color=self.colors['subtext'])
                ax.set_facecolor(bg)
        else:
            labels = [str(r['analysis_index']) for r in self.colony_count_results]
            counts = [r['colony_count'] for r in self.colony_count_results]
            self.colony_ax1.bar(labels, counts, color='#3498db', width=0.65)
            self.colony_ax1.set_title('Colony Count by Analysis',
                                      fontweight='bold', pad=12,
                                      color=self.colors['text'])
            self.colony_ax1.set_ylabel('Colonies', color=self.colors['subtext'])
            self.colony_ax1.tick_params(colors=self.colors['subtext'])
            self.colony_ax1.set_facecolor(self.colors['results_bg'])
            self.colony_ax1.grid(True, axis='y', alpha=0.18)

            running = []
            total = 0
            for count in counts:
                total += count
                running.append(total)
            self.colony_ax2.plot(labels, running, 'o-',
                                 color='#27ae60', linewidth=2, markersize=7)
            self.colony_ax2.set_title('Cumulative Colony Count',
                                      fontweight='bold', pad=12,
                                      color=self.colors['text'])
            self.colony_ax2.set_ylabel('Total Colonies',
                                       color=self.colors['subtext'])
            self.colony_ax2.set_xlabel('Analysis #',
                                       color=self.colors['subtext'])
            self.colony_ax2.tick_params(colors=self.colors['subtext'])
            self.colony_ax2.set_facecolor(self.colors['results_bg'])
            self.colony_ax2.grid(True, alpha=0.18)
        for ax in [self.colony_ax1, self.colony_ax2]:
            for spine in ax.spines.values():
                spine.set_visible(False)
        self.colony_fig.tight_layout()
        self.colony_canvas_widget.draw()

    # Sessions tab is configured.
    def setup_sessions_tab(self):
        sb = self._create_scrollbar(self.sessions_tab, orient="vertical")
        sb.pack(side="right", fill="y")
        canvas = tk.Canvas(self.sessions_tab, bg=self.colors['background'],
                           highlightthickness=0, bd=0)
        canvas.pack(side="left", fill="both", expand=True)
        sb.config(command=canvas.yview)
        sc = tk.Frame(canvas, bg=self.colors['background'])
        sc.bind("<Configure>",
                lambda e: canvas.configure(
                    scrollregion=canvas.bbox("all")))
        win = canvas.create_window((0, 0), window=sc, anchor="nw")
        canvas.configure(yscrollcommand=sb.set)
        canvas.bind("<Configure>",
                    lambda e: canvas.itemconfigure(win, width=e.width))
        self._bind_mousewheel(canvas)
        tk.Label(sc, text="ANALYSIS DASHBOARD",
                 font=("Segoe UI", 16, "bold"),
                 fg=self.colors['primary'],
                 bg=self.colors['background']).pack(pady=(12, 10))
        # Control bar is configured.
        ctrl = tk.Frame(sc, bg=self.colors['card'],
                        highlightbackground=self.colors['border'],
                        highlightthickness=1)
        ctrl.pack(fill=tk.X, pady=(0, 12), padx=10)
        ci = tk.Frame(ctrl, bg=self.colors['card'])
        ci.pack(pady=10, padx=10)
        tk.Label(ci, text="Session Name:",
                 font=("Segoe UI", 10, "bold"),
                 bg=self.colors['card'],
                 fg=self.colors['primary']).pack(side=tk.LEFT,
                                                  padx=(0, 6))
        self.session_name_var = tk.StringVar(
            value=self.current_session_name)
        tk.Entry(ci, textvariable=self.session_name_var, width=18,
                 font=("Segoe UI", 10),
                 bg=self.colors['input_bg'], fg=self.colors['input_fg'],
                 relief=tk.FLAT,
                 highlightbackground=self.colors['border'],
                 highlightthickness=1).pack(side=tk.LEFT, padx=(0, 14))
        for label, cmd, sty in [
            ("Save Session", self.save_session, "primary"),
            ("Load Session", self.load_session, "primary"),
            ("Export PDF", self.export_pdf, "senary"),
        ]:
            self.create_button(ci, label, cmd, sty).pack(
                side=tk.LEFT, padx=4)
        # Session treeview is configured.
        tree_frame = tk.LabelFrame(
            sc, text="Current Session Analyses",
            font=("Segoe UI", 11, "bold"),
            fg=self.colors['primary'],
            bg=self.colors['card'],
            bd=0, relief=tk.FLAT,
            highlightbackground=self.colors['border'],
            highlightthickness=1)
        tree_frame.pack(fill=tk.X, expand=False, padx=10, pady=8)
        self.session_tree_frame = tree_frame
        self._configure_session_tree_style()
        cols = ("sel", "num", "ts", "file", "diam", "area", "cov", "pre")
        heads = ("✓", "#", "Timestamp", "Filename",
                 "Diam (mm)", "Area (mm²)", "Coverage (%)", "Processing")
        widths = (40, 72, 122, 122, 92, 92, 92, 92)
        self.analyses_tree = ttk.Treeview(
            tree_frame, columns=cols, show="headings",
            style="Sess.Treeview", selectmode='none', height=5)
        for c, h, w in zip(cols, heads, widths):
            self.analyses_tree.heading(c, text=h)
            anchor = tk.W if c in ("file", "pre") else tk.CENTER
            self.analyses_tree.column(c, width=w, minwidth=max(40, w // 2),
                                      stretch=True, anchor=anchor)
        t_sb = self._create_scrollbar(tree_frame, orient="vertical",
                                      command=self.analyses_tree.yview)
        t_sb.pack(side=tk.RIGHT, fill=tk.Y)
        self.analyses_tree.configure(yscrollcommand=t_sb.set)
        self.analyses_tree.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.analyses_tree.bind("<Configure>", self._update_session_tree_columns)
        self.analyses_tree.bind("<Button-1>", self.on_tree_click)
        self.analyses_tree.bind("<Double-1>", self.on_analysis_double_click)
        self.root.after(50, self._update_session_tree_columns)
        # Tree controls are configured.
        bot = tk.Frame(tree_frame, bg=self.colors['card'])
        bot.pack(fill=tk.X, pady=(4, 8), padx=5)
        self.session_tree_controls = bot
        self.create_button(bot, "Delete Selected",
                           self.delete_selected_analyses,
                           "danger").pack(side=tk.LEFT)
        tp_frame = tk.Frame(bot, bg=self.colors['card'])
        tp_frame.pack(side=tk.LEFT, padx=(18, 4))
        self.session_time_period_frame = tp_frame
        tk.Label(tp_frame, text="Compare Using:",
                 font=("Segoe UI", 9, "bold"),
                 bg=self.colors['card'],
                 fg=self.colors['primary']).pack(side=tk.LEFT)
        tk.Radiobutton(
            tp_frame,
            text="Timestamps",
            variable=self.compare_time_source_var,
            value="timestamps",
            command=self.update_compare_time_mode,
            font=("Segoe UI", 9),
            bg=self.colors['card'],
            fg=self.colors['text'],
            selectcolor=self.colors['input_bg'],
            activebackground=self.colors['card'],
            activeforeground=self.colors['text']
        ).pack(side=tk.LEFT, padx=(8, 2))
        tk.Radiobutton(
            tp_frame,
            text="Manual",
            variable=self.compare_time_source_var,
            value="manual",
            command=self.update_compare_time_mode,
            font=("Segoe UI", 9),
            bg=self.colors['card'],
            fg=self.colors['text'],
            selectcolor=self.colors['input_bg'],
            activebackground=self.colors['card'],
            activeforeground=self.colors['text']
        ).pack(side=tk.LEFT, padx=(4, 6))
        tk.Label(tp_frame, text="Time Period:",
                 font=("Segoe UI", 9, "bold"),
                 bg=self.colors['card'],
                 fg=self.colors['primary']).pack(side=tk.LEFT)
        tk.Label(tp_frame, text=" h:",
                 font=("Segoe UI", 9),
                 bg=self.colors['card'],
                 fg=self.colors['text']).pack(side=tk.LEFT)
        self.compare_manual_hours_spinbox = tk.Spinbox(
            tp_frame, from_=0, to=999, width=4,
            textvariable=self.manual_time_hours_var,
            font=("Segoe UI", 9),
            bg=self.colors['input_bg'],
            fg=self.colors['input_fg'])
        self.compare_manual_hours_spinbox.pack(side=tk.LEFT, padx=(2, 0))
        tk.Label(tp_frame, text=" min:",
                 font=("Segoe UI", 9),
                 bg=self.colors['card'],
                 fg=self.colors['text']).pack(side=tk.LEFT)
        self.compare_manual_minutes_spinbox = tk.Spinbox(
            tp_frame, from_=0, to=59, width=4,
            textvariable=self.manual_time_minutes_var,
            font=("Segoe UI", 9),
            bg=self.colors['input_bg'],
            fg=self.colors['input_fg'])
        self.compare_manual_minutes_spinbox.pack(side=tk.LEFT, padx=(2, 6))
        tk.Label(tp_frame, text="(timestamps uses analysis dates)",
                 font=("Segoe UI", 8),
                 fg=self.colors['subtext'],
                 bg=self.colors['card']).pack(side=tk.LEFT)
        self.update_compare_time_mode()
        self.compare_btn = self.create_button(
            bot, "Compare Selected",
            self.compare_selected_analyses, "secondary")
        self.compare_btn.pack(side=tk.LEFT, padx=(10, 0))
        # Comparison results are configured.
        self.comparison_frame = tk.LabelFrame(
            sc, text="Comparison Results",
            font=("Segoe UI", 11, "bold"),
            fg=self.colors['primary'],
            bg=self.colors['card'], bd=0, relief=tk.FLAT,
            highlightbackground=self.colors['border'],
            highlightthickness=1)
        self.comparison_frame.pack(fill=tk.BOTH, expand=True,
                                   padx=10, pady=8)
        comp_sb = self._create_scrollbar(self.comparison_frame,
                                         orient="vertical")
        comp_sb.pack(side=tk.RIGHT, fill=tk.Y)
        comp_c = tk.Canvas(self.comparison_frame, bg=self.colors['card'],
                           highlightthickness=0, bd=0)
        comp_c.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        comp_sb.config(command=comp_c.yview)
        self.comparison_inner = tk.Frame(comp_c, bg=self.colors['card'])
        comp_c.create_window((0, 0), window=self.comparison_inner,
                             anchor="nw")
        comp_c.configure(yscrollcommand=comp_sb.set)
        self.comparison_inner.bind(
            "<Configure>",
            lambda e: comp_c.configure(
                scrollregion=comp_c.bbox("all")))
        self._bind_mousewheel(comp_c)
        tk.Label(sc,
                 text="Double-click an analysis to view the detected image.\n"
                      "Save sessions to compare growth patterns over time.",
                 font=("Segoe UI", 11), fg=self.colors['text'],
                 bg=self.colors['background'],
                 anchor='center').pack(pady=12)

    # Automation tab is configured.
    def setup_automation_tab(self):
        c = tk.Frame(self.automation_tab, bg=self.colors['background'])
        c.pack(expand=True, fill=tk.BOTH, padx=24, pady=24)
        tk.Label(c, text="AUTOMATION SETTINGS",
                 font=("Segoe UI", 16, "bold"),
                 fg=self.colors['primary'],
                 bg=self.colors['background']).pack(pady=10)
        iv = tk.Frame(c, bg=self.colors['background'])
        iv.pack(pady=10)
        tk.Label(iv, text="Capture Interval:",
                 font=("Segoe UI", 11),
                 bg=self.colors['background'],
                 fg=self.colors['text']).pack(side=tk.LEFT)
        for lbl, var, hi in [("Hours", self.auto_hours_var, 23),
                              ("Minutes", self.auto_minutes_var, 59)]:
            tk.Label(iv, text=f" {lbl}:",
                     bg=self.colors['background'],
                     fg=self.colors['text']).pack(side=tk.LEFT)
            tk.Spinbox(iv, from_=0, to=hi, width=5, textvariable=var,
                       bg=self.colors['input_bg'],
                       fg=self.colors['input_fg']).pack(side=tk.LEFT)
        bf = tk.Frame(c, bg=self.colors['background'])
        bf.pack(pady=10)
        self.start_auto_btn = self.create_button(
            bf, "Start Automation", self.start_automation, "success")
        self.start_auto_btn.pack(side=tk.LEFT)
        self.stop_auto_btn = self.create_button(
            bf, "Stop Automation", self.stop_automation,
            "danger", state=tk.DISABLED)
        self.stop_auto_btn.pack(side=tk.LEFT, padx=(10, 0))
        self.auto_timer_label = tk.Label(
            c, text="Automation not running",
            font=("Segoe UI Semibold", 14),
            fg=self.colors['primary'],
            bg=self.colors['background'])
        self.auto_timer_label.pack(pady=20)

    def setup_colony_tab(self):
        tab_container = tk.Frame(self.colony_tab, bg=self.colors['background'])
        tab_container.pack(expand=True, fill=tk.BOTH)

        left_panel = tk.Frame(tab_container, width=440,
                              bg=self.colors['background'])
        left_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=False,
                        padx=(0, 16))
        left_panel.pack_propagate(False)

        middle_panel = tk.Frame(tab_container, width=560,
                                bg=self.colors['card'])
        middle_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        right_panel = tk.Frame(tab_container, width=430,
                               bg=self.colors['background'])
        right_panel.pack(side=tk.RIGHT, fill=tk.BOTH, expand=False,
                         padx=(16, 0))
        right_panel.pack_propagate(False)

        self.setup_colony_left_panel(left_panel)
        self.setup_colony_middle_panel(middle_panel)
        self.setup_colony_right_panel(right_panel)

    def setup_colony_left_panel(self, parent):
        sb = self._create_scrollbar(parent, orient="vertical")
        sb.pack(side="right", fill="y")
        canvas = tk.Canvas(parent, bg=self.colors['background'],
                           highlightthickness=0, bd=0)
        canvas.pack(side="left", fill="both", expand=True)
        sb.config(command=canvas.yview)
        sf = tk.Frame(canvas, bg=self.colors['background'])
        sf.bind("<Configure>",
                lambda e: canvas.configure(
                    scrollregion=canvas.bbox("all")))
        win = canvas.create_window((0, 0), window=sf, anchor="nw")
        canvas.configure(yscrollcommand=sb.set)
        canvas.bind("<Configure>",
                    lambda e: canvas.itemconfigure(win, width=e.width))
        self._bind_mousewheel(canvas)

        intro = self.create_card(sf, "Session Input")
        tk.Label(intro,
                 text="Run colony counting on analyses already listed in the Sessions table. If rows are checked there, only those analyses are used.",
                 font=("Segoe UI", 10),
                 fg=self.colors['text'],
                 bg=self.colors['card'],
                 justify=tk.LEFT, wraplength=350).pack(anchor=tk.W)
        ctrl = tk.Frame(intro, bg=self.colors['card'])
        ctrl.pack(fill=tk.X, pady=(12, 2))
        self.count_selected_btn = self.create_button(
            ctrl, "COUNT SELECTED", self.run_colony_count_selected, "secondary")
        self.count_selected_btn.pack(side=tk.LEFT)
        self.count_all_btn = self.create_button(
            ctrl, "COUNT ALL", self.run_colony_count_all, "primary")
        self.count_all_btn.pack(side=tk.LEFT, padx=(8, 0))

        settings = self.create_card(sf, "Counting Settings")
        tk.Label(settings, text="Colony Confidence:",
                 font=("Segoe UI", 10, "bold"),
                 fg=self.colors['primary'],
                 bg=self.colors['card']).pack(anchor=tk.W)
        row = tk.Frame(settings, bg=self.colors['card'])
        row.pack(fill=tk.X, pady=(6, 0))
        self.colony_conf_scale = tk.Scale(
            row, from_=5, to=95, resolution=5,
            variable=self.colony_confidence,
            orient=tk.HORIZONTAL, length=210,
            bg=self.colors['card'], fg=self.colors['text'],
            troughcolor=self.colors['border'],
            highlightthickness=0)
        self.colony_conf_scale.pack(side=tk.LEFT)
        self.colony_conf_label = tk.Label(
            row, text=f"({self.colony_confidence.get()}%)",
            font=("Segoe UI", 9),
            fg=self.colors['subtext'],
            bg=self.colors['card'])
        self.colony_conf_label.pack(side=tk.LEFT, padx=(8, 0))
        self.colony_confidence.trace("w", self.update_colony_conf_label)

        summary = self.create_card(sf, "Count Summary", height=300)
        self.colony_summary_text = tk.Text(
            summary, wrap=tk.WORD,
            font=("Consolas", 9),
            relief=tk.FLAT,
            bg=self.colors['results_bg'],
            fg=self.colors['text'],
            padx=12, pady=12,
            height=15)
        self.colony_summary_text.pack(fill=tk.BOTH, expand=True)
        self.colony_summary_text.insert(
            tk.END,
            "No colony counting run yet.\n\nUse the Sessions tab to select analyses, then run counting here.")
        self.colony_summary_text.configure(state=tk.DISABLED)

    def setup_colony_middle_panel(self, parent):
        sb = self._create_scrollbar(parent, orient="vertical")
        sb.pack(side="right", fill="y")
        canvas = tk.Canvas(parent, bg=self.colors['card'],
                           highlightthickness=0, bd=0)
        canvas.pack(side="left", fill="both", expand=True)
        sb.config(command=canvas.yview)
        sf = tk.Frame(canvas, bg=self.colors['card'])
        sf.bind("<Configure>",
                lambda e: canvas.configure(
                    scrollregion=canvas.bbox("all")))
        win = canvas.create_window((0, 0), window=sf, anchor="nw")
        canvas.configure(yscrollcommand=sb.set)
        canvas.bind("<Configure>",
                    lambda e: canvas.itemconfigure(win, width=e.width))
        self._bind_mousewheel(canvas)

        tk.Label(sf, text="COUNT PREVIEW",
                 font=("Segoe UI", 15, "bold"),
                 fg=self.colors['primary'],
                 bg=self.colors['card']).pack(pady=(18, 8))
        img_outer = tk.Frame(sf, bg=self.colors['results_bg'],
                             highlightbackground=self.colors['border'],
                             highlightthickness=1)
        img_outer.pack(padx=28, pady=10, expand=True, fill=tk.NONE)
        self.colony_preview_frame = tk.Frame(
            img_outer, bg=self.colors['results_bg'], width=460, height=460)
        self.colony_preview_frame.pack_propagate(False)
        self.colony_preview_frame.pack(expand=True)
        self.colony_preview_label = tk.Label(
            self.colony_preview_frame,
            text="Annotated colony-count preview\nwill appear here",
            font=("Segoe UI", 12),
            fg=self.colors['subtext'],
            bg=self.colors['results_bg'])
        self.colony_preview_label.pack(expand=True, fill=tk.BOTH)
        self.colony_preview_info = tk.Label(
            sf, text="No colony count available",
            font=("Segoe UI", 11, "bold"),
            fg=self.colors['secondary'],
            bg=self.colors['card'])
        self.colony_preview_info.pack(pady=6)

    def setup_colony_right_panel(self, parent):
        vc = tk.Frame(parent, bg=self.colors['background'])
        vc.pack(expand=True, fill=tk.BOTH)
        v_sb = self._create_scrollbar(vc, orient="vertical")
        v_sb.pack(side=tk.RIGHT, fill=tk.Y)
        v_canvas = tk.Canvas(vc, bg=self.colors['background'],
                             highlightthickness=0, bd=0)
        v_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        v_sb.config(command=v_canvas.yview)
        v_canvas.configure(yscrollcommand=v_sb.set)
        vf = tk.Frame(v_canvas, bg=self.colors['background'])
        win = v_canvas.create_window((0, 0), window=vf, anchor="nw")
        v_canvas.bind("<Configure>",
                      lambda e: v_canvas.itemconfigure(win, width=e.width))
        vf.bind("<Configure>",
                lambda e: v_canvas.configure(
                    scrollregion=v_canvas.bbox("all")))
        self._bind_mousewheel(v_canvas)

        tk.Label(vf, text="COUNT VISUALIZATION",
                 font=("Segoe UI", 15, "bold"),
                 fg=self.colors['primary'],
                 bg=self.colors['background']).pack(pady=(4, 14))
        if MATPLOTLIB_AVAILABLE:
            self.colony_fig, (self.colony_ax1, self.colony_ax2) = plt.subplots(
                2, 1, figsize=(4.2, 6.2))
            self.colony_fig.patch.set_facecolor(self.colors['background'])
            self.colony_canvas_widget = FigureCanvasTkAgg(self.colony_fig, vf)
            self.colony_canvas_widget.get_tk_widget().config(
                bd=0, highlightthickness=0, relief='flat')
            self.colony_canvas_widget.get_tk_widget().pack(
                fill=tk.BOTH, expand=True)
            self.refresh_colony_visualization()
        else:
            tk.Label(vf,
                     text="Matplotlib not available.\npip install matplotlib",
                     font=("Segoe UI", 11),
                     fg=self.colors['subtext'],
                     bg=self.colors['background']).pack(expand=True)

    # Header is retained.
    def create_header(self, parent):
        pass
    def load_logo(self):
        pass

    # Automation is performed.
    def start_automation(self):
        h = self.auto_hours_var.get()
        m = self.auto_minutes_var.get()
        if h == 0 and m == 0:
            self.show_message("warning", "Warning",
                              "Please set a valid interval.")
            return
        self.remaining_seconds = h * 3600 + m * 60
        self.automation_running = True
        self.start_auto_btn.config(state=tk.DISABLED)
        self.stop_auto_btn.config(state=tk.NORMAL)
        self.auto_countdown()

    def stop_automation(self):
        if self.timer_id:
            try:
                self.root.after_cancel(self.timer_id)
            except Exception:
                pass
            self.timer_id = None
        self.automation_running = False
        self.start_auto_btn.config(state=tk.NORMAL)
        self.stop_auto_btn.config(state=tk.DISABLED)
        self.auto_timer_label.config(text="Automation stopped")

    def auto_countdown(self):
        if self.remaining_seconds > 0:
            h = self.remaining_seconds // 3600
            m = (self.remaining_seconds % 3600) // 60
            s = self.remaining_seconds % 60
            self.auto_timer_label.config(
                text=f"Next capture in {h:02d}:{m:02d}:{s:02d}")
            self.remaining_seconds -= 1
            self.timer_id = self.root.after(1000, self.auto_countdown)
        else:
            self.capture_and_analyze_auto()
            h = self.auto_hours_var.get()
            m = self.auto_minutes_var.get()
            self.remaining_seconds = h * 3600 + m * 60
            self.auto_countdown()

    def capture_and_analyze_auto(self):
        if not OPENCV_AVAILABLE:
            self.show_message("error", "Error",
                              "OpenCV not available for camera capture.")
            return
        try:
            cap = cv2.VideoCapture(0)
            if not cap.isOpened():
                raise Exception("Cannot open camera")
            ret, frame = cap.read()
            if not ret:
                raise Exception("Cannot capture frame")
            cap.release()
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            path = os.path.join(self.results_dir, f"capture_{ts}.jpg")
            cv2.imwrite(path, frame)
            self.current_image_path = path
            self.run_detection_auto()
        except Exception as e:
            self.show_message("error", "Capture Error",
                              f"Failed to capture: {e}")

    def run_detection_auto(self):
        if not self.current_image_path or \
                not self.dish_model or not self.Culture_model:
            return
        def _thread():
            pp = None
            try:
                if not self.is_internet_available():
                    return
                pp = self.apply_clahe_preprocessing(self.current_image_path)
                dr = self._predict_with_confidence(
                    self.dish_model, pp, self.dish_confidence.get())
                dr = self._filter_predictions_by_score(
                    dr, self.dish_confidence.get())
                cr = self._predict_with_confidence(
                    self.Culture_model, pp, self.Culture_confidence.get())
                cr = self._filter_predictions_by_score(
                    cr, self.Culture_confidence.get())
                pp_px, cp_px = self.process_predictions_simple(dr, cr)
                self.detected_plate_pixels = pp_px
                self.detected_Culture_pixels = cp_px
                if pp_px > 0:
                    self.create_visualization_simple()
                    self.calculate_area_auto()
            except Exception:
                pass
            finally:
                if pp and pp != self.current_image_path \
                        and os.path.exists(pp):
                    try:
                        os.remove(pp)
                    except Exception:
                        pass
        threading.Thread(target=_thread, daemon=True).start()

    def calculate_area_auto(self):
        if self.detected_plate_pixels == 0:
            return
        d = 100.0
        pa = 3.14159 * (d / 2) ** 2
        scale = pa / self.detected_plate_pixels
        ca = self.detected_Culture_pixels * scale
        cov = (self.detected_Culture_pixels /
               self.detected_plate_pixels) * 105
        data = {
            'timestamp': datetime.now(),
            'filename': os.path.basename(self.current_image_path),
            'source_image_path': self.current_image_path,
            'coverage': cov,
            'Culture_area': ca,
            'plate_area': pa,
            'plate_pixels': self.detected_plate_pixels,
            'Culture_pixels': self.detected_Culture_pixels,
            'diameter': d,
            'preprocessing': 'CLAHE Enhanced' if self.use_clahe.get()
                             else 'Standard'
        }
        self.analysis_history.append(data)
        with self._image_lock:
            img_snap = self.processed_image
        if img_snap:
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            ip = os.path.join(
                self.results_dir,
                f"analysis_{len(self.analysis_history)}_{ts}.png")
            img_snap.save(ip)
            data['detection_image_path'] = ip
        else:
            data['detection_image_path'] = None
        self.root.after(0, self.refresh_visualization)
        self.root.after(0, self.update_analyses_tree)

    # Tree interactions are handled.
    def on_tree_click(self, event):
        item = self.analyses_tree.identify_row(event.y)
        if not item:
            return
        if self.analyses_tree.identify_column(event.x) == '#1':
            vals = list(self.analyses_tree.item(item)['values'])
            vals[0] = '[ ]' if vals[0] == '[âœ”]' else '[âœ”]'
            self.analyses_tree.item(item, values=vals)

    def get_selected_indices(self):
        return [self.analyses_tree.index(i)
                for i in self.analyses_tree.get_children()
                if self.analyses_tree.item(i)['values'][0] == '[âœ”]']

    def delete_selected_analyses(self):
        idxs = sorted(self.get_selected_indices(), reverse=True)
        if not idxs:
            self.show_message("warning", "Warning",
                              "No analyses selected.")
            return
        for i in idxs:
            del self.analysis_history[i]
        self.update_analyses_tree()
        self.refresh_visualization()
        self.show_message("info", "Done", "Selected analyses deleted.")

    def compare_selected_analyses(self):
        for w in self.comparison_inner.winfo_children():
            w.destroy()
        idxs = self.get_selected_indices()
        if len(idxs) != 2:
            self.show_message("warning", "Warning",
                              "Select exactly two analyses to compare.")
            return
        sel = sorted([self.analysis_history[i] for i in idxs],
                     key=lambda a: a['timestamp'])
        img_row = tk.Frame(self.comparison_inner, bg=self.colors['card'])
        img_row.pack(pady=10)
        for a in sel:
            f = tk.Frame(img_row, bg=self.colors['card'])
            f.pack(side=tk.LEFT, padx=20)
            ip = a.get('detection_image_path')
            if ip and os.path.exists(ip):
                img = Image.open(ip)
                img.thumbnail((280, 280), Image.Resampling.LANCZOS)
                ph = ImageTk.PhotoImage(img)
                lbl = tk.Label(f, image=ph, bg=self.colors['card'])
                lbl.image = ph
                lbl.pack()
            else:
                tk.Label(f, text="No image",
                         bg=self.colors['card'],
                         fg=self.colors['subtext']).pack()
            tk.Label(f, text=a['filename'],
                    font=("Segoe UI", 9, "bold"),
                     bg=self.colors['card'],
                     fg=self.colors['text']).pack()
            tk.Label(f,
                     text=f"Ø {a['diameter']:.1f} mm | "
                          f"{a['Culture_area']:.2f} mm² | "
                          f"{a['coverage']:.2f}%",
                    font=("Segoe UI", 9),
                     bg=self.colors['card'],
                     fg=self.colors['subtext']).pack()
        prev, curr = sel
        cov_diff = curr['coverage'] - prev['coverage']
        area_diff = curr['Culture_area'] - prev['Culture_area']
        if self.compare_time_source_var.get() == "manual":
            th = self.manual_time_hours_var.get()
            tm = self.manual_time_minutes_var.get()
            total_manual = th * 60 + tm
            if total_manual <= 0:
                self.show_message(
                    "warning", "Warning",
                    "Enter a manual comparison time greater than zero.")
                return
            time_hours = total_manual / 60.0
            time_src = f"Manual ({th}h {tm}m = {time_hours:.3f} h)"
        else:
            dt = (curr['timestamp'] - prev['timestamp']).total_seconds()
            time_hours = dt / 3600 if dt > 0 else 1
            time_src = f"Auto from timestamps ({time_hours:.3f} h)"
        pr = (prev['Culture_area'] / np.pi) ** 0.5
        cr_ = (curr['Culture_area'] / np.pi) ** 0.5
        rad_rate = (cr_ - pr) / time_hours
        area_rate = area_diff / time_hours
        info = tk.Frame(self.comparison_inner, bg=self.colors['card'])
        info.pack(pady=8, padx=16)
        rows = [
            ("Time Period Used", time_src),
            ("Coverage Change", f"{cov_diff:+.2f}%"),
            ("Area Change", f"{area_diff:+.2f} mm²"),
            ("Radial Growth Rate", f"{rad_rate:.4f} mm/hour"),
            ("Areal Growth Rate", f"{area_rate:.4f} mm²/hour"),
        ]
        for label, val in rows:
            r = tk.Frame(info, bg=self.colors['card'])
            r.pack(fill=tk.X, pady=2)
            tk.Label(r, text=label + ":",
                    font=("Segoe UI", 10, "bold"), width=22,
                     anchor=tk.W, bg=self.colors['card'],
                     fg=self.colors['primary']).pack(side=tk.LEFT)
            tk.Label(r, text=val, font=("Segoe UI", 10),
                     bg=self.colors['card'],
                     fg=self.colors['text']).pack(side=tk.LEFT)

    # Advanced toggles are handled.
    def toggle_advanced_settings(self):
        if self.show_advanced.get():
            self.advanced_content.pack_forget()
            self.advanced_toggle_btn.set_text("▶ Advanced Detection Settings")
            self.show_advanced.set(False)
        else:
            self.advanced_content.pack(fill=tk.X, pady=8)
            self.advanced_toggle_btn.set_text("â–¼ Advanced Detection Settings")
            self.show_advanced.set(True)

    def update_dish_conf_label(self, *_):
        self.dish_conf_label.config(
            text=f"({self.dish_confidence.get()}%)")

    def update_Culture_conf_label(self, *_):
        self.Culture_conf_label.config(
            text=f"({self.Culture_confidence.get()}%)")

    def update_colony_conf_label(self, *_):
        if hasattr(self, 'colony_conf_label'):
            self.colony_conf_label.config(
                text=f"({self.colony_confidence.get()}%)")

    def get_colony_input_analyses(self, selected_only=True):
        if not self.analysis_history:
            return []
        if selected_only:
            idxs = self.get_selected_indices()
            if idxs:
                return [(i + 1, self.analysis_history[i]) for i in idxs]
        return [(i, a) for i, a in enumerate(self.analysis_history, 1)]

    def resolve_analysis_image_path(self, analysis):
        for key in ('source_image_path', 'detection_image_path'):
            path = analysis.get(key)
            if path and os.path.exists(path):
                return path
        return None

    def render_colony_overlay(self, image_path, predictions):
        try:
            with Image.open(image_path) as raw:
                img = raw.convert('RGB')
        except Exception:
            return None
        draw = ImageDraw.Draw(img)
        for i, pred in enumerate(predictions, 1):
            x = pred.get('x')
            y = pred.get('y')
            w = pred.get('width')
            h = pred.get('height')
            if None in (x, y, w, h):
                continue
            x0 = x - w / 2
            y0 = y - h / 2
            x1 = x + w / 2
            y1 = y + h / 2
            draw.rectangle((x0, y0, x1, y1), outline='#ff4d5a', width=2)
            draw.text((x0 + 4, max(4, y0 - 16)), str(i), fill='#ff4d5a')
        return img

    def set_colony_preview(self, image, text):
        if image is None:
            self.colony_preview_label.config(
                image='', text="Unable to render colony preview")
            self.colony_preview_label.image = None
            self.colony_preview_info.config(text=text)
            return
        preview = image.copy()
        preview.thumbnail((460, 460), Image.Resampling.LANCZOS)
        photo = ImageTk.PhotoImage(preview)
        self.colony_preview_label.config(image=photo, text="")
        self.colony_preview_label.image = photo
        self.colony_preview_info.config(text=text)

    def update_colony_summary(self, lines):
        self.colony_summary_text.config(state=tk.NORMAL)
        self.colony_summary_text.delete(1.0, tk.END)
        self.colony_summary_text.insert(tk.END, "\n".join(lines))
        self.colony_summary_text.config(state=tk.DISABLED)

    def run_colony_count_selected(self):
        self.run_colony_counting(selected_only=True)

    def run_colony_count_all(self):
        self.run_colony_counting(selected_only=False)

    def run_colony_counting(self, selected_only=True):
        if not self.colony_model:
            self.show_message("error", "Error",
                              "Colony counting model is not ready yet.")
            return
        analyses = self.get_colony_input_analyses(selected_only=selected_only)
        if not analyses:
            self.show_message("warning", "Warning",
                              "No session analyses available for colony counting.")
            return
        self.count_selected_btn.config(state=tk.DISABLED)
        self.count_all_btn.config(state=tk.DISABLED)
        self.update_colony_summary(["Counting colonies...", "",
                                    "Selected analyses are being processed."])

        def _thread():
            results = []
            preview_image = None
            preview_text = "No colony detections found"
            try:
                if not self.is_internet_available():
                    raise RuntimeError("No internet connection.")
                for analysis_index, analysis in analyses:
                    image_path = self.resolve_analysis_image_path(analysis)
                    if not image_path:
                        continue
                    result = self._predict_with_confidence(
                        self.colony_model, image_path,
                        self.colony_confidence.get())
                    preds = result.get('predictions', []) or []
                    colony_count = len(preds)
                    results.append({
                        'analysis_index': analysis_index,
                        'filename': analysis.get('filename',
                                                 os.path.basename(image_path)),
                        'image_path': image_path,
                        'colony_count': colony_count,
                        'predictions': preds,
                    })
                    if preview_image is None:
                        preview_image = self.render_colony_overlay(image_path, preds)
                        preview_text = (
                            f"Analysis #{analysis_index} â€¢ {colony_count} colonies")
                self.root.after(
                    0, lambda: self.finish_colony_counting(
                        results, preview_image, preview_text, selected_only))
            except Exception as e:
                self.root.after(0, lambda: self.fail_colony_counting(str(e)))

        threading.Thread(target=_thread, daemon=True).start()

    def finish_colony_counting(self, results, preview_image, preview_text,
                               selected_only):
        self.count_selected_btn.config(state=tk.NORMAL)
        self.count_all_btn.config(state=tk.NORMAL)
        self.colony_count_results = results
        self.colony_preview_image = preview_image
        scope = "selected analyses" if selected_only else "all analyses"
        if not results:
            self.set_colony_preview(None, "No usable analysis images found")
            self.update_colony_summary([
                "No colony count results were produced.",
                "",
                f"Input scope: {scope}",
                "The selected analyses may not have accessible source or detection images."
            ])
        else:
            total = sum(r['colony_count'] for r in results)
            avg = total / len(results)
            lines = [
                f"Colony counting complete for {scope}.",
                "",
                f"Analyses processed: {len(results)}",
                f"Total colonies: {total}",
                f"Average colonies / analysis: {avg:.2f}",
                "",
            ]
            for r in results:
                lines.append(
                    f"#{r['analysis_index']} {r['filename']} -> {r['colony_count']} colonies")
            self.set_colony_preview(preview_image, preview_text)
            self.update_colony_summary(lines)
        self.refresh_colony_visualization()

    def fail_colony_counting(self, error_text):
        self.count_selected_btn.config(state=tk.NORMAL)
        self.count_all_btn.config(state=tk.NORMAL)
        self.update_colony_summary([
            "Colony counting failed.",
            "",
            error_text
        ])
        self.show_message("error", "Colony Counting Error", error_text)

    # Model is initialized.
    def initialize_models(self):
        def _init():
            try:
                if not self.is_internet_available():
                    self.update_status("No internet â€“ cannot load models.")
                    return
                self.update_status("Initializing models…")
                with suppress_stdout():
                    rf = Roboflow(api_key=ROBOFLOW_API_KEY)
                    self.dish_model = (rf.workspace()
                                        .project(DISH_MODEL_ID)
                                        .version(DISH_MODEL_VERSION).model)
                    self.Culture_model = (rf.workspace()
                                           .project(Culture_MODEL_ID)
                                           .version(Culture_MODEL_VERSION).model)
                self.update_status("Models ready ✓")
            except Exception as e:
                self.update_status(f"Init failed: {e}")
                self.show_message("error", "Initialization Error",
                                  f"Failed to load models:\n{e}")
        threading.Thread(target=_init, daemon=True).start()

    def update_status(self, msg):
        self.root.after(0,
                        lambda: self.detection_status.config(text=msg))

    # Image selection is handled.
    def select_image(self):
        fp = filedialog.askopenfilename(
            title="Select Image",
            filetypes=[("Images",
                        "*.jpg *.jpeg *.png *.bmp *.gif *.webp *.tif *.tiff *.heic *.HEIC")])
        if fp:
            self.load_selected_image(fp)

    def capture_image(self):
        if not OPENCV_AVAILABLE:
            self.show_message("error", "Error",
                              "OpenCV not available â€“ "
                              "pip install opencv-python")
            return
        try:
            cap = cv2.VideoCapture(0)
            if not cap.isOpened():
                raise Exception("Cannot open camera")
            ret, frame = cap.read()
            cap.release()
            if not ret:
                raise Exception("Cannot capture frame")
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            fp = os.path.join(self.results_dir, f"capture_{ts}.jpg")
            cv2.imwrite(fp, frame)
            self.current_image_path = fp
            self.image_status.config(
                text=os.path.basename(fp), fg=self.colors['success'])
            self.run_detection_btn.config(state=tk.NORMAL)
            self.update_status("Ready to run detection")
            self.reset_detection_data()
            self.show_image_preview()
        except Exception as e:
            self.show_message("error", "Capture Error", str(e))

    def select_folder(self):
        folder = filedialog.askdirectory(title="Select Folder")
        if not folder:
            return
        imgs = [f for f in os.listdir(folder)
                if f.lower().endswith(
                    ('.jpg', '.jpeg', '.png', '.bmp', '.gif',
                     '.webp', '.tif', '.tiff', '.heic'))]
        if not imgs:
            self.show_message("info", "Empty",
                              "No image files found.")
            return
        self.batch_cancelled = False
        dlg = tk.Toplevel(self.root)
        dlg.title("Batch Processing")
        dlg.configure(bg=self.colors['background'])
        tk.Label(dlg, text="Processing images…",
                 bg=self.colors['background'],
                 fg=self.colors['text']).pack(pady=10)
        self.batch_progress = AnimatedProgressBar(
            dlg, mode='determinate', maximum=len(imgs), width=320, height=14)
        self._update_progressbar_widgets()
        self.batch_progress.pack(pady=8, padx=20)
        self.create_button(dlg, "Cancel",
                           self.cancel_batch, "danger").pack(pady=8)
        self.progress_dialog = dlg
        threading.Thread(target=self.process_folder_thread,
                         args=(folder, imgs), daemon=True).start()

    def process_folder_thread(self, folder, imgs):
        for i, fn in enumerate(imgs):
            if self.batch_cancelled:
                break
            self.root.after(0,
                            lambda v=i+1: self.update_batch_progress(v))
            ip = os.path.join(folder, fn)
            self.current_image_path = ip
            pp = None
            try:
                pp = self.apply_clahe_preprocessing(ip)
                dr = self._predict_with_confidence(
                    self.dish_model, pp, self.dish_confidence.get())
                dr = self._filter_predictions_by_score(
                    dr, self.dish_confidence.get())
                cr = self._predict_with_confidence(
                    self.Culture_model, pp, self.Culture_confidence.get())
                cr = self._filter_predictions_by_score(
                    cr, self.Culture_confidence.get())
                pp_px, cp_px = self.process_predictions_simple(dr, cr)
                self.detected_plate_pixels = pp_px
                self.detected_Culture_pixels = cp_px
                if pp_px > 0:
                    self.create_visualization_simple()
                    d = 100.0
                    pa = 3.14159 * (d / 2) ** 2
                    scale = pa / pp_px
                    ca = cp_px * scale
                    cov = (cp_px / pp_px) * 105
                    data = {
                        'timestamp': datetime.now(),
                        'filename': fn,
                        'source_image_path': ip,
                        'coverage': cov,
                        'Culture_area': ca,
                        'plate_area': pa,
                        'plate_pixels': pp_px,
                        'Culture_pixels': cp_px,
                        'diameter': d,
                        'preprocessing': 'CLAHE Enhanced'
                                         if self.use_clahe.get()
                                         else 'Standard'
                    }
                    self.analysis_history.append(data)
                    with self._image_lock:
                        img_snap = self.processed_image
                    if img_snap:
                        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                        sp = os.path.join(
                            self.results_dir,
                            f"batch_{i+1}_{ts}.png")
                        img_snap.save(sp)
                        data['detection_image_path'] = sp
                    self.root.after(0, self.refresh_visualization)
                    self.root.after(0, self.update_analyses_tree)
            except Exception:
                pass
            finally:
                if pp and pp != ip and os.path.exists(pp):
                    try:
                        os.remove(pp)
                    except Exception:
                        pass
        self.root.after(0, self.close_progress_dialog)

    def update_batch_progress(self, v):
        self.batch_progress.set_value(v)

    def cancel_batch(self):
        self.batch_cancelled = True

    def close_progress_dialog(self):
        if hasattr(self, 'progress_dialog'):
            self.progress_dialog.destroy()
        if not self.batch_cancelled:
            self.show_message("info", "Done",
                              "Batch processing complete.")

    # Preview and reset are handled.
    def show_image_preview(self):
        try:
            img = Image.open(self.current_image_path)
            img.thumbnail((440, 440), Image.Resampling.LANCZOS)
            ph = ImageTk.PhotoImage(img)
            self.image_display.config(image=ph, text="")
            self.image_display.image = ph
            self.detection_info.config(
                text="Image loaded — ready for analysis")
        except Exception:
            self.image_display.config(text="Error loading preview")

    def reset_detection_data(self):
        self.detected_plate_pixels = 0
        self.detected_Culture_pixels = 0
        self.plate_mask = None
        self.Culture_mask = None
        with self._image_lock:
            self.processed_image = None
        self.calculate_btn.config(state=tk.DISABLED)
        self.save_image_btn.config(state=tk.DISABLED)

    # CLAHE is processed.
    def apply_clahe_preprocessing(self, path):
        if not OPENCV_AVAILABLE or not self.use_clahe.get():
            return path
        try:
            img = cv2.imread(path)
            if img is None:
                return path
            lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
            l, a, b = cv2.split(lab)
            clip_limit = max(0.1, float(self.clahe_clip_limit.get()))
            tile_size = max(1, int(round(float(self.clahe_tile_size.get()))))
            clahe = cv2.createCLAHE(
                clipLimit=clip_limit,
                tileGridSize=(tile_size, tile_size))
            lc = clahe.apply(l)
            bgr = cv2.cvtColor(cv2.merge((lc, a, b)),
                               cv2.COLOR_LAB2BGR)
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            out = os.path.join(self.results_dir,
                               f"temp_clahe_{ts}.jpg")
            cv2.imwrite(out, bgr)
            self.preprocessed_image_path = out
            return out
        except Exception as e:
            print(f"CLAHE error: {e}")
            return path

    # Detection is processed.
    def run_detection(self, realtime=False):
        if not self.current_image_path or \
                not self.dish_model or not self.Culture_model:
            if not realtime:
                self.show_message("error", "Error",
                                  "Image or models not ready.")
            return
        self._detection_generation += 1
        generation = self._detection_generation

        def _thread():
            self.detected_plate_pixels = 0
            self.detected_Culture_pixels = 0
            self.plate_mask = None
            self.Culture_mask = None
            pp = None
            try:
                if not self.is_internet_available():
                    self.update_status("No internet connection.")
                    return
                self.root.after(0, self._show_detection_progress)
                self.root.after(
                    0, lambda: self.run_detection_btn.config(
                        state=tk.DISABLED))
                pp = self.apply_clahe_preprocessing(
                    self.current_image_path)
                dc = self._roboflow_confidence(self.dish_confidence.get())
                cc = self._roboflow_confidence(self.Culture_confidence.get())
                self.update_status("Detecting petri dish…")
                dr = self._predict_with_confidence(
                    self.dish_model, pp, dc)
                dr = self._filter_predictions_by_score(
                    dr, self.dish_confidence.get())
                self.update_status("Detecting culture colonies…")
                cr = self._predict_with_confidence(
                    self.Culture_model, pp, cc)
                cr = self._filter_predictions_by_score(
                    cr, self.Culture_confidence.get())
                if generation != self._detection_generation:
                    return
                self.update_status("Processing…")
                pp_px, cp_px = self.process_predictions_simple(dr, cr)
                if generation != self._detection_generation:
                    return
                self.detected_plate_pixels = pp_px
                self.detected_Culture_pixels = cp_px
                if pp_px > 0:
                    self.update_status("Building visualization…")
                    self.create_visualization_simple()
                    cov = (cp_px / pp_px * 105) if pp_px > 0 else 0
                    self.update_status("Detection complete ✓")
                    self.root.after(0, lambda: self.calculate_btn.config(
                        state=tk.NORMAL))
                    self.root.after(0, lambda: self.save_image_btn.config(
                        state=tk.NORMAL))
                    pre = "CLAHE" if self.use_clahe.get() else "Standard"
                    s = (f"\n{'─'*55}\nDETECTION RESULTS\n{'─'*55}\n\n"
                         f"Processing : {pre}\n"
                         f"Dish conf : {self.dish_confidence.get()}%\n"
                         f"Culture conf: {self.Culture_confidence.get()}%\n"
                         f"Dish found : Yes\n"
                         f"Plate px : {pp_px:,}\n"
                         f"Culture px : {cp_px:,}\n"
                         f"Coverage : {cov:.2f}%\n\n"
                         "Enter diameter â†’ Calculate Area.")
                    if realtime:
                        self.root.after(0, lambda: (
                            self.results_text.delete(1.0, tk.END),
                            self.results_text.insert(tk.END, s)))
                    else:
                        self.root.after(0, lambda: self.results_text.insert(
                            tk.END, s))
                else:
                    self.update_status(
                        "No dish detected — adjust confidence?")
                    if not realtime:
                        self.show_message(
                            "warning", "Detection Failed",
                            "No petri dish detected.\n\n"
                            "Tips:\n"
                            "â€¢ Enable CLAHE preprocessing\n"
                            "â€¢ Lower confidence in Advanced Settings\n"
                            "â€¢ Ensure good image quality")
            except Exception as e:
                self.update_status(f"Failed: {e}")
                if not realtime:
                    self.show_message("error", "Detection Error",
                                      f"{e}\n\nCheck internet connection.")
            finally:
                self.root.after(0, self._hide_detection_progress)
                self.root.after(
                    0, lambda: self.run_detection_btn.config(
                        state=tk.NORMAL))
                if pp and pp != self.current_image_path \
                        and os.path.exists(pp):
                    try:
                        os.remove(pp)
                    except Exception:
                        pass
        threading.Thread(target=_thread, daemon=True).start()

    # Prediction is processed.
    def process_predictions_simple(self, dish_r, culture_r):
        plate_px = 0
        self.plate_mask = None
        try:
            if dish_r.get('predictions'):
                for pred in dish_r['predictions']:
                    if 'segmentation_mask' in pred:
                        md = pred['segmentation_mask']
                        if ',' in md:
                            md = md.split(',', 1)[1]
                        raw = base64.b64decode(md)
                        mi = Image.open(BytesIO(raw))
                        ma = np.array(mi)
                        if ma.ndim == 3:
                            ma = ma[:, :, 0]
                        self.plate_mask = (ma > 0).astype(np.uint8)
                        plate_px = np.sum(self.plate_mask == 1)
                        break
        except Exception as e:
            print(f"Dish pred error: {e}")
            return 0, 0
        if plate_px == 0:
            return 0, 0
        c_px = 0
        self.Culture_mask = None
        try:
            if culture_r.get('predictions'):
                combo = None
                for pred in culture_r['predictions']:
                    if 'segmentation_mask' in pred:
                        md = pred['segmentation_mask']
                        if ',' in md:
                            md = md.split(',', 1)[1]
                        raw = base64.b64decode(md)
                        mi = Image.open(BytesIO(raw))
                        ca = np.array(mi)
                        if ca.ndim == 3:
                            ca = ca[:, :, 0]
                        if self.plate_mask.shape != ca.shape:
                            cp = Image.fromarray(ca.astype(np.uint8))
                            cr = cp.resize(
                                (self.plate_mask.shape[1],
                                 self.plate_mask.shape[0]),
                                Image.NEAREST)
                            ca = np.array(cr)
                        combo = (ca > 0) if combo is None \
                            else combo | (ca > 0)
                if combo is not None:
                    inside = (self.plate_mask == 1) & combo
                    c_px = np.sum(inside)
                    self.Culture_mask = np.zeros_like(self.plate_mask)
                    self.Culture_mask[inside] = 1
        except Exception as e:
            print(f"Culture pred error: {e}")
            return plate_px, 0
        return plate_px, c_px

    # Overlay is processed.
    def _display_processed_image(self, img):
        """Must be called on the main thread."""
        ph = ImageTk.PhotoImage(img)
        self.image_display.config(image=ph, text="")
        self.image_display.image = ph

    def create_visualization_simple(self):
        """Builds the overlay image on the background thread, then schedules
        the Tk widget update on the main thread via root.after."""
        try:
            if self.use_clahe.get() and self.preprocessed_image_path \
                    and os.path.exists(self.preprocessed_image_path):
                if OPENCV_AVAILABLE:
                    ci = cv2.imread(self.preprocessed_image_path)
                    orig = Image.fromarray(
                        cv2.cvtColor(ci, cv2.COLOR_BGR2RGB))
                else:
                    orig = Image.open(self.preprocessed_image_path)
            else:
                orig = Image.open(self.current_image_path)
            if orig.mode != 'RGBA':
                orig = orig.convert('RGBA')
            overlay = Image.new('RGBA', orig.size, (0, 0, 0, 0))
            if self.plate_mask is not None:
                if self.plate_mask.shape != (orig.height, orig.width):
                    pm = Image.fromarray(
                        self.plate_mask.astype(np.uint8) * 255)
                    pm = pm.resize((orig.width, orig.height),
                                    Image.NEAREST)
                    pmv = np.array(pm)
                else:
                    pmv = self.plate_mask * 255
                pmv = pmv.astype(np.uint8)
                if OPENCV_AVAILABLE:
                    conts, _ = cv2.findContours(
                        pmv, cv2.RETR_EXTERNAL,
                        cv2.CHAIN_APPROX_SIMPLE)
                    if conts:
                        lc = max(conts, key=cv2.contourArea)
                        if len(lc) >= 5:
                            ell = cv2.fitEllipse(lc)
                            oa = np.array(overlay)
                            cen = (int(ell[0][0]), int(ell[0][1]))
                            axes = (int(ell[1][0]/2), int(ell[1][1]/2))
                            cv2.ellipse(oa, cen, axes, ell[2],
                                        0, 360, (50, 255, 50, 220), 3)
                            overlay = Image.fromarray(oa, 'RGBA')
                        else:
                            overlay = self._draw_boundary(overlay, pmv)
                    else:
                        overlay = self._draw_boundary(overlay, pmv)
                else:
                    overlay = self._draw_boundary(overlay, pmv)
            if self.Culture_mask is not None:
                if self.Culture_mask.shape != (orig.height, orig.width):
                    cm = Image.fromarray(
                        self.Culture_mask.astype(np.uint8) * 255)
                    cm = cm.resize((orig.width, orig.height),
                                    Image.NEAREST)
                    cmv = np.array(cm)
                else:
                    cmv = self.Culture_mask * 255
                cpx = np.where(cmv > 128)
                if len(cpx[0]) > 0:
                    oa = np.array(overlay)
                    oa[cpx[0], cpx[1]] = [255, 50, 50, 200]
                    overlay = Image.fromarray(oa, 'RGBA')
            result = Image.alpha_composite(orig, overlay).convert('RGB')
            with self._image_lock:
                self.processed_image = result
            disp = result.copy()
            disp.thumbnail((440, 440), Image.Resampling.LANCZOS)
            self.root.after(
                0, lambda d=disp: self._display_processed_image(d))
        except Exception as e:
            print(f"Viz error: {e}")
            try:
                img = Image.open(self.current_image_path)
                img.thumbnail((440, 440), Image.Resampling.LANCZOS)
                self.root.after(
                    0, lambda i=img: self._display_processed_image(i))
            except Exception:
                self.root.after(
                    0, lambda: self.image_display.config(
                        text="Unable to display image"))

    def _draw_boundary(self, overlay, mask):
        pa = mask > 128
        if SCIPY_AVAILABLE:
            pb = pa & ~ndimage.binary_erosion(pa, iterations=2)
        else:
            pb = pa
        bpx = np.where(pb)
        if len(bpx[0]) > 0:
            oa = np.array(overlay)
            oa[bpx[0], bpx[1]] = [50, 255, 50, 220]
            return Image.fromarray(oa, 'RGBA')
        return overlay

    # Area is calculated.
    def calculate_area(self):
        if self.detected_plate_pixels == 0:
            self.show_message("error", "Error",
                              "No plate detected — run detection first.")
            return
        try:
            ed = float(self.diameter_var.get())
            if ed <= 0:
                raise ValueError
            d = ed + 3
        except ValueError:
            self.show_message("error", "Error",
                              "Enter a valid positive diameter.")
            return
        pa = 3.14159 * (d / 2) ** 2
        scale = pa / self.detected_plate_pixels
        ca = self.detected_Culture_pixels * scale
        cov = (self.detected_Culture_pixels /
                 self.detected_plate_pixels) * 105
        data = {
            'timestamp': datetime.now(),
            'filename': os.path.basename(self.current_image_path),
            'source_image_path': self.current_image_path,
            'coverage': cov,
            'Culture_area': ca,
            'plate_area': pa,
            'plate_pixels': self.detected_plate_pixels,
            'Culture_pixels': self.detected_Culture_pixels,
            'diameter': ed,
            'preprocessing': 'CLAHE Enhanced' if self.use_clahe.get()
                             else 'Standard'
        }
        self.analysis_history.append(data)
        with self._image_lock:
            img_snap = self.processed_image
        if img_snap:
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            ip = os.path.join(
                self.results_dir,
                f"analysis_{len(self.analysis_history)}_{ts}.png")
            img_snap.save(ip)
            data['detection_image_path'] = ip
        else:
            data['detection_image_path'] = None
        res = (f"\n{'─'*55}\nANALYSIS RESULTS\n{'─'*55}\n\n"
               f"Image : {os.path.basename(self.current_image_path)}\n"
               f"Date : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
               f"Processing : {'CLAHE' if self.use_clahe.get() else 'Standard'}\n"
               f"Analysis # : {len(self.analysis_history)}\n\n"
               f"Dish conf : {self.dish_confidence.get()}%\n"
               f"Culture conf: {self.Culture_confidence.get()}%\n\n"
               f"Plate px : {self.detected_plate_pixels:,}\n"
               f"Culture px : {self.detected_Culture_pixels:,}\n"
               f"Coverage : {cov:.2f}%\n\n"
               f"Entered Ø : {ed:.1f} mm → adjusted {d:.1f} mm\n"
               f"Plate area : {pa:.2f} mm²\n"
               f"Scale : {scale:.6f} mm²/px\n")
        self.results_text.delete(1.0, tk.END)
        self.results_text.insert(tk.END, res, "results")
        self.results_text.insert(tk.END,
                                  f"Culture area: {ca:.2f} mm²\n",
                                  "highlight")
        self.save_btn.config(state=tk.NORMAL)
        if MATPLOTLIB_AVAILABLE:
            self.refresh_visualization()
        self.update_analyses_tree()
        self.Culture_area_value.config(text=f"{ca:.2f} mm²")
        self.coverage_value.config(text=f"{cov:.2f}%")
        self.analysis_num_label.config(
            text=f"Analysis #{len(self.analysis_history)} added to history")

    # Save and reset are handled.
    def clear_results(self):
        self.results_text.delete(1.0, tk.END)

    def reset_analysis(self):
        dlg = tk.Toplevel(self.root)
        dlg.title("Reset")
        dlg.configure(bg=self.colors['card'])
        dlg.resizable(False, False)
        tk.Label(dlg, text="Reset Analysis",
                 font=("Segoe UI Semibold", 12),
                 bg=self.colors['card'],
                 fg=self.colors['primary']).pack(pady=12, padx=24)
        tk.Label(dlg, text="Clear all data and start over?",
                 bg=self.colors['card'],
                 fg=self.colors['text']).pack(pady=4)
        bf = tk.Frame(dlg, bg=self.colors['card'])
        bf.pack(pady=14)
        def yes():
            self.reset_detection_data()
            self.image_status.config(
                text="No image selected", fg=self.colors['subtext'])
            self.run_detection_btn.config(state=tk.DISABLED)
            self.update_status("Select an image to begin")
            self.detection_info.config(text="")
            self.image_display.config(
                image="",
                text="Image will appear here\nafter detection")
            self.results_text.delete(1.0, tk.END)
            self.current_image_path = None
            dlg.destroy()
        self.create_button(bf, "Yes", yes, "danger").pack(
            side=tk.LEFT, padx=8)
        self.create_button(bf, "No", dlg.destroy, "primary").pack(
            side=tk.LEFT, padx=8)

    def save_detection_image(self):
        with self._image_lock:
            img_snap = self.processed_image
        if not img_snap:
            self.show_message("warning", "Warning",
                              "No detection image to save.")
            return
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        suf = "_clahe" if self.use_clahe.get() else ""
        fp = filedialog.asksaveasfilename(
            initialfile=f"MoldEZ_detection{suf}_{ts}.png",
            defaultextension=".png",
            filetypes=[("PNG", "*.png"), ("JPEG", "*.jpg")])
        if fp:
            try:
                self._save_pil_image(img_snap, fp)
                self.show_message("info", "Saved",
                                  "Detection image saved.")
            except Exception as e:
                self.show_message("error", "Error", str(e))

    def save_results(self):
        if not self.results_text.get(1.0, tk.END).strip():
            self.show_message("warning", "Warning",
                              "No results to save.")
            return
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        suf = "_clahe" if self.use_clahe.get() else ""
        fp = filedialog.asksaveasfilename(
            initialfile=f"MoldEZ_results{suf}_{ts}.txt",
            defaultextension=".txt",
            filetypes=[("Text", "*.txt")])
        if fp:
            try:
                with open(fp, 'w') as f:
                    f.write(self.results_text.get(1.0, tk.END))
                    if self.analysis_history:
                        f.write(f"\n\n{'='*65}\nHISTORY\n{'='*65}\n")
                        for i, a in enumerate(self.analysis_history, 1):
                            f.write(
                                f"\n#{i} {a['filename']}\n"
                                f" {a['timestamp'].strftime('%Y-%m-%d %H:%M:%S')}\n"
                                f" Coverage: {a['coverage']:.3f}%\n"
                                f" Culture: {a['Culture_area']:.3f} mm²\n"
                                f" Plate: {a['plate_area']:.2f} mm²\n")
                self.show_message("info", "Saved", "Results saved.")
            except Exception as e:
                self.show_message("error", "Error", str(e))

    # Sessions are saved and loaded.
    def save_session(self):
        if not self.analysis_history:
            self.show_message("warning", "Warning",
                              "No analyses to save.")
            return
        sn = self.session_name_var.get()
        m = re.search(r'\((\d+)\)', sn)
        sess_num = m.group(1) if m else "1"
        now = datetime.now()
        date_str = now.strftime("%Y%m%d")
        time_str = now.strftime("%H%M%S")
        default_name = f"Session({sess_num})({date_str})({time_str}).ez"
        fp = filedialog.asksaveasfilename(
            initialfile=default_name,
            defaultextension=".ez",
            filetypes=[("MoldEZ Session", "*.ez")])
        if fp:
            try:
                with open(fp, 'wb') as f:
                    pickle.dump({'name': sn,
                                 'timestamp': datetime.now(),
                                 'analyses': self.analysis_history}, f)
                self.show_message("info", "Saved",
                                  "Session saved successfully.")
            except Exception as e:
                self.show_message("error", "Error", str(e))

    def load_session(self):
        fp = filedialog.askopenfilename(
            filetypes=[("MoldEZ Session", "*.ez"), ("Legacy MoldEZ Session", "*.MoldEZ")])
        if fp:
            try:
                with open(fp, 'rb') as f:
                    sd = pickle.load(f)
                self.analysis_history = sd['analyses']
                for a in self.analysis_history:
                    a.setdefault('source_image_path', None)
                self.session_name_var.set(sd['name'])
                if MATPLOTLIB_AVAILABLE:
                    self.refresh_visualization()
                self.update_analyses_tree()
                self.show_message(
                    "info", "Loaded",
                    f"Session '{sd['name']}' — "
                    f"{len(self.analysis_history)} analyses.")
            except Exception as e:
                self.show_message("error", "Error", str(e))

    def update_analyses_tree(self):
        for row in self.analyses_tree.get_children():
            self.analyses_tree.delete(row)
        for i, a in enumerate(self.analysis_history, 1):
            self.analyses_tree.insert(
                "", "end",
                values=('[ ]', i,
                        a['timestamp'].strftime('%Y-%m-%d %H:%M:%S'),
                        a['filename'],
                        f"{a['diameter']:.1f}",
                        f"{a['Culture_area']:.2f}",
                        f"{a['coverage']:.2f}",
                        a['preprocessing']),
                tags=('row_even' if i % 2 == 0 else 'row_odd',))

    # PDF export is processed.
    def export_pdf(self):
        if not REPORTLAB_AVAILABLE:
            self.show_message("error", "Error",
                              "ReportLab missing — pip install reportlab")
            return
        if not self.analysis_history:
            self.show_message("warning", "Warning",
                              "No analyses to export.")
            return
        sn = self.session_name_var.get()
        m = re.search(r'\((\d+)\)', sn)
        sess_num = m.group(1) if m else "1"
        now = datetime.now()
        date_str = now.strftime("%Y%m%d")
        time_str = now.strftime("%H%M%S")
        default_name = f"Session({sess_num})({date_str})({time_str}).pdf"
        fp = filedialog.asksaveasfilename(
            title="Export PDF Report",
            initialfile=default_name,
            defaultextension=".pdf",
            filetypes=[("PDF", "*.pdf")])
        if fp:
            try:
                self.generate_pdf_report(fp)
                self.show_message("info", "Exported",
                                  f"Report saved:\n{os.path.basename(fp)}")
            except Exception as e:
                self.show_message("error", "Error",
                                  f"PDF failed:\n{e}")

    def generate_pdf_report(self, fp):
        from reportlab.lib import colors as rl_colors
        primary = rl_colors.HexColor('#1f3147')
        ink = rl_colors.HexColor('#1f2937')
        muted = rl_colors.HexColor('#667085')
        line = rl_colors.HexColor('#d7dfeb')
        title_font = 'Helvetica-Bold'
        def border(cv, doc):
            cv.saveState()
            cv.setStrokeColor(line)
            cv.setLineWidth(0.8)
            cv.rect(20, 20, doc.pagesize[0]-40, doc.pagesize[1]-40)
            cv.setFont("Helvetica", 8)
            cv.setFillColor(muted)
            cv.drawRightString(doc.pagesize[0]-28, 28, f"Page {doc.page}")
            cv.restoreState()
        doc = SimpleDocTemplate(fp, pagesize=A4,
                                leftMargin=0.75*inch,
                                rightMargin=0.75*inch,
                                topMargin=0.85*inch,
                                bottomMargin=0.75*inch)
        styles = getSampleStyleSheet()
        story = []
        title_s = ParagraphStyle(
            'T', parent=styles['Title'],
            fontName='Courier-Bold', fontSize=22,
            leading=24, spaceAfter=2, alignment=TA_CENTER,
            textColor=primary)
        sub_s = ParagraphStyle(
            'Sub', parent=styles['Normal'],
            fontName=title_font, fontSize=9.5,
            alignment=TA_CENTER, spaceAfter=10,
            textColor=muted)
        h2_s = ParagraphStyle(
            'H2', parent=styles['Heading2'],
            fontName=title_font, fontSize=12,
            spaceBefore=10, spaceAfter=6,
            textColor=primary)
        norm_s = ParagraphStyle(
            'N', parent=styles['Normal'],
            fontName='Helvetica', fontSize=9,
            leading=11.5, spaceAfter=3, textColor=ink)
        caption_s = ParagraphStyle(
            'Cap', parent=styles['Normal'],
            fontName='Helvetica-Oblique', fontSize=8,
            alignment=TA_CENTER,
            textColor=muted)
        lead_s = ParagraphStyle(
            'Lead', parent=styles['Normal'],
            fontName=title_font, fontSize=9,
            leading=12, spaceAfter=8, alignment=TA_CENTER,
            textColor=ink)
        banner_path = resource_path("banner.png")
        if os.path.exists(banner_path):
            try:
                pb = Image.open(banner_path)
                bw, bh = pb.size
                target_w = 4.1 * inch
                target_h = target_w * bh / bw
                story.append(RLImage(banner_path, width=target_w,
                                      height=target_h, hAlign='CENTER'))
                story.append(Spacer(1, 5))
            except Exception:
                pass
        story.append(Paragraph("ANALYSIS REPORT", title_s))
        story.append(Paragraph(
            "A formatted summary of session results, growth trends, and saved detection outputs.",
            lead_s))
        story.append(HRFlowable(
            width="100%", thickness=1.2,
            color=line, spaceAfter=8))
        sn = self.session_name_var.get()
        now = datetime.now()
        m = re.search(r'\((\d+)\)', sn)
        sess_num = m.group(1) if m else "1"
        report_table_width = 7.2 * inch
        meta_table_data = [
            ["Session Name:", sn, "Session Number:", f"#{sess_num}"],
            ["Software:", "MoldEZ 4.0", "Total Analyses:",
             str(len(self.analysis_history))],
            ["Report Generation Date:", now.strftime('%d/%m/%Y'),
             "Report Generation Time:", now.strftime('%H:%M:%S')],
        ]
        mt = Table(meta_table_data,
                   colWidths=[report_table_width / 4.0] * 4)
        mt.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTNAME', (0, 0), (0, -1), title_font),
            ('FONTNAME', (2, 0), (2, -1), title_font),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('TEXTCOLOR', (0, 0), (-1, -1), ink),
            ('BOX', (0, 0), (-1, -1), 0.7, line),
            ('INNERGRID', (0, 0), (-1, -1), 0.35, line),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
            ('LEFTPADDING', (0, 0), (-1, -1), 7),
            ('RIGHTPADDING', (0, 0), (-1, -1), 7),
        ]))
        story.append(mt)
        story.append(Spacer(1, 10))
        story.append(Paragraph("Summary:", h2_s))
        if self.analysis_history:
            areas = [a['Culture_area'] for a in self.analysis_history]
            covs = [a['coverage'] for a in self.analysis_history]
            story.append(Paragraph(
                f"This session spans {len(self.analysis_history)} analyses with culture area ranging from "
                f"{min(areas):.2f} to {max(areas):.2f} mm² and coverage ranging from "
                f"{min(covs):.2f}% to {max(covs):.2f}%.",
                norm_s))
            sum_data = [
                ["Metric", "Minimum", "Maximum", "Mean"],
                ["Culture Area (mm²)",
                 f"{min(areas):.2f}", f"{max(areas):.2f}",
                 f"{sum(areas)/len(areas):.2f}"],
                ["Coverage (%)",
                 f"{min(covs):.2f}", f"{max(covs):.2f}",
                 f"{sum(covs)/len(covs):.2f}"],
            ]
            st = Table(sum_data, colWidths=[report_table_width / 4.0] * 4)
            st.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), rl_colors.white),
                ('TEXTCOLOR', (0, 0), (-1, 0), ink),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                ('TEXTCOLOR', (0, 1), (-1, -1), ink),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('GRID', (0, 0), (-1, -1), 0.45, line),
                ('BOX', (0, 0), (-1, -1), 0.8, line),
                ('TOPPADDING', (0, 0), (-1, -1), 5),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
            ]))
            story.append(st)
            story.append(Spacer(1, 10))
        story.append(Paragraph("Processing Results:", h2_s))
        hdr = ['#', 'Sample', 'Date & Time', 'Ø (mm)',
                'Area (mm²)', 'Coverage (%)', 'Processing']
        rows = [hdr]
        for i, a in enumerate(self.analysis_history, 1):
            fn = a['filename']
            if len(fn) > 20:
                fn = fn[:18] + '...'
            rows.append([
                str(i), fn,
                a['timestamp'].strftime('%Y-%m-%d %H:%M'),
                f"{a['diameter']:.1f}",
                f"{a['Culture_area']:.2f}",
                f"{a['coverage']:.2f}",
                a['preprocessing']
            ])
        dt = Table(rows, colWidths=[report_table_width / len(hdr)] * len(hdr))
        dt.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), rl_colors.white),
            ('TEXTCOLOR', (0, 0), (-1, 0), ink),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 8),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('TEXTCOLOR', (0, 1), (-1, -1), ink),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('GRID', (0, 0), (-1, -1), 0.4, line),
            ('BOX', (0, 0), (-1, -1), 0.8, line),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('LEFTPADDING', (0, 0), (-1, -1), 4),
            ('RIGHTPADDING', (0, 0), (-1, -1), 4),
            ('WORDWRAP', (0, 0), (-1, -1), 'CJK'),
        ]))
        story.append(dt)
        story.append(Spacer(1, 12))
        if MATPLOTLIB_AVAILABLE and self.analysis_history:
            story.append(Paragraph("Culture Area Trend:", h2_s))
            fig, ax = plt.subplots(figsize=(6.5, 2.8))
            fig.patch.set_facecolor('#ffffff')
            ax.set_facecolor('#ffffff')
            ar = [a['Culture_area'] for a in self.analysis_history]
            xs = list(range(1, len(ar)+1))
            ax.plot(xs, ar, 'o-', color='#e74c3c', linewidth=2,
                    markersize=6, markerfacecolor='white',
                    markeredgewidth=2)
            ax.set_xlabel('Analysis Number', fontsize=9, color='#555')
            ax.set_ylabel('Culture Area (mm²)', fontsize=9, color='#555')
            ax.set_title('Culture Area Trend Across Analyses',
                         fontsize=10, fontweight='bold',
                         color='#2c3e50', pad=10)
            ax.tick_params(colors='#777', labelsize=8)
            ax.grid(True, alpha=0.25, linestyle='--')
            for sp in ax.spines.values():
                sp.set_color('#ddd')
            fig.tight_layout()
            buf = BytesIO()
            fig.savefig(buf, format='png', dpi=150, bbox_inches='tight')
            buf.seek(0)
            plt.close(fig)
            story.append(RLImage(buf, width=6*inch, height=2.5*inch,
                                  hAlign='CENTER'))
            story.append(Spacer(1, 12))
        story.append(Paragraph("Detection Images:", h2_s))
        story.append(Paragraph(
            "Each page below shows one analysis with its detection overlay.",
            norm_s))
        pw = A4[0] - 1.5*inch
        ph = A4[1] - 2.2*inch
        for i, a in enumerate(self.analysis_history, 1):
            story.append(PageBreak())
            hdr_data = [[
                f"Analysis #{i} · {a['filename']}",
                a['timestamp'].strftime('%Y-%m-%d %H:%M:%S')
            ]]
            ht = Table(hdr_data, colWidths=[report_table_width / 2.0] * 2)
            ht.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, -1), rl_colors.white),
                ('TEXTCOLOR', (0, 0), (-1, -1), ink),
                ('FONTNAME', (0, 0), (0, 0), 'Helvetica-Bold'),
                ('FONTNAME', (1, 0), (1, 0), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('ALIGN', (0, 0), (0, 0), 'LEFT'),
                ('ALIGN', (1, 0), (1, 0), 'RIGHT'),
                ('TOPPADDING', (0, 0), (-1, -1), 5),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
                ('LEFTPADDING', (0, 0), (-1, -1), 6),
                ('RIGHTPADDING', (0, 0), (-1, -1), 6),
                ('LINEBELOW', (0, 0), (-1, 0), 0.6, line),
            ]))
            story.append(ht)
            story.append(Spacer(1, 6))
            img_path = a.get('detection_image_path')
            if img_path and os.path.exists(img_path):
                pi = Image.open(img_path)
                ow, oh = pi.size
                asp = ow / oh
                if asp > pw / ph:
                    iw, ih = pw, pw / asp
                else:
                    iw, ih = ph * asp, ph
                story.append(RLImage(img_path, width=iw, height=ih,
                                      hAlign='CENTER'))
                story.append(Spacer(1, 5))
                story.append(Paragraph(
                    f"Figure {i}: Detection overlay where "
                    "Green Outline = Petri Dish, Red Fill = Culture Colonies",
                    caption_s))
            else:
                story.append(Paragraph(
                    f"No detection image available for Analysis #{i}.",
                    norm_s))
            story.append(Spacer(1, 8))
            px_val = a.get('plate_pixels')
            px_str = (f"{int(px_val):,}"
                      if isinstance(px_val, (int, np.integer)) else "—")
            mrows = [
                ["Plate Diameter", f"{a['diameter']:.1f} mm",
                 "Culture Area", f"{a['Culture_area']:.2f} mm²"],
                ["Plate Area", f"{a['plate_area']:.2f} mm²",
                 "Coverage", f"{a['coverage']:.2f}%"],
                ["Image Processing", a['preprocessing'],
                 "Plate Pixels", px_str],
            ]
            mt2 = Table(mrows,
                        colWidths=[report_table_width / 4.0] * 4)
            mt2.setStyle(TableStyle([
                ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
                ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                ('FONTNAME', (2, 0), (2, -1), 'Helvetica-Bold'),
                ('TEXTCOLOR', (0, 0), (-1, -1), ink),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('GRID', (0, 0), (-1, -1), 0.4, line),
                ('BOX', (0, 0), (-1, -1), 0.8, line),
                ('TOPPADDING', (0, 0), (-1, -1), 5),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
                ('LEFTPADDING', (0, 0), (-1, -1), 6),
            ]))
            story.append(mt2)
            if i == len(self.analysis_history):
                story.append(Spacer(1, 8))
                story.append(HRFlowable(
                    width="100%", thickness=1,
                    color=line, spaceAfter=8, spaceBefore=2))
                story.append(Paragraph(
                    "Developed by Mohammed Ayan Mahmood.",
                    ParagraphStyle('Ft', parent=styles['Normal'],
                                   fontName=title_font, fontSize=9,
                                   alignment=TA_CENTER,
                                   textColor=primary)))
                story.append(Spacer(1, 3))
                story.append(Paragraph(
                    "Under the mentorship of Dr. Kafi R. Rahman and "
                    "Dr. Hajeewaka C. Mendis",
                    ParagraphStyle('Ft2', parent=styles['Normal'],
                                   fontName=title_font, fontSize=8.5,
                                   alignment=TA_CENTER,
                                   textColor=muted)))
                story.append(Paragraph(
                    "Software version 4.0 | Truman State University | "
                    "MoldEZ Professional Culture Analysis Solution",
                    ParagraphStyle('Ft3', parent=styles['Normal'],
                                   fontName=title_font, fontSize=8.5,
                                   alignment=TA_CENTER,
                                   textColor=muted)))
        if not self.analysis_history:
            story.append(Spacer(1, 8))
            story.append(HRFlowable(
                width="100%", thickness=1,
                color=line, spaceAfter=8, spaceBefore=2))
            story.append(Paragraph(
                "Developed by Mohammed Ayan Mahmood.",
                ParagraphStyle('Ft', parent=styles['Normal'],
                               fontName=title_font, fontSize=9,
                               alignment=TA_CENTER,
                               textColor=primary)))
            story.append(Spacer(1, 3))
            story.append(Paragraph(
                "Under the mentorship of Dr. Kafi R. Rahman and "
                "Dr. Hajeewaka C. Mendis",
                ParagraphStyle('Ft2', parent=styles['Normal'],
                               fontName=title_font, fontSize=8.5,
                               alignment=TA_CENTER,
                               textColor=muted)))
            story.append(Paragraph(
                "Software Version 4.0 | Truman State University | "
                "Professional Culture Analysis Solution",
                ParagraphStyle('Ft3', parent=styles['Normal'],
                               fontName=title_font, fontSize=8.5,
                               alignment=TA_CENTER,
                               textColor=muted)))
        doc.build(story, onFirstPage=border, onLaterPages=border)

    # Message dialogs are handled.
    def show_message(self, kind, title, text):
        icon = {'info': '🔵', 'warning': '🟡',
                'error': '🔴', 'success': '🟢'}.get(kind, '⚪')
        col = {'info': '#3498db', 'warning': '#f39c12',
                'error': '#e74c3c', 'success': '#27ae60'}.get(
            kind, '#2c3e50')
        dlg = tk.Toplevel(self.root)
        dlg.title(title)
        dlg.configure(bg=self.colors['card'])
        dlg.resizable(False, False)
        dlg.grab_set()
        tk.Label(dlg, text=f"{icon} {title}",
                 font=("Segoe UI Semibold", 12),
                 bg=self.colors['card'], fg=col).pack(pady=(16, 4), padx=24)
        tk.Label(dlg, text=text, bg=self.colors['card'],
                 fg=self.colors['text'],
                 font=("Segoe UI", 10),
                 justify=tk.LEFT).pack(pady=6, padx=24)
        self.create_button(dlg, "OK", dlg.destroy,
                           "primary").pack(pady=(8, 16))

    # Image viewing is handled.
    def on_analysis_double_click(self, event):
        if self.analyses_tree.identify_column(event.x) == '#1':
            return
        item = self.analyses_tree.identify_row(event.y)
        if item:
            idx = self.analyses_tree.index(item)
            a = self.analysis_history[idx]
            ip = a.get('detection_image_path')
            if ip and os.path.exists(ip):
                self.display_image(ip)
            else:
                self.show_message("info", "No Image",
                                  "No detection image for this analysis.")

    def display_image(self, path):
        img = Image.open(path)
        img.thumbnail((600, 600), Image.Resampling.LANCZOS)
        ph = ImageTk.PhotoImage(img)
        w = tk.Toplevel(self.root)
        w.title("Detection Image")
        w.configure(bg=self.colors['card'])
        w.image = ph
        tk.Label(w, image=ph, bg=self.colors['card']).pack(
            padx=10, pady=10)

    # Clean exit is handled.
    def on_closing(self):
        self.stop_automation()
        if MATPLOTLIB_AVAILABLE:
            try:
                plt.close('all')
            except Exception:
                pass
        try:
            self.root.quit()
        except Exception:
            pass
        try:
            self.root.destroy()
        except Exception:
            pass
        if getattr(sys, 'frozen', False) and sys.platform.startswith("win"):
            os._exit(0)


def main():
    root = tk.Tk()
    if sys.platform.startswith("win"):
        try:
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
                "MoldEZ.MarkIV.2026")
        except Exception:
            pass
    set_window_icon(root)
    app = MoldEZAnalyzer(root)
    if sys.platform == "darwin":
        try:
            root.createcommand(
                "tk::mac::Quit",
                lambda: (app.on_closing(), "break")[1])
        except Exception:
            pass
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()

# Entry point is processed.
if __name__ == "__main__":
    main()

