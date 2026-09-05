import os
import re
import sys
import json
import base64
import socket
import pickle
import urllib.request
import urllib.error
import threading
from io import BytesIO
from datetime import datetime
from pathlib import Path
from contextlib import contextmanager, redirect_stdout

# PySide6 Imports
from PySide6.QtCore import Qt, QThread, Signal, Slot, QTimer, QSize, QRectF, QRect, QPointF, QPoint
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QFrame, QLabel,
                               QPushButton, QLineEdit, QSpinBox, QDoubleSpinBox,
                               QComboBox, QCheckBox, QHBoxLayout, QVBoxLayout,
                               QGridLayout, QTabWidget, QTreeWidget, QTreeWidgetItem,
                               QFileDialog, QMessageBox, QScrollArea, QProgressBar,
                               QSplashScreen, QSplitter, QSlider, QSizePolicy,
                               QTextEdit, QTextBrowser, QStyleFactory)
from PySide6.QtGui import QIcon, QPixmap, QColor, QFont, QPainter, QPen, QBrush, QImage, QPalette

# Optional Imports
try:
    import pillow_heif
    PILLOW_HEIF_AVAILABLE = True
except ImportError:
    PILLOW_HEIF_AVAILABLE = False

from roboflow import Roboflow
from PIL import Image, ImageTk, ImageDraw
import numpy as np

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
    matplotlib.use('QtAgg')
    import matplotlib.pyplot as plt
    from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
    import matplotlib.patches as patches
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False

try:
    from reportlab.lib import colors as rl_colors
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

# Core Roboflow constants
ROBOFLOW_API_KEY = "Ixdl8OkpfEuJSBr6DV55"
DISH_MODEL_ID = "moldez_dish_finder"
DISH_MODEL_VERSION = 4
Culture_MODEL_ID = "moldez_segmentation"
Culture_MODEL_VERSION = 6
ROBOFLOW_CONNECTIVITY_HOSTS = (
    "api.roboflow.com",
    "segment.roboflow.com",
)

# App themes matching Tkinter colors
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
    'background': '#ffffff',
    'card': '#ffffff',
    'border': '#dee2e6',
    'text': '#2c3e50',
    'subtext': '#6c757d',
    'results_bg': '#ffffff',
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
    'results_bg': '#1e2536',
    'input_bg': '#2c3551',
    'input_fg': '#e0e6ed',
}

def resource_path(relative_path):
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    local_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), relative_path)
    if not os.path.exists(local_path):
        subdir_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "MoldEZMac", relative_path)
        if os.path.exists(subdir_path):
            return subdir_path
    return local_path

def get_app_dir():
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

# Custom QSS Stylesheet Generator
def get_theme_qss(colors):
    return f"""
    QMainWindow, QDialog, QScrollArea, QScrollArea > QWidget, QScrollArea > QWidget > QWidget, QWidget#mainContainer {{
        background-color: {colors['background']};
        color: {colors['text']};
    }}
    QScrollArea {{
        border: none;
    }}
    QFrame#card {{
        background-color: {colors['card']};
        border: 1px solid {colors['border']};
        border-radius: 8px;
    }}
    QLabel {{
        color: {colors['text']};
        border: none;
        background: transparent;
        font-family: 'Segoe UI', '.AppleSystemUIFont', sans-serif;
    }}
    QLabel#title {{
        font-size: 13px;
        font-weight: bold;
        color: {colors['primary']};
    }}
    QPushButton {{
        border: none;
        border-radius: 6px;
        padding: 8px 16px;
        font-weight: bold;
        font-family: 'Segoe UI', '.AppleSystemUIFont', sans-serif;
        font-size: 11px;
    }}
    QPushButton[styleClass="primary"] {{
        background-color: {colors['primary']};
        color: {colors['background']};
    }}
    QPushButton[styleClass="secondary"] {{
        background-color: {colors['secondary']};
        color: white;
    }}
    QPushButton[styleClass="tertiary"] {{
        background-color: {colors['tertiary']};
        color: white;
    }}
    QPushButton[styleClass="quaternary"] {{
        background-color: {colors['quaternary']};
        color: white;
    }}
    QPushButton[styleClass="quinary"] {{
        background-color: {colors['quinary']};
        color: white;
    }}
    QPushButton[styleClass="senary"] {{
        background-color: {colors['senary']};
        color: white;
    }}
    QPushButton[styleClass="danger"] {{
        background-color: {colors['danger']};
        color: white;
    }}
    QPushButton[styleClass="success"] {{
        background-color: {colors['success']};
        color: white;
    }}
    QPushButton:hover {{
        opacity: 0.9;
    }}
    QPushButton:disabled {{
        background-color: {colors['border']};
        color: {colors['subtext']};
    }}
    QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox {{
        background-color: {colors['input_bg']};
        color: {colors['input_fg']};
        border: 1px solid {colors['border']};
        border-radius: 4px;
        padding: 4px 8px;
    }}
    QTabWidget::pane {{
        border: 1px solid {colors['border']};
        background-color: {colors['background']};
        top: -1px;
    }}
    QTabBar {{
        background-color: transparent;
        border: none;
    }}
    QTabBar::tab {{
        background-color: {colors['card']};
        border: 1px solid {colors['border']};
        border-bottom-color: {colors['border']};
        border-top-left-radius: 4px;
        border-top-right-radius: 4px;
        padding: 8px 16px;
        color: {colors['subtext']};
        font-weight: bold;
    }}
    QTabBar::tab:selected {{
        background-color: {colors['background']};
        color: {colors['text']};
        border-bottom-color: {colors['background']};
    }}
    QTabBar::tab:hover:!selected {{
        background-color: {colors['card']};
        color: {colors['text']};
    }}
    QTreeWidget, QTableWidget {{
        background-color: {colors['card']};
        color: {colors['text']};
        border: 1px solid {colors['border']};
        gridline-color: {colors['border']};
    }}
    QHeaderView::section {{
        background-color: {colors['light']};
        color: {colors['text']};
        border: 1px solid {colors['border']};
        padding: 4px;
        font-weight: bold;
    }}
    QProgressBar {{
        background-color: {colors['light']};
        border: 1px solid {colors['border']};
        border-radius: 4px;
        text-align: center;
        color: {colors['text']};
    }}
    QProgressBar::chunk {{
        background-color: {colors['secondary']};
        border-radius: 4px;
    }}
    QScrollBar:vertical {{
        border: none;
        background-color: {colors['background']};
        width: 10px;
        margin: 0px;
    }}
    QScrollBar::handle:vertical {{
        background-color: {colors['border']};
        min-height: 20px;
        border-radius: 5px;
    }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
        height: 0px;
    }}
    QTextEdit, QTextBrowser {{
        background-color: {colors['results_bg']};
        color: {colors['text']};
        border: 1px solid {colors['border']};
        font-family: 'Consolas', 'Courier New', monospace;
        font-size: 11px;
    }}
    """

# Custom aspect-ratio label for image previews
class AspectLabel(QLabel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(260, 220)
        self._pixmap = None
        self.setAlignment(Qt.AlignCenter)
        
    def setPixmap(self, pixmap):
        self._pixmap = pixmap
        if self._pixmap and not self._pixmap.isNull():
            super().setPixmap(self._scaledPixmap())
        else:
            super().setPixmap(QPixmap())
        
    def _scaledPixmap(self):
        if self._pixmap and not self._pixmap.isNull():
            return self._pixmap.scaled(self.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
        return QPixmap()
        
    def resizeEvent(self, event):
        if self._pixmap and not self._pixmap.isNull():
            super().setPixmap(self._scaledPixmap())
        super().resizeEvent(event)

# Native PySide6 Drag and Drop target Zone
class DropZoneFrame(QFrame):
    fileDropped = Signal(str)
    clicked = Signal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setCursor(Qt.PointingHandCursor)
        
        self.layout = QVBoxLayout(self)
        self.label = QLabel("Drag and drop an image here\nor click to browse")
        self.label.setAlignment(Qt.AlignCenter)
        self.layout.addWidget(self.label)
        
    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            self.setStyleSheet("QFrame { border: 2px dashed #3498db; background-color: rgba(52, 152, 219, 0.1); }")
            
    def dragLeaveEvent(self, event):
        self.setStyleSheet("")
        
    def dropEvent(self, event):
        self.setStyleSheet("")
        if event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            if urls:
                path = urls[0].toLocalFile()
                self.fileDropped.emit(path)
                event.acceptProposedAction()
                
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit()

# Custom PySide6 Toggle Switch widget
class ToggleSwitch(QWidget):
    toggled = Signal(bool)
    
    def __init__(self, parent=None, active_color="#2ecc71", inactive_color="#bdc3c7"):
        super().__init__(parent)
        self.setFixedSize(46, 24)
        self._checked = False
        self._active_color = QColor(active_color)
        self._inactive_color = QColor(inactive_color)
        self.setCursor(Qt.PointingHandCursor)
        
    def isChecked(self):
        return self._checked
        
    def setChecked(self, checked):
        if self._checked != checked:
            self._checked = checked
            self.toggled.emit(self._checked)
            self.update()
            
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.setChecked(not self._checked)
            
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Track
        pen = QPen(Qt.NoPen)
        painter.setPen(pen)
        color = self._active_color if self._checked else self._inactive_color
        painter.setBrush(QBrush(color))
        painter.drawRoundedRect(0, 0, self.width(), self.height(), 12, 12)
        
        # Thumb
        painter.setBrush(QBrush(QColor("#ffffff")))
        thumb_size = 18
        padding = 3
        x = self.width() - thumb_size - padding if self._checked else padding
        painter.drawEllipse(x, padding, thumb_size, thumb_size)

# Custom Interactive Mask Painter Editor Widget
class MaskEditorWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(320, 240)
        self.setMouseTracking(True)
        self.analyzer = None
        self._pixmap = None
        self._brush_pos = None
        self.setCursor(Qt.BlankCursor) # Blank cursor when inside editor, like Tk "none"
        
    def setPixmap(self, pixmap):
        self._pixmap = pixmap
        self.update()
        
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Draw background
        bg = QColor(self.analyzer.colors['results_bg'] if self.analyzer else "#ffffff")
        painter.fillRect(self.rect(), bg)
        
        if self._pixmap and not self._pixmap.isNull():
            # Scale conserving aspect ratio
            scaled = self._pixmap.scaled(self.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
            x = (self.width() - scaled.width()) // 2
            y = (self.height() - scaled.height()) // 2
            
            if self.analyzer:
                self.analyzer.mask_editor_offset = (x, y)
                self.analyzer.mask_editor_display_size = (scaled.width(), scaled.height())
                
            painter.drawPixmap(x, y, scaled)
            
            # Draw semi-transparent culture overlay on top
            if self.analyzer and self.analyzer.mask_overlay_qimage:
                target_rect = QRect(x, y, scaled.width(), scaled.height())
                painter.drawImage(target_rect, self.analyzer.mask_overlay_qimage)
            
            # Draw overlay brush pointer
            if self._brush_pos and self.analyzer and self.analyzer.Culture_mask is not None:
                bx, by = self._brush_pos
                r = self.analyzer._brush_canvas_radius()
                tool = self.analyzer.mask_editor_tool
                outline = QColor('#ff4d5a') if tool == "erase" else QColor('#2ecc71')
                
                painter.setPen(QPen(outline, 2))
                painter.setBrush(Qt.NoBrush)
                painter.drawEllipse(QPointF(bx, by), r, r)
                
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton and self.analyzer:
            self.analyzer._start_mask_stroke(event.position())
            
    def mouseMoveEvent(self, event):
        self._brush_pos = (event.position().x(), event.position().y())
        if self.analyzer:
            if event.buttons() & Qt.LeftButton:
                self.analyzer._paint_mask_stroke(event.position())
            else:
                self.analyzer._show_mask_brush(event.position())
        self.update()
        
    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton and self.analyzer:
            self.analyzer._end_mask_stroke(event.position())
        self.update()
        
    def leaveEvent(self, event):
        self._brush_pos = None
        if self.analyzer:
            self.analyzer._hide_mask_brush(None)
        self.update()

# Worker threads for background processing
class ModelInitWorker(QThread):
    finished = Signal(object, object, str) # dish, culture, status message
    
    def __init__(self, is_internet_cb):
        super().__init__()
        self.is_internet_cb = is_internet_cb
        
    def run(self):
        if not self.is_internet_cb():
            self.finished.emit(None, None, "No internet - models cannot be loaded.")
            return
        try:
            with suppress_stdout():
                rf = Roboflow(api_key=ROBOFLOW_API_KEY)
                dish_model = rf.workspace().project(DISH_MODEL_ID).version(DISH_MODEL_VERSION).model
                culture_model = rf.workspace().project(Culture_MODEL_ID).version(Culture_MODEL_VERSION).model
            self.finished.emit(dish_model, culture_model, "Models are ready")
        except Exception as e:
            self.finished.emit(None, None, f"Initialization Error: {e}")

class DetectionWorker(QThread):
    status = Signal(str)
    finished = Signal(dict)
    error = Signal(str)
    
    def __init__(self, analyzer, image_path, dish_conf, culture_conf, use_clahe, clip_limit, tile_size):
        super().__init__()
        self.analyzer = analyzer
        self.image_path = image_path
        self.dish_conf = dish_conf
        self.culture_conf = culture_conf
        self.use_clahe = use_clahe
        self.clip_limit = clip_limit
        self.tile_size = tile_size
        
    def run(self):
        try:
            if not self.analyzer.is_internet_available():
                self.error.emit("No internet connection.")
                return
                
            self.status.emit("Detecting petri dish...")
            pp = self.analyzer.apply_clahe_preprocessing(self.image_path)
            
            dc = self.analyzer._roboflow_confidence(self.dish_conf)
            cc = self.analyzer._roboflow_confidence(self.culture_conf)
            
            dr = self.analyzer._predict_with_confidence(self.analyzer.dish_model, pp, dc)
            
            self.status.emit("Detecting culture colonies...")
            cr = self.analyzer._predict_with_confidence(self.analyzer.Culture_model, pp, cc)
            
            self.status.emit("Processing...")
            pp_px, cp_px = self.analyzer.process_predictions_simple(dr, cr)
            
            self.finished.emit({
                'plate_pixels': pp_px,
                'culture_pixels': cp_px,
                'pp': pp
            })
        except Exception as e:
            self.error.emit(str(e))

# Native transparent borderless splash screen
class SplashScreen(QWidget):
    def __init__(self, image_name="SplashScreen.png"):
        super().__init__()
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.SubWindow)
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        path = resource_path(image_name)
        if os.path.exists(path):
            self.pixmap = QPixmap(path)
        else:
            self.pixmap = QPixmap()
            
        self.setFixedSize(self.pixmap.size() if not self.pixmap.isNull() else QSize(400, 300))
        screen = QApplication.primaryScreen().geometry()
        x = (screen.width() - self.width()) // 2
        y = (screen.height() - self.height()) // 2
        self.move(x, y)
        
    def paintEvent(self, event):
        painter = QPainter(self)
        if not self.pixmap.isNull():
            painter.drawPixmap(0, 0, self.pixmap)

# Main UI Class using QMainWindow
class MoldEZAnalyzer(QMainWindow):
    def __init__(self):
        super().__init__()
        if PILLOW_HEIF_AVAILABLE:
            pillow_heif.register_heif_opener()
            
        self.setWindowTitle("MoldEZ (Mark IV)")
        self.resize(1600, 920)
        
        # Application Variables
        self.dark_mode = False
        self.colors = dict(LIGHT_COLORS)
        
        self.dish_model = None
        self.Culture_model = None
        self.colony_model = None
        self.model_startup_done = threading.Event()
        
        self.current_image_path = None
        self.processed_image = None
        self.image_display_source = None
        self._image_lock = threading.Lock()
        self.preprocessed_image_path = None
        self.detected_plate_pixels = 0
        self.detected_Culture_pixels = 0
        self.plate_mask = None
        self.Culture_mask = None
        
        self.use_clahe = False
        self.clahe_clip_limit = 2.0
        self.clahe_tile_size = 8
        self.show_advanced = False
        self.dish_confidence = 30
        self.Culture_confidence = 40
        
        self.mask_editor_tool = "draw"
        self.mask_brush_size = 24
        self.mask_undo_stack = []
        self.mask_redo_stack = []
        self.mask_editor_base_image = None
        self.mask_overlay_buffer = None
        self.mask_overlay_qimage = None
        self.mask_editor_base_pixmap = None
        self.mask_editor_display_size = (0, 0)
        self.mask_editor_offset = (0, 0)
        self.mask_editor_stroke_active = False
        self.mask_editor_last_pos = None
        
        self.analysis_history = []
        self.sessions = []
        self.current_session_name = "Session(1)"
        self.session_files = {}
        
        self.results_dir = os.path.join(get_app_dir(), "results")
        if not os.path.exists(self.results_dir):
            os.makedirs(self.results_dir)
            
        self.compare_time_source = "timestamps"
        self.manual_time_hours = 0
        self.manual_time_minutes = 0
        
        self.timer_id = None
        self.remaining_seconds = 0
        self.automation_running = False
        self.auto_hours = 0
        self.auto_minutes = 10
        self.batch_cancelled = False
        self.colony_count_results = []
        self.colony_preview_image = None
        
        self.setup_gui()
        
        # Load models in QThread
        self.init_worker = ModelInitWorker(self.is_internet_available)
        self.init_worker.finished.connect(self._on_models_initialized)
        self.init_worker.start()
        
    def _on_models_initialized(self, dish_m, cult_m, status_msg):
        self.dish_model = dish_m
        self.Culture_model = cult_m
        self.detection_status.setText(status_msg)
        self.model_startup_done.set()
        
    def is_internet_available(self, timeout=3):
        for host in ROBOFLOW_CONNECTIVITY_HOSTS:
            try:
                req = urllib.request.Request(
                    f"https://{host}/",
                    method="HEAD",
                    headers={"User-Agent": "MoldEZ/Mark-IV"})
                with urllib.request.urlopen(req, timeout=timeout):
                    return True
            except Exception:
                pass
            try:
                with socket.create_connection((host, 443), timeout=timeout):
                    return True
            except OSError:
                pass
        return False

    def setup_gui(self):
        # Set window icon
        icon_path = resource_path("icon.png")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
            
        # Top-level Central Widget & Layout
        central = QWidget()
        central.setObjectName("mainContainer")
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(18, 10, 18, 6)
        
        # 1. Top Bar Header
        self.topbar = QFrame()
        self.topbar.setFixedHeight(42)
        topbar_layout = QHBoxLayout(self.topbar)
        topbar_layout.setContentsMargins(16, 4, 16, 4)
        
        topbar_layout.addStretch()
        
        self.dm_label = QLabel("Dark Mode")
        self.dm_label.setFont(QFont("Segoe UI", 10, QFont.Bold))
        topbar_layout.addWidget(self.dm_label)
        
        self.dm_toggle_btn = ToggleSwitch(active_color="#2ecc71")
        self.dm_toggle_btn.toggled.connect(self.toggle_dark_mode)
        topbar_layout.addWidget(self.dm_toggle_btn)
        
        main_layout.addWidget(self.topbar)
        
        # 2. Main Banner Logo
        self.banner_frame = QFrame()
        banner_layout = QHBoxLayout(self.banner_frame)
        self.banner_label = QLabel()
        self.banner_label.setAlignment(Qt.AlignCenter)
        self.update_banner()
        banner_layout.addWidget(self.banner_label)
        main_layout.addWidget(self.banner_frame)
        
        # 3. Tab Navigation Notebook
        self.tabs = QTabWidget()
        self.tabs.setStyle(QStyleFactory.create("Fusion"))
        main_layout.addWidget(self.tabs)
        
        # Create Tabs
        self.main_tab = QWidget()
        self.sessions_tab = QWidget()
        self.automation_tab = QWidget()
        
        self.tabs.addTab(self.main_tab, "Main")
        self.tabs.addTab(self.sessions_tab, "Sessions")
        self.tabs.addTab(self.automation_tab, "Automation")
        
        # Setup individual tab content
        self.setup_main_tab()
        self.setup_sessions_tab()
        self.setup_automation_tab()
        
        # 4. Footer Bar
        self.footer = QLabel("Powered by Truman State University - Developed by Mohammed Ayan Mahmood - 2026")
        self.footer.setFont(QFont("Segoe UI", 8, QFont.Light))
        self.footer.setAlignment(Qt.AlignCenter)
        self.footer.setObjectName("subtext")
        main_layout.addWidget(self.footer)
        
        # Apply initial stylesheet
        self.setStyleSheet(get_theme_qss(self.colors))
        self._update_header_theme()
        
    def _header_bg(self):
        return '#1a1f2e' if self.dark_mode else '#ffffff'

    def _update_header_theme(self):
        bg = self._header_bg()
        fg = 'white' if self.dark_mode else '#2c3e50'
        self.topbar.setStyleSheet(f"QFrame {{ background-color: {bg}; border: none; }}")
        self.dm_label.setStyleSheet(f"color: {fg};")
        self.dm_toggle_btn.setStyleSheet(f"background-color: {bg};")
        self.banner_frame.setStyleSheet(f"background-color: {bg};")

    def toggle_dark_mode(self, enabled):
        self.dark_mode = enabled
        self.colors = dict(DARK_COLORS if enabled else LIGHT_COLORS)
        self.setStyleSheet(get_theme_qss(self.colors))
        self._update_header_theme()
        self.update_banner()
        self.refresh_visualization()
        
    def update_banner(self):
        banner_name = "banner-dark.png" if self.dark_mode else "banner.png"
        bg_col = self._header_bg()
        
        try:
            banner_path = resource_path(banner_name)
            if os.path.exists(banner_path):
                with Image.open(banner_path) as pil_image:
                    if pil_image.mode != 'RGBA':
                        pil_image = pil_image.convert('RGBA')
                    
                    data = pil_image.getdata()
                    new_data = []
                    if len(data) > 0:
                        bg_r, bg_g, bg_b, bg_a = data[0]
                        target_bg = bg_col.lstrip('#')
                        t_r = int(target_bg[0:2], 16)
                        t_g = int(target_bg[2:4], 16)
                        t_b = int(target_bg[4:6], 16)
                        for item in data:
                            r, g, b, a = item
                            if a > 0 and abs(r - bg_r) < 15 and abs(g - bg_g) < 15 and abs(b - bg_b) < 15:
                                new_data.append((t_r, t_g, t_b, a))
                            else:
                                new_data.append(item)
                        pil_image.putdata(new_data)

                    pil_image.thumbnail((440, 96), Image.Resampling.LANCZOS)
                    bio = BytesIO()
                    pil_image.save(bio, format='PNG')
                    pix = QPixmap()
                    pix.loadFromData(bio.getvalue())
                    self.banner_label.setPixmap(pix)
                    self.banner_label.show()
            else:
                self.banner_label.hide()
        except Exception as e:
            print("Banner error:", e)

    # WIDGET CREATION HELPERS
    def create_card(self, title_text):
        card = QFrame()
        card.setObjectName("card")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(12, 12, 12, 12)
        
        title = QLabel(title_text)
        title.setObjectName("title")
        title.setFont(QFont("Segoe UI", 10, QFont.Bold))
        layout.addWidget(title)
        
        return card, layout
        
    def create_button(self, text, handler, style_class="primary"):
        btn = QPushButton(text)
        btn.setProperty("styleClass", style_class)
        btn.setCursor(Qt.PointingHandCursor)
        btn.clicked.connect(handler)
        return btn

    def setup_main_tab(self):
        layout = QHBoxLayout(self.main_tab)
        layout.setContentsMargins(0, 10, 0, 0)
        
        # Left Panel QScrollArea
        left_scroll = QScrollArea()
        left_scroll.setWidgetResizable(True)
        left_scroll.setFixedWidth(520)
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(10, 10, 10, 10)
        
        # Left Panel - Card 1: Select Image
        c1, c1_lay = self.create_card("Step 1 - Select Image")
        bf = QHBoxLayout()
        self.select_image_btn = self.create_button("SELECT IMAGE", self.select_image, "tertiary")
        self.capture_image_btn = self.create_button("CAPTURE", self.capture_image, "senary")
        self.select_folder_btn = self.create_button("BATCH FOLDER", self.select_folder, "quinary")
        bf.addWidget(self.select_image_btn)
        bf.addWidget(self.capture_image_btn)
        bf.addWidget(self.select_folder_btn)
        c1_lay.addLayout(bf)
        
        self.drop_zone = DropZoneFrame()
        self.drop_zone.fileDropped.connect(self.load_selected_image)
        self.drop_zone.clicked.connect(self.select_image)
        c1_lay.addWidget(self.drop_zone)
        
        self.image_status = QLabel("No image selected")
        self.image_status.setObjectName("subtext")
        c1_lay.addWidget(self.image_status)
        left_layout.addWidget(c1)
        
        # Left Panel - Card 1.5: Preprocessing (Optional)
        c15, c15_lay = self.create_card("Step 1.5 - Preprocessing (Optional)")
        self.clahe_check = QCheckBox("Enable CLAHE Enhancement (for poor lighting)")
        self.clahe_check.setChecked(self.use_clahe)
        self.clahe_check.toggled.connect(self.on_clahe_toggled)
        c15_lay.addWidget(self.clahe_check)
        
        pf = QHBoxLayout()
        pf.addWidget(QLabel("Clip:"))
        self.clahe_clip_spin = QDoubleSpinBox()
        self.clahe_clip_spin.setRange(1.0, 4.0)
        self.clahe_clip_spin.setSingleStep(0.1)
        self.clahe_clip_spin.setValue(self.clahe_clip_limit)
        self.clahe_clip_spin.setFixedWidth(80)
        pf.addWidget(self.clahe_clip_spin)
        
        pf.addWidget(QLabel("Tile:"))
        self.clahe_tile_spin = QSpinBox()
        self.clahe_tile_spin.setRange(2, 16)
        self.clahe_tile_spin.setSingleStep(2)
        self.clahe_tile_spin.setValue(self.clahe_tile_size)
        self.clahe_tile_spin.setFixedWidth(80)
        pf.addWidget(self.clahe_tile_spin)
        pf.addStretch(1)
        c15_lay.addLayout(pf)
        left_layout.addWidget(c15)
        
        # Initialize enabled state
        self.on_clahe_toggled(self.use_clahe)
        
        # Left Panel - Card 2: Step 2 - Run Detection
        c2, c2_lay = self.create_card("Step 2 - Run Detection")
        det_row = QHBoxLayout()
        self.run_detection_btn = self.create_button("RUN DETECTION", self.run_detection, "secondary")
        self.run_detection_btn.setEnabled(False)
        det_row.addWidget(self.run_detection_btn)
        
        self.detection_status = QLabel("Select an image first")
        self.detection_status.setObjectName("subtext")
        det_row.addWidget(self.detection_status)
        c2_lay.addLayout(det_row)
        
        self.detection_progress = QProgressBar()
        self.detection_progress.setRange(0, 0) # Indeterminate
        self.detection_progress.hide()
        c2_lay.addWidget(self.detection_progress)
        
        self.detection_info = QLabel("")
        self.detection_info.setObjectName("subtext")
        c2_lay.addWidget(self.detection_info)
        left_layout.addWidget(c2)
        
        # Left Panel - Card 3: Advanced Detection Settings (Expandable)
        adv_card, adv_card_lay = self.create_card("")
        self.advanced_toggle_btn = self.create_button("Advanced Detection Settings", self.toggle_advanced_settings, "primary")
        adv_card_lay.addWidget(self.advanced_toggle_btn)
        
        self.advanced_content = QFrame()
        adv_content_lay = QVBoxLayout(self.advanced_content)
        adv_content_lay.setContentsMargins(0, 10, 0, 0)
        
        # Interactive Mask Editor Sub-Header
        editor_title = QLabel("Interactive Mask Editor")
        editor_title.setFont(QFont("Segoe UI", 10, QFont.Bold))
        adv_content_lay.addWidget(editor_title)
        
        btn_row = QHBoxLayout()
        self.draw_btn = self.create_button("DRAW MOLD", lambda: self.set_mask_editor_tool("draw"), "success")
        self.erase_btn = self.create_button("ERASE MOLD", lambda: self.set_mask_editor_tool("erase"), "danger")
        self.undo_btn = self.create_button("UNDO", self.undo_mask_edit, "secondary")
        self.redo_btn = self.create_button("REDO", self.redo_mask_edit, "secondary")
        self.reset_btn = self.create_button("RESET", self.run_detection, "secondary")
        self.undo_btn.setEnabled(False)
        self.redo_btn.setEnabled(False)
        btn_row.addWidget(self.draw_btn)
        btn_row.addWidget(self.erase_btn)
        btn_row.addWidget(self.undo_btn)
        btn_row.addWidget(self.redo_btn)
        btn_row.addWidget(self.reset_btn)
        adv_content_lay.addLayout(btn_row)
        
        brush_row = QHBoxLayout()
        brush_row.addWidget(QLabel("Brush Size:"))
        self.brush_slider = QSlider(Qt.Horizontal)
        self.brush_slider.setRange(4, 250)
        self.brush_slider.setValue(self.mask_brush_size)
        self.brush_slider.valueChanged.connect(self.on_brush_size_changed)
        brush_row.addWidget(self.brush_slider)
        adv_content_lay.addLayout(brush_row)
        
        # Custom mask editing widget
        self.mask_editor = MaskEditorWidget()
        self.mask_editor.analyzer = self
        adv_content_lay.addWidget(self.mask_editor)
        
        self.mask_editor_status = QLabel("Run detection to enable mask editing")
        self.mask_editor_status.setObjectName("subtext")
        adv_content_lay.addWidget(self.mask_editor_status)
        
        # Confidence Settings Grid
        param_grid = QGridLayout()
        param_grid.addWidget(QLabel("Dish Confidence (%):"), 0, 0)
        self.dish_conf_spin = QSpinBox()
        self.dish_conf_spin.setRange(10, 100)
        self.dish_conf_spin.setValue(self.dish_confidence)
        param_grid.addWidget(self.dish_conf_spin, 0, 1)
        
        param_grid.addWidget(QLabel("Culture Confidence (%):"), 1, 0)
        self.culture_conf_spin = QSpinBox()
        self.culture_conf_spin.setRange(10, 100)
        self.culture_conf_spin.setValue(self.Culture_confidence)
        param_grid.addWidget(self.culture_conf_spin, 1, 1)
        adv_content_lay.addLayout(param_grid)
        
        adv_card_lay.addWidget(self.advanced_content)
        self.advanced_content.hide()
        
        left_layout.addWidget(adv_card)
        
        # Left Panel - Card 4: Step 3 - Plate Diameter
        c3, c3_lay = self.create_card("Step 3 - Plate Diameter")
        diam_row = QHBoxLayout()
        diam_row.addWidget(QLabel("Diameter (mm):"))
        self.diameter_input = QLineEdit("100")
        diam_row.addWidget(self.diameter_input)
        self.calculate_btn = self.create_button("CALCULATE AREA", self.calculate_area, "quaternary")
        self.calculate_btn.setEnabled(False)
        diam_row.addWidget(self.calculate_btn)
        c3_lay.addLayout(diam_row)
        left_layout.addWidget(c3)
        
        # Left Panel - Card 5: Results
        c4, c4_lay = self.create_card("Results")
        self.results_text = QTextEdit()
        self.results_text.setReadOnly(True)
        c4_lay.addWidget(self.results_text)
        left_layout.addWidget(c4)
        
        left_scroll.setWidget(left_widget)
        layout.addWidget(left_scroll)
        
        # Middle Panel (Dynamic image rendering preview)
        middle_panel = QFrame()
        middle_layout = QVBoxLayout(middle_panel)
        middle_layout.setContentsMargins(10, 10, 10, 10)
        
        # Section Title
        title_det = QLabel("DETECTION RESULTS")
        title_det.setFont(QFont("Segoe UI", 16, QFont.Bold))
        title_det.setAlignment(Qt.AlignCenter)
        middle_layout.addWidget(title_det)
        
        # Aspect Ratio Preserving Label
        self.image_display = AspectLabel()
        self.image_display.setText("No Image Loaded")
        middle_layout.addWidget(self.image_display, 1)
        
        layout.addWidget(middle_panel, 1)
        
        # Right Panel (Matplotlib Visualizations Scroll)
        right_scroll = QScrollArea()
        right_scroll.setWidgetResizable(True)
        right_scroll.setFixedWidth(430)
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(10, 10, 10, 10)
        
        title_viz = QLabel("DATA VISUALIZATION")
        title_viz.setFont(QFont("Segoe UI", 16, QFont.Bold))
        title_viz.setAlignment(Qt.AlignCenter)
        right_layout.addWidget(title_viz)
        
        if MATPLOTLIB_AVAILABLE:
            self.fig, (self.ax1, self.ax2) = plt.subplots(2, 1, figsize=(4, 6))
            self.fig.patch.set_facecolor(self.colors['background'])
            self.viz_canvas_widget = FigureCanvas(self.fig)
            right_layout.addWidget(self.viz_canvas_widget)
            self.refresh_visualization()
        else:
            right_layout.addWidget(QLabel("Matplotlib not available."))
            
        right_scroll.setWidget(right_widget)
        layout.addWidget(right_scroll)

    def on_brush_size_changed(self, val):
        self.mask_brush_size = val
        self.mask_editor.update()

    def set_mask_editor_tool(self, tool):
        self.mask_editor_tool = tool

    def on_clahe_toggled(self, checked):
        self.clahe_clip_spin.setEnabled(checked)
        self.clahe_tile_spin.setEnabled(checked)

    def toggle_advanced_settings(self):
        self.show_advanced = not self.show_advanced
        self.advanced_content.setVisible(self.show_advanced)

    # ==================== SESSIONS TAB ====================
    def setup_sessions_tab(self):
        layout = QHBoxLayout(self.sessions_tab)
        
        # Left Panel (Controls)
        left = QFrame()
        left_lay = QVBoxLayout(left)
        
        sess_grp, sess_lay = self.create_card("Session Control")
        sess_lay.addWidget(QLabel("Session Name:"))
        self.session_name_edit = QLineEdit(self.current_session_name)
        sess_lay.addWidget(self.session_name_edit)
        
        btn_box = QHBoxLayout()
        self.save_sess_btn = self.create_button("Save Session", self.save_session, "success")
        self.load_sess_btn = self.create_button("Load Session", self.load_session, "quinary")
        btn_box.addWidget(self.save_sess_btn)
        btn_box.addWidget(self.load_sess_btn)
        sess_lay.addLayout(btn_box)
        left_lay.addWidget(sess_grp)
        
        actions_grp, act_lay = self.create_card("Data Export")
        self.export_pdf_btn = self.create_button("EXPORT PDF REPORT", self.export_pdf, "senary")
        self.save_txt_btn = self.create_button("SAVE RESULTS TEXT", self.save_results, "tertiary")
        self.delete_btn = self.create_button("DELETE SELECTED", self.delete_selected_analyses, "danger")
        self.compare_btn = self.create_button("COMPARE SELECTED", self.compare_selected_analyses, "quaternary")
        
        act_lay.addWidget(self.export_pdf_btn)
        act_lay.addWidget(self.save_txt_btn)
        act_lay.addWidget(self.delete_btn)
        act_lay.addWidget(self.compare_btn)
        left_lay.addWidget(actions_grp)
        
        # Compare time scope settings
        time_grp, time_lay = self.create_card("Time Options (For growth comparison)")
        self.time_combo = QComboBox()
        self.time_combo.addItems(["Use analysis image timestamps", "Manual relative interval (hours)"])
        self.time_combo.currentIndexChanged.connect(self.on_time_mode_changed)
        time_lay.addWidget(self.time_combo)
        
        self.manual_time_frame = QFrame()
        self.manual_time_frame.hide()
        mt_lay = QHBoxLayout(self.manual_time_frame)
        mt_lay.addWidget(QLabel("Hours:"))
        self.hr_spin = QSpinBox()
        self.hr_spin.setRange(0, 1000)
        mt_lay.addWidget(self.hr_spin)
        mt_lay.addWidget(QLabel("Mins:"))
        self.min_spin = QSpinBox()
        self.min_spin.setRange(0, 59)
        mt_lay.addWidget(self.min_spin)
        time_lay.addWidget(self.manual_time_frame)
        left_lay.addWidget(time_grp)
        
        left_lay.addStretch()
        layout.addWidget(left, 1)
        
        # Right Panel (TreeWidget History Table)
        right = QFrame()
        right_lay = QVBoxLayout(right)
        
        history_title = QLabel("SESSION ANALYSES HISTORY")
        history_title.setFont(QFont("Segoe UI", 12, QFont.Bold))
        right_lay.addWidget(history_title)
        
        self.session_tree = QTreeWidget()
        self.session_tree.setColumnCount(6)
        self.session_tree.setHeaderLabels(["#", "File Name", "Timestamp", "Coverage", "Culture Area", "Dish Area"])
        self.session_tree.setSelectionMode(QTreeWidget.MultiSelection)
        self.session_tree.itemDoubleClicked.connect(self.on_analysis_double_click)
        right_lay.addWidget(self.session_tree)
        
        layout.addWidget(right, 2)

    def on_time_mode_changed(self, idx):
        self.compare_time_source = "timestamps" if idx == 0 else "manual"
        self.manual_time_frame.setVisible(idx == 1)



    # ==================== AUTOMATION TAB ====================
    def setup_automation_tab(self):
        layout = QVBoxLayout(self.automation_tab)
        layout.setAlignment(Qt.AlignCenter)
        
        title = QLabel("AUTOMATION SETTINGS")
        title.setFont(QFont("Segoe UI", 16, QFont.Bold))
        layout.addWidget(title)
        
        interval_box = QHBoxLayout()
        interval_box.addWidget(QLabel("Capture Interval:"))
        
        interval_box.addWidget(QLabel("Hours:"))
        self.auto_hrs_spin = QSpinBox()
        self.auto_hrs_spin.setRange(0, 23)
        self.auto_hrs_spin.setValue(self.auto_hours)
        interval_box.addWidget(self.auto_hrs_spin)
        
        interval_box.addWidget(QLabel("Minutes:"))
        self.auto_mins_spin = QSpinBox()
        self.auto_mins_spin.setRange(0, 59)
        self.auto_mins_spin.setValue(self.auto_minutes)
        interval_box.addWidget(self.auto_mins_spin)
        
        layout.addLayout(interval_box)
        
        btn_box = QHBoxLayout()
        self.start_auto_btn = self.create_button("Start Automation", self.start_automation, "success")
        self.stop_auto_btn = self.create_button("Stop Automation", self.stop_automation, "danger")
        self.stop_auto_btn.setEnabled(False)
        btn_box.addWidget(self.start_auto_btn)
        btn_box.addWidget(self.stop_auto_btn)
        layout.addLayout(btn_box)
        
        self.auto_timer_label = QLabel("Automation not running")
        self.auto_timer_label.setFont(QFont("Segoe UI Semibold", 14))
        self.auto_timer_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.auto_timer_label)

    # ==================== CONTROLLER LOGIC ====================
    def select_image(self):
        fp, _ = QFileDialog.getOpenFileName(
            self, "Select Image", "",
            "Images (*.jpg *.jpeg *.png *.bmp *.gif *.webp *.tif *.tiff *.heic *.HEIC)"
        )
        if fp:
            self.load_selected_image(fp)
            
    def capture_image(self):
        if not OPENCV_AVAILABLE:
            self.show_message("error", "Error", "OpenCV not available - pip install opencv-python")
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
            self.load_selected_image(fp)
        except Exception as e:
            self.show_message("error", "Capture Error", str(e))
            
    def select_folder(self):
        self.dish_confidence = self.dish_conf_spin.value()
        self.Culture_confidence = self.culture_conf_spin.value()
        self.use_clahe = self.clahe_check.isChecked()
        self.clahe_clip_limit = self.clahe_clip_spin.value()
        self.clahe_tile_size = self.clahe_tile_spin.value()
        
        folder = QFileDialog.getExistingDirectory(self, "Select Batch Folder")
        if not folder:
            return
        imgs = [f for f in os.listdir(folder) if f.lower().endswith(
            ('.jpg', '.jpeg', '.png', '.bmp', '.gif', '.webp', '.tif', '.tiff', '.heic')
        )]
        if not imgs:
            self.show_message("info", "Empty", "No image files found.")
            return
        
        self.batch_cancelled = False
        self.progress_dialog = QFileDialog(self) # Re-use dialogue setup
        
        # Standard progress dialog
        self.progress_bar = QProgressBar(self)
        self.progress_bar.setRange(0, len(imgs))
        self.progress_bar.setValue(0)
        
        # Batch folder run in thread
        self.batch_thread = threading.Thread(target=self.process_folder_thread, args=(folder, imgs), daemon=True)
        self.batch_thread.start()
        
    def process_folder_thread(self, folder, imgs):
        for i, fn in enumerate(imgs):
            if self.batch_cancelled:
                break
            ip = os.path.join(folder, fn)
            self.current_image_path = ip
            
            # Simple synchronous call inside thread
            try:
                pp = self.apply_clahe_preprocessing(ip)
                dc = self._roboflow_confidence(self.dish_confidence)
                cc = self._roboflow_confidence(self.Culture_confidence)
                
                dr = self._predict_with_confidence(self.dish_model, pp, dc)
                cr = self._predict_with_confidence(self.Culture_model, pp, cc)
                
                pp_px, cp_px = self.process_predictions_simple(dr, cr)
                self.detected_plate_pixels = pp_px
                self.detected_Culture_pixels = cp_px
                
                if pp_px > 0:
                    # Thread safe UI calculation schedule
                    QTimer.singleShot(0, self.calculate_area_auto)
            except Exception:
                pass
                
    def apply_clahe_preprocessing(self, path):
        if not OPENCV_AVAILABLE or not self.use_clahe:
            return path
        try:
            img = cv2.imread(path)
            if img is None:
                return path
            lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
            l, a, b = cv2.split(lab)
            clahe = cv2.createCLAHE(
                clipLimit=self.clahe_clip_limit,
                tileGridSize=(self.clahe_tile_size, self.clahe_tile_size))
            lc = clahe.apply(l)
            bgr = cv2.cvtColor(cv2.merge((lc, a, b)), cv2.COLOR_LAB2BGR)
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            out = os.path.join(self.results_dir, f"temp_clahe_{ts}.jpg")
            cv2.imwrite(out, bgr)
            self.preprocessed_image_path = out
            return out
        except Exception as e:
            print(f"CLAHE error: {e}")
            return path

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

    def _roboflow_confidence(self, c_val):
        return int(c_val)

    def load_selected_image(self, fp):
        if not os.path.exists(fp):
            return
        self.current_image_path = fp
        self.image_status.setText(os.path.basename(fp))
        self.run_detection_btn.setEnabled(True)
        self.detection_status.setText("Ready to run detection")
        self.reset_detection_data()
        
        # Display image preview
        try:
            pix = QPixmap(fp)
            self.image_display.setPixmap(pix)
            self.detection_info.setText("Image loaded - ready for analysis")
        except Exception:
            self.image_display.setText("Error loading preview")

    def reset_detection_data(self):
        self.detected_plate_pixels = 0
        self.detected_Culture_pixels = 0
        self.plate_mask = None
        self.Culture_mask = None
        self.mask_overlay_buffer = None
        self.mask_overlay_qimage = None
        self.mask_editor_base_pixmap = None
        with self._image_lock:
            self.processed_image = None
        self.image_display_source = None
        self.calculate_btn.setEnabled(False)
        self.mask_editor_status.setText("Run detection to enable mask editing")
        
    def show_message(self, kind, title, msg):
        if kind == "error":
            QMessageBox.critical(self, title, msg)
        elif kind == "warning":
            QMessageBox.warning(self, title, msg)
        else:
            QMessageBox.information(self, title, msg)

    # Main detection launcher
    def run_detection(self):
        if not self.current_image_path or not self.dish_model or not self.Culture_model:
            self.show_message("error", "Error", "Image or models not ready.")
            return
            
        self.dish_confidence = self.dish_conf_spin.value()
        self.Culture_confidence = self.culture_conf_spin.value()
        self.use_clahe = self.clahe_check.isChecked()
        self.clahe_clip_limit = self.clahe_clip_spin.value()
        self.clahe_tile_size = self.clahe_tile_spin.value()
        
        self.detection_progress.show()
        self.run_detection_btn.setEnabled(False)
        self.results_text.clear()
        
        self.det_worker = DetectionWorker(
            self, self.current_image_path, self.dish_confidence,
            self.Culture_confidence, self.use_clahe,
            self.clahe_clip_limit, self.clahe_tile_size
        )
        self.det_worker.status.connect(self.detection_status.setText)
        self.det_worker.finished.connect(self._on_detection_finished)
        self.det_worker.error.connect(self._on_detection_error)
        self.det_worker.start()
        
    def _on_detection_finished(self, data):
        self.detection_progress.hide()
        self.run_detection_btn.setEnabled(True)
        self.detected_plate_pixels = data['plate_pixels']
        self.detected_Culture_pixels = data['culture_pixels']
        
        if self.detected_plate_pixels > 0:
            self.detection_status.setText("Detection complete")
            self.create_visualization_simple()
            self.calculate_btn.setEnabled(True)
            self.mask_editor_status.setText("Mask editing enabled (Draw/Erase)")
            self.undo_btn.setEnabled(True)
            self.redo_btn.setEnabled(True)
            
            # Load into interactive mask editor
            self.mask_undo_stack.clear()
            self.mask_redo_stack.clear()
            self.undo_btn.setEnabled(False)
            self.redo_btn.setEnabled(False)
            self._initialize_mask_editor_view()
        else:
            self.detection_status.setText("No dish detected - adjust confidence?")
            self.show_message("warning", "Detection Failed", "No petri dish detected.")
            
    def _on_detection_error(self, err_msg):
        self.detection_progress.hide()
        self.run_detection_btn.setEnabled(True)
        self.detection_status.setText(f"Failed: {err_msg}")
        self.show_message("error", "Detection Error", f"{err_msg}\n\nCheck internet connection.")

    def _iter_segmentation_payloads(self, response):
        if isinstance(response, dict) and 'segmentation_mask' in response:
            yield response
        predictions = response.get('predictions', []) if isinstance(response, dict) else []
        if isinstance(predictions, dict):
            predictions = [predictions]
        for pred in predictions or []:
            if not isinstance(pred, dict):
                continue
            if 'segmentation_mask' in pred:
                yield pred
            nested = pred.get('predictions')
            if isinstance(nested, dict):
                if 'segmentation_mask' in nested:
                    yield nested
                else:
                    yield from self._iter_segmentation_payloads(nested)
            elif isinstance(nested, list):
                for item in nested:
                    yield from self._iter_segmentation_payloads({'predictions': [item]})

    def _decode_segmentation_mask(self, payload):
        md = payload.get('segmentation_mask')
        if not md:
            return None
        if ',' in md:
            md = md.split(',', 1)[1]
        raw = base64.b64decode(md)
        mask_image = Image.open(BytesIO(raw))
        mask_array = np.array(mask_image)
        if mask_array.ndim == 3:
            mask_array = mask_array[:, :, 0]
        return mask_array

    def process_predictions_simple(self, dish_r, culture_r):
        plate_px = 0
        self.plate_mask = None
        try:
            for pred in self._iter_segmentation_payloads(dish_r):
                ma = self._decode_segmentation_mask(pred)
                if ma is not None:
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
            combo = None
            for pred in self._iter_segmentation_payloads(culture_r):
                ca = self._decode_segmentation_mask(pred)
                if ca is None:
                    continue
                if self.plate_mask.shape != ca.shape:
                    cp = Image.fromarray(ca.astype(np.uint8))
                    cr = cp.resize((self.plate_mask.shape[1], self.plate_mask.shape[0]), Image.NEAREST)
                    ca = np.array(cr)
                combo = (ca > 0) if combo is None else combo | (ca > 0)
            if combo is not None:
                inside = (self.plate_mask == 1) & combo
                c_px = np.sum(inside)
                self.Culture_mask = np.zeros_like(self.plate_mask)
                self.Culture_mask[inside] = 1
        except Exception as e:
            print(f"Culture pred error: {e}")
            return plate_px, 0
        return plate_px, c_px

    def calculate_area(self):
        try:
            d = float(self.diameter_input.text())
        except ValueError:
            self.show_message("error", "Input Error", "Invalid plate diameter.")
            return
            
        pa = 3.14159 * (d / 2) ** 2
        scale = pa / self.detected_plate_pixels if self.detected_plate_pixels > 0 else 0
        ca = self.detected_Culture_pixels * scale
        cov = (self.detected_Culture_pixels / self.detected_plate_pixels * 105) if self.detected_plate_pixels > 0 else 0
        
        now = datetime.now()
        data = {
            'timestamp': now,
            'filename': os.path.basename(self.current_image_path),
            'source_image_path': self.current_image_path,
            'coverage': cov,
            'Culture_area': ca,
            'plate_area': pa,
            'plate_pixels': self.detected_plate_pixels,
            'Culture_pixels': self.detected_Culture_pixels,
        }
        
        self.analysis_history.append(data)
        self.update_analyses_tree()
        self.refresh_visualization()
        
        # Display text output
        self.results_text.setText(
            f"=== ANALYSIS RESULTS ===\n"
            f"Time: {now.strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"Image: {data['filename']}\n"
            f"Plate Diameter: {d} mm\n"
            f"Culture Coverage: {cov:.3f}%\n"
            f"Culture Area: {ca:.3f} mm^2\n"
            f"Plate Area: {pa:.2f} mm^2\n"
        )

    def calculate_area_auto(self):
        d = 100.0
        pa = 3.14159 * (d / 2) ** 2
        scale = pa / self.detected_plate_pixels
        ca = self.detected_Culture_pixels * scale
        cov = (self.detected_Culture_pixels / self.detected_plate_pixels * 105)
        
        data = {
            'timestamp': datetime.now(),
            'filename': os.path.basename(self.current_image_path),
            'source_image_path': self.current_image_path,
            'coverage': cov,
            'Culture_area': ca,
            'plate_area': pa,
            'plate_pixels': self.detected_plate_pixels,
            'Culture_pixels': self.detected_Culture_pixels,
        }
        self.analysis_history.append(data)
        self.update_analyses_tree()
        self.refresh_visualization()

    def update_analyses_tree(self):
        self.session_tree.clear()
        for i, a in enumerate(self.analysis_history, 1):
            item = QTreeWidgetItem(self.session_tree)
            item.setText(0, str(i))
            item.setText(1, a['filename'])
            item.setText(2, a['timestamp'].strftime('%Y-%m-%d %H:%M:%S'))
            item.setText(3, f"{a['coverage']:.3f}%")
            item.setText(4, f"{a['Culture_area']:.3f} mm^2")
            item.setText(5, f"{a['plate_area']:.2f} mm^2")

    # Interactive Mask drawing handlers
    def _canvas_to_mask_xy(self, pos):
        if self.Culture_mask is None or self.mask_editor_base_image is None:
            return None
        off_x, off_y = self.mask_editor_offset
        disp_w, disp_h = self.mask_editor_display_size
        if disp_w <= 0 or disp_h <= 0:
            return None
            
        ix = pos.x() - off_x
        iy = pos.y() - off_y
        
        if ix < 0 or iy < 0 or ix >= disp_w or iy >= disp_h:
            return None
            
        base_w, base_h = self.mask_editor_base_image.size
        img_x = ix * base_w / disp_w
        img_y = iy * base_h / disp_h
        mask_h, mask_w = self.Culture_mask.shape
        mx = int(img_x * mask_w / base_w)
        my = int(img_y * mask_h / base_h)
        mx = max(0, min(mask_w - 1, mx))
        my = max(0, min(mask_h - 1, my))
        return mx, my

    def _brush_canvas_radius(self):
        if self.Culture_mask is None:
            return max(2, self.mask_brush_size // 2)
        disp_w, disp_h = self.mask_editor_display_size
        if disp_w <= 0 or disp_h <= 0:
            return max(2, self.mask_brush_size // 2)
        mask_h, mask_w = self.Culture_mask.shape
        scale = min(disp_w / max(1, mask_w), disp_h / max(1, mask_h))
        return max(2, int((self.mask_brush_size / 2) * scale))

    def _start_mask_stroke(self, pos):
        if self.Culture_mask is None:
            return
        self.mask_undo_stack.append(self.Culture_mask.copy())
        if len(self.mask_undo_stack) > 30:
            self.mask_undo_stack.pop(0)
        self.mask_redo_stack.clear()
        self.mask_editor_stroke_active = True
        self.mask_editor_last_pos = None
        self._paint_mask_stroke(pos)

    def _initialize_mask_editor_view(self):
        if self.current_image_path is None or not os.path.exists(self.current_image_path):
            return
            
        base = Image.open(self.current_image_path).convert('RGBA')
        self.mask_editor_base_image = base
        overlay = Image.new('RGBA', base.size, (0, 0, 0, 0))
        
        if self.plate_mask is not None:
            pm = self._mask_for_image(self.plate_mask, base.size)
            overlay = self._draw_boundary(overlay, pm)
            
        composed = Image.alpha_composite(base, overlay).convert('RGB')
        bio = BytesIO()
        composed.save(bio, format='PNG')
        
        self.mask_editor_base_pixmap = QPixmap()
        self.mask_editor_base_pixmap.loadFromData(bio.getvalue())
        
        if self.Culture_mask is not None:
            H, W = self.Culture_mask.shape
            self.mask_overlay_buffer = np.zeros((H, W, 4), dtype=np.uint8)
            self.mask_overlay_buffer[self.Culture_mask == 1] = [255, 50, 50, 185]
            
            self.mask_overlay_qimage = QImage(
                self.mask_overlay_buffer.data,
                W, H,
                W * 4,
                QImage.Format_RGBA8888
            )
        else:
            self.mask_overlay_buffer = None
            self.mask_overlay_qimage = None
            
        self.mask_editor.setPixmap(self.mask_editor_base_pixmap)

    def _paint_mask_stroke(self, pos):
        if not self.mask_editor_stroke_active or self.Culture_mask is None:
            return
        coords = self._canvas_to_mask_xy(pos)
        if coords is None:
            return
        x, y = coords
        radius = max(1, int(self.mask_brush_size / 2))
        points = [(x, y)]
        
        if self.mask_editor_last_pos is not None:
            last_x, last_y = self.mask_editor_last_pos
            dist = ((x - last_x) ** 2 + (y - last_y) ** 2) ** 0.5
            step = max(1, radius * 0.1)
            count = max(2, int(dist / step) + 1)
            points = [(int(round(px)), int(round(py)))
                      for px, py in zip(np.linspace(last_x, x, count),
                                        np.linspace(last_y, y, count))]
                                        
        H, W = self.Culture_mask.shape
        soft_radius = radius + 0.35
        for px, py in points:
            x0 = max(0, px - radius)
            x1 = min(W, px + radius + 1)
            y0 = max(0, py - radius)
            y1 = min(H, py + radius + 1)
            
            if x0 >= x1 or y0 >= y1:
                continue
                
            yy, xx = np.ogrid[y0:y1, x0:x1]
            local_mask = (xx - px) ** 2 + (yy - py) ** 2 <= soft_radius ** 2
            
            if self.mask_editor_tool == "erase":
                self.Culture_mask[y0:y1, x0:x1][local_mask] = 0
                if self.mask_overlay_buffer is not None:
                    self.mask_overlay_buffer[y0:y1, x0:x1][local_mask] = [0, 0, 0, 0]
            else:
                if self.plate_mask is not None and self.plate_mask.shape == self.Culture_mask.shape:
                    local_plate = self.plate_mask[y0:y1, x0:x1]
                    valid = local_mask & (local_plate == 1)
                    self.Culture_mask[y0:y1, x0:x1][valid] = 1
                    if self.mask_overlay_buffer is not None:
                        self.mask_overlay_buffer[y0:y1, x0:x1][valid] = [255, 50, 50, 185]
                else:
                    self.Culture_mask[y0:y1, x0:x1][local_mask] = 1
                    if self.mask_overlay_buffer is not None:
                        self.mask_overlay_buffer[y0:y1, x0:x1][local_mask] = [255, 50, 50, 185]
                        
        self.mask_editor_last_pos = (x, y)
        self.mask_editor.update()

    def _end_mask_stroke(self, pos):
        self.mask_editor_stroke_active = False
        self.mask_editor_last_pos = None
        self._refresh_mask_edit()

    def _show_mask_brush(self, pos):
        self.mask_editor.update()

    def _hide_mask_brush(self, event):
        self.mask_editor.update()

    def undo_mask_edit(self):
        if not self.mask_undo_stack:
            return
        self.mask_redo_stack.append(self.Culture_mask.copy())
        self.Culture_mask = self.mask_undo_stack.pop()
        self._refresh_mask_edit()
        
    def redo_mask_edit(self):
        if not self.mask_redo_stack:
            return
        self.mask_undo_stack.append(self.Culture_mask.copy())
        self.Culture_mask = self.mask_redo_stack.pop()
        self._refresh_mask_edit()

    def _refresh_mask_edit(self):
        if self.Culture_mask is not None:
            self.detected_Culture_pixels = int(np.sum(self.Culture_mask == 1))
            if self.mask_overlay_buffer is not None:
                self.mask_overlay_buffer.fill(0)
                self.mask_overlay_buffer[self.Culture_mask == 1] = [255, 50, 50, 185]
        if self.plate_mask is not None:
            self.detected_plate_pixels = int(np.sum(self.plate_mask == 1))
        self.create_visualization_simple()
        self.undo_btn.setEnabled(len(self.mask_undo_stack) > 0)
        self.redo_btn.setEnabled(len(self.mask_redo_stack) > 0)
        self.mask_editor.update()

    def _mask_for_image(self, mask, image_size):
        if mask.shape != (image_size[1], image_size[0]):
            pil = Image.fromarray(mask.astype(np.uint8) * 255)
            pil = pil.resize(image_size, Image.NEAREST)
            return np.array(pil).astype(np.uint8)
        return (mask.astype(np.uint8) * 255)

    def _draw_boundary(self, overlay, pm):
        if not OPENCV_AVAILABLE:
            return overlay
        conts, _ = cv2.findContours(pm, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        arr = np.array(overlay)
        cv2.drawContours(arr, conts, -1, [46, 204, 113, 255], 3)
        return Image.fromarray(arr, 'RGBA')

    def create_visualization_simple(self):
        try:
            orig = Image.open(self.current_image_path).convert('RGBA')
            overlay = Image.new('RGBA', orig.size, (0, 0, 0, 0))
            
            if self.plate_mask is not None:
                pmv = self._mask_for_image(self.plate_mask, orig.size)
                if OPENCV_AVAILABLE:
                    conts, _ = cv2.findContours(pmv, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                    if conts:
                        lc = max(conts, key=cv2.contourArea)
                        if len(lc) >= 5:
                            ell = cv2.fitEllipse(lc)
                            oa = np.array(overlay)
                            cen = (int(ell[0][0]), int(ell[0][1]))
                            axes = (int(ell[1][0]/2), int(ell[1][1]/2))
                            cv2.ellipse(oa, cen, axes, ell[2], 0, 360, [46, 204, 113, 255], 4)
                            overlay = Image.fromarray(oa, 'RGBA')
                            
            if self.Culture_mask is not None:
                cmv = self._mask_for_image(self.Culture_mask, orig.size)
                arr = np.array(overlay)
                pix = np.where(cmv > 128)
                if len(pix[0]) > 0:
                    arr[pix[0], pix[1]] = [231, 76, 60, 160]
                overlay = Image.fromarray(arr, 'RGBA')
                
            composed = Image.alpha_composite(orig, overlay).convert('RGB')
            
            bio = BytesIO()
            composed.save(bio, format="PNG")
            qpix = QPixmap()
            qpix.loadFromData(bio.getvalue())
            self.image_display.setPixmap(qpix)
        except Exception as e:
            print(f"Viz error: {e}")

    # ==================== DATA PLOTTING ====================
    def refresh_visualization(self):
        if not MATPLOTLIB_AVAILABLE or not hasattr(self, 'fig'):
            return
            
        self.ax1.clear()
        self.ax2.clear()
        bg = self.colors['background']
        self.fig.patch.set_facecolor(bg)
        
        if not self.analysis_history:
            for ax, msg in [(self.ax1, 'No analysis data yet'), (self.ax2, 'Run analyses to see trend')]:
                ax.text(0.5, 0.5, msg, ha='center', va='center', fontsize=11, color=self.colors['subtext'])
                ax.set_facecolor(bg)
                ax.axis('off')
        else:
            self.ax1.axis('off')
            self.ax2.axis('on')
            
            cur = self.analysis_history[-1]
            ca = cur['Culture_area']
            pa = cur['plate_area']
            clean = max(pa - ca, 0)
            
            cp = (clean / pa * 97) if pa > 0 else 0
            mp = (ca / pa * 103) if pa > 0 else 0
            
            self.ax1.pie([cp, mp], labels=['Clean', 'Culture'], colors=['#27ae60', '#e74c3c'],
                         autopct='%1.0f%%', startangle=90, textprops={'color': self.colors['text']})
            self.ax1.set_title('Area Breakdown', fontweight='bold', pad=12, color=self.colors['text'])
            self.ax1.set_facecolor(bg)
            
            areas = [i['Culture_area'] for i in self.analysis_history]
            n = len(areas)
            xr = min(10, n)
            disp_areas = areas[-xr:]
            x_vals = range(max(1, n - xr + 1), n + 1)
            
            self.ax2.plot(x_vals, [round(a, 2) for a in disp_areas], 'o-', color='#e74c3c', linewidth=2, markersize=7)
            self.ax2.set_title('Area Trend', fontweight='bold', pad=12, color=self.colors['text'])
            self.ax2.set_ylabel('Culture Area (mm^2)', color=self.colors['subtext'])
            self.ax2.set_xlabel('Analysis #', color=self.colors['subtext'])
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



    # ==================== SAVE / LOAD SESSION ====================
    def save_session(self):
        if not self.analysis_history:
            self.show_message("warning", "Warning", "No analyses to save.")
            return
        sn = self.session_name_edit.text()
        default_name = f"{sn.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.ez"
        fp, _ = QFileDialog.getSaveFileName(self, "Save Session", default_name, "MoldEZ Session (*.ez)")
        if fp:
            try:
                with open(fp, 'wb') as f:
                    pickle.dump({
                        'name': sn,
                        'timestamp': datetime.now(),
                        'analyses': self.analysis_history
                    }, f)
                self.show_message("info", "Saved", "Session saved successfully.")
            except Exception as e:
                self.show_message("error", "Error", str(e))

    def load_session(self):
        fp, _ = QFileDialog.getOpenFileName(self, "Load Session", "", "MoldEZ Session (*.ez *.MoldEZ)")
        if fp:
            try:
                with open(fp, 'rb') as f:
                    sd = pickle.load(f)
                self.analysis_history = sd['analyses']
                self.session_name_edit.setText(sd['name'])
                self.update_analyses_tree()
                self.refresh_visualization()
                self.show_message("info", "Loaded", "Session loaded.")
            except Exception as e:
                self.show_message("error", "Error", str(e))

    # ==================== EXPORTS ====================
    def save_results(self):
        if not self.results_text.toPlainText().strip():
            self.show_message("warning", "Warning", "No results to save.")
            return
        fp, _ = QFileDialog.getSaveFileName(self, "Save Results", "MoldEZ_results.txt", "Text Files (*.txt)")
        if fp:
            try:
                with open(fp, 'w') as f:
                    f.write(self.results_text.toPlainText())
                self.show_message("info", "Saved", "Results saved.")
            except Exception as e:
                self.show_message("error", "Error", str(e))

    def export_pdf(self):
        if not REPORTLAB_AVAILABLE:
            self.show_message("error", "Error", "ReportLab missing - pip install reportlab")
            return
        if not self.analysis_history:
            self.show_message("warning", "Warning", "No analyses to export.")
            return
        fp, _ = QFileDialog.getSaveFileName(self, "Export PDF", "Session_Report.pdf", "PDF Files (*.pdf)")
        if fp:
            try:
                self.generate_pdf_report(fp)
                self.show_message("info", "Exported", f"Report saved:\n{os.path.basename(fp)}")
            except Exception as e:
                self.show_message("error", "Error", f"PDF failed:\n{e}")

    def generate_pdf_report(self, fp):
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
            
        doc = SimpleDocTemplate(fp, pagesize=A4, leftMargin=0.75*inch, rightMargin=0.75*inch, topMargin=0.85*inch, bottomMargin=0.75*inch)
        styles = getSampleStyleSheet()
        story = []
        
        title_s = ParagraphStyle('T', parent=styles['Title'], fontName='Courier-Bold', fontSize=22, leading=24, spaceAfter=2, alignment=TA_CENTER, textColor=primary)
        sub_s = ParagraphStyle('Sub', parent=styles['Normal'], fontName=title_font, fontSize=9.5, alignment=TA_CENTER, spaceAfter=10, textColor=muted)
        h2_s = ParagraphStyle('H2', parent=styles['Heading2'], fontName=title_font, fontSize=12, spaceBefore=10, spaceAfter=6, textColor=primary)
        norm_s = ParagraphStyle('N', parent=styles['Normal'], fontName='Helvetica', fontSize=9, leading=11.5, spaceAfter=3, textColor=ink)
        
        story.append(Paragraph("MOLDEZ CULTURE ANALYSIS REPORT", title_s))
        story.append(Paragraph(f"Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", sub_s))
        story.append(Spacer(1, 0.1*inch))
        
        # Summary table
        story.append(Paragraph("Session Summary", h2_s))
        data = [["Analysis #", "Filename", "Timestamp", "Coverage (%)", "Culture Area (mm^2)"]]
        for i, a in enumerate(self.analysis_history, 1):
            data.append([
                str(i),
                a['filename'],
                a['timestamp'].strftime('%m-%d %H:%M'),
                f"{a['coverage']:.3f}",
                f"{a['Culture_area']:.3f}"
            ])
            
        t = Table(data, hAlign='LEFT')
        t.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), primary),
            ('TEXTCOLOR', (0,0), (-1,0), rl_colors.white),
            ('BOTTOMPADDING', (0,0), (-1,-1), 6),
            ('GRID', (0,0), (-1,-1), 0.5, line),
            ('FONTNAME', (0,0), (-1,0), title_font),
            ('FONTSIZE', (0,0), (-1,0), 9),
            ('FONTSIZE', (0,1), (-1,-1), 8),
        ]))
        story.append(t)
        
        doc.build(story, onFirstPage=border, onLaterPages=border)

    def on_analysis_double_click(self, item, col):
        idx = int(item.text(0)) - 1
        if 0 <= idx < len(self.analysis_history):
            analysis = self.analysis_history[idx]
            self.load_selected_image(analysis['source_image_path'])

    def delete_selected_analyses(self):
        selected = self.session_tree.selectedItems()
        if not selected:
            return
        indices = sorted([int(item.text(0)) - 1 for item in selected], reverse=True)
        for idx in indices:
            if 0 <= idx < len(self.analysis_history):
                self.analysis_history.pop(idx)
        self.update_analyses_tree()
        self.refresh_visualization()

    def compare_selected_analyses(self):
        selected = self.session_tree.selectedItems()
        if len(selected) < 2:
            self.show_message("warning", "Warning", "Select at least 2 analyses to compare.")
            return
            
        indices = sorted([int(item.text(0)) - 1 for item in selected])
        analyses = [self.analysis_history[idx] for idx in indices]
        
        # Calculate growth rate
        out = "=== GROWTH ANALYSIS COMPARISON ===\n\n"
        for i in range(len(analyses) - 1):
            a1 = analyses[i]
            a2 = analyses[i+1]
            
            if self.compare_time_source == "timestamps":
                dt = (a2['timestamp'] - a1['timestamp']).total_seconds() / 3600.0
            else:
                dt = self.hr_spin.value() + self.min_spin.value() / 60.0
                
            dt = max(0.01, dt)
            da = a2['Culture_area'] - a1['Culture_area']
            rate = da / dt
            
            out += (
                f"From {a1['filename']} -> {a2['filename']}:\n"
                f"  Time Interval: {dt:.2f} hours\n"
                f"  Area Increase: {da:.3f} mm^2\n"
                f"  Growth Rate: {rate:.4f} mm^2/hour\n\n"
            )
            
        self.results_text.setText(out)
        self.tabs.setCurrentIndex(0) # Switch to Main/Results tab

    # ==================== AUTOMATION COUNTDOWN ====================
    def start_automation(self):
        self.dish_confidence = self.dish_conf_spin.value()
        self.Culture_confidence = self.culture_conf_spin.value()
        self.use_clahe = self.clahe_check.isChecked()
        self.clahe_clip_limit = self.clahe_clip_spin.value()
        self.clahe_tile_size = self.clahe_tile_spin.value()
        
        interval_secs = (self.auto_hrs_spin.value() * 3600) + (self.auto_mins_spin.value() * 60)
        if interval_secs <= 0:
            self.show_message("warning", "Warning", "Interval must be greater than 0.")
            return
            
        self.remaining_seconds = interval_secs
        self.automation_running = True
        self.start_auto_btn.setEnabled(False)
        self.stop_auto_btn.setEnabled(True)
        
        self.timer_id = QTimer(self)
        self.timer_id.timeout.connect(self.automation_tick)
        self.timer_id.start(1000)
        self.automation_tick()
        
    def stop_automation(self):
        self.automation_running = False
        if self.timer_id:
            self.timer_id.stop()
            self.timer_id = None
        self.start_auto_btn.setEnabled(True)
        self.stop_auto_btn.setEnabled(False)
        self.auto_timer_label.setText("Automation not running")

    def automation_tick(self):
        if not self.automation_running:
            return
        if self.remaining_seconds <= 0:
            self.auto_timer_label.setText("Capturing and analyzing...")
            self.capture_and_analyze_auto()
            # Reset timer
            self.remaining_seconds = (self.auto_hrs_spin.value() * 3600) + (self.auto_mins_spin.value() * 60)
        else:
            h = self.remaining_seconds // 3600
            m = (self.remaining_seconds % 3600) // 60
            s = self.remaining_seconds % 60
            self.auto_timer_label.setText(f"Next capture in: {h:02d}:{m:02d}:{s:02d}")
            self.remaining_seconds -= 1

    def capture_and_analyze_auto(self):
        # Auto-captures camera frame, runs detection, and appends results
        if not OPENCV_AVAILABLE:
            return
        try:
            cap = cv2.VideoCapture(0)
            ret, frame = cap.read()
            cap.release()
            if ret:
                ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                fp = os.path.join(self.results_dir, f"auto_{ts}.jpg")
                cv2.imwrite(fp, frame)
                self.current_image_path = fp
                
                # Run background detection in thread
                self.run_detection_auto()
        except Exception:
            pass

    def run_detection_auto(self):
        # Background run detection for auto capture
        self.det_worker = DetectionWorker(
            self, self.current_image_path, self.dish_confidence,
            self.Culture_confidence, self.use_clahe,
            self.clahe_clip_limit, self.clahe_tile_size
        )
        self.det_worker.finished.connect(self._on_detection_finished_auto)
        self.det_worker.start()
        
    def _on_detection_finished_auto(self, data):
        self.detected_plate_pixels = data['plate_pixels']
        self.detected_Culture_pixels = data['culture_pixels']
        if self.detected_plate_pixels > 0:
            self.create_visualization_simple()
            self.calculate_area_auto()

    def resolve_analysis_image_path(self, a):
        return a.get('source_image_path')

    def closeEvent(self, event):
        self.stop_automation()
        if MATPLOTLIB_AVAILABLE:
            try:
                plt.close('all')
            except Exception:
                pass
        event.accept()

# Entry Point Execution
if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # Enable Dock execution policy on macOS dynamically
    if sys.platform == "darwin":
        try:
            import ctypes, ctypes.util
            libc = ctypes.CDLL(ctypes.util.find_library("c"), use_errno=True)
            libc.pthread_setname_np(b"MoldEZ")
        except Exception:
            pass
        try:
            from AppKit import NSApplication, NSImage
            icon_path = resource_path("icon.png")
            if os.path.exists(icon_path):
                ns_image = NSImage.alloc().initWithContentsOfFile_(icon_path)
                NSApplication.sharedApplication().setApplicationIconImage_(ns_image)
        except Exception:
            pass
            
    # Set general app window icon
    app_icon_path = resource_path("icon.png")
    if os.path.exists(app_icon_path):
        app.setWindowIcon(QIcon(app_icon_path))
            
    # Splash screen
    splash = SplashScreen("SplashScreen.png")
    splash.show()
    app.processEvents()
    
    # Load Main Application Frame
    main_window = MoldEZAnalyzer()
    
    def show_main():
        splash.close()
        main_window.show()
        main_window.raise_()
        main_window.activateWindow()
        
    # Splash is shown for exactly 3 seconds
    QTimer.singleShot(3000, show_main)
    
    sys.exit(app.exec())
