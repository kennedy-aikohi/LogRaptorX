"""
LogRaptorX - Results Table (Paginated)
Professional, clean. 500 rows per page -- UI never freezes.
Developer: Kennedy Aikohi
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget,
    QTableWidgetItem, QHeaderView, QLabel, QLineEdit,
    QPushButton, QComboBox, QSpinBox, QFrame
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QColor, QBrush, QFont
from core.parser import LogEntry
from typing import List

PAGE_SIZE = 500

# Subtle, professional level coloring -- text color only, no loud backgrounds
LEVEL_FG = {
    'INFO':       '#8BAAC8',
    'DEBUG':      '#6A8F6A',
    'WARN':       '#C8A84A',
    'WARNING':    '#C8A84A',
    'ERROR':      '#C86060',
    'CRITICAL':   '#E05050',
    'AUDIT-OK':   '#4A9A6A',
    'AUDIT-FAIL': '#C06040',
    'NOTICE':     '#7090C0',
}
DEFAULT_FG = '#9098A6'
ROW_BG_ODD  = '#14161A'
ROW_BG_EVEN = '#18191F'


class ResultsTableWidget(QWidget):
    row_selected = pyqtSignal(object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._entries: List[LogEntry] = []
        self._filtered: List[LogEntry] = []
        self._current_page = 0
        self._debounce = QTimer()
        self._debounce.setSingleShot(True)
        self._debounce.setInterval(280)
        self._debounce.timeout.connect(self._run_filter)
        self._setup_ui()

    # -- Setup --------------------------------------------------

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Filter bar
        filter_wrap = QWidget()
        filter_wrap.setStyleSheet("background-color: #1C1E24; border-bottom: 1px solid #2A2D35;")
        filter_wrap.setFixedHeight(44)
        fbar = QHBoxLayout(filter_wrap)
        fbar.setContentsMargins(12, 6, 12, 6)
        fbar.setSpacing(10)

        self._search_box = QLineEdit()
        self._search_box.setPlaceholderText("Filter entries by keyword...")
        self._search_box.textChanged.connect(self._debounce.start)
        fbar.addWidget(self._search_box, stretch=4)

        sep1 = self._vsep()
        fbar.addWidget(sep1)

        level_lbl = QLabel("Level")
        level_lbl.setStyleSheet("color: #5A6270; font-size: 11px; background: transparent;")
        fbar.addWidget(level_lbl)

        self._level_combo = QComboBox()
        self._level_combo.addItems(["All", "INFO", "DEBUG", "WARN", "ERROR", "CRITICAL", "AUDIT-OK", "AUDIT-FAIL"])
        self._level_combo.setFixedWidth(110)
        self._level_combo.currentTextChanged.connect(self._debounce.start)
        fbar.addWidget(self._level_combo)

        sep2 = self._vsep()
        fbar.addWidget(sep2)

        self._sec_btn = QPushButton("Security Only")
        self._sec_btn.setObjectName("dangerBtn")
        self._sec_btn.setCheckable(True)
        self._sec_btn.setFixedWidth(110)
        self._sec_btn.clicked.connect(self._debounce.start)
        fbar.addWidget(self._sec_btn)

        fbar.addStretch()

        self._count_label = QLabel("0 entries")
        self._count_label.setStyleSheet("color: #5A6270; font-size: 11px; background: transparent;")
        fbar.addWidget(self._count_label)

        layout.addWidget(filter_wrap)

        # Table
        self._table = QTableWidget()
        self._table.setColumnCount(7)
        self._table.setHorizontalHeaderLabels(
            ["Line", "Timestamp", "Level", "Source", "Event ID", "Message", "Sec"]
        )
        self._table.setAlternatingRowColors(True)
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.setSortingEnabled(False)
        self._table.verticalHeader().setVisible(False)
        self._table.horizontalHeader().setStretchLastSection(False)
        self._table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.Stretch)
        self._table.setColumnWidth(0, 65)
        self._table.setColumnWidth(1, 155)
        self._table.setColumnWidth(2, 85)
        self._table.setColumnWidth(3, 145)
        self._table.setColumnWidth(4, 75)
        self._table.setColumnWidth(6, 40)
        self._table.setFont(QFont("Consolas", 10))
        self._table.setWordWrap(False)
        self._table.setShowGrid(False)
        self._table.itemSelectionChanged.connect(self._on_selected)
        layout.addWidget(self._table)

        # Pagination bar
        page_wrap = QWidget()
        page_wrap.setStyleSheet("background-color: #1C1E24; border-top: 1px solid #2A2D35;")
        page_wrap.setFixedHeight(38)
        pbar = QHBoxLayout(page_wrap)
        pbar.setContentsMargins(12, 4, 12, 4)
        pbar.setSpacing(6)

        self._first_btn = QPushButton("|< First")
        self._first_btn.setFixedWidth(68)
        self._first_btn.clicked.connect(self._go_first)
        pbar.addWidget(self._first_btn)

        self._prev_btn = QPushButton("< Prev")
        self._prev_btn.setFixedWidth(60)
        self._prev_btn.clicked.connect(self._go_prev)
        pbar.addWidget(self._prev_btn)

        pbar.addStretch()

        pg_lbl = QLabel("Page")
        pg_lbl.setStyleSheet("color: #5A6270; font-size: 11px; background: transparent;")
        pbar.addWidget(pg_lbl)

        self._page_spin = QSpinBox()
        self._page_spin.setMinimum(1)
        self._page_spin.setMaximum(1)
        self._page_spin.setFixedWidth(64)
        self._page_spin.valueChanged.connect(self._on_spin)
        pbar.addWidget(self._page_spin)

        self._page_of = QLabel("of 1")
        self._page_of.setStyleSheet("color: #5A6270; font-size: 11px; background: transparent;")
        pbar.addWidget(self._page_of)

        pbar.addStretch()

        self._next_btn = QPushButton("Next >")
        self._next_btn.setFixedWidth(60)
        self._next_btn.clicked.connect(self._go_next)
        pbar.addWidget(self._next_btn)

        self._last_btn = QPushButton("Last >|")
        self._last_btn.setFixedWidth(68)
        self._last_btn.clicked.connect(self._go_last)
        pbar.addWidget(self._last_btn)

        sep3 = self._vsep()
        pbar.addWidget(sep3)

        self._range_label = QLabel("--")
        self._range_label.setStyleSheet("color: #404550; font-size: 10px; min-width: 160px; background: transparent;")
        self._range_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        pbar.addWidget(self._range_label)

        layout.addWidget(page_wrap)

    @staticmethod
    def _vsep():
        f = QFrame()
        f.setFrameShape(QFrame.Shape.VLine)
        f.setFixedHeight(20)
        f.setStyleSheet("color: #2A2D35;")
        return f

    # -- Public --------------------------------------------------

    def load_entries(self, entries: List[LogEntry]):
        self._entries = entries
        self._run_filter()

    def get_filtered_entries(self) -> List[LogEntry]:
        return self._filtered

    def clear(self):
        self._entries = []
        self._filtered = []
        self._current_page = 0
        self._table.setRowCount(0)
        self._count_label.setText("0 entries")
        self._update_controls()

    # -- Filter --------------------------------------------------

    def _run_filter(self):
        kw = self._search_box.text().strip().lower()
        lvl = self._level_combo.currentText()
        sec = self._sec_btn.isChecked()

        out = []
        for e in self._entries:
            if lvl != "All" and e.level != lvl:
                continue
            if sec and not e.extra.get('security_flag'):
                continue
            if kw and kw not in f"{e.message} {e.source} {e.timestamp} {e.event_id}".lower():
                continue
            out.append(e)

        self._filtered = out
        self._current_page = 0
        self._count_label.setText(f"{len(out):,} entries")
        self._update_controls()
        self._render()

    # -- Pagination ----------------------------------------------

    @property
    def _total_pages(self):
        return max(1, (len(self._filtered) + PAGE_SIZE - 1) // PAGE_SIZE)

    def _go_first(self): self._set_page(0)
    def _go_last(self):  self._set_page(self._total_pages - 1)
    def _go_prev(self):  self._set_page(max(0, self._current_page - 1))
    def _go_next(self):  self._set_page(min(self._total_pages - 1, self._current_page + 1))

    def _on_spin(self, v):
        if v - 1 != self._current_page:
            self._set_page(v - 1)

    def _set_page(self, p):
        self._current_page = max(0, min(p, self._total_pages - 1))
        self._update_controls()
        self._render()

    def _update_controls(self):
        total = self._total_pages
        cur   = self._current_page
        self._page_spin.blockSignals(True)
        self._page_spin.setMaximum(total)
        self._page_spin.setValue(cur + 1)
        self._page_spin.blockSignals(False)
        self._page_of.setText(f"of {total}")
        self._first_btn.setEnabled(cur > 0)
        self._prev_btn.setEnabled(cur > 0)
        self._next_btn.setEnabled(cur < total - 1)
        self._last_btn.setEnabled(cur < total - 1)
        n = len(self._filtered)
        s = cur * PAGE_SIZE + 1 if n else 0
        e = min((cur + 1) * PAGE_SIZE, n)
        self._range_label.setText(f"Showing {s:,} - {e:,} of {n:,}")

    # -- Render --------------------------------------------------

    def _render(self):
        start = self._current_page * PAGE_SIZE
        page  = self._filtered[start:start + PAGE_SIZE]

        self._table.setUpdatesEnabled(False)
        self._table.clearContents()
        self._table.setRowCount(len(page))

        for row, entry in enumerate(page):
            bg = QBrush(QColor(ROW_BG_ODD if row % 2 == 0 else ROW_BG_EVEN))
            fg_level = QBrush(QColor(LEVEL_FG.get(entry.level, DEFAULT_FG)))
            fg_dim   = QBrush(QColor('#606878'))
            fg_normal= QBrush(QColor('#9098A6'))
            fg_sec   = QBrush(QColor('#C86060'))

            cols = [
                (str(entry.line_number), fg_dim),
                (entry.timestamp,        fg_normal),
                (entry.level,            fg_level),
                (entry.source,           fg_normal),
                (entry.event_id,         fg_dim),
                (entry.message,          fg_normal),
                ("[!]" if entry.extra.get('security_flag') else "", fg_sec),
            ]
            for col, (text, fg) in enumerate(cols):
                item = QTableWidgetItem(text)
                item.setBackground(bg)
                item.setForeground(fg)
                self._table.setItem(row, col, item)
            self._table.setRowHeight(row, 21)

        self._table.setUpdatesEnabled(True)

    # -- Selection -----------------------------------------------

    def _on_selected(self):
        row = self._table.currentRow()
        if row < 0:
            return
        idx = self._current_page * PAGE_SIZE + row
        if 0 <= idx < len(self._filtered):
            self.row_selected.emit(self._filtered[idx])
