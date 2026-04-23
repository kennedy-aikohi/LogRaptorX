"""
LogRaptorX - Visualization & Threat Detection Tab
Production-grade native PyQt6 charts. No truncation, no overlap.
Developer: Kennedy Aikohi
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QScrollArea, QFrame, QGridLayout, QSizePolicy,
    QStackedLayout
)
from PyQt6.QtCore import Qt, QRectF, QRect
from PyQt6.QtGui import (
    QPainter, QColor, QPen, QBrush, QFont,
    QLinearGradient, QPainterPath, QFontMetrics
)
from typing import List, Dict
from core.detections import Detection
from ui.theme import PyramidBackground


SEVERITY_COLORS = {
    "CRITICAL": "#C0392B",
    "HIGH":     "#E67E22",
    "MEDIUM":   "#D4AC0D",
    "LOW":      "#27AE60",
}

LEVEL_COLORS = {
    "CRITICAL":   "#C0392B",
    "ERROR":      "#E74C3C",
    "WARN":       "#E67E22",
    "WARNING":    "#E67E22",
    "AUDIT-FAIL": "#C0392B",
    "AUDIT-OK":   "#27AE60",
    "INFO":       "#2A6FAD",
    "DEBUG":      "#4A5568",
}


# -------------------------------------------------------
#  Horizontal Bar Chart  --  fixed label truncation
# -------------------------------------------------------

class HBarChart(QWidget):
    """
    Horizontal bar chart with auto-sized left label column.
    Labels are never clipped -- margin is computed from actual text width.
    """

    def __init__(self, title: str, parent=None):
        super().__init__(parent)
        self._title  = title
        self._data: Dict[str, int] = {}
        self._colors: Dict[str, str] = {}
        self.setMinimumHeight(40)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setStyleSheet("background: transparent;")

    def set_data(self, data: Dict[str, int], colors: Dict[str, str]):
        self._data   = dict(sorted(data.items(), key=lambda x: -x[1]))
        self._colors = colors
        n = len(data)
        self.setMinimumHeight(max(60, n * 34 + 36))
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        W, H = self.width(), self.height()

        if not self._data:
            painter.setPen(QColor("#3A4050"))
            painter.setFont(QFont("Segoe UI", 10))
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "No data")
            painter.end()
            return

        # --- Measure widest label ---
        lbl_font = QFont("Segoe UI", 10)
        fm = QFontMetrics(lbl_font)
        max_lbl_w = max(fm.horizontalAdvance(k) for k in self._data) + 16
        max_lbl_w = max(max_lbl_w, 80)

        val_font = QFont("Segoe UI", 9)
        fmv = QFontMetrics(val_font)
        max_val_w = max(fmv.horizontalAdvance(f"{v:,}") for v in self._data.values()) + 12

        PAD_TOP    = 28
        PAD_BOTTOM = 8
        PAD_RIGHT  = max_val_w + 8

        bar_x = max_lbl_w + 8
        bar_w = W - bar_x - PAD_RIGHT

        # Title
        painter.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        painter.setPen(QColor("#4A5260"))
        painter.drawText(0, 18, self._title.upper())

        items  = list(self._data.items())
        n      = len(items)
        row_h  = max(26, (H - PAD_TOP - PAD_BOTTOM) // n)
        max_v  = max(v for _, v in items) or 1

        for i, (label, value) in enumerate(items):
            y    = PAD_TOP + i * row_h
            bw   = int((value / max_v) * bar_w)
            cy_r = y + row_h // 2

            # Label -- right-aligned, full width, no clip
            painter.setFont(lbl_font)
            painter.setPen(QColor("#8090A8"))
            painter.drawText(
                QRect(0, y, max_lbl_w, row_h),
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
                label
            )

            # Track
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(QColor("#141820")))
            painter.drawRoundedRect(bar_x, y + 4, bar_w, row_h - 10, 3, 3)

            # Bar
            if bw > 2:
                color = QColor(self._colors.get(label, "#2A6FAD"))
                grad  = QLinearGradient(bar_x, 0, bar_x + bw, 0)
                grad.setColorAt(0.0, color)
                c2 = QColor(color); c2.setAlpha(180)
                grad.setColorAt(1.0, c2)
                painter.setBrush(QBrush(grad))
                painter.drawRoundedRect(bar_x, y + 4, bw, row_h - 10, 3, 3)

            # Count value
            painter.setFont(val_font)
            painter.setPen(QColor("#C0C8D8"))
            painter.drawText(
                QRect(bar_x + bw + 6, y, max_val_w, row_h),
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                f"{value:,}"
            )

        painter.end()


# -------------------------------------------------------
#  Donut Chart  --  legend rendered beside, not below
# -------------------------------------------------------

class DonutChart(QWidget):
    def __init__(self, title: str, parent=None):
        super().__init__(parent)
        self._title = title
        self._data: Dict[str, int] = {}
        self.setMinimumSize(260, 260)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding)
        self.setStyleSheet("background: transparent;")

    def set_data(self, data: Dict[str, int]):
        self._data = data
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        W, H = self.width(), self.height()

        # Title
        painter.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        painter.setPen(QColor("#4A5260"))
        painter.drawText(0, 18, self._title.upper())

        total = sum(self._data.values()) if self._data else 0

        if not total:
            painter.setPen(QColor("#3A4050"))
            painter.setFont(QFont("Segoe UI", 10))
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "No detections")
            painter.end()
            return

        # Reserve right 90px for legend
        legend_w = 110
        donut_w  = W - legend_w
        cx = donut_w // 2
        cy = H // 2 + 10
        r_out = min(donut_w, H - 40) // 2 - 10
        r_in  = int(r_out * 0.54)

        # Draw segments
        angle = 90.0
        painter.setPen(Qt.PenStyle.NoPen)
        for label, val in self._data.items():
            span  = (val / total) * 360.0
            color = QColor(SEVERITY_COLORS.get(label, "#2A6FAD"))
            path  = QPainterPath()
            path.moveTo(cx, cy)
            outer = QRectF(cx - r_out, cy - r_out, r_out * 2, r_out * 2)
            path.arcTo(outer, angle, span)
            path.closeSubpath()
            painter.setBrush(QBrush(color))
            painter.drawPath(path)

            # Thin separator
            sep = QPen(QColor("#0E1015"), 1.5)
            painter.setPen(sep)
            painter.drawPath(path)
            painter.setPen(Qt.PenStyle.NoPen)
            angle += span

        # Hole
        painter.setBrush(QBrush(QColor("#0E1015")))
        painter.drawEllipse(QRectF(cx - r_in, cy - r_in, r_in * 2, r_in * 2))

        # Center label
        painter.setPen(QColor("#E0E4EC"))
        painter.setFont(QFont("Segoe UI", int(r_in * 0.45), QFont.Weight.Bold))
        painter.drawText(
            QRect(int(cx - r_in), int(cy - r_in), r_in * 2, r_in * 2),
            Qt.AlignmentFlag.AlignCenter, str(total)
        )
        painter.setPen(QColor("#4A5260"))
        painter.setFont(QFont("Segoe UI", 8))
        painter.drawText(
            QRect(int(cx - r_in), int(cy + 4), r_in * 2, 20),
            Qt.AlignmentFlag.AlignCenter, "total"
        )

        # Legend -- right side, vertically centred
        lx   = donut_w + 8
        ly   = cy - (len(self._data) * 22) // 2
        painter.setFont(QFont("Segoe UI", 10))
        for label, val in self._data.items():
            color = QColor(SEVERITY_COLORS.get(label, "#2A6FAD"))
            painter.setBrush(QBrush(color))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRoundedRect(lx, ly + 4, 10, 10, 2, 2)
            painter.setPen(QColor("#9098A6"))
            painter.drawText(lx + 16, ly, legend_w - 18, 22,
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                f"{label}")
            painter.setPen(QColor("#CDD3DE"))
            painter.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
            painter.drawText(lx + 16, ly + 14, legend_w - 18, 14,
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                f"{val:,}")
            painter.setFont(QFont("Segoe UI", 10))
            ly += 26

        painter.end()


# -------------------------------------------------------
#  MITRE Tags
# -------------------------------------------------------

class MitreTagWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("background: transparent;")

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._scroll.setStyleSheet("background: transparent; border: none;")
        self._scroll.setFixedHeight(76)

        self._inner = QWidget()
        self._inner.setStyleSheet("background: transparent;")
        self._grid = QGridLayout(self._inner)
        self._grid.setContentsMargins(0, 2, 0, 2)
        self._grid.setSpacing(5)
        self._scroll.setWidget(self._inner)
        outer.addWidget(self._scroll)

    def set_data(self, detections: List[Detection]):
        while self._grid.count():
            item = self._grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        counts: Dict[str, int] = {}
        rule_sev: Dict[str, str] = {}
        for d in detections:
            counts[d.mitre_id] = counts.get(d.mitre_id, 0) + 1
            # Escalate to worst severity seen
            prev = rule_sev.get(d.mitre_id, "LOW")
            order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
            if order.get(d.severity, 3) < order.get(prev, 3):
                rule_sev[d.mitre_id] = d.severity

        row, col = 0, 0
        for tid, count in sorted(counts.items(), key=lambda x: -x[1])[:40]:
            sev   = rule_sev.get(tid, "LOW")
            color = SEVERITY_COLORS.get(sev, "#2A5298")
            badge = QLabel(f"{tid}   x{count}")
            badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
            badge.setToolTip(f"MITRE {tid} -- {count} detection(s)  [{sev}]")
            badge.setStyleSheet(f"""
                QLabel {{
                    background-color: #0E1420;
                    color: {color};
                    border: 1px solid {color}55;
                    border-radius: 3px;
                    padding: 3px 10px;
                    font-size: 10px;
                    font-family: Consolas;
                    font-weight: 600;
                }}
            """)
            self._grid.addWidget(badge, row, col)
            col += 1
            if col >= 6:
                col = 0
                row += 1


# -------------------------------------------------------
#  Detection Hits List
# -------------------------------------------------------

class DetectionListWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("background: transparent;")
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        # Column headers
        hdr = QWidget()
        hdr.setFixedHeight(26)
        hdr.setStyleSheet("background-color: #0A0C12; border-bottom: 1px solid #1E2130;")
        hl = QHBoxLayout(hdr)
        hl.setContentsMargins(10, 0, 10, 0)
        hl.setSpacing(0)
        for txt, w in [("SEVERITY", 80), ("RULE", 220), ("MITRE", 90),
                       ("CATEGORY", 150), ("MATCHED VALUE", 0)]:
            lbl = QLabel(txt)
            lbl.setStyleSheet(
                "color: #3A4050; font-size: 9px; font-weight: 700; "
                "letter-spacing: 1px; background: transparent;"
            )
            if w:
                lbl.setFixedWidth(w)
            else:
                lbl.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
            hl.addWidget(lbl)
        lay.addWidget(hdr)

        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setStyleSheet(
            "QScrollArea { border: none; background: transparent; }"
            "QScrollBar:vertical { width: 6px; background: #0E1015; }"
            "QScrollBar::handle:vertical { background: #2A2D38; border-radius: 3px; }"
        )
        self._inner = QWidget()
        self._inner.setStyleSheet("background: transparent;")
        self._vbox  = QVBoxLayout(self._inner)
        self._vbox.setContentsMargins(0, 2, 0, 2)
        self._vbox.setSpacing(2)
        self._vbox.addStretch()
        self._scroll.setWidget(self._inner)
        lay.addWidget(self._scroll)

    def set_data(self, detections: List[Detection]):
        while self._vbox.count() > 1:
            item = self._vbox.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        seen  = set()
        shown = 0
        for d in sorted(detections, key=lambda x: x.severity_order):
            key = (d.rule_id, d.matched_value[:50])
            if key in seen:
                continue
            seen.add(key)

            sc = SEVERITY_COLORS.get(d.severity, "#2A5298")

            row_w = QFrame()
            row_w.setFixedHeight(34)
            row_w.setStyleSheet(f"""
                QFrame {{
                    background-color: #0A0C12;
                    border-left: 3px solid {sc};
                    border-bottom: 1px solid #14161C;
                }}
                QFrame:hover {{ background-color: #10141E; }}
            """)
            rl = QHBoxLayout(row_w)
            rl.setContentsMargins(10, 0, 10, 0)
            rl.setSpacing(0)

            sev_lbl = QLabel(d.severity)
            sev_lbl.setFixedWidth(80)
            sev_lbl.setStyleSheet(f"""
                QLabel {{
                    color: {sc};
                    font-size: 9px;
                    font-weight: 700;
                    font-family: Consolas;
                    background: transparent;
                }}
            """)
            rl.addWidget(sev_lbl)

            name_lbl = QLabel(d.rule_name)
            name_lbl.setFixedWidth(220)
            name_lbl.setStyleSheet(
                "color: #CDD3DE; font-size: 11px; font-weight: 600; background: transparent;"
            )
            rl.addWidget(name_lbl)

            mitre_lbl = QLabel(d.mitre_id)
            mitre_lbl.setFixedWidth(90)
            mitre_lbl.setStyleSheet(
                "color: #2A5298; font-size: 10px; font-family: Consolas; background: transparent;"
            )
            rl.addWidget(mitre_lbl)

            cat_lbl = QLabel(d.category)
            cat_lbl.setFixedWidth(150)
            cat_lbl.setStyleSheet(
                "color: #5A6270; font-size: 10px; background: transparent;"
            )
            rl.addWidget(cat_lbl)

            match_lbl = QLabel(d.matched_value[:120])
            match_lbl.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
            match_lbl.setStyleSheet(
                "color: #3A4050; font-size: 10px; font-family: Consolas; background: transparent;"
            )
            match_lbl.setToolTip(d.matched_value)
            rl.addWidget(match_lbl)

            self._vbox.insertWidget(self._vbox.count() - 1, row_w)
            shown += 1
            if shown >= 300:
                break


# -------------------------------------------------------
#  Main Visualization Widget
# -------------------------------------------------------

class VisualizationWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        # Stack pyramid behind content
        stack = QStackedLayout(self)
        stack.setStackingMode(QStackedLayout.StackingMode.StackAll)

        self._pyramid = PyramidBackground()
        stack.addWidget(self._pyramid)

        content = QWidget()
        content.setStyleSheet("background: transparent;")
        stack.addWidget(content)
        stack.setCurrentWidget(content)

        # Scrollable main area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("background: transparent; border: none;")

        inner = QWidget()
        inner.setStyleSheet("background: transparent;")
        lay = QVBoxLayout(inner)
        lay.setContentsMargins(20, 16, 20, 16)
        lay.setSpacing(16)

        # Header
        hdr_row = QHBoxLayout()
        hdr = QLabel("THREAT INTELLIGENCE DASHBOARD")
        hdr.setStyleSheet(
            "color: #4A5260; font-size: 10px; letter-spacing: 2px; background: transparent;"
        )
        hdr_row.addWidget(hdr)
        hdr_row.addStretch()
        lay.addLayout(hdr_row)

        # Row 1: Level bar chart + Severity donut side by side
        row1 = QHBoxLayout()
        row1.setSpacing(16)

        # Level distribution in a card
        lvl_card = self._card()
        lvl_inner = QVBoxLayout(lvl_card)
        lvl_inner.setContentsMargins(14, 12, 14, 12)
        lv_lbl = QLabel("LEVEL DISTRIBUTION")
        lv_lbl.setStyleSheet(
            "color: #3A4050; font-size: 9px; letter-spacing: 1px; background: transparent;"
        )
        lvl_inner.addWidget(lv_lbl)
        self._level_chart = HBarChart("", lvl_card)
        lvl_inner.addWidget(self._level_chart)
        row1.addWidget(lvl_card, stretch=3)

        # Donut in a card
        don_card = self._card()
        don_card.setFixedWidth(300)
        don_inner = QVBoxLayout(don_card)
        don_inner.setContentsMargins(14, 12, 14, 12)
        don_lbl = QLabel("DETECTION SEVERITY")
        don_lbl.setStyleSheet(
            "color: #3A4050; font-size: 9px; letter-spacing: 1px; background: transparent;"
        )
        don_inner.addWidget(don_lbl)
        self._severity_chart = DonutChart("", don_card)
        don_inner.addWidget(self._severity_chart)
        row1.addWidget(don_card, stretch=1)

        lay.addLayout(row1)

        # Row 2: Detections by rule
        rule_card = self._card()
        rule_inner = QVBoxLayout(rule_card)
        rule_inner.setContentsMargins(14, 12, 14, 12)
        rule_lbl = QLabel("DETECTIONS BY RULE")
        rule_lbl.setStyleSheet(
            "color: #3A4050; font-size: 9px; letter-spacing: 1px; background: transparent;"
        )
        rule_inner.addWidget(rule_lbl)
        self._rule_chart = HBarChart("", rule_card)
        self._rule_chart.setMinimumHeight(180)
        rule_inner.addWidget(self._rule_chart)
        lay.addWidget(rule_card)

        # Row 3: MITRE tags
        mitre_card = self._card()
        mitre_inner = QVBoxLayout(mitre_card)
        mitre_inner.setContentsMargins(14, 10, 14, 10)
        mitre_lbl = QLabel("MITRE ATT&CK TECHNIQUE TAGS")
        mitre_lbl.setStyleSheet(
            "color: #3A4050; font-size: 9px; letter-spacing: 1px; background: transparent;"
        )
        mitre_inner.addWidget(mitre_lbl)
        self._mitre_tags = MitreTagWidget()
        mitre_inner.addWidget(self._mitre_tags)
        lay.addWidget(mitre_card)

        # Row 4: Detection hits list
        det_card = self._card()
        det_inner = QVBoxLayout(det_card)
        det_inner.setContentsMargins(0, 0, 0, 0)
        det_hdr = QWidget()
        det_hdr.setFixedHeight(32)
        det_hdr.setStyleSheet("background: transparent;")
        det_hdr_l = QHBoxLayout(det_hdr)
        det_hdr_l.setContentsMargins(14, 0, 14, 0)
        det_title = QLabel("DETECTION HITS  (sorted by severity)")
        det_title.setStyleSheet(
            "color: #3A4050; font-size: 9px; letter-spacing: 1px; background: transparent;"
        )
        det_hdr_l.addWidget(det_title)
        det_inner.addWidget(det_hdr)
        self._detection_list = DetectionListWidget()
        self._detection_list.setMinimumHeight(300)
        det_inner.addWidget(self._detection_list)
        lay.addWidget(det_card, stretch=1)

        scroll.setWidget(inner)
        content_lay = QVBoxLayout(content)
        content_lay.setContentsMargins(0, 0, 0, 0)
        content_lay.addWidget(scroll)

    def resizeEvent(self, event):
        self._pyramid.setGeometry(0, 0, self.width(), self.height())
        super().resizeEvent(event)

    @staticmethod
    def _card() -> QFrame:
        f = QFrame()
        f.setStyleSheet("""
            QFrame {
                background-color: #0A0C12;
                border: 1px solid #1A1D28;
                border-radius: 6px;
            }
        """)
        return f

    def update_data(self, entries, detections: List[Detection]):
        level_counts: Dict[str, int] = {}
        for e in entries:
            level_counts[e.level] = level_counts.get(e.level, 0) + 1
        self._level_chart.set_data(level_counts, LEVEL_COLORS)

        sev_counts: Dict[str, int] = {}
        for d in detections:
            sev_counts[d.severity] = sev_counts.get(d.severity, 0) + 1
        self._severity_chart.set_data(sev_counts)

        rule_counts: Dict[str, int] = {}
        rule_colors: Dict[str, str] = {}
        for d in detections:
            rule_counts[d.rule_name] = rule_counts.get(d.rule_name, 0) + 1
            cur = rule_colors.get(d.rule_name, "LOW")
            order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
            if order.get(d.severity, 3) <= order.get(cur, 3):
                rule_colors[d.rule_name] = SEVERITY_COLORS.get(d.severity, "#2A6FAD")
        self._rule_chart.set_data(rule_counts, rule_colors)

        self._mitre_tags.set_data(detections)
        self._detection_list.set_data(detections)

    def reset(self):
        self._level_chart.set_data({}, {})
        self._severity_chart.set_data({})
        self._rule_chart.set_data({}, {})
        self._mitre_tags.set_data([])
        self._detection_list.set_data([])
