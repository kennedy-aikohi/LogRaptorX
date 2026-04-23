"""
LogRaptorX - Entry Detail Panel
Clean, readable layout with full author attribution.
Developer: Kennedy Aikohi
"""

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QTextEdit
from PyQt6.QtGui import QFont
from core.parser import LogEntry


class DetailPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        hdr = QLabel("ENTRY DETAIL")
        hdr.setStyleSheet(
            "color: #5A6270; font-size: 10px; letter-spacing: 0.8px; background: transparent;"
        )
        layout.addWidget(hdr)

        self._text = QTextEdit()
        self._text.setReadOnly(True)
        self._text.setFont(QFont("Consolas", 10))
        self._text.setStyleSheet("""
            QTextEdit {
                background-color: #14161A;
                border: 1px solid #2A2D35;
                color: #9098A6;
                padding: 10px;
                selection-background-color: #2A5298;
            }
        """)
        layout.addWidget(self._text)

    def show_entry(self, entry: LogEntry):
        sec = "  [SECURITY HIT]" if entry.extra.get('security_flag') else ""

        def row(label, value, color="#9098A6"):
            val = self._esc(value or "--")
            return (
                f'<tr>'
                f'<td style="color:#5A6270; padding: 2px 12px 2px 0; white-space: nowrap;">{label}</td>'
                f'<td style="color:{color}; padding: 2px 0;">{val}</td>'
                f'</tr>'
            )

        html = f"""
<div style="font-family: Consolas, monospace; font-size: 10pt; color: #9098A6;">
  <div style="color: #CDD3DE; font-size: 10pt; margin-bottom: 10px; font-weight: 600;">
    Entry {entry.line_number:,}{self._esc(sec)}
  </div>
  <table cellspacing="0" cellpadding="0" style="width: 100%;">
    {row("Timestamp", entry.timestamp, "#BEC4CE")}
    {row("Level",     entry.level,     "#8BAAC8")}
    {row("Source",    entry.source,    "#BEC4CE")}
    {row("Event ID",  entry.event_id)}
    {row("File",      entry.file_path, "#4A5060")}
  </table>
  <div style="margin-top: 12px; color: #5A6270; font-size: 9pt; letter-spacing: 0.6px;">MESSAGE</div>
  <div style="margin-top: 4px; color: #CDD3DE; white-space: pre-wrap; word-break: break-all;">
{self._esc(entry.message)}
  </div>
  <div style="margin-top: 12px; color: #5A6270; font-size: 9pt; letter-spacing: 0.6px;">RAW</div>
  <div style="margin-top: 4px; color: #4A5060; white-space: pre-wrap; word-break: break-all; font-size: 9pt;">
{self._esc(entry.raw[:800])}
  </div>
</div>
"""
        self._text.setHtml(html)

    @staticmethod
    def _esc(text: str) -> str:
        return (text or "") \
            .replace("&", "&amp;") \
            .replace("<", "&lt;") \
            .replace(">", "&gt;") \
            .replace('"', "&quot;")

    def clear(self):
        self._text.clear()
