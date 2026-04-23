"""
LogRaptorX - Dashboard with Pyramid Watermark
Developer: Kennedy Aikohi
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QFrame, QStackedLayout
)
from PyQt6.QtCore import Qt
from core.parser import ParseResult
from core.detections import Detection
from ui.theme import PyramidBackground
from typing import Dict, List


class StatCard(QFrame):
    def __init__(self, title: str, value: str = "--", accent: str = "#2A5298"):
        super().__init__()
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setMinimumWidth(110)
        self._accent = accent
        self.setStyleSheet(f"""
            StatCard {{
                background-color: #0A0C10;
                border: 1px solid #1E2130;
                border-top: 2px solid {accent};
                border-radius: 4px;
            }}
        """)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(3)

        self._val = QLabel(value)
        self._val.setStyleSheet(
            f"color: #E0E4EC; font-size: 20px; font-weight: 600; background: transparent;"
        )
        self._val.setAlignment(Qt.AlignmentFlag.AlignLeft)

        self._lbl = QLabel(title.upper())
        self._lbl.setStyleSheet(
            "color: #3A4050; font-size: 9px; letter-spacing: 1px; background: transparent;"
        )
        self._lbl.setAlignment(Qt.AlignmentFlag.AlignLeft)

        layout.addWidget(self._val)
        layout.addWidget(self._lbl)

    def set_value(self, v: str):
        self._val.setText(v)

    def set_alert(self, on: bool):
        color = "#C0392B" if on else self._accent
        self.setStyleSheet(f"""
            StatCard {{
                background-color: #0A0C10;
                border: 1px solid #1E2130;
                border-top: 2px solid {color};
                border-radius: 4px;
            }}
        """)
        if on:
            self._val.setStyleSheet(
                "color: #E05050; font-size: 20px; font-weight: 600; background: transparent;"
            )


class DashboardWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        # Stack: pyramid behind, content on top
        stack = QStackedLayout(self)
        stack.setStackingMode(QStackedLayout.StackingMode.StackAll)

        self._pyramid = PyramidBackground()
        stack.addWidget(self._pyramid)

        content = QWidget()
        content.setStyleSheet("background: transparent;")
        stack.addWidget(content)
        stack.setCurrentWidget(content)

        layout = QVBoxLayout(content)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(18)

        # --- Title + Author ---
        title_row = QHBoxLayout()

        left_col = QVBoxLayout()
        left_col.setSpacing(3)
        app_lbl = QLabel("LogRaptorX")
        app_lbl.setStyleSheet(
            "color: #E0E4EC; font-size: 22px; font-weight: 700; background: transparent;"
        )
        sub_lbl = QLabel("Windows Log Intelligence Platform  v1.0.0")
        sub_lbl.setStyleSheet(
            "color: #2A3040; font-size: 11px; background: transparent;"
        )
        left_col.addWidget(app_lbl)
        left_col.addWidget(sub_lbl)
        title_row.addLayout(left_col)
        title_row.addStretch()

        # Author block
        author_col = QVBoxLayout()
        author_col.setSpacing(2)
        author_col.setAlignment(Qt.AlignmentFlag.AlignRight)

        def ml(text, bright=False):
            lbl = QLabel(text)
            color = "#CDD3DE" if bright else "#3A4050"
            lbl.setStyleSheet(
                f"color: {color}; font-size: 11px; background: transparent;"
            )
            lbl.setAlignment(Qt.AlignmentFlag.AlignRight)
            return lbl

        author_col.addWidget(ml("Author", False))
        author_col.addWidget(ml("Kennedy Aikohi", True))
        author_col.addWidget(ml("github.com/kennedy-aikohi", False))
        author_col.addWidget(ml("linkedin.com/in/aikohikennedy", False))
        title_row.addLayout(author_col)
        layout.addLayout(title_row)

        div = QFrame()
        div.setFrameShape(QFrame.Shape.HLine)
        div.setStyleSheet("color: #1E2130;")
        layout.addWidget(div)

        # --- Stat cards row 1: parse stats ---
        row1 = QHBoxLayout()
        row1.setSpacing(10)
        self._cards: Dict[str, StatCard] = {}
        parse_stats = [
            ("total",    "Total Lines",  "#2A5298"),
            ("parsed",   "Parsed",       "#2A5298"),
            ("errors",   "Errors",       "#C0392B"),
            ("warnings", "Warnings",     "#E67E22"),
            ("critical", "Critical",     "#C0392B"),
            ("duration", "Parse Time",   "#2A5298"),
            ("rate",     "Lines / sec",  "#27AE60"),
        ]
        for key, label, color in parse_stats:
            card = StatCard(label, "--", color)
            self._cards[key] = card
            row1.addWidget(card)
        layout.addLayout(row1)

        # --- Stat cards row 2: detection stats ---
        row2 = QHBoxLayout()
        row2.setSpacing(10)
        det_stats = [
            ("det_total",    "Total Detections", "#E67E22"),
            ("det_critical", "Critical Hits",    "#C0392B"),
            ("det_high",     "High Hits",        "#E67E22"),
            ("det_medium",   "Medium Hits",      "#F1C40F"),
            ("det_rules",    "Rules Triggered",  "#2A5298"),
            ("sec_entries",  "Flagged Entries",  "#C0392B"),
        ]
        for key, label, color in det_stats:
            card = StatCard(label, "--", color)
            self._cards[key] = card
            row2.addWidget(card)
        row2.addStretch()
        layout.addLayout(row2)

        # --- Level distribution ---
        level_frame = QFrame()
        level_frame.setStyleSheet(
            "QFrame { background-color: #0A0C10; border: 1px solid #1E2130; border-radius: 4px; }"
        )
        lf_layout = QVBoxLayout(level_frame)
        lf_layout.setContentsMargins(14, 10, 14, 10)
        lf_layout.setSpacing(5)
        lev_hdr = QLabel("LEVEL DISTRIBUTION")
        lev_hdr.setStyleSheet(
            "color: #2A3040; font-size: 9px; letter-spacing: 1px; background: transparent;"
        )
        lf_layout.addWidget(lev_hdr)
        self._level_text = QLabel("No data.")
        self._level_text.setStyleSheet(
            "color: #3A4050; font-size: 11px; background: transparent;"
        )
        lf_layout.addWidget(self._level_text)
        layout.addWidget(level_frame)

        # --- Alert banner (hidden until critical detection) ---
        self._alert_banner = QLabel("")
        self._alert_banner.setVisible(False)
        self._alert_banner.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._alert_banner.setStyleSheet("""
            QLabel {
                background-color: #2A0808;
                color: #FF6060;
                border: 1px solid #8A2020;
                border-radius: 4px;
                padding: 8px 16px;
                font-size: 12px;
                font-weight: 600;
            }
        """)
        layout.addWidget(self._alert_banner)

        self._info_label = QLabel(
            "Open log files via File > Open, or drag and drop onto this window.\n"
            "Supports: Windows Event Log (.evtx), Syslog, IIS/W3C, Apache/NGINX, "
            "PowerShell ScriptBlock, and generic timestamped logs.\n"
            "Detection engine: 15 rules covering MITRE ATT&CK techniques."
        )
        self._info_label.setStyleSheet(
            "color: #1E2430; font-size: 11px; background: transparent;"
        )
        self._info_label.setWordWrap(True)
        layout.addWidget(self._info_label)

        layout.addStretch()

        # Footer
        div2 = QFrame()
        div2.setFrameShape(QFrame.Shape.HLine)
        div2.setStyleSheet("color: #14161C;")
        layout.addWidget(div2)

        footer = QLabel(
            "Kennedy Aikohi  |  github.com/kennedy-aikohi  |  "
            "linkedin.com/in/aikohikennedy  |  LogRaptorX v1.0.0"
        )
        footer.setStyleSheet("color: #1A2030; font-size: 10px; background: transparent;")
        footer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(footer)

    # resize pyramid to always fill
    def resizeEvent(self, event):
        self._pyramid.setGeometry(0, 0, self.width(), self.height())
        super().resizeEvent(event)

    def update_stats(self, result: ParseResult, detections: List[Detection] = None):
        detections = detections or []
        entries = result.entries

        level_counts: Dict[str, int] = {}
        for e in entries:
            level_counts[e.level] = level_counts.get(e.level, 0) + 1

        errors   = sum(v for k, v in level_counts.items() if "ERROR" in k or "CRITICAL" in k)
        warnings = level_counts.get("WARN", 0) + level_counts.get("WARNING", 0)
        critical = level_counts.get("CRITICAL", 0)

        self._cards["total"].set_value(f"{result.total_lines:,}")
        self._cards["parsed"].set_value(f"{result.parsed_count:,}")
        self._cards["errors"].set_value(f"{errors:,}")
        self._cards["warnings"].set_value(f"{warnings:,}")
        self._cards["critical"].set_value(f"{critical:,}")
        self._cards["duration"].set_value(f"{result.duration_seconds:.2f}s")
        self._cards["rate"].set_value(f"{result.parse_rate:,.0f}")

        # Detection stats
        sev: Dict[str, int] = {}
        for d in detections:
            sev[d.severity] = sev.get(d.severity, 0) + 1
        rules_hit = len({d.rule_id for d in detections})
        flagged   = len({id(d.entry) for d in detections if d.entry})

        self._cards["det_total"].set_value(f"{len(detections):,}")
        self._cards["det_critical"].set_value(f"{sev.get('CRITICAL', 0):,}")
        self._cards["det_high"].set_value(f"{sev.get('HIGH', 0):,}")
        self._cards["det_medium"].set_value(f"{sev.get('MEDIUM', 0):,}")
        self._cards["det_rules"].set_value(f"{rules_hit}")
        self._cards["sec_entries"].set_value(f"{flagged:,}")

        if sev.get("CRITICAL", 0) > 0:
            self._cards["det_critical"].set_alert(True)
            self._cards["sec_entries"].set_alert(True)
            self._alert_banner.setText(
                f"[!]  CRITICAL DETECTIONS FOUND  --  "
                f"{sev.get('CRITICAL', 0)} critical threat(s) detected across {flagged} log entries.  "
                f"Review the Detections tab immediately."
            )
            self._alert_banner.setVisible(True)
        else:
            self._alert_banner.setVisible(False)

        parts = [f"{k}: {v:,}" for k, v in sorted(level_counts.items(), key=lambda x: -x[1])]
        self._level_text.setText("  |  ".join(parts) if parts else "No entries.")

        from pathlib import Path
        fname = Path(result.file_path).name if result.file_path else "multiple files"
        self._info_label.setText(
            f"Parsed {result.parsed_count:,} entries from {fname}  --  "
            f"{result.skipped_count:,} lines skipped  --  "
            f"{len(detections):,} detection hits across {rules_hit} rule(s)."
        )

    def reset(self):
        for card in self._cards.values():
            card.set_value("--")
        self._level_text.setText("No data.")
        self._alert_banner.setVisible(False)
        self._info_label.setText(
            "Open log files via File > Open, or drag and drop onto this window."
        )
