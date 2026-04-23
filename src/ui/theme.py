"""
LogRaptorX - Professional Theme + Pyramid Watermark
Developer: Kennedy Aikohi
"""

from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPainter, QColor, QPen, QLinearGradient, QBrush, QFont, QPainterPath


# -------------------------------------------------------
#  Pyramid Watermark Background Widget
# -------------------------------------------------------

class PyramidBackground(QWidget):
    """
    3D wireframe pyramid watermark -- visible, production-grade.
    Positioned centre-right so it never covers text.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        W, H = self.width(), self.height()

        # Pyramid anchored centre-right, large enough to be seen
        cx      = W * 0.75
        base_y  = H * 0.82
        half_b  = min(W, H) * 0.28
        pyr_h   = min(W, H) * 0.52

        apex = (cx,              base_y - pyr_h)
        bl   = (cx - half_b,    base_y)
        br   = (cx + half_b,    base_y)
        fl   = (cx - half_b * 0.55, base_y - half_b * 0.22)
        fr   = (cx + half_b * 0.55, base_y - half_b * 0.22)

        def pt(p): return int(p[0]), int(p[1])

        # ---- Filled faces (subtle but visible) ----
        def draw_face(pts, color_hex, alpha):
            path = QPainterPath()
            path.moveTo(*pts[0])
            for p in pts[1:]:
                path.lineTo(*p)
            path.closeSubpath()
            c = QColor(color_hex)
            c.setAlpha(alpha)
            painter.setBrush(QBrush(c))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawPath(path)

        # Back face (darkest)
        draw_face([apex, bl, br],  "#1A2A50", 30)
        # Left face
        draw_face([apex, bl, fl],  "#2A4A8A", 38)
        # Right face
        draw_face([apex, br, fr],  "#1E3A70", 28)
        # Front face (brightest, most visible)
        draw_face([apex, fl, fr],  "#3A6AC0", 48)
        # Base
        draw_face([bl, br, fr, fl], "#0E1830", 22)

        # ---- Wireframe edges ----
        solid_edges = [
            (apex, fl), (apex, fr), (fl, fr),   # front face
            (apex, bl), (apex, br),              # back edges
        ]
        solid_pen = QPen(QColor(80, 130, 220, 90), 1.2, Qt.PenStyle.SolidLine)
        painter.setPen(solid_pen)
        for p1, p2 in solid_edges:
            painter.drawLine(*pt(p1), *pt(p2))

        # Hidden/back edges dashed
        dash_pen = QPen(QColor(60, 100, 180, 45), 0.8, Qt.PenStyle.DashLine)
        painter.setPen(dash_pen)
        hidden_edges = [(bl, fl), (br, fr), (bl, br)]
        for p1, p2 in hidden_edges:
            painter.drawLine(*pt(p1), *pt(p2))

        # ---- Grid lines on front face (depth effect) ----
        grid_pen = QPen(QColor(60, 100, 200, 22), 0.6, Qt.PenStyle.SolidLine)
        painter.setPen(grid_pen)
        steps = 5
        for i in range(1, steps):
            t = i / steps
            # Horizontal lines across the front face
            lx1 = apex[0] + (fl[0] - apex[0]) * t
            ly1 = apex[1] + (fl[1] - apex[1]) * t
            lx2 = apex[0] + (fr[0] - apex[0]) * t
            ly2 = apex[1] + (fr[1] - apex[1]) * t
            painter.drawLine(int(lx1), int(ly1), int(lx2), int(ly2))
            # Vertical lines from apex down
            mx = apex[0] + (fl[0] + (fr[0] - fl[0]) * (i / steps) - apex[0]) * 1.0
            my = apex[1] + (fl[1] + (fr[1] - fl[1]) * (i / steps) - apex[1]) * 1.0
            painter.drawLine(*pt(apex), int(mx), int(my))

        # ---- Glowing apex ----
        painter.setPen(Qt.PenStyle.NoPen)
        for r, a in [(16, 8), (10, 18), (5, 40), (2, 80)]:
            c = QColor(80, 140, 255, a)
            painter.setBrush(QBrush(c))
            painter.drawEllipse(int(apex[0]) - r, int(apex[1]) - r, r * 2, r * 2)

        # ---- Watermark text ----
        painter.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        painter.setPen(QColor(60, 100, 200, 35))
        painter.drawText(
            int(cx - half_b), int(base_y + 8),
            "LogRaptorX  --  Kennedy Aikohi"
        )

        painter.end()



# -------------------------------------------------------
#  Qt Stylesheet
# -------------------------------------------------------

DARK_THEME = """
/* === Base === */
* {
    font-family: 'Segoe UI', Arial, sans-serif;
    font-size: 12px;
    color: #CDD3DE;
}

QMainWindow, QDialog {
    background-color: #0E1015;
}

QWidget {
    background-color: #0E1015;
}

/* === Menu Bar === */
QMenuBar {
    background-color: #0A0C10;
    border-bottom: 1px solid #1E2130;
    padding: 1px 4px;
}
QMenuBar::item {
    background: transparent;
    padding: 4px 12px;
    color: #7A8494;
}
QMenuBar::item:selected {
    background-color: #1A1D24;
    color: #E0E4EC;
    border-radius: 3px;
}
QMenu {
    background-color: #13151C;
    border: 1px solid #2A2D35;
    padding: 2px 0;
}
QMenu::item {
    padding: 5px 24px;
    color: #BEC4CE;
}
QMenu::item:selected {
    background-color: #2A5298;
    color: #FFFFFF;
}
QMenu::separator {
    height: 1px;
    background: #1E2130;
    margin: 3px 6px;
}

/* === Status Bar === */
QStatusBar {
    background-color: #2A5298;
    color: #E8ECF4;
    font-size: 11px;
    padding: 2px 8px;
    border: none;
}
QStatusBar::item { border: none; }

/* === Tab Widget === */
QTabWidget::pane {
    border: none;
    border-top: 1px solid #1E2130;
    background-color: #0E1015;
}
QTabBar::tab {
    background-color: #0A0C10;
    color: #4A5260;
    padding: 7px 22px;
    border: none;
    border-bottom: 2px solid transparent;
    font-size: 11px;
    letter-spacing: 0.5px;
    min-width: 100px;
}
QTabBar::tab:selected {
    background-color: #0E1015;
    color: #E0E4EC;
    border-bottom: 2px solid #2A5298;
}
QTabBar::tab:hover:!selected {
    color: #8090A0;
    background-color: #0E1015;
}

/* === Push Button === */
QPushButton {
    background-color: #1A1D24;
    color: #9098A6;
    border: 1px solid #2A2D38;
    border-radius: 3px;
    padding: 5px 14px;
    font-size: 12px;
}
QPushButton:hover {
    background-color: #22252E;
    border: 1px solid #3A3D50;
    color: #CDD3DE;
}
QPushButton:pressed {
    background-color: #0E1015;
}
QPushButton:disabled {
    background-color: #0E1015;
    color: #2A2D38;
    border: 1px solid #1A1D24;
}

QPushButton#primaryBtn {
    background-color: #2A5298;
    color: #FFFFFF;
    border: none;
    font-weight: 600;
    padding: 6px 18px;
}
QPushButton#primaryBtn:hover {
    background-color: #3362B0;
}
QPushButton#primaryBtn:pressed {
    background-color: #1E3F78;
}
QPushButton#primaryBtn:disabled {
    background-color: #0E1A30;
    color: #2A3A50;
}

QPushButton#dangerBtn {
    background-color: #1A1D24;
    color: #C05050;
    border: 1px solid #3A1A1A;
}
QPushButton#dangerBtn:hover {
    background-color: #2A1010;
    color: #E07070;
    border: 1px solid #5A2A2A;
}
QPushButton#dangerBtn:checked {
    background-color: #2A1010;
    color: #E07070;
    border: 1px solid #5A2020;
}

/* === Line Edit === */
QLineEdit {
    background-color: #0A0C10;
    border: 1px solid #1E2130;
    border-radius: 3px;
    padding: 5px 9px;
    font-size: 12px;
    color: #BEC4CE;
    selection-background-color: #2A5298;
}
QLineEdit:focus {
    border: 1px solid #2A5298;
}

/* === Text Edit === */
QTextEdit, QPlainTextEdit {
    background-color: #0A0C10;
    border: 1px solid #1E2130;
    color: #9098A6;
    font-size: 11px;
    selection-background-color: #2A5298;
    padding: 4px;
}

/* === Table Widget === */
QTableWidget {
    background-color: #0A0C10;
    alternate-background-color: #0E1015;
    border: none;
    gridline-color: #14161C;
    font-size: 11px;
    color: #9098A6;
    selection-background-color: #162040;
    selection-color: #C0D0F0;
    outline: none;
}
QTableWidget::item {
    padding: 1px 4px;
    border: none;
}
QTableWidget::item:selected {
    background-color: #162040;
    color: #C0D0F0;
}
QHeaderView {
    background-color: #0A0C10;
}
QHeaderView::section {
    background-color: #0E1015;
    color: #4A5260;
    padding: 5px 8px;
    border: none;
    border-right: 1px solid #14161C;
    border-bottom: 1px solid #1E2130;
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 0.5px;
    text-transform: uppercase;
}
QHeaderView::section:hover {
    background-color: #14161C;
    color: #7080A0;
}

/* === Combo Box === */
QComboBox {
    background-color: #0A0C10;
    border: 1px solid #1E2130;
    border-radius: 3px;
    padding: 4px 9px;
    font-size: 12px;
    color: #9098A6;
    min-width: 90px;
}
QComboBox:focus {
    border: 1px solid #2A5298;
}
QComboBox::drop-down {
    border: none;
    width: 18px;
}
QComboBox QAbstractItemView {
    background-color: #13151C;
    border: 1px solid #1E2130;
    selection-background-color: #2A5298;
    color: #9098A6;
    outline: none;
}

/* === Spin Box === */
QSpinBox {
    background-color: #0A0C10;
    border: 1px solid #1E2130;
    border-radius: 3px;
    padding: 4px 7px;
    color: #9098A6;
    font-size: 12px;
}
QSpinBox:focus {
    border: 1px solid #2A5298;
}
QSpinBox::up-button, QSpinBox::down-button {
    background-color: #14161C;
    border: none;
    width: 14px;
}

/* === Check Box === */
QCheckBox {
    font-size: 12px;
    color: #6A7280;
    spacing: 7px;
}
QCheckBox::indicator {
    width: 13px;
    height: 13px;
    border: 1px solid #2A2D38;
    background-color: #0A0C10;
    border-radius: 2px;
}
QCheckBox::indicator:checked {
    background-color: #2A5298;
    border: 1px solid #2A5298;
}

/* === Progress Bar === */
QProgressBar {
    background-color: #0A0C10;
    border: none;
    border-radius: 2px;
    text-align: center;
    color: transparent;
    height: 12px;
}
QProgressBar::chunk {
    background-color: #2A5298;
    border-radius: 2px;
}

/* === Scroll Bar === */
QScrollBar:vertical {
    background: #0E1015;
    width: 6px;
    border: none;
    margin: 0;
}
QScrollBar::handle:vertical {
    background: #2A2D38;
    border-radius: 3px;
    min-height: 20px;
}
QScrollBar::handle:vertical:hover { background: #3A4050; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }

QScrollBar:horizontal {
    background: #0E1015;
    height: 6px;
    border: none;
    margin: 0;
}
QScrollBar::handle:horizontal {
    background: #2A2D38;
    border-radius: 3px;
    min-width: 20px;
}
QScrollBar::handle:horizontal:hover { background: #3A4050; }
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0; }

/* === Labels === */
QLabel {
    color: #6A7280;
    font-size: 12px;
    background: transparent;
}

/* === Frame === */
QFrame[frameShape="4"],
QFrame[frameShape="5"] {
    color: #1E2130;
}

/* === Splitter === */
QSplitter::handle { background-color: #1E2130; }
QSplitter::handle:horizontal { width: 1px; }
QSplitter::handle:vertical   { height: 1px; }

/* === Tool Tip === */
QToolTip {
    background-color: #13151C;
    color: #BEC4CE;
    border: 1px solid #2A2D38;
    font-size: 11px;
    padding: 3px 7px;
}

/* === Group Box === */
QGroupBox {
    border: 1px solid #1E2130;
    border-radius: 4px;
    margin-top: 10px;
    padding-top: 6px;
    color: #4A5260;
}
QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 0 6px;
    left: 8px;
    color: #4A5260;
}
"""
