"""
LogRaptorX - Main Window
Developer: Kennedy Aikohi
GitHub   : https://github.com/kennedy-aikohi
LinkedIn : https://www.linkedin.com/in/aikohikennedy/
"""

import os
from pathlib import Path
from datetime import datetime

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTabWidget, QSplitter, QProgressBar, QLabel,
    QFileDialog, QMessageBox, QPushButton,
    QComboBox, QLineEdit, QFrame
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QAction, QDragEnterEvent, QDropEvent

from ui.dashboard      import DashboardWidget
from ui.results_table  import ResultsTableWidget
from ui.detail_panel   import DetailPanel
from ui.visualization  import VisualizationWidget
from core.workers      import ParseWorker, DetectionWorker, ExportWorker
from core.parser       import ParseResult, LogEntry


class MainWindow(QMainWindow):
    APP_NAME = "LogRaptorX"
    VERSION  = "1.0.0"
    AUTHOR   = "Kennedy Aikohi"

    def __init__(self):
        super().__init__()
        self._result          = None
        self._detections      = []
        self._parse_worker    = None
        self._detect_worker   = None
        self._export_worker   = None
        self._setup_window()
        self._setup_menu()
        self._setup_statusbar()
        self._setup_central()
        self.setAcceptDrops(True)

    # -- Window ---------------------------------------------

    def _setup_window(self):
        self.setWindowTitle(
            f"{self.APP_NAME}  v{self.VERSION}  --  {self.AUTHOR}"
        )
        self.resize(1440, 880)
        self.setMinimumSize(1100, 660)

    # -- Menu -----------------------------------------------

    def _setup_menu(self):
        mb = self.menuBar()

        fm = mb.addMenu("File")
        self._add_action(fm, "Open File(s)...",          "Ctrl+O",       self.open_files)
        self._add_action(fm, "Open Directory...",         "Ctrl+Shift+O", self.open_directory)
        fm.addSeparator()
        self._add_action(fm, "Export All to CSV...",      "Ctrl+E",       self.export_csv)
        self._add_action(fm, "Export Filtered to CSV...", "Ctrl+Shift+E", lambda: self.export_csv(filtered=True))
        fm.addSeparator()
        self._add_action(fm, "Clear Results",             "Ctrl+R",       self.clear_results)
        fm.addSeparator()
        self._add_action(fm, "Exit",                      "Ctrl+Q",       self.close)

        pm = mb.addMenu("Parse")
        self._add_action(pm, "Cancel Active Parse", "Ctrl+.", self.cancel_parse)

        dm = mb.addMenu("Detections")
        self._add_action(dm, "Run Detection Scan", "Ctrl+D", self.run_detections)

        vm = mb.addMenu("View")
        self._add_action(vm, "Dashboard",          "", lambda: self._tabs.setCurrentIndex(0))
        self._add_action(vm, "Results Table",      "", lambda: self._tabs.setCurrentIndex(1))
        self._add_action(vm, "Threat Detections",  "", lambda: self._tabs.setCurrentIndex(2))

        hm = mb.addMenu("Help")
        self._add_action(hm, "About LogRaptorX", "", self.show_about)

    @staticmethod
    def _add_action(menu, label, shortcut, slot):
        a = QAction(label, menu.parent())
        if shortcut:
            a.setShortcut(shortcut)
        a.triggered.connect(slot)
        menu.addAction(a)

    # -- Status bar -----------------------------------------

    def _setup_statusbar(self):
        sb = self.statusBar()
        self._status_lbl = QLabel("Ready")
        self._status_lbl.setStyleSheet("color: #D0D8E8; background: transparent;")
        sb.addWidget(self._status_lbl, 1)

        self._progress = QProgressBar()
        self._progress.setFixedWidth(200)
        self._progress.setFixedHeight(10)
        self._progress.setVisible(False)
        sb.addPermanentWidget(self._progress)

        self._cancel_btn = QPushButton("Cancel")
        self._cancel_btn.setFixedHeight(18)
        self._cancel_btn.setFixedWidth(60)
        self._cancel_btn.setObjectName("dangerBtn")
        self._cancel_btn.setVisible(False)
        self._cancel_btn.clicked.connect(self.cancel_parse)
        sb.addPermanentWidget(self._cancel_btn)

    # -- Central --------------------------------------------

    def _setup_central(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        root.addWidget(self._build_toolbar())

        div = QFrame()
        div.setFrameShape(QFrame.Shape.HLine)
        div.setStyleSheet("color: #1E2130;")
        root.addWidget(div)

        # Splitter: tabs | detail
        self._splitter = QSplitter(Qt.Orientation.Horizontal)
        self._splitter.setHandleWidth(1)

        self._tabs = QTabWidget()
        self._dashboard = DashboardWidget()
        self._results   = ResultsTableWidget()
        self._viz       = VisualizationWidget()

        self._tabs.addTab(self._dashboard, "  Dashboard  ")
        self._tabs.addTab(self._results,   "  Results Table  ")
        self._tabs.addTab(self._viz,       "  Threat Detections  ")

        self._results.row_selected.connect(self._on_entry_selected)

        self._detail = DetailPanel()
        self._detail.setMinimumWidth(300)

        self._splitter.addWidget(self._tabs)
        self._splitter.addWidget(self._detail)
        self._splitter.setStretchFactor(0, 3)
        self._splitter.setStretchFactor(1, 1)
        self._splitter.setSizes([1020, 380])

        root.addWidget(self._splitter, stretch=1)

    def _build_toolbar(self) -> QWidget:
        bar = QWidget()
        bar.setFixedHeight(48)
        bar.setStyleSheet("background-color: #0A0C10; border-bottom: 1px solid #1A1D24;")
        lay = QHBoxLayout(bar)
        lay.setContentsMargins(12, 6, 12, 6)
        lay.setSpacing(8)

        ob = QPushButton("Open Files")
        ob.setObjectName("primaryBtn")
        ob.clicked.connect(self.open_files)
        lay.addWidget(ob)

        db = QPushButton("Open Directory")
        db.clicked.connect(self.open_directory)
        lay.addWidget(db)

        lay.addWidget(self._vsep())

        fl = QLabel("Format")
        fl.setStyleSheet("color: #3A4050; font-size: 11px; background: transparent;")
        lay.addWidget(fl)

        self._fmt_combo = QComboBox()
        self._fmt_combo.addItems([
            "Auto-Detect", "Windows Event Log", "Syslog RFC 3164",
            "Syslog RFC 5424", "IIS / W3C", "Apache / NGINX", "Generic"
        ])
        self._fmt_combo.setFixedWidth(155)
        lay.addWidget(self._fmt_combo)

        lay.addWidget(self._vsep())

        kl = QLabel("Parse Filter")
        kl.setStyleSheet("color: #3A4050; font-size: 11px; background: transparent;")
        lay.addWidget(kl)

        self._kw_input = QLineEdit()
        self._kw_input.setPlaceholderText("keyword filter during parse...")
        self._kw_input.setFixedWidth(180)
        lay.addWidget(self._kw_input)

        lay.addStretch()

        # Detection scan button
        self._scan_btn = QPushButton("Run Detection Scan")
        self._scan_btn.setObjectName("dangerBtn")
        self._scan_btn.clicked.connect(self.run_detections)
        self._scan_btn.setEnabled(False)
        lay.addWidget(self._scan_btn)

        lay.addWidget(self._vsep())

        exp_btn = QPushButton("Export CSV")
        exp_btn.clicked.connect(self.export_csv)
        lay.addWidget(exp_btn)

        expf_btn = QPushButton("Export Filtered")
        expf_btn.clicked.connect(lambda: self.export_csv(filtered=True))
        lay.addWidget(expf_btn)

        return bar

    @staticmethod
    def _vsep():
        f = QFrame()
        f.setFrameShape(QFrame.Shape.VLine)
        f.setFixedHeight(22)
        f.setStyleSheet("color: #1E2130;")
        return f

    # -- Format mapping -------------------------------------

    _FMT_MAP = {
        "Auto-Detect":       "auto",
        "Windows Event Log": "windows_evt",
        "Syslog RFC 3164":   "syslog3164",
        "Syslog RFC 5424":   "syslog5424",
        "IIS / W3C":         "iis_w3c",
        "Apache / NGINX":    "apache",
        "Generic":           "generic",
    }

    def _get_fmt(self):
        return self._FMT_MAP.get(self._fmt_combo.currentText(), "auto")

    def _get_filters(self):
        kw = self._kw_input.text().strip()
        return {"keyword": kw} if kw else {}

    # -- File operations ------------------------------------

    def open_files(self):
        paths, _ = QFileDialog.getOpenFileNames(
            self, "Open Log Files", "",
            "Log Files (*.log *.txt *.evtx *.evt *.gz *.out *.syslog);;All Files (*)"
        )
        if paths:
            self._start_parse(paths)

    def open_directory(self):
        d = QFileDialog.getExistingDirectory(self, "Open Log Directory")
        if not d:
            return
        exts = {".log", ".txt", ".evtx", ".evt", ".out", ".syslog", ".gz"}
        paths = [str(p) for p in Path(d).rglob("*")
                 if p.suffix.lower() in exts and p.is_file()]
        if not paths:
            QMessageBox.information(self, "No Logs Found",
                "No log files found in the selected directory.")
            return
        reply = QMessageBox.question(
            self, "Confirm",
            f"Found {len(paths)} log file(s). Parse all?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self._start_parse(paths)

    def export_csv(self, filtered=False):
        if not self._result or not self._result.entries:
            QMessageBox.information(self, "No Data", "No entries to export.")
            return
        entries = self._results.get_filtered_entries() if filtered else self._result.entries
        if not entries:
            QMessageBox.information(self, "No Data", "No entries match the filter.")
            return
        default = f"LogRaptorX_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        path, _ = QFileDialog.getSaveFileName(
            self, "Export CSV", default, "CSV Files (*.csv);;All Files (*)"
        )
        if not path:
            return
        self._set_busy(True, "Exporting CSV...")
        self._export_worker = ExportWorker(entries, path)
        self._export_worker.progress.connect(lambda p, m: (
            self._progress.setValue(p), self._status_lbl.setText(m)
        ))
        self._export_worker.finished.connect(self._on_export_done)
        self._export_worker.error.connect(self._on_export_error)
        self._export_worker.start()

    def clear_results(self):
        self._result     = None
        self._detections = []
        self._results.clear()
        self._dashboard.reset()
        self._detail.clear()
        self._viz.reset()
        self._scan_btn.setEnabled(False)
        self._set_busy(False)
        self._status_lbl.setText("Results cleared.")
        self.setWindowTitle(
            f"{self.APP_NAME}  v{self.VERSION}  --  {self.AUTHOR}"
        )

    def cancel_parse(self):
        if self._parse_worker and self._parse_worker.isRunning():
            self._parse_worker.cancel()
            self._set_busy(False)
            self._status_lbl.setText("Parse cancelled.")

    # -- Detection scan -------------------------------------

    def run_detections(self):
        if not self._result or not self._result.entries:
            QMessageBox.information(self, "No Data",
                "Parse log files first before running detection scan.")
            return
        self._set_busy(True, "Running detection scan...")
        self._tabs.setCurrentIndex(2)
        self._detect_worker = DetectionWorker(self._result.entries)
        self._detect_worker.progress.connect(lambda p, m: (
            self._progress.setValue(p), self._status_lbl.setText(m)
        ))
        self._detect_worker.finished.connect(self._on_detect_done)
        self._detect_worker.error.connect(lambda e: (
            self._set_busy(False),
            QMessageBox.critical(self, "Detection Error", e)
        ))
        self._detect_worker.start()

    def _on_detect_done(self, detections):
        self._detections = detections
        self._set_busy(False)

        sev = {}
        for d in detections:
            sev[d.severity] = sev.get(d.severity, 0) + 1

        self._viz.update_data(self._result.entries, detections)
        self._dashboard.update_stats(self._result, detections)
        self._results.load_entries(self._result.entries)  # refresh with updated levels

        crit = sev.get("CRITICAL", 0)
        self._status_lbl.setText(
            f"Detection scan complete  --  {len(detections):,} hits  "
            f"({crit} CRITICAL, {sev.get('HIGH', 0)} HIGH, "
            f"{sev.get('MEDIUM', 0)} MEDIUM)"
        )

    # -- Parse workflow -------------------------------------

    def _start_parse(self, paths):
        self.clear_results()
        self._tabs.setCurrentIndex(0)
        self._set_busy(True, f"Parsing {len(paths)} file(s)...")
        self._parse_worker = ParseWorker(paths, self._get_fmt(), self._get_filters())
        self._parse_worker.progress.connect(self._on_progress)
        self._parse_worker.finished.connect(self._on_parse_done)
        self._parse_worker.error.connect(self._on_parse_error)
        self._parse_worker.start()

    def _on_progress(self, pct, msg):
        self._progress.setValue(pct)
        self._status_lbl.setText(msg)

    def _on_parse_done(self, result: ParseResult):
        self._result = result
        self._set_busy(False)
        self._scan_btn.setEnabled(True)
        self._dashboard.update_stats(result, [])
        self._results.load_entries(result.entries)

        fname = Path(result.file_path).name if result.file_path else "Multiple files"
        self._status_lbl.setText(
            f"Done  --  {result.parsed_count:,} entries  |  "
            f"{result.duration_seconds:.2f}s  |  "
            f"{result.parse_rate:,.0f} lines/sec  --  "
            f"Click 'Run Detection Scan' to analyse threats."
        )
        self.setWindowTitle(
            f"{self.APP_NAME}  v{self.VERSION}  --  "
            f"{result.parsed_count:,} entries  --  {fname}"
        )
        QTimer.singleShot(400, lambda: self._tabs.setCurrentIndex(1))

        # Auto-run detection scan
        QTimer.singleShot(800, self.run_detections)

    def _on_parse_error(self, msg):
        self._set_busy(False)
        self._status_lbl.setText(f"Error: {msg}")
        QMessageBox.critical(self, "Parse Error", msg)

    def _on_export_done(self, rows, path):
        self._set_busy(False)
        self._status_lbl.setText(f"Exported {rows:,} rows  --  {path}")
        QMessageBox.information(self, "Export Complete",
            f"Exported {rows:,} entries to:\n{path}")

    def _on_export_error(self, msg):
        self._set_busy(False)
        self._status_lbl.setText(f"Export failed: {msg}")
        QMessageBox.critical(self, "Export Error", msg)

    # -- UI helpers -----------------------------------------

    def _set_busy(self, busy, msg=""):
        self._progress.setVisible(busy)
        self._cancel_btn.setVisible(busy)
        if busy:
            self._progress.setValue(0)
        if msg:
            self._status_lbl.setText(msg)

    def _on_entry_selected(self, entry: LogEntry):
        self._detail.show_entry(entry)

    # -- Drag & drop ----------------------------------------

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent):
        paths = [u.toLocalFile() for u in event.mimeData().urls() if u.isLocalFile()]
        files = []
        for p in paths:
            if os.path.isdir(p):
                exts = {".log", ".txt", ".evtx", ".evt", ".out", ".syslog", ".gz"}
                files.extend(str(f) for f in Path(p).rglob("*")
                              if f.suffix.lower() in exts)
            else:
                files.append(p)
        if files:
            self._start_parse(files)

    # -- About ----------------------------------------------

    def show_about(self):
        QMessageBox.about(self, f"About {self.APP_NAME}", f"""
<div style="font-family: Segoe UI, Arial, sans-serif;">
  <h2 style="margin-bottom:4px;">LogRaptorX  v{self.VERSION}</h2>
  <p style="color:#666; margin-top:0;">Windows Log Intelligence Platform</p>
  <hr>
  <table cellspacing="4">
    <tr><td style="color:#888; padding-right:16px;">Author</td>
        <td><b>Kennedy Aikohi</b></td></tr>
    <tr><td style="color:#888;">GitHub</td>
        <td>github.com/kennedy-aikohi</td></tr>
    <tr><td style="color:#888;">LinkedIn</td>
        <td>linkedin.com/in/aikohikennedy</td></tr>
    <tr><td style="color:#888;">Version</td>
        <td>{self.VERSION}</td></tr>
  </table>
  <hr>
  <p style="color:#888; font-size:10pt;">
    Multi-threaded EVTX + text log parser.<br>
    Detection engine: 15 MITRE ATT&CK-mapped rules.<br>
    Supports: EVTX, Syslog, IIS, Apache, PowerShell, Generic.<br>
    Output: UTF-8 CSV, compatible with Excel and SIEM tools.
  </p>
</div>""")
